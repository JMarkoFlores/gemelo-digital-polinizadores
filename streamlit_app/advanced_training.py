"""
streamlit_app/advanced_training.py
Módulo de entrenamiento y evaluación adaptado al núcleo científico riguroso (Nested CV).
Garantiza:
  1. Delegación completa en scientific_core.nested_cv.run_nested_cv.
  2. Eliminación definitiva del ajuste global de hiperparámetros antes de la CV.
  3. Escalado independiente por fold sin fuga hacia validación ni test.
  4. Refit final documentado del modelo ganador sobre el dataset de desarrollo.
  5. Soporte integral de UniversalSurrogatePredictor para exportación multi-familia.
"""
from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.metrics import (
    explained_variance_score,
    max_error,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)
from sklearn.preprocessing import StandardScaler

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.model_bundle import UniversalSurrogatePredictor, export_bundle
from scientific_core.nested_cv import (
    ModelFactory,
    fit_and_predict_neural_outer,
    run_nested_cv,
)

logger = logging.getLogger(__name__)

FAMILY_DISPLAY_NAMES = {
    "random_forest": "Random Forest (Tradicional)",
    "ridge": "Ridge Regression (Tradicional)",
    "xgboost": "XGBoost (Tradicional)",
    "dnn": "DNN Surrogate (Híbrido)",
    "autoencoder_mlp": "Autoencoder+MLP (Híbrido)",
}

DISPLAY_TO_FAMILY = {v: k for k, v in FAMILY_DISPLAY_NAMES.items()}


def evaluate_preds(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Dict[str, float]]:
    metrics = {}
    for i, target in enumerate(TARGET_COLUMNS):
        yt = y_true[:, i]
        yp = y_pred[:, i]
        var_yt = float(np.var(yt))
        metrics[target] = {
            "mae": float(mean_absolute_error(yt, yp)),
            "rmse": float(np.sqrt(mean_squared_error(yt, yp))),
            "r2": float(r2_score(yt, yp)) if var_yt > 1e-12 else float("nan"),
            "mape": float(mean_absolute_percentage_error(yt, yp)),
            "max_error": float(max_error(yt, yp)),
            "medae": float(median_absolute_error(yt, yp)),
            "explained_variance": float(explained_variance_score(yt, yp)) if var_yt > 1e-12 else float("nan"),
        }
    return metrics


