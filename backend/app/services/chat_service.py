from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from groq import Groq
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Simulacion, Usuario


SYSTEM_BASE_PROMPT = """
Eres el Asistente Inteligente del Gemelo Digital Agroecológico "Gemelos Digitales 02" (gemelo-digital-polinizadores).
Tu misión es asistir a los usuarios interpretando los resultados de simulaciones, el impacto de variables agronómicas
(pesticidas, áreas naturales, franjas florales, escenarios climáticos) en el rendimiento de cultivos y la abundancia/diversidad
de polinizadores, así como responder consultas con datos reales de la base de datos del sistema.

REGLAS DE ORO:
1. RESPONDE LA PREGUNTA EXACTA QUE HACE EL USUARIO:
   - Si pregunta cuántas simulaciones ha hecho, responde con el número exacto y detalle de sus simulaciones.
   - Si pregunta por una simulación específica (#X), analiza y explica las métricas de esa simulación.
   - Si pregunta por cómo funciona el sistema, explica la metodología respondiendo a su duda concreta.
   - NUNCA repitas una misma respuesta predeterminada para preguntas diferentes.
2. CONTROL DE ROLES Y PRIVACIDAD:
   - Rol "admin": Puede consultar usuarios activos, totales del sistema, ranking global de regiones y cualquier simulación.
   - Rol "cliente": ÚNICAMENTE puede consultar sus propias simulaciones. No tiene acceso a datos de otros usuarios ni a estadísticas de administración del sistema (como conteo global de usuarios activos). Si solicita datos restringidos, explícale de forma cortés que no cuenta con permisos para ver datos administrativos y ofrécele ayuda con sus propias simulaciones.
3. CONTEXTO E HISTORIAL:
   - Mantén el hilo de la conversación considerando los mensajes previos del usuario.
   - Usa un tono profesional, claro, empático y en español.
""".strip()


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _extract_metric(data: dict[str, Any] | None, *keys: str, default: float = 0.0) -> float:
    if not isinstance(data, dict):
        return default
    for k in keys:
        if k in data and data[k] is not None:
            return _safe_float(data[k], default)
    return default


def _extract_region(simulation: Simulacion) -> str:
    mb = simulation.metricas_base
    if isinstance(mb, dict):
        region = mb.get("region_label")
        if region and str(region).strip():
            return str(region).strip()
        center = mb.get("center")
        if isinstance(center, (list, tuple)) and len(center) == 2:
            return f"Lat: {center[0]:.2f}, Lon: {center[1]:.2f}"
    return "Parcela Agrícola"


# ==========================================
# FUNCIONES DE CONSULTA A LA BASE DE DATOS
# ==========================================

