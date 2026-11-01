"""
scientific_core/nested_cv.py
Motor de Evaluación Predictiva sin Contaminación (Nested Cross-Validation).
Protocolo Científico:
  1. Outer CV (K=5): Divide el dataset en K particiones de prueba disjuntas.
  2. GroupKFold automático si group_duplicates=True: Agrupa instancias con características
     idénticas en el mismo fold para evitar fuga por duplicados.
  3. Preprocesamiento estricto: Escalado (StandardScaler) ajustado exclusivamente
     con los datos de entrenamiento permitidos de cada partición.
  4. Redes Neuronales (DNN y Bottleneck MLP):
     - Subpartición de monitorización separada del fold de validación que puntúa candidatos.
     - EarlyStopping evaluando exclusivamente sobre la partición de monitorización.
     - Reajuste sobre todo el entrenamiento del fold externo con política de épocas
       derivada de los folds internos.
     - Normalización transparente de hiperparámetros (layers/hidden_units, dropout/dropout_rate,
       bottleneck_dim/latent_dim, decoder_units/regressor_units).
     - Medición real de tiempos de entrenamiento e inferencia (sin valores arbitrarios).
  5. Criterio de Selección: MAE Macro en escala original de las 3 salidas.
  6. Out-of-Fold (OOF): Exactamente 1 predicción por fila para cada modelo evaluado.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from scientific_core.contracts import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    compute_macro_metrics,
    compute_target_metrics,
)

logger = logging.getLogger(__name__)

# Intentar imports opcionales de librerías pesadas
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


def compute_feature_groups(X: np.ndarray, precision_decimals: int = 4) -> np.ndarray:
    """
    Asigna un identificador de grupo entero único a cada vector de características idéntico
    redondeado a precision_decimals. Permite GroupKFold para evitar fuga por duplicados (Mandato 5).
    """
    X_rounded = np.round(X, decimals=precision_decimals)
    group_map: Dict[bytes, int] = {}
    groups = np.zeros(len(X), dtype=int)
    current_group_id = 0

    for i, row in enumerate(X_rounded):
        row_bytes = row.tobytes()
        if row_bytes not in group_map:
            group_map[row_bytes] = current_group_id
            current_group_id += 1
        groups[i] = group_map[row_bytes]

    return groups


class ModelFactory:
    """Fábrica de modelos sustitutos tradicionales (Ridge, Random Forest, XGBoost)."""

    @staticmethod
    def create_model(model_family: str, params: Dict[str, Any], seed: int = 42, **kwargs) -> Any:
        clean_params = dict(params)
        clean_params.pop("max_epochs", None)
        clean_params.pop("batch_size", None)
        clean_params.pop("early_stopping_patience", None)
        clean_params.pop("patience", None)
        clean_params.pop("internal_monitor_val_split", None)
        effective_seed = kwargs.get("random_state", seed)

        if model_family == "ridge":
            alpha = float(clean_params.get("alpha", 1.0))
            return Ridge(alpha=alpha, random_state=effective_seed)

        elif model_family == "random_forest":
            rf_params = {
                "n_estimators": int(clean_params.get("n_estimators", 100)),
                "max_depth": clean_params.get("max_depth", None),
                "min_samples_split": int(clean_params.get("min_samples_split", 2)),
                "random_state": effective_seed,
                "n_jobs": 1,
            }
            if rf_params["max_depth"] is not None:
                rf_params["max_depth"] = int(rf_params["max_depth"])
            return RandomForestRegressor(**rf_params)

        elif model_family == "xgboost":
            if xgb is None:
                raise RuntimeError("XGBoost no está instalado.")
            xgb_params = {
                "n_estimators": int(clean_params.get("n_estimators", 100)),
                "max_depth": int(clean_params.get("max_depth", 4)),
                "learning_rate": float(clean_params.get("learning_rate", 0.05)),
                "random_state": effective_seed,
                "n_jobs": 1,
            }
            return xgb.XGBRegressor(**xgb_params)

        else:
            raise ValueError(f"Familia de modelo tradicional desconocida: {model_family}")


def normalize_neural_params(params: Dict[str, Any], model_family: str) -> Dict[str, Any]:
    """
    Unifica el esquema de hiperparámetros neuronales entre JSON, código y metadatos (Bloque 4).
    Mapea de forma bidireccional:
      - hidden_units <-> layers
      - dropout_rate <-> dropout
      - latent_dim <-> bottleneck_dim
      - regressor_units <-> decoder_units
    """
    norm = dict(params)

    # 1. Capas y unidades
    if "hidden_units" in norm and "layers" not in norm:
        norm["layers"] = list(norm["hidden_units"])
    elif "layers" in norm and "hidden_units" not in norm:
        norm["hidden_units"] = list(norm["layers"])
    elif "layers" not in norm and "hidden_units" not in norm:
        norm["layers"] = [64, 32]
        norm["hidden_units"] = [64, 32]

    # 2. Dropout
    if "dropout_rate" in norm and "dropout" not in norm:
        norm["dropout"] = float(norm["dropout_rate"])
    elif "dropout" in norm and "dropout_rate" not in norm:
        norm["dropout_rate"] = float(norm["dropout"])
    elif "dropout" not in norm and "dropout_rate" not in norm:
        norm["dropout"] = 0.1
        norm["dropout_rate"] = 0.1

    # 3. Cuello de botella / Autoencoder MLP
    if model_family == "autoencoder_mlp":
        if "latent_dim" in norm and "bottleneck_dim" not in norm:
            norm["bottleneck_dim"] = int(norm["latent_dim"])
        elif "bottleneck_dim" in norm and "latent_dim" not in norm:
            norm["latent_dim"] = int(norm["bottleneck_dim"])
        elif "bottleneck_dim" not in norm and "latent_dim" not in norm:
            norm["bottleneck_dim"] = 8
            norm["latent_dim"] = 8

        if "regressor_units" in norm:
            ru = norm["regressor_units"]
            norm["decoder_units"] = [ru] if isinstance(ru, int) else list(ru)
        elif "decoder_units" not in norm:
            norm["decoder_units"] = [32]

        if "encoder_units" not in norm:
            norm["encoder_units"] = [64, 32]

    # 4. Épocas, batch size, paciencia y regularización
    patience = norm.get("early_stopping_patience", norm.get("patience", 10))
    norm["early_stopping_patience"] = int(patience)
    norm["patience"] = int(patience)
    norm["max_epochs"] = int(norm.get("max_epochs", 100))
    norm["batch_size"] = int(norm.get("batch_size", 32))
    norm["learning_rate"] = float(norm.get("learning_rate", 0.001))
    norm["l2_reg"] = float(norm.get("l2_reg", 1e-4))
    norm["internal_monitor_val_split"] = float(norm.get("internal_monitor_val_split", 0.20))

    return norm


def build_keras_neural_model(
    model_family: str,
    params: Dict[str, Any],
    input_dim: int,
    output_dim: int,
    seed: int = 42,
) -> Any:
    """
    Construye y compila una instancia limpia de Keras para DNN o Autoencoder/Bottleneck MLP.
    Aplica rigurosamente la arquitectura especificada en params (Bloque 4).
    """
    if tf is None or keras is None:
        raise RuntimeError("TensorFlow/Keras no está disponible.")

    norm_params = normalize_neural_params(params, model_family)
    tf.keras.utils.set_random_seed(seed)
    lr = float(norm_params["learning_rate"])
    dropout = float(norm_params["dropout"])
    l2_reg = float(norm_params["l2_reg"])

    if model_family == "dnn":
        layers_units = norm_params["layers"]
        inputs = keras.layers.Input(shape=(input_dim,), name="features_in")
        x = inputs
        for i, units in enumerate(layers_units):
            x = keras.layers.Dense(
                units,
                activation="relu",
                kernel_regularizer=keras.regularizers.l2(l2_reg),
                name=f"dnn_dense_{i}",
            )(x)
            if dropout > 0.0:
                x = keras.layers.Dropout(dropout, seed=seed + i, name=f"dnn_drop_{i}")(x)
        outputs = keras.layers.Dense(output_dim, activation="linear", name="targets_out")(x)
        model = keras.Model(inputs=inputs, outputs=outputs, name="dnn_surrogate")
        model.compile(optimizer=keras.optimizers.Adam(learning_rate=lr), loss="mse", metrics=["mae"])
        return model

    elif model_family == "autoencoder_mlp":
        # Modelo cuello de botella supervisado (Bottleneck MLP)
        enc_units = norm_params["encoder_units"]
        bottleneck_dim = norm_params["bottleneck_dim"]
        dec_units = norm_params["decoder_units"]

        inputs = keras.layers.Input(shape=(input_dim,), name="features_in")
        x = inputs
        for i, u in enumerate(enc_units):
            x = keras.layers.Dense(
                u,
                activation="relu",
                kernel_regularizer=keras.regularizers.l2(l2_reg),
                name=f"enc_dense_{i}",
            )(x)
        bottleneck = keras.layers.Dense(
            bottleneck_dim,
            activation="relu",
            name="bottleneck_repr",
        )(x)
        x = bottleneck
        for i, u in enumerate(dec_units):
            x = keras.layers.Dense(
                u,
                activation="relu",
                kernel_regularizer=keras.regularizers.l2(l2_reg),
                name=f"dec_dense_{i}",
            )(x)
        if dropout > 0.0:
            x = keras.layers.Dropout(dropout, seed=seed + 99, name="dec_drop")(x)
        outputs = keras.layers.Dense(output_dim, activation="linear", name="targets_out")(x)
        model = keras.Model(inputs=inputs, outputs=outputs, name="bottleneck_mlp_surrogate")
        model.compile(optimizer=keras.optimizers.Adam(learning_rate=lr), loss="mse", metrics=["mae"])
        return model

    else:
        raise ValueError(f"Familia neuronal no soportada: {model_family}")


def fit_and_predict_traditional(
    model: Any,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
) -> Tuple[np.ndarray, StandardScaler, StandardScaler]:
    """
    Ajusta escalador de entrada y salida ÚNICAMENTE sobre X_train e y_train.
    Retorna predicciones en escala original de y, junto con los escaladores ajustados.
    """
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()

    X_train_s = scaler_x.fit_transform(X_train)
    y_train_s = scaler_y.fit_transform(y_train)

    model.fit(X_train_s, y_train_s)

    X_val_s = scaler_x.transform(X_val)
    preds_scaled = model.predict(X_val_s)
    preds = scaler_y.inverse_transform(preds_scaled)

    return preds, scaler_x, scaler_y


def fit_and_predict_neural_inner(
    model_family: str,
    params: Dict[str, Any],
    X_in_tr: np.ndarray,
    y_in_tr: np.ndarray,
    X_in_val: np.ndarray,
    groups_in_tr: Optional[np.ndarray] = None,
    seed: int = 42,
) -> Tuple[np.ndarray, int]:
    """
    Entrena red neuronal en fold interno con:
      - Subpartición de monitorización separada del fold de validación que puntúa candidatos (X_in_val).
      - Escaladores ajustados exclusivamente en core_train (sin monitor ni validación).
      - EarlyStopping evaluando exclusivamente sobre la subpartición de monitorización.
      - Falla con error informativo si group_duplicates genera menos grupos que los requeridos (Bloque 4).
      - Retorna (predicciones en escala original sobre X_in_val, época óptima alcanzada).
    """
    norm_params = normalize_neural_params(params, model_family)
    n_samples = len(X_in_tr)
    val_split = norm_params["internal_monitor_val_split"]

    # Partición core_train / monitor respetando grupos
    if groups_in_tr is not None:
        unique_groups = np.unique(groups_in_tr)
        if len(unique_groups) < 2:
            raise ValueError(
                f"La división de monitorización interna requiere al menos 2 grupos disjuntos cuando "
                f"'group_duplicates' está activo, pero solo se encontraron {len(unique_groups)} grupos. "
                f"Verifique la variabilidad del conjunto de entrenamiento interno."
            )
        rng = np.random.default_rng(seed)
        shuffled_groups = rng.permutation(unique_groups)
        n_mon_groups = max(1, int(len(unique_groups) * val_split))
        mon_group_set = set(shuffled_groups[:n_mon_groups])
        core_idx = np.array([i for i, g in enumerate(groups_in_tr) if g not in mon_group_set], dtype=int)
        mon_idx = np.array([i for i, g in enumerate(groups_in_tr) if g in mon_group_set], dtype=int)
    else:
        rng = np.random.default_rng(seed)
        perm = rng.permutation(n_samples)
        split_at = max(1, int(n_samples * (1.0 - val_split)))
        core_idx = perm[:split_at]
        mon_idx = perm[split_at:]

    X_core, y_core = X_in_tr[core_idx], y_in_tr[core_idx]
    X_mon, y_mon = X_in_tr[mon_idx], y_in_tr[mon_idx]

    scaler_x = StandardScaler().fit(X_core)
    scaler_y = StandardScaler().fit(y_core)

    X_core_s = scaler_x.transform(X_core)
    y_core_s = scaler_y.transform(y_core)
    X_mon_s = scaler_x.transform(X_mon)
    y_mon_s = scaler_y.transform(y_mon)

    model = build_keras_neural_model(
        model_family=model_family,
        params=norm_params,
        input_dim=X_in_tr.shape[1],
        output_dim=y_in_tr.shape[1],
        seed=seed,
    )

    patience = norm_params["early_stopping_patience"]
    max_epochs = norm_params["max_epochs"]
    batch_size = norm_params["batch_size"]

    early_stopping = keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=patience,
        restore_best_weights=True,
        verbose=0,
    )

    history = model.fit(
        X_core_s,
        y_core_s,
        validation_data=(X_mon_s, y_mon_s),
        epochs=max_epochs,
        batch_size=batch_size,
        callbacks=[early_stopping],
        verbose=0,
    )

    val_losses = history.history.get("val_loss", [])
    optimal_epochs = int(np.argmin(val_losses) + 1) if val_losses else len(history.history.get("loss", [1]))

    # Predicción sobre el fold de validación de puntuación
    X_in_val_s = scaler_x.transform(X_in_val)
    preds_scaled = model.predict(X_in_val_s, verbose=0)
    preds = scaler_y.inverse_transform(preds_scaled)

    return preds, optimal_epochs


def fit_and_predict_neural_outer(
    model_family: str,
    params: Dict[str, Any],
    X_train_outer: np.ndarray,
    y_train_outer: np.ndarray,
    X_test_outer: np.ndarray,
    optimal_epochs: int,
    seed: int = 42,
) -> Tuple[np.ndarray, StandardScaler, StandardScaler, Any]:
    """
    Reajuste externo de la red neuronal sobre TODO el train externo con política
    de épocas derivada exclusivamente de la validación cruzada interna (sin tocar el test externo).
    """
    norm_params = normalize_neural_params(params, model_family)
    scaler_x = StandardScaler().fit(X_train_outer)
    scaler_y = StandardScaler().fit(y_train_outer)

    X_train_s = scaler_x.transform(X_train_outer)
    y_train_s = scaler_y.transform(y_train_outer)

    model = build_keras_neural_model(
        model_family=model_family,
        params=norm_params,
        input_dim=X_train_outer.shape[1],
        output_dim=y_train_outer.shape[1],
        seed=seed,
    )

    epochs_to_run = max(2, int(optimal_epochs))
    batch_size = norm_params["batch_size"]

    model.fit(
        X_train_s,
        y_train_s,
        epochs=epochs_to_run,
        batch_size=batch_size,
        verbose=0,
    )

    X_test_s = scaler_x.transform(X_test_outer)
    preds_scaled = model.predict(X_test_s, verbose=0)
    preds_test = scaler_y.inverse_transform(preds_scaled)

    return preds_test, scaler_x, scaler_y, model


def parse_params_string(params_str: str) -> Dict[str, Any]:
    """
    Deserializa de forma segura y canónica una cadena de hiperparámetros.
    1. Intenta deserialización directa con JSON canónico.
    2. Si falla, intenta compatibilidad con diccionarios de Python (ast.literal_eval)
       saneando null/None, true/True, false/False.
    3. Si la cadena está corrupta o vacía, arroja ValueError explícito (NUNCA {} silencioso).
    """
    if not isinstance(params_str, str) or not params_str.strip():
        raise ValueError(f"Cadena de hiperparámetros vacía o no válida: {params_str!r}")

    # 1. JSON canónico
    try:
        val = json.loads(params_str)
        if isinstance(val, dict):
            return val
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Compatibilidad con repr() de Python (ast.literal_eval)
    import ast
    try:
        val = ast.literal_eval(params_str)
        if isinstance(val, dict):
            return val
    except (ValueError, SyntaxError):
        pass

    # 3. Sanitización de literales mixtos (null en Python o comillas simples en JSON)
    try:
        sanitized = (
            params_str.replace("'", '"')
            .replace("None", "null")
            .replace("True", "true")
            .replace("False", "false")
        )
        val = json.loads(sanitized)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    raise ValueError(f"No se pudieron deserializar los hiperparámetros de tuning (cadena malformada): {params_str!r}")


def select_final_hyperparameters(
    tuning_df: pd.DataFrame,
    model_family: str,
    expected_n_evaluations: Optional[int] = None,
    allow_adaptation: bool = False,
) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Selecciona de forma agregada, determinista y unificada los hiperparámetros ganadores
    para el refit final sobre el dataset de desarrollo.
    
    Reutilizada idénticamente por CLI y Streamlit.
    Aplica desempate determinista: menor MAE macro -> menor RMSE macro -> orden canónico de parámetros.
    Rechaza candidatos con cobertura insuficiente o puntuaciones no finitas.
    """
    if tuning_df is None or tuning_df.empty:
        raise ValueError("tuning_df está vacío o es None. No es posible seleccionar hiperparámetros.")

    fam_df = tuning_df[tuning_df["model_family"] == model_family].copy()
    if fam_df.empty:
        raise ValueError(f"No se encontraron registros de tuning para la familia '{model_family}'.")

    # Validar que inner_macro_mae no tenga NaN o Inf
    if fam_df["inner_macro_mae"].isna().any() or np.isinf(fam_df["inner_macro_mae"]).any():
        raise ValueError(f"Puntuaciones no finitas (NaN o Inf) detectadas en tuning_results para {model_family}.")

    # Validar presencia de columna params
    if "params" not in fam_df.columns:
        raise ValueError("Columna requerida 'params' no encontrada en tuning_df.")

    # Calcular máxima cobertura observada
    eval_counts = fam_df.groupby("params").size()
    max_evals = int(eval_counts.max())
    req_evals = expected_n_evaluations if expected_n_evaluations is not None else max_evals

    candidates: List[Dict[str, Any]] = []
    for p_str, p_group in fam_df.groupby("params"):
        n_evals = len(p_group)
        if n_evals < req_evals and not allow_adaptation:
            raise ValueError(
                f"Candidato con hiperparámetros {p_str} tiene cobertura insuficiente: "
                f"{n_evals} evaluaciones observadas frente a {req_evals} requeridas."
            )

        parsed_params = parse_params_string(p_str)
        mean_mae = float(p_group["inner_macro_mae"].mean())
        mean_rmse = float(p_group["inner_macro_rmse"].mean()) if "inner_macro_rmse" in p_group.columns else 0.0

        opt_eps = p_group["optimal_epochs"].dropna() if "optimal_epochs" in p_group.columns else pd.Series(dtype=float)
        mean_ep = int(round(opt_eps.mean())) if not opt_eps.empty else 20

        candidates.append({
            "params_str": p_str,
            "params": parsed_params,
            "canonical_repr": json.dumps(parsed_params, sort_keys=True),
            "mean_inner_macro_mae": mean_mae,
            "mean_inner_macro_rmse": mean_rmse,
            "n_evaluations": n_evals,
            "mean_optimal_epochs": mean_ep,
        })

    if not candidates:
        raise ValueError(f"No hay candidatos válidos evaluados para la familia '{model_family}'.")

    # Ordenamiento determinista: 1. MAE ascendente, 2. RMSE ascendente, 3. Representación canónica lexicográfica
    candidates.sort(key=lambda c: (c["mean_inner_macro_mae"], c["mean_inner_macro_rmse"], c["canonical_repr"]))

    winner = candidates[0]
    best_params = winner["params"]
    optimal_epochs = winner["mean_optimal_epochs"]

    selection_policy = {
        "method": "mean_inner_cv_aggregation_all_folds",
        "metric": "inner_macro_mae",
        "tie_breaker_metric": "inner_macro_rmse",
        "aggregation": "mean_across_all_outer_folds",
        "deterministic_tie_breaker": "canonical_param_json_lexicographical",
        "winning_mean_score": winner["mean_inner_macro_mae"],
        "winning_mean_rmse": winner["mean_inner_macro_rmse"],
        "winning_params": best_params,
        "selected_params": best_params,
        "candidates": candidates,
        "n_evaluations": winner["n_evaluations"],
        "all_candidates_summary": [
            {
                "params": c["params"],
                "mean_inner_macro_mae": c["mean_inner_macro_mae"],
                "mean_inner_macro_rmse": c["mean_inner_macro_rmse"],
                "n_evaluations": c["n_evaluations"],
            }
            for c in candidates
        ],
        "rationale": (
            "Configuración seleccionada por menor MAE macro promedio a través de todos los folds internos de "
            "todas las particiones externas para mitigar el sesgo de fold particular. Desempate determinista por "
            "menor RMSE y orden canónico de parámetros."
        ),
        "nota_metodologica_agregacion": (
            "Limitación metodológica: los folds internos pertenecen a particiones de entrenamiento externas "
            "que comparten entre 75% y 80% de datos comunes. Las evaluaciones internas no constituyen "
            "observaciones independientes desde el punto de vista inferencial."
        ),
    }

    return best_params, optimal_epochs, selection_policy


