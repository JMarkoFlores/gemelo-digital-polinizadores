from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
from typing import Any
import numpy as np

try:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import Problem
    from pymoo.optimize import minimize
except ImportError:
    # Minimal stub if pymoo is not installed locally
    Problem = object
    NSGA2 = None
    minimize = None

try:
    from shapely.geometry import box, shape
except ImportError:
    box = None
    shape = None

try:
    from app.config import get_settings
except ImportError:
    class MinimalSettings:
        cache_ttl_seconds = 3600
        cache_max_items = 500
    def get_settings():
        return MinimalSettings()
from app.services.model_store import model_store

FEATURE_COLUMNS = [
    "crop_area_pct",
    "natural_area_pct",
    "floral_strips_pct",
    "pesticide_level",
    "soil_management_score",
    "temperature_c",
    "precipitation_mm",
    "landscape_diversity",
]

CLIMATE_SCENARIOS = {
    "current": {"temperature_delta": 0.0, "precipitation_delta": 0.0},
    "warm": {"temperature_delta": 1.8, "precipitation_delta": -40.0},
    "dry": {"temperature_delta": 0.9, "precipitation_delta": -140.0},
    "extreme": {"temperature_delta": 2.6, "precipitation_delta": -220.0},
}


class TimedCache:
    def __init__(self, ttl_seconds: int, max_items: int) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        import time
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: dict[str, Any]) -> None:
        import time
        if len(self._store) >= self.max_items:
            oldest_key = next(iter(self._store))
            self._store.pop(oldest_key, None)
        self._store[key] = (time.time() + self.ttl_seconds, value)

    def clear(self) -> None:
        self._store.clear()


settings = get_settings()
simulation_cache = TimedCache(ttl_seconds=settings.cache_ttl_seconds, max_items=settings.cache_max_items)


@dataclass
class SpatialContext:
    area_km2: float
    centroid_lat: float
    centroid_lon: float
    geometry: dict[str, Any]
    region_label: str


def parse_geometry(geometry: dict[str, Any] | None, bbox_values: list[float] | None) -> SpatialContext:
    if geometry and shape is not None:
        geom_obj = shape(geometry)
        centroid = geom_obj.centroid
        approx_area_km2 = max(0.5, float(geom_obj.area * 111.0 * 111.0))
        return SpatialContext(
            area_km2=approx_area_km2,
            centroid_lat=float(centroid.y),
            centroid_lon=float(centroid.x),
            geometry=geometry,
            region_label="Área Personalizada Poligonal",
        )

    if bbox_values and len(bbox_values) == 4 and box is not None:
        min_lat, min_lon, max_lat, max_lon = [float(v) for v in bbox_values]
        geom_obj = box(min_lon, min_lat, max_lon, max_lat)
        centroid = geom_obj.centroid
        area_km2 = max(0.5, float(geom_obj.area * 111.0 * 111.0))
        return SpatialContext(
            area_km2=area_km2,
            centroid_lat=float(centroid.y),
            centroid_lon=float(centroid.x),
            geometry={
                "type": "Polygon",
                "coordinates": [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat],
                ]],
            },
            region_label="Cuadrícula BoundingBox",
        )

    # Fallback predeterminado a Valle del Cauca
    return SpatialContext(
        area_km2=12.5,
        centroid_lat=3.52,
        centroid_lon=-76.30,
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-76.32, 3.50],
                [-76.28, 3.50],
                [-76.28, 3.54],
                [-76.32, 3.54],
                [-76.32, 3.50],
            ]],
        },
        region_label="Valle del Cauca (Predeterminado)",
    )


def build_cache_key(payload: dict[str, Any], model_version: str | None = None, bundle_id: str | None = None) -> str:
    """Clave canónica de caché dependiente del payload, bundle_id, versión y tipo de modelo (Mandato 10)."""
    active_bundle_id = (
        bundle_id
        or getattr(model_store, "bundle_id", None)
        or model_store.metadata.get("bundle_id")
        or "none"
    )
    cache_payload = {
        "payload": payload,
        "bundle_id": str(active_bundle_id),
        "model_version": str(model_version or model_store.version or "none"),
        "model_type": str(model_store.model_type),
    }
    return hashlib.sha256(json.dumps(cache_payload, sort_keys=True).encode("utf-8")).hexdigest()


def climate_adjustments(climate_scenario: str) -> dict[str, float]:
    if climate_scenario not in CLIMATE_SCENARIOS:
        raise ValueError(
            f"Escenario climático desconocido: '{climate_scenario}'. "
            f"Escenarios válidos documentados: {list(CLIMATE_SCENARIOS.keys())}"
        )
    return CLIMATE_SCENARIOS[climate_scenario]


