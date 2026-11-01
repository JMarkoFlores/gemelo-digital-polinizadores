"""
tests/revision/test_linked_export.py
Verificación del Mandato 3: Vinculación estricta de la exportación a una ejecución evaluada.
Comprueba:
  1. Rechazo de exportación si el run no existe o no tiene estado 'completed'.
  2. Uso del dataset.csv del experimento sin regeneración silenciosa.
  3. Verificación de hash criptográfico de dataset.csv contra manifest.
  4. Preservación del flag test_only=True si el run de origen fue un smoke test.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cli import cmd_export_model
from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.data_audit import compute_file_sha256
from scientific_core.generator import generate_coherent_dataset
from scientific_core.persistence import save_run_artifacts, init_run_manifest


def test_export_rejects_incomplete_run(tmp_path: Path):
    """Verifica que un run con estado 'started' o 'failed' no pueda exportarse."""
    run_dir = tmp_path / "run_incomplete"
    init_run_manifest(run_dir, "run_incomplete", config_effective={"outer_cv": {"seed": 42}})

    args = argparse.Namespace(
        run_dir=str(run_dir),
        run_id=None,
        family="random_forest",
        output_dir=str(tmp_path / "bundle_out"),
    )
    ret = cmd_export_model(args)
    assert ret != 0, "cmd_export_model debió rechazar el run incompleto."
    print("PASS: test_export_rejects_incomplete_run")


def test_export_linked_to_completed_run(tmp_path: Path):
    """
    Verifica que la exportación cargue el dataset del experimento, preserve
    la configuración y marque test_only si el run era smoke.
    """
    run_dir = tmp_path / "smoke_experiment"
    df, _ = generate_coherent_dataset(n_samples=30, random_state=42)

    # Simular artefactos de una ejecución completa
    mock_cv = {
        "best_overall": "random_forest",
        "duration_seconds": 1.2,
        "splits_manifest": {},
        "summary_df": pd.DataFrame([{
            "model_id": "random_forest",
            "CV_MAE_Mean": 4.5,
            "CV_RMSE_Mean": 6.2,
            "CV_R2_Mean": 0.85,
        }]),
        "tuning_results_df": pd.DataFrame([{
            "model_family": "random_forest",
            "params": "{'n_estimators': 20, 'max_depth': 5}",
            "inner_macro_mae": 4.4,
        }]),
    }

    save_run_artifacts(
        base_artifacts_dir=tmp_path,
        run_id="smoke_experiment",
        config_effective={"outer_cv": {"seed": 42}},
        df=df,
        audit_dict={"audit_passed": True},
        cv_results=mock_cv,
        test_only=True,
    )

    bundle_out = tmp_path / "bundle_exported"
    args = argparse.Namespace(
        run_dir=str(run_dir),
        run_id=None,
        family=None,  # Debe inferir 'random_forest'
        output_dir=str(bundle_out),
    )

    ret = cmd_export_model(args)
    assert ret == 0, "cmd_export_model debió exportar exitosamente."

    meta_file = bundle_out / "bundle_metadata.json"
    assert meta_file.is_file()
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    # Comprobaciones de integridad
    assert meta["model_type"] == "random_forest"
    assert meta["test_only"] is True
    assert meta["dataset_rows"] == 30
    assert meta["dataset_sha256"] == compute_file_sha256(run_dir / "dataset.csv")
    assert "observed_training_ranges" in meta
    assert "cv_evaluation_reference" in meta
    assert meta["cv_evaluation_reference"]["CV_MAE_Mean"] == 4.5
    print("PASS: test_export_linked_to_completed_run")


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        test_export_rejects_incomplete_run(p)
        test_export_linked_to_completed_run(p)
