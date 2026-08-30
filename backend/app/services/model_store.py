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
            logger.info("Model loaded successfully: %s", self.model_path)
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


model_store = ModelStore()
