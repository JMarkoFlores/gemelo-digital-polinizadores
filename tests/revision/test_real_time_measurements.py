"""
tests/revision/test_real_time_measurements.py
Verifica que las métricas de tiempo de entrenamiento e inferencia provengan de mediciones reales
y no de constantes arbitrarias como 0.1 y 0.01 (Bloque 6 de la Auditoría 02).
"""
import numpy as np
import pandas as pd
import pytest

from scientific_core.nested_cv import run_nested_cv
from streamlit_app.advanced_training import train_and_evaluate_all_models


def create_clean_sample_df(n_samples: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    data = {
        "sample_id": np.arange(n_samples),
        "crop_area_pct": rng.uniform(20.0, 60.0, size=n_samples),
        "natural_area_pct": rng.uniform(10.0, 30.0, size=n_samples),
        "floral_strips_pct": rng.uniform(2.0, 8.0, size=n_samples),
        "pesticide_level": rng.uniform(10.0, 50.0, size=n_samples),
        "soil_management_score": rng.uniform(40.0, 90.0, size=n_samples),
        "temperature_c": rng.uniform(18.0, 26.0, size=n_samples),
        "precipitation_mm": rng.uniform(800.0, 1400.0, size=n_samples),
        "landscape_diversity": rng.uniform(0.3, 0.9, size=n_samples),
        "crop_yield_index": rng.uniform(80.0, 150.0, size=n_samples),
        "pollinator_abundance_index": rng.uniform(50.0, 120.0, size=n_samples),
        "pollinator_diversity_index": rng.uniform(30.0, 80.0, size=n_samples),
    }
    return pd.DataFrame(data)


def test_no_fictitious_timings_in_nested_cv():
    """Verifica que run_nested_cv reporte tiempos reales medidos para cada familia."""
    df = create_clean_sample_df(30)
    config = {
        "outer_cv": {"n_splits": 2, "seed": 42, "group_duplicates": False},
        "inner_cv": {"n_splits": 2, "seed": 1042},
        "models": {
            "ridge": {"enabled": True, "param_grid": [{"alpha": 1.0}]},
            "random_forest": {"enabled": True, "param_grid": [{"n_estimators": 5, "max_depth": 3}]},
        },
    }

    res = run_nested_cv(df, config)
    summary_df = res["summary_df"]

    assert "Train_Time_Mean" in summary_df.columns
    assert "Infer_Time_Mean" in summary_df.columns

    for _, row in summary_df.iterrows():
        t_train = row["Train_Time_Mean"]
        t_infer = row["Infer_Time_Mean"]
        assert t_train is not None and not np.isnan(t_train)
        assert t_train > 0.0, "El tiempo de entrenamiento debe ser positivo"
        # Comprobar que no son los valores fijos arbitrarios 0.1 o 0.01
        assert t_train != 0.1, "El tiempo de entrenamiento no debe ser la constante ficticia 0.1"
        assert t_infer != 0.01, "El tiempo de inferencia no debe ser la constante ficticia 0.01"

    # Comparar tiempos entre Ridge y Random Forest: RF toma más tiempo en entrenar que Ridge
    ridge_time = float(summary_df[summary_df["model_id"] == "ridge"]["Train_Time_Mean"].iloc[0])
    rf_time = float(summary_df[summary_df["model_id"] == "random_forest"]["Train_Time_Mean"].iloc[0])
    assert ridge_time != rf_time, "El tiempo de entrenamiento debe variar entre familias de modelos"


def test_advanced_training_uses_measured_timings():
    """Verifica que train_and_evaluate_all_models utilice tiempos reales y no constantes."""
    df = create_clean_sample_df(30)
    res = train_and_evaluate_all_models(
        dataframe=df,
        k_folds=2,
        tune_hyperparameters=False,
        config_path="configs/smoke_test.json",
    )

    results_df = res["results_df"]
    for _, row in results_df.iterrows():
        t_train = row["Train_Time_Mean"]
        t_infer = row["Infer_Time_Mean"]
        assert t_train is not None and not np.isnan(t_train)
        assert t_train != 0.1
        assert t_infer != 0.01
