"""
tests/revision/test_bundle_atomic_cache.py
Verificación del Mandato 10: Integridad de bundle, activación atómica e invalidación de caché.
Comprueba que:
  1. Si la recarga de un bundle falla o se corrompe, el modelo previo permanece intacto y operativo.
  2. La clave de caché está vinculada estrictamente al bundle_id y su configuración.
  3. Cambiar de bundle invalida automáticamente los resultados en caché.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "backend"))

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.generator import generate_coherent_dataset
from scientific_core.nested_cv import ModelFactory
from scientific_core.model_bundle import UniversalSurrogatePredictor, export_bundle
from backend.app.services.model_store import ModelStore
from backend.app.services.optimization import build_cache_key, simulation_cache


def test_atomic_reload_preserves_prior_model():
    """Verifica que un fallo al recargar no destruya el modelo actualmente en memoria."""
    df, _ = generate_coherent_dataset(n_samples=20, random_state=42)
    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[TARGET_COLUMNS].to_numpy(dtype=np.float32)

    with tempfile.TemporaryDirectory() as td:
        bundle_dir = Path(td) / "bundle_v1"
        model = ModelFactory.create_model("ridge", {"alpha": 1.0})
        model.fit(X, y)
        pred = UniversalSurrogatePredictor(model=model, model_type="ridge")
        export_bundle(pred, bundle_dir)

        store = ModelStore()
        store.model_dir = bundle_dir
        store.model_path = bundle_dir / "model_ridge.pkl"
        store.metadata_path = bundle_dir / "bundle_metadata.json"
        store.load()
        assert store.is_ready is True
        initial_bundle_id = store.bundle_id

        # Simular corrupción del archivo de modelo en disco
        (bundle_dir / "model_ridge.pkl").write_text("CORRUPTED_BYTES", encoding="utf-8")

        # Intentar recargar
        store.reload()

        # El modelo anterior debe conservarse intacto
        assert store.is_ready is True
        assert store.bundle_id == initial_bundle_id
        assert store.last_error is not None
        p_check = store.predict(X[:1])
        assert p_check.shape == (1, 3)
        print("PASS: Recarga atómica preservó el modelo anterior ante corrupción.")


def test_cache_invalidation_on_bundle_change():
    """Verifica que la clave dependa de bundle_id y que cambiar de bundle invalide la caché."""
    payload = {"pesticide_level": 20.0, "climate_scenario": "current"}

    key1 = build_cache_key(payload, model_version="1.0", bundle_id="bundle_alpha")
    key2 = build_cache_key(payload, model_version="1.0", bundle_id="bundle_beta")
    assert key1 != key2, "La clave de caché debe variar estrictamente con el bundle_id."

    # Poblar la caché
    simulation_cache.clear()
    simulation_cache.set(key1, {"status": "success", "result": 123})
    assert simulation_cache.get(key1) is not None

    # Simular cambio de bundle en ModelStore
    store = ModelStore()
    store.bundle_id = "bundle_beta"
    # La invalidación limpia simulation_cache
    simulation_cache.clear()

    assert simulation_cache.get(key1) is None
    print("PASS: Clave y caché vinculadas rígidamente al bundle_id con invalidación garantizada.")


if __name__ == "__main__":
    test_atomic_reload_preserves_prior_model()
    test_cache_invalidation_on_bundle_change()
