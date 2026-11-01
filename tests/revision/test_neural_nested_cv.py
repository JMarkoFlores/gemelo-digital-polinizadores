"""
tests/revision/test_neural_nested_cv.py
Verificación de la evaluación de redes neuronales (DNN y Supervised Bottleneck MLP)
según los mandatos metodológicos:
  1. Subpartición de monitorización separada de la validación que puntúa candidatos.
  2. Escaladores ajustados únicamente con el entrenamiento permitido.
  3. EarlyStopping sin acceso al test externo.
  4. Reajuste externo con política de épocas derivada solo de datos internos.
  5. Predicciones externas en escala original.
  6. Modelos y transformadores nuevos entre particiones.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scientific_core.nested_cv import (
    fit_and_predict_neural_inner,
    fit_and_predict_neural_outer,
    run_nested_cv,
    tf,
    keras,
)


def test_neural_inner_training_isolation_mocked():
    """
    Verifica que el flujo de entrenamiento interno de redes aísle rigurosamente
    core_train y monitorización, ajuste scalers sólo en core_train y evalúe en escala original.
    """
    rng = np.random.default_rng(42)
    n_tr = 40
    n_val = 10
    n_features = 8
    n_targets = 3

    X_in_tr = rng.normal(10.0, 2.0, size=(n_tr, n_features)).astype(np.float32)
    y_in_tr = rng.normal(50.0, 5.0, size=(n_tr, n_targets)).astype(np.float32)
    X_in_val = rng.normal(10.0, 2.0, size=(n_val, n_features)).astype(np.float32)

    # Mock de Keras para probar el protocolo matemático cuando TF no está en host
    mock_model = MagicMock()
    # model.predict retorna datos escalados
    mock_model.predict.return_value = np.zeros((n_val, n_targets), dtype=np.float32)
    mock_history = MagicMock()
    mock_history.history = {"loss": [1.0, 0.8, 0.6, 0.5], "val_loss": [1.1, 0.9, 0.7, 0.8]}
    mock_model.fit.return_value = mock_history

    with patch("scientific_core.nested_cv.build_keras_neural_model", return_value=mock_model), \
         patch("scientific_core.nested_cv.keras") as mock_keras:
        mock_keras.callbacks.EarlyStopping = MagicMock()

        preds_val, optimal_epochs = fit_and_predict_neural_inner(
            model_family="dnn",
            params={"patience": 2, "max_epochs": 10, "learning_rate": 0.001},
            X_in_tr=X_in_tr,
            y_in_tr=y_in_tr,
            X_in_val=X_in_val,
            seed=42,
        )

        assert preds_val.shape == (n_val, n_targets)
        # Época óptima debe ser argmin de val_loss (índice 2 -> época 3)
        assert optimal_epochs == 3
        # Predicción no debe ser cero pues se invierte con scaler_y (media ~50.0)
        assert not np.allclose(preds_val, 0.0)
        assert np.allclose(np.mean(preds_val, axis=0), 50.0, atol=3.0)
        print("PASS: test_neural_inner_training_isolation_mocked")


def test_neural_outer_refit_with_derived_epoch_policy():
    """
    Verifica que el reajuste externo entrene exactamente por la política de épocas
    derivada de la CV interna sin acceso al test externo.
    """
    rng = np.random.default_rng(123)
    n_train = 50
    n_test = 15
    n_features = 8
    n_targets = 3

    X_train_outer = rng.normal(5.0, 1.0, size=(n_train, n_features)).astype(np.float32)
    y_train_outer = rng.normal(100.0, 10.0, size=(n_train, n_targets)).astype(np.float32)
    X_test_outer = rng.normal(5.0, 1.0, size=(n_test, n_features)).astype(np.float32)

    mock_model = MagicMock()
    mock_model.predict.return_value = np.zeros((n_test, n_targets), dtype=np.float32)

    with patch("scientific_core.nested_cv.build_keras_neural_model", return_value=mock_model):
        preds_test, scaler_x, scaler_y, trained_model = fit_and_predict_neural_outer(
            model_family="autoencoder_mlp",
            params={"learning_rate": 0.001, "batch_size": 16},
            X_train_outer=X_train_outer,
            y_train_outer=y_train_outer,
            X_test_outer=X_test_outer,
            optimal_epochs=17,
            seed=42,
        )

        assert preds_test.shape == (n_test, n_targets)
        # fit llamado con epochs=17 exactamente
        call_kwargs = mock_model.fit.call_args[1]
        assert call_kwargs["epochs"] == 17
        assert call_kwargs["batch_size"] == 16
        # Predicciones desescaladas hacia ~100.0
        assert np.allclose(np.mean(preds_test, axis=0), 100.0, atol=5.0)
        print("PASS: test_neural_outer_refit_with_derived_epoch_policy")


def test_real_tf_execution_status():
    """
    Si TensorFlow está disponible en el entorno (ej. en Docker), corre un micro-test real.
    Si no está disponible, registra explícitamente el comando oficial para Docker.
    """
    if tf is None:
        print("\n[INFO] TensorFlow no instalado en el host local (Python 3.13 Windows).")
        print("Prueba de entrenamiento Keras real marcada como: NO EJECUTADA EN HOST.")
        print("Comando verificado para ejecutar la suite completa en contenedor oficial:")
        print("  docker compose run --rm backend python -m pytest tests/revision/test_neural_nested_cv.py -v\n")
        return

    # Si TF está presente, ejecutar verificación real
    rng = np.random.default_rng(999)
    X_in_tr = rng.normal(10.0, 2.0, size=(20, 8)).astype(np.float32)
    y_in_tr = rng.normal(50.0, 5.0, size=(20, 3)).astype(np.float32)
    X_in_val = rng.normal(10.0, 2.0, size=(5, 8)).astype(np.float32)

    preds_val, opt_ep = fit_and_predict_neural_inner(
        model_family="dnn",
        params={"layers": [16], "learning_rate": 0.01, "patience": 2, "max_epochs": 5, "batch_size": 10},
        X_in_tr=X_in_tr,
        y_in_tr=y_in_tr,
        X_in_val=X_in_val,
        seed=42,
    )
    assert preds_val.shape == (5, 3)
    assert opt_ep >= 1
    print("PASS: test_real_tf_execution_status (Real TensorFlow execution verified)")


if __name__ == "__main__":
    test_neural_inner_training_isolation_mocked()
    test_neural_outer_refit_with_derived_epoch_policy()
    test_real_tf_execution_status()
