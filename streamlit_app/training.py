from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import tensorflow as tf
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow import keras

from data_pipeline import FEATURE_COLUMNS, TARGET_COLUMNS


class StreamlitTrainingCallback(keras.callbacks.Callback):
    def __init__(self, progress_bar, status_placeholder, chart_placeholder, total_epochs: int) -> None:
        super().__init__()
        self.progress_bar = progress_bar
        self.status_placeholder = status_placeholder
        self.chart_placeholder = chart_placeholder
        self.total_epochs = total_epochs
        self.history_rows: list[dict[str, float]] = []

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        self.history_rows.append(
            {
                "epoch": epoch + 1,
                "loss": float(logs.get("loss", 0.0)),
                "val_loss": float(logs.get("val_loss", 0.0)),
                "mae": float(logs.get("mae", 0.0)),
                "val_mae": float(logs.get("val_mae", 0.0)),
            }
        )
        self.progress_bar.progress((epoch + 1) / self.total_epochs)
        self.status_placeholder.caption(
            f"Epoca {epoch + 1}/{self.total_epochs} | loss={logs.get('loss', 0.0):.4f} | val_mae={logs.get('val_mae', 0.0):.4f}"
        )

        chart_df = pd.DataFrame(self.history_rows)
        figure = go.Figure()
        figure.add_scatter(x=chart_df["epoch"], y=chart_df["loss"], mode="lines+markers", name="Loss")
        figure.add_scatter(x=chart_df["epoch"], y=chart_df["val_loss"], mode="lines+markers", name="Val Loss")
        figure.add_scatter(x=chart_df["epoch"], y=chart_df["mae"], mode="lines", name="MAE", yaxis="y2")
        figure.add_scatter(x=chart_df["epoch"], y=chart_df["val_mae"], mode="lines", name="Val MAE", yaxis="y2")
        figure.update_layout(
            height=360,
            margin=dict(l=0, r=0, t=24, b=0),
            template="plotly_white",
            yaxis=dict(title="Loss"),
            yaxis2=dict(title="MAE", overlaying="y", side="right"),
        )
        self.chart_placeholder.plotly_chart(figure, use_container_width=True)


def build_surrogate_model(input_dim: int, normalization_layer: keras.layers.Layer) -> keras.Model:
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
            "r2": float(r2_score(target_true, target_pred)),
        }
    return metrics


def train_surrogate_model(
    dataframe: pd.DataFrame,
    progress_bar,
    status_placeholder,
    chart_placeholder,
    epochs: int = 30,
    batch_size: int = 24,
    random_state: int = 42,
) -> dict[str, object]:
    tf.keras.utils.set_random_seed(random_state)

    X = dataframe[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = dataframe[TARGET_COLUMNS].to_numpy(dtype=np.float32)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=random_state)
    X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.2, random_state=random_state)

    target_scaler = StandardScaler()
    y_train_scaled = target_scaler.fit_transform(y_train)
    y_val_scaled = target_scaler.transform(y_val)

    normalization = keras.layers.Normalization(axis=-1)
    normalization.adapt(X_train)

    model = build_surrogate_model(X.shape[1], normalization)
    callback = StreamlitTrainingCallback(progress_bar, status_placeholder, chart_placeholder, epochs)
    early_stopping = keras.callbacks.EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)

    start = time.perf_counter()
    history = model.fit(
        X_train,
        y_train_scaled,
        validation_data=(X_val, y_val_scaled),
        epochs=epochs,
        batch_size=batch_size,
        verbose=0,
        callbacks=[callback, early_stopping],
    )
    duration = time.perf_counter() - start

    predictions_scaled = model.predict(X_test, verbose=0)
    predictions = target_scaler.inverse_transform(predictions_scaled)
    metrics = evaluate_predictions(y_test, predictions)

    return {
        "model": model,
        "history": history.history,
        "metrics": metrics,
        "duration_seconds": duration,
        "x_test": X_test,
        "y_test": y_test,
        "predictions": predictions,
        "target_scaler_mean": target_scaler.mean_.tolist(),
        "target_scaler_scale": target_scaler.scale_.tolist(),
        "trained_at": datetime.utcnow().isoformat(),
    }


def export_model_bundle(
    model: keras.Model,
    export_dir: str | Path,
    metrics: dict[str, dict[str, float]],
    target_scaler_mean: list[float],
    target_scaler_scale: list[float],
) -> dict[str, str]:
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    model_path = export_path / "modelo_optimizado.h5"
    metadata_path = export_path / "modelo_optimizado_metadata.json"
    version = f"surrogate_{timestamp}"

    model.save(model_path)
    metadata = {
        "version": version,
        "saved_at": datetime.utcnow().isoformat(),
        "model_path": str(model_path),
        "feature_columns": FEATURE_COLUMNS,
        "target_columns": TARGET_COLUMNS,
        "metrics": metrics,
        "target_scaler_mean": target_scaler_mean,
        "target_scaler_scale": target_scaler_scale,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "version": version,
    }
