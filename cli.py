"""
cli.py
Herramienta CLI desacoplada de la interfaz Streamlit para auditoría, generación,
evaluación predictiva, exportación de bundles vinculada a runs, optimización multiobjetivo
y reconstrucción reproducible sin contaminación de datos.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

# Asegurar que el directorio raíz y backend están en sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "backend"))

from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS
from scientific_core.data_audit import (
    audit_dataset,
    classify_dataset_provenance,
    compute_file_sha256,
)
from scientific_core.generator import generate_coherent_dataset
from scientific_core.nested_cv import (
    ModelFactory,
    fit_and_predict_neural_outer,
    recompute_metrics_from_oof,
    run_nested_cv,
)
from scientific_core.model_bundle import (
    UniversalSurrogatePredictor,
    export_bundle,
    load_bundle,
)
from scientific_core.persistence import (
    generate_sha256sums,
    get_environment_info,
    init_run_manifest,
    record_run_failure,
    save_run_artifacts,
    update_manifest_bundle,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cli_revision")


def cmd_audit_data(args: argparse.Namespace) -> int:
    """Subcomando: Auditar dataset según política científica estricta o histórica."""
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Ruta de entrada no encontrada: %s", input_path)
        return 1

    if input_path.is_file():
        files_to_audit = [input_path]
    else:
        files_to_audit = list(input_path.glob("*.csv"))

    if not files_to_audit:
        logger.error("No se encontraron archivos CSV para auditar en: %s", input_path)
        return 1

    overall_passed = True
    reports = {}

    for f in sorted(files_to_audit):
        logger.info("Auditando archivo: %s con política: %s", f, args.policy)
        try:
            df = pd.read_csv(f)
            res = audit_dataset(df, policy=args.policy)
            reports[f.name] = res
            status_str = "APROBADO" if res["audit_passed"] else "FALLIDO"
            logger.info("Resultado para %s: %s (calidad: %s | procedencia: %s)",
                        f.name, status_str, res["data_quality"], res["data_provenance"])
            if not res["audit_passed"]:
                overall_passed = False
                for issue in res["issues"]:
                    logger.warning("  - Defecto: %s", issue)
        except Exception as e:
            logger.error("Error al procesar %s: %s", f, e)
            overall_passed = False
            reports[f.name] = {"audit_passed": False, "error": str(e)}

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Reporte consolidado guardado en: %s", out_p)

    return 0 if overall_passed else 1


def cmd_generate_data(args: argparse.Namespace) -> int:
    """Subcomando: Generar dataset con balance físico estricto y trazabilidad completa."""
    out_p = Path(args.output)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Generando dataset con N=%d, politica_abm=%s, seed=%d...",
        args.samples,
        args.abm_policy,
        args.seed,
    )
    df, meta = generate_coherent_dataset(
        n_samples=args.samples,
        random_state=args.seed,
        abm_policy=args.abm_policy,
        max_abm_simulations=args.max_abm_sims,
        test_mode=args.test_mode,
    )

    df.to_csv(out_p, index=False)
    logger.info("Dataset generado exitosamente en: %s (%d filas)", out_p, len(df))

    if args.save_metadata:
        meta_p = out_p.with_suffix(".json")
        meta_p.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Metadatos de generación guardados en: %s", meta_p)

    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """
    Subcomando: Ejecutar evaluación predictiva sin contaminación (Nested CV).
    Bloquea inmediatamente la ejecución si la auditoría de datos no es satisfactoria (Bloque 3).
    """
    cfg_p = Path(args.config)
    if not cfg_p.is_file():
        logger.error("Archivo de configuración no encontrado: %s", cfg_p)
        return 1

    config = json.loads(cfg_p.read_text(encoding="utf-8"))
    test_only = bool(config.get("test_only", False) or args.smoke)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"{'smoke_' if test_only else 'run_'}{timestamp}"
    base_out_dir = Path(args.output_dir or "artifacts/revision_metodologica")
    run_dir = base_out_dir / run_id

    # 1. Inicializar manifest con estado 'started' (preservando timestamp de inicio)
    init_run_manifest(run_dir=run_dir, run_id=run_id, config_effective=config, test_only=test_only)
    logger.info("Iniciando evaluación predictiva [run_id: %s] (test_only=%s)...", run_id, test_only)

    try:
        # 2. Cargar o generar dataset (Bloque 3: no generar datos silenciosamente si se pide evaluación)
        generator_meta: Dict[str, Any] = {}
        if args.dataset:
            d_path = Path(args.dataset)
            if not d_path.is_file():
                raise FileNotFoundError(f"Ruta de dataset especificada no existe: {args.dataset}")
            df = pd.read_csv(d_path)
            logger.info("Dataset cargado desde archivo: %s (%d filas)", args.dataset, len(df))
            generator_meta = {"source": "file", "path": str(d_path.resolve())}
        else:
            if not test_only and not getattr(args, "allow_synthetic", False):
                raise ValueError(
                    "No se especificó un dataset existente para evaluar (--dataset <ruta>). "
                    "Para evaluar rigurosamente debe proporcionar un dataset preexistente "
                    "o indicar explícitamente --smoke o --allow-synthetic."
                )
            d_cfg = config.get("data", {})
            n_samples = d_cfg.get("n_samples", 40 if test_only else 320)
            abm_pol = d_cfg.get("abm_policy", "corrected_none" if test_only else "corrected_full")
            max_sims = 2 if test_only else None
            df, meta = generate_coherent_dataset(
                n_samples=n_samples,
                random_state=config.get("seed", 42),
                abm_policy=abm_pol,
                max_abm_simulations=max_sims,
                test_mode=test_only,
            )
            generator_meta = meta
            logger.info("Dataset generado para evaluación: %d filas", len(df))

        # 3. Auditoría previa del dataset (Bloque 3: bloquea la evaluación si no pasa)
        audit_res = audit_dataset(df, policy="corrected")
        if not audit_res.get("audit_passed", False):
            issues = audit_res.get("issues", [])
            err_msg = f"Auditoría previa falló: el dataset no cumple los contratos metodológicos: {issues}"
            logger.error(err_msg)
            # Guardar auditoría y dataset para trazabilidad del rechazo
            (run_dir / "data_audit.json").write_text(
                json.dumps(audit_res, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            df.to_csv(run_dir / "dataset.csv", index=False)
            record_run_failure(run_dir=run_dir, run_id=run_id, error_message=err_msg)
            return 1

        provenance_info = classify_dataset_provenance(df)

        # 4. Ejecución de Nested Cross-Validation sin contaminación
        cv_res = run_nested_cv(df, config, status_callback=lambda msg: logger.info("[CV] %s", msg))

        # 5. Guardar artefactos completos y actualizar manifest a 'completed' (Bloques 9 y 10)
        save_run_artifacts(
            base_artifacts_dir=base_out_dir,
            run_id=run_id,
            config_effective=config,
            df=df,
            audit_dict=audit_res,
            cv_results=cv_res,
            test_only=test_only,
            generator_metadata=generator_meta,
            dataset_provenance=provenance_info,
        )
        logger.info("Ejecución completada con éxito. Artefactos guardados en: %s", run_dir)
        logger.info("Ganador seleccionado (menor MAE macro): %s", cv_res["best_overall"])
        return 0

    except Exception as e:
        logger.error("Error durante la ejecución del run %s: %s", run_id, e)
        record_run_failure(run_dir=run_dir, run_id=run_id, error_message=str(e))
        return 1


def cmd_recompute_metrics(args: argparse.Namespace) -> int:
    """Subcomando: Reconstruir métricas a partir del archivo oof_predictions.csv."""
    oof_p = Path(args.oof)
    if not oof_p.is_file():
        logger.error("Archivo OOF no encontrado: %s", oof_p)
        return 1

    oof_df = pd.read_csv(oof_p)
    recomputed = recompute_metrics_from_oof(oof_df)
    print(json.dumps(recomputed, indent=2, ensure_ascii=False))
    return 0


def cmd_export_model(args: argparse.Namespace) -> int:
    """
    Subcomando: Exportar bundle universal vinculado estrictamente a un run de evaluación (Bloque 7 y Bloque 10).
    Aplica:
      - Agregación reproducible de hiperparámetros a través de todos los folds (sin sesgo de fold único).
      - Reajuste sobre el dataset íntegro del run evaluado.
      - Actualización automática del manifiesto del run con el bundle exportado.
      - Rechazo de bundles científicos desde runs smoke o incompletos.
    """
    target_input = args.run_dir or args.run_id
    if not target_input:
        logger.error("Debe proporcionar --run-dir o --run-id de una ejecución completada.")
        return 1

    run_path = Path(target_input)
    if not run_path.is_dir():
        cand_path = Path("artifacts/revision_metodologica") / target_input
        if cand_path.is_dir():
            run_path = cand_path
        else:
            logger.error("Directorio de run no encontrado: %s", run_path)
            return 1

    # 1. Comprobar manifest.json
    manifest_file = run_path / "manifest.json"
    if not manifest_file.is_file():
        logger.error("No se encontró manifest.json en el run: %s", run_path)
        return 1

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    status = manifest.get("status")
    if status != "completed":
        logger.error(
            "El run %s no puede exportarse para uso científico porque su estado es '%s' (se exige 'completed').",
            run_path.name,
            status,
        )
        return 1

    is_test_only = bool(manifest.get("test_only", False))
    if is_test_only and not getattr(args, "force_test_bundle", False):
        logger.warning(
            "El run %s es test_only (smoke). Se generará un bundle explícitamente etiquetado como test_only/is_test_bundle.",
            run_path.name,
        )

    # 2. Cargar dataset identificado del experimento
    dataset_file = run_path / "dataset.csv"
    if not dataset_file.is_file():
        logger.error("No se encontró dataset.csv en el run: %s", run_path)
        return 1

    df = pd.read_csv(dataset_file)
    current_dataset_hash = compute_file_sha256(dataset_file)
    expected_dataset_hash = manifest.get("dataset_sha256")
    if expected_dataset_hash and current_dataset_hash != expected_dataset_hash:
        logger.error("Discrepancia en el hash del dataset. Esperado: %s, Actual: %s", expected_dataset_hash, current_dataset_hash)
        return 1

    X = df[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[TARGET_COLUMNS].to_numpy(dtype=np.float32)

    # 3. Determinar familia a exportar y seleccionar hiperparámetros ganadores de forma agregada (Bloque 7)
    family = args.family or manifest.get("best_model_id")
    if not family:
        summary_file = run_path / "model_summary.csv"
        if summary_file.is_file():
            sum_df = pd.read_csv(summary_file)
            family = str(sum_df.iloc[0]["model_id"])
        else:
            family = "random_forest"

    tuning_file = run_path / "tuning_results.csv"
    best_params: Dict[str, Any] = {}
    optimal_epochs = 20
    selection_policy: Dict[str, Any] = {
        "method": "default_fallback",
        "description": "Sin tuning_results previo",
    }

    if tuning_file.is_file():
        tuning_df = pd.read_csv(tuning_file)
        try:
            from scientific_core.nested_cv import select_final_hyperparameters
            best_params, optimal_epochs, selection_policy = select_final_hyperparameters(
                tuning_df=tuning_df,
                model_family=family,
                allow_adaptation=is_test_only,
            )
        except Exception as exc:
            logger.error("Error al seleccionar hiperparámetros de forma agregada: %s", exc)
            raise

    # Recuperar referencia de evaluación de model_summary.csv
    cv_eval_ref: Dict[str, Any] = {}
    summary_file = run_path / "model_summary.csv"
    if summary_file.is_file():
        sum_df = pd.read_csv(summary_file)
        fam_sum = sum_df[sum_df["model_id"] == family]
        if not fam_sum.empty:
            row_sum = fam_sum.iloc[0]
            cv_eval_ref = {
                "CV_MAE_Mean": float(row_sum["CV_MAE_Mean"]),
                "CV_RMSE_Mean": float(row_sum["CV_RMSE_Mean"]),
                "CV_R2_Mean": float(row_sum["CV_R2_Mean"]),
                "nota_metodologica": (
                    "Métricas derivadas de Nested Cross-Validation en fase de desarrollo. "
                    "No representan una evaluación independiente del artefacto final reajustado."
                ),
            }

    # 4. Reajuste final sobre el dataset completo
    scaler_x = StandardScaler().fit(X)
    scaler_y = StandardScaler().fit(y)

    config_eff_file = run_path / "config_effective.json"
    seed = 42
    if config_eff_file.is_file():
        try:
            cfg_eff = json.loads(config_eff_file.read_text(encoding="utf-8"))
            seed = int(cfg_eff.get("outer_cv", {}).get("seed", 42))
        except Exception:
            pass

    if family in ["dnn", "autoencoder_mlp"]:
        _, _, _, final_model = fit_and_predict_neural_outer(
            model_family=family,
            params=best_params,
            X_train_outer=X,
            y_train_outer=y,
            X_test_outer=X[:1],
            optimal_epochs=optimal_epochs,
            seed=seed,
        )
    else:
        final_model = ModelFactory.create_model(family, best_params, seed=seed)
        final_model.fit(scaler_x.transform(X), scaler_y.transform(y))

    observed_ranges = {col: [float(df[col].min()), float(df[col].max())] for col in FEATURE_COLUMNS}

    overlay_metadata = {
        "run_id": manifest.get("run_id", run_path.name),
        "run_dir": str(run_path),
        "test_only": is_test_only,
        "is_test_bundle": is_test_only,
        "dataset_rows": len(df),
        "dataset_sha256": current_dataset_hash,
        "selected_family": family,
        "winning_hyperparameters": best_params,
        "final_selection_policy": selection_policy,
        "optimal_epochs": optimal_epochs if family in ["dnn", "autoencoder_mlp"] else None,
        "observed_training_ranges": observed_ranges,
        "cv_evaluation_reference": cv_eval_ref,
        "fuente_datos": "calibrado_revision",
        "region_name": "Valle del Cauca (Colombia)",
    }

    predictor = UniversalSurrogatePredictor(
        model=final_model,
        model_type=family,
        scaler_x=scaler_x,
        scaler_y=scaler_y,
        metadata=overlay_metadata,
    )

    out_dir = Path(args.output_dir)
    res = export_bundle(predictor, out_dir, metadata_overlay=overlay_metadata, strict_scientific=True)
    logger.info("Bundle universal exportado y verificado en: %s", res["export_dir"])
    logger.info("Identificador persistente de bundle: %s", res["bundle_id"])

    # Actualizar manifest del run con la información del bundle exportado (Bloque 10)
    bundle_manifest_info = {
        "bundle_id": res["bundle_id"],
        "export_dir": str(res["export_dir"]),
        "model_type": res["model_type"],
        "model_file": str(res["model_file"]),
        "metadata_file": str(res["metadata_file"]),
        "file_hashes": res.get("file_hashes", {}),
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_only": is_test_only,
    }
    update_manifest_bundle(run_dir=run_path, bundle_info=bundle_manifest_info)

    if out_dir.resolve().is_relative_to(run_path.resolve()):
        generate_sha256sums(run_path)

    return 0


def cmd_validate_bundle(args: argparse.Namespace) -> int:
    """Subcomando: Validar integridad y consistencia de un bundle exportado."""
    b_dir = Path(args.bundle_dir)
    logger.info("Validando bundle en: %s", b_dir)
    allow_test = getattr(args, "allow_test_bundle", False)
    try:
        predictor = load_bundle(b_dir, allow_test_bundle=allow_test)
        dummy_x = np.array([[50.0, 20.0, 8.0, 25.0, 70.0, 23.5, 1050.0, 0.65]], dtype=np.float32)
        preds = predictor.predict(dummy_x)
        assert preds.shape == (1, 3), f"Forma de predicción inesperada: {preds.shape}"
        logger.info(
            "Bundle válido. Bundle ID: %s | Tipo: %s. Predicción test: %s",
            predictor.bundle_id,
            predictor.model_type,
            preds.tolist(),
        )
        return 0
    except Exception as e:
        logger.error("Validación de bundle fallida: %s", e)
        return 1


def cmd_optimize(args: argparse.Namespace) -> int:
    """Subcomando: Ejecutar optimización multiobjetivo con NSGA-II y control estricto de dominio."""
    from app.services.model_store import model_store
    from app.services.optimization import run_simulation

    if args.model_dir:
        model_store.model_dir = Path(args.model_dir)
        if args.test_mode:
            model_store.allow_test_bundle = True
        model_store.load()
    elif not model_store.is_ready:
        if args.test_mode:
            model_store.allow_test_bundle = True
        model_store.load()

    if not model_store.is_ready:
        logger.error("No hay modelo cargado para optimizar. Especifique --model-dir apuntando a un bundle válido.")
        return 1

    payload = {
        "pesticide_level": args.pesticide_level,
        "min_natural_area_pct": args.min_natural_area_pct,
        "climate_scenario": args.climate_scenario,
        "bbox": args.bbox,
        "test_mode": args.test_mode,
    }

    if args.geometry_file and Path(args.geometry_file).is_file():
        geom_dict = json.loads(Path(args.geometry_file).read_text(encoding="utf-8"))
        payload["geometry"] = geom_dict

    logger.info("Ejecutando optimización de paisaje con payload: %s", payload)
    try:
        result = run_simulation(payload)
        logger.info("Estado de optimización: %s", result.get("status", "success"))
        logger.info("Evaluaciones del algoritmo: %d | Soluciones retornadas: %d | Frente Pareto verificado: %d",
                    result.get("algorithm_evaluations_total", result.get("pareto_candidates_evaluated", 0)),
                    result.get("pareto_solutions_returned", 0),
                    result.get("pareto_verified_count", 0))

        if result.get("best_solution"):
            best = result["best_solution"]
            logger.info("Mejor solución: Rendimiento=%.2f, Abundancia=%.2f",
                        best.get("crop_yield_index", 0), best.get("pollinator_abundance_index", 0))
            logger.info("Delta Rendimiento: %s | Delta Abundancia: %s%%",
                        result.get("delta_yield"), result.get("delta_pollinators"))
            logger.info("Estado de hipótesis: %s", result.get("hypothesis_status"))

        if args.output:
            out_p = Path(args.output)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Resultado de optimización guardado en: %s", out_p)
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))

        return 0 if result.get("status") != "infeasible" else 2

    except Exception as exc:
        logger.error("Error en optimización: %s", exc)
        return 1


def cmd_smoke(args: argparse.Namespace) -> int:
    """Subcomando directo: Ejecutar smoke test completo T19."""
    logger.info("=== EJECUTANDO SMOKE TEST T19 (test_only=true) ===")
    smoke_cfg_path = ROOT_DIR / "configs" / "smoke_test.json"
    if not smoke_cfg_path.is_file():
        logger.error("Configuración smoke_test.json no encontrada.")
        return 1

    args.config = str(smoke_cfg_path)
    args.smoke = True
    args.dataset = None
    args.allow_synthetic = True
    args.output_dir = args.output_dir or "artifacts/revision_metodologica"
    return cmd_evaluate(args)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CLI de Revisión Metodológica — Gemelo Digital Agroecológico",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # 1. audit-data
    p_audit = subparsers.add_parser("audit-data", help="Audita integridad de dataset")
    p_audit.add_argument("--input", required=True, help="Ruta al archivo CSV o directorio")
    p_audit.add_argument("--policy", default="corrected", choices=["corrected", "historical_audit"], help="Política de auditoría")
    p_audit.add_argument("--output", help="Ruta opcional para guardar reporte JSON")

    # 2. generate-data
    p_gen = subparsers.add_parser("generate-data", help="Genera dataset corregido")
    p_gen.add_argument("--output", required=True, help="Ruta de salida del archivo CSV")
    p_gen.add_argument("--samples", type=int, default=320, help="Número de muestras")
    p_gen.add_argument("--abm-policy", default="corrected_none", choices=["corrected_none", "corrected_full", "historical_partial"], help="Política ABM")
    p_gen.add_argument("--max-abm-sims", type=int, default=None, help="Límite de simulaciones para pruebas")
    p_gen.add_argument("--seed", type=int, default=42, help="Semilla pseudoaleatoria")
    p_gen.add_argument("--save-metadata", action="store_true", help="Guardar metadatos JSON junto al CSV")
    p_gen.add_argument("--test-mode", action="store_true", help="Modo test para pruebas desacopladas")

    # 3. evaluate
    p_eval = subparsers.add_parser("evaluate", help="Ejecuta CV anidada sin contaminación")
    p_eval.add_argument("--config", default="configs/revision_metodologica.json", help="Ruta de configuración")
    p_eval.add_argument("--dataset", help="Ruta opcional a CSV preexistente")
    p_eval.add_argument("--allow-synthetic", action="store_true", help="Permite generar datos sintéticos si no se pasa dataset")
    p_eval.add_argument("--output-dir", default="artifacts/revision_metodologica", help="Directorio base de artefactos")
    p_eval.add_argument("--smoke", action="store_true", help="Forzar modo smoke rápido")

    # 4. recompute-metrics
    p_recomp = subparsers.add_parser("recompute-metrics", help="Reconstruye métricas desde OOF")
    p_recomp.add_argument("--oof", required=True, help="Ruta al archivo oof_predictions.csv")

    # 5. export-model
    p_export = subparsers.add_parser("export-model", help="Entrena y exporta bundle universal vinculado a un run")
    p_export.add_argument("--run-dir", help="Directorio del run completado")
    p_export.add_argument("--run-id", help="Identificador del run completado (en artifacts/revision_metodologica)")
    p_export.add_argument("--family", choices=["ridge", "random_forest", "xgboost", "dnn", "autoencoder_mlp"], help="Familia a exportar")
    p_export.add_argument("--output-dir", required=True, help="Directorio destino del bundle")
    p_export.add_argument("--force-test-bundle", action="store_true", help="Permitir exportar bundle de test")

    # 6. validate-bundle
    p_val = subparsers.add_parser("validate-bundle", help="Valida un bundle exportado")
    p_val.add_argument("--bundle-dir", required=True, help="Directorio del bundle a validar")
    p_val.add_argument("--allow-test-bundle", action="store_true", help="Permitir validar bundles de test")

    # 7. optimize
    p_opt = subparsers.add_parser("optimize", help="Ejecuta optimización multiobjetivo con NSGA-II")
    p_opt.add_argument("--pesticide-level", type=float, default=20.0, help="Nivel de pesticidas (0-100)")
    p_opt.add_argument("--min-natural-area-pct", type=float, default=20.0, help="Área natural mínima (%%)")
    p_opt.add_argument("--climate-scenario", default="current", choices=["current", "warm", "dry", "extreme"], help="Escenario climático")
    p_opt.add_argument("--bbox", type=float, nargs=4, default=[3.4, -76.6, 3.6, -76.4], help="Bounding box [min_lat, min_lon, max_lat, max_lon]")
    p_opt.add_argument("--geometry-file", help="Archivo GeoJSON opcional con polígono")
    p_opt.add_argument("--output", help="Ruta opcional para guardar resultado JSON")
    p_opt.add_argument("--model-dir", help="Directorio del bundle de modelo a utilizar para optimizar")
    p_opt.add_argument("--test-mode", action="store_true", help="Modo test desacoplado")

    # 8. smoke
    p_smoke = subparsers.add_parser("smoke", help="Ejecuta el smoke test integral desacoplado (T19)")
    p_smoke.add_argument("--output-dir", default="artifacts/revision_metodologica", help="Directorio destino")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    command_map = {
        "audit-data": cmd_audit_data,
        "generate-data": cmd_generate_data,
        "evaluate": cmd_evaluate,
        "recompute-metrics": cmd_recompute_metrics,
        "export-model": cmd_export_model,
        "validate-bundle": cmd_validate_bundle,
        "optimize": cmd_optimize,
        "smoke": cmd_smoke,
    }

    handler = command_map.get(args.command)
    if handler:
        return handler(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
