"""
tests/revision/test_t02_data_integrity.py
Prueba técnica T02: Validación rigurosa de integridad de dataset (NaN, Inf, coberturas y duplicados).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scientific_core.data_audit import audit_dataset
from scientific_core.generator import generate_coherent_dataset


def test_coherent_dataset_passes_audit():
    df, meta = generate_coherent_dataset(n_samples=50, random_state=42)
    audit = audit_dataset(df)
    assert audit["is_valid"] is True
    assert audit["coverage_violations_count"] == 0
    assert audit["total_nans"] == 0
    assert audit["total_infs"] == 0


def test_malformed_dataset_rejected_with_reasons():
    df, _ = generate_coherent_dataset(n_samples=30, random_state=42)
    
    # Inyectar anomalías
    df.loc[0, "crop_area_pct"] = np.nan
    df.loc[1, "temperature_c"] = np.inf
    df.loc[2, "crop_area_pct"] = 70.0
    df.loc[2, "natural_area_pct"] = 35.0
    df.loc[2, "floral_strips_pct"] = 15.0  # Suma 120%
    df.loc[4] = df.loc[3]  # Duplicado exacto

    res = audit_dataset(df)
    assert res["is_valid"] is False
    assert res["total_nans"] == 1
    assert res["total_infs"] == 1
    assert res["coverage_violations_count"] >= 1
    assert res["n_duplicates"] >= 2
    assert len(res["rejection_reasons"]) >= 3


if __name__ == "__main__":
    test_coherent_dataset_passes_audit()
    test_malformed_dataset_rejected_with_reasons()
    print("test_t02_data_integrity passed successfully!")
