from __future__ import annotations

import hashlib
import json
import math
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from shapely.geometry import box, shape

from app.config import get_settings
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
        self._items: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._items.get(key)
        if not entry:
            return None
        created_at, value = entry
        if time.time() - created_at > self.ttl_seconds:
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return value

    def set(self, key: str, value: dict[str, Any]) -> None:
        self._items[key] = (time.time(), value)
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)


settings = get_settings()
simulation_cache = TimedCache(settings.cache_ttl_seconds, settings.cache_max_items)


@dataclass
class SpatialContext:
    geometry: dict[str, Any]
    area_km2: float
    centroid_lon: float
    centroid_lat: float
    region_label: str


def parse_geometry(geometry: dict[str, Any] | None, bbox_values: list[float] | None) -> SpatialContext:
    if geometry:
        geom = shape(geometry)
        geometry_payload = geometry
    elif bbox_values:
        min_lon, min_lat, max_lon, max_lat = bbox_values
        geom = box(min_lon, min_lat, max_lon, max_lat)
        geometry_payload = {
            "type": "Polygon",
            "coordinates": [[[float(lon), float(lat)] for lon, lat in geom.exterior.coords]],
        }
    else:
        raise ValueError("Either geometry or bbox must be provided")

    min_lon, min_lat, max_lon, max_lat = geom.bounds
    mean_lat_rad = math.radians((min_lat + max_lat) / 2)
    width_km = max(0.1, abs(max_lon - min_lon) * 111.32 * math.cos(mean_lat_rad))
    height_km = max(0.1, abs(max_lat - min_lat) * 110.57)
    area_km2 = max(1.0, width_km * height_km)
    centroid = geom.centroid

    return SpatialContext(
        geometry=geometry_payload,
        area_km2=area_km2,
        centroid_lon=float(centroid.x),
        centroid_lat=float(centroid.y),
        region_label=f"{centroid.y:.2f},{centroid.x:.2f}",
    )


