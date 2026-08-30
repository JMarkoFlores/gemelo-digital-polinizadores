from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tensorflow as tf

from app.config import get_settings


class ModelStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.model_dir = Path(settings.model_dir)
        self.model_path = self.model_dir / settings.model_filename
        self.metadata_path = self.model_dir / settings.model_metadata_filename
        self.model: tf.keras.Model | None = None
        self.metadata: dict[str, Any] = {}
        self.status_message = "Model not loaded"

    def load(self) -> None:
        if not self.model_path.exists():
            self.model = None
            self.metadata = {}
            self.status_message = (
                f"Model file not found at {self.model_path}. Train and export the surrogate from Streamlit first."
            )
            return

        self.model = tf.keras.models.load_model(self.model_path, compile=False)
        self.metadata = self._load_metadata()
        self.status_message = f"Loaded model from {self.model_path}"

    def reload(self) -> None:
        self.load()

    def _load_metadata(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    @property
    def version(self) -> str | None:
        return self.metadata.get("version")


model_store = ModelStore()
