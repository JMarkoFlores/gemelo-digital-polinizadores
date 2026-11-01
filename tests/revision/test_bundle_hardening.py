"""
tests/revision/test_bundle_hardening.py
Verifica el endurecimiento de la serialización y activación del bundle universal:
  - Rechazo de orden invertido o incorrecto de feature_names.
  - Rechazo si falta scalers.pkl cuando se requiere escalado.
  - Verificación criptográfica SHA-256 de integridad de los archivos del bundle.
  - Exportación atómica vía directorio temporal.
  - Retención del modelo activo ante fallos de recarga en model_store.
  - Rechazo de bundles test_only en producción de backend (Bloque 5 y Bloque 8).
"""
import copy
import json
from pathlib import Path
import pickle
import shutil
import tempfile
import numpy as np
import pytest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from backend.app.services.model_store import ModelStore
from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.model_bundle import (
    UniversalSurrogatePredictor,
    export_bundle,
    load_bundle,
)


def create_dummy_predictor(model_type: str = "ridge") -> UniversalSurrogatePredictor:
    X_train = np.arange(80, dtype=np.float32).reshape(10, 8)
    y_train = np.arange(30, dtype=np.float32).reshape(10, 3)

    scaler_x = StandardScaler().fit(X_train)
    scaler_y = StandardScaler().fit(y_train)

    model = Ridge(alpha=1.0)
    model.fit(scaler_x.transform(X_train), scaler_y.transform(y_train))

    meta = {
        "model_type": model_type,
        "feature_names": list(FEATURE_COLUMNS),
        "target_names": list(TARGET_COLUMNS),
        "test_only": False,
        "preprocessing_contract": {
            "scaler_x_applied": True,
            "scaler_y_applied": True,
            "inverse_transform_required": True,
        },
    }

    return UniversalSurrogatePredictor(
        model=model,
        model_type=model_type,
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata=meta,
    )


def test_inverted_features_rejected():
    """Un bundle con nombres o orden de características alterado debe ser rechazado."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        predictor = create_dummy_predictor()
        bundle_dir = tmp_dir / "valid_bundle"
        export_bundle(predictor, bundle_dir)

        # Alterar el orden de feature_names en bundle_metadata.json
        meta_file = bundle_dir / "bundle_metadata.json"
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta["feature_names"] = list(reversed(FEATURE_COLUMNS))
        meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        with pytest.raises(ValueError, match="Contrato de características inválido"):
            load_bundle(bundle_dir)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_missing_scalers_fails_strictly_without_degraded_operation():
    """Si scalers.pkl fue eliminado, load_bundle debe fallar y nunca operar con scaler_x=None."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        predictor = create_dummy_predictor()
        bundle_dir = tmp_dir / "bundle_without_scalers"
        export_bundle(predictor, bundle_dir)

        # Eliminar scalers.pkl
        scalers_file = bundle_dir / "scalers.pkl"
        assert scalers_file.is_file()
        scalers_file.unlink()

        with pytest.raises(FileNotFoundError, match="scalers.pkl"):
            load_bundle(bundle_dir)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_tampered_model_file_fails_sha256_verification():
    """Si el archivo de modelo es alterado, la verificación SHA-256 debe detectar la corrupción."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        predictor = create_dummy_predictor()
        bundle_dir = tmp_dir / "bundle_tampered"
        export_bundle(predictor, bundle_dir)

        model_file = bundle_dir / "model_ridge.pkl"
        assert model_file.is_file()
        # Alterar un byte del archivo del modelo
        with open(model_file, "ab") as f:
            f.write(b"tamper_data")

        with pytest.raises(ValueError, match="Fallo de integridad criptográfica"):
            load_bundle(bundle_dir)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_model_store_retains_active_model_on_reload_failure():
    """Si model_store intenta recargar un bundle inválido, debe retener el modelo previamente activo."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        predictor = create_dummy_predictor()
        valid_bundle_dir = tmp_dir / "valid_bundle"
        export_bundle(predictor, valid_bundle_dir)

        store = ModelStore()
        store.model_dir = valid_bundle_dir
        store.load()

        assert store.is_ready is True
        assert store.bundle_id is not None
        initial_bundle_id = store.bundle_id
        initial_model = store.model

        # Corromper scalers.pkl en el directorio
        (valid_bundle_dir / "scalers.pkl").unlink()

        # Intentar recargar
        store.reload()

        # Comprobar que el modelo anterior se mantuvo y no se dejó en estado roto
        assert store.is_ready is True
        assert store.bundle_id == initial_bundle_id
        assert store.model is initial_model
        assert store.last_error is not None
        assert "scalers.pkl" in store.last_error

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_model_store_rejects_test_only_bundle_in_production():
    """Un bundle etiquetado como test_only debe ser rechazado en backend salvo en modo de prueba explícito."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        predictor = create_dummy_predictor()
        predictor.metadata["test_only"] = True
        bundle_dir = tmp_dir / "test_bundle"
        export_bundle(predictor, bundle_dir, metadata_overlay={"test_only": True})

        store = ModelStore()
        store.model_dir = bundle_dir
        store.allow_test_bundle = False

        store.load()
        assert store.is_ready is False
        assert "test_only" in str(store.last_error)

        # Ahora permitiendo modo de prueba explícito
        store.allow_test_bundle = True
        store.load()
        assert store.is_ready is True

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
