"""
tests/revision/test_neural_config_unification.py
Verifica la unificación del esquema de configuración de redes neuronales,
la propagación de parámetros de familia y el microentrenamiento real de Keras (Bloque 4 de la Auditoría 02).
"""
import json
from pathlib import Path
import numpy as np
import pytest

from scientific_core.nested_cv import (
    build_keras_neural_model,
    fit_and_predict_neural_inner,
    fit_and_predict_neural_outer,
    normalize_neural_params,
    tf,
)


def test_neural_params_normalization():
    """Verifica que el mapeo entre esquemas JSON y código sea consistente y sin ambigüedades."""
    # Caso 1: DNN con hidden_units y dropout_rate
    dnn_raw = {
        "hidden_units": [128, 64, 32],
        "dropout_rate": 0.15,
        "learning_rate": 0.001,
        "early_stopping_patience": 6,
        "max_epochs": 25,
        "batch_size": 16,
    }
    dnn_norm = normalize_neural_params(dnn_raw, "dnn")
    assert dnn_norm["layers"] == [128, 64, 32]
    assert dnn_norm["hidden_units"] == [128, 64, 32]
    assert dnn_norm["dropout"] == 0.15
    assert dnn_norm["dropout_rate"] == 0.15
    assert dnn_norm["early_stopping_patience"] == 6
    assert dnn_norm["patience"] == 6
    assert dnn_norm["max_epochs"] == 25
    assert dnn_norm["batch_size"] == 16

    # Caso 2: Bottleneck MLP con latent_dim y regressor_units
    ae_raw = {
        "latent_dim": 16,
        "regressor_units": 64,
        "dropout_rate": 0.12,
        "learning_rate": 0.0015,
    }
    ae_norm = normalize_neural_params(ae_raw, "autoencoder_mlp")
    assert ae_norm["bottleneck_dim"] == 16
    assert ae_norm["latent_dim"] == 16
    assert ae_norm["decoder_units"] == [64]
    assert ae_norm["encoder_units"] == [64, 32]
    assert ae_norm["dropout"] == 0.12


def test_revision_config_architectures_are_distinct():
    """Verifica que las configuraciones de redes en configs/revision_metodologica.json contemplen arquitecturas distintas."""
    cfg_p = Path("configs/revision_metodologica.json")
    assert cfg_p.is_file(), "configs/revision_metodologica.json debe existir"
    config = json.loads(cfg_p.read_text(encoding="utf-8"))

    models = config["models"]
    assert "dnn" in models and "autoencoder_mlp" in models

    # Comprobar candidatos de dnn
    dnn_grid = models["dnn"]["param_grid"]
    assert len(dnn_grid) >= 3
    dnn_units = [tuple(normalize_neural_params(p, "dnn")["layers"]) for p in dnn_grid]
    assert len(set(dnn_units)) == len(dnn_grid), "Todos los candidatos de DNN deben tener arquitecturas distintas"

    # Comprobar candidatos de bottleneck mlp
    ae_grid = models["autoencoder_mlp"]["param_grid"]
    assert len(ae_grid) >= 3
    ae_bottlenecks = [normalize_neural_params(p, "autoencoder_mlp")["bottleneck_dim"] for p in ae_grid]
    assert len(set(ae_bottlenecks)) == len(ae_grid), "Todos los candidatos de Bottleneck deben tener dimensiones de cuello distintas"


def test_insufficient_groups_fails_with_informative_error():
    """Si group_duplicates está activo y hay menos de 2 grupos para monitor split, debe fallar con error descriptivo."""
    if tf is None:
        pytest.skip("TensorFlow no disponible en este entorno host")

    X_dummy = np.ones((10, 8), dtype=np.float32)
    y_dummy = np.ones((10, 3), dtype=np.float32)
    X_val = np.ones((2, 8), dtype=np.float32)
    groups = np.zeros(10, dtype=int)  # Solo 1 grupo único

    with pytest.raises(ValueError, match="al menos 2 grupos disjuntos"):
        fit_and_predict_neural_inner(
            model_family="dnn",
            params={"max_epochs": 2, "batch_size": 4},
            X_in_tr=X_dummy,
            y_in_tr=y_dummy,
            X_in_val=X_val,
            groups_in_tr=groups,
        )


def test_real_microtraining_dnn_and_bottleneck():
    """Ejecuta microentrenamiento real de Keras para DNN y Bottleneck MLP con early stopping y escalado."""
    if tf is None:
        pytest.skip("TensorFlow no disponible en este entorno host")

    rng = np.random.default_rng(42)
    X_tr = rng.normal(size=(40, 8)).astype(np.float32)
    y_tr = (X_tr[:, :3] * 2.0 + 10.0).astype(np.float32)
    X_val = rng.normal(size=(8, 8)).astype(np.float32)
    groups = np.array([i // 4 for i in range(40)], dtype=int)  # 10 grupos

    # 1. Microtraining DNN
    dnn_params = {
        "hidden_units": [32, 16],
        "dropout_rate": 0.1,
        "max_epochs": 4,
        "batch_size": 8,
        "early_stopping_patience": 2,
    }
    preds_dnn, opt_ep_dnn = fit_and_predict_neural_inner(
        model_family="dnn",
        params=dnn_params,
        X_in_tr=X_tr,
        y_in_tr=y_tr,
        X_in_val=X_val,
        groups_in_tr=groups,
    )
    assert preds_dnn.shape == (8, 3), "Las predicciones de DNN deben ser (N, 3)"
    assert opt_ep_dnn >= 1, "La época óptima debe ser positiva"

    # Reajuste externo DNN
    preds_outer, sx, sy, model = fit_and_predict_neural_outer(
        model_family="dnn",
        params=dnn_params,
        X_train_outer=X_tr,
        y_train_outer=y_tr,
        X_test_outer=X_val,
        optimal_epochs=opt_ep_dnn,
    )
    assert preds_outer.shape == (8, 3)

    # 2. Microtraining Bottleneck MLP
    ae_params = {
        "latent_dim": 8,
        "regressor_units": 16,
        "dropout_rate": 0.05,
        "max_epochs": 4,
        "batch_size": 8,
        "early_stopping_patience": 2,
    }
    preds_ae, opt_ep_ae = fit_and_predict_neural_inner(
        model_family="autoencoder_mlp",
        params=ae_params,
        X_in_tr=X_tr,
        y_in_tr=y_tr,
        X_in_val=X_val,
        groups_in_tr=groups,
    )
    assert preds_ae.shape == (8, 3), "Las predicciones de Bottleneck MLP deben ser (N, 3)"
    assert opt_ep_ae >= 1
