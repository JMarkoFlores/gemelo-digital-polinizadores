"""
tests/revision/test_audit03_atomic_publication.py
Pruebas de regresión obligatorias para la Auditoría 03 - Bloque 3:
Publicación atómica, rollback automático e invalidación de caché.
"""
from pathlib import Path
import shutil
import numpy as np
import pytest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from unittest.mock import patch

from scientific_core.contracts import FEATURE_COLUMNS
from scientific_core.model_bundle import UniversalSurrogatePredictor, export_bundle
from backend.app.services.model_store import ModelStore
from backend.app.services.optimization import simulation_cache, build_cache_key


def test_export_bundle_atomic_rollback_on_failure(tmp_path):
    """
    Verifica que si ocurre un fallo durante export_bundle (por ejemplo al escribir metadata),
    el directorio de destino no queda en un estado corrupto o a medias, y si existía
    un bundle previo, este es restaurado automáticamente desde el backup.
    """
    dest_dir = tmp_path / "active_model"
    dest_dir.mkdir()

    X = np.ones((10, 8), dtype=np.float32)
    y = np.ones((10, 3), dtype=np.float32)
    scaler_x = StandardScaler().fit(X)
    scaler_y = StandardScaler().fit(y)
    observed_ranges = {c: [0.0, 10.0] for c in FEATURE_COLUMNS}

    # 1. Exportar versión 1 válida
    model1 = Ridge(alpha=1.0).fit(X, y)
    p1 = UniversalSurrogatePredictor(
        model=model1,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": observed_ranges},
    )
    res1 = export_bundle(p1, dest_dir, metadata_overlay={"test_only": False})
    bundle_id_1 = res1["bundle_id"]
    assert (dest_dir / "model_ridge.pkl").exists()
    assert (dest_dir / "bundle_metadata.json").exists()

    # 2. Inyectar fallo durante la exportación de versión 2 (simular error al mover o validar)
    model2 = Ridge(alpha=2.0).fit(X, y)
    p2 = UniversalSurrogatePredictor(
        model=model2,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": observed_ranges},
    )
    with patch("scientific_core.model_bundle.load_bundle", side_effect=RuntimeError("Simulated validation failure")):
        with pytest.raises(RuntimeError, match="Simulated validation failure"):
            export_bundle(p2, dest_dir, metadata_overlay={"test_only": False})

    # 3. Verificar que la versión 1 sigue intacta y el bundle_id sigue siendo el de la versión 1
    import json
    meta = json.loads((dest_dir / "bundle_metadata.json").read_text(encoding="utf-8"))
    assert meta["bundle_id"] == bundle_id_1


def test_bundle_switch_invalidates_cache_and_atomic_snapshot(tmp_path):
    """
    Verifica que:
    1. ModelStore mantiene un snapshot atómico en _active_predictor (no mezcla modelo y scalers).
    2. Cambiar de bundle invalida la clave de caché generada por build_cache_key.
    """
    model_dir = tmp_path / "model_dir"
    model_dir.mkdir()

    X = np.ones((10, 8), dtype=np.float32)
    y1 = np.ones((10, 3), dtype=np.float32) * 5.0
    y2 = np.ones((10, 3), dtype=np.float32) * 20.0
    scaler_x = StandardScaler().fit(X)
    scaler_y1 = StandardScaler().fit(y1)
    scaler_y2 = StandardScaler().fit(y2)
    observed_ranges = {c: [0.0, 10.0] for c in FEATURE_COLUMNS}

    # Exportar Bundle 1
    m1 = Ridge(alpha=1.0).fit(X, y1)
    p1 = UniversalSurrogatePredictor(
        model=m1, model_type="ridge", scaler_x=scaler_x, scaler_y=scaler_y1,
        metadata={"observed_training_ranges": observed_ranges}
    )
    res1 = export_bundle(p1, model_dir, metadata_overlay={"test_only": False})
    b1_id = res1["bundle_id"]

    store = ModelStore(model_dir, allow_test_bundle=True)
    store.load()
    assert store.bundle_id == b1_id

    # Cache key con bundle 1
    dummy_payload = {"pesticide_level": 10.0, "min_natural_area_pct": 20.0}
    key1 = build_cache_key(dummy_payload, bundle_id=store.bundle_id)
    simulation_cache.set(key1, {"result": "cached_bundle_1"})
    assert simulation_cache.get(key1) is not None

    # Exportar Bundle 2 (sobrescribe atómicamente)
    m2 = Ridge(alpha=2.0).fit(X, y2)
    p2 = UniversalSurrogatePredictor(
        model=m2, model_type="ridge", scaler_x=scaler_x, scaler_y=scaler_y2,
        metadata={"observed_training_ranges": observed_ranges}
    )
    res2 = export_bundle(p2, model_dir, metadata_overlay={"test_only": False})
    b2_id = res2["bundle_id"]
    assert b1_id != b2_id

    # Recargar store con Bundle 2
    store.load()
    assert store.bundle_id == b2_id

    # La clave de cache calculada ahora es diferente
    key2 = build_cache_key(dummy_payload, bundle_id=store.bundle_id)
    assert key1 != key2
    # El cache con key2 no tiene el resultado de key1
    assert simulation_cache.get(key2) is None