def build_cache_key(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def climate_adjustments(climate_scenario: str) -> dict[str, float]:
    return CLIMATE_SCENARIOS.get(climate_scenario, CLIMATE_SCENARIOS["current"])


def build_baseline_features(context: SpatialContext, pesticide_level: float, min_natural_area_pct: float, climate_scenario: str) -> dict[str, float]:
    climate = climate_adjustments(climate_scenario)
    area_pressure = min(1.0, context.area_km2 / 100.0)
    natural_area_pct = max(min_natural_area_pct, 14.0 + area_pressure * 7.5)
    floral_strips_pct = min(14.0, max(3.0, natural_area_pct * 0.28))
    crop_area_pct = max(35.0, 86.0 - natural_area_pct - floral_strips_pct)
    soil_management_score = 52.0 + area_pressure * 18.0
    landscape_diversity = min(0.92, 0.34 + natural_area_pct / 100.0 + floral_strips_pct / 120.0)

    return {
        "crop_area_pct": round(crop_area_pct, 2),
        "natural_area_pct": round(natural_area_pct, 2),
        "floral_strips_pct": round(floral_strips_pct, 2),
        "pesticide_level": round(pesticide_level, 2),
        "soil_management_score": round(soil_management_score, 2),
        "temperature_c": round(23.6 + climate["temperature_delta"] + context.centroid_lat * -0.015, 2),
        "precipitation_mm": round(1040.0 + climate["precipitation_delta"] - abs(context.centroid_lon) * 1.5, 2),
        "landscape_diversity": round(landscape_diversity, 3),
    }


def predict_targets(feature_rows: list[dict[str, float]]) -> np.ndarray:
    if not model_store.is_ready or model_store.model is None:
        raise RuntimeError(model_store.status_message)
    features = np.array([[row[column] for column in FEATURE_COLUMNS] for row in feature_rows], dtype=np.float32)
    predictions = model_store.model.predict(features, verbose=0)
    scale = np.array(model_store.metadata.get("target_scaler_scale", []), dtype=np.float32)
    mean = np.array(model_store.metadata.get("target_scaler_mean", []), dtype=np.float32)
    if len(scale) == predictions.shape[1] and len(mean) == predictions.shape[1]:
        predictions = predictions * scale + mean
    return predictions


class LandscapeOptimizationProblem(Problem):
    def __init__(self, context: SpatialContext, baseline_features: dict[str, float], min_natural_area_pct: float, climate_scenario: str):
        self.context = context
        self.baseline_features = baseline_features
        self.min_natural_area_pct = min_natural_area_pct
        self.climate = climate_adjustments(climate_scenario)
        super().__init__(n_var=5, n_obj=2, n_constr=2, xl=np.array([40, min_natural_area_pct, 3, 0, 45]), xu=np.array([85, 45, 20, 100, 95]))

    def _evaluate(self, X, out, *args, **kwargs):
        rows: list[dict[str, float]] = []
        for crop_area, natural_area, floral_strips, pesticide_level, soil_management in X:
            remaining = 100.0 - natural_area - floral_strips
            adjusted_crop_area = min(crop_area, remaining)
            diversity = min(0.96, 0.25 + natural_area / 100.0 + floral_strips / 90.0 + soil_management / 250.0)
            rows.append(
                {
                    "crop_area_pct": float(adjusted_crop_area),
                    "natural_area_pct": float(natural_area),
                    "floral_strips_pct": float(floral_strips),
                    "pesticide_level": float(pesticide_level),
                    "soil_management_score": float(soil_management),
                    "temperature_c": float(self.baseline_features["temperature_c"]),
                    "precipitation_mm": float(self.baseline_features["precipitation_mm"]),
                    "landscape_diversity": float(diversity),
                }
            )

        predictions = predict_targets(rows)
        crop_yield = predictions[:, 0]
        pollinator_abundance = predictions[:, 1]
        out["F"] = np.column_stack([-crop_yield, -pollinator_abundance])

        total_area_penalty = np.array([row["crop_area_pct"] + row["natural_area_pct"] + row["floral_strips_pct"] - 100.0 for row in rows])
        natural_area_penalty = np.array([self.min_natural_area_pct - row["natural_area_pct"] for row in rows])
        out["G"] = np.column_stack([total_area_penalty, natural_area_penalty])


def summarize_candidate(features: dict[str, float], predictions: np.ndarray) -> dict[str, float]:
    return {
        **{key: round(float(value), 3) for key, value in features.items()},
        "crop_yield_index": round(float(predictions[0]), 3),
        "pollinator_abundance_index": round(float(predictions[1]), 3),
        "pollinator_diversity_index": round(float(predictions[2]), 3),
    }


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
    cache_key = build_cache_key(payload)
    cached = simulation_cache.get(cache_key)
    if cached:
        return {**cached, "cache_hit": True}

    context = parse_geometry(payload.get("geometry"), payload.get("bbox"))
    baseline_features = build_baseline_features(
        context=context,
        pesticide_level=float(payload["pesticide_level"]),
        min_natural_area_pct=float(payload["min_natural_area_pct"]),
        climate_scenario=str(payload["climate_scenario"]),
    )
    baseline_prediction = predict_targets([baseline_features])[0]
    baseline = summarize_candidate(baseline_features, baseline_prediction)

    problem = LandscapeOptimizationProblem(
        context=context,
        baseline_features=baseline_features,
        min_natural_area_pct=float(payload["min_natural_area_pct"]),
        climate_scenario=str(payload["climate_scenario"]),
    )
    algorithm = NSGA2(pop_size=64)
    result = minimize(problem, algorithm, ("n_gen", 40), seed=42, verbose=False)

    candidate_features: list[dict[str, float]] = []
    for row in result.X:
        crop_area, natural_area, floral_strips, pesticide_level, soil_management = row
        adjusted_crop_area = min(float(crop_area), 100.0 - float(natural_area) - float(floral_strips))
        diversity = min(0.96, 0.25 + float(natural_area) / 100.0 + float(floral_strips) / 90.0 + float(soil_management) / 250.0)
        candidate_features.append(
            {
                "crop_area_pct": round(max(15.0, adjusted_crop_area), 3),
                "natural_area_pct": round(float(natural_area), 3),
                "floral_strips_pct": round(float(floral_strips), 3),
                "pesticide_level": round(float(pesticide_level), 3),
                "soil_management_score": round(float(soil_management), 3),
                "temperature_c": baseline_features["temperature_c"],
                "precipitation_mm": baseline_features["precipitation_mm"],
                "landscape_diversity": round(float(diversity), 3),
            }
        )

    predictions = predict_targets(candidate_features)
    pareto_front = [summarize_candidate(features, prediction) for features, prediction in zip(candidate_features, predictions, strict=False)]
    pareto_front.sort(key=lambda item: (item["pollinator_abundance_index"], item["crop_yield_index"]), reverse=True)

    def score(candidate: dict[str, float]) -> float:
        delta_yield = candidate["crop_yield_index"] - baseline["crop_yield_index"]
        delta_pollinators = ((candidate["pollinator_abundance_index"] - baseline["pollinator_abundance_index"]) / max(1.0, baseline["pollinator_abundance_index"])) * 100.0
        bonus = 120.0 if delta_yield >= 0 and delta_pollinators >= 20 else 0.0
        return bonus + delta_pollinators + delta_yield * 1.4 + candidate["pollinator_diversity_index"] * 0.1

    best_solution = max(pareto_front, key=score)
    delta_yield = round(best_solution["crop_yield_index"] - baseline["crop_yield_index"], 3)
    delta_pollinators = round(
        ((best_solution["pollinator_abundance_index"] - baseline["pollinator_abundance_index"]) / max(1.0, baseline["pollinator_abundance_index"])) * 100.0,
        3,
    )
    hypothesis_status = "Hipotesis comprobada" if delta_yield >= 0 and delta_pollinators >= 20 else "Hipotesis no comprobada"

    response = {
        "baseline": {
            **baseline,
            "geometry": context.geometry,
            "area_km2": round(context.area_km2, 2),
            "region_label": context.region_label,
        },
        "pareto_front": pareto_front[:20],
        "best_solution": {
            **best_solution,
            "selection_reason": "Best compromise maximizing pollinator gains while protecting yield.",
        },
        "optimized_landscape": build_optimized_landscape(best_solution, context),
        "delta_yield": delta_yield,
        "delta_pollinators": delta_pollinators,
        "hypothesis_status": hypothesis_status,
        "model_version": model_store.version,
        "cache_hit": False,
    }
    simulation_cache.set(cache_key, response)
    return response
