"""
scientific_core/persistence.py
Gestión de persistencia por ejecución (run_id), manifiestos de ciclo de vida (started, completed, failed),
trazabilidad criptográfica SHA-256 e integridad de artefactos.
Garantiza:
  1. Manifiesto inicial con estado 'started' antes de la ejecución.
  2. Registro explícito de fallos ('failed') si ocurre alguna interrupción o error.
  3. Manifiesto 'completed' únicamente cuando todos los artefactos se generan con éxito.
  4. Preservación estricta de started_at_utc original y registro de completed_at_utc.
  5. Actualización explícita del manifest al exportar un bundle (ID, ruta, hash, fecha).
  6. Inclusión en el manifiesto de la procedencia y metadatos completos del dataset.
  7. Generación de SHA256SUMS.txt incluyendo todos los archivos y bundles, sin auto-referencia.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import platform
import sys
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from scientific_core.data_audit import compute_file_sha256

logger = logging.getLogger(__name__)


def get_environment_info() -> Dict[str, Any]:
    """Recopila información del entorno técnico de ejecución sin exponer secretos."""
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def generate_sha256sums(target_dir: Union[str, Path]) -> Dict[str, str]:
    """
    Genera el archivo SHA256SUMS.txt con los hashes de todos los archivos del directorio.
    El archivo SHA256SUMS.txt NO se incluye a sí mismo (Mandato 11).
    """
    p = Path(target_dir)
    hash_dict = {}
    lines = []

    for item in sorted(p.rglob("*")):
        if item.is_file() and item.name != "SHA256SUMS.txt":
            rel_path = item.relative_to(p).as_posix()
            f_hash = compute_file_sha256(item)
            hash_dict[rel_path] = f_hash
            lines.append(f"{f_hash}  {rel_path}")

    sums_file = p / "SHA256SUMS.txt"
    sums_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hash_dict


def init_run_manifest(
    run_dir: Union[str, Path],
    run_id: str,
    config_effective: Dict[str, Any],
    test_only: bool = False,
) -> Path:
    """
    Inicializa el manifest con estado 'started' antes de iniciar la evaluación (Mandato 11).
    """
    p_dir = Path(run_dir)
    p_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": "2.0_revision_metodologica",
        "run_id": run_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "started",
        "test_only": test_only,
    }
    (p_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (p_dir / "config_effective.json").write_text(json.dumps(config_effective, indent=2, ensure_ascii=False), encoding="utf-8")
    (p_dir / "environment.json").write_text(json.dumps(get_environment_info(), indent=2, ensure_ascii=False), encoding="utf-8")
    return p_dir


def record_run_failure(
    run_dir: Union[str, Path],
    run_id: str,
    error_message: str,
) -> None:
    """
    Registra el fallo y estado parcial en el manifest si el proceso se interrumpe (Mandato 11).
    Preserva el started_at_utc original.
    """
    p_dir = Path(run_dir)
    m_path = p_dir / "manifest.json"
    manifest: Dict[str, Any] = {}
    if m_path.is_file():
        try:
            manifest = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    manifest["run_id"] = manifest.get("run_id", run_id)
    manifest["status"] = "failed"
    manifest["failed_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["error"] = str(error_message)
    m_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def save_run_artifacts(
    base_artifacts_dir: Union[str, Path],
    run_id: str,
    config_effective: Dict[str, Any],
    df: pd.DataFrame,
    audit_dict: Dict[str, Any],
    cv_results: Dict[str, Any],
    test_only: bool = False,
    bundle_info: Optional[Dict[str, Any]] = None,
    generator_metadata: Optional[Dict[str, Any]] = None,
    dataset_provenance: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Guarda la jerarquía completa de artefactos y actualiza el manifiesto a 'completed'.
    Preserva started_at_utc e incluye metadatos de generador y procedencia de datos.
    """
    run_dir = Path(base_artifacts_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Recuperar started_at_utc previo si existe
    m_path = run_dir / "manifest.json"
    started_at = None
    if m_path.is_file():
        try:
            prev_m = json.loads(m_path.read_text(encoding="utf-8"))
            started_at = prev_m.get("started_at_utc")
        except Exception:
            pass
    if not started_at:
        started_at = datetime.now(timezone.utc).isoformat()

    # 2. Configuración efectiva y entorno
    (run_dir / "config_effective.json").write_text(
        json.dumps(config_effective, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "environment.json").write_text(
        json.dumps(get_environment_info(), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 3. Dataset y auditoría
    (run_dir / "data_audit.json").write_text(
        json.dumps(audit_dict, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    df.to_csv(run_dir / "dataset.csv", index=False)

    # 4. Splits y tuning
    (run_dir / "splits.json").write_text(
        json.dumps(cv_results.get("splits_manifest", {}), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    tuning_df = cv_results.get("tuning_results_df")
    if tuning_df is not None and isinstance(tuning_df, pd.DataFrame):
        tuning_df.to_csv(run_dir / "tuning_results.csv", index=False)

    # 5. Métricas por fold y predicciones OOF
    fold_metrics_df = cv_results.get("fold_metrics_df")
    if fold_metrics_df is not None and isinstance(fold_metrics_df, pd.DataFrame):
        fold_metrics_df["run_id"] = run_id
        fold_metrics_df.to_csv(run_dir / "fold_metrics.csv", index=False)

    oof_df = cv_results.get("oof_predictions_df")
    if oof_df is not None and isinstance(oof_df, pd.DataFrame):
        oof_df["run_id"] = run_id
        oof_df.to_csv(run_dir / "oof_predictions.csv", index=False)

    summary_df = cv_results.get("summary_df")
    if summary_df is not None and isinstance(summary_df, pd.DataFrame):
        summary_df["run_id"] = run_id
        summary_df.to_csv(run_dir / "model_summary.csv", index=False)

    # 6. Manifiesto general completado con procedencia completa
    manifest = {
        "schema_version": "2.0_revision_metodologica",
        "run_id": run_id,
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "test_only": test_only,
        "dataset_rows": len(df),
        "dataset_sha256": compute_file_sha256(run_dir / "dataset.csv"),
        "best_model_id": cv_results.get("best_overall"),
        "cv_duration_seconds": cv_results.get("duration_seconds", 0.0),
        "generator_metadata": generator_metadata or {},
        "dataset_provenance": dataset_provenance or {},
        "bundle": bundle_info,
        "files": [
            "config_effective.json",
            "environment.json",
            "data_audit.json",
            "dataset.csv",
            "splits.json",
            "tuning_results.csv",
            "fold_metrics.csv",
            "oof_predictions.csv",
            "model_summary.csv",
        ],
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 7. Generar índice criptográfico SHA-256 (sin auto-referencia)
    generate_sha256sums(run_dir)

    return run_dir


def update_manifest_bundle(
    run_dir: Union[str, Path],
    bundle_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Actualiza el manifiesto del run tras exportar un bundle, registrando su ID,
    ruta, hash y componentes asociados, regenerando SHA256SUMS.txt.
    """
    r_dir = Path(run_dir)
    m_path = r_dir / "manifest.json"
    manifest: Dict[str, Any] = {}
    if m_path.is_file():
        try:
            manifest = json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    manifest["bundle"] = bundle_info
    manifest["bundle_exported_at_utc"] = datetime.now(timezone.utc).isoformat()
    m_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    generate_sha256sums(r_dir)
    return manifest