def calculate_landscape_diversity(natural_area_pct: float, floral_strips_pct: float, soil_management_score: float) -> float:
    diversity = 0.25 + (natural_area_pct / 100.0) + (floral_strips_pct / 90.0) + (soil_management_score / 250.0)
    return float(min(0.96, max(0.10, diversity)))


def build_baseline_features(context: SpatialContext, pesticide_level: float, min_natural_area_pct: float, climate_scenario: str) -> dict[str, float]:
    adjustments = climate_adjustments(climate_scenario)
    natural_area = max(float(min_natural_area_pct), 12.0)
    floral_strips = 4.0
    crop_area = max(20.0, 100.0 - natural_area - floral_strips)
    soil_management = 55.0
    diversity = calculate_landscape_diversity(natural_area, floral_strips, soil_management)

    base_temp = 23.5 if not model_store.metadata.get("clima_resumen") else float(model_store.metadata["clima_resumen"]["temperature_mean"])
    base_precip = 1100.0 if not model_store.metadata.get("clima_resumen") else float(model_store.metadata["clima_resumen"]["precipitation_annual_mean"])

    return {
        "crop_area_pct": float(crop_area),
        "natural_area_pct": float(natural_area),
        "floral_strips_pct": float(floral_strips),
        "pesticide_level": float(pesticide_level),
        "soil_management_score": float(soil_management),
        "temperature_c": float(base_temp + adjustments["temperature_delta"]),
        "precipitation_mm": float(max(100.0, base_precip + adjustments["precipitation_delta"])),
        "landscape_diversity": float(diversity),
    }


def predict_targets(feature_rows: list[dict[str, float]]) -> np.ndarray:
    matrix = np.array([[row[col] for col in FEATURE_COLUMNS] for row in feature_rows], dtype=np.float32)
    return model_store.predict(matrix)


class LandscapeOptimizationProblem(Problem):
    def __init__(self, context: SpatialContext, baseline_features: dict[str, float], min_natural_area_pct: float, climate_scenario: str):
        self.context = context
        self.baseline_features = baseline_features
        self.min_natural_area_pct = min_natural_area_pct
        self.climate_scenario = climate_scenario

        decision_vars = [
            "crop_area_pct",
            "natural_area_pct",
            "floral_strips_pct",
            "pesticide_level",
            "soil_management_score",
        ]
        base_physical_bounds = {
            "crop_area_pct": (15.0, 85.0),
            "natural_area_pct": (max(1.0, float(min_natural_area_pct)), 50.0),
            "floral_strips_pct": (1.0, 20.0),
            "pesticide_level": (0.0, 80.0),
            "soil_management_score": (30.0, 95.0),
        }

        observed_ranges = (
            model_store.metadata.get("observed_training_ranges")
            or model_store.metadata.get("observed_ranges")
            or {}
        )

        xl_vals = []
        xu_vals = []
        for v in decision_vars:
            p_min, p_max = base_physical_bounds[v]
            if v in observed_ranges:
                obs_min, obs_max = float(observed_ranges[v][0]), float(observed_ranges[v][1])
                inter_min = max(p_min, obs_min)
                inter_max = min(p_max, obs_max)
                if inter_min > inter_max:
                    raise ValueError(
                        f"Conflicto entre restricciones físicas y dominio aprendido para '{v}': "
                        f"rango físico [{p_min}, {p_max}] no se intersecta con el rango "
                        f"observado en entrenamiento [{obs_min}, {obs_max}]."
                    )
                xl_vals.append(inter_min)
                xu_vals.append(inter_max)
            else:
                xl_vals.append(p_min)
                xu_vals.append(p_max)

        super().__init__(
            n_var=5,
            n_obj=2,
            n_constr=2,
            xl=np.array(xl_vals, dtype=np.float32),
            xu=np.array(xu_vals, dtype=np.float32),
        )
        self.evaluations_count = 0

    def _evaluate(self, X, out, *args, **kwargs):
        self.evaluations_count += len(X)
        rows: list[dict[str, float]] = []
        is_valid_list: list[bool] = []
        for individual in X:
            crop_area, natural_area, floral_strips, pesticide_level, soil_management = individual
            diversity = calculate_landscape_diversity(float(natural_area), float(floral_strips), float(soil_management))
            row = {
                "crop_area_pct": float(crop_area),
                "natural_area_pct": float(natural_area),
                "floral_strips_pct": float(floral_strips),
                "pesticide_level": float(pesticide_level),
                "soil_management_score": float(soil_management),
                "temperature_c": float(self.baseline_features["temperature_c"]),
                "precipitation_mm": float(self.baseline_features["precipitation_mm"]),
                "landscape_diversity": float(diversity),
            }
            chk = model_store.check_domain(row)
            is_valid_list.append(chk["is_valid"])
            rows.append(row)

        f1_list = np.zeros(len(rows), dtype=np.float32)
        f2_list = np.zeros(len(rows), dtype=np.float32)

        valid_indices = [i for i, v in enumerate(is_valid_list) if v]
        if valid_indices:
            valid_rows = [rows[i] for i in valid_indices]
            preds = predict_targets(valid_rows)
            for idx, r_idx in enumerate(valid_indices):
                f1_list[r_idx] = -preds[idx, 0]
                f2_list[r_idx] = -preds[idx, 1]

        # Penalización severa para individuos que caigan fuera del dominio aprendido (Bloque 9)
        for i, v in enumerate(is_valid_list):
            if not v:
                f1_list[i] = 1e5
                f2_list[i] = 1e5

        out["F"] = np.column_stack([f1_list, f2_list])

        total_area_penalty = np.array([
            (row["crop_area_pct"] + row["natural_area_pct"] + row["floral_strips_pct"] - 100.0)
            + (1e3 if not is_valid_list[i] else 0.0)
            for i, row in enumerate(rows)
        ])
        natural_area_penalty = np.array([
            (self.min_natural_area_pct - row["natural_area_pct"])
            + (1e3 if not is_valid_list[i] else 0.0)
            for i, row in enumerate(rows)
        ])
        out["G"] = np.column_stack([total_area_penalty, natural_area_penalty])


