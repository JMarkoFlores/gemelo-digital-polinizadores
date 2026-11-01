import pandas as pd
import numpy as np
from streamlit_app.pollinator_abm import ABMScenario, PollinatorLandscapeModel

df = pd.read_csv('/app/artifacts/revision_metodologica/campana_cientifica/dataset_320_corrected_full.csv')

print("=== DIAGNÓSTICO POSTERIOR SEPARADO: 5 ESCENARIOS ABM BRUTOS VS TRANSFORMADOS ===")
for idx in range(5):
    row = df.iloc[idx]
    seed_i = int(42 + idx)
    init_poll = max(30, int(28 + row['natural_area_pct'] * 0.8))
    scenario = ABMScenario(
        crop_area_pct=float(row['crop_area_pct']),
        natural_area_pct=float(row['natural_area_pct']),
        floral_strips_pct=float(row['floral_strips_pct']),
        pesticide_level=float(row['pesticide_level']),
        soil_management_score=float(row['soil_management_score']),
        temperature_c=float(row['temperature_c']),
        landscape_diversity=float(row['landscape_diversity']),
        initial_pollinators=init_poll,
        seed=seed_i,
    )
    model = PollinatorLandscapeModel(scenario)
    res = model.run()
    raw_mean_pop = float(res['mean_population'])
    raw_final_pop = float(res['final_population'])
    scaled = raw_mean_pop * 1.25
    clipped = float(np.clip(scaled, 8, 120))
    sid = int(row['sample_id'])
    csv_val = float(row['abm_pollinator_abundance'])
    pop_hist = res.get('population_history', [])
    print(f"Escenario {idx+1} (sample_id={sid}):")
    print(f"  Inputs: nat={row['natural_area_pct']:.1f}%, flor={row['floral_strips_pct']:.1f}%, pest={row['pesticide_level']:.1f}, temp={row['temperature_c']:.1f} C")
    print(f"  Seed={seed_i}, Población Inicial={init_poll}")
    print(f"  Historial primeros 5 pasos: {pop_hist[:5]}")
    print(f"  Historial ultimos 5 pasos:  {pop_hist[-5:]}")
    print(f"  Mean Population (Bruta) = {raw_mean_pop:.2f}")
    print(f"  Final Population (Bruta) = {raw_final_pop:.0f}")
    print(f"  Bruta * 1.25            = {scaled:.2f}")
    print(f"  Tras clip(., 8, 120)    = {clipped:.2f}")
    print(f"  Valor en CSV Campaña    = {csv_val:.2f}")
    print("-" * 65)
