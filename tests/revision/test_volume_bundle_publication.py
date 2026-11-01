"""
tests/revision/test_volume_bundle_publication.py
Pruebas focalizadas de publicación de bundles dentro de volumen Docker y directorios ordinarios (CP-FUNC-02).
Verifica:
1. Publicación inicial y directorio versionado dentro del destino sin renombrar la raíz.
2. Nueva publicación sucesiva: genera nuevo directorio versionado, preserva el anterior y conmuta active_bundle.json.
3. Fallo antes de activar: un error en validación elimina staging y preserva intacto el bundle previo.
4. Compatibilidad con ModelStore y load_bundle resolviendo el puntero activo.
"""
from pathlib import Path
import json
import numpy as np
import pytest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from unittest.mock import patch

from scientific_core.contracts import FEATURE_COLUMNS
from scientific_core.model_bundle import UniversalSurrogatePredictor, export_bundle, load_bundle
from backend.app.services.model_store import ModelStore


def create_fixture_predictor(multiplier: float = 1.0):
    X = np.ones((10, 8), dtype=np.float32)
    y = np.ones((10, 3), dtype=np.float32) * multiplier
    scaler_x = StandardScaler().fit(X)
    scaler_y = StandardScaler().fit(y)
    observed_ranges = {c: [0.0, 10.0] for c in FEATURE_COLUMNS}
    model = Ridge(alpha=multiplier).fit(X, y)
    return UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": observed_ranges},
    )


def test_ordinary_and_volume_directory_publication_lifecycle(tmp_path):
    vol_dir = tmp_path / "modelos_ia_mock"
    vol_dir.mkdir()

    # 1. Publicación Inicial (Versión 1)
    p1 = create_fixture_predictor(multiplier=1.0)
    res1 = export_bundle(p1, vol_dir, metadata_overlay={"test_only": True})
    b1_id = res1["bundle_id"]

    # Comprobar estructura: directorio versionado existe y active_bundle.json apunta a él
    b1_dir = vol_dir / b1_id
    assert b1_dir.is_dir()
    assert (b1_dir / "model_ridge.pkl").is_file()
    assert (b1_dir / "bundle_metadata.json").is_file()
    assert (b1_dir / "scalers.pkl").is_file()
    assert (b1_dir / "SHA256SUMS.txt").is_file()

    # active_bundle.json en raíz del volumen
    active_ptr = vol_dir / "active_bundle.json"
    assert active_ptr.is_file()
    active_info1 = json.loads(active_ptr.read_text(encoding="utf-8"))
    assert active_info1["bundle_id"] == b1_id
    assert active_info1["bundle_dir"] == b1_id

    # load_bundle resuelve automáticamente desde la raíz del volumen
    loaded1 = load_bundle(vol_dir, allow_test_bundle=True)
    assert loaded1.bundle_id == b1_id

    # ModelStore carga y queda listo
    store = ModelStore(vol_dir, allow_test_bundle=True)
    assert store.load() is True
    assert store.bundle_id == b1_id

    # 2. Nueva Publicación (Versión 2 con diferentes características)
    p2 = create_fixture_predictor(multiplier=5.0)
    p2.metadata["observed_training_ranges"] = {c: [0.0, 50.0] for c in FEATURE_COLUMNS}
    res2 = export_bundle(p2, vol_dir, metadata_overlay={"test_only": True})
    b2_id = res2["bundle_id"]
    assert b1_id != b2_id

    # Ambos directorios versionados coexisten (no se borran evidencias previas)
    b2_dir = vol_dir / b2_id
    assert b1_dir.is_dir()
    assert b2_dir.is_dir()

    # El puntero activo ahora señala atómicamente a la versión 2
    active_info2 = json.loads(active_ptr.read_text(encoding="utf-8"))
    assert active_info2["bundle_id"] == b2_id
    assert active_info2["bundle_dir"] == b2_id

    # ModelStore recarga y detecta el nuevo bundle
    assert store.reload() is True
    assert store.bundle_id == b2_id

    # 3. Fallo antes de activar el nuevo bundle (Rollback y Preservación del Activo)
    p3_corrupt = create_fixture_predictor(multiplier=10.0)
    with patch("scientific_core.model_bundle.load_bundle", side_effect=RuntimeError("Simulated pre-activation failure")):
        with pytest.raises(RuntimeError, match="Simulated pre-activation failure"):
            export_bundle(p3_corrupt, vol_dir, metadata_overlay={"test_only": True})

    # Verificar que el puntero activo SIGUE apuntando a b2_id y que b2_dir sigue íntegro
    active_info3 = json.loads(active_ptr.read_text(encoding="utf-8"))
    assert active_info3["bundle_id"] == b2_id
    assert active_info3["bundle_dir"] == b2_id

    loaded_after_fail = load_bundle(vol_dir, allow_test_bundle=True)
    assert loaded_after_fail.bundle_id == b2_id
    assert store.reload() is True
    assert store.bundle_id == b2_id
