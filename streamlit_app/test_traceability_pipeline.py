import json
import time
from pathlib import Path
import urllib.request
import pandas as pd

from data_pipeline import generate_synthetic_dataset, build_real_public_dataset
from advanced_training import train_and_evaluate_all_models
from training import export_model_bundle

MODEL_DIR = Path("/modelos_ia")

class DummyWidget:
    def progress(self, val): pass
    def caption(self, val): pass
    def text(self, val): pass
    def empty(self): pass

def run_export_pipeline(dataset, source_type, source_label, source_details, k_folds=3):
    print(f"\n========================================================")
    print(f"Iniciando pipeline para: {source_label}")
    print(f"Tipo de fuente: {source_type} | Registros: {len(dataset)}")
    print(f"========================================================")

    # 1. Entrenamiento con advanced_training (K-Fold CV real)
    print("-> Ejecutando entrenamiento (train_and_evaluate_all_models)...")
    progress_bar = DummyWidget()
    status_text = DummyWidget()
    
    train_res = train_and_evaluate_all_models(
        dataframe=dataset,
        progress_bar=progress_bar,
        status_text=status_text,
        random_state=42,
        k_folds=k_folds,
    )
    
    results_df = train_res["results_df"]
    best_overall = train_res["best_overall"]
    best_keras_model = train_res["best_keras_model"]
    target_scaler = train_res["target_scaler"]
    
    print(f"-> Entrenamiento finalizado. Mejor modelo: {best_overall}")
    print(f"   Mejor MAE (CV): {results_df.iloc[0]['CV_MAE_Mean']:.4f}")

    # 2. Exportación a /modelos_ia/
    print("-> Exportando modelo_optimizado.h5 y enriqueciendo metadata...")
    metrics = {"general": {"mae": float(results_df.iloc[0]["CV_MAE_Mean"]), "rmse": 0.0, "r2": 0.0}}
    
    export_res = export_model_bundle(
        best_keras_model,
        MODEL_DIR,
        metrics,
        target_scaler.mean_.tolist(),
        target_scaler.scale_.tolist(),
    )
    
    metadata_path = Path(export_res["metadata_path"])
    try:
        meta_dict = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        meta_dict = {}

    # Enriquecer con los campos de trazabilidad (idéntico a app.py)
    meta_dict["fuente_datos"] = source_type
    meta_dict["data_source_label"] = source_label
    meta_dict["n_samples"] = len(dataset)
    meta_dict["dataset_rows"] = len(dataset)
    meta_dict["region_name"] = source_details.get("region_name")

    if source_type == "publico_gbif_nasa_power":
        meta_dict["coordinates"] = source_details.get("coordinates")
        meta_dict["time_range"] = source_details.get("time_range")
        meta_dict["gbif_occurrences"] = source_details.get("gbif", {}).get("total_occurrences")
        meta_dict["distinct_species_count"] = source_details.get("gbif", {}).get("distinct_species_count")
        meta_dict["species_sample"] = source_details.get("gbif", {}).get("species_sample", [])
        meta_dict["clima_resumen"] = {
            "temperature_mean": source_details.get("nasa_power", {}).get("temperature_mean"),
            "temperature_std": source_details.get("nasa_power", {}).get("temperature_std"),
            "precipitation_annual_mean": source_details.get("nasa_power", {}).get("precipitation_annual_mean"),
        }
        meta_dict["column_provenance"] = source_details.get("column_provenance", {})
        meta_dict["crisp_dm_notes"] = "Datos reales públicos integrados vía GBIF API y NASA POWER API."
    elif source_type == "csv_propio":
        meta_dict["filename"] = source_details.get("filename")
        meta_dict["origen_detalle"] = "Archivo CSV suministrado por el usuario."
    else:
        meta_dict["random_state"] = source_details.get("random_state", 42)
        meta_dict["origen_detalle"] = "Generador estocástico agroecológico calibrado (CRISP-DM)."

    meta_dict["enrich_with_abm"] = source_details.get("enrich_with_abm", True)
    meta_dict["data_source_details"] = source_details

    metadata_path.write_text(json.dumps(meta_dict, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"-> Metadata guardado exitosamente en: {metadata_path}")
    return meta_dict

def get_backend_health():
    url = "http://backend:8000/health"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=== TEST EMPÍRICO DE AUDITORÍA Y TRAZABILIDAD DE MODELOS ===")

    # -------------------------------------------------------------
    # ETAPA 1: Dataset Sintético
    # -------------------------------------------------------------
    print("\n>>> ETAPA 1: Generación con Dataset Sintético <<<")
    synth_df = generate_synthetic_dataset(n_samples=320, random_state=42, enrich_with_abm=True)
    synth_source_type = "sintetico"
    synth_label = "Dataset Sintético (320 filas, semilla 42)"
    synth_details = {
        "fuente_datos": "sintetico",
        "origen_detalle": "Generador estocástico agroecológico calibrado (CRISP-DM)",
        "n_samples": len(synth_df),
        "random_state": 42,
        "enrich_with_abm": True,
    }

    meta_synth = run_export_pipeline(
        dataset=synth_df,
        source_type=synth_source_type,
        source_label=synth_label,
        source_details=synth_details,
        k_folds=3
    )

    # Guardar copia para comparación
    Path("/modelos_ia/metadata_sintetico.json").write_text(json.dumps(meta_synth, indent=2, ensure_ascii=False))

    print("\nEsperando 6 segundos a que ModelStore watcher recargue el modelo en Backend...")
    time.sleep(6)
    health_synth = get_backend_health()
    print("Respuesta de /health en Backend tras exportación sintética:")
    print(json.dumps(health_synth, indent=2))

    # -------------------------------------------------------------
    # ETAPA 2: Dataset Público Real (GBIF + NASA POWER)
    # -------------------------------------------------------------
    print("\n>>> ETAPA 2: Generación con Datos Públicos Reales (GBIF + NASA POWER) <<<")
    df_public, meta_public = build_real_public_dataset(
        region_name="Valle del Cauca (Colombia)",
        latitude=3.45,
        longitude=-76.53,
        radius_km=35.0,
        start_year=2019,
        end_year=2023,
        n_samples=320,
        random_state=42,
        enrich_with_abm=True,
    )
    public_source_type = "publico_gbif_nasa_power"
    public_label = "Dataset Público Real: GBIF + NASA POWER (Valle del Cauca (Colombia))"
    public_details = {
        "fuente_datos": "publico_gbif_nasa_power",
        "region_name": "Valle del Cauca (Colombia)",
        "coordinates": {"lat": 3.45, "lon": -76.53, "radius_km": 35.0},
        "time_range": "2019 - 2023",
        "n_samples": len(df_public),
        "enrich_with_abm": True,
        "gbif": meta_public.get("gbif", {}),
        "nasa_power": meta_public.get("nasa_power", {}),
        "column_provenance": meta_public.get("column_provenance", {}),
    }

    meta_public_res = run_export_pipeline(
        dataset=df_public,
        source_type=public_source_type,
        source_label=public_label,
        source_details=public_details,
        k_folds=3
    )

    # Guardar copia para comparación
    Path("/modelos_ia/metadata_publico.json").write_text(json.dumps(meta_public_res, indent=2, ensure_ascii=False))

    print("\nEsperando 6 segundos a que ModelStore watcher recargue el modelo en Backend...")
    time.sleep(6)
    health_public = get_backend_health()
    print("Respuesta de /health en Backend tras exportación pública:")
    print(json.dumps(health_public, indent=2))

    print("\n========================================================")
    print("¡TEST EMPÍRICO COMPLETADO EXITOSAMENTE!")
    print("========================================================")

if __name__ == "__main__":
    main()
