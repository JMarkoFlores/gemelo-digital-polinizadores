from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

import tensorflow as tf

from app.config import get_settings

logger = logging.getLogger(__name__)


class ModelStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.model_dir = Path(settings.model_dir)
        self.model_path = self.model_dir / settings.model_filename
        self.metadata_path = self.model_dir / settings.model_metadata_filename
        self.model: tf.keras.Model | None = None
        self.metadata: dict[str, Any] = {}
        self.status_message = "Model not loaded"
        self._lock = threading.Lock()
        self._watcher_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Try to load the model from disk. Thread-safe."""
        with self._lock:
            self._do_load()

    def reload(self) -> None:
        """Force a reload (same as load, kept for clarity)."""
        self.load()

    def start_watcher(self, poll_interval: float = 5.0) -> None:
        """Start a background thread that reloads the model whenever the
        .h5 file appears or changes on disk (mtime-based).  This is the
        key fix: even if the backend starts before Streamlit exports the
        model, it will pick it up automatically without a container restart.
        """
        if self._watcher_thread and self._watcher_thread.is_alive():
            return  # already running

        self._stop_event.clear()

        def _watch() -> None:
            last_mtime: float | None = None
            while not self._stop_event.is_set():
                try:
                    if self.model_path.exists():
                        mtime = self.model_path.stat().st_mtime
                        if mtime != last_mtime:
                            logger.info(
                                "ModelStore watcher: detected new/updated model at %s – reloading…",
                                self.model_path,
                            )
                            with self._lock:
                                self._do_load()
                            last_mtime = mtime
                    else:
                        # File disappeared (e.g. volume removed) – mark as unready
                        if last_mtime is not None:
                            logger.warning("ModelStore watcher: model file removed, marking unready.")
                            with self._lock:
                                self.model = None
                                self.metadata = {}
                                self.status_message = (
                                    f"Model file not found at {self.model_path}. "
                                    "Train and export the surrogate from Streamlit first."
                                )
                            last_mtime = None
                except Exception as exc:  # noqa: BLE001
                    logger.error("ModelStore watcher error: %s", exc)

                self._stop_event.wait(poll_interval)

        self._watcher_thread = threading.Thread(target=_watch, daemon=True, name="model-watcher")
        self._watcher_thread.start()
        logger.info("ModelStore watcher started (poll_interval=%.1fs)", poll_interval)

    def stop_watcher(self) -> None:
        self._stop_event.set()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _do_load(self) -> None:
        """Actually load/reload from disk. Must be called with self._lock held."""
        if not self.model_path.exists():
            self.model = None
            self.metadata = {}
            self.status_message = (
                f"Model file not found at {self.model_path}. "
                "Train and export the surrogate from Streamlit first."
            )
            return

        try:
            self.model = tf.keras.models.load_model(self.model_path, compile=False)
            self.metadata = self._load_metadata()
            self.status_message = f"Loaded model from {self.model_path}"
            fuente = self.metadata.get("fuente_datos", "no registrada")
            region = self.metadata.get("region_name")
            region_str = f" | región: {region}" if region else ""
            n_samples = self.metadata.get("n_samples") or self.metadata.get("dataset_rows")
            samples_str = f" | registros: {n_samples}" if n_samples else ""
            logger.info(
                "Model loaded successfully: %s (versión: %s | fuente_datos: %s%s%s)",
                self.model_path,
                self.version,
                fuente,
                region_str,
                samples_str,
            )
        except Exception as exc:  # noqa: BLE001
            self.model = None
            self.metadata = {}
            self.status_message = f"Failed to load model: {exc}"
            logger.error("Failed to load model: %s", exc)

    def _load_metadata(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    @property
    def version(self) -> str | None:
        return self.metadata.get("version")

    @property
    def fuente_datos(self) -> str | None:
        return self.metadata.get("fuente_datos")

    @property
    def region_name(self) -> str | None:
        return self.metadata.get("region_name")

    @property
    def region_bounds(self) -> dict[str, float] | None:
        """Coordenadas y radio de validez agroecológica para modelos entrenados con datos públicos reales."""
        coords = self.metadata.get("coordinates")
        if isinstance(coords, dict) and "lat" in coords and "lon" in coords and "radius_km" in coords:
            try:
                return {
                    "lat": float(coords["lat"]),
                    "lon": float(coords["lon"]),
                    "radius_km": float(coords["radius_km"]),
                }
            except (TypeError, ValueError):
                pass

        details = self.metadata.get("data_source_details")
        if isinstance(details, dict):
            coords = details.get("coordinates")
            if isinstance(coords, dict) and "lat" in coords and "lon" in coords and "radius_km" in coords:
                try:
                    return {
                        "lat": float(coords["lat"]),
                        "lon": float(coords["lon"]),
                        "radius_km": float(coords["radius_km"]),
                    }
                except (TypeError, ValueError):
                    pass
        return None

    def check_point_in_region(self, lat: float, lon: float, tolerance: float = 0.2) -> dict[str, Any]:
        """Verifica si un punto o centroide (lat, lon) cae dentro del alcance geográfico válido del modelo activo."""
        bounds = self.region_bounds
        if not bounds:
            return {
                "has_restriction": False,
                "is_valid": True,
                "distance_km": None,
                "allowed_radius_km": None,
                "max_radius_with_tolerance_km": None,
                "region_name": self.region_name,
                "region_bounds": None,
                "fuente_datos": self.fuente_datos,
                "message": "Modelo sintético — no calibrado a una región geográfica real (sin restricción espacial).",
            }

        import math

        r_earth_km = 6371.0
        d_lat = math.radians(lat - bounds["lat"])
        d_lon = math.radians(lon - bounds["lon"])
        a = (
            math.sin(d_lat / 2.0) ** 2
            + math.cos(math.radians(bounds["lat"]))
            * math.cos(math.radians(lat))
            * math.sin(d_lon / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance_km = round(r_earth_km * c, 2)

        allowed_radius_km = float(bounds["radius_km"])
        max_radius_with_tolerance_km = round(allowed_radius_km * (1.0 + max(0.0, tolerance)), 2)
        is_valid = distance_km <= max_radius_with_tolerance_km

        region_name = self.region_name or "Región de entrenamiento"
        if is_valid:
            message = f"Punto dentro del área agroecológica válida de {region_name} ({distance_km} km del centroide)."
        else:
            message = (
                f"⚠️ Esta área está fuera de la región para la que el modelo activo fue entrenado y validado "
                f"({region_name}). Distancia observada: {distance_km} km (radio máximo permitido con tolerancia: {max_radius_with_tolerance_km} km). "
                f"Los resultados no serían científicamente válidos. Entrena y activa un modelo para tu región en Streamlit antes de continuar."
            )

        return {
            "has_restriction": True,
            "is_valid": is_valid,
            "distance_km": distance_km,
            "allowed_radius_km": allowed_radius_km,
            "max_radius_with_tolerance_km": max_radius_with_tolerance_km,
            "region_name": region_name,
            "region_bounds": bounds,
            "fuente_datos": self.fuente_datos,
            "message": message,
        }

    @property
    def data_source_summary(self) -> dict[str, Any]:
        return {
            "fuente_datos": self.metadata.get("fuente_datos"),
            "data_source_label": self.metadata.get("data_source_label"),
            "region_name": self.metadata.get("region_name"),
            "region_bounds": self.region_bounds,
            "coordinates": self.region_bounds,
            "n_samples": self.metadata.get("n_samples") or self.metadata.get("dataset_rows"),
            "gbif_occurrences": self.metadata.get("gbif_occurrences"),
            "distinct_species_count": self.metadata.get("distinct_species_count"),
            "clima_resumen": self.metadata.get("clima_resumen"),
        }


model_store = ModelStore()