def summarize_candidate(features: dict[str, float], predictions: np.ndarray) -> dict[str, float]:
    """Conserva precisión flotante completa para optimización e inferencia (Mandato 9)."""
    return {
        **{key: float(value) for key, value in features.items()},
        "crop_yield_index": float(predictions[0]),
        "pollinator_abundance_index": float(predictions[1]),
        "pollinator_diversity_index": float(predictions[2]),
    }


def filter_verified_pareto_front(
    candidates: list[dict[str, float]],
    decision_atol: float = 1e-5,
    objective_tol: float = 1e-7,
) -> list[dict[str, float]]:
    """
    Filtra rigurosamente dominancia de Pareto a precisión completa.
    Deduplica soluciones idénticas en espacio de decisión usando tolerancia explícita (decision_atol),
    sin descartar soluciones distintas por redondeos prematuros (Mandato 9).
    """
    if not candidates:
        return []

    # Eliminar duplicados exactos usando tolerancia continua
    unique_candidates: list[dict[str, float]] = []
    decision_keys = ["crop_area_pct", "natural_area_pct", "floral_strips_pct", "pesticide_level", "soil_management_score"]

    for c in candidates:
        is_dup = False
        for u in unique_candidates:
            if all(abs(c[k] - u[k]) <= decision_atol for k in decision_keys):
                is_dup = True
                break
        if not is_dup:
            unique_candidates.append(c)

    verified = []
    for i, a in enumerate(unique_candidates):
        is_dominated = False
        y_a = a["crop_yield_index"]
        p_a = a["pollinator_abundance_index"]
        for j, b in enumerate(unique_candidates):
            if i == j:
                continue
            y_b = b["crop_yield_index"]
            p_b = b["pollinator_abundance_index"]
            # b domina a a si: b >= a en ambos y b > a en al menos uno con tolerancia
            if (y_b >= y_a - objective_tol and p_b >= p_a - objective_tol) and (y_b > y_a + objective_tol or p_b > p_a + objective_tol):
                is_dominated = True
                break
        if not is_dominated:
            verified.append(a)

    verified.sort(key=lambda item: (item["pollinator_abundance_index"], item["crop_yield_index"]), reverse=True)
    return verified


def build_optimized_landscape(candidate: dict[str, float], context: SpatialContext) -> dict[str, Any]:
    return {
        "representation": "aggregated_landscape_profile",
        "region_label": context.region_label,
        "area_km2": round(context.area_km2, 2),
        "land_use_mix": {
            "crop_area_pct": candidate["crop_area_pct"],
            "natural_area_pct": candidate["natural_area_pct"],
            "floral_strips_pct": candidate["floral_strips_pct"],
        },
        "management": {
            "pesticide_level": candidate["pesticide_level"],
            "soil_management_score": candidate["soil_management_score"],
            "landscape_diversity": candidate["landscape_diversity"],
        },
    }


