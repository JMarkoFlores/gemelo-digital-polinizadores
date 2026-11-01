"""
scientific_core/contracts.py
Contratos científicos, nombres de columnas, rangos biofísicos y reglas de consistencia de paisaje.
Garantiza:
  1. Separación estricta entre límites biofísicos/operativos y rangos observados en entrenamiento.
  2. Validación física de balance de coberturas (suma <= 100%).
  3. Advertencia explícita sobre las limitaciones del cumplimiento univariado frente al soporte conjunto.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Contrato semántico de variables de entrada (8 características en orden estricto)
FEATURE_COLUMNS: List[str] = [
    "crop_area_pct",
    "natural_area_pct",
    "floral_strips_pct",
    "pesticide_level",
    "soil_management_score",
    "temperature_c",
    "precipitation_mm",
    "landscape_diversity",
]

# Contrato semántico de variables de salida (3 índices en orden estricto)
TARGET_COLUMNS: List[str] = [
    "crop_yield_index",
    "pollinator_abundance_index",
    "pollinator_diversity_index",
]

# Límites biofísicos y operativos generales (Hard limits físicos)
PHYSICAL_BOUNDS: Dict[str, Tuple[float, float]] = {
    "crop_area_pct": (0.0, 100.0),
    "natural_area_pct": (0.0, 100.0),
    "floral_strips_pct": (0.0, 100.0),
    "pesticide_level": (0.0, 100.0),
    "soil_management_score": (0.0, 100.0),
    "temperature_c": (5.0, 45.0),
    "precipitation_mm": (0.0, 5000.0),
    "landscape_diversity": (0.0, 1.0),
}

# Alias de compatibilidad hacia atrás
FEATURE_BOUNDS = PHYSICAL_BOUNDS

TARGET_BOUNDS: Dict[str, Tuple[float, float]] = {
    "crop_yield_index": (0.0, 200.0),
    "pollinator_abundance_index": (0.0, 200.0),
    "pollinator_diversity_index": (0.0, 100.0),
}

JOINT_SUPPORT_WARNING = (
    "Aviso metodológico: El cumplimiento univariado de los rangos individuales de entrenamiento "
    "no demuestra la pertenencia al soporte conjunto multidimensional ni la ausencia de extrapolación fuera de distribución."
)


def calculate_landscape_diversity(
    natural_area_pct: float,
    floral_strips_pct: float,
    soil_management_score: float,
) -> float:
    """
    Función biofísica unificada para landscape_diversity.
    Consistente entre dataset generado, línea base, optimización y ABM.
    """
    diversity = 0.25 + (natural_area_pct / 100.0) + (floral_strips_pct / 90.0) + (soil_management_score / 250.0)
    return float(min(0.96, max(0.10, diversity)))


def validate_coverage(
    crop_area_pct: float,
    natural_area_pct: float,
    floral_strips_pct: float,
    tolerance: float = 1e-4,
) -> Tuple[bool, float, float, str]:
    """
    Valida la física de exclusión de coberturas en el paisaje:
      - Todas las coberturas deben ser >= 0.
      - La suma total (cultivo + natural + franjas) no debe superar el 100% (+ tolerancia).
    Retorna: (is_valid, total_sum, remaining_area, message)
    """
    if crop_area_pct < -tolerance or natural_area_pct < -tolerance or floral_strips_pct < -tolerance:
        return False, 0.0, 0.0, "Coberturas negativas no permitidas"
    
    total = float(crop_area_pct + natural_area_pct + floral_strips_pct)
    remaining = float(max(0.0, 100.0 - total))
    
    if total > 100.0 + tolerance:
        excess = total - 100.0
        return False, total, remaining, f"Violación de balance de coberturas: suma={total:.2f}% excede 100% por {excess:.2f}%"
    
    return True, total, remaining, "OK"


def check_feature_domain(
    features: Dict[str, float],
    observed_ranges: Optional[Dict[str, Tuple[float, float] | List[float]]] = None,
    physical_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
    require_observed: bool = False,
) -> Dict[str, Any]:
    """
    Evalúa el dominio univariado distinguiendo:
      1. Límites físicos generales.
      2. Rangos observados en el dataset de entrenamiento correspondiente.
      3. Coherencia física de suma de coberturas.
    """
    bounds = physical_bounds or PHYSICAL_BOUNDS
    violations: List[str] = []

    # 1. Comprobación contra límites físicos generales
    for feat, (b_min, b_max) in bounds.items():
        if feat in features:
            val = float(features[feat])
            if val < b_min or val > b_max:
                violations.append(
                    f"Variable {feat}={val} fuera de los límites físicos [{b_min}, {b_max}]"
                )

    # 2. Comprobación contra rangos aprendidos de entrenamiento
    if observed_ranges:
        for feat, rng in observed_ranges.items():
            if feat in features:
                val = float(features[feat])
                r_min, r_max = float(rng[0]), float(rng[1])
                if val < r_min or val > r_max:
                    violations.append(
                        f"Variable {feat}={val} fuera del rango observado en entrenamiento [{r_min:.2f}, {r_max:.2f}]"
                    )
    elif require_observed:
        violations.append("Metadatos de rangos observados de entrenamiento ausentes en ejecución estricta.")

    # 3. Comprobación física de coberturas
    c_pct = float(features.get("crop_area_pct", 0.0))
    n_pct = float(features.get("natural_area_pct", 0.0))
    f_pct = float(features.get("floral_strips_pct", 0.0))
    is_cov_valid, tot, _, msg = validate_coverage(c_pct, n_pct, f_pct)
    if not is_cov_valid:
        violations.append(msg)

    return {
        "is_valid": len(violations) == 0,
        "violations": violations,
        "joint_support_warning": JOINT_SUPPORT_WARNING,
    }



def repair_coverage(
    crop_area_pct: float,
    natural_area_pct: float,
    floral_strips_pct: float,
) -> Tuple[float, float, float]:
    """
    Ajusta coberturas para respetar el límite del 100% preservando
    prioritariamente el área natural y las franjas florales.
    """
    nat = float(max(0.0, natural_area_pct))
    flor = float(max(0.0, floral_strips_pct))
    rem = max(0.0, 100.0 - nat - flor)
    crop = float(min(crop_area_pct, rem))
    return crop, nat, flor


def check_feature_bounds(row: Dict[str, float]) -> List[str]:
    """Valida los límites físicos de un registro o diccionario de características."""
    violations = []
    for feat, (b_min, b_max) in PHYSICAL_BOUNDS.items():
        if feat in row:
            val = float(row[feat])
            if val < b_min or val > b_max:
                violations.append(f"{feat}={val} fuera de [{b_min}, {b_max}]")
    return violations


def compute_target_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict[str, float]]:
    """Calcula MAE, RMSE y R2 para cada una de las 3 salidas objetivo."""
    metrics: Dict[str, Dict[str, float]] = {}
    for i, col in enumerate(TARGET_COLUMNS):
        yt = y_true[:, i]
        yp = y_pred[:, i]
        mae = float(np.mean(np.abs(yt - yp)))
        rmse = float(np.sqrt(np.mean((yt - yp) ** 2)))
        var_yt = float(np.var(yt))
        r2 = float(1.0 - (np.sum((yt - yp) ** 2) / np.sum((yt - np.mean(yt)) ** 2))) if var_yt > 1e-12 else float("nan")
        metrics[col] = {"mae": mae, "rmse": rmse, "r2": r2}
    return metrics


def compute_macro_metrics(target_metrics: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Calcula las métricas macro no ponderadas a través de las 3 salidas en escala original."""
    maes = [m["mae"] for m in target_metrics.values()]
    rmses = [m["rmse"] for m in target_metrics.values()]
    r2s = [m["r2"] for m in target_metrics.values() if not np.isnan(m["r2"])]
    return {
        "macro_mae": float(np.mean(maes)) if maes else float("nan"),
        "macro_rmse": float(np.mean(rmses)) if rmses else float("nan"),
        "macro_r2": float(np.mean(r2s)) if r2s else float("nan"),
    }
