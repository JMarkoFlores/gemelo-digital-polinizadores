from __future__ import annotations

import logging
from typing import Any, Tuple
try:
    import httpx
except ImportError:
    httpx = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from app.config import get_settings
except ImportError:
    class MinimalSettings:
        langflow_url = "http://langflow:7860"
        langflow_flow_id = "asistente-recomendaciones-agroecologicas"
        groq_api_key = ""
        groq_model = "llama-3.3-70b-versatile"
    def get_settings():
        return MinimalSettings()

logger = logging.getLogger("recommendation_service")


PROMPT_AGROECOLOGICO_TEMPLATE = """
Eres el Asistente en Análisis de Escenarios Agroecológicos del Gemelo Digital de Paisajes.

Analiza la siguiente comparativa de optimización multiobjetivo (Frente de Pareto generado por NSGA-II):

{resumen_comparativo}

Tu tarea es explicar de forma concisa, técnica y fundamentada:
1. MOTIVO DEL COMPROMISO (TRADE-OFF): Explica por qué la configuración seleccionada equilibra los índices simulados frente a los extremos del frente.
2. VARIABLES DE CONFIGURACIÓN: Cita los valores modelados exactos del resumen (índice de plaguicidas, porcentaje de franjas florales y área natural).
3. SUGERENCIAS DE MANEJO: 1 o 2 prácticas generales recomendadas, aclarando que son referenciales y no reemplazan la validación técnica en campo.

REGLAS ESTRICTAS:
- Usa 'índice predicho', 'índice de rendimiento' y 'configuración seleccionada'. No afirmes rentabilidad económica ni conservación observada de campo.
- Cita cifras exactas del resumen provisto.
- Máximo 3 párrafos compactos en español.
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
- LÍNEA BASE (ESTADO REFERENCIAL):
  * Índice de Rendimiento: {round(yb, 2)}
  * Índice de Abundancia de Polinizadores: {round(pb, 2)}
  * Nivel de Plaguicidas: {round(pest_b, 1)}
  * Área Natural: {round(nat_b, 1)}%

- CONFIGURACIÓN SELECCIONADA POR CRITERIO MULTICRITERIO:
  * Índice de Rendimiento Predicho: {round(yo, 2)} (Delta: {delta_y:+} unidades)
  * Índice de Abundancia Predicho: {round(po, 2)} (Cambio: {delta_p_pct:+}%)
  * Distribución del Paisaje: {round(crop_o, 1)}% cultivo, {round(nat_o, 1)}% natural, {round(fl_o, 1)}% franjas florales
  * Nivel de Plaguicidas: {round(pest_o, 2)}
  * Calificación de Manejo del Suelo: {round(soil_o, 1)}

- EXTREMOS DEL FRENTE DE PARETO:
  * Máximo Rendimiento: {max_y_val} (abundancia de polinizadores: {max_y_poll})
  * Máxima Abundancia: {max_p_poll} (rendimiento: {max_p_yield})
""".strip()

    return text_summary, structured_summary


def call_langflow_flow(payload: dict[str, Any]) -> str | None:
    if httpx is None:
        return None
    settings = get_settings()
    url = f"{settings.langflow_url.rstrip('/')}/api/v1/run/{settings.langflow_flow_id}"

    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.post(
                url,
                json={
                    "input_value": payload.get("comparativa_texto", ""),
                    "input_type": "chat",
                    "output_type": "chat",
                },
            )
            if response.status_code == 200:
                data = response.json()
                outputs = data.get("outputs", [])
                if outputs:
                    for out in outputs:
                        for item in out.get("outputs", []):
                            results = item.get("results", {})
                            message = results.get("message", {})
                            text = message.get("text") or results.get("text")
                            if text and str(text).strip():
                                return f"[Origen: Asistente Langflow]\n{str(text).strip()}"
    except Exception as exc:
        logger.debug("Langflow no disponible: %s", exc)

    return None


def call_groq_direct_fallback(comparativa_texto: str) -> str | None:
    settings = get_settings()
    if not settings.groq_api_key or Groq is None:
        return None

    try:
        client = Groq(api_key=settings.groq_api_key)
        prompt = PROMPT_AGROECOLOGICO_TEMPLATE.format(resumen_comparativo=comparativa_texto)

        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.25,
            messages=[
                {"role": "system", "content": "Eres un asistente de modelado agroecológico cuantitativo."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=650,
        )
        content = response.choices[0].message.content or ""
        if content.strip():
            return f"[Origen: Servicio LLM Groq]\n{content.strip()}"
    except Exception as exc:
        logger.debug("Fallo en llamada directa a Groq: %s", exc)

    return None


def generate_deterministic_recommendation(summary: dict[str, Any]) -> str:
    """
    Genera una explicación cuantitativa estructurada basada en los índices calculados,
    claramente identificada como fallback heurístico local.
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
        f"[Origen: Análisis heurístico determinista]\n"
        f"Esta configuración fue seleccionada mediante la regla operativa multi-criterio sobre el Frente de Pareto verificado: "
        f"proyecta una variación del índice de abundancia de polinizadores de **+{delta_p}%** ({base_p} ➔ **{po}**) "
        f"manteniendo el índice de rendimiento agrícola ({base_y} ➔ **{yo}**, variación neta de **{sign_y}**). "
        f"Frente a la alternativa de máximo rendimiento del frente ({max_y} de rendimiento, {max_y_p} de polinizadores) "
        f"y la de máxima conservación ({max_p} de polinizadores, {max_p_y} de rendimiento), este escenario equilibra ambos objetivos modelados."
    )

    p2 = (
        f"La configuración se compone de un nivel de plaguicidas de **{pest}**, "
        f"con **{franjas}% de franjas florales** y **{nat}% de área natural**. "
        f"Estas proporciones corresponden a composiciones estimadas del paisaje para mitigar la presión química."
    )

    p3 = (
        f"*Nota metodológica:* Las sugerencias agronómicas derivadas del modelo representan pautas orientativas "
        f"y no constituyen prescripciones validadas en campo. Requieren contrastación agronómica y ecológica local."
    )

    return f"{p1}\n\n{p2}\n\n{p3}"


def generate_ai_recommendation(
    baseline: dict[str, Any],
    best_solution: Optional[dict[str, Any]],
    pareto_front: list[dict[str, Any]],
) -> str:
    """
    Genera la recomendación narrativa sin mutar las métricas numéricas del baseline ni del resultado.
    """
    if not best_solution:
        return "Sin recomendación: no se encontraron soluciones admisibles en el espacio de búsqueda."
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

        langflow_result = call_langflow_flow(payload)
        if langflow_result:
            return langflow_result

        groq_result = call_groq_direct_fallback(comparativa_texto)
        if groq_result:
            return groq_result

        return generate_deterministic_recommendation(structured_summary)

    except Exception as exc:
        logger.error("Error generando recomendación: %s", exc)
        return (
            "[Origen: Fallback básico]\n"
            "Configuración seleccionada por regla operativa multi-criterio. "
            "Sujeta a revisión agronómica especializada."
        )
