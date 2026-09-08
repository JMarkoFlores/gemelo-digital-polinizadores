import time
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
import xgboost as xgb

from data_pipeline import FEATURE_COLUMNS, TARGET_COLUMNS
from training import build_surrogate_model

def build_autoencoder_mlp_model(input_dim: int, normalization_layer: keras.layers.Layer) -> keras.Model:
    inputs = keras.Input(shape=(input_dim,), name="landscape_features")
    x = normalization_layer(inputs)
    # Encoder part
    encoded = keras.layers.Dense(32, activation="relu")(x)
    encoded = keras.layers.Dense(16, activation="relu")(encoded)
    
    # MLP Regressor part on top of encoded features
    x = keras.layers.Dense(64, activation="relu")(encoded)
    x = keras.layers.Dropout(0.1)(x)
    outputs = keras.layers.Dense(len(TARGET_COLUMNS), activation="linear", name="predictions")(x)
    
    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001), loss="mse", metrics=["mae"])
    return model

def evaluate_preds(y_true, y_pred):
    metrics = {}
    for i, target in enumerate(TARGET_COLUMNS):
        metrics[target] = {
            "mae": mean_absolute_error(y_true[:, i], y_pred[:, i]),
            "rmse": np.sqrt(mean_squared_error(y_true[:, i], y_pred[:, i])),
            "r2": r2_score(y_true[:, i], y_pred[:, i])
        }
    return metrics

def train_and_evaluate_all_models(dataframe: pd.DataFrame, progress_bar, status_text, random_state=42):
    X = dataframe[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = dataframe[TARGET_COLUMNS].to_numpy(dtype=np.float32)
    
    scaler = StandardScaler()
    y_scaled = scaler.fit_transform(y)
    
    models_config = {
        "Random Forest (Tradicional)": MultiOutputRegressor(RandomForestRegressor(n_estimators=100, random_state=random_state)),
        "XGBoost (Tradicional)": MultiOutputRegressor(xgb.XGBRegressor(n_estimators=100, random_state=random_state)),
        "Ridge Regression (Tradicional)": MultiOutputRegressor(Ridge(alpha=1.0)),
        "DNN Surrogate (Híbrido)": "dnn",
        "Autoencoder+MLP (Híbrido)": "autoencoder"
    }
    
    kf = KFold(n_splits=3, shuffle=True, random_state=random_state)
    
    results = []
    
    total_steps = len(models_config) * 3
    current_step = 0
    
    best_keras_model = None
    best_keras_mae = float('inf')
    
    for model_name, model_def in models_config.items():
        status_text.text(f"Evaluando: {model_name} (Cross-Validation 3-Folds)...")
        
        fold_maes = []
        
        for fold, (train_idx, val_idx) in enumerate(kf.split(X)):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y_scaled[train_idx], y_scaled[val_idx]
            y_val_orig = y[val_idx]
            
            if isinstance(model_def, str): # Keras model
                tf.keras.utils.set_random_seed(random_state + fold)
                normalization = keras.layers.Normalization(axis=-1)
                normalization.adapt(X_train)
                
                if model_def == "dnn":
                    model = build_surrogate_model(X.shape[1], normalization)
                else:
                    model = build_autoencoder_mlp_model(X.shape[1], normalization)
                    
                early_stopping = keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
                model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=30, batch_size=24, verbose=0, callbacks=[early_stopping])
                
                preds_scaled = model.predict(X_val, verbose=0)
                preds = scaler.inverse_transform(preds_scaled)
                
                # Check if this should be the exported model
                val_mae = np.mean(np.abs(preds - y_val_orig))
                if val_mae < best_keras_mae:
                    best_keras_mae = val_mae
                    best_keras_model = model
            else:
                # Scikit-Learn / XGBoost
                model_def.fit(X_train, y_train)
                preds_scaled = model_def.predict(X_val)
                preds = scaler.inverse_transform(preds_scaled)
                
            fold_metrics = evaluate_preds(y_val_orig, preds)
            # Calculate overall average MAE for this fold
            avg_mae = np.mean([m["mae"] for m in fold_metrics.values()])
            fold_maes.append(avg_mae)
            
            current_step += 1
            progress_bar.progress(current_step / total_steps)
            
        results.append({
            "Modelo": model_name,
            "CV_MAE_Mean": np.mean(fold_maes),
            "CV_MAE_Std": np.std(fold_maes)
        })
        
    results_df = pd.DataFrame(results).sort_values("CV_MAE_Mean")
    
    return {
        "results_df": results_df,
        "best_keras_model": best_keras_model,
        "target_scaler": scaler,
        "best_overall": results_df.iloc[0]["Modelo"]
    }