def run_simulation(payload: dict[str, Any]) -> dict[str, Any]:
    # Clave de caché dependiente de modelo, bundle_id y versión (Mandato 10)
    cache_key = build_cache_key(payload, model_version=model_store.version)
    cached = simulation_cache.get(cache_key)
    if cached:
        return {**cached, "cache_hit": True}

    context = parse_geometry(payload.get("geometry"), payload.get("bbox"))

    # Control de validez geográfica
    region_check = model_store.check_point_in_region(context.centroid_lat, context.centroid_lon)
    if not region_check["is_valid"]:
        raise ValueError(region_check["message"])

    # Validar escenario climático explícito
    climate_scen = str(payload.get("climate_scenario", "current"))
    climate_adjustments(climate_scen)

    baseline_features = build_baseline_features(
        context=context,
        pesticide_level=float(payload["pesticide_level"]),
        min_natural_area_pct=float(payload["min_natural_area_pct"]),
        climate_scenario=climate_scen,
    )

    # Validar dominio de la línea base contra límites físicos y rangos de entrenamiento
    domain_check = model_store.check_domain(baseline_features)
    if not domain_check["is_valid"]:
        raise ValueError(f"Línea base fuera de dominio: {domain_check['violations']}")

    baseline_prediction = predict_targets([baseline_features])[0]
    baseline = summarize_candidate(baseline_features, baseline_prediction)

    # Optimización NSGA-II o simulación controlada según pymoo disponible (Mandato 7)
    candidate_features: list[dict[str, float]] = []
    test_mode = bool(payload.get("test_mode", False))

    if NSGA2 is not None and minimize is not None:
        problem = LandscapeOptimizationProblem(
            context=context,
            baseline_features=baseline_features,
            min_natural_area_pct=float(payload["min_natural_area_pct"]),
            climate_scenario=climate_scen,
        )
        algorithm = NSGA2(pop_size=64)
        result = minimize(problem, algorithm, ("n_gen", 40), seed=42, verbose=False)

        if result.X is not None:
            for row in result.X:
                crop_area, natural_area, floral_strips, pesticide_level, soil_management = row
                adjusted_crop_area = min(float(crop_area), 100.0 - float(natural_area) - float(floral_strips))
                diversity = calculate_landscape_diversity(float(natural_area), float(floral_strips), float(soil_management))
                candidate_features.append({
                    "crop_area_pct": float(max(15.0, adjusted_crop_area)),
                    "natural_area_pct": float(natural_area),
                    "floral_strips_pct": float(floral_strips),
                    "pesticide_level": float(pesticide_level),
                    "soil_management_score": float(soil_management),
                    "temperature_c": float(baseline_features["temperature_c"]),
                    "precipitation_mm": float(baseline_features["precipitation_mm"]),
                    "landscape_diversity": float(diversity),
                })
        algorithm_evaluations_total = int(getattr(result, "n_evals", getattr(problem, "evaluations_count", len(candidate_features))))
        pareto_solutions_returned = len(candidate_features)
    else:
        if not test_mode:
            raise RuntimeError(
                "La optimización multiobjetivo científica requiere la biblioteca 'pymoo' con el algoritmo NSGA-II. "
                "En ejecución científica no se admiten fallbacks heurísticos silenciosos. "
                "Ejecute dentro del contenedor Docker oficial con pymoo instalado o pase explícitamente test_mode=True si realiza pruebas desacopladas."
            )
        # Fallback exclusivo para pruebas desacopladas de integración sin dependencias locales
        rng = np.random.default_rng(42)
        for _ in range(16):
            nat = rng.uniform(float(payload["min_natural_area_pct"]), 35.0)
            flor = rng.uniform(3.0, 15.0)
            rem = max(10.0, 100.0 - nat - flor)
            crop = rem * rng.uniform(0.6, 0.95)
            pest = rng.uniform(5.0, 60.0)
            soil = rng.uniform(50.0, 95.0)
            div = calculate_landscape_diversity(nat, flor, soil)
            candidate_features.append({
                "crop_area_pct": float(crop),
                "natural_area_pct": float(nat),
                "floral_strips_pct": float(flor),
                "pesticide_level": float(pest),
                "soil_management_score": float(soil),
                "temperature_c": float(baseline_features["temperature_c"]),
                "precipitation_mm": float(baseline_features["precipitation_mm"]),
                "landscape_diversity": float(div),
            })
        algorithm_evaluations_total = len(candidate_features)
        pareto_solutions_returned = len(candidate_features)

    # Predicción a precisión completa
    raw_predictions = predict_targets(candidate_features)
    raw_candidates = [
        summarize_candidate(features, pred)
        for features, pred in zip(candidate_features, raw_predictions)
    ]

    # Filtrar candidatos admisibles según dominio aprendido y restricciones biofísicas
    admissible_candidates = []
    for c in raw_candidates:
        d_chk = model_store.check_domain(c)
        if d_chk["is_valid"]:
            admissible_candidates.append(c)

    # Filtrar frente de Pareto estrictamente no dominado (Mandato 9)
    pareto_front = filter_verified_pareto_front(admissible_candidates)

    if not pareto_front:
        # Mandato 9: Si no existe solución admisible, devolver ese estado de forma explícita
        return {
            "status": "infeasible",
            "message": "No se encontraron soluciones admisibles que cumplan las restricciones biofísicas y el dominio del modelo.",
            "baseline": {
                **baseline,
                "geometry": context.geometry,
                "area_km2": round(context.area_km2, 2),
                "region_label": context.region_label,
                "center": [context.centroid_lat, context.centroid_lon],
            },
            "pareto_front": [],
            "algorithm_evaluations_total": algorithm_evaluations_total,
            "pareto_solutions_returned": pareto_solutions_returned,
            "pareto_candidates_evaluated": algorithm_evaluations_total,
            "pareto_verified_count": 0,
            "best_solution": None,
            "optimized_landscape": None,
            "delta_yield": None,
            "delta_pollinators": None,
            "hypothesis_status": "No evaluable: sin soluciones admisibles dentro del dominio",
            "meets_joint_criteria": None,
            "model_version": model_store.version,
            "bundle_id": model_store.bundle_id,
            "cache_hit": False,
            "recomendacion_ia": None,
        }

    # Regla operativa de puntuación multi-criterio
    def score(candidate: dict[str, float]) -> float:
        delta_y = candidate["crop_yield_index"] - baseline["crop_yield_index"]
        base_abund = max(1.0, baseline["pollinator_abundance_index"])
        delta_p_pct = ((candidate["pollinator_abundance_index"] - baseline["pollinator_abundance_index"]) / base_abund) * 100.0
        bonus = 120.0 if delta_y >= 0 and delta_p_pct >= 20.0 else 0.0
        return bonus + delta_p_pct + delta_y * 1.4 + candidate["pollinator_diversity_index"] * 0.1

    best_solution = max(pareto_front, key=score)

    # Cálculo a precisión completa ANTES de cualquier redondeo de presentación (Auditoría 05, Hallazgo 3)
    raw_delta_yield = float(best_solution["crop_yield_index"]) - float(baseline["crop_yield_index"])
    base_abund = max(1.0, float(baseline["pollinator_abundance_index"]))
    raw_delta_pollinators = (
        (float(best_solution["pollinator_abundance_index"]) - float(baseline["pollinator_abundance_index"]))
        / base_abund
    ) * 100.0

    # Evaluación rigurosa sin distorsión por redondeo
    meets_joint_criteria = bool(raw_delta_yield >= 0.0 and raw_delta_pollinators >= 20.0)

    hypothesis_status = (
        "Criterio operativo de mejora conjunta cumplido (+20% abundancia simulada con rendimiento no degradado)"
        if meets_joint_criteria
        else "Criterio operativo de mejora conjunta no alcanzado"
    )

    # Redondeo exclusivo para presentación y serialización
    delta_yield = round(raw_delta_yield, 3)
    delta_pollinators = round(raw_delta_pollinators, 3)

    response = {
        "status": "success",
        "message": None,
        "baseline": {
            **baseline,
            "geometry": context.geometry,
            "area_km2": round(context.area_km2, 2),
            "region_label": context.region_label,
            "center": [context.centroid_lat, context.centroid_lon],
        },
        "pareto_front": pareto_front,
        "algorithm_evaluations_total": algorithm_evaluations_total,
        "pareto_solutions_returned": pareto_solutions_returned,
        "pareto_candidates_evaluated": algorithm_evaluations_total,
        "pareto_verified_count": len(pareto_front),
        "best_solution": {
            **best_solution,
            "selection_reason": "Configuración óptima según el criterio operativo multi-criterio predefinido.",
        },
        "optimized_landscape": build_optimized_landscape(best_solution, context),
        "delta_yield": delta_yield,
        "delta_pollinators": delta_pollinators,
        "hypothesis_status": hypothesis_status,
        "meets_joint_criteria": meets_joint_criteria,
        "model_version": model_store.version,
        "bundle_id": model_store.bundle_id,
        "cache_hit": False,
    }
    simulation_cache.set(cache_key, response)
    return response
