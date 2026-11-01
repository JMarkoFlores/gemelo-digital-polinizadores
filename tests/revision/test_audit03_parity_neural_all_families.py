"""
tests/revision/test_audit03_parity_neural_all_families.py
Pruebas de regresión obligatorias para la Auditoría 03 - Bloque 6:
Paridad estricta en 4 etapas para modelos neuronales (DNN y Bottleneck MLP),
y prueba de integración fin a fin con nested CV neuronal.
"""
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.generator import generate_coherent_dataset
from scientific_core.nested_cv import (
    ModelFactory,
    fit_and_predict_neural_outer,
    fit_and_predict_traditional,
    run_nested_cv,
    select_final_hyperparameters,
)
from scientific_core.model_bundle import UniversalSurrogatePredictor, export_bundle, load_bundle
from backend.app.services.model_store import ModelStore


def _check_neural_parity_stages(family: str, params: dict, tmp_path: Path):
    """
    Comprueba paridad numérica estricta (<= 1e-4) a través de las 4 etapas:
      Etapa A: Modelo evaluado directamente con fit_and_predict (ajuste con escaladores).
      Etapa B: UniversalSurrogatePredictor antes de exportar.
      Etapa C: Predictor recargado desde disco (load_bundle).
      Etapa D: Inferencia del backend (ModelStore.predict).
    """
    try:
        import tensorflow as tf
    except ImportError:
        pytest.skip("TensorFlow no disponible en este entorno.")

    df, _ = generate_coherent_dataset(n_samples=40, random_state=42)
    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[TARGET_COLUMNS].to_numpy(dtype=np.float32)

    X_train, X_test = X[:30], X[30:]
    y_train, y_test = y[:30], y[30:]

    # Etapa A: Predicción directa
    preds_eval_a, scaler_x, scaler_y, trained_model = fit_and_predict_neural_outer(
        model_family=family,
        params=params,
        X_train_outer=X_train,
        y_train_outer=y_train,
        X_test_outer=X_test,
        optimal_epochs=3,
        seed=42,
    )
    assert preds_eval_a.shape == (10, 3)
    assert np.all(np.isfinite(preds_eval_a))

    # Etapa B: UniversalSurrogatePredictor antes de exportar
    observed_ranges = {col: [float(X[:, i].min()), float(X[:, i].max())] for i, col in enumerate(FEATURE_COLUMNS)}
    predictor_b = UniversalSurrogatePredictor(
        model=trained_model,
        model_type=family,
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={
            "observed_training_ranges": observed_ranges,
            "test_only": False,
        },
    )
    preds_b = predictor_b.predict(X_test)
    assert preds_b.shape == (10, 3)

    # Etapa C: Predictor recargado desde disco (load_bundle)
    bundle_dir = tmp_path / f"bundle_{family}"
    export_bundle(predictor_b, bundle_dir, metadata_overlay={"test_only": False})
    predictor_c = load_bundle(bundle_dir, allow_test_bundle=True)
    preds_c = predictor_c.predict(X_test)

    # Etapa D: Inferencia del backend (ModelStore.predict)
    store = ModelStore(bundle_dir, allow_test_bundle=True)
    store.load()
    assert store.is_ready is True
    preds_d = store.predict(X_test)

    # Tolerancia numérica estricta (1e-4)
    tol = 1e-4
    diff_ab = float(np.max(np.abs(preds_eval_a - preds_b)))
    diff_bc = float(np.max(np.abs(preds_b - preds_c)))
    diff_cd = float(np.max(np.abs(preds_c - preds_d)))

    assert diff_ab <= tol, f"[{family}] Discrepancia Etapa A vs B: {diff_ab} > {tol}"
    assert diff_bc <= tol, f"[{family}] Discrepancia Etapa B vs C: {diff_bc} > {tol}"
    assert diff_cd <= tol, f"[{family}] Discrepancia Etapa C vs D: {diff_cd} > {tol}"


def test_audit03_dnn_four_stage_parity(tmp_path):
    """Verifica paridad de 4 etapas para la familia DNN."""
    _check_neural_parity_stages("dnn", {"hidden_units": [32, 16], "epochs": 5, "batch_size": 16}, tmp_path)


def test_audit03_bottleneck_mlp_four_stage_parity(tmp_path):
    """Verifica paridad de 4 etapas para la familia autoencoder_mlp (cuello de botella)."""
    _check_neural_parity_stages("autoencoder_mlp", {"bottleneck_dim": 4, "epochs": 5, "batch_size": 16}, tmp_path)


def test_audit03_neural_nested_cv_and_refit_integration(tmp_path):
    """
    Prueba de integración de extremo a extremo:
    Ejecuta un nested CV pequeño con modelo neuronal, selecciona hiperparámetros
    por agregación y reajusta el modelo final exportando el bundle.
    """
    try:
        import tensorflow as tf
    except ImportError:
        pytest.skip("TensorFlow no disponible en este entorno.")

    df, _ = generate_coherent_dataset(n_samples=30, random_state=42)
    config = {
        "models": [
            {
                "family": "dnn",
                "param_grid": {
                    "hidden_units": [[16, 8]],
                    "epochs": [3],
                    "batch_size": [16],
                },
            }
        ],
        "outer_cv": {
            "n_splits": 2,
            "group_duplicates": True,
        },
        "inner_cv": {
            "n_splits": 2,
        },
        "allow_adaptation": True,
    }

    cv_results = run_nested_cv(df, config=config)
    assert cv_results is not None
    assert "tuning_records" in cv_results
    assert len(cv_results["tuning_records"]) > 0

    df_records = pd.DataFrame(cv_results["tuning_records"])
    best_params, optimal_epochs, policy = select_final_hyperparameters(
        df_records, model_family="dnn", expected_n_evaluations=2
    )
    assert "hidden_units" in best_params

    # Reajuste final sobre dataset completo
    X_full = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y_full = df[TARGET_COLUMNS].to_numpy(dtype=np.float32)

    _, scaler_x, scaler_y, final_model = fit_and_predict_neural_outer(
        model_family="dnn",
        params=best_params,
        X_train_outer=X_full,
        y_train_outer=y_full,
        X_test_outer=X_full[:5],
        optimal_epochs=3,
        seed=42,
    )

    observed_ranges = {col: [float(X_full[:, i].min()), float(X_full[:, i].max())] for i, col in enumerate(FEATURE_COLUMNS)}
    predictor = UniversalSurrogatePredictor(
        model=final_model,
        model_type="dnn",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": observed_ranges},
    )

    export_res = export_bundle(predictor, tmp_path / "final_dnn_bundle", metadata_overlay={"test_only": False})
    assert export_res["status"] == "verified"
    assert export_res["bundle_id"] is not None