def query_simulation_details(db: Session, user: Usuario, simulation_id: int) -> dict[str, Any]:
    """Obtiene datos detallados de una simulación específica respetando el control de roles."""
    sim = db.query(Simulacion).filter(Simulacion.id == simulation_id).first()
    if not sim:
        return {
            "status": "error",
            "encontrada": False,
            "mensaje": f"No se encontró la simulación #{simulation_id} en el sistema.",
        }

    # Control de rol estricto
    if user.rol != "admin" and sim.usuario_id != user.id:
        return {
            "status": "forbidden",
            "encontrada": False,
            "acceso_denegado": True,
            "mensaje": f"Acceso restringido: La simulación #{simulation_id} no pertenece a tu cuenta de usuario.",
        }

    yb = _extract_metric(sim.metricas_base, "crop_yield_index", "rendimiento", default=0.0)
    yo = _extract_metric(sim.metricas_optimas, "crop_yield_index", "rendimiento", default=yb)
    pb = _extract_metric(sim.metricas_base, "pollinator_abundance_index", "polinizadores", default=0.0)
    po = _extract_metric(sim.metricas_optimas, "pollinator_abundance_index", "polinizadores", default=pb)
    db_val = _extract_metric(sim.metricas_base, "pollinator_diversity_index", "diversidad", default=0.0)
    do_val = _extract_metric(sim.metricas_optimas, "pollinator_diversity_index", "diversidad", default=db_val)

    delta_yield = round(yo - yb, 2)
    delta_poll_pct = round(((po - pb) / max(1.0, pb)) * 100.0, 2)

    return {
        "status": "success",
        "encontrada": True,
        "simulacion_id": sim.id,
        "fecha": sim.fecha.strftime("%Y-%m-%d %H:%M:%S") if sim.fecha else "N/A",
        "region": _extract_region(sim),
        "usuario_id": sim.usuario_id,
        "variables_entrada": {
            "nivel_pesticidas": sim.variables_entrada.get("pesticide_level", sim.variables_entrada.get("pesticidas")),
            "area_natural_minima_pct": sim.variables_entrada.get("min_natural_area_pct", sim.variables_entrada.get("area_natural_minima")),
            "escenario_climatico": sim.variables_entrada.get("climate_scenario", sim.variables_entrada.get("escenario", "actual")),
        },
        "metricas_base": {
            "rendimiento": round(yb, 2),
            "abundancia_polinizadores": round(pb, 2),
            "diversidad_polinizadores": round(db_val, 2) if db_val else None,
        },
        "metricas_optimas": {
            "rendimiento": round(yo, 2),
            "abundancia_polinizadores": round(po, 2),
            "diversidad_polinizadores": round(do_val, 2) if do_val else None,
            "area_cultivo_pct": sim.metricas_optimas.get("crop_area_pct"),
            "area_natural_pct": sim.metricas_optimas.get("natural_area_pct"),
            "franjas_florales_pct": sim.metricas_optimas.get("floral_strips_pct"),
            "nivel_pesticidas_recomendado": sim.metricas_optimas.get("pesticide_level"),
            "salud_suelo": sim.metricas_optimas.get("soil_management_score"),
            "justificacion": sim.metricas_optimas.get("selection_reason"),
        },
        "mejoras": {
            "delta_rendimiento": delta_yield,
            "delta_polinizadores_porcentaje": f"+{delta_poll_pct}%" if delta_poll_pct >= 0 else f"{delta_poll_pct}%",
        },
        "total_soluciones_pareto": len(sim.frente_pareto) if isinstance(sim.frente_pareto, list) else 0,
    }


def query_active_users_count(db: Session, user: Usuario) -> dict[str, Any]:
    """Obtiene el conteo real de usuarios activos en la plataforma (solo administradores)."""
    if user.rol != "admin":
        return {
            "status": "forbidden",
            "acceso_denegado": True,
            "mensaje": "Acceso denegado: El conteo de usuarios del sistema es información confidencial solo disponible para administradores.",
        }

    total_usuarios = db.query(func.count(Usuario.id)).scalar() or 0
    usuarios_activos = db.query(func.count(Usuario.id)).filter(Usuario.activo.is_(True)).scalar() or 0
    usuarios_inactivos = total_usuarios - usuarios_activos
    admins = db.query(func.count(Usuario.id)).filter(Usuario.rol == "admin").scalar() or 0
    clientes = db.query(func.count(Usuario.id)).filter(Usuario.rol == "cliente").scalar() or 0

    return {
        "status": "success",
        "total_usuarios": total_usuarios,
        "usuarios_activos": usuarios_activos,
        "usuarios_inactivos": usuarios_inactivos,
        "administradores": admins,
        "clientes": clientes,
    }


