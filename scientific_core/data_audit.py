"""
scientific_core/data_audit.py
Auditoría científica rigurosa de integridad de datos y verificación de procedencia real.
Garantiza:
  1. Procedencia veraz: No etiquetar variables como NASA POWER o GBIF por su mero nombre;
     exigir evidencia documental de importación / snapshot verificado.
  2. Detección exhaustiva de anomalías (NaN, Inf, duplicados).
  3. Cálculo de rangos empíricos observados para control estricto de dominio en inferencia.
  4. Verificación de balance físico de coberturas (suma <= 100%).
  5. Cálculo determinista de hashes criptográficos SHA-256.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
try:
    import pandas as pd
except ImportError:
    pd = None

from scientific_core.contracts import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    PHYSICAL_BOUNDS,
    validate_coverage,
)


def compute_file_sha256(filepath: Union[str, Path]) -> str:
    """Calcula el hash SHA-256 de un archivo en disco."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_dataframe_sha256(df: pd.DataFrame) -> str:
    """Calcula un hash SHA-256 determinista sobre el contenido numérico del DataFrame."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def classify_column_provenance(col: str, source_metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Clasifica la procedencia formal de cada variable basándose en evidencia real de origen
    y no en el nombre arbitrario de la columna (Mandato 8).
    """
    meta = source_metadata or {}
    source_type = str(meta.get("fuente_datos") or meta.get("source_type") or "sintetico")
    has_real_nasa = bool(meta.get("nasa_power_verified", False) or (source_type == "publico_gbif_nasa_power" and "snapshot_sha256" in meta))
    has_real_gbif = bool(meta.get("gbif_verified", False) or (source_type == "publico_gbif_nasa_power" and "gbif_snapshot_sha256" in meta))

    if col in ["temperature_c", "precipitation_mm"]:
        if has_real_nasa:
            return "dato_publico_nasa_power_verificado"
        return "variable_climatica_sintetica_calibrada"

    elif col in ["crop_area_pct", "natural_area_pct", "floral_strips_pct"]:
        return "variable_paisaje_agroecologico"

    elif col in ["pesticide_level", "soil_management_score"]:
        return "variable_manejo_agricola"

    elif col == "landscape_diversity":
        return "caracteristica_derivada_consistente"

    elif col in TARGET_COLUMNS:
        if has_real_gbif and col in ["pollinator_abundance_index", "pollinator_diversity_index"]:
            return "indice_hibrido_gbif_abm"
        return "indice_objetivo_simulado"

    elif col.startswith("abm_"):
        return "enriquecimiento_abm_mesa"

    else:
        return "metadato_o_auxiliar"


