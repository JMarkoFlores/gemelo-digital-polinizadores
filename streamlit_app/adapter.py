"""
streamlit_app/adapter.py
Adaptador desacoplado y comprobable para el ciclo de vida de entrenamiento,
persistencia y exportación de modelos en Streamlit (Auditoría 04, Bloque 1).

Garantiza:
  1. Inicialización formal del manifest con estado 'started' antes del entrenamiento.
  2. Persistencia de la configuración efectivamente ejecutada (modelos, semillas, folds, modo).
  3. Registro explícito de fallos ('failed') ante cualquier excepción en entrenamiento.
  4. Persistencia de los 11 artefactos normalizados mediante save_run_artifacts respetando contratos.
  5. Vinculación estricta de la exportación al dataset y run evaluados (sin peeking al estado UI mutado).
  6. Actualización trazable de manifest.json con update_manifest_bundle.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
import numpy as np
import pandas as pd

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.data_audit import (
    audit_dataset,
    classify_dataset_provenance,
    compute_file_sha256,
)
from scientific_core.persistence import (
    init_run_manifest,
    record_run_failure,
    save_run_artifacts,
    update_manifest_bundle,
)
from scientific_core.model_bundle import (
    UniversalSurrogatePredictor,
    export_bundle,
)
from streamlit_app.advanced_training import train_and_evaluate_all_models

logger = logging.getLogger(__name__)


def prepare_streamlit_run_config(
    k_folds: int = 5,
    tune_hyperparameters: bool = False,
    scientific_mode: bool = False,
    random_state: int = 42,
    config_path: Optional[Union[str, Path]] = None,
    group_duplicates: Optional[bool] = None,
    base_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construye la configuración efectiva única que gobernará tanto el entrenamiento
    como la persistencia (Auditoría 05, Hallazgo 1).
    """
    import copy
    root_dir = Path(__file__).resolve().parent.parent

    if base_config is not None:
        config = copy.deepcopy(base_config)
    elif config_path is not None:
        cfg_file = Path(config_path)
        if not cfg_file.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_path}")
        with open(cfg_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        cfg_file = root_dir / "configs" / "revision_metodologica.json"
        if not cfg_file.exists():
            cfg_file = root_dir / "configs" / "smoke_test.json"
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {
                "outer_cv": {"n_splits": k_folds, "seed": random_state, "group_duplicates": True},
                "inner_cv": {"n_splits": 3, "seed": random_state + 1000},
                "models": {
                    "ridge": {"enabled": True, "param_grid": [{"alpha": 0.1}, {"alpha": 1.0}, {"alpha": 10.0}]},
                    "random_forest": {"enabled": True, "param_grid": [{"n_estimators": 100, "max_depth": 10}]},
                },
            }

    outer_cfg = config.setdefault("outer_cv", {})
    outer_cfg["n_splits"] = int(k_folds)
    outer_cfg["seed"] = int(random_state)
    config["seed"] = int(random_state)

    if group_duplicates is not None:
        requested_group_duplicates = bool(group_duplicates)
    else:
        requested_group_duplicates = bool(outer_cfg.get("group_duplicates", True))

    # Regla metodológica: En modo científico estricto no se permite desactivar group_duplicates
    if scientific_mode:
        if not requested_group_duplicates:
            raise ValueError(
                "Configuración científica rechazada: 'group_duplicates' no puede ser False en modo científico estricto. "
                "El protocolo metodológico exige agrupar instancias duplicadas mediante GroupKFold para prevenir fuga de datos."
            )
        outer_cfg["group_duplicates"] = True
        config["scientific_mode"] = True
        config["test_only"] = False
        config["allow_missing_dependencies"] = False
    else:
        outer_cfg["group_duplicates"] = requested_group_duplicates
        config["scientific_mode"] = False
        config["test_only"] = True
        config["allow_missing_dependencies"] = True

    config["tune_hyperparameters"] = bool(tune_hyperparameters)
    if not tune_hyperparameters:
        for fam, m_cfg in config.get("models", {}).items():
            grid = m_cfg.get("param_grid", [{}])
            if grid:
                m_cfg["param_grid"] = [grid[0]]

    return config


def execute_streamlit_training_run(
    dataframe: pd.DataFrame,
    k_folds: int = 5,
    tune_hyperparameters: bool = False,
    scientific_mode: bool = False,
    random_state: int = 42,
    group_duplicates: Optional[bool] = None,
    data_source_type: str = "sintetico",
    data_source_label: Optional[str] = None,
    data_source_details: Optional[Dict[str, Any]] = None,
    progress_bar: Any = None,
    status_text: Any = None,
    base_artifacts_dir: Optional[Union[str, Path]] = None,
    config_path: Optional[Union[str, Path]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el ciclo integral de evaluación en Streamlit con trazabilidad y persistencia formal:
      1. Auditoría previa del dataset.
      2. Construcción de una sola configuración efectiva (o recepción directa de config).
      3. Inicialización del manifest con estado 'started'.
      4. Ejecución de Nested CV pasando exactamente la misma configuración efectiva.
      5. Persistencia de artefactos con save_run_artifacts ('completed' o 'failed').
      6. Vinculación del dataset entrenado para prevenir desajustes en exportación.
    """
    if base_artifacts_dir is None:
        base_dir = Path(__file__).resolve().parent.parent / "artifacts" / "revision_metodologica"
    else:
        base_dir = Path(base_artifacts_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    # 1. Auditoría previa
    audit_res = audit_dataset(dataframe, policy="corrected")
    if not audit_res.get("audit_passed", False):
        issues = audit_res.get("rejection_reasons") or audit_res.get("issues") or []
        raise ValueError(f"El dataset no superó la auditoría metodológica: {issues}")

    # 2. Configuración efectiva y generación de identificadores (Configuración única)
    if config is not None:
        config_effective = config
    else:
        config_effective = prepare_streamlit_run_config(
            k_folds=k_folds,
            tune_hyperparameters=tune_hyperparameters,
            scientific_mode=scientific_mode,
            random_state=random_state,
            config_path=config_path,
            group_duplicates=group_duplicates,
        )

    is_scientific = bool(config_effective.get("scientific_mode", scientific_mode))
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    mode_prefix = "streamlit_scientific" if is_scientific else "streamlit_exploratory"
    run_id = f"{mode_prefix}_{run_ts}"
    run_dir = base_dir / run_id

    # 3. Inicializar manifest con estado 'started' ANTES del entrenamiento
    init_run_manifest(
        run_dir=run_dir,
        run_id=run_id,
        config_effective=config_effective,
        test_only=not is_scientific,
    )

    # 4. Ejecución del entrenamiento pasando exactamente la misma config_effective y semilla efectiva
    try:
        effective_run_seed = int(config_effective.get("seed", config_effective.get("outer_cv", {}).get("seed", random_state)))
        t_res = train_and_evaluate_all_models(
            dataframe=dataframe,
            progress_bar=progress_bar,
            status_text=status_text,
            config=config_effective,
            scientific_mode=is_scientific,
            random_state=effective_run_seed,
        )
    except Exception as eval_err:
        record_run_failure(run_dir=run_dir, run_id=run_id, error_message=str(eval_err))
        logger.error("Error durante el entrenamiento en Streamlit [run_id: %s]: %s", run_id, eval_err)
        raise

    # 5. Persistencia de artefactos con save_run_artifacts
    cv_res = t_res.get("cv_results", {})
    gen_meta = dict(data_source_details or {})
    gen_meta["source_type"] = data_source_type
    gen_meta["source_label"] = data_source_label or f"Dataset ({len(dataframe)} filas)"

    prov_info = classify_dataset_provenance(dataframe)

    try:
        save_run_artifacts(
            base_artifacts_dir=base_dir,
            run_id=run_id,
            config_effective=config_effective,
            df=dataframe,
            audit_dict=audit_res,
            cv_results=cv_res,
            test_only=not scientific_mode,
            generator_metadata=gen_meta,
            dataset_provenance=prov_info,
        )
    except Exception as persist_err:
        err_msg = f"Fallo al persistir artefactos completos del run: {persist_err}"
        record_run_failure(run_dir=run_dir, run_id=run_id, error_message=err_msg)
        if scientific_mode:
            raise RuntimeError(f"Fallo crítico de persistencia en modo científico: {persist_err}") from persist_err
        else:
            logger.warning("Advertencia en persistencia exploratoria: %s", persist_err)

    # 6. Vincular metadatos e inmutabilidad del dataset de entrenamiento
    t_res["run_id"] = run_id
    t_res["run_dir"] = str(run_dir)
    t_res["training_dataset"] = dataframe.copy()
    dataset_file = run_dir / "dataset.csv"
    if dataset_file.is_file():
        t_res["dataset_sha256"] = compute_file_sha256(dataset_file)
    t_res["scientific_mode"] = scientific_mode
    t_res["test_only"] = not scientific_mode
    t_res["data_source_type"] = data_source_type
    t_res["data_source_label"] = data_source_label
    t_res["data_source_details"] = gen_meta

    return t_res


def export_streamlit_model(
    training_result: Dict[str, Any],
    export_dir: Union[str, Path],
    force_test_bundle: bool = False,
) -> Dict[str, Any]:
    """
    Exporta un bundle universal vinculado estrictamente a un entrenamiento registrado:
      1. Extrae el predictor y el dataset exactamente entrenado.
      2. Calcula rangos observados empíricos sobre el dataset del run.
      3. Invoca export_bundle con validación y rollback atómico.
      4. Actualiza el manifest.json del run mediante update_manifest_bundle.
    """
    predictor: Optional[UniversalSurrogatePredictor] = training_result.get("predictor")
    if predictor is None:
        raise ValueError("El resultado de entrenamiento no contiene un predictor universal válido para exportar.")

    train_df: Optional[pd.DataFrame] = training_result.get("training_dataset")
    if train_df is None or train_df.empty:
        raise ValueError("El resultado de entrenamiento no tiene vinculado el dataset de entrenamiento ('training_dataset').")

    run_dir_str = training_result.get("run_dir")
    run_id = training_result.get("run_id")
    is_scientific = bool(training_result.get("scientific_mode", False))
    is_test_bundle = bool(training_result.get("test_only", not is_scientific)) or force_test_bundle

    if is_scientific and not run_dir_str:
        raise ValueError("Exportación rechazada en modo científico: el run de entrenamiento no fue persistido.")

    # Rangos observados obligatorios reales procedentes del dataset evaluado
    observed_ranges = {
        col: [float(train_df[col].min()), float(train_df[col].max())]
        for col in FEATURE_COLUMNS
        if col in train_df.columns
    }

    results_df = training_result.get("results_df")
    real_metrics: Dict[str, float] = {}
    if results_df is not None and isinstance(results_df, pd.DataFrame) and not results_df.empty:
        first_row = results_df.iloc[0]
        real_metrics = {
            "macro_mae": float(first_row.get("CV_MAE_Mean", 0.0)),
            "macro_rmse": float(first_row.get("CV_RMSE_Mean", 0.0)),
            "macro_r2": float(first_row.get("CV_R2_Mean", 0.0)),
            "macro_mape": float(first_row.get("CV_MAPE_Mean", 0.0)),
            "macro_expl_var": float(first_row.get("CV_ExplVar_Mean", 0.0)),
        }

    source_details = dict(training_result.get("data_source_details") or {})
    raw_region = source_details.get("region_name")
    data_source_type = training_result.get("data_source_type") or source_details.get("fuente_datos", "desconocido")
    filename = str(source_details.get("filename") or "")

    if raw_region:
        resolved_region = str(raw_region)
    elif data_source_type == "sintetico" or "sintetico" in filename.lower() or "fixture_funcional" in filename.lower():
        resolved_region = "Dataset sintético (sin anclaje territorial)"
    else:
        resolved_region = "Procedencia geográfica no especificada"

    coords = source_details.get("coordinates")
    resolved_coords = coords if (isinstance(coords, dict) and "lat" in coords and "lon" in coords) else None

    overlay = {
        "run_id": run_id,
        "run_dir": run_dir_str,
        "test_only": is_test_bundle,
        "is_test_bundle": is_test_bundle,
        "fuente_datos": data_source_type,
        "data_source_label": training_result.get("data_source_label"),
        "n_samples": len(train_df),
        "dataset_rows": len(train_df),
        "region_name": resolved_region,
        "coordinates": resolved_coords,
        "region_bounds": resolved_coords,
        "observed_training_ranges": observed_ranges,
        "metrics": real_metrics,
        "final_selection_policy": training_result.get("final_selection_policy"),
        "final_seed": training_result.get("final_seed"),
        "seed": training_result.get("final_seed"),
        "winning_hyperparameters": training_result.get("best_params"),
    }

    # Exportación atómica
    export_res = export_bundle(
        predictor=predictor,
        export_dir=export_dir,
        metadata_overlay=overlay,
        strict_scientific=is_scientific,
    )

    # Actualizar manifest del run si existe
    if run_dir_str:
        r_path = Path(run_dir_str)
        if (r_path / "manifest.json").is_file():
            update_manifest_bundle(r_path, export_res)

    return export_res