def query_regions_summary(db: Session, user: Usuario) -> dict[str, Any]:
    """Obtiene la distribución y ranking de regiones con más simulaciones."""
    query = db.query(Simulacion)
    if user.rol != "admin":
        query = query.filter(Simulacion.usuario_id == user.id)

    simulations = query.all()
    if not simulations:
        return {
            "status": "success",
            "total_simulaciones": 0,
            "ranking_regiones": [],
            "mensaje": "No hay simulaciones registradas en este alcance.",
        }

    counts: dict[str, int] = {}
    for s in simulations:
        reg = _extract_region(s)
        counts[reg] = counts.get(reg, 0) + 1

    sorted_regions = [{"region": reg, "total_simulaciones": cnt} for reg, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

    return {
        "status": "success",
        "ambito": "global" if user.rol == "admin" else "usuario_actual",
        "total_simulaciones_analizadas": len(simulations),
        "region_con_mas_simulaciones": sorted_regions[0]["region"] if sorted_regions else "N/A",
        "ranking_regiones": sorted_regions[:5],
    }


def query_simulations_summary(db: Session, user: Usuario) -> dict[str, Any]:
    """Obtiene conteo exacto y resumen de las simulaciones registradas para el usuario o sistema."""
    user_sim_count = db.query(func.count(Simulacion.id)).filter(Simulacion.usuario_id == user.id).scalar() or 0
    total_system_count = db.query(func.count(Simulacion.id)).scalar() or 0

    query = db.query(Simulacion)
    if user.rol != "admin":
        query = query.filter(Simulacion.usuario_id == user.id)

    sims = query.order_by(Simulacion.fecha.desc()).all()

    recent = [
        {
            "id": s.id,
            "fecha": s.fecha.strftime("%Y-%m-%d %H:%M") if s.fecha else "N/A",
            "region": _extract_region(s),
            "rendimiento_optimo": _extract_metric(s.metricas_optimas, "crop_yield_index", "rendimiento"),
            "polinizadores_optimos": _extract_metric(s.metricas_optimas, "pollinator_abundance_index", "polinizadores"),
        }
        for s in sims[:5]
    ]

    return {
        "status": "success",
        "ambito": "global" if user.rol == "admin" else "usuario_actual",
        "simulaciones_del_usuario": user_sim_count,
        "simulaciones_totales_sistema": total_system_count if user.rol == "admin" else None,
        "total_en_alcance": len(sims),
        "ultimas_simulaciones": recent,
    }


# ==========================================
# PRE-RETRIEVAL: RECUPERACIÓN PREVIA DE DATOS
# ==========================================

def retrieve_context_before_llm(message: str, user: Usuario, db: Session) -> tuple[str, dict[str, Any]]:
    """
    Analiza la pregunta del usuario y recupera preventivamente los datos reales relevantes de la BD.
    Retorna un texto de contexto y un diccionario estructurado de datos recuperados.
    """
    context_chunks: list[str] = []
    structured_data: dict[str, Any] = {}
    msg_lower = message.lower()

    # 1. Detección de solicitud de simulación específica (ej: "simulación #16", "simulacion 1", "mi simulación #4")
    sim_matches = re.findall(r'(?:simulaci[oó]n|#)\s*#?(\d+)', message, re.IGNORECASE)
    if not sim_matches:
        sim_matches = re.findall(r'\b(?:id|numero|número)\s*(\d+)\b', message, re.IGNORECASE)

    if sim_matches:
        sim_id = int(sim_matches[0])
        sim_data = query_simulation_details(db, user, sim_id)
        structured_data["simulation_query"] = sim_data
        if sim_data.get("acceso_denegado"):
            context_chunks.append(
                f"[SEGURIDAD]: El usuario con rol '{user.rol}' ha intentado consultar la simulación #{sim_id}, "
                f"pero no le pertenece. Debes denegar el acceso amablemente y recordarle que solo puede ver sus propias simulaciones."
            )
        elif sim_data.get("encontrada"):
            context_chunks.append(
                f"[DATOS REALES DE LA BASE DE DATOS - SIMULACIÓN #{sim_id}]:\n"
                f"{json.dumps(sim_data, ensure_ascii=False, indent=2)}"
            )
        else:
            context_chunks.append(
                f"[DATOS REALES]: No existe ninguna simulación con el ID #{sim_id} en la base de datos."
            )

    # 2. Detección de preguntas sobre cantidad de simulaciones del usuario
    # Cubre: "¿cuántas simulaciones hice yo?", "¿cuántas simulaciones ya hice?", "¿cuántas simulaciones he hecho?", "mis simulaciones"
    is_asking_sim_count = (
        any(k in msg_lower for k in ["cuantas simulaciones", "cuántas simulaciones", "cuantas hice", "cuántas hice", "hice yo", "ya hice", "he hecho", "he realizado", "mis simulaciones"])
        or (("simulaci" in msg_lower) and any(w in msg_lower for w in ["cuant", "cuánt", "total", "hice", "llevo", "registrad"]))
    )

    if is_asking_sim_count:
        sims_summary = query_simulations_summary(db, user)
        structured_data["simulations_summary"] = sims_summary
        user_count = sims_summary["simulaciones_del_usuario"]
        context_chunks.append(
            f"[DATOS REALES DE LA BASE DE DATOS - CONTEO EXACTO DE SIMULACIONES]:\n"
            f"- El usuario actual ({user.email}, ID {user.id}) ha realizado exactamente {user_count} simulación(es) en total.\n"
            f"- Detalle de las últimas simulaciones realizadas por este usuario:\n"
            f"{json.dumps(sims_summary.get('ultimas_simulaciones', []), ensure_ascii=False, indent=2)}"
        )

    # 3. Detección de preguntas sobre usuarios activos / total de usuarios
    if any(term in msg_lower for term in ["usuario activo", "usuarios activos", "cuantos usuarios", "cuántos usuarios", "total de usuarios"]):
        if user.rol == "admin":
            users_data = query_active_users_count(db, user)
            structured_data["users_data"] = users_data
            context_chunks.append(
                f"[DATOS REALES DE LA BASE DE DATOS - USUARIOS DEL SISTEMA]:\n"
                f"{json.dumps(users_data, ensure_ascii=False, indent=2)}"
            )
        else:
            context_chunks.append(
                f"[SEGURIDAD]: El usuario tiene rol 'cliente' y pregunta por usuarios del sistema. "
                f"El conteo global de usuarios es información administrativa confidencial. Indícale cortésmente que no cuenta con permisos de administrador."
            )

    # 4. Detección de preguntas sobre regiones
    if any(term in msg_lower for term in ["región", "region", "regiones", "zona"]):
        regions_data = query_regions_summary(db, user)
        structured_data["regions_data"] = regions_data
        context_chunks.append(
            f"[DATOS REALES DE LA BASE DE DATOS - REGIONES Y SIMULACIONES]:\n"
            f"{json.dumps(regions_data, ensure_ascii=False, indent=2)}"
        )

    return "\n\n".join(context_chunks), structured_data


# ==========================================
# GENERADOR LOCAL DE RESPALDO (SIN GROQ)
# ==========================================

def generate_local_fallback_reply(
    message: str,
    user: Usuario,
    db: Session,
    structured_data: dict[str, Any],
) -> str:
    """
    Genera una respuesta inteligente con datos 100% reales de la base de datos
    cuando GROQ_API_KEY no está configurada o si el proveedor LLM no está disponible.
    """
    msg_lower = message.lower()

    # 1. Consulta por simulación específica
    if "simulation_query" in structured_data:
        sim = structured_data["simulation_query"]
        if sim.get("acceso_denegado"):
            return f"🔒 **Acceso restringido:** La simulación solicitada no pertenece a tu cuenta de usuario ({user.email}). Como usuario con rol **{user.rol}**, únicamente puedes consultar tus propias simulaciones."
        if not sim.get("encontrada"):
            return f"❌ No se encontró ninguna simulación con el identificador solicitado en la base de datos."

        sid = sim["simulacion_id"]
        fecha = sim["fecha"]
        region = sim["region"]
        base_y = sim["metricas_base"]["rendimiento"]
        opt_y = sim["metricas_optimas"]["rendimiento"]
        base_p = sim["metricas_base"]["abundancia_polinizadores"]
        opt_p = sim["metricas_optimas"]["abundancia_polinizadores"]
        delta_p = sim["mejoras"]["delta_polinizadores_porcentaje"]
        pesticidas = sim["variables_entrada"]["nivel_pesticidas"]
        nat_pct = sim["variables_entrada"]["area_natural_minima_pct"]

        return (
            f"📊 **Resultados de la Simulación #{sid}:**\n\n"
            f"- **Fecha:** {fecha}\n"
            f"- **Región / Parcela:** {region}\n"
            f"- **Variables de Entrada:** Nivel de pesticidas: {pesticidas}% | Área natural mínima: {nat_pct}%\n"
            f"- **Rendimiento Agrícola:** Inicial: {base_y} ➔ Optimizado: **{opt_y}**\n"
            f"- **Abundancia de Polinizadores:** Inicial: {base_p} ➔ Optimizada: **{opt_p}** ({delta_p})\n"
            f"- **Soluciones Pareto:** Se hallaron {sim['total_soluciones_pareto']} configuraciones en la frontera óptima."
        )

    # 2. Conteo de simulaciones del usuario
    if "simulations_summary" in structured_data or any(k in msg_lower for k in ["cuantas", "cuántas", "hice", "he hecho"]):
        sims_summary = structured_data.get("simulations_summary") or query_simulations_summary(db, user)
        count = sims_summary["simulaciones_del_usuario"]

        if count == 0:
            return (
                f"Actualmente no has registrado ninguna simulación con tu cuenta (**{user.email}**). "
                f"Puedes ir a la sección **Optimización** para dibujar una parcela en el mapa y ejecutar tu primera simulación agroecológica."
            )

        recent_lines = []
        for s in sims_summary.get("ultimas_simulaciones", [])[:3]:
            recent_lines.append(f"  • **Simulación #{s['id']}** ({s['fecha']}) en *{s['region']}*: Rendimiento óptimo {s['rendimiento_optimo']}, Polinizadores {s['polinizadores_optimos']}.")

        history_text = "\n".join(recent_lines)
        return (
            f"📈 Has realizado un total de **{count} simulación(es)** con tu cuenta (**{user.email}**).\n\n"
            f"**Tus simulaciones más recientes:**\n{history_text}\n\n"
            f"Puedes preguntarme detalles sobre cualquiera de ellas diciendo por ejemplo: *'¿Qué resultados dio mi simulación #{sims_summary['ultimas_simulaciones'][0]['id']}?'*"
        )

    # 3. Usuarios activos (control de roles)
    if any(k in msg_lower for k in ["usuario", "usuarios"]):
        if user.rol == "admin":
            u_data = query_active_users_count(db, user)
            return (
                f"👥 **Métricas de Usuarios del Sistema:**\n\n"
                f"- **Usuarios Activos:** {u_data['usuarios_activos']}\n"
                f"- **Usuarios Inactivos:** {u_data['usuarios_inactivos']}\n"
                f"- **Total Registrados:** {u_data['total_usuarios']} (Administradores: {u_data['administradores']}, Clientes: {u_data['clientes']})"
            )
        else:
            return (
                f"🔒 Por motivos de seguridad y privacidad, el rol **cliente** no tiene acceso a las métricas globales de usuarios del sistema. "
                f"Con gusto puedo ayudarte con el conteo de tus simulaciones, resultados agronómicos o interpretación de polinizadores."
            )

    # 4. Regiones
    if any(k in msg_lower for k in ["region", "región", "regiones", "zona"]):
        r_data = query_regions_summary(db, user)
        if r_data["total_simulaciones_analizadas"] == 0:
            return "No hay simulaciones registradas actualmente para analizar regiones."
        top_reg = r_data["region_con_mas_simulaciones"]
        ranking_str = ", ".join([f"{r['region']} ({r['total_simulaciones']})" for r in r_data["ranking_regiones"][:3]])
        return (
            f"🗺️ La región con más simulaciones es **{top_reg}**.\n"
            f"- Distribución principal: {ranking_str}."
        )

    # 5. Preguntas generales sobre cómo funciona
    return (
        "🌱 **Gemelos Digitales 02** es una plataforma agroecológica de toma de decisiones que combina:\n\n"
        "1. **Modelos Basados en Agentes (ABM):** Simulan el comportamiento y forrajeo de polinizadores en el paisaje.\n"
        "2. **Modelo Sustituto (Surrogate DNN):** Predice rápidamente el rendimiento de cultivos y la abundancia de especies.\n"
        "3. **Optimización Multiobjetivo (Algoritmo NSGA-II):** Encuentra el Frente de Pareto entre rentabilidad agrícola y conservación biológica.\n\n"
        "Puedes preguntarme por tus simulaciones registradas, métricas específicas (#ID) o sugerencias agronómicas."
    )


# ==========================================
# GENERADOR PRINCIPAL DEL CHAT
# ==========================================

def generate_chat_reply(
    message: str,
    user: Usuario | None = None,
    db: Session | None = None,
    history: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """
    Genera la respuesta del chatbot utilizando Groq con acceso a datos reales de PostgreSQL,
    historial conversacional y control estricto de roles de usuario (admin / cliente).
    Si Groq no está configurado o falla, activa el motor local con datos reales de la BD.
    """
    settings = get_settings()

    # Si hay sesión de BD y usuario autenticado, recuperamos los datos reales pertinentes
    structured_data: dict[str, Any] = {}
    pre_retrieved_context = ""
    if user is not None and db is not None:
        pre_retrieved_context, structured_data = retrieve_context_before_llm(message, user, db)

    # Si no hay GROQ_API_KEY configurada en el entorno, respondemos con el motor local y datos reales
    if not settings.groq_api_key:
        if user is not None and db is not None:
            reply = generate_local_fallback_reply(message, user, db, structured_data)
            return reply, "gemelos-db-engine"
        return (
            "El servicio de LLM externo no está configurado (falta GROQ_API_KEY). Por favor inicia sesión para consultar datos reales de la plataforma.",
            "gemelos-db-engine",
        )

    # Si GROQ_API_KEY está configurada, llamamos a Groq enriquecido con los datos reales y el historial
    try:
        client = Groq(api_key=settings.groq_api_key)

        user_info = f"Usuario autenticado: {user.email} | Rol: {user.rol} (ID: {user.id})" if user else "Usuario anónimo"
        system_content = f"{SYSTEM_BASE_PROMPT}\n\n[CONTEXTO DE AUTENTICACIÓN]\n{user_info}"
        if pre_retrieved_context:
            system_content += f"\n\n[DATOS REALES RECUPERADOS DE LA BASE DE DATOS POSTGRESQL]:\n{pre_retrieved_context}"

        groq_messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content}
        ]

        # Inyectar historial de conversación (últimos 6 turnos)
        if history:
            for item in history[-6:]:
                role = item.get("role")
                content = item.get("content")
                if role in ["user", "assistant"] and content:
                    groq_messages.append({"role": role, "content": content})

        # Mensaje actual del usuario
        groq_messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.3,
            messages=groq_messages,
        )
        reply = response.choices[0].message.content or ""
        return reply, settings.groq_model

    except Exception:
        # En caso de error de red, cuota o API key en Groq, recurrimos al motor local con datos reales
        if user is not None and db is not None:
            reply = generate_local_fallback_reply(message, user, db, structured_data)
            return reply, "gemelos-db-engine"
        raise
