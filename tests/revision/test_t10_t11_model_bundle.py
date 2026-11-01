"""
tests/revision/test_t10_t11_model_bundle.py
Pruebas técnicas T10 y T11: Serialización, verificación numérica y rechazo de metadatos incoherentes.
"""
import sys
import shutil
import tempfile
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scientific_core.generator import generate_coherent_dataset
from scientific_core.model_bundle import (
    UniversalSurrogatePredictor,
    export_bundle,
    load_bundle,
)
from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS


def test_t10_bundle_export_and_load_equality():
    """
    T10: Verifica que exportar y re-cargar un predictor conserva exactamente
    las predicciones numéricas con tolerancia estricta.
    """
    df, _ = generate_coherent_dataset(n_samples=30, random_state=42)
    X = df[FEATURE_COLUMNS].to_numpy()
    y = df[TARGET_COLUMNS].to_numpy()

    scaler_x = StandardScaler().fit(X)
    scaler_y = StandardScaler().fit(y)

    model = MultiOutputRegressor(Ridge(alpha=1.0))
    model.fit(scaler_x.transform(X), scaler_y.transform(y))

    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"version": "test_v1"},
    )

    temp_dir = tempfile.mkdtemp(prefix="bundle_test_")
    try:
        export_res = export_bundle(predictor, temp_dir)
        assert export_res["status"] == "verified"
        assert export_res["verification_diff"] < 1e-5

        reloaded = load_bundle(temp_dir)
        test_points = X[:5]
        preds_1 = predictor.predict(test_points)
        preds_2 = reloaded.predict(test_points)

        np.testing.assert_allclose(preds_1, preds_2, rtol=1e-5, atol=1e-5)
        print("T10 PASSED: Bundle serializado y re-cargado produce predicciones idénticas.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_t11_incoherent_bundle_rejected():
    """
    T11: Verifica que si los metadatos apuntan a un archivo de modelo inexistente
    o faltan archivos requeridos, la carga es rechazada limpiamente con excepción descriptiva.
    """
    temp_dir = tempfile.mkdtemp(prefix="bundle_incoherent_")
    try:
        # Directorio sin archivos
        rejected = False
        try:
            load_bundle(temp_dir)
        except FileNotFoundError:
            rejected = True
        assert rejected, "La carga de un directorio vacío debe fallar"

        # Crear metadatos incoherentes con modelo inexistente
        meta_path = Path(temp_dir) / "bundle_metadata.json"
        meta_path.write_text('{"model_type": "ridge", "model_filename": "non_existent.pkl"}', encoding="utf-8")
        rejected_file = False
        try:
            load_bundle(temp_dir)
        except FileNotFoundError:
            rejected_file = True
        assert rejected_file, "La carga con archivo de modelo inexistente debe fallar"
        print("T11 PASSED: Artefactos o metadatos incoherentes son rechazados limpiamente.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_t10_bundle_export_and_load_equality()
    test_t11_incoherent_bundle_rejected()
    print("Bundle tests passed successfully!")
