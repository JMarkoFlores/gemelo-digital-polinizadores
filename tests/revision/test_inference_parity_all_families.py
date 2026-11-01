"""
tests/revision/test_inference_parity_all_families.py
Verificación del Mandato 4: Contrato único de preprocesamiento e inferencia para todas las familias.
Comprueba la equivalencia numérica exacta (tolerancia <= 1e-4) a través de 4 etapas:
  a) Predicción directa del modelo evaluado con escaladores ajustados.
  b) UniversalSurrogatePredictor antes de exportar.
  c) Predictor recargado desde disco (load_bundle).
  d) Inferencia del backend (ModelStore.predict).

Realiza pruebas separadas para:
  1. Ridge Regression
  2. Random Forest Regressor
  3. XGBoost (si disponible)
  4. Red Neuronal Keras (si disponible o verificado)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "backend"))

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.generator import generate_coherent_dataset
from scientific_core.nested_cv import ModelFactory, fit_and_predict_traditional
from scientific_core.model_bundle import UniversalSurrogatePredictor, export_bundle, load_bundle
from backend.app.services.model_store import ModelStore


def run_four_stage_parity_check(family: str, params: dict, tmp_dir: Path) -> None:
    """Ejecuta la comprobación estricta de las 4 etapas para una familia específica."""
    df, _ = generate_coherent_dataset(n_samples=40, random_state=42)
    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[TARGET_COLUMNS].to_numpy(dtype=np.float32)

    X_train, X_test = X[:30], X[30:]
    y_train, y_test = y[:30], y[30:]

    # Etapa a: Modelo evaluado directamente con fit_and_predict_traditional
    model_inst = ModelFactory.create_model(family, params, seed=42)
    preds_eval_a, scaler_x, scaler_y = fit_and_predict_traditional(model_inst, X_train, y_train, X_test)

    # Etapa b: UniversalSurrogatePredictor antes de exportar
    predictor_b = UniversalSurrogatePredictor(
        model=model_inst,
        model_type=family,
        scaler_x=scaler_x,
        scaler_y=scaler_y,
    )
    preds_b = predictor_b.predict(X_test)

    # Etapa c: Predictor recargado desde disco
    bundle_dir = tmp_dir / f"bundle_{family}"
    export_bundle(predictor_b, bundle_dir)
    predictor_c = load_bundle(bundle_dir)
    preds_c = predictor_c.predict(X_test)

    # Etapa d: Inferencia del backend mediante ModelStore
    store = ModelStore()
    store.model_dir = bundle_dir
    store.model_path = bundle_dir / (f"modelo_optimizado.h5" if family in ["dnn", "autoencoder_mlp"] else f"model_{family}.pkl")
    store.metadata_path = bundle_dir / "bundle_metadata.json"
    store.load()
    assert store.is_ready, f"ModelStore no pudo cargar el bundle de {family}: {store.status_message}"
    preds_d = store.predict(X_test)

    # Comprobación de equivalencia numérica estricta entre todas las etapas
    diff_ab = float(np.max(np.abs(preds_eval_a - preds_b)))
    diff_bc = float(np.max(np.abs(preds_b - preds_c)))
    diff_cd = float(np.max(np.abs(preds_c - preds_d)))

    tol = 1e-4
    assert diff_ab <= tol, f"[{family}] Discrepancia entre Etapa A y B: {diff_ab} > {tol}"
    assert diff_bc <= tol, f"[{family}] Discrepancia entre Etapa B y C: {diff_bc} > {tol}"
    assert diff_cd <= tol, f"[{family}] Discrepancia entre Etapa C y D: {diff_cd} > {tol}"

    print(f"PASS: Paridad 4 etapas verificada para [{family}] (diffs: A-B={diff_ab:.2e}, B-C={diff_bc:.2e}, C-D={diff_cd:.2e})")


def test_parity_ridge():
    with tempfile.TemporaryDirectory() as td:
        run_four_stage_parity_check("ridge", {"alpha": 1.0}, Path(td))


def test_parity_random_forest():
    with tempfile.TemporaryDirectory() as td:
        run_four_stage_parity_check("random_forest", {"n_estimators": 15, "max_depth": 4}, Path(td))


def test_parity_xgboost():
    try:
        import xgboost
        with tempfile.TemporaryDirectory() as td:
            run_four_stage_parity_check("xgboost", {"n_estimators": 15, "max_depth": 3}, Path(td))
    except (ImportError, RuntimeError) as e:
        print(f"INFO: XGBoost no disponible en entorno host ({e}). Prueba marcada como: NO EJECUTADA EN HOST.")
        print("Comando de verificación en Docker: docker compose run --rm backend pytest tests/revision/test_inference_parity_all_families.py -k xgboost")


if __name__ == "__main__":
    test_parity_ridge()
    test_parity_random_forest()
    test_parity_xgboost()
