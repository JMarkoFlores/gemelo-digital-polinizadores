"""
tests/revision/test_audit03_bundle_validation.py
Pruebas de regresión obligatorias para la Auditoría 03 - Bloque 2:
Centralización de la validación y carga de bundles (load_bundle y ModelStore).
Casos A hasta H.
"""
import copy
import hashlib
import json
import pickle
from pathlib import Path
import tempfile
import numpy as np
import pytest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.data_audit import compute_file_sha256
from scientific_core.model_bundle import UniversalSurrogatePredictor, export_bundle, load_bundle
from backend.app.services.model_store import ModelStore


class BrokenModel:
    """Modelo roto de nivel superior para prueba de serialización y no finitud."""
    def predict(self, X):
        return np.full((len(X), 3), np.nan, dtype=np.float32)


@pytest.fixture
def base_valid_bundle(tmp_path_factory):
    """Genera un bundle válido mínimo para pruebas de mutación."""
    temp_dir = tmp_path_factory.mktemp("bundle_fixture")
    export_dir = temp_dir / "valid_bundle"

    # Modelo Ridge ajustado
    X = np.ones((10, 8), dtype=np.float32) * 5.0
    y = np.ones((10, 3), dtype=np.float32) * 10.0
    model = Ridge(alpha=1.0)
    model.fit(X, y)

    scaler_x = StandardScaler().fit(X)
    scaler_y = StandardScaler().fit(y)

    observed_ranges = {col: [0.0, 100.0] for col in FEATURE_COLUMNS}

    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={
            "observed_training_ranges": observed_ranges,
            "test_only": False,
            "run_id": "fixture_run",
        },
    )

    res = export_bundle(
        predictor=predictor,
        export_dir=export_dir,
        metadata_overlay={"test_only": False, "run_id": "fixture_run"},
    )
    return export_dir, res["bundle_id"]


def test_bundle_validation_a_tampered_model_rejected_by_hash(base_valid_bundle, tmp_path):
    """
    Caso A: Archivo de modelo modificado (pickle/h5 alterado) rechazado por discrepancia
    de SHA-256 ANTES de la deserialización.
    """
    orig_dir, _ = base_valid_bundle
    tampered_dir = tmp_path / "tampered_a"
    import shutil
    shutil.copytree(orig_dir, tampered_dir)

    model_file = tampered_dir / "model_ridge.pkl"
    # Corromper o alterar el contenido del archivo
    with open(model_file, "ab") as f:
        f.write(b"CORRUPTED_BYTES")

    # load_bundle directo
    with pytest.raises(ValueError, match="no coincide"):
        load_bundle(tampered_dir, allow_test_bundle=True)

    # ModelStore directo
    store = ModelStore(tampered_dir, allow_test_bundle=True)
    with pytest.raises(ValueError, match="no coincide"):
        store.load(raise_on_error=True)


def test_bundle_validation_b_missing_schema_version(base_valid_bundle, tmp_path):
    """
    Caso B: Metadatos sin schema_version o versión incompatible.
    """
    orig_dir, _ = base_valid_bundle
    tampered_dir = tmp_path / "tampered_b"
    import shutil
    shutil.copytree(orig_dir, tampered_dir)

    meta_file = tampered_dir / "bundle_metadata.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    del meta["schema_version"]
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version"):
        load_bundle(tampered_dir, allow_test_bundle=True)


def test_bundle_validation_c_features_targets_missing_or_wrong_order(base_valid_bundle, tmp_path):
    """
    Caso C: Nombres de features o targets faltantes o en orden incorrecto.
    """
    orig_dir, _ = base_valid_bundle
    tampered_dir = tmp_path / "tampered_c"
    import shutil
    shutil.copytree(orig_dir, tampered_dir)

    meta_file = tampered_dir / "bundle_metadata.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    # Invertir el orden de las features
    meta["feature_names"] = list(reversed(FEATURE_COLUMNS))
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="Contrato de características inválido"):
        load_bundle(tampered_dir, allow_test_bundle=True)