def classify_dataset_provenance(df: pd.DataFrame, source_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Clasifica la procedencia formal de cada variable y del conjunto completo
    basándose en evidencias verificables (Mandato 8).
    """
    col_prov = {col: classify_column_provenance(col, source_metadata) for col in df.columns}
    prov_values = set(col_prov.values())
    if any("nasa" in p for p in prov_values) or any("gbif" in p for p in prov_values):
        overall = "publico_gbif_nasa_power"
    elif any("sintetica" in p for p in prov_values):
        overall = "sintetico_calibrado"
    else:
        overall = "calibrado_revision"

    return {
        "overall_provenance": overall,
        "columns_provenance": col_prov,
    }


def audit_dataset(
    dataset_input: Union[str, Path, pd.DataFrame],
    policy: str = "corrected",
    group_duplicates: bool = True,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta la auditoría científica rigurosa:
      - Hashes criptográficos deterministas
      - Detección de ausentes (NaN / None) e infinitos
      - Detección y agrupamiento de duplicados de características
      - Violaciones univariadas de límites físicos
      - Cálculo de los rangos observados en el dataset (observed_ranges)
      - Violación de la regla física de balance de coberturas (crop + nat + floral <= 100)
      - Procedencia veraz por columna sin claims infundados
    """
    if isinstance(dataset_input, (str, Path)):
        p = Path(dataset_input)
        if not p.exists():
            raise FileNotFoundError(f"Archivo de dataset no encontrado: {p}")
        df = pd.read_csv(p)
        file_sha256 = compute_file_sha256(p)
    else:
        df = dataset_input.copy()
        file_sha256 = compute_dataframe_sha256(df)

    n_rows, n_cols = df.shape
    cols = df.columns.tolist()

    rejection_reasons: List[str] = []

    # 1. Comprobación de dataset vacío
    if n_rows == 0:
        rejection_reasons.append("El dataset está vacío (0 filas).")

    # 2. Comprobación de columnas requeridas (entradas y salidas)
    missing_features = [c for c in FEATURE_COLUMNS if c not in cols]
    if missing_features:
        rejection_reasons.append(f"Columnas de entrada requeridas ausentes: {missing_features}")

    missing_targets = [c for c in TARGET_COLUMNS if c not in cols]
    if policy == "corrected" and missing_targets:
        rejection_reasons.append(f"Columnas objetivo requeridas ausentes: {missing_targets}")

    # 3. Comprobación de tipos numéricos
    cols_to_check_numeric = [c for c in FEATURE_COLUMNS if c in cols]
    if policy == "corrected":
        cols_to_check_numeric += [c for c in TARGET_COLUMNS if c in cols]

    non_numeric_cols = []
    for c in cols_to_check_numeric:
        if not pd.api.types.is_numeric_dtype(df[c]):
            non_numeric_cols.append(c)
    if non_numeric_cols:
        rejection_reasons.append(f"Columnas con tipos de datos no numéricos inválidos: {non_numeric_cols}")

    # 4. Comprobación de identificadores de muestra duplicados
    if "sample_id" in cols:
        sample_id_dups = int(df["sample_id"].duplicated().sum())
        if sample_id_dups > 0:
            rejection_reasons.append(
                f"Identificadores de muestra repetidos en 'sample_id': {sample_id_dups} registros duplicados."
            )

    # 5. Comprobación de nulos e infinitos
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    nan_counts = {col: int(df[col].isna().sum()) for col in cols if df[col].isna().sum() > 0}
    inf_counts = {col: int(np.isinf(df[col]).sum()) for col in numeric_cols if np.isinf(df[col]).sum() > 0}

    # 6. Análisis de duplicados de características
    feature_cols_present = [c for c in FEATURE_COLUMNS if c in df.columns]
    if feature_cols_present and n_rows > 0 and len(non_numeric_cols) == 0:
        duplicates_mask = df.duplicated(subset=feature_cols_present, keep=False)
        n_duplicate_rows = int(duplicates_mask.sum())
        # Identificación de grupos estables de duplicados
        rounded_feats = np.round(df[feature_cols_present].to_numpy(dtype=float), decimals=4)
        _, group_indices = np.unique(rounded_feats, axis=0, return_inverse=True)
        df_audit_groups = group_indices.tolist()
        n_unique_groups = len(set(df_audit_groups))
    else:
        n_duplicate_rows = 0
        df_audit_groups = list(range(n_rows))
        n_unique_groups = n_rows

    # 7. Comprobación de límites físicos univariados y cálculo de rangos observados
    bounds_violations = {}
    observed_ranges = {}
    for feat in feature_cols_present:
        if feat in non_numeric_cols:
            continue
        vals = df[feat].to_numpy(dtype=float)
        if len(vals) == 0:
            continue
        b_min, b_max = PHYSICAL_BOUNDS[feat]
        below = int((vals < b_min).sum())
        above = int((vals > b_max).sum())
        if below > 0 or above > 0:
            bounds_violations[feat] = {
                "below_min": below,
                "above_max": above,
                "allowed_bounds": [b_min, b_max],
            }
        observed_ranges[feat] = [float(vals.min()), float(vals.max())]

    # 8. Violación de balance físico de coberturas
    coverage_violations = 0
    max_coverage_sum = 0.0
    if all(c in df.columns for c in ["crop_area_pct", "natural_area_pct", "floral_strips_pct"]):
        if not any(c in non_numeric_cols for c in ["crop_area_pct", "natural_area_pct", "floral_strips_pct"]):
            cov_sums = (df["crop_area_pct"] + df["natural_area_pct"] + df["floral_strips_pct"]).to_numpy(dtype=float)
            coverage_violations = int((cov_sums > 100.0001).sum())
            max_coverage_sum = float(cov_sums.max()) if len(cov_sums) > 0 else 0.0

    # 9. Procedencia veraz por columna
    provenance_map = {c: classify_column_provenance(c, source_metadata) for c in cols}

    total_nans = int(sum(nan_counts.values()))
    total_infs = int(sum(inf_counts.values()))
    if total_nans > 0:
        rejection_reasons.append(f"Se encontraron {total_nans} valores nulos (NaN/None).")
    if total_infs > 0:
        rejection_reasons.append(f"Se encontraron {total_infs} valores infinitos.")
    if coverage_violations > 0:
        rejection_reasons.append(f"Se encontraron {coverage_violations} violaciones de balance de coberturas (suma > 100%).")
    if bounds_violations:
        rejection_reasons.append(f"Violaciones de límites físicos en {len(bounds_violations)} variables.")

    audit_passed = len(rejection_reasons) == 0

    audit_summary = {
        "file_sha256": file_sha256,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "audit_passed": audit_passed,
        "is_valid": audit_passed,
        "valid": audit_passed,
        "nan_counts": nan_counts,
        "total_nans": total_nans,
        "inf_counts": inf_counts,
        "total_infs": total_infs,
        "n_duplicate_rows": n_duplicate_rows,
        "n_duplicates": n_duplicate_rows,
        "n_unique_feature_groups": n_unique_groups,
        "bounds_violations": bounds_violations,
        "observed_ranges": observed_ranges,
        "coverage_violations": coverage_violations,
        "coverage_violations_count": coverage_violations,
        "max_coverage_sum": max_coverage_sum,
        "column_provenance": provenance_map,
        "rejection_reasons": rejection_reasons,
        "issues": rejection_reasons,
        "errors": rejection_reasons,
        "source_metadata_declared": source_metadata or {"fuente_datos": "sintetico_calibrado"},
    }

    return audit_summary
