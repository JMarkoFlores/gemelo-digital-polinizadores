from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "crop_area_pct",
    "natural_area_pct",
    "floral_strips_pct",
    "pesticide_level",
    "soil_management_score",
    "temperature_c",
    "precipitation_mm",
    "landscape_diversity",
]

TARGET_COLUMNS = [
    "crop_yield_index",
    "pollinator_abundance_index",
    "pollinator_diversity_index",
]


@dataclass
class RealDataConfig:
    latitude: float
    longitude: float
    start_year: int
    end_year: int
    radius_km: float = 10.0
    climate_dataset: str = "reanalysis-era5-single-levels-monthly-means"


def _clip(values: np.ndarray, lower: float, upper: float) -> np.ndarray:
    return np.clip(values, lower, upper)


def generate_synthetic_dataset(
    n_samples: int = 300,
    random_state: int = 42,
    enrich_with_abm: bool = False,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)

    crop_area = rng.uniform(35, 82, size=n_samples)
    natural_area = rng.uniform(8, 42, size=n_samples)
    floral_strips = rng.uniform(2, 18, size=n_samples)
    pesticide = rng.uniform(5, 95, size=n_samples)
    soil_management = rng.uniform(35, 95, size=n_samples)
    temperature = rng.normal(23.5, 2.8, size=n_samples)
    precipitation = rng.normal(1050, 180, size=n_samples)
    landscape_diversity = rng.uniform(0.2, 0.95, size=n_samples)

    heat_stress = _clip(np.abs(temperature - 24.0) * 4.2, 0, 30)
    water_stress = _clip(np.abs(precipitation - 1025) / 16.0, 0, 28)

    pollinator_abundance = (
        36
        + natural_area * 0.92
        + floral_strips * 1.35
        + landscape_diversity * 24
        + soil_management * 0.18
        - pesticide * 0.42
        - heat_stress * 0.55
        + rng.normal(0, 4.0, size=n_samples)
    )
    pollinator_abundance = _clip(pollinator_abundance, 8, 120)

    pollinator_diversity = (
        14
        + natural_area * 0.48
        + floral_strips * 0.85
        + landscape_diversity * 18
        - pesticide * 0.15
        - heat_stress * 0.18
        + rng.normal(0, 2.0, size=n_samples)
    )
    pollinator_diversity = _clip(pollinator_diversity, 5, 55)

    crop_yield = (
        54
        + crop_area * 0.42
        + soil_management * 0.28
        + pollinator_abundance * 0.16
        + precipitation * 0.004
        - pesticide * 0.08
        - heat_stress * 0.7
        - water_stress * 0.52
        + rng.normal(0, 3.5, size=n_samples)
    )
    crop_yield = _clip(crop_yield, 20, 130)

    data = pd.DataFrame(
        {
            "crop_area_pct": crop_area.round(2),
            "natural_area_pct": natural_area.round(2),
            "floral_strips_pct": floral_strips.round(2),
            "pesticide_level": pesticide.round(2),
            "soil_management_score": soil_management.round(2),
            "temperature_c": temperature.round(2),
            "precipitation_mm": precipitation.round(2),
            "landscape_diversity": landscape_diversity.round(3),
            "crop_yield_index": crop_yield.round(2),
            "pollinator_abundance_index": pollinator_abundance.round(2),
            "pollinator_diversity_index": pollinator_diversity.round(2),
        }
    )

    if enrich_with_abm:
        from pollinator_abm import enrich_dataset_with_abm

        data = enrich_dataset_with_abm(data, random_state=random_state)

    return data


def summarize_dataset(dataframe: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(dataframe)),
        "input_features": [column for column in FEATURE_COLUMNS if column in dataframe.columns],
        "target_features": [column for column in TARGET_COLUMNS if column in dataframe.columns],
        "missing_values": int(dataframe.isna().sum().sum()),
    }


def fetch_gbif_pollinator_records(config: RealDataConfig, limit: int = 200) -> pd.DataFrame:
    try:
        from pygbif import occurrences
    except ImportError as exc:
        raise RuntimeError("pygbif no esta instalado. Instalala si quieres activar el conector real.") from exc

    response = occurrences.search(
        decimalLatitude=config.latitude,
        decimalLongitude=config.longitude,
        radius=int(config.radius_km * 1000),
        year=f"{config.start_year},{config.end_year}",
        limit=limit,
    )
    return pd.DataFrame(response.get("results", []))


def fetch_era5_climate_timeseries(config: RealDataConfig, output_path: str) -> str:
    try:
        import cdsapi
    except ImportError as exc:
        raise RuntimeError("cdsapi no esta instalado. Instalala y configura tus credenciales de Copernicus.") from exc

    client = cdsapi.Client()
    client.retrieve(
        config.climate_dataset,
        {
            "product_type": "monthly_averaged_reanalysis",
            "variable": ["2m_temperature", "total_precipitation"],
            "year": [str(year) for year in range(config.start_year, config.end_year + 1)],
            "month": [f"{month:02d}" for month in range(1, 13)],
            "time": "00:00",
            "format": "netcdf",
            "area": [config.latitude + 0.2, config.longitude - 0.2, config.latitude - 0.2, config.longitude + 0.2],
        },
        output_path,
    )
    return output_path


def fetch_land_use_snapshot(config: RealDataConfig, output_path: str) -> str:
    try:
        import ee
        import geemap
    except ImportError as exc:
        raise RuntimeError(
            "earthengine-api/geemap no estan instalados. Instalala y autentica Earth Engine para usar este conector."
        ) from exc

    ee.Initialize()
    point = ee.Geometry.Point([config.longitude, config.latitude])
    region = point.buffer(config.radius_km * 1000).bounds()
    image = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(f"{config.start_year}-01-01", f"{config.end_year}-12-31")
        .median()
    )
    geemap.ee_export_image(image.clip(region), filename=output_path, scale=10, region=region)
    return output_path