def test_bundle_validation_d_missing_file_hashes(base_valid_bundle, tmp_path):
    """
    Caso D: Metadatos sin bloque file_hashes o hashes faltantes.
    """
    orig_dir, _ = base_valid_bundle
    tampered_dir = tmp_path / "tampered_d"
    import shutil
    shutil.copytree(orig_dir, tampered_dir)

    meta_file = tampered_dir / "bundle_metadata.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    del meta["file_hashes"]
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="file_hashes"):
        load_bundle(tampered_dir, allow_test_bundle=True)


def test_bundle_validation_e_declared_file_missing_on_disk(base_valid_bundle, tmp_path):
    """
    Caso E: Archivo declarado en file_hashes que no existe físicamente en disco.
    """
    orig_dir, _ = base_valid_bundle
    tampered_dir = tmp_path / "tampered_e"
    import shutil
    shutil.copytree(orig_dir, tampered_dir)

    # Eliminar model_ridge.pkl
    (tampered_dir / "model_ridge.pkl").unlink()

    with pytest.raises(FileNotFoundError, match="ausente en disco"):
        load_bundle(tampered_dir, allow_test_bundle=True)


def test_bundle_validation_f_scaler_missing_or_none(base_valid_bundle, tmp_path):
    """
    Caso F: Scaler obligatorio no instanciado o almacenado como None.
    """
    orig_dir, _ = base_valid_bundle
    tampered_dir = tmp_path / "tampered_f"
    import shutil
    shutil.copytree(orig_dir, tampered_dir)

    # Sobrescribir scalers.pkl con None
    with open(tampered_dir / "scalers.pkl", "wb") as f:
        pickle.dump({"scaler_x": None, "scaler_y": None}, f)

    # Actualizar hash en metadata
    meta_file = tampered_dir / "bundle_metadata.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    meta["file_hashes"]["scalers.pkl"] = compute_file_sha256(tampered_dir / "scalers.pkl")
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="scaler_x"):
        load_bundle(tampered_dir, allow_test_bundle=True)


def test_bundle_validation_g_incompatible_or_non_finite_outputs(base_valid_bundle, tmp_path):
    """
    Caso G: Modelo genera salidas no finitas o incompatibles durante el smoke check de carga.
    """
    orig_dir, _ = base_valid_bundle
    tampered_dir = tmp_path / "tampered_g"
    import shutil
    shutil.copytree(orig_dir, tampered_dir)

    with open(tampered_dir / "model_ridge.pkl", "wb") as f:
        pickle.dump(BrokenModel(), f)

    meta_file = tampered_dir / "bundle_metadata.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    meta["file_hashes"]["model_ridge.pkl"] = compute_file_sha256(tampered_dir / "model_ridge.pkl")
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="no finitos"):
        load_bundle(tampered_dir, allow_test_bundle=True)


def test_bundle_validation_h_and_model_store_rollback(base_valid_bundle, tmp_path):
    """
    Caso H: Bundle válido carga correctamente preservando paridad.
    Además, si ModelStore intenta recargar un bundle corrupto, CONSERVA el predictor previo intacto.
    """
    orig_dir, _ = base_valid_bundle

    # 1. Carga inicial válida
    store = ModelStore(orig_dir, allow_test_bundle=True)
    store.load()
    assert store.is_ready is True
    initial_predictor = store._active_predictor

    sample_x = np.ones((2, 8), dtype=np.float32) * 5.0
    pred1 = store.predict(sample_x)
    assert pred1.shape == (2, 3)
    assert np.all(np.isfinite(pred1))

    # 2. Corromper el archivo en disco
    (orig_dir / "model_ridge.pkl").write_bytes(b"CORRUPT")

    # 3. Intentar recarga fallida
    with pytest.raises(ValueError):
        store.load(raise_on_error=True)

    # 4. Verificar que ModelStore retuvo el predictor previo y sigue operativo
    assert store.is_ready is True
    assert store._active_predictor is initial_predictor
    pred2 = store.predict(sample_x)
    np.testing.assert_allclose(pred1, pred2)
