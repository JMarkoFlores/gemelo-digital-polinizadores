from __future__ import annotations

import json
import logging
from pathlib import Path
import pickle
import threading
import time
from typing import Any, Dict, List, Optional
import numpy as np

try:
    import tensorflow as tf
except ImportError:
    tf = None

try:
    from app.config import get_settings
except ImportError:
    class MinimalSettings:
        model_dir = "modelos_ia"
        model_filename = "modelo_optimizado.h5"
        model_metadata_filename = "modelo_optimizado_metadata.json"
    def get_settings():
        return MinimalSettings()

logger = logging.getLogger(__name__)

# Límites biofísicos y operativos generales (Hard limits)
PHYSICAL_BOUNDS = {
    "crop_area_pct": (0.0, 100.0),
    "natural_area_pct": (0.0, 100.0),
    "floral_strips_pct": (0.0, 100.0),
    "pesticide_level": (0.0, 100.0),
    "soil_management_score": (0.0, 100.0),
    "temperature_c": (5.0, 45.0),
    "precipitation_mm": (0.0, 5000.0),
    "landscape_diversity": (0.0, 1.0),
}

FEATURE_BOUNDS = PHYSICAL_BOUNDS


class ModelStore:
    def __init__(self, model_dir: Optional[Union[str, Path]] = None, allow_test_bundle: bool = False) -> None:
        settings = get_settings()
        self.model_dir = Path(model_dir) if model_dir is not None else Path(settings.model_dir)
        self.model_path = self.model_dir / settings.model_filename
        self.metadata_path = self.model_dir / settings.model_metadata_filename
        self.model: Any = None
        self._active_predictor: Any = None
        self.model_type: str = "unknown"
        self.bundle_id: str | None = None
        self.scaler_x: Any = None
        self.scaler_y: Any = None
        self.metadata: dict[str, Any] = {}
        self.status_message = "Model not loaded"
        self.last_error: str | None = None
        self.allow_test_bundle: bool = allow_test_bundle
        self._lock = threading.Lock()
        self._watcher_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, raise_on_error: bool = False) -> bool:
        """Try to load the model from disk. Thread-safe."""
        with self._lock:
            try:
                self._do_load()
                return True
            except Exception as exc:
                if raise_on_error:
                    raise
                return False

    def reload(self, raise_on_error: bool = False) -> bool:
        """Force a reload."""
        return self.load(raise_on_error=raise_on_error)

    def start_watcher(self, poll_interval: float = 5.0) -> None:
        if self._watcher_thread and self._watcher_thread.is_alive():
            return

        self._stop_event.clear()

        def _watch() -> None:
            last_mtime: float | None = None
            while not self._stop_event.is_set():
                try:
                    active_target = self.model_dir / "active_bundle.json"
                    if not active_target.exists():
                        active_target = self.model_dir / "bundle_metadata.json"
                    if not active_target.exists():
                        active_target = self.model_path

                    if active_target.exists():
                        mtime = active_target.stat().st_mtime
                        if mtime != last_mtime:
                            logger.info(
                                "ModelStore watcher: detected new/updated model at %s – reloading…",
                                active_target,
                            )
                            with self._lock:
                                self._do_load()
                            last_mtime = mtime
                    else:
                        if last_mtime is not None:
                            logger.warning("ModelStore watcher: model file removed.")
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
        """
        Carga atómica y tolerante a fallos desde disco reutilizando load_bundle de scientific_core (Bloque 2 y Bloque 3).
        Preserva el modelo previo si la carga o validación del nuevo bundle falla.
        """
        from scientific_core.model_bundle import load_bundle

        try:
            new_predictor = load_bundle(
                self.model_dir,
                allow_test_bundle=getattr(self, "allow_test_bundle", False),
            )
            # Activación atómica en memoria
            old_bundle_id = self.bundle_id
            self._active_predictor = new_predictor
            self.model = new_predictor.model
            self.model_type = new_predictor.model_type
            self.scaler_x = new_predictor.scaler_x
            self.scaler_y = new_predictor.scaler_y
            self.metadata = new_predictor.metadata
            self.bundle_id = new_predictor.bundle_id
            self.last_error = None
            self.status_message = f"Model loaded successfully: {new_predictor.bundle_id} ({new_predictor.model_type})"
            logger.info("ModelStore: %s", self.status_message)

            # Si cambió el bundle, invalidar la caché de optimización
            if old_bundle_id is not None and old_bundle_id != new_predictor.bundle_id:
                try:
                    from backend.app.services.optimization import simulation_cache
                    simulation_cache.clear()
                    logger.info("Simulation cache invalidated: %s -> %s", old_bundle_id, new_predictor.bundle_id)
                except Exception:
                    pass

        except Exception as exc:
            self.last_error = str(exc)
            logger.error("ModelStore error loading bundle from %s: %s", self.model_dir, exc)
            if self._active_predictor is not None:
                self.status_message = f"Error recargando bundle: {exc}. Conservando versión previa: {self.bundle_id}"
                logger.warning("ModelStore: Conservando modelo previo operativo (%s)", self.bundle_id)
            else:
                self.model = None
                self.status_message = f"Error cargando bundle: {exc}"
            raise

    def _load_metadata(self) -> dict[str, Any]:
        active_target = self.model_dir / "active_bundle.json"
        if active_target.exists():
            try:
                ainfo = json.loads(active_target.read_text(encoding="utf-8"))
                bdir = ainfo.get("bundle_dir")
                if bdir and (self.model_dir / bdir / "bundle_metadata.json").exists():
                    return json.loads((self.model_dir / bdir / "bundle_metadata.json").read_text(encoding="utf-8"))
            except Exception:
                pass
        meta_candidates = [
            self.model_dir / "bundle_metadata.json",
            self.metadata_path,
            self.model_dir / "modelo_optimizado_metadata.json",
        ]
        for p in meta_candidates:
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
        return {}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Ejecuta predicción universal aplicando escalado y desescalado de manera idéntica
        a todas las familias a través del predictor universal validado (Mandato 4).
        """
        predictor_snapshot = self._active_predictor
        if predictor_snapshot is None:
            if self.model is not None:
                from scientific_core.model_bundle import UniversalSurrogatePredictor
                predictor_snapshot = UniversalSurrogatePredictor(
                    model=self.model,
                    model_type=self.model_type,
                    scaler_x=self.scaler_x,
                    scaler_y=self.scaler_y,
                    metadata=self.metadata,
                )
            else:
                raise RuntimeError(self.status_message)

        return predictor_snapshot.predict(X)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    @property
    def version(self) -> str | None:
        return self.metadata.get("version") or self.bundle_id

    @property
    def fuente_datos(self) -> str | None:
        return self.metadata.get("fuente_datos")

    @property
    def region_name(self) -> str | None:
        return self.metadata.get("region_name")

    @property
    def region_bounds(self) -> dict[str, float] | None:
        coords = self.metadata.get("coordinates")
        if isinstance(coords, dict) and "lat" in coords and "lon" in coords:
            return coords
        return None

    def check_point_in_region(self, lat: float, lon: float) -> dict[str, Any]:
        """Validación de pertenencia geográfica del punto."""
        coords = self.region_bounds
        region_name = self.region_name or "Desconocida"
        bounds = self.region_bounds

        if coords:
            c_lat = float(coords["lat"])
            c_lon = float(coords["lon"])
            radius_km = float(coords.get("radius_km", 35.0))

            d_lat = (lat - c_lat) * 111.0
            d_lon = (lon - c_lon) * 111.0 * np.cos(np.radians(c_lat))
            dist_km = float(np.sqrt(d_lat**2 + d_lon**2))

            is_valid = dist_km <= radius_km
            message = (
                f"Punto dentro del radio de validez ({dist_km:.1f} km <= {radius_km} km de {region_name})"
                if is_valid
                else f"Punto fuera del radio de validez ({dist_km:.1f} km > {radius_km} km de {region_name})"
            )
        else:
            is_valid = True
            message = "Sin restricción geográfica explícita en metadatos."

        return {
            "is_valid": is_valid,
            "region_name": region_name,
            "region_bounds": bounds,
            "fuente_datos": self.fuente_datos,
            "message": message,
        }

    def check_domain(self, features: dict[str, float], strict_mode: bool = True) -> dict[str, Any]:
        """
        Verifica cumplimiento de:
          1. Límites biofísicos generales.
          2. Rangos observados en el entrenamiento del modelo (Mandato 6).
          3. Coherencia física de suma de coberturas (<= 100%).
        """
        violations = []

        # 1. Comprobación contra límites físicos generales
        for feat, (b_min, b_max) in PHYSICAL_BOUNDS.items():
            if feat in features:
                val = float(features[feat])
                if val < b_min or val > b_max:
                    violations.append(f"Variable {feat}={val} fuera de límites físicos [{b_min}, {b_max}]")

        # 2. Comprobación contra rangos aprendidos de entrenamiento
        observed_ranges = (
            self.metadata.get("observed_training_ranges")
            or self.metadata.get("observed_ranges")
        )

        if observed_ranges:
            for feat, rng in observed_ranges.items():
                if feat in features:
                    val = float(features[feat])
                    r_min, r_max = float(rng[0]), float(rng[1])
                    if val < r_min or val > r_max:
                        violations.append(
                            f"Variable {feat}={val} fuera del rango observado de entrenamiento [{r_min:.2f}, {r_max:.2f}]"
                        )
        elif strict_mode and self.metadata.get("schema_version") == "2.0_revision_metodologica":
            violations.append("Metadatos de rangos observados de entrenamiento ausentes en bundle científico.")

        # 3. Coberturas (física de exclusión)
        c_pct = float(features.get("crop_area_pct", 0.0))
        n_pct = float(features.get("natural_area_pct", 0.0))
        f_pct = float(features.get("floral_strips_pct", 0.0))
        tot = c_pct + n_pct + f_pct
        if tot > 100.0001:
            violations.append(f"Suma de coberturas excede 100% ({tot:.2f}%)")

        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "joint_support_warning": (
                "Aviso metodológico: El cumplimiento univariado de los rangos individuales de entrenamiento "
                "no demuestra la pertenencia al soporte conjunto multidimensional ni la ausencia de extrapolación fuera de distribución."
            ),
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
            "observed_training_ranges": self.metadata.get("observed_training_ranges"),
        }


model_store = ModelStore()
