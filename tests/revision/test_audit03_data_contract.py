"""
tests/revision/test_audit03_data_contract.py
Pruebas de regresión obligatorias para la Auditoría 03 - Bloque 5:
Contratos de datos íntegros, auditoría estricta y particionado científico sin degradación silenciosa.
"""
import numpy as np
import pandas as pd
import pytest

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.data_audit import audit_dataset
from scientific_core.nested_cv import run_nested_cv


def _make_valid_df(n_samples=20):
    data = {
        "sample_id": np.arange(n_samples),
        "crop_area_pct": np.linspace(20.0, 60.0, n_samples),
        "natural_area_pct": np.linspace(10.0, 30.0, n_samples),
        "floral_strips_pct": np.linspace(2.0, 10.0, n_samples),
        "pesticide_level": np.linspace(10.0, 50.0, n_samples),
        "soil_management_score": np.linspace(40.0, 80.0, n_samples),
        "temperature_c": np.linspace(18.0, 26.0, n_samples),
        "precipitation_mm": np.linspace(900.0, 1400.0, n_samples),
        "landscape_diversity": np.linspace(0.4, 0.8, n_samples),
        "crop_yield_index": np.linspace(100.0, 130.0, n_samples),
        "pollinator_abundance_index": np.linspace(70.0, 110.0, n_samples),
        "pollinator_diversity_index": np.linspace(40.0, 60.0, n_samples),
    }
    return pd.DataFrame(data)


def test_audit_dataset_rejects_missing_targets_in_corrected_policy():
    """Verifica que audit_dataset en política corrected exige TODAS las columnas objetivo."""
    df = _make_valid_df()
    df = df.drop(columns=["pollinator_diversity_index"])
    res = audit_dataset(df, policy="corrected")
    assert res["valid"] is False
    assert any("pollinator_diversity_index" in r for r in res["rejection_reasons"])
    assert res["rejection_reasons"] == res["issues"]
    assert res["rejection_reasons"] == res["errors"]


def test_audit_dataset_rejects_missing_features():
    """Verifica que audit_dataset exige TODAS las columnas de características."""
    df = _make_valid_df()
    df = df.drop(columns=["temperature_c"])
    res = audit_dataset(df, policy="corrected")
    assert res["valid"] is False
    assert any("temperature_c" in r for r in res["rejection_reasons"])


def test_audit_dataset_rejects_non_numeric_columns():
    """Verifica el rechazo de tipos no numéricos o strings en columnas cuantitativas."""
    df = _make_valid_df()
    df["crop_area_pct"] = ["valid_text"] * len(df)
    res = audit_dataset(df, policy="corrected")
    assert res["valid"] is False
    assert any("no numéricos" in r for r in res["rejection_reasons"])


def test_audit_dataset_rejects_repeated_sample_id():
    """Verifica el reporte explícito de identificadores sample_id repetidos."""
    df = _make_valid_df()
    df.loc[1, "sample_id"] = df.loc[0, "sample_id"]  # duplicado
    res = audit_dataset(df, policy="corrected")
    assert res["valid"] is False
    assert any("duplicados" in r for r in res["rejection_reasons"])


def test_audit_dataset_rejects_empty_dataframe():
    """Verifica que un DataFrame vacío (0 filas) se rechaza de inmediato."""
    df_empty = pd.DataFrame(columns=["sample_id"] + FEATURE_COLUMNS + TARGET_COLUMNS)
    res = audit_dataset(df_empty, policy="corrected")
    assert res["valid"] is False
    assert any("vacío" in r for r in res["rejection_reasons"])


def test_nested_cv_rejects_insufficient_groups_without_silent_fold_reduction():
    """
    En modo científico estricto, run_nested_cv debe lanzar ValueError si los grupos únicos
    son menores a los folds solicitados, en lugar de degradar silenciosamente el particionado.
    """
    # 20 muestras pero sólo 2 perfiles únicos de features repetidos 10 veces cada uno
    row1 = _make_valid_df(n_samples=1)
    row2 = _make_valid_df(n_samples=1)
    row2["crop_area_pct"] = 80.0
    df = pd.concat([row1] * 10 + [row2] * 10, ignore_index=True)
    df["sample_id"] = np.arange(20)

    config = {
        "models": [{"family": "ridge", "param_grid": {"alpha": [1.0]}}],
        "outer_cv": {"n_splits": 5, "group_duplicates": True},
        "inner_cv": {"n_splits": 3},
        "allow_adaptation": False,
    }

    with pytest.raises(ValueError, match="Grupos únicos de características insuficientes"):
        run_nested_cv(df, config=config)


def test_nested_cv_persists_complete_splits_manifest():
    """
    Verifica que el splits_manifest almacena todos los índices y metadatos necesarios
    para reconstruir exactamente cada partición externa e interna.
    """
    df = _make_valid_df(n_samples=30)

    config = {
        "models": [{"family": "ridge", "param_grid": {"alpha": [1.0]}}],
        "outer_cv": {"n_splits": 3, "group_duplicates": True},
        "inner_cv": {"n_splits": 2},
        "allow_adaptation": True,
    }
    result = run_nested_cv(df, config=config)

    manifest = result["splits_manifest"]
    assert "outer_folds" in manifest
    assert len(manifest["outer_folds"]) == 3

    for o_split in manifest["outer_folds"]:
        assert "train_indices" in o_split
        assert "test_indices" in o_split
        assert "inner_splits" in o_split
        assert len(o_split["inner_splits"]) == 2
        for i_split in o_split["inner_splits"]:
            assert "in_train_indices" in i_split
            assert "in_val_indices" in i_split
