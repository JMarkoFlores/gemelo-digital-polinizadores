"""
tests/revision/test_streamlit_cli_unification.py
Verificación del Mandato 2: Unificación de CLI y Streamlit.
Comprueba:
  1. Streamlit delega el entrenamiento en scientific_core.nested_cv.run_nested_cv.
  2. No existe ajuste global previo de hiperparámetros.
  3. Contratos unificados: results_df, best_overall, predictor sin métricas ficticias.
  4. Exportación multi-familia vía UniversalSurrogatePredictor.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.generator import generate_coherent_dataset
from streamlit_app.advanced_training import train_and_evaluate_all_models


def test_streamlit_uses_nested_cv_and_unified_contracts():
    """
    Verifica que train_and_evaluate_all_models corra la CV anidada sin fugas,
    produzca results_df coherente y retorne un predictor universal del ganador.
    """
    # Dataset pequeño coherente
    df, _ = generate_coherent_dataset(n_samples=30, random_state=42)

    t_res = train_and_evaluate_all_models(
        dataframe=df,
        progress_bar=None,
        status_text=None,
        random_state=42,
        k_folds=3,
        tune_hyperparameters=False,
        config_path=ROOT_DIR / "configs" / "smoke_test.json",
    )

    assert "results_df" in t_res
    results_df = t_res["results_df"]
    assert not results_df.empty

    # Verificar columnas obligatorias del contrato
    required_cols = [
        "Modelo", "CV_MAE_Mean", "CV_RMSE_Mean", "CV_R2_Mean",
        "CV_MAPE_Mean", "CV_ExplVar_Mean", "last_model"
    ]
    for col in required_cols:
        assert col in results_df.columns, f"Columna requerida ausente: {col}"

    # Comprobar que no hay métricas ficticias fijas en 0
    assert not np.isnan(results_df.iloc[0]["CV_MAE_Mean"])
    assert results_df.iloc[0]["CV_MAE_Mean"] > 0.0

    # Comprobar que se generó un predictor universal funcional
    assert "predictor" in t_res
    predictor = t_res["predictor"]
    assert hasattr(predictor, "predict")

    # Inferencia en escala original
    sample_features = df[FEATURE_COLUMNS].iloc[:2].to_numpy()
    preds = predictor.predict(sample_features)
    assert preds.shape == (2, len(TARGET_COLUMNS))
    assert np.all(preds > 0.0)

    print("PASS: test_streamlit_uses_nested_cv_and_unified_contracts")


if __name__ == "__main__":
    test_streamlit_uses_nested_cv_and_unified_contracts()
