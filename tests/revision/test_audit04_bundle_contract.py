"""
tests/revision/test_audit04_bundle_contract.py
Pruebas de regresión para la Auditoría 04 - Bloque 4:
Contrato de exportación científica, rangos observados canónicos, validación de esquemas
y derivación determinista del identificador de bundle (bundle_id).
"""
import copy
import json
import numpy as np
import pytest
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS, PHYSICAL_BOUNDS
from scientific_core.model_bundle import UniversalSurrogatePredictor, export_bundle, load_bundle

VALID_TEST_RANGES = {
    "crop_area_pct": [10.0, 80.0],
    "natural_area_pct": [5.0, 40.0],
    "floral_strips_pct": [1.0, 20.0],
    "pesticide_level": [5.0, 50.0],
    "soil_management_score": [20.0, 80.0],
    "temperature_c": [15.0, 35.0],
    "precipitation_mm": [200.0, 1500.0],
    "landscape_diversity": [0.1, 0.8],
}


def create_trained_fixture():
    X = np.ones((20, len(FEATURE_COLUMNS)), dtype=np.float32) * 20.0
    X[:, 7] = 0.5  # landscape_diversity within [0, 1]
    y = np.ones((20, len(TARGET_COLUMNS)), dtype=np.float32) * 50.0
    scaler_x = StandardScaler().fit(X)
    scaler_y = StandardScaler().fit(y)
    model = Ridge(alpha=1.0).fit(X, y)
    return model, scaler_x, scaler_y


def test_scientific_export_missing_observed_ranges_rejected(tmp_path):
    """
    En exportación científica (no test_only / sin allow_default_bounds),
    la ausencia de 'observed_training_ranges' debe lanzar ValueError explícito.
    """
    model, scaler_x, scaler_y = create_trained_fixture()
    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"test_only": False},
    )

    out_dir = tmp_path / "bundle_missing_ranges"
    with pytest.raises(ValueError, match="observed_training_ranges"):
        export_bundle(predictor, out_dir, metadata_overlay={"test_only": False}, strict_scientific=True)


def test_scientific_export_incomplete_features_rejected(tmp_path):
    """
    Si 'observed_training_ranges' no contiene las 8 características requeridas,
    debe lanzar ValueError detallando las faltantes.
    """
    model, scaler_x, scaler_y = create_trained_fixture()
    incomplete_ranges = {col: [10.0, 50.0] for col in FEATURE_COLUMNS[:5]}  # only 5 of 8
    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": incomplete_ranges, "test_only": False},
    )

    out_dir = tmp_path / "bundle_incomplete_ranges"
    with pytest.raises(ValueError, match="Rangos observados incompletos"):
        export_bundle(predictor, out_dir, metadata_overlay={"test_only": False}, strict_scientific=True)


def test_scientific_export_non_finite_or_inverted_ranges_rejected(tmp_path):
    """
    Si los rangos contienen NaN, inf, o min > max, debe rechazarse con ValueError.
    """
    model, scaler_x, scaler_y = create_trained_fixture()

    # Caso 1: min > max
    invalid_ranges_inverted = dict(VALID_TEST_RANGES)
    invalid_ranges_inverted["crop_area_pct"] = [80.0, 20.0]

    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": invalid_ranges_inverted, "test_only": False},
    )
    with pytest.raises(ValueError, match="Orden inválido en límites"):
        export_bundle(predictor, tmp_path / "bundle_inverted", metadata_overlay={"test_only": False}, strict_scientific=True)

    # Caso 2: NaN
    invalid_ranges_nan = dict(VALID_TEST_RANGES)
    invalid_ranges_nan["natural_area_pct"] = [float("nan"), 40.0]
    predictor.metadata["observed_training_ranges"] = invalid_ranges_nan
    with pytest.raises(ValueError, match="Límites no finitos"):
        export_bundle(predictor, tmp_path / "bundle_nan", metadata_overlay={"test_only": False}, strict_scientific=True)


def test_load_bundle_unsupported_schema_version_rejected(tmp_path):
    """
    load_bundle debe validar estrictamente que schema_version esté en {'2.0', '2.0_revision_metodologica'}.
    """
    model, scaler_x, scaler_y = create_trained_fixture()
    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": VALID_TEST_RANGES, "test_only": True},
    )
    bundle_dir = tmp_path / "bundle_schema_test"
    export_bundle(predictor, bundle_dir, metadata_overlay={"test_only": True})

    meta_file = bundle_dir / "bundle_metadata.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # Modificar versión de esquema a una versión obsoleta o inválida
    meta["schema_version"] = "1.0_deprecated"
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version"):
        load_bundle(bundle_dir, allow_test_bundle=True)


