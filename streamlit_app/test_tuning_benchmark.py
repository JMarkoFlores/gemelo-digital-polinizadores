import time
import pandas as pd
from data_pipeline import generate_synthetic_dataset
from advanced_training import train_and_evaluate_all_models

class DummyProgress:
    def progress(self, val): pass

class DummyStatus:
    def text(self, val): 
        # print status updates cleanly
        if "Sintonizando" in val or "Evaluando" in val:
            print(f"  [Status] {val}")
    def empty(self): pass

def run_benchmark():
    print("=" * 60)
    print("BENCHMARK COMPARATIVO: MODO SIN TUNING VS MODO CON TUNING")
    print("=" * 60)

    df = generate_synthetic_dataset(n_samples=320, random_state=42, enrich_with_abm=False)
    print(f"Dataset generado: {len(df)} registros.")

    # 1. MODO SIN TUNING (Valores Fijos por defecto)
    print("\n>>> 1. EJECUTANDO MODO SIN TUNING (k_folds=3) <<<")
    p_bar = DummyProgress()
    s_text = DummyStatus()
    
    t0 = time.time()
    res_no_tuning = train_and_evaluate_all_models(
        dataframe=df,
        progress_bar=p_bar,
        status_text=s_text,
        random_state=42,
        k_folds=3,
        tune_hyperparameters=False
    )
    time_no_tuning = time.time() - t0
    print(f"Tiempo Total (Sin Tuning): {time_no_tuning:.2f} segundos.")
    print(f"Mejor Modelo: {res_no_tuning['best_overall']}")
    print(f"R² Medio del Ganador: {res_no_tuning['results_df'].iloc[0]['CV_R2_Mean']:.4f}")

    # 2. MODO CON TUNING (RandomizedSearchCV + NAS)
    print("\n>>> 2. EJECUTANDO MODO CON TUNING (k_folds=3) <<<")
    t0 = time.time()
    res_with_tuning = train_and_evaluate_all_models(
        dataframe=df,
        progress_bar=p_bar,
        status_text=s_text,
        random_state=42,
        k_folds=3,
        tune_hyperparameters=True
    )
    time_with_tuning = time.time() - t0
    ht = res_with_tuning["hyperparameter_tuning"]
    print(f"\nTiempo Total (Con Tuning): {time_with_tuning:.2f} segundos.")
    print(f"Tiempo específico de búsqueda de hiperparámetros: {ht['tiempo_total_tuning']:.2f} segundos.")
    print(f"Mejor Modelo: {res_with_tuning['best_overall']}")
    print(f"R² Medio del Ganador: {res_with_tuning['results_df'].iloc[0]['CV_R2_Mean']:.4f}")

    print("\n" + "=" * 60)
    print("TABLA DETALLADA: MEJORES HIPERPARÁMETROS ENCONTRADOS")
    print("=" * 60)
    print(ht["tuning_df"].to_string(index=False))

    print("\n" + "=" * 60)
    print("TABLA RESUMEN POR MODELO")
    print("=" * 60)
    print(ht["summary_df"].to_string(index=False))

    print("\n" + "=" * 60)
    print("INTERPRETACIÓN OBJETIVA Y EXPLICABILIDAD GENERADA")
    print("=" * 60)
    print(ht["interpretacion"])

    print("\n" + "=" * 60)
    print("RESUMEN DE TIEMPOS Y FACTIBILIDAD EN CLASE/DEMO")
    print("=" * 60)
    delta = time_with_tuning - time_no_tuning
    print(f"- Tiempo SIN tuning: {time_no_tuning:.2f} s")
    print(f"- Tiempo CON tuning: {time_with_tuning:.2f} s")
    print(f"- Incremento por tuning: +{delta:.2f} s ({((time_with_tuning/time_no_tuning)-1)*100:.1f}%)")
    if time_with_tuning < 90:
        print("-> CONCLUSIÓN: Totalmente viable para demos en vivo y exposiciones en clase (< 1.5 min).")
    else:
        print("-> CONCLUSIÓN: Recomendado activar solo cuando se requiera el reporte final.")

if __name__ == "__main__":
    run_benchmark()
