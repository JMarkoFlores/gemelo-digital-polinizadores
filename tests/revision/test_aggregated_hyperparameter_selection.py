"""
tests/revision/test_aggregated_hyperparameter_selection.py
Verifica la selección reproducible de hiperparámetros finales por agregación
a través de todos los folds en lugar del fold con menor error interno (Bloque 7 de la Auditoría 02).
"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import numpy as np
import pandas as pd
import pytest

from cli import cmd_export_model
from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.data_audit import compute_file_sha256
from scientific_core.model_bundle import load_bundle


def test_aggregated_hyperparameter_selection():
    """
    Simula un run donde el fold 0 tuvo una puntuación anormalmente baja para el candidato A (lucky fold),
    pero el candidato B obtuvo un mejor promedio global a través de todos los folds.
    El exportador debe seleccionar el candidato B (mejor promedio), no el A.
    """
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        run_dir = tmp_dir / "run_20261028_test"
        run_dir.mkdir(parents=True)

        # 1. Crear dataset sintético coherente
        n_samples = 40
        data = {
            "sample_id": np.arange(n_samples),
            "crop_area_pct": np.full(n_samples, 45.0),
            "natural_area_pct": np.full(n_samples, 25.0),
            "floral_strips_pct": np.full(n_samples, 5.0),
            "pesticide_level": np.full(n_samples, 20.0),
            "soil_management_score": np.full(n_samples, 65.0),
            "temperature_c": np.full(n_samples, 22.0),
            "precipitation_mm": np.full(n_samples, 1100.0),
            "landscape_diversity": np.full(n_samples, 0.70),
            "crop_yield_index": np.full(n_samples, 115.0),
            "pollinator_abundance_index": np.full(n_samples, 90.0),
            "pollinator_diversity_index": np.full(n_samples, 50.0),
        }
        df = pd.DataFrame(data)
        dataset_path = run_dir / "dataset.csv"
        df.to_csv(dataset_path, index=False)
        d_hash = compute_file_sha256(dataset_path)

        # 2. Manifest completed
        manifest = {
            "schema_version": "2.0_revision_metodologica",
            "run_id": "run_20261028_test",
            "status": "completed",
            "test_only": False,
            "dataset_rows": n_samples,
            "dataset_sha256": d_hash,
            "best_model_id": "ridge",
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # 3. Tuning results donde:
        # Candidato A (alpha=0.1): fold 0 = 0.05 (muy bajo, lucky), fold 1 = 0.50, fold 2 = 0.50 -> media = 0.35
        # Candidato B (alpha=10.0): fold 0 = 0.20, fold 1 = 0.20, fold 2 = 0.20 -> media = 0.20 (ganador real)
        tuning_records = [
            {"outer_fold": 0, "model_family": "ridge", "candidate_idx": 0, "params": json.dumps({"alpha": 0.1}), "inner_macro_mae": 0.05, "optimal_epochs": None},
            {"outer_fold": 1, "model_family": "ridge", "candidate_idx": 0, "params": json.dumps({"alpha": 0.1}), "inner_macro_mae": 0.50, "optimal_epochs": None},
            {"outer_fold": 2, "model_family": "ridge", "candidate_idx": 0, "params": json.dumps({"alpha": 0.1}), "inner_macro_mae": 0.50, "optimal_epochs": None},
            {"outer_fold": 0, "model_family": "ridge", "candidate_idx": 1, "params": json.dumps({"alpha": 10.0}), "inner_macro_mae": 0.20, "optimal_epochs": None},
            {"outer_fold": 1, "model_family": "ridge", "candidate_idx": 1, "params": json.dumps({"alpha": 10.0}), "inner_macro_mae": 0.20, "optimal_epochs": None},
            {"outer_fold": 2, "model_family": "ridge", "candidate_idx": 1, "params": json.dumps({"alpha": 10.0}), "inner_macro_mae": 0.20, "optimal_epochs": None},
        ]
        pd.DataFrame(tuning_records).to_csv(run_dir / "tuning_results.csv", index=False)

        # 4. Exportar bundle con cmd_export_model
        export_out = tmp_dir / "exported_bundle"
        args = argparse.Namespace(
            run_dir=str(run_dir),
            run_id=None,
            family="ridge",
            output_dir=str(export_out),
            force_test_bundle=False,
        )

        exit_code = cmd_export_model(args)
        assert exit_code == 0, "cmd_export_model debe completarse con éxito"

        # 5. Cargar y verificar metadatos del bundle
        predictor = load_bundle(export_out)
        meta = predictor.metadata

        # Verificar que el ganador fue alpha=10.0 (mejor promedio global 0.20), no alpha=0.1 (lucky fold de 0.05)
        assert meta["winning_hyperparameters"] == {"alpha": 10.0}, (
            f"Se esperaba alpha=10.0 por agregación de medias, pero se seleccionó {meta['winning_hyperparameters']}"
        )

        # Verificar política de selección y registro de puntuaciones candidatas
        policy = meta["final_selection_policy"]
        assert policy["method"] == "mean_inner_cv_aggregation_all_folds"
        assert policy["winning_mean_score"] == pytest.approx(0.20, abs=1e-4)
        assert len(policy["all_candidates_summary"]) == 2

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
