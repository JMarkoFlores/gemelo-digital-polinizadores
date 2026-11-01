"""
tests/revision/test_manifest_bundle_provenance.py
Verifica que los manifiestos registren la procedencia completa, el generador,
la preservación de started_at_utc y la información del bundle exportado (Bloque 10 de la Auditoría 02).
"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import numpy as np
import pandas as pd
import pytest

from cli import cmd_evaluate, cmd_export_model


def test_manifest_lifecycle_and_bundle_export():
    """
    Ejecuta un ciclo completo de evaluación y exportación smoke:
      1. Verifica que started_at_utc se preserve en manifest.json.
      2. Verifica que generator_metadata y dataset_provenance se registren.
      3. Verifica que tras exportar el bundle, manifest.json tenga bundle != null.
      4. Verifica que SHA256SUMS.txt indexe los artefactos correctamente sin auto-referencia.
    """
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        out_runs = tmp_dir / "runs"
        smoke_cfg = Path("configs/smoke_test.json").resolve()

        # 1. Evaluar smoke
        args_eval = argparse.Namespace(
            config=str(smoke_cfg),
            dataset=None,
            output_dir=str(out_runs),
            smoke=True,
            allow_synthetic=True,
        )

        ret_eval = cmd_evaluate(args_eval)
        assert ret_eval == 0, "cmd_evaluate smoke debe retornar 0"

        run_dirs = list(out_runs.glob("smoke_*"))
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]

        manifest_file = run_dir / "manifest.json"
        assert manifest_file.is_file()
        manifest_post_eval = json.loads(manifest_file.read_text(encoding="utf-8"))

        assert manifest_post_eval["status"] == "completed"
        assert "started_at_utc" in manifest_post_eval
        assert "completed_at_utc" in manifest_post_eval
        # started_at debe ser <= completed_at
        assert manifest_post_eval["started_at_utc"] <= manifest_post_eval["completed_at_utc"]

        # Procedencia y generador
        assert "generator_metadata" in manifest_post_eval
        assert "dataset_provenance" in manifest_post_eval

        # 2. Exportar bundle
        bundle_out = run_dir / "exported_bundle"
        args_export = argparse.Namespace(
            run_dir=str(run_dir),
            run_id=None,
            family="ridge",
            output_dir=str(bundle_out),
            force_test_bundle=True,
        )

        ret_exp = cmd_export_model(args_export)
        assert ret_exp == 0, "cmd_export_model debe retornar 0"

        # 3. Comprobar que el manifest ahora registra el bundle (Bloque 10)
        manifest_post_export = json.loads(manifest_file.read_text(encoding="utf-8"))
        bundle_info = manifest_post_export.get("bundle")
        assert bundle_info is not None, "El manifiesto debe registrar la información del bundle"
        assert "bundle_id" in bundle_info
        assert bundle_info["model_type"] == "ridge"
        assert "file_hashes" in bundle_info
        assert "exported_at_utc" in bundle_info

        # started_at_utc debe haberse conservado intacto
        assert manifest_post_export["started_at_utc"] == manifest_post_eval["started_at_utc"]

        # 4. SHA256SUMS.txt no debe tener auto-referencia y debe existir
        sums_file = run_dir / "SHA256SUMS.txt"
        assert sums_file.is_file()
        sums_content = sums_file.read_text(encoding="utf-8")
        assert "SHA256SUMS.txt" not in sums_content

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
