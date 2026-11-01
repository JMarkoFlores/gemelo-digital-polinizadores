from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import pickle
import time
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from data_pipeline import FEATURE_COLUMNS, TARGET_COLUMNS

try:
    import tensorflow as tf
    from tensorflow import keras
except ImportError:
    tf = None
    keras = None

try:
    import streamlit as st
    import plotly.graph_objects as go
except ImportError:
    st = None
    go = None


def build_surrogate_model(input_dim: int, normalization_layer: Any) -> Any:
    if keras is None:
        raise RuntimeError("TensorFlow/Keras no disponible.")
    inputs = keras.Input(shape=(input_dim,), name="landscape_features")
    x = normalization_layer(inputs)
    x = keras.layers.Dense(64, activation="relu")(x)
    x = keras.layers.Dense(64, activation="relu")(x)
    x = keras.layers.Dropout(0.12)(x)
    x = keras.layers.Dense(32, activation="relu")(x)
    outputs = keras.layers.Dense(len(TARGET_COLUMNS), activation="linear", name="predictions")(x)
    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.0015), loss="mse", metrics=["mae"])
    return model


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for index, target in enumerate(TARGET_COLUMNS):
        target_true = y_true[:, index]
        target_pred = y_pred[:, index]
        metrics[target] = {
            "mae": float(mean_absolute_error(target_true, target_pred)),
            "rmse": float(np.sqrt(mean_squared_error(target_true, target_pred))),
            "r2": float(r2_score(target_true, target_pred)) if np.var(target_true) > 1e-12 else 0.0,
        }
    return metrics


def export_model_bundle(
    model: Any,
    export_dir: str | Path,
    metrics: dict[str, Any],
    target_scaler_mean: list[float],
    target_scaler_scale: list[float],
    model_type: str = "auto",
    scaler_x: Optional[Any] = None,
) -> dict[str, str]:
    """
    Exporta un bundle universal compatible tanto con Keras (.h5) como con modelos tradicionales (.pkl).
    Genera metadatos completos y compatibles con el backend y ModelStore.
    """
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    version = f"surrogate_{timestamp}"

    # Detección de tipo de modelo
    is_keras = hasattr(model, "save") and hasattr(model, "compile")
    if is_keras:
        detected_type = "dnn"
        model_filename = "modelo_optimizado.h5"
        model_path = export_path / model_filename
        model.save(str(model_path))
    else:
        detected_type = model_type if model_type != "auto" else "traditional"
        model_filename = f"model_{detected_type}.pkl"
        model_path = export_path / model_filename
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

    # Guardar escaladores pickle si existen
    if scaler_x is not None or target_scaler_mean:
        s_y = StandardScaler()
        s_y.mean_ = np.array(target_scaler_mean, dtype=np.float32)
        s_y.scale_ = np.array(target_scaler_scale, dtype=np.float32)
        s_y.var_ = s_y.scale_ ** 2
        with open(export_path / "scalers.pkl", "wb") as f:
            pickle.dump({"scaler_x": scaler_x, "scaler_y": s_y}, f)

    metadata = {
        "schema_version": "2.0_revision_metodologica",
        "version": version,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "model_type": detected_type,
        "model_filename": model_filename,
        "model_path": str(model_path),
        "feature_columns": FEATURE_COLUMNS,
        "target_columns": TARGET_COLUMNS,
        "metrics": metrics,
        "target_scaler_mean": target_scaler_mean,
        "target_scaler_scale": target_scaler_scale,
        "preprocessing_contract": {
            "scaler_x_applied": scaler_x is not None,
            "scaler_y_applied": True,
            "inverse_transform_required": True,
        },
    }

    metadata_path = export_path / "modelo_optimizado_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    bundle_meta_path = export_path / "bundle_metadata.json"
    bundle_meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "bundle_metadata_path": str(bundle_meta_path),
        "version": version,
        "model_type": detected_type,
    }