def train_and_evaluate_all_models(
    dataframe: pd.DataFrame,
    progress_bar: Any = None,
    status_text: Any = None,
    random_state: int = 42,
    k_folds: int = 5,
    tune_hyperparameters: bool = False,
    config_path: Optional[Union[str, Path]] = None,
    scientific_mode: bool = False,
    group_duplicates: Optional[bool] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Entrena y compara modelos utilizando exclusivamente la validación cruzada anidada
    de scientific_core, gobernado por una sola configuración efectiva (Auditoría 05, Hallazgo 1).
    """
    if config is None:
        from streamlit_app.adapter import prepare_streamlit_run_config
        config = prepare_streamlit_run_config(
            k_folds=k_folds,
            tune_hyperparameters=tune_hyperparameters,
            scientific_mode=scientific_mode,
            random_state=random_state,
            config_path=config_path,
            group_duplicates=group_duplicates,
        )

    # Semilla canónica efectiva gobernada por la configuración única (Auditoría 06, Hallazgo 1)
    final_seed = int(
        config.get("seed")
        if config.get("seed") is not None
        else config.get("outer_cv", {}).get("seed", random_state)
    )

    def _callback(msg: str) -> None:
        if status_text:
            status_text.text(msg)

    # 1. Ejecutar CV anidada rigurosa con la configuración efectiva única
    cv_res = run_nested_cv(df=dataframe, config=config, status_callback=_callback)

    available_families = cv_res["available_families"]
    summary_cv = cv_res["summary_df"]
    oof_preds_by_model = cv_res["oof_preds_matrices"]
    oof_df = cv_res["oof_predictions_df"]
    fold_metrics_df = cv_res["fold_metrics_df"]
    tuning_df = cv_res["tuning_results_df"]

    y_full = dataframe[TARGET_COLUMNS].to_numpy(dtype=np.float32)
    X_full = dataframe[FEATURE_COLUMNS].to_numpy(dtype=np.float32)

    results_rows: List[Dict[str, Any]] = []

    for fam in available_families:
        disp_name = FAMILY_DISPLAY_NAMES.get(fam, fam)
        oof_matrix = oof_preds_by_model[fam]

        # Métricas descriptivas detalladas sobre OOF
        oof_target_metrics = evaluate_preds(y_full, oof_matrix)
        macro_mape = float(np.mean([m["mape"] for m in oof_target_metrics.values()]))
        macro_max_err = float(np.mean([m["max_error"] for m in oof_target_metrics.values()]))
        macro_medae = float(np.mean([m["medae"] for m in oof_target_metrics.values()]))
        macro_ev = float(np.nanmean([m["explained_variance"] for m in oof_target_metrics.values()]))

        # Métricas CV por fold
        fam_folds = fold_metrics_df[
            (fold_metrics_df["model_id"] == fam) & (fold_metrics_df["target"] == "macro_average")
        ]
        mean_mae = float(fam_folds["mae"].mean()) if not fam_folds.empty else float("nan")
        std_mae = float(fam_folds["mae"].std()) if not fam_folds.empty else 0.0
        mean_rmse = float(fam_folds["rmse"].mean()) if not fam_folds.empty else float("nan")
        std_rmse = float(fam_folds["rmse"].std()) if not fam_folds.empty else 0.0
        mean_r2 = float(fam_folds["r2"].mean()) if not fam_folds.empty else float("nan")
        std_r2 = float(fam_folds["r2"].std()) if not fam_folds.empty else 0.0

        # Medición real de tiempos recuperada de la evaluación nested CV (Bloque 6)
        fam_sum = summary_cv[summary_cv["model_id"] == fam] if "model_id" in summary_cv.columns else pd.DataFrame()
        train_time_val = (
            float(fam_sum.iloc[0]["Train_Time_Mean"])
            if not fam_sum.empty and "Train_Time_Mean" in fam_sum.columns and not pd.isna(fam_sum.iloc[0]["Train_Time_Mean"])
            else None
        )
        infer_time_val = (
            float(fam_sum.iloc[0]["Infer_Time_Mean"])
            if not fam_sum.empty and "Infer_Time_Mean" in fam_sum.columns and not pd.isna(fam_sum.iloc[0]["Infer_Time_Mean"])
            else None
        )

        results_rows.append({
            "model_family": fam,
            "Modelo": disp_name,
            "CV_MAE_Mean": mean_mae,
            "CV_MAE_Std": std_mae,
            "CV_RMSE_Mean": mean_rmse,
            "CV_RMSE_Std": std_rmse,
            "CV_R2_Mean": mean_r2,
            "CV_R2_Std": std_r2,
            "CV_MAPE_Mean": macro_mape,
            "CV_MaxError_Mean": macro_max_err,
            "CV_MedAE_Mean": macro_medae,
            "CV_ExplVar_Mean": macro_ev,
            "Train_Time_Mean": train_time_val,
            "Infer_Time_Mean": infer_time_val,
            "last_y_true": y_full,
            "last_y_pred": oof_matrix,
            "last_X_val": X_full,
        })

    results_df = pd.DataFrame(results_rows).sort_values(
        by=["CV_MAE_Mean", "CV_RMSE_Mean", "CV_R2_Mean"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    best_family = results_df.iloc[0]["model_family"]
    best_overall_display = results_df.iloc[0]["Modelo"]

    # 2. Refit final documentado del modelo ganador sobre TODO el dataset de desarrollo
    if status_text:
        status_text.text(f"Ajustando modelo ganador ({best_overall_display}) sobre el dataset completo...")

    # Recuperar los mejores hiperparámetros del ganador mediante selección agregada unificada (Bloque 1)
    from scientific_core.nested_cv import select_final_hyperparameters
    if not tuning_df.empty:
        best_params, opt_epochs, selection_policy = select_final_hyperparameters(
            tuning_df=tuning_df,
            model_family=best_family,
            allow_adaptation=not scientific_mode,
        )
    else:
        best_params = {}
        opt_epochs = 20
        selection_policy = {
            "method": "default_fallback",
            "description": "Sin registros de tuning previos",
        }

    scaler_x_final = StandardScaler().fit(X_full)
    scaler_y_final = StandardScaler().fit(y_full)

    if best_family in ["dnn", "autoencoder_mlp"]:
        _, _, _, final_trained_model = fit_and_predict_neural_outer(
            model_family=best_family,
            params=best_params,
            X_train_outer=X_full,
            y_train_outer=y_full,
            X_test_outer=X_full[:1],  # Dummy evaluado
            optimal_epochs=opt_epochs,
            seed=final_seed,
        )
        best_keras_model = final_trained_model
    else:
        final_trained_model = ModelFactory.create_model(best_family, best_params, seed=final_seed)
        final_trained_model.fit(scaler_x_final.transform(X_full), scaler_y_final.transform(y_full))
        best_keras_model = None

    # Registrar el predictor universal listo para predicciones e importancia de variables
    final_predictor = UniversalSurrogatePredictor(
        model=final_trained_model,
        model_type=best_family,
        scaler_x=scaler_x_final,
        scaler_y=scaler_y_final,
        metadata={
            "fuente_datos": "calibrado_nested_cv",
            "best_family": best_family,
            "best_params": best_params,
            "final_selection_policy": selection_policy,
            "final_seed": final_seed,
            "optimal_epochs": opt_epochs if best_family in ["dnn", "autoencoder_mlp"] else None,
        },
    )

    # Inyectar el objeto predictor en el DataFrame para el cálculo de feature importance
    results_df["last_model"] = [final_predictor] * len(results_df)

    dataset_summary = dataframe.describe().reset_index()
    dataset_summary.rename(columns={"index": "Estadística"}, inplace=True)

    # Preparar tabla de tuning para UI si aplica
    tuning_ui_df = None
    if not tuning_df.empty:
        tuning_ui_df = tuning_df.copy()
        tuning_ui_df["Modelo"] = tuning_ui_df["model_family"].map(FAMILY_DISPLAY_NAMES).fillna(tuning_ui_df["model_family"])

    return {
        "results_df": results_df,
        "dataset_summary": dataset_summary,
        "best_keras_model": best_keras_model,
        "target_scaler": scaler_y_final,
        "scaler_x": scaler_x_final,
        "predictor": final_predictor,
        "best_overall": best_overall_display,
        "best_family": best_family,
        "best_params": best_params,
        "final_selection_policy": selection_policy,
        "final_seed": final_seed,
        "cv_results": cv_res,
        "config_effective": config,
        "hyperparameter_tuning": {
            "activado": tune_hyperparameters,
            "mejores_params_por_modelo": {best_family: best_params},
            "tuning_df": tuning_ui_df,
            "tiempo_total_tuning": round(cv_res.get("duration_seconds", 0.0), 2),
        },
    }
