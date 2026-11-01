from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.multioutput import MultiOutputRegressor

try:
    import xgboost as xgb
except ImportError:
    xgb = None

try:
    import tensorflow as tf
    from tensorflow import keras
except ImportError:
    tf = None
    keras = None

DEFAULT_HYPERPARAMS: dict[str, dict[str, Any]] = {
    "Random Forest (Tradicional)": {
        "n_estimators": 100,
        "max_depth": None,
        "min_samples_split": 2,
    },
    "XGBoost (Tradicional)": {
        "n_estimators": 100,
        "max_depth": 3,
        "learning_rate": 0.05,
    },
    "Ridge Regression (Tradicional)": {
        "alpha": 1.0,
    },
    "DNN Surrogate (Híbrido)": {
        "hidden_units": [64, 64, 32],
        "learning_rate": 0.0015,
        "dropout_rate": 0.12,
    },
    "Autoencoder+MLP (Híbrido)": {
        "latent_dim": 16,
        "regressor_units": 64,
        "learning_rate": 0.0010,
        "dropout_rate": 0.10,
    },
}


def build_custom_dnn_surrogate(
    input_dim: int,
    normalization_layer: Any,
    hidden_units: list[int] = (64, 64, 32),
    learning_rate: float = 0.0015,
    dropout_rate: float = 0.12,
    target_dim: int = 3,
) -> Any:
    if keras is None:
        raise RuntimeError("TensorFlow/Keras no está disponible en este entorno.")
    inputs = keras.Input(shape=(input_dim,), name="landscape_features")
    x = normalization_layer(inputs)
    for units in hidden_units:
        x = keras.layers.Dense(units, activation="relu")(x)
    if dropout_rate > 0:
        x = keras.layers.Dropout(dropout_rate)(x)
    outputs = keras.layers.Dense(target_dim, activation="linear", name="predictions")(x)
    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae"],
    )
    return model


def build_custom_autoencoder_mlp(
    input_dim: int,
    normalization_layer: Any,
    latent_dim: int = 16,
    regressor_units: int = 64,
    learning_rate: float = 0.0010,
    dropout_rate: float = 0.10,
    target_dim: int = 3,
) -> Any:
    """
    NOTA METODOLÓGICA (AUDITORÍA):
    Este modelo implementa un cuello de botella supervisado (bottleneck MLP), no un autoencoder
    con función de pérdida de reconstrucción no supervisada. La representación latente
    se optimiza de extremo a extremo mediante el error cuadrático en las salidas biofísicas.
    """
    if keras is None:
        raise RuntimeError("TensorFlow/Keras no está disponible en este entorno.")
    inputs = keras.Input(shape=(input_dim,), name="landscape_features")
    x = normalization_layer(inputs)
    # Cuello de botella
    encoded = keras.layers.Dense(max(32, latent_dim * 2), activation="relu")(x)
    encoded = keras.layers.Dense(latent_dim, activation="relu", name="latent_space")(encoded)
    # Regresor sobre características comprimidas
    x_reg = keras.layers.Dense(regressor_units, activation="relu")(encoded)
    if dropout_rate > 0:
        x_reg = keras.layers.Dropout(dropout_rate)(x_reg)
    outputs = keras.layers.Dense(target_dim, activation="linear", name="predictions")(x_reg)
    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae"],
    )
    return model