def run_nested_cv(
    df: pd.DataFrame,
    config: Dict[str, Any],
    status_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el protocolo de validación cruzada anidada riguroso.
    """
    start_total_time = time.time()

    # 1. Extraer matrices X e y respetando contratos
    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[TARGET_COLUMNS].to_numpy(dtype=np.float32)
    n_samples = len(df)
    sample_ids = df["sample_id"].to_numpy() if "sample_id" in df.columns else np.arange(n_samples)

    # 2. Configurar particiones externas
    outer_cfg = config.get("outer_cv", {})
    n_outer_splits = int(outer_cfg.get("n_splits", 5))
    outer_seed = int(outer_cfg.get("seed", 42))
    group_duplicates = bool(outer_cfg.get("group_duplicates", True))
    allow_adaptation = bool(config.get("allow_adaptation", False) or config.get("test_mode", False))

    feature_groups = None
    splits_manifest = {
        "outer_folds": [],
        "group_duplicates_applied": group_duplicates,
        "n_unique_feature_groups": None,
        "adapted_outer_splits": False,
        "seeds": {"outer_seed": outer_seed},
    }

    if group_duplicates:
        feature_groups = compute_feature_groups(X)
        n_unique_groups = len(np.unique(feature_groups))
        splits_manifest["n_unique_feature_groups"] = int(n_unique_groups)
        splits_manifest["feature_groups"] = feature_groups.tolist()

        if n_unique_groups < n_outer_splits:
            if not allow_adaptation:
                raise ValueError(
                    f"Grupos únicos de características insuficientes ({n_unique_groups}) para {n_outer_splits} "
                    f"particiones externas solicitadas en modo científico. Se requieren al menos {n_outer_splits} grupos distintos."
                )
            logger.warning(
                "Número de grupos únicos (%d) menor que n_splits externo (%d). Reduciendo n_splits a %d (adaptación exploratoria).",
                n_unique_groups,
                n_outer_splits,
                n_unique_groups,
            )
            splits_manifest["adapted_outer_splits"] = True
            splits_manifest["original_requested_splits"] = n_outer_splits
            splits_manifest["executed_splits"] = max(2, n_unique_groups)
            n_outer_splits = max(2, n_unique_groups)

        outer_splitter = GroupKFold(n_splits=n_outer_splits)
        outer_splits = list(outer_splitter.split(X, y, groups=feature_groups))
    else:
        outer_splitter = KFold(n_splits=n_outer_splits, shuffle=True, random_state=outer_seed)
        outer_splits = list(outer_splitter.split(X))

    # 3. Configurar particiones internas
    inner_cfg = config.get("inner_cv", {})
    n_inner_splits = int(inner_cfg.get("n_splits", 3))
    inner_seed_base = int(inner_cfg.get("seed", 1042))

    # 4. Familias de modelos habilitadas
    models_cfg = config.get("models", {})
    if isinstance(models_cfg, list):
        models_dict = {}
        for m in models_cfg:
            fam = m.get("family")
            if fam:
                models_dict[fam] = m
        models_cfg = models_dict

    allow_missing_deps = bool(config.get("allow_missing_dependencies", False))

    available_families = []
    for fam, f_cfg in models_cfg.items():
        if f_cfg.get("enabled", True):
            if fam == "xgboost" and xgb is None:
                if allow_missing_deps:
                    logger.warning("XGBoost solicitado pero xgboost no está instalado. Omitiendo en modo permisivo.")
                    continue
                raise RuntimeError("XGBoost solicitado pero la librería 'xgboost' no disponible en este entorno (dependencias ausentes).")
            elif fam in ["dnn", "autoencoder_mlp"] and (tf is None or keras is None):
                if allow_missing_deps:
                    logger.warning("Red %s solicitada pero TensorFlow no está instalado. Omitiendo en modo permisivo.", fam)
                    continue
                raise RuntimeError(f"Red {fam} solicitada pero TensorFlow/Keras no está disponible en este entorno.")
            available_families.append(fam)

    if not available_families:
        raise RuntimeError("No hay familias de modelo disponibles para entrenar.")

    oof_preds_by_model: Dict[str, np.ndarray] = {
        fam: np.full((n_samples, len(TARGET_COLUMNS)), np.nan, dtype=np.float32)
        for fam in available_families
    }

    fold_metrics_records: List[Dict[str, Any]] = []
    oof_predictions_records: List[Dict[str, Any]] = []
    tuning_records: List[Dict[str, Any]] = []
    splits_manifest = {
        "outer_folds": [],
        "group_duplicates_applied": group_duplicates,
        "n_unique_feature_groups": int(len(np.unique(feature_groups))) if feature_groups is not None else None,
    }

    # Estructura para registrar tiempos reales medidos por familia
    fam_train_times: Dict[str, List[float]] = {fam: [] for fam in available_families}
    fam_infer_times: Dict[str, List[float]] = {fam: [] for fam in available_families}

    for outer_fold, (train_idx, test_idx) in enumerate(outer_splits):
        if status_callback:
            status_callback(f"Iniciando Fold Externo {outer_fold + 1}/{n_outer_splits}...")

        X_train_outer, y_train_outer = X[train_idx], y[train_idx]
        X_test_outer, y_test_outer = X[test_idx], y[test_idx]
        groups_outer_tr = feature_groups[train_idx] if feature_groups is not None else None

        # Configurar Inner Splitter respetando agrupamiento
        if group_duplicates and groups_outer_tr is not None:
            n_inner_groups = len(np.unique(groups_outer_tr))
            if n_inner_groups < n_inner_splits:
                if not allow_adaptation:
                    raise ValueError(
                        f"Grupos únicos en partición interna ({n_inner_groups}) insuficientes para {n_inner_splits} "
                        f"folds internos solicitados en modo científico."
                    )
                inner_k = max(2, min(n_inner_splits, n_inner_groups))
                splits_manifest.setdefault("adapted_inner_splits", []).append({
                    "outer_fold": outer_fold,
                    "n_inner_groups": n_inner_groups,
                    "adapted_to": inner_k,
                })
            else:
                inner_k = n_inner_splits
            inner_splitter = GroupKFold(n_splits=inner_k)
            inner_splits = list(inner_splitter.split(X_train_outer, y_train_outer, groups=groups_outer_tr))
        else:
            inner_splitter = KFold(n_splits=n_inner_splits, shuffle=True, random_state=inner_seed_base + outer_fold)
            inner_splits = list(inner_splitter.split(X_train_outer))

        splits_manifest["outer_folds"].append({
            "outer_fold": outer_fold,
            "train_sample_ids": sample_ids[train_idx].tolist(),
            "test_sample_ids": sample_ids[test_idx].tolist(),
            "train_indices": train_idx.tolist(),
            "test_indices": test_idx.tolist(),
            "n_train": len(train_idx),
            "n_test": len(test_idx),
            "inner_splits": [
                {
                    "inner_fold": in_f,
                    "in_train_indices": in_tr_idx.tolist(),
                    "in_val_indices": in_v_idx.tolist(),
                }
                for in_f, (in_tr_idx, in_v_idx) in enumerate(inner_splits)
            ],
        })

        for fam in available_families:
            fam_cfg = models_cfg.get(fam, {})
            family_defaults = {
                "max_epochs": fam_cfg.get("max_epochs", 100),
                "batch_size": fam_cfg.get("batch_size", 32),
                "early_stopping_patience": fam_cfg.get("early_stopping_patience", fam_cfg.get("patience", 10)),
                "internal_monitor_val_split": fam_cfg.get("internal_monitor_val_split", 0.20),
            }
            raw_param_grid = fam_cfg.get("param_grid", [{}])
            if isinstance(raw_param_grid, dict):
                from sklearn.model_selection import ParameterGrid
                raw_param_grid = list(ParameterGrid(raw_param_grid))
            elif isinstance(raw_param_grid, list):
                raw_param_grid = [p if isinstance(p, dict) else {} for p in raw_param_grid]
            else:
                raw_param_grid = [{}]

            # Fusionar cada candidato con los parámetros a nivel de familia (Bloque 4)
            param_grid = [{**family_defaults, **p} for p in raw_param_grid]
            is_neural = fam in ["dnn", "autoencoder_mlp"]

            # ──────────────────────────────────────────────────────────────────
            # CV Interna: Selección de hiperparámetros sin tocar test externo
            # ──────────────────────────────────────────────────────────────────
            best_candidate_params = param_grid[0]
            best_inner_score = float("inf")
            best_optimal_epochs = 20

            for cand_idx, cand_params in enumerate(param_grid):
                inner_fold_maes = []
                inner_fold_rmses = []
                inner_fold_epochs = []

                for inner_fold, (in_train_idx, in_val_idx) in enumerate(inner_splits):
                    X_in_tr = X_train_outer[in_train_idx]
                    y_in_tr = y_train_outer[in_train_idx]
                    X_in_val = X_train_outer[in_val_idx]
                    y_in_val = y_train_outer[in_val_idx]
                    groups_in_tr = groups_outer_tr[in_train_idx] if groups_outer_tr is not None else None

                    if is_neural:
                        preds_val, opt_ep = fit_and_predict_neural_inner(
                            model_family=fam,
                            params=cand_params,
                            X_in_tr=X_in_tr,
                            y_in_tr=y_in_tr,
                            X_in_val=X_in_val,
                            groups_in_tr=groups_in_tr,
                            seed=outer_seed + outer_fold * 100 + inner_fold,
                        )
                        inner_fold_epochs.append(opt_ep)
                    else:
                        model_inst = ModelFactory.create_model(
                            fam,
                            cand_params,
                            seed=outer_seed + outer_fold * 100 + inner_fold,
                        )
                        preds_val, _, _ = fit_and_predict_traditional(model_inst, X_in_tr, y_in_tr, X_in_val)

                    metrics_val = compute_target_metrics(y_in_val, preds_val)
                    macro_val = compute_macro_metrics(metrics_val)
                    inner_fold_maes.append(macro_val["macro_mae"])
                    inner_fold_rmses.append(macro_val["macro_rmse"])

                cand_mean_inner_mae = float(np.mean(inner_fold_maes)) if inner_fold_maes else float("inf")
                cand_mean_inner_rmse = float(np.mean(inner_fold_rmses)) if inner_fold_rmses else 0.0
                cand_opt_epochs = int(np.median(inner_fold_epochs)) if inner_fold_epochs else 0

                tuning_records.append({
                    "outer_fold": outer_fold,
                    "model_family": fam,
                    "candidate_idx": cand_idx,
                    "params": json.dumps(cand_params, sort_keys=True),
                    "inner_macro_mae": cand_mean_inner_mae,
                    "inner_macro_rmse": cand_mean_inner_rmse,
                    "optimal_epochs": cand_opt_epochs if is_neural else None,
                })

                if cand_mean_inner_mae < best_inner_score:
                    best_inner_score = cand_mean_inner_mae
                    best_candidate_params = cand_params
                    if is_neural and inner_fold_epochs:
                        best_optimal_epochs = int(np.median(inner_fold_epochs))

            # ──────────────────────────────────────────────────────────────────
            # Reajuste sobre todo el entrenamiento externo con medición real de tiempo
            # ──────────────────────────────────────────────────────────────────
            t_train_start = time.perf_counter()
            if is_neural:
                preds_test, scaler_x_final, scaler_y_final, trained_model = fit_and_predict_neural_outer(
                    model_family=fam,
                    params=best_candidate_params,
                    X_train_outer=X_train_outer,
                    y_train_outer=y_train_outer,
                    X_test_outer=X_test_outer,
                    optimal_epochs=best_optimal_epochs,
                    seed=outer_seed + outer_fold,
                )
            else:
                final_outer_model = ModelFactory.create_model(
                    fam,
                    best_candidate_params,
                    seed=outer_seed + outer_fold,
                )
                preds_test, scaler_x_final, scaler_y_final = fit_and_predict_traditional(
                    final_outer_model,
                    X_train_outer,
                    y_train_outer,
                    X_test_outer,
                )
                trained_model = final_outer_model
            t_train_end = time.perf_counter()
            fold_train_sec = float(t_train_end - t_train_start)
            fam_train_times[fam].append(fold_train_sec)

            # Medición real de tiempo de inferencia sobre muestra de prueba (Bloque 6)
            sample_in = X_test_outer[:1]
            t_infer_start = time.perf_counter()
            if is_neural:
                s_pred_s = trained_model.predict(scaler_x_final.transform(sample_in), verbose=0)
            else:
                s_pred_s = trained_model.predict(scaler_x_final.transform(sample_in))
            _ = scaler_y_final.inverse_transform(s_pred_s)
            t_infer_end = time.perf_counter()
            fold_infer_sec = float(max(1e-6, t_infer_end - t_infer_start))
            fam_infer_times[fam].append(fold_infer_sec)

            # Asignar a OOF
            oof_preds_by_model[fam][test_idx] = preds_test

            # Métricas del fold externo
            fold_metrics = compute_target_metrics(y_test_outer, preds_test)
            fold_macro = compute_macro_metrics(fold_metrics)

            for target_name, t_metrics in fold_metrics.items():
                fold_metrics_records.append({
                    "model_id": fam,
                    "outer_fold": outer_fold,
                    "target": target_name,
                    "n_train": len(train_idx),
                    "n_test": len(test_idx),
                    "mae": t_metrics["mae"],
                    "rmse": t_metrics["rmse"],
                    "r2": t_metrics["r2"],
                    "train_time_seconds": fold_train_sec,
                    "infer_time_seconds": fold_infer_sec,
                    "status": "completed",
                })

            fold_metrics_records.append({
                "model_id": fam,
                "outer_fold": outer_fold,
                "target": "macro_average",
                "n_train": len(train_idx),
                "n_test": len(test_idx),
                "mae": fold_macro["macro_mae"],
                "rmse": fold_macro["macro_rmse"],
                "r2": fold_macro["macro_r2"],
                "train_time_seconds": fold_train_sec,
                "infer_time_seconds": fold_infer_sec,
                "status": "completed",
            })

            # Registro fila a fila de OOF
            for loc_idx, global_idx in enumerate(test_idx):
                raw_sid = sample_ids[global_idx]
                s_id = int(raw_sid) if (isinstance(raw_sid, (int, np.integer)) or (isinstance(raw_sid, str) and raw_sid.isdigit())) else str(raw_sid)
                for t_idx, target_name in enumerate(TARGET_COLUMNS):
                    y_t = float(y_test_outer[loc_idx, t_idx])
                    y_p = float(preds_test[loc_idx, t_idx])
                    oof_predictions_records.append({
                        "model_id": fam,
                        "outer_fold": outer_fold,
                        "sample_id": s_id,
                        "target": target_name,
                        "y_true": y_t,
                        "y_pred": y_p,
                        "residual": float(y_t - y_p),
                    })

    total_cv_duration = time.time() - start_total_time

    # ──────────────────────────────────────────────────────────────────────────
    # Resumen global y Selección del Ganador
    # ──────────────────────────────────────────────────────────────────────────
    model_summaries = []
    for fam in available_families:
        oof_matrix = oof_preds_by_model[fam]
        nan_count = int(np.isnan(oof_matrix).sum())
        if nan_count > 0:
            raise RuntimeError(f"OOF para {fam} tiene {nan_count} valores NaN no cubiertos.")

        global_oof_metrics = compute_target_metrics(y, oof_matrix)
        global_oof_macro = compute_macro_metrics(global_oof_metrics)

        fam_fold_records = [
            r for r in fold_metrics_records
            if r["model_id"] == fam and r["target"] == "macro_average"
        ]
        mean_fold_mae = float(np.mean([r["mae"] for r in fam_fold_records]))
        std_fold_mae = float(np.std([r["mae"] for r in fam_fold_records]))
        mean_fold_rmse = float(np.mean([r["rmse"] for r in fam_fold_records]))
        mean_fold_r2 = float(np.mean([r["r2"] for r in fam_fold_records if not np.isnan(r["r2"])]))

        mean_train_time = float(np.mean(fam_train_times[fam])) if fam_train_times[fam] else None
        mean_infer_time = float(np.mean(fam_infer_times[fam])) if fam_infer_times[fam] else None

        model_summaries.append({
            "model_id": fam,
            "CV_MAE_Mean": mean_fold_mae,
            "CV_MAE_Std": std_fold_mae,
            "CV_RMSE_Mean": mean_fold_rmse,
            "CV_R2_Mean": mean_fold_r2,
            "Train_Time_Mean": mean_train_time,
            "Infer_Time_Mean": mean_infer_time,
            "train_time_mean_seconds": mean_train_time,
            "infer_time_mean_seconds": mean_infer_time,
            "OOF_Macro_MAE": global_oof_macro["macro_mae"],
            "OOF_Macro_RMSE": global_oof_macro["macro_rmse"],
            "OOF_Macro_R2": global_oof_macro["macro_r2"],
        })

    summary_df = pd.DataFrame(model_summaries).sort_values(
        by=["CV_MAE_Mean", "CV_RMSE_Mean", "CV_R2_Mean"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    best_overall_model = str(summary_df.iloc[0]["model_id"])

    return {
        "status": "completed",
        "best_overall": best_overall_model,
        "available_families": available_families,
        "summary_df": summary_df,
        "fold_metrics_df": pd.DataFrame(fold_metrics_records),
        "oof_predictions_df": pd.DataFrame(oof_predictions_records),
        "tuning_results_df": pd.DataFrame(tuning_records),
        "tuning_records": tuning_records,
        "splits_manifest": splits_manifest,
        "duration_seconds": total_cv_duration,
        "oof_predictions_matrices": oof_preds_by_model,
        "oof_preds_matrices": oof_preds_by_model,
        "measured_timings": {
            "train_times": fam_train_times,
            "infer_times": fam_infer_times,
        },
    }


def recompute_metrics_from_oof(oof_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Reconstruye métricas de desempeño (MAE, RMSE, R2, Macro) a partir del archivo oof_predictions.csv.
    Garantiza que la reconstrucción offline coincide exactamente con las métricas registradas en evaluación.
    """
    results: Dict[str, Any] = {}
    models = oof_df["model_id"].unique()
    for m in models:
        m_df = oof_df[oof_df["model_id"] == m]
        targets = m_df["target"].unique()
        target_dict: Dict[str, Dict[str, float]] = {}
        for t in targets:
            sub = m_df[m_df["target"] == t]
            yt = sub["y_true"].to_numpy(dtype=float)
            yp = sub["y_pred"].to_numpy(dtype=float)
            mae = float(np.mean(np.abs(yt - yp)))
            rmse = float(np.sqrt(np.mean((yt - yp) ** 2)))
            var_yt = float(np.var(yt))
            r2 = float(1.0 - (np.sum((yt - yp) ** 2) / np.sum((yt - np.mean(yt)) ** 2))) if var_yt > 1e-12 else float("nan")
            target_dict[t] = {"mae": mae, "rmse": rmse, "r2": r2}

        macro_mae = float(np.mean([td["mae"] for td in target_dict.values()]))
        macro_rmse = float(np.mean([td["rmse"] for td in target_dict.values()]))
        macro_r2_vals = [td["r2"] for td in target_dict.values() if not np.isnan(td["r2"])]
        macro_r2 = float(np.mean(macro_r2_vals)) if macro_r2_vals else float("nan")

        macro_dict = {
            "macro_mae": macro_mae,
            "macro_rmse": macro_rmse,
            "macro_r2": macro_r2,
        }
        results[str(m)] = {
            "targets": target_dict,
            "macro": macro_dict,
            "macro_mae": macro_mae,
            "macro_rmse": macro_rmse,
            "macro_r2": macro_r2,
        }
    return results
