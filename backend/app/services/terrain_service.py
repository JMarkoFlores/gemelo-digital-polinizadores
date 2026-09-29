from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Simple in-memory cache for elevation grids
# Key: sha256(bbox_json), Value: (timestamp, data)
_ELEVATION_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes


def _collect_points(coords: Any) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    if isinstance(coords, (list, tuple)):
        if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
            pts.append((float(coords[0]), float(coords[1])))
        else:
            for item in coords:
                pts.extend(_collect_points(item))
    return pts


def _extract_bbox(
    geometry: dict[str, Any] | None,
    bbox: list[float] | None,
) -> tuple[float, float, float, float] | None:
    """Extrae [min_lon, min_lat, max_lon, max_lat] a partir de GeoJSON o bbox."""
    if bbox and len(bbox) == 4:
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])

    if not geometry:
        return None

    coords = geometry.get("coordinates")
    if coords is None:
        return None

    pts = _collect_points(coords)
    if len(pts) < 3:
        return None

    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]

    return min(lons), min(lats), max(lons), max(lats)


def _generate_10x10_grid_points(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> list[dict[str, Any]]:
    """Genera 100 puntos (10x10) alineados exactamente con la grilla del diorama.
    x: 0 a 9 (Oeste a Este, columnas de longitud)
    z: 0 a 9 (Norte a Sur, filas de latitud)
    """
    width = max_lon - min_lon
    height = max_lat - min_lat

    points = []
    for z in range(10):
        # z=0 es el borde Norte (max_lat), z=9 es el borde Sur (min_lat)
        lat = round(max_lat - (z + 0.5) * (height / 10.0), 5)
        for x in range(10):
            # x=0 es el borde Oeste (min_lon), x=9 es el borde Este (max_lon)
            lon = round(min_lon + (x + 0.5) * (width / 10.0), 5)
            points.append({"x": x, "z": z, "lat": lat, "lon": lon})
    return points


def _query_open_elevation(points: list[dict[str, Any]]) -> list[float] | None:
    """Preferencia 1: Open-Elevation API (lote de 100 puntos)."""
    url = "https://api.open-elevation.com/api/v1/lookup"
    locations = [{"latitude": p["lat"], "longitude": p["lon"]} for p in points]
    try:
        resp = requests.post(url, json={"locations": locations}, timeout=4.0, verify=False)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if len(results) == len(points):
                return [float(r.get("elevation", 0.0)) for r in results]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Elevation no disponible: %s. Pasando a alternativa.", exc)
    return None


def _query_open_meteo_elevation(points: list[dict[str, Any]]) -> list[float] | None:
    """Preferencia 2 / Alternativa: Open-Meteo Elevation API (gratuita, sin key)."""
    lat_str = ",".join(str(p["lat"]) for p in points)
    lon_str = ",".join(str(p["lon"]) for p in points)
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lat_str}&longitude={lon_str}"
    try:
        resp = requests.get(url, timeout=5.0)
        if resp.status_code == 200:
            elevations = resp.json().get("elevation", [])
            if len(elevations) == len(points):
                return [float(e) for e in elevations]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo Elevation no disponible: %s.", exc)
    return None


def get_elevation_grid(
    geometry: dict[str, Any] | None = None,
    bbox: list[float] | None = None,
) -> dict[str, Any]:
    """Obtiene la grilla 10x10 de elevación real para el polígono."""
    bbox_tuple = _extract_bbox(geometry, bbox)
    if not bbox_tuple:
        return _build_fallback_grid("No se proporcionó una geometría o bounding box válido.")

    min_lon, min_lat, max_lon, max_lat = bbox_tuple

    # Comprobar caché en memoria
    cache_key = hashlib.sha256(
        f"{min_lon:.5f}_{min_lat:.5f}_{max_lon:.5f}_{max_lat:.5f}".encode()
    ).hexdigest()

    cached_entry = _ELEVATION_CACHE.get(cache_key)
    if cached_entry:
        cached_time, cached_data = cached_entry
        if time.time() - cached_time < CACHE_TTL_SECONDS:
            return cached_data

    # Generar los 100 puntos en grilla 10x10
    points = _generate_10x10_grid_points(min_lon, min_lat, max_lon, max_lat)

    # 1. Intentar Open-Elevation
    elevations = _query_open_elevation(points)
    source = "Open-Elevation API"

    # 2. Fallback a Open-Meteo
    if elevations is None:
        elevations = _query_open_meteo_elevation(points)
        source = "Open-Meteo Elevation API (Copernicus DEM 90m)"

    # 3. Fallback a relieve plano si ambas fallan
    if elevations is None:
        result = _build_fallback_grid("Relieve no disponible para esta zona, mostrando vista plana.")
        _ELEVATION_CACHE[cache_key] = (time.time(), result)
        return result

    # Procesar métricas topográficas
    min_elev = round(float(min(elevations)), 2)
    max_elev = round(float(max(elevations)), 2)
    elev_range = round(max_elev - min_elev, 2)
    mean_elev = round(float(sum(elevations) / len(elevations)), 2)

    # Construir grilla y matrices
    grid_cells: list[dict[str, Any]] = []
    matrix: list[list[float]] = [[0.0] * 10 for _ in range(10)]
    normalized_matrix: list[list[float]] = [[0.0] * 10 for _ in range(10)]

    for idx, p in enumerate(points):
        x = p["x"]
        z = p["z"]
        elev = round(float(elevations[idx]), 2)
        rel_elev = round(elev - min_elev, 2)
        norm = round(rel_elev / elev_range, 4) if elev_range > 0.05 else 0.0

        matrix[z][x] = elev
        normalized_matrix[z][x] = norm

        grid_cells.append(
            {
                "x": x,
                "z": z,
                "lat": p["lat"],
                "lon": p["lon"],
                "elevation_m": elev,
                "rel_elevation_m": rel_elev,
                "normalized": norm,
            }
        )

    result = {
        "available": True,
        "source": source,
        "min_elevation_m": min_elev,
        "max_elevation_m": max_elev,
        "elevation_range_m": elev_range,
        "mean_elevation_m": mean_elev,
        "grid": grid_cells,
        "matrix": matrix,
        "normalized_matrix": normalized_matrix,
        "message": (
            f"Relieve real obtenido ({source}). "
            f"Desnivel: {elev_range} m (Mín: {min_elev} m, Máx: {max_elev} m)."
        ),
    }

    _ELEVATION_CACHE[cache_key] = (time.time(), result)
    return result


def _build_fallback_grid(message: str) -> dict[str, Any]:
    """Genera una grilla plana 10x10 como fallback seguro."""
    grid_cells = []
    for z in range(10):
        for x in range(10):
            grid_cells.append(
                {
                    "x": x,
                    "z": z,
                    "lat": 0.0,
                    "lon": 0.0,
                    "elevation_m": 0.0,
                    "rel_elevation_m": 0.0,
                    "normalized": 0.0,
                }
            )

    return {
        "available": False,
        "source": "Fallback estándar (Plano)",
        "min_elevation_m": 0.0,
        "max_elevation_m": 0.0,
        "elevation_range_m": 0.0,
        "mean_elevation_m": 0.0,
        "grid": grid_cells,
        "matrix": [[0.0] * 10 for _ in range(10)],
        "normalized_matrix": [[0.0] * 10 for _ in range(10)],
        "message": message,
    }
