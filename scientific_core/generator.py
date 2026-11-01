"""
scientific_core/generator.py
Generador determinista y coherente de escenarios agroecológicos para el gemelo digital.
Garantiza:
  1. Coberturas biofísicas excluyentes (suma de cultivo + natural + franjas florales <= 100%).
  2. Diversidad del paisaje unificada con la misma función que optimización e inferencia.
  3. Política explícita de enriquecimiento ABM (corrected_full exige enriquecer todas las filas;
     sin fallbacks silenciosos en ejecución científica).
  4. Identificación veraz como dataset sintético (sin falsa atribución a NASA POWER o GBIF).
  5. Versionado explícito v2_corrected preservando la referencia a v1_historical.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd

from scientific_core.contracts import (
    FEATURE_COLUMNS,
    TARGET_COLUMNS,
    calculate_landscape_diversity,
)

logger = logging.getLogger(__name__)


def generate_coherent_dataset(
    n_samples: int = 320,
    random_state: int = 42,
    abm_policy: str = "corrected_none",
    max_abm_simulations: Optional[int] = None,
    test_mode: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Genera un dataset sintético calibrado sin violaciones físicas de coberturas.

    Políticas de ABM:
      - 'corrected_none': Sin enriquecimiento ABM (dataset base puramente analítico).
      - 'corrected_full': Todas las filas se enriquecen con simulación ABM Mesa (sin saltos discretos).
      - 'historical_partial': Enriquecimiento histórico parcial (primeras 120 filas con ABM).
    """
    rng = np.random.default_rng(random_state)

    # 1. Muestreo de coberturas excluyentes con suma estricta <= 100%
    natural_area = rng.uniform(5.0, 40.0, size=n_samples)
    floral_strips = rng.uniform(1.0, 15.0, size=n_samples)
    max_crop_allowed = 100.0 - natural_area - floral_strips
    crop_area = max_crop_allowed * rng.uniform(0.60, 0.98, size=n_samples)

    # 2. Manejo agrícola y variables climáticas calibradas sintéticas
    pesticide_level = rng.uniform(0.0, 95.0, size=n_samples)
    soil_management = rng.uniform(10.0, 95.0, size=n_samples)
    temperature_c = rng.normal(loc=23.5, scale=3.2, size=n_samples)
    precipitation_mm = rng.normal(loc=1150.0, scale=280.0, size=n_samples)

    # 3. Variable derivada consistente
    diversity_vals = np.array([
        calculate_landscape_diversity(nat, flor, sm)
        for nat, flor, sm in zip(natural_area, floral_strips, soil_management)
    ])

    # 4. Señales base para los objetivos
    yield_base = (
        (crop_area * 0.95)
        + (soil_management * 0.28)
        - (pesticide_level * 0.12)
        + (temperature_c * 0.8)
        + rng.normal(0, 2.5, size=n_samples)
    )
    yield_index = np.clip(yield_base, 15.0, 195.0)

    abundance_base = (
        (natural_area * 1.6)
        + (floral_strips * 2.8)
        - (pesticide_level * 0.75)
        + (soil_management * 0.35)
        + (diversity_vals * 22.0)
        + rng.normal(0, 3.5, size=n_samples)
    )
    abundance_index = np.clip(abundance_base, 5.0, 195.0)

    div_index_base = (
        (natural_area * 0.85)
        + (floral_strips * 1.6)
        - (pesticide_level * 0.35)
        + (diversity_vals * 38.0)
        + rng.normal(0, 2.0, size=n_samples)
    )
    pollinator_diversity_index = np.clip(div_index_base, 2.0, 98.0)

    # Construcción del DataFrame canónico con sample_id
    df = pd.DataFrame({
        "sample_id": np.arange(1, n_samples + 1, dtype=int),
        "crop_area_pct": np.round(crop_area, 2),
        "natural_area_pct": np.round(natural_area, 2),
        "floral_strips_pct": np.round(floral_strips, 2),
        "pesticide_level": np.round(pesticide_level, 2),
        "soil_management_score": np.round(soil_management, 2),
        "temperature_c": np.round(temperature_c, 2),
        "precipitation_mm": np.round(precipitation_mm, 2),
        "landscape_diversity": np.round(diversity_vals, 4),
        "crop_yield_index": np.round(yield_index, 2),
        "pollinator_abundance_index": np.round(abundance_index, 2),
        "pollinator_diversity_index": np.round(pollinator_diversity_index, 2),
    })

    # 5. Enriquecimiento ABM según política explícita sin fallbacks silenciosos
    abm_metadata: Dict[str, Any] = {
        "abm_policy": abm_policy,
        "max_abm_simulations": max_abm_simulations,
        "simulations_performed": 0,
        "status": "not_requested" if abm_policy == "corrected_none" else "pending",
    }

    if abm_policy != "corrected_none":
        if abm_policy == "corrected_full" and max_abm_simulations is not None and max_abm_simulations < n_samples:
            if not test_mode:
                raise ValueError(
                    f"Incoherencia en solicitud: policy='corrected_full' exige {n_samples} simulaciones, "
                    f"pero max_abm_simulations={max_abm_simulations}."
                )

        try:
            from streamlit_app.pollinator_abm import ABMScenario, PollinatorLandscapeModel

            n_sims = n_samples
            if max_abm_simulations is not None:
                n_sims = min(n_samples, max_abm_simulations)
            elif abm_policy == "historical_partial":
                n_sims = min(n_samples, 120)

            abundance_vals = []
            diversity_abm_vals = []

            for idx in range(n_sims):
                row = df.iloc[idx]
                scenario = ABMScenario(
                    crop_area_pct=float(row["crop_area_pct"]),
                    natural_area_pct=float(row["natural_area_pct"]),
                    floral_strips_pct=float(row["floral_strips_pct"]),
                    pesticide_level=float(row["pesticide_level"]),
                    soil_management_score=float(row["soil_management_score"]),
                    temperature_c=float(row["temperature_c"]),
                    landscape_diversity=float(row["landscape_diversity"]),
                    initial_pollinators=max(30, int(28 + row["natural_area_pct"] * 0.8)),
                    seed=int(random_state + idx),
                )
                model = PollinatorLandscapeModel(scenario)
                res = model.run()
                abundance_vals.append(float(np.clip(res["mean_population"] * 1.25, 8, 120)))
                diversity_abm_vals.append(float(res["diversity_index"]))

            abm_metadata["simulations_performed"] = n_sims
            abm_metadata["status"] = "completed"

            if n_sims < n_samples:
                tail = df.iloc[n_sims:]
                abundance_vals.extend(tail["pollinator_abundance_index"].tolist())
                diversity_abm_vals.extend(tail["pollinator_diversity_index"].tolist())

            df["abm_pollinator_abundance"] = np.round(abundance_vals, 2)
            df["abm_pollinator_diversity"] = np.round(diversity_abm_vals, 2)
            df["pollinator_abundance_index"] = np.round(
                df["pollinator_abundance_index"] * 0.35 + df["abm_pollinator_abundance"] * 0.65, 2
            )
            df["pollinator_diversity_index"] = np.round(
                df["pollinator_diversity_index"] * 0.30 + df["abm_pollinator_diversity"] * 0.70, 2
            )
            df["crop_yield_index"] = np.round(
                df["crop_yield_index"] + df["pollinator_abundance_index"] * 0.03, 2
            )

        except Exception as e:
            abm_metadata["status"] = "failed"
            abm_metadata["error"] = str(e)
            if not test_mode:
                raise RuntimeError(
                    f"Fallo en enriquecimiento ABM solicitado ({abm_policy}): {e}. "
                    "En ejecución científica no se permite continuar silenciosamente con cero simulaciones. "
                    "Ejecute en el entorno Docker oficial o utilice test_mode=True si realiza pruebas desacopladas."
                ) from e
            logger.warning("Fallo en ABM en modo test: %s", e)

    metadata = {
        "generator_version": "v2_corrected",
        "dataset_version": "v2_corrected",
        "historical_version_preserved": "v1_historical",
        "n_samples": n_samples,
        "random_state": random_state,
        "abm_policy": abm_policy,
        "abm": abm_metadata,
        "source_type": "sintetico_generado",
        "real_data_attributions": False,
        "provenance_notes": "Dataset sintético calibrado con física de coberturas excluyentes. No atribuido a NASA POWER ni GBIF sin importación verificada.",
    }

    return df, metadata
