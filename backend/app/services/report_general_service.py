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

    yield_base_list: list[float] = []
    yield_opt_list: list[float] = []
    poll_base_list: list[float] = []
    poll_opt_list: list[float] = []
    div_base_list: list[float] = []
    div_opt_list: list[float] = []

    cumplen_hipotesis = 0

    # Regional structures
    region_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total": 0,
            "yield_base": [],
            "yield_opt": [],
            "poll_base": [],
            "poll_opt": [],
            "div_base": [],
            "div_opt": [],
            "cumplen": 0,
        }
    )

    # Temporal structures (grouped by day)
    temporal_stats: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {
            "yb": [],
            "yo": [],
            "pb": [],
            "po": [],
            "db": [],
            "do": [],
        }
    )

    # Collect pareto front candidates
    pareto_candidates: list[dict[str, Any]] = []

    for s in simulations:
        reg = _extract_region(s)
        day_key = _format_date(s.fecha)

        yb = _extract_metric(s.metricas_base, "crop_yield_index", "rendimiento", default=70.0)
        yo = _extract_metric(s.metricas_optimas, "crop_yield_index", "rendimiento", default=yb)

        pb = _extract_metric(s.metricas_base, "pollinator_abundance_index", "polinizadores", default=50.0)
        po = _extract_metric(s.metricas_optimas, "pollinator_abundance_index", "polinizadores", default=pb)

        db_val = _extract_metric(s.metricas_base, "pollinator_diversity_index", "diversidad", default=0.55)
        do_val = _extract_metric(s.metricas_optimas, "pollinator_diversity_index", "diversidad", default=0.75)

        yield_base_list.append(yb)
        yield_opt_list.append(yo)
        poll_base_list.append(pb)
        poll_opt_list.append(po)
        div_base_list.append(db_val)
        div_opt_list.append(do_val)

        # Hypothesis test: delta_yield >= 0 AND delta_pollinators >= 20%
        dy = yo - yb
        dp_pct = ((po - pb) / max(1.0, pb)) * 100.0
        meets = (dy >= 0.0) and (dp_pct >= 20.0)
        if meets:
            cumplen_hipotesis += 1

        # Region stats
        rs = region_stats[reg]
        rs["total"] += 1
        rs["yield_base"].append(yb)
        rs["yield_opt"].append(yo)
        rs["poll_base"].append(pb)
        rs["poll_opt"].append(po)
        rs["div_base"].append(db_val)
        rs["div_opt"].append(do_val)
        if meets:
            rs["cumplen"] += 1

        # Temporal stats
        ts = temporal_stats[day_key]
        ts["yb"].append(yb)
        ts["yo"].append(yo)
        ts["pb"].append(pb)
        ts["po"].append(po)
        ts["db"].append(db_val)
        ts["do"].append(do_val)

        # Extract Pareto front items
        if isinstance(s.frente_pareto, list):
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
    def _mean(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    yb_mean = _mean(yield_base_list)
    yo_mean = _mean(yield_opt_list)
    dy_mean = round(yo_mean - yb_mean, 3)
    dy_pct = round(((yo_mean - yb_mean) / max(1.0, yb_mean)) * 100.0, 2) if yb_mean > 0 else 0.0

    pb_mean = _mean(poll_base_list)
    po_mean = _mean(poll_opt_list)
    dp_mean = round(po_mean - pb_mean, 3)
    dp_pct = round(((po_mean - pb_mean) / max(1.0, pb_mean)) * 100.0, 2) if pb_mean > 0 else 0.0

    db_mean = _mean(div_base_list)
    do_mean = _mean(div_opt_list)
    dd_mean = round(do_mean - db_mean, 3)

    tasa_hipotesis = round((cumplen_hipotesis / total_sims * 100.0), 2) if total_sims > 0 else 0.0

    kpis = ManagementKpis(
        total_simulaciones=total_sims,
        rendimiento_promedio_base=yb_mean,
        rendimiento_promedio_optimo=yo_mean,
        delta_rendimiento_promedio=dy_mean,
        delta_rendimiento_pct=dy_pct,
        abundancia_polinizadores_base=pb_mean,
        abundancia_polinizadores_optima=po_mean,
        delta_abundancia_promedio=dp_mean,
        delta_abundancia_pct=dp_pct,
        diversidad_polinizadores_base=db_mean,
        diversidad_polinizadores_optima=do_mean,
        delta_diversidad_promedio=dd_mean,
        tasa_cumplimiento_hipotesis=tasa_hipotesis,
        simulaciones_cumplen_hipotesis=cumplen_hipotesis,
        simulaciones_no_cumplen=total_sims - cumplen_hipotesis,
    )

    # Regional comparison table
    comparacion_regiones: list[RegionManagementItem] = []
    for reg_name, data in sorted(region_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        reg_total = data["total"]
        reg_tasa = round((data["cumplen"] / reg_total * 100.0), 2) if reg_total > 0 else 0.0
        comparacion_regiones.append(
            RegionManagementItem(
                region=reg_name,
                total_simulaciones=reg_total,
                rendimiento_promedio_base=_mean(data["yield_base"]),
                rendimiento_promedio_optimo=_mean(data["yield_opt"]),
                abundancia_promedio_base=_mean(data["poll_base"]),
                abundancia_promedio_optimo=_mean(data["poll_opt"]),
                diversidad_promedio_base=_mean(data["div_base"]),
                diversidad_promedio_optimo=_mean(data["div_opt"]),
                tasa_cumplimiento_hipotesis=reg_tasa,
            )
        )

    # Temporal Evolution
    evolucion_temporal: list[ManagementTemporalEvolutionPoint] = []
    for d in sorted(temporal_stats.keys()):
        d_data = temporal_stats[d]
        d_yb = _mean(d_data["yb"])
        d_yo = _mean(d_data["yo"])
        d_pb = _mean(d_data["pb"])
        d_po = _mean(d_data["po"])
        d_db = _mean(d_data["db"])
        d_do = _mean(d_data["do"])

        evolucion_temporal.append(
            ManagementTemporalEvolutionPoint(
                fecha=d,
                rendimiento_base=d_yb,
                rendimiento_optimo=d_yo,
                delta_rendimiento=round(d_yo - d_yb, 3),
                abundancia_base=d_pb,
                abundancia_optima=d_po,
                delta_abundancia=round(d_po - d_pb, 3),
                diversidad_base=d_db,
                diversidad_optima=d_do,
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
