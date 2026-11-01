"""
tests/revision/test_audit04_streamlit_persistence.py
Pruebas obligatorias para el Bloque 1 de la Auditoría 04:
Verificación del adaptador de persistencia y exportación de Streamlit.
Recorrido completo:
  inicialización -> evaluación -> persistencia -> exportación -> actualización del manifiesto.
Comprobaciones:
  - Archivos existentes (11 artefactos normalizados).
  - Configuración completa guardada.
  - Hash del dataset verificado.
  - run_id no nulo y trazable.
  - Exportación vinculada estrictamente al dataset entrenado.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.data_audit import compute_file_sha256
from streamlit_app.adapter import (
    execute_streamlit_training_run,
    export_streamlit_model,
)


@pytest.fixture
def small_valid_dataset() -> pd.DataFrame:
    """Genera un dataset sintético pequeño pero perfectamente coherente."""
    rng = np.random.default_rng(1042)
    n = 24
    crop = rng.uniform(40.0, 60.0, size=n)
    nat = rng.uniform(15.0, 25.0, size=n)
    flor = rng.uniform(3.0, 8.0, size=n)
    pest = rng.uniform(10.0, 40.0, size=n)
    soil = rng.uniform(60.0, 90.0, size=n)
    temp = rng.uniform(20.0, 28.0, size=n)
    prec = rng.uniform(800.0, 1200.0, size=n)
    div = (nat / 100.0) * 0.5 + (flor / 100.0) * 0.3 + (soil / 100.0) * 0.2

    y_yield = crop * 1.5 + soil * 0.3 - pest * 0.2 + rng.normal(0, 1, size=n)
    y_abund = nat * 2.0 + flor * 3.0 - pest * 0.5 + rng.normal(0, 1, size=n)
    y_div = div * 100.0 + rng.normal(0, 0.5, size=n)

    data = {
        "crop_area_pct": crop,
        "natural_area_pct": nat,
        "floral_strips_pct": flor,
        "pesticide_level": pest,
        "soil_management_score": soil,
        "temperature_c": temp,
        "precipitation_mm": prec,
        "landscape_diversity": div,
        "crop_yield_index": y_yield,
        "pollinator_abundance_index": y_abund,
        "pollinator_diversity_index": y_div,
    }
    df = pd.DataFrame(data)
    df.insert(0, "sample_id", [f"SMP_{i:04d}" for i in range(len(df))])
    return df


def test_streamlit_lifecycle_end_to_end(small_valid_dataset: pd.DataFrame):
    """
    Recorrido completo: inicialización -> evaluación -> persistencia -> exportación -> manifest actualizado.
    """
    with tempfile.TemporaryDirectory() as tmp_artifacts:
        with tempfile.TemporaryDirectory() as tmp_export:
            artifacts_dir = Path(tmp_artifacts)
            export_dir = Path(tmp_export)

            # 1. Ejecutar ciclo Streamlit mediante el adaptador
            t_res = execute_streamlit_training_run(
                dataframe=small_valid_dataset,
                k_folds=2,
                tune_hyperparameters=False,
                scientific_mode=False,
                random_state=42,
                data_source_type="sintetico_calibrado",
                data_source_label="Dataset de Prueba Pequeño",
                base_artifacts_dir=artifacts_dir,
            )

            # 2. Verificar que run_id y run_dir fueron registrados
            run_id = t_res.get("run_id")
            run_dir_str = t_res.get("run_dir")
            assert run_id is not None and str(run_id).startswith("streamlit_")
            assert run_dir_str is not None
            run_dir = Path(run_dir_str)
            assert run_dir.is_dir()

            # 3. Comprobar existencia física de los 11 artefactos normalizados
            expected_files = [
                "manifest.json",
                "config_effective.json",
                "environment.json",
                "data_audit.json",
                "dataset.csv",
                "splits.json",
                "tuning_results.csv",
                "fold_metrics.csv",
                "oof_predictions.csv",
                "model_summary.csv",
                "SHA256SUMS.txt",
            ]
            for ef in expected_files:
                f_path = run_dir / ef
                assert f_path.is_file(), f"Artefacto requerido ausente: {ef}"

            # 4. Comprobar contenido y hash en manifest.json
            manifest_path = run_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["status"] == "completed"
            assert manifest["run_id"] == run_id
            assert manifest["started_at_utc"] is not None
            assert manifest["completed_at_utc"] is not None
            assert manifest["dataset_rows"] == len(small_valid_dataset)

            dataset_file = run_dir / "dataset.csv"
            expected_ds_hash = compute_file_sha256(dataset_file)
            assert manifest["dataset_sha256"] == expected_ds_hash
            assert t_res.get("dataset_sha256") == expected_ds_hash

            # 5. Comprobar config_effective.json
            cfg = json.loads((run_dir / "config_effective.json").read_text(encoding="utf-8"))
            assert cfg["outer_cv"]["n_splits"] == 2
            assert "scientific_mode" in cfg

            # 6. Exportar bundle vinculado a este run
            bundle_out = export_dir / "test_bundle"
            export_res = export_streamlit_model(
                training_result=t_res,
                export_dir=bundle_out,
                force_test_bundle=True,
            )

            assert export_res["status"] == "verified"
            assert (bundle_out / "bundle_metadata.json").is_file()

            # 7. Comprobar que el manifest.json del run se actualizó con el bundle exportado
            manifest_updated = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest_updated.get("bundle") is not None
            assert manifest_updated["bundle"]["bundle_id"] == export_res["bundle_id"]
            assert "bundle_exported_at_utc" in manifest_updated


def test_streamlit_export_bound_to_training_dataset(small_valid_dataset: pd.DataFrame):
    """
    Verifica que la exportación use estrictamente el dataset con el que se entrenó,
    evitando discrepancias si el usuario muta o selecciona otro dataset después.
    """
    with tempfile.TemporaryDirectory() as tmp_artifacts:
        with tempfile.TemporaryDirectory() as tmp_export:
            artifacts_dir = Path(tmp_artifacts)
            export_dir = Path(tmp_export)

            t_res = execute_streamlit_training_run(
                dataframe=small_valid_dataset,
                k_folds=2,
                tune_hyperparameters=False,
                scientific_mode=False,
                random_state=42,
                base_artifacts_dir=artifacts_dir,
            )

            # Verificar que training_dataset está vinculado
            assert "training_dataset" in t_res
            assert len(t_res["training_dataset"]) == len(small_valid_dataset)

            # Exportar y verificar que los rangos observados coincidan exactamente con small_valid_dataset
            bundle_out = export_dir / "bound_bundle"
            export_res = export_streamlit_model(
                training_result=t_res,
                export_dir=bundle_out,
                force_test_bundle=True,
            )

            meta = json.loads((bundle_out / "bundle_metadata.json").read_text(encoding="utf-8"))
            observed = meta["observed_training_ranges"]
            for col in FEATURE_COLUMNS:
                assert observed[col][0] == pytest.approx(float(small_valid_dataset[col].min()))
                assert observed[col][1] == pytest.approx(float(small_valid_dataset[col].max()))