def test_load_bundle_missing_model_hash_in_file_hashes(tmp_path):
    """
    load_bundle debe exigir que el archivo de modelo esté presente en 'file_hashes' antes de deserializar.
    """
    model, scaler_x, scaler_y = create_trained_fixture()
    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": VALID_TEST_RANGES, "test_only": True},
    )
    bundle_dir = tmp_path / "bundle_no_model_hash"
    export_bundle(predictor, bundle_dir, metadata_overlay={"test_only": True})

    meta_file = bundle_dir / "bundle_metadata.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # Quitar el hash del modelo de file_hashes
    model_fn = meta["model_filename"]
    del meta["file_hashes"][model_fn]
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="Hash obligatorio del archivo de modelo"):
        load_bundle(bundle_dir, allow_test_bundle=True)


def test_load_bundle_missing_scalers_hash_in_file_hashes(tmp_path):
    """
    load_bundle debe exigir que 'scalers.pkl' esté en 'file_hashes' si se aplican escaladores.
    """
    model, scaler_x, scaler_y = create_trained_fixture()
    predictor = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": VALID_TEST_RANGES, "test_only": True},
    )
    bundle_dir = tmp_path / "bundle_no_scalers_hash"
    export_bundle(predictor, bundle_dir, metadata_overlay={"test_only": True})

    meta_file = bundle_dir / "bundle_metadata.json"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # Quitar el hash de scalers.pkl
    del meta["file_hashes"]["scalers.pkl"]
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="Hash obligatorio de 'scalers.pkl' ausente"):
        load_bundle(bundle_dir, allow_test_bundle=True)


def test_canonical_bundle_id_depends_on_observed_ranges(tmp_path):
    """
    Comprueba que el bundle_id canónico incorpora los rangos observados:
    dos bundles con idéntico modelo y escaladores pero distintos rangos observados
    deben generar bundle_id distintos.
    """
    model, scaler_x, scaler_y = create_trained_fixture()
    ranges_a = dict(VALID_TEST_RANGES)
    ranges_b = dict(VALID_TEST_RANGES)
    ranges_b["crop_area_pct"] = [20.0, 70.0]

    pred_a = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": ranges_a, "test_only": True},
    )
    res_a = export_bundle(pred_a, tmp_path / "bundle_a", metadata_overlay={"test_only": True})

    pred_b = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": ranges_b, "test_only": True},
    )
    res_b = export_bundle(pred_b, tmp_path / "bundle_b", metadata_overlay={"test_only": True})

    assert res_a["bundle_id"] != res_b["bundle_id"], (
        f"Se esperaba bundle_id distinto al variar rangos de entrenamiento: {res_a['bundle_id']} vs {res_b['bundle_id']}"
    )


def test_canonical_bundle_id_deterministic_and_reproducible(tmp_path):
    """
    Comprueba que la derivación de bundle_id es completamente determinista y reproducible:
    reexportar exactamente la misma configuración produce el mismo bundle_id.
    """
    model, scaler_x, scaler_y = create_trained_fixture()

    pred_1 = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": VALID_TEST_RANGES, "test_only": True},
    )
    res_1 = export_bundle(pred_1, tmp_path / "bundle_det_1", metadata_overlay={"test_only": True})

    pred_2 = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": VALID_TEST_RANGES, "test_only": True},
    )
    res_2 = export_bundle(pred_2, tmp_path / "bundle_det_2", metadata_overlay={"test_only": True})

    assert res_1["bundle_id"] == res_2["bundle_id"], (
        f"bundle_id no fue determinista: {res_1['bundle_id']} != {res_2['bundle_id']}"
    )


def test_export_atomic_publication_rollback_on_failure(tmp_path):
    """
    Comprueba que si el directorio de destino ya existe y ocurre un fallo durante la
    exportación o validación, el bundle original permanece intacto (rollback funcional).
    """
    model, scaler_x, scaler_y = create_trained_fixture()

    target_dir = tmp_path / "target_bundle_dir"

    # 1. Exportar bundle inicial válido
    pred_valid = UniversalSurrogatePredictor(
        model=model,
        model_type="ridge",
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata={"observed_training_ranges": VALID_TEST_RANGES, "test_only": True},
    )
    initial_res = export_bundle(pred_valid, target_dir, metadata_overlay={"test_only": True})
    initial_bundle_id = initial_res["bundle_id"]

    # 2. Intentar sobreescribir con un predictor defectuoso que produce NaN en predicción
    class CorruptPredictor:
        def __init__(self):
            self.model = model
            self.model_type = "ridge"
            self.scaler_x = scaler_x
            self.scaler_y = scaler_y
            self.metadata = {"observed_training_ranges": VALID_TEST_RANGES, "test_only": True}

        def predict(self, X):
            return np.full((len(X), len(TARGET_COLUMNS)), np.nan, dtype=np.float32)

    with pytest.raises(RuntimeError, match="Error de serialización en bundle"):
        export_bundle(CorruptPredictor(), target_dir, metadata_overlay={"test_only": True})

    # 3. Comprobar que el directorio original sigue operativo y su bundle_id no cambió
    restored_bundle = load_bundle(target_dir, allow_test_bundle=True)
    assert restored_bundle.bundle_id == initial_bundle_id
