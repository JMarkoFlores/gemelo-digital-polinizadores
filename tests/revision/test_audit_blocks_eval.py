"""
tests/revision/test_audit_blocks_eval.py
Verifica que la auditoría de datos bloquee la evaluación de modelos ante datos inválidos
y que no exista regeneración silenciosa de datos (Bloque 3 de la Auditoría 02).
"""
import argparse
import json
import shutil
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from cli import cmd_evaluate
from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.data_audit import audit_dataset


def create_sample_dataset(crop_area_pct: float = 50.0, n_samples: int = 20) -> pd.DataFrame:
    data = {
        "sample_id": np.arange(n_samples),
        "crop_area_pct": np.full(n_samples, crop_area_pct),
        "natural_area_pct": np.full(n_samples, 20.0),
        "floral_strips_pct": np.full(n_samples, 5.0),
        "pesticide_level": np.full(n_samples, 25.0),
        "soil_management_score": np.full(n_samples, 60.0),
        "temperature_c": np.full(n_samples, 23.5),
        "precipitation_mm": np.full(n_samples, 1050.0),
        "landscape_diversity": np.full(n_samples, 0.65),
        "crop_yield_index": np.full(n_samples, 120.0),
        "pollinator_abundance_index": np.full(n_samples, 85.0),
        "pollinator_diversity_index": np.full(n_samples, 45.0),
    }
    return pd.DataFrame(data)


def test_invalid_dataset_with_crop_area_120_blocked():
    """Un dataset con crop_area_pct = 120 debe fallar auditoría y detener la evaluación inmediatamente."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        # 1. Crear dataset corrupto con crop_area_pct = 120
        df_invalid = create_sample_dataset(crop_area_pct=120.0, n_samples=20)
        invalid_csv = tmp_dir / "invalid_dataset.csv"
        df_invalid.to_csv(invalid_csv, index=False)

        audit_res = audit_dataset(df_invalid, policy="corrected")
        assert audit_res["audit_passed"] is False, "La auditoría debió fallar por crop_area_pct = 120"

        # 2. Ejecutar cmd_evaluate sobre el dataset inválido
        smoke_cfg = Path("configs/smoke_test.json").resolve()
        out_runs = tmp_dir / "runs"

        args = argparse.Namespace(
            config=str(smoke_cfg),
            dataset=str(invalid_csv),
            output_dir=str(out_runs),
            smoke=True,
            allow_synthetic=False,
        )

        exit_code = cmd_evaluate(args)
        assert exit_code == 1, "cmd_evaluate debe salir con código de error (1) ante dataset inválido"

        # 3. Comprobar que el manifest se registró con estado 'failed'
        run_dirs = list(out_runs.glob("smoke_*"))
        assert len(run_dirs) == 1, "Debe existir el directorio del run"
        run_dir = run_dirs[0]

        manifest_p = run_dir / "manifest.json"
        assert manifest_p.is_file(), "El manifest debe existir"
        manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
        assert manifest["status"] == "failed", f"El estado debe ser 'failed', pero fue '{manifest['status']}'"
        assert "Auditoría previa falló" in manifest.get("error", "")

        # 4. Comprobar que NO se generaron archivos de entrenamiento completado
        assert not (run_dir / "model_summary.csv").exists(), "No debe generarse model_summary.csv"
        assert not (run_dir / "oof_predictions.csv").exists(), "No debe generarse oof_predictions.csv"

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_nonexistent_dataset_fails_explicitly():
    """Si la ruta de datos especificada no existe, debe fallar explícitamente sin generar datos silenciosamente."""
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        nonexistent = tmp_dir / "archivo_fantasma.csv"
        smoke_cfg = Path("configs/smoke_test.json").resolve()
        out_runs = tmp_dir / "runs"

        args = argparse.Namespace(
            config=str(smoke_cfg),
            dataset=str(nonexistent),
            output_dir=str(out_runs),
            smoke=False,
            allow_synthetic=False,
        )

        exit_code = cmd_evaluate(args)
        assert exit_code == 1, "cmd_evaluate debe fallar con código 1 si el archivo no existe"

        run_dirs = list(out_runs.glob("*_*"))
        assert len(run_dirs) == 1
        manifest = json.loads((run_dirs[0] / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        assert "no existe" in manifest.get("error", "").lower()

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
