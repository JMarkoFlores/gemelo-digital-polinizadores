from __future__ import annotations

import logging
from typing import Any
import httpx
from groq import Groq

from app.config import get_settings

logger = logging.getLogger("recommendation_service")


PROMPT_AGROECOLOGICO_TEMPLATE = """
Eres el Asistente Experto en Recomendaciones Agroecológicas del Gemelo Digital de Paisajes Agrícolas.

Analiza la siguiente comparativa de optimización multiobjetivo (Frente de Pareto generado por NSGA-II):

{resumen_comparativo}

Tu tarea es explicar de forma concisa, técnica y fundamentada:
1. MOTIVO DEL COMPROMISO (TRADE-OFF): Explica por qué la configuración recomendada es superior a los extremos del frente de Pareto (comparándola explícitamente con la alternativa de máximo rendimiento y la de máxima biodiversidad).
2. VARIABLES CLAVE DE DECISIÓN: Indica cuáles variables tuvieron mayor impacto agronómico (reducción de pesticidas, porcentaje de franjas florales y área natural). Cita cifras reales numéricas exactas del resumen.
3. RECOMENDACIÓN OPERATIVA EN CAMPO: Proporciona 1 o 2 acciones prácticas inmediatas para el agricultor en campo.

REGLAS ESTRICTAS:
- Cita cifras reales exactas del resumen provisto.
- Redacta en español, tono profesional y directo (máximo 3 párrafos compactos).
- No uses frases genéricas como 'es el mejor compromiso'; explica con fundamentos agronómicos y biológicos.
""".strip()


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def format_pareto_tradeoff_summary(
    baseline: dict[str, Any],
    best_solution: dict[str, Any],
    pareto_front: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """
    Construye la comparativa cuantitativa entre la línea base, la solución óptima
    y los extremos del frente de Pareto.
    """
    yb = _safe_float(baseline.get("crop_yield_index", baseline.get("rendimiento", 70.0)))
    pb = _safe_float(baseline.get("pollinator_abundance_index", baseline.get("polinizadores", 50.0)))
    pest_b = _safe_float(baseline.get("pesticide_level", 30.0))
    nat_b = _safe_float(baseline.get("natural_area_pct", 20.0))

    yo = _safe_float(best_solution.get("crop_yield_index", best_solution.get("rendimiento", yb)))
    po = _safe_float(best_solution.get("pollinator_abundance_index", best_solution.get("polinizadores", pb)))
    crop_o = _safe_float(best_solution.get("crop_area_pct", 60.0))
    nat_o = _safe_float(best_solution.get("natural_area_pct", 25.0))
    fl_o = _safe_float(best_solution.get("floral_strips_pct", 15.0))
    pest_o = _safe_float(best_solution.get("pesticide_level", 0.0))
    soil_o = _safe_float(best_solution.get("soil_management_score", 90.0))

    delta_y = round(yo - yb, 2)
    delta_p_pct = round(((po - pb) / max(1.0, pb)) * 100.0, 1)

    # Buscar extremos del frente de Pareto
    max_y_cand = max(pareto_front, key=lambda x: _safe_float(x.get("crop_yield_index", 0))) if pareto_front else best_solution
    max_p_cand = max(pareto_front, key=lambda x: _safe_float(x.get("pollinator_abundance_index", 0))) if pareto_front else best_solution

    max_y_val = round(_safe_float(max_y_cand.get("crop_yield_index", yo)), 2)
    max_y_poll = round(_safe_float(max_y_cand.get("pollinator_abundance_index", po)), 2)

    max_p_poll = round(_safe_float(max_p_cand.get("pollinator_abundance_index", po)), 2)
    max_p_yield = round(_safe_float(max_p_cand.get("crop_yield_index", yo)), 2)

    structured_summary = {
        "linea_base": {
            "rendimiento": round(yb, 2),
            "polinizadores": round(pb, 2),
            "pesticidas_pct": round(pest_b, 1),
            "area_natural_pct": round(nat_b, 1),
        },
        "solucion_recomendada": {
            "rendimiento": round(yo, 2),
            "delta_rendimiento": delta_y,
            "polinizadores": round(po, 2),
            "delta_polinizadores_pct": delta_p_pct,
            "area_cultivo_pct": round(crop_o, 1),
            "area_natural_pct": round(nat_o, 1),
            "franjas_florales_pct": round(fl_o, 1),
            "pesticidas_pct": round(pest_o, 2),
            "salud_suelo": round(soil_o, 1),
        },
        "alternativas_frente": {
            "max_rendimiento": {"rendimiento": max_y_val, "polinizadores": max_y_poll},
            "max_polinizadores": {"polinizadores": max_p_poll, "rendimiento": max_p_yield},
        },
    }

    text_summary = f"""
COMPARATIVA DE OPTIMIZACIÓN MULTIOBJETIVO DEL PAISAJE:
- LÍNEA BASE (ESTADO ACTUAL):
  * Rendimiento Agrícola: {round(yb, 2)}
  * Abundancia de Polinizadores: {round(pb, 2)}
  * Uso de Pesticidas: {round(pest_b, 1)}%
  * Área Natural: {round(nat_b, 1)}%

- CONFIGURACIÓN ÓPTIMA SELECCIONADA (RECOMENDACIÓN NSGA-II):
  * Rendimiento Proyectado: {round(yo, 2)} (Delta: {delta_y:+} unidades)
  * Abundancia de Polinizadores: {round(po, 2)} (Incremento: {delta_p_pct:+}%)
  * Distribución del Paisaje: {round(crop_o, 1)}% cultivo comercial, {round(nat_o, 1)}% área natural protegida, {round(fl_o, 1)}% franjas florales
  * Nivel de Pesticidas: reducido a {round(pest_o, 2)}%
  * Índice de Manejo del Suelo: {round(soil_o, 1)} / 100

- EXTREMOS ALTERNATIVOS DEL FRENTE DE PARETO (NO ELEGIDOS):
  * Alternativa Max Rendimiento: Alcanza rendimiento {max_y_val}, pero la abundancia de polinizadores se degrada a {max_y_poll}.
  * Alternativa Max Conservación: Eleva polinizadores a {max_p_poll}, pero penaliza el rendimiento reduciéndolo a {max_p_yield}.
""".strip()

    return text_summary, structured_summary


def call_langflow_flow(payload: dict[str, Any]) -> str | None:
    """
    Invoca el flujo de Langflow expuesto en su API REST.
    """
    settings = get_settings()
    url = f"{settings.langflow_url.rstrip('/')}/api/v1/run/{settings.langflow_flow_id}"

    try:
        with httpx.Client(timeout=4.5) as client:
            response = client.post(
                url,
                json={
                    "input_value": payload.get("comparativa_texto", ""),
                    "input_type": "chat",
                    "output_type": "chat",
                    "tweaks": {
                        "DatosOptimizacionInput": {
                            "frente_pareto": payload.get("frente_pareto", []),
                            "solucion_elegida": payload.get("solucion_elegida", {}),
                            "linea_base": payload.get("linea_base", {}),
                        }
                    },
                },
            )
            if response.status_code == 200:
                data = response.json()
                # Extraer texto del formato de respuesta estándar de Langflow
                outputs = data.get("outputs", [])
                if outputs:
                    for out in outputs:
                        for item in out.get("outputs", []):
                            results = item.get("results", {})
                            message = results.get("message", {})
                            text = message.get("text") or results.get("text")
                            if text and str(text).strip():
                                return str(text).strip()
    except Exception as exc:
        logger.debug(f"Langflow no disponible o tiempo de espera agotado: {exc}")

    return None


def call_groq_direct_fallback(comparativa_texto: str) -> str | None:
    """
    Ejecuta el prompt de Langflow directamente vía Groq si Langflow no está activo.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        return None

    try:
        client = Groq(api_key=settings.groq_api_key)
        prompt = PROMPT_AGROECOLOGICO_TEMPLATE.format(resumen_comparativo=comparativa_texto)

        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.25,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un agrónomo y ecólogo experto en modelado agroecológico y toma de decisiones multiobjetivo.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=650,
        )
        content = response.choices[0].message.content or ""
        if content.strip():
            return content.strip()
    except Exception as exc:
        logger.debug(f"Fallo en llamada directa a Groq: {exc}")

    return None


def generate_deterministic_recommendation(summary: dict[str, Any]) -> str:
    """
    Genera una explicación agroecológica dinámica y cuantitativa basada en los datos reales
    cuando no hay conexión a Langflow ni a Groq.
    """
    sol = summary["solucion_recomendada"]
    base = summary["linea_base"]
    alts = summary["alternativas_frente"]

    delta_y = sol["delta_rendimiento"]
    delta_p = sol["delta_polinizadores_pct"]
    yo = sol["rendimiento"]
    base_y = base["rendimiento"]
    po = sol["polinizadores"]
    base_p = base["polinizadores"]
    pest = sol["pesticidas_pct"]
    franjas = sol["franjas_florales_pct"]
    nat = sol["area_natural_pct"]
    max_y = alts["max_rendimiento"]["rendimiento"]
    max_y_p = alts["max_rendimiento"]["polinizadores"]
    max_p = alts["max_polinizadores"]["polinizadores"]
    max_p_y = alts["max_polinizadores"]["rendimiento"]

    sign_y = f"+{delta_y}" if delta_y >= 0 else f"{delta_y}"

    p1 = (
        f"Esta configuración fue seleccionada por el algoritmo NSGA-II porque representa el punto de equilibrio óptimo "
        f"en el Frente de Pareto: incrementa la abundancia de polinizadores en un **+{delta_p}%** ({base_p} ➔ **{po}**) "
        f"protegiendo simultáneamente la productividad agrícola ({base_y} ➔ **{yo}**, variación neta de **{sign_y}**). "
        f"Frente a la alternativa puramente productivista ({max_y} de rendimiento pero apenas {max_y_p} de polinizadores) "
        f"y la conservacionista extrema ({max_p} de polinizadores con caída a {max_p_y} de rendimiento), este escenario evita "
        f"el colapso ecológico sin castigar la rentabilidad del lote."
    )

    p2 = (
        f"Los factores determinantes de esta solución fueron la drástica reducción del uso de pesticidas a **{pest}%** "
        f"y la integración estratégica de **{franjas}% de franjas florales** junto a un **{nat}% de área natural**. "
        f"La diversificación del paisaje mitiga la deriva química y genera corredores biológicos continuos para el forrajeo de abejas nativas."
    )

    p3 = (
        f"**Recomendación en campo:** Establecer setos vivos y bordes florales en los perímetros del lote con especies melíferas locales, "
        f"y programar aplicaciones de bioplaguicidas únicamente fuera de los horarios de pecoreo para consolidar la meta de {po} de abundancia."
    )

    return f"{p1}\n\n{p2}\n\n{p3}"


def generate_ai_recommendation(
    baseline: dict[str, Any],
    best_solution: dict[str, Any],
    pareto_front: list[dict[str, Any]],
) -> str:
    """
    Punto de entrada principal para generar la recomendación agroecológica inteligente.
    Intenta:
    1. Langflow REST API (flujo visual de agentes)
    2. Fallback directo a Groq con el mismo prompt del flujo
    3. Fallback heurístico dinámico basado en las cifras reales de la optimización
    4. Fallback original como red de seguridad absoluta
    """
    try:
        comparativa_texto, structured_summary = format_pareto_tradeoff_summary(
            baseline=baseline,
            best_solution=best_solution,
            pareto_front=pareto_front,
        )

        payload = {
            "comparativa_texto": comparativa_texto,
            "structured_summary": structured_summary,
            "frente_pareto": pareto_front,
            "solucion_elegida": best_solution,
            "linea_base": baseline,
        }

        # 1. Intento con Langflow
        langflow_result = call_langflow_flow(payload)
        if langflow_result:
            return langflow_result

        # 2. Intento directo con Groq (mismo prompt del flujo)
        groq_result = call_groq_direct_fallback(comparativa_texto)
        if groq_result:
            return groq_result

        # 3. Fallback analítico cuantitativo con datos reales
        return generate_deterministic_recommendation(structured_summary)

    except Exception as exc:
        logger.error(f"Error inesperado generando recomendación agroecológica: {exc}")
        # Red de seguridad: mantener el texto previo para no romper nada
        return "Mejor compromiso entre proteger el rendimiento y maximizar la ganancia de polinizadores."
