from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Simulacion, Usuario
from app.schemas_reports import (
    ManagementKpis,
    ManagementReportResponse,
    ManagementTemporalEvolutionPoint,
    OperationalReportResponse,
    OperationalSummary,
    ParetoConfigurationItem,
    RegionDistributionItem,
    RegionManagementItem,
    TemporalTrendPoint,
    UserRankingItem,
)


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
    return "Zona Agrícola"


def _format_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d")


def _format_datetime(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.isoformat()


def build_filtered_query(
    db: Session,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
    region: str | None = None,
    usuario_id: int | None = None,
):
    query = db.query(Simulacion)

    if usuario_id is not None:
        query = query.filter(Simulacion.usuario_id == usuario_id)
    if fecha_inicio is not None:
        query = query.filter(Simulacion.fecha >= fecha_inicio)
    if fecha_fin is not None:
        query = query.filter(Simulacion.fecha <= fecha_fin)

    if region and region.strip():
        search_region = region.strip().lower()
        # PostgreSQL JSON text access with fallback
        try:
            query = query.filter(
                Simulacion.metricas_base["region_label"].astext.ilike(f"%{search_region}%")
            )
        except Exception:
            pass

    return query


def get_operational_report(
    db: Session,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
    region: str | None = None,
    usuario_id: int | None = None,
    periodo: str = "dia",
) -> OperationalReportResponse:
    query = build_filtered_query(db, fecha_inicio, fecha_fin, region, usuario_id)
    simulations = query.order_by(Simulacion.fecha.asc()).all()

    # Manual region filter fallback if needed
    if region and region.strip():
        search_region = region.strip().lower()
        simulations = [s for s in simulations if search_region in _extract_region(s).lower()]

    total_simulaciones = len(simulations)

    # Active unique users in this scope
    active_user_ids = {s.usuario_id for s in simulations}
    usuarios_activos_count = len(active_user_ids)

    # Covered regions
    region_counts: dict[str, int] = defaultdict(int)
    for s in simulations:
        r = _extract_region(s)
        region_counts[r] += 1
    regiones_cubiertas_count = len(region_counts)

    # Check execution time
    times: list[float] = []
    for s in simulations:
        for payload in [s.metricas_optimas, s.variables_entrada]:
            if isinstance(payload, dict):
                for k in ["execution_time", "duracion_segundos", "optimization_time_sec", "duracion"]:
                    if k in payload and payload[k] is not None:
                        t = _safe_float(payload[k], -1)
                        if t >= 0:
                            times.append(t)
                            break

    tiempo_promedio_disponible = len(times) > 0
    tiempo_promedio = round(sum(times) / len(times), 2) if tiempo_promedio_disponible else None

    # Temporal trend
    period_buckets: dict[str, int] = defaultdict(int)
    for s in simulations:
        dt = s.fecha
        if periodo == "mes":
            key = dt.strftime("%Y-%m")
        elif periodo == "semana":
            key = dt.strftime("%Y-W%W")
        else:
            key = dt.strftime("%Y-%m-%d")
        period_buckets[key] += 1

    tendencia_temporal: list[TemporalTrendPoint] = []
    cumulative = 0
    for k in sorted(period_buckets.keys()):
        count = period_buckets[k]
        cumulative += count
        tendencia_temporal.append(
            TemporalTrendPoint(periodo=k, simulaciones=count, acumulado=cumulative)
        )

    # User ranking
    user_sim_counts: dict[int, int] = defaultdict(int)
    user_latest_sim: dict[int, datetime] = {}
    for s in simulations:
        uid = s.usuario_id
        user_sim_counts[uid] += 1
        if uid not in user_latest_sim or s.fecha > user_latest_sim[uid]:
            user_latest_sim[uid] = s.fecha

    users_map = {
        u.id: u for u in db.query(Usuario).filter(Usuario.id.in_(list(active_user_ids) or [-1])).all()
    }

    ranking_usuarios: list[UserRankingItem] = []
    sorted_user_ids = sorted(user_sim_counts.keys(), key=lambda uid: user_sim_counts[uid], reverse=True)
    for uid in sorted_user_ids[:15]:
        u = users_map.get(uid)
        ranking_usuarios.append(
            UserRankingItem(
                usuario_id=uid,
                email=u.email if u else f"usuario_{uid}@local",
                rol=u.rol if u else "cliente",
                total_simulaciones=user_sim_counts[uid],
                ultima_simulacion=_format_datetime(user_latest_sim.get(uid)),
            )
        )

    # Regions distribution
    distribucion_regiones: list[RegionDistributionItem] = []
    sorted_regions = sorted(region_counts.items(), key=lambda item: item[1], reverse=True)
    for reg_name, count in sorted_regions:
        pct = round((count / total_simulaciones * 100.0), 2) if total_simulaciones > 0 else 0.0
        distribucion_regiones.append(
            RegionDistributionItem(region=reg_name, total=count, porcentaje=pct)
        )

    return OperationalReportResponse(
        filtros={
            "fecha_inicio": _format_datetime(fecha_inicio) if fecha_inicio else None,
            "fecha_fin": _format_datetime(fecha_fin) if fecha_fin else None,
            "region": region,
            "usuario_id": usuario_id,
            "periodo": periodo,
        },
        resumen=OperationalSummary(
            total_simulaciones=total_simulaciones,
            usuarios_activos=usuarios_activos_count,
            regiones_cubiertas=regiones_cubiertas_count,
            tiempo_promedio_segundos=tiempo_promedio,
            tiempo_promedio_disponible=tiempo_promedio_disponible,
            tiempo_estimado_segundos=1.25,
        ),
        tendencia_temporal=tendencia_temporal,
        ranking_usuarios=ranking_usuarios,
        distribucion_regiones=distribucion_regiones,
    )


def get_management_report(
    db: Session,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
    region: str | None = None,
    usuario_id: int | None = None,
    top_n: int = 10,
) -> ManagementReportResponse:
    query = build_filtered_query(db, fecha_inicio, fecha_fin, region, usuario_id)
    simulations = query.order_by(Simulacion.fecha.asc()).all()

    if region and region.strip():
        search_region = region.strip().lower()
        simulations = [s for s in simulations if search_region in _extract_region(s).lower()]

    total_sims = len(simulations)

    # Listas de línea base total (identificadas separadamente para todas las simulaciones)
    yield_base_total_list: list[float] = []
    poll_base_total_list: list[float] = []
    div_base_total_list: list[float] = []

    # Listas pareadas evaluables (estrictamente simulaciones con solución óptima admisible)
    yield_base_eval_list: list[float] = []
    yield_opt_eval_list: list[float] = []
    poll_base_eval_list: list[float] = []
    poll_opt_eval_list: list[float] = []
    div_base_eval_list: list[float] = []
    div_opt_eval_list: list[float] = []

    cumplen_hipotesis = 0
    sims_evaluables = 0
    sims_no_evaluables = 0

    # Regional structures
    region_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total": 0,
            "evaluables": 0,
            "no_evaluables": 0,
            "yield_base_total": [],
            "poll_base_total": [],
            "div_base_total": [],
            "yield_base_eval": [],
            "yield_opt_eval": [],
            "poll_base_eval": [],
            "poll_opt_eval": [],
            "div_base_eval": [],
            "div_opt_eval": [],
            "cumplen": 0,
        }
    )

    # Temporal structures (grouped by day)
    temporal_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total": 0,
            "evaluables": 0,
            "no_evaluables": 0,
            "yb_total": [],
            "pb_total": [],
            "db_total": [],
            "yb_eval": [],
            "yo_eval": [],
            "pb_eval": [],
            "po_eval": [],
            "db_eval": [],
            "do_eval": [],
            "cumplen": 0,
        }
    )

    # Collect pareto front candidates
    pareto_candidates: list[dict[str, Any]] = []

    for s in simulations:
        reg = _extract_region(s)
        day_key = _format_date(s.fecha)

        yb = _extract_metric(s.metricas_base, "crop_yield_index", "rendimiento", default=70.0)
        pb = _extract_metric(s.metricas_base, "pollinator_abundance_index", "polinizadores", default=50.0)
        db_val = _extract_metric(s.metricas_base, "pollinator_diversity_index", "diversidad", default=0.55)

        yield_base_total_list.append(yb)
        poll_base_total_list.append(pb)
        div_base_total_list.append(db_val)

        has_opt = s.metricas_optimas is not None and isinstance(s.metricas_optimas, dict)

        rs = region_stats[reg]
        rs["total"] += 1
        rs["yield_base_total"].append(yb)
        rs["poll_base_total"].append(pb)
        rs["div_base_total"].append(db_val)

        ts = temporal_stats[day_key]
        ts["total"] += 1
        ts["yb_total"].append(yb)
        ts["pb_total"].append(pb)
        ts["db_total"].append(db_val)

        if has_opt:
            sims_evaluables += 1
            yo = _extract_metric(s.metricas_optimas, "crop_yield_index", "rendimiento", default=yb)
            po = _extract_metric(s.metricas_optimas, "pollinator_abundance_index", "polinizadores", default=pb)
            do_val = _extract_metric(s.metricas_optimas, "pollinator_diversity_index", "diversidad", default=0.75)

            yield_base_eval_list.append(yb)
            yield_opt_eval_list.append(yo)
            poll_base_eval_list.append(pb)
            poll_opt_eval_list.append(po)
            div_base_eval_list.append(db_val)
            div_opt_eval_list.append(do_val)

            # Criterio conjunto pareado sobre la misma observación: delta_yield >= 0 AND delta_pollinators >= 20%
            dy = yo - yb
            dp_pct = ((po - pb) / max(1.0, pb)) * 100.0
            meets = (dy >= 0.0) and (dp_pct >= 20.0)
            if meets:
                cumplen_hipotesis += 1

            rs["evaluables"] += 1
            rs["yield_base_eval"].append(yb)
            rs["yield_opt_eval"].append(yo)
            rs["poll_base_eval"].append(pb)
            rs["poll_opt_eval"].append(po)
            rs["div_base_eval"].append(db_val)
            rs["div_opt_eval"].append(do_val)
            if meets:
                rs["cumplen"] += 1

            ts["evaluables"] += 1
            ts["yb_eval"].append(yb)
            ts["yo_eval"].append(yo)
            ts["pb_eval"].append(pb)
            ts["po_eval"].append(po)
            ts["db_eval"].append(db_val)
            ts["do_eval"].append(do_val)
            if meets:
                ts["cumplen"] += 1
        else:
            sims_no_evaluables += 1
            rs["no_evaluables"] += 1
            ts["no_evaluables"] += 1

        # Extract Pareto front items
        if isinstance(s.frente_pareto, list) and has_opt:
            for candidate in s.frente_pareto:
                if isinstance(candidate, dict):
                    cyi = _extract_metric(candidate, "crop_yield_index", "rendimiento", default=yo)
                    pai = _extract_metric(candidate, "pollinator_abundance_index", "polinizadores", default=po)
                    pdi = _extract_metric(candidate, "pollinator_diversity_index", "diversidad", default=do_val)

                    # Landscape decision features
                    crop_pct = _extract_metric(candidate, "crop_area_pct", default=60.0)
                    nat_pct = _extract_metric(candidate, "natural_area_pct", default=25.0)
                    strips_pct = _extract_metric(candidate, "floral_strips_pct", default=10.0)
                    pest = _extract_metric(candidate, "pesticide_level", default=25.0)
                    soil = _extract_metric(candidate, "soil_management_score", default=70.0)

                    # Multi-objective composite score
                    score = round((pai * 0.45) + (cyi * 0.40) + (pdi * 100.0 * 0.15), 2)

                    pareto_candidates.append(
                        {
                            "simulacion_id": s.id,
                            "region": reg,
                            "fecha": _format_datetime(s.fecha),
                            "crop_yield_index": round(cyi, 3),
                            "pollinator_abundance_index": round(pai, 3),
                            "pollinator_diversity_index": round(pdi, 3),
                            "crop_area_pct": round(crop_pct, 2),
                            "natural_area_pct": round(nat_pct, 2),
                            "floral_strips_pct": round(strips_pct, 2),
                            "pesticide_level": round(pest, 2),
                            "soil_management_score": round(soil, 2),
                            "score": score,
                        }
                    )

    # Compute Global KPIs
    def _mean(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 3) if vals else None

    # Líneas base totales de toda la población (identificadas separadamente)
    yb_total_mean = _mean(yield_base_total_list)
    pb_total_mean = _mean(poll_base_total_list)
    db_total_mean = _mean(div_base_total_list)

    if sims_evaluables > 0:
        # Comparación pareada estricta sobre la misma población evaluable
        yb_eval_mean = _mean(yield_base_eval_list)
        yo_eval_mean = _mean(yield_opt_eval_list)
        dy_mean = round(yo_eval_mean - yb_eval_mean, 3) if yo_eval_mean is not None and yb_eval_mean is not None else None
        dy_pct = round(((yo_eval_mean - yb_eval_mean) / max(1.0, yb_eval_mean)) * 100.0, 2) if (yo_eval_mean is not None and yb_eval_mean is not None and yb_eval_mean > 0) else 0.0

        pb_eval_mean = _mean(poll_base_eval_list)
        po_eval_mean = _mean(poll_opt_eval_list)
        dp_mean = round(po_eval_mean - pb_eval_mean, 3) if po_eval_mean is not None and pb_eval_mean is not None else None
        dp_pct = round(((po_eval_mean - pb_eval_mean) / max(1.0, pb_eval_mean)) * 100.0, 2) if (po_eval_mean is not None and pb_eval_mean is not None and pb_eval_mean > 0) else 0.0

        db_eval_mean = _mean(div_base_eval_list)
        do_eval_mean = _mean(div_opt_eval_list)
        dd_mean = round(do_eval_mean - db_eval_mean, 3) if do_eval_mean is not None and db_eval_mean is not None else None

        tasa_hipotesis = round((cumplen_hipotesis / sims_evaluables * 100.0), 2)
        sims_no_cumplen = sims_evaluables - cumplen_hipotesis
    else:
        # Ausencia de comparaciones evaluables: no fabricar mejoras con ceros
        yb_eval_mean = None
        yo_eval_mean = None
        dy_mean = None
        dy_pct = None

        pb_eval_mean = None
        po_eval_mean = None
        dp_mean = None
        dp_pct = None

        db_eval_mean = None
        do_eval_mean = None
        dd_mean = None

        tasa_hipotesis = None
        sims_no_cumplen = 0

    kpis = ManagementKpis(
        total_simulaciones=total_sims,
        simulaciones_evaluables=sims_evaluables,
        simulaciones_no_evaluables=sims_no_evaluables,
        rendimiento_promedio_base=yb_eval_mean,
        rendimiento_promedio_optimo=yo_eval_mean,
        delta_rendimiento_promedio=dy_mean,
        delta_rendimiento_pct=dy_pct,
        abundancia_polinizadores_base=pb_eval_mean,
        abundancia_polinizadores_optima=po_eval_mean,
        delta_abundancia_promedio=dp_mean,
        delta_abundancia_pct=dp_pct,
        diversidad_polinizadores_base=db_eval_mean,
        diversidad_polinizadores_optima=do_eval_mean,
        delta_diversidad_promedio=dd_mean,
        tasa_cumplimiento_hipotesis=tasa_hipotesis,
        denominador_tasa="evaluables",
        simulaciones_cumplen_hipotesis=cumplen_hipotesis,
        simulaciones_no_cumplen=sims_no_cumplen,
        rendimiento_promedio_base_total=yb_total_mean,
        abundancia_polinizadores_base_total=pb_total_mean,
        diversidad_polinizadores_base_total=db_total_mean,
    )

    # Regional comparison table
    comparacion_regiones: list[RegionManagementItem] = []
    for reg_name, data in sorted(region_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        reg_total = data["total"]
        reg_eval = data["evaluables"]
        reg_no_eval = data["no_evaluables"]
        reg_cumplen = data["cumplen"]
        reg_no_cumplen = reg_eval - reg_cumplen if reg_eval > 0 else 0
        if reg_eval > 0:
            reg_yb = _mean(data["yield_base_eval"])
            reg_yo = _mean(data["yield_opt_eval"])
            reg_dy = round(reg_yo - reg_yb, 3) if reg_yo is not None and reg_yb is not None else None

            reg_pb = _mean(data["poll_base_eval"])
            reg_po = _mean(data["poll_opt_eval"])
            reg_dp = round(reg_po - reg_pb, 3) if reg_po is not None and reg_pb is not None else None

            reg_db = _mean(data["div_base_eval"])
            reg_do = _mean(data["div_opt_eval"])
            reg_dd = round(reg_do - reg_db, 3) if reg_do is not None and reg_db is not None else None

            reg_tasa = round((data["cumplen"] / reg_eval * 100.0), 2)
        else:
            reg_yb = None
            reg_yo = None
            reg_dy = None
            reg_pb = None
            reg_po = None
            reg_dp = None
            reg_db = None
            reg_do = None
            reg_dd = None
            reg_tasa = None

        comparacion_regiones.append(
            RegionManagementItem(
                region=reg_name,
                total_simulaciones=reg_total,
                simulaciones_evaluables=reg_eval,
                simulaciones_no_evaluables=reg_no_eval,
                simulaciones_cumplen_hipotesis=reg_cumplen,
                simulaciones_no_cumplen=reg_no_cumplen,
                rendimiento_promedio_base=reg_yb,
                rendimiento_promedio_optimo=reg_yo,
                delta_rendimiento_promedio=reg_dy,
                abundancia_promedio_base=reg_pb,
                abundancia_promedio_optimo=reg_po,
                delta_abundancia_promedio=reg_dp,
                diversidad_promedio_base=reg_db,
                diversidad_promedio_optimo=reg_do,
                delta_diversidad_promedio=reg_dd,
                tasa_cumplimiento_hipotesis=reg_tasa,
                denominador_tasa="evaluables",
                rendimiento_promedio_base_total=_mean(data["yield_base_total"]),
                abundancia_promedio_base_total=_mean(data["poll_base_total"]),
                diversidad_promedio_base_total=_mean(data["div_base_total"]),
            )
        )

    # Temporal Evolution
    evolucion_temporal: list[ManagementTemporalEvolutionPoint] = []
    for d in sorted(temporal_stats.keys()):
        d_data = temporal_stats[d]
        d_total = d_data["total"]
        d_eval = d_data["evaluables"]
        d_no_eval = d_data["no_evaluables"]
        d_cumplen = d_data["cumplen"]
        d_no_cumplen = d_eval - d_cumplen if d_eval > 0 else 0
        if d_eval > 0:
            d_yb = _mean(d_data["yb_eval"])
            d_yo = _mean(d_data["yo_eval"])
            d_dy = round(d_yo - d_yb, 3) if d_yo is not None and d_yb is not None else None

            d_pb = _mean(d_data["pb_eval"])
            d_po = _mean(d_data["po_eval"])
            d_dp = round(d_po - d_pb, 3) if d_po is not None and d_pb is not None else None

            d_db = _mean(d_data["db_eval"])
            d_do = _mean(d_data["do_eval"])
            d_dd = round(d_do - d_db, 3) if d_do is not None and d_db is not None else None
        else:
            d_yb = None
            d_yo = None
            d_dy = None
            d_pb = None
            d_po = None
            d_dp = None
            d_db = None
            d_do = None
            d_dd = None

        evolucion_temporal.append(
            ManagementTemporalEvolutionPoint(
                fecha=d,
                total_simulaciones=d_total,
                simulaciones_evaluables=d_eval,
                simulaciones_no_evaluables=d_no_eval,
                simulaciones_cumplen_hipotesis=d_cumplen,
                simulaciones_no_cumplen=d_no_cumplen,
                rendimiento_base=d_yb,
                rendimiento_optimo=d_yo,
                delta_rendimiento=d_dy,
                abundancia_base=d_pb,
                abundancia_optima=d_po,
                delta_abundancia=d_dp,
                diversidad_base=d_db,
                diversidad_optima=d_do,
                delta_diversidad=d_dd,
                rendimiento_base_total=_mean(d_data["yb_total"]),
                abundancia_base_total=_mean(d_data["pb_total"]),
                diversidad_base_total=_mean(d_data["db_total"]),
            )
        )

    # Top Pareto configurations
    pareto_candidates.sort(key=lambda x: x["score"], reverse=True)
    # De-duplicate by yield, poll, diversity
    seen_combos = set()
    unique_candidates: list[dict[str, Any]] = []
    for c in pareto_candidates:
        combo_key = (round(c["crop_yield_index"], 2), round(c["pollinator_abundance_index"], 2), c["region"])
        if combo_key not in seen_combos:
            seen_combos.add(combo_key)
            unique_candidates.append(c)
        if len(unique_candidates) >= top_n:
            break

    top_configuraciones_pareto = [
        ParetoConfigurationItem(rank=i + 1, **cand)
        for i, cand in enumerate(unique_candidates)
    ]

    return ManagementReportResponse(
        filtros={
            "fecha_inicio": _format_datetime(fecha_inicio) if fecha_inicio else None,
            "fecha_fin": _format_datetime(fecha_fin) if fecha_fin else None,
            "region": region,
            "usuario_id": usuario_id,
            "top_n": top_n,
        },
        kpis_agroecologicos=kpis,
        evolucion_temporal=evolucion_temporal,
        comparacion_regiones=comparacion_regiones,
        top_configuraciones_pareto=top_configuraciones_pareto,
    )