def tune_all_hyperparameters(
    X: np.ndarray,
    y: np.ndarray,
    y_scaled: np.ndarray,
    k_folds: int = 5,
    random_state: int = 42,
    status_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    start_total = time.time()
    cv_splits = min(max(3, k_folds), 5)
    tuning_records: list[dict[str, Any]] = []
    best_params_per_model: dict[str, dict[str, Any]] = {}
    summary_rows: list[dict[str, Any]] = []

    # 1. Random Forest
    if status_callback:
        status_callback("Sintonizando Random Forest...")
    t0 = time.time()
    rf_base = MultiOutputRegressor(RandomForestRegressor(random_state=random_state, n_jobs=1))
    rf_param_dist = {
        "estimator__n_estimators": [50, 100],
        "estimator__max_depth": [None, 6, 10],
        "estimator__min_samples_split": [2, 5],
    }
    search_rf = RandomizedSearchCV(
        rf_base,
        rf_param_dist,
        n_iter=4,
        cv=cv_splits,
        scoring="neg_mean_absolute_error",
        random_state=random_state,
        n_jobs=1,
    )
    search_rf.fit(X, y)
    t_rf = time.time() - t0
    rf_best = {
        "n_estimators": search_rf.best_params_["estimator__n_estimators"],
        "max_depth": search_rf.best_params_["estimator__max_depth"],
        "min_samples_split": search_rf.best_params_["estimator__min_samples_split"],
    }
    rf_score = float(-search_rf.best_score_)
    best_params_per_model["Random Forest (Tradicional)"] = rf_best
    tuning_records.extend([
        {"Modelo": "Random Forest (Tradicional)", "Hiperparámetro": "n_estimators", "Mejor Valor": str(rf_best["n_estimators"]), "Score CV Alcanzado": round(rf_score, 4), "Tiempo (s)": round(t_rf, 2)},
        {"Modelo": "Random Forest (Tradicional)", "Hiperparámetro": "max_depth", "Mejor Valor": str(rf_best["max_depth"]), "Score CV Alcanzado": round(rf_score, 4), "Tiempo (s)": round(t_rf, 2)},
    ])
    summary_rows.append({
        "Modelo": "Random Forest (Tradicional)",
        "Mejores Hiperparámetros": f"n_estimators={rf_best['n_estimators']}, max_depth={rf_best['max_depth']}",
        "Score CV (MAE)": round(rf_score, 4),
        "Tiempo Búsqueda": f"{t_rf:.2f}s",
    })

    # 2. Ridge Regression
    if status_callback:
        status_callback("Sintonizando Ridge Regression...")
    t0 = time.time()
    ridge_base = MultiOutputRegressor(Ridge())
    ridge_param_dist = {"estimator__alpha": [0.1, 1.0, 10.0, 50.0]}
    search_ridge = RandomizedSearchCV(
        ridge_base,
        ridge_param_dist,
        n_iter=4,
        cv=cv_splits,
        scoring="neg_mean_absolute_error",
        random_state=random_state,
        n_jobs=1,
    )
    search_ridge.fit(X, y)
    t_ridge = time.time() - t0
    ridge_best = {"alpha": search_ridge.best_params_["estimator__alpha"]}
    ridge_score = float(-search_ridge.best_score_)
    best_params_per_model["Ridge Regression (Tradicional)"] = ridge_best
    tuning_records.append(
        {"Modelo": "Ridge Regression (Tradicional)", "Hiperparámetro": "alpha", "Mejor Valor": str(ridge_best["alpha"]), "Score CV Alcanzado": round(ridge_score, 4), "Tiempo (s)": round(t_ridge, 2)}
    )
    summary_rows.append({
        "Modelo": "Ridge Regression (Tradicional)",
        "Mejores Hiperparámetros": f"alpha={ridge_best['alpha']}",
        "Score CV (MAE)": round(ridge_score, 4),
        "Tiempo Búsqueda": f"{t_ridge:.2f}s",
    })

    # 3. XGBoost si está instalado
    if xgb is not None:
        if status_callback:
            status_callback("Sintonizando XGBoost...")
        t0 = time.time()
        xgb_base = MultiOutputRegressor(xgb.XGBRegressor(random_state=random_state, n_jobs=1))
        xgb_param_dist = {
            "estimator__n_estimators": [50, 100],
            "estimator__max_depth": [3, 5],
            "estimator__learning_rate": [0.03, 0.05],
        }
        search_xgb = RandomizedSearchCV(
            xgb_base,
            xgb_param_dist,
            n_iter=4,
            cv=cv_splits,
            scoring="neg_mean_absolute_error",
            random_state=random_state,
            n_jobs=1,
        )
        search_xgb.fit(X, y)
        t_xgb = time.time() - t0
        xgb_best = {
            "n_estimators": search_xgb.best_params_["estimator__n_estimators"],
            "max_depth": search_xgb.best_params_["estimator__max_depth"],
            "learning_rate": search_xgb.best_params_["estimator__learning_rate"],
        }
        xgb_score = float(-search_xgb.best_score_)
        best_params_per_model["XGBoost (Tradicional)"] = xgb_best
        summary_rows.append({
            "Modelo": "XGBoost (Tradicional)",
            "Mejores Hiperparámetros": f"n_estimators={xgb_best['n_estimators']}, max_depth={xgb_best['max_depth']}, lr={xgb_best['learning_rate']}",
            "Score CV (MAE)": round(xgb_score, 4),
            "Tiempo Búsqueda": f"{t_xgb:.2f}s",
        })
    else:
        best_params_per_model["XGBoost (Tradicional)"] = DEFAULT_HYPERPARAMS["XGBoost (Tradicional)"]

    # 4. DNN y Autoencoder si TensorFlow está disponible
    if tf is not None and keras is not None:
        X_tr_sub, X_val_sub, y_tr_sub, y_val_sub = train_test_split(
            X, y_scaled, test_size=0.2, random_state=random_state
        )
        norm_sub = keras.layers.Normalization(axis=-1)
        norm_sub.adapt(X_tr_sub)

        # DNN
        dnn_candidates = [
            {"hidden_units": [64, 64, 32], "learning_rate": 0.0015, "dropout_rate": 0.12},
            {"hidden_units": [128, 64, 32], "learning_rate": 0.0010, "dropout_rate": 0.10},
        ]
        best_dnn_score = float("inf")
        best_dnn_cfg = dnn_candidates[0]
        for cfg in dnn_candidates:
            tf.keras.utils.set_random_seed(random_state)
            model_dnn = build_custom_dnn_surrogate(
                input_dim=X.shape[1],
                normalization_layer=norm_sub,
                hidden_units=cfg["hidden_units"],
                learning_rate=cfg["learning_rate"],
                dropout_rate=cfg["dropout_rate"],
                target_dim=y.shape[1],
            )
            early_stop = keras.callbacks.EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True)
            model_dnn.fit(
                X_tr_sub, y_tr_sub,
                validation_data=(X_val_sub, y_val_sub),
                epochs=15, batch_size=24, verbose=0, callbacks=[early_stop]
            )
            preds = model_dnn.predict(X_val_sub, verbose=0)
            score = float(np.mean([mean_absolute_error(y_val_sub[:, i], preds[:, i]) for i in range(y_val_sub.shape[1])]))
            if score < best_dnn_score:
                best_dnn_score = score
                best_dnn_cfg = cfg
        best_params_per_model["DNN Surrogate (Híbrido)"] = best_dnn_cfg

        # Autoencoder / Bottleneck
        ae_candidates = [
            {"latent_dim": 16, "regressor_units": 64, "learning_rate": 0.0010, "dropout_rate": 0.10},
            {"latent_dim": 8, "regressor_units": 32, "learning_rate": 0.0015, "dropout_rate": 0.12},
        ]
        best_ae_score = float("inf")
        best_ae_cfg = ae_candidates[0]
        for cfg in ae_candidates:
            tf.keras.utils.set_random_seed(random_state)
            model_ae = build_custom_autoencoder_mlp(
                input_dim=X.shape[1],
                normalization_layer=norm_sub,
                latent_dim=cfg["latent_dim"],
                regressor_units=cfg["regressor_units"],
                learning_rate=cfg["learning_rate"],
                dropout_rate=cfg["dropout_rate"],
                target_dim=y.shape[1],
            )
            early_stop = keras.callbacks.EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True)
            model_ae.fit(
                X_tr_sub, y_tr_sub,
                validation_data=(X_val_sub, y_val_sub),
                epochs=15, batch_size=24, verbose=0, callbacks=[early_stop]
            )
            preds = model_ae.predict(X_val_sub, verbose=0)
            score = float(np.mean([mean_absolute_error(y_val_sub[:, i], preds[:, i]) for i in range(y_val_sub.shape[1])]))
            if score < best_ae_score:
                best_ae_score = score
                best_ae_cfg = cfg
        best_params_per_model["Autoencoder+MLP (Híbrido)"] = best_ae_cfg
    else:
        best_params_per_model["DNN Surrogate (Híbrido)"] = DEFAULT_HYPERPARAMS["DNN Surrogate (Híbrido)"]
        best_params_per_model["Autoencoder+MLP (Híbrido)"] = DEFAULT_HYPERPARAMS["Autoencoder+MLP (Híbrido)"]

    total_tuning_time = time.time() - start_total
    tuning_df = pd.DataFrame(tuning_records)
    summary_df = pd.DataFrame(summary_rows)

    interpretation = (
        "Sintonización de hiperparámetros ejecutada respetando la métrica MAE. "
        "Las arquitecturas de red neuronal implementan un cuello de botella supervisado; "
        "los hiperparámetros seleccionados se transfieren a los evaluadores correspondientes."
    )

    return {
        "best_params_per_model": best_params_per_model,
        "tuning_df": tuning_df,
        "summary_df": summary_df,
        "interpretation": interpretation,
        "total_tuning_time": total_tuning_time,
    }
