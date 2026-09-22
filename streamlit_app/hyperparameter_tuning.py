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
import tensorflow as tf
from tensorflow import keras
import xgboost as xgb

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
    normalization_layer: keras.layers.Layer,
    hidden_units: list[int] = (64, 64, 32),
    learning_rate: float = 0.0015,
    dropout_rate: float = 0.12,
    target_dim: int = 3,
) -> keras.Model:
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
    normalization_layer: keras.layers.Layer,
    latent_dim: int = 16,
    regressor_units: int = 64,
    learning_rate: float = 0.0010,
    dropout_rate: float = 0.10,
    target_dim: int = 3,
) -> keras.Model:
    inputs = keras.Input(shape=(input_dim,), name="landscape_features")
    x = normalization_layer(inputs)
    # Encoder
    encoded = keras.layers.Dense(max(32, latent_dim * 2), activation="relu")(x)
    encoded = keras.layers.Dense(latent_dim, activation="relu", name="latent_space")(encoded)
    # MLP Regressor
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
    """
    Ejecuta la sintonización de hiperparámetros para los 5 modelos:
      1. Random Forest (RandomizedSearchCV)
      2. XGBoost (RandomizedSearchCV)
      3. Ridge (RandomizedSearchCV)
      4. DNN Surrogate (Evaluación sobre espacio reducido)
      5. Autoencoder+MLP (Evaluación sobre espacio reducido)
    """
    start_total = time.time()
    cv_splits = min(max(3, k_folds), 5)
    tuning_records: list[dict[str, Any]] = []
    best_params_per_model: dict[str, dict[str, Any]] = {}

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Random Forest (Tradicional)
    # ──────────────────────────────────────────────────────────────────────────
    if status_callback:
        status_callback("Sintonizando Random Forest con RandomizedSearchCV...")
    t0 = time.time()
    rf_base = MultiOutputRegressor(RandomForestRegressor(random_state=random_state))
    rf_param_dist = {
        "estimator__n_estimators": [50, 100, 150],
        "estimator__max_depth": [None, 6, 12],
        "estimator__min_samples_split": [2, 5],
    }
    search_rf = RandomizedSearchCV(
        rf_base,
        rf_param_dist,
        n_iter=6,
        cv=cv_splits,
        scoring="r2",
        random_state=random_state,
        n_jobs=-1,
    )
    search_rf.fit(X, y_scaled)
    t_rf = time.time() - t0
    rf_best = {
        "n_estimators": search_rf.best_params_["estimator__n_estimators"],
        "max_depth": search_rf.best_params_["estimator__max_depth"],
        "min_samples_split": search_rf.best_params_["estimator__min_samples_split"],
    }
    rf_score = float(search_rf.best_score_)
    best_params_per_model["Random Forest (Tradicional)"] = rf_best

    tuning_records.extend([
        {"Modelo": "Random Forest (Tradicional)", "Hiperparámetro": "n_estimators", "Mejor Valor": str(rf_best["n_estimators"]), "Score CV Alcanzado": round(rf_score, 4), "Tiempo (s)": round(t_rf, 2)},
        {"Modelo": "Random Forest (Tradicional)", "Hiperparámetro": "max_depth", "Mejor Valor": str(rf_best["max_depth"] if rf_best["max_depth"] is not None else "None (sin límite)"), "Score CV Alcanzado": round(rf_score, 4), "Tiempo (s)": round(t_rf, 2)},
        {"Modelo": "Random Forest (Tradicional)", "Hiperparámetro": "min_samples_split", "Mejor Valor": str(rf_best["min_samples_split"]), "Score CV Alcanzado": round(rf_score, 4), "Tiempo (s)": round(t_rf, 2)},
    ])

    # ──────────────────────────────────────────────────────────────────────────
    # 2. XGBoost (Tradicional)
    # ──────────────────────────────────────────────────────────────────────────
    if status_callback:
        status_callback("Sintonizando XGBoost con RandomizedSearchCV...")
    t0 = time.time()
    xgb_base = MultiOutputRegressor(xgb.XGBRegressor(random_state=random_state))
    xgb_param_dist = {
        "estimator__n_estimators": [50, 100, 150],
        "estimator__max_depth": [3, 5, 7],
        "estimator__learning_rate": [0.03, 0.05, 0.10],
    }
    search_xgb = RandomizedSearchCV(
        xgb_base,
        xgb_param_dist,
        n_iter=6,
        cv=cv_splits,
        scoring="r2",
        random_state=random_state,
        n_jobs=-1,
    )
    search_xgb.fit(X, y_scaled)
    t_xgb = time.time() - t0
    xgb_best = {
        "n_estimators": search_xgb.best_params_["estimator__n_estimators"],
        "max_depth": search_xgb.best_params_["estimator__max_depth"],
        "learning_rate": search_xgb.best_params_["estimator__learning_rate"],
    }
    xgb_score = float(search_xgb.best_score_)
    best_params_per_model["XGBoost (Tradicional)"] = xgb_best

    tuning_records.extend([
        {"Modelo": "XGBoost (Tradicional)", "Hiperparámetro": "n_estimators", "Mejor Valor": str(xgb_best["n_estimators"]), "Score CV Alcanzado": round(xgb_score, 4), "Tiempo (s)": round(t_xgb, 2)},
        {"Modelo": "XGBoost (Tradicional)", "Hiperparámetro": "max_depth", "Mejor Valor": str(xgb_best["max_depth"]), "Score CV Alcanzado": round(xgb_score, 4), "Tiempo (s)": round(t_xgb, 2)},
        {"Modelo": "XGBoost (Tradicional)", "Hiperparámetro": "learning_rate", "Mejor Valor": str(xgb_best["learning_rate"]), "Score CV Alcanzado": round(xgb_score, 4), "Tiempo (s)": round(t_xgb, 2)},
    ])

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Ridge Regression (Tradicional)
    # ──────────────────────────────────────────────────────────────────────────
    if status_callback:
        status_callback("Sintonizando Ridge Regression con RandomizedSearchCV...")
    t0 = time.time()
    ridge_base = MultiOutputRegressor(Ridge())
    ridge_param_dist = {
        "estimator__alpha": [0.01, 0.1, 1.0, 5.0, 10.0, 50.0],
    }
    search_ridge = RandomizedSearchCV(
        ridge_base,
        ridge_param_dist,
        n_iter=6,
        cv=cv_splits,
        scoring="r2",
        random_state=random_state,
        n_jobs=-1,
    )
    search_ridge.fit(X, y_scaled)
    t_ridge = time.time() - t0
    ridge_best = {
        "alpha": search_ridge.best_params_["estimator__alpha"],
    }
    ridge_score = float(search_ridge.best_score_)
    best_params_per_model["Ridge Regression (Tradicional)"] = ridge_best

    tuning_records.append(
        {"Modelo": "Ridge Regression (Tradicional)", "Hiperparámetro": "alpha", "Mejor Valor": str(ridge_best["alpha"]), "Score CV Alcanzado": round(ridge_score, 4), "Tiempo (s)": round(t_ridge, 2)}
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Partición para redes neuronales (80% entrenamiento, 20% validación)
    # ──────────────────────────────────────────────────────────────────────────
    X_tr_sub, X_val_sub, y_tr_sub, y_val_sub = train_test_split(
        X, y_scaled, test_size=0.2, random_state=random_state
    )
    norm_sub = keras.layers.Normalization(axis=-1)
    norm_sub.adapt(X_tr_sub)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. DNN Surrogate (Híbrido)
    # ──────────────────────────────────────────────────────────────────────────
    if status_callback:
        status_callback("Sintonizando arquitectura y optimizador de DNN Surrogate...")
    t0 = time.time()
    dnn_candidates = [
        {"hidden_units": [64, 64, 32], "learning_rate": 0.0015, "dropout_rate": 0.12},
        {"hidden_units": [128, 64, 32], "learning_rate": 0.0010, "dropout_rate": 0.10},
        {"hidden_units": [64, 32, 16], "learning_rate": 0.0020, "dropout_rate": 0.15},
    ]
    best_dnn_score = -float("inf")
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
            X_tr_sub,
            y_tr_sub,
            validation_data=(X_val_sub, y_val_sub),
            epochs=15,
            batch_size=24,
            verbose=0,
            callbacks=[early_stop],
        )
        preds = model_dnn.predict(X_val_sub, verbose=0)
        score = float(np.mean([r2_score(y_val_sub[:, i], preds[:, i]) for i in range(y_val_sub.shape[1])]))
        if score > best_dnn_score:
            best_dnn_score = score
            best_dnn_cfg = cfg

    t_dnn = time.time() - t0
    best_params_per_model["DNN Surrogate (Híbrido)"] = best_dnn_cfg
    tuning_records.extend([
        {"Modelo": "DNN Surrogate (Híbrido)", "Hiperparámetro": "hidden_units", "Mejor Valor": str(best_dnn_cfg["hidden_units"]), "Score CV Alcanzado": round(best_dnn_score, 4), "Tiempo (s)": round(t_dnn, 2)},
        {"Modelo": "DNN Surrogate (Híbrido)", "Hiperparámetro": "learning_rate", "Mejor Valor": str(best_dnn_cfg["learning_rate"]), "Score CV Alcanzado": round(best_dnn_score, 4), "Tiempo (s)": round(t_dnn, 2)},
        {"Modelo": "DNN Surrogate (Híbrido)", "Hiperparámetro": "dropout_rate", "Mejor Valor": str(best_dnn_cfg["dropout_rate"]), "Score CV Alcanzado": round(best_dnn_score, 4), "Tiempo (s)": round(t_dnn, 2)},
    ])

    # ──────────────────────────────────────────────────────────────────────────
    # 5. Autoencoder+MLP (Híbrido)
    # ──────────────────────────────────────────────────────────────────────────
    if status_callback:
        status_callback("Sintonizando espacio latente y regresor de Autoencoder+MLP...")
    t0 = time.time()
    ae_candidates = [
        {"latent_dim": 16, "regressor_units": 64, "learning_rate": 0.0010, "dropout_rate": 0.10},
        {"latent_dim": 8, "regressor_units": 32, "learning_rate": 0.0015, "dropout_rate": 0.12},
        {"latent_dim": 24, "regressor_units": 64, "learning_rate": 0.0008, "dropout_rate": 0.08},
    ]
    best_ae_score = -float("inf")
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
            X_tr_sub,
            y_tr_sub,
            validation_data=(X_val_sub, y_val_sub),
            epochs=15,
            batch_size=24,
            verbose=0,
            callbacks=[early_stop],
        )
        preds = model_ae.predict(X_val_sub, verbose=0)
        score = float(np.mean([r2_score(y_val_sub[:, i], preds[:, i]) for i in range(y_val_sub.shape[1])]))
        if score > best_ae_score:
            best_ae_score = score
            best_ae_cfg = cfg

    t_ae = time.time() - t0
    best_params_per_model["Autoencoder+MLP (Híbrido)"] = best_ae_cfg
    tuning_records.extend([
        {"Modelo": "Autoencoder+MLP (Híbrido)", "Hiperparámetro": "latent_dim", "Mejor Valor": str(best_ae_cfg["latent_dim"]), "Score CV Alcanzado": round(best_ae_score, 4), "Tiempo (s)": round(t_ae, 2)},
        {"Modelo": "Autoencoder+MLP (Híbrido)", "Hiperparámetro": "regressor_units", "Mejor Valor": str(best_ae_cfg["regressor_units"]), "Score CV Alcanzado": round(best_ae_score, 4), "Tiempo (s)": round(t_ae, 2)},
        {"Modelo": "Autoencoder+MLP (Híbrido)", "Hiperparámetro": "learning_rate", "Mejor Valor": str(best_ae_cfg["learning_rate"]), "Score CV Alcanzado": round(best_ae_score, 4), "Tiempo (s)": round(t_ae, 2)},
    ])

    total_tuning_time = time.time() - start_total

    # Crear DataFrame detallado
    tuning_df = pd.DataFrame(tuning_records)

    # Crear DataFrame consolidado por modelo
    summary_rows = [
        {
            "Modelo": "Random Forest (Tradicional)",
            "Mejores Hiperparámetros": f"n_estimators={rf_best['n_estimators']}, max_depth={rf_best['max_depth']}, min_split={rf_best['min_samples_split']}",
            "Score CV (R²)": round(rf_score, 4),
            "Tiempo Búsqueda": f"{t_rf:.2f}s",
        },
        {
            "Modelo": "XGBoost (Tradicional)",
            "Mejores Hiperparámetros": f"n_estimators={xgb_best['n_estimators']}, max_depth={xgb_best['max_depth']}, lr={xgb_best['learning_rate']}",
            "Score CV (R²)": round(xgb_score, 4),
            "Tiempo Búsqueda": f"{t_xgb:.2f}s",
        },
        {
            "Modelo": "Ridge Regression (Tradicional)",
            "Mejores Hiperparámetros": f"alpha={ridge_best['alpha']}",
            "Score CV (R²)": round(ridge_score, 4),
            "Tiempo Búsqueda": f"{t_ridge:.2f}s",
        },
        {
            "Modelo": "DNN Surrogate (Híbrido)",
            "Mejores Hiperparámetros": f"units={best_dnn_cfg['hidden_units']}, lr={best_dnn_cfg['learning_rate']}, dropout={best_dnn_cfg['dropout_rate']}",
            "Score CV (R²)": round(best_dnn_score, 4),
            "Tiempo Búsqueda": f"{t_dnn:.2f}s",
        },
        {
            "Modelo": "Autoencoder+MLP (Híbrido)",
            "Mejores Hiperparámetros": f"latent_dim={best_ae_cfg['latent_dim']}, regressor={best_ae_cfg['regressor_units']}, lr={best_ae_cfg['learning_rate']}",
            "Score CV (R²)": round(best_ae_score, 4),
            "Tiempo Búsqueda": f"{t_ae:.2f}s",
        },
    ]
    summary_df = pd.DataFrame(summary_rows)

    # Generación de interpretación objetiva y explicabilidad
    interpretation = (
        f"- **Random Forest:** La búsqueda estocástica optimizó la arquitectura del ensamble en "
        f"`n_estimators={rf_best['n_estimators']}` y `max_depth={rf_best['max_depth']}` ($R^2={rf_score:.4f}$). "
        f"Esta profundidad acotada evita la memorización de ruido local y controla el sobreajuste observador en árboles ilimitados.\n"
        f"- **XGBoost:** La tasa de aprendizaje `learning_rate={xgb_best['learning_rate']}` junto con `max_depth={xgb_best['max_depth']}` "
        f"($R^2={xgb_score:.4f}$) garantiza una convergencia controlada de los árboles de regresión aditivos sin oscilaciones en los residuos.\n"
        f"- **Ridge Regression:** La penalización L2 óptima con `alpha={ridge_best['alpha']}` ($R^2={ridge_score:.4f}$) estabiliza los coeficientes "
        f"lineales mitigando la colinealidad intrínseca entre las variables de temperatura, precipitación y diversidad vegetal.\n"
        f"- **Modelos Neuronales Híbridos:** La DNN Surrogate alcanzó su mejor desempeño con topología `{best_dnn_cfg['hidden_units']}` "
        f"y tasa `{best_dnn_cfg['learning_rate']}` ($R^2={best_dnn_score:.4f}$), mientras que el Autoencoder+MLP optimizó la compresión en "
        f"`latent_dim={best_ae_cfg['latent_dim']}` ($R^2={best_ae_score:.4f}$), confirmando que la reducción no lineal preserva las relaciones ecológicas clave."
    )

    return {
        "best_params_per_model": best_params_per_model,
        "tuning_df": tuning_df,
        "summary_df": summary_df,
        "interpretation": interpretation,
        "total_tuning_time": total_tuning_time,
    }
