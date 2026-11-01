"""
tests/revision/test_learned_domain_bounds.py
Verificación del Mandato 6: Control de dominio basado en rangos aprendidos de entrenamiento.
Comprueba que:
  1. Se diferencian límites físicos generales (5–45 °C) de rangos observados de entrenamiento (ej. 14.31–18.69 °C).
  2. Un valor de 23.55 °C se rechaza en modo científico si el bundle indica 14.31–18.69 °C.
  3. Se conserva la advertencia explícita sobre la insuficiencia del cumplimiento univariado frente al soporte conjunto.
  4. La suma de coberturas se valida físicamente.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "backend"))

from backend.app.services.model_store import ModelStore, PHYSICAL_BOUNDS


def test_learned_bounds_rejection():
    """Caso obligatorio: bundle con 14.31-18.69 °C debe rechazar 23.55 °C."""
    store = ModelStore()
    store.metadata = {
        "schema_version": "2.0_revision_metodologica",
        "observed_training_ranges": {
            "crop_area_pct": [20.0, 75.0],
            "natural_area_pct": [10.0, 35.0],
            "floral_strips_pct": [2.0, 12.0],
            "pesticide_level": [5.0, 80.0],
            "soil_management_score": [20.0, 90.0],
            "temperature_c": [14.31, 18.69],
            "precipitation_mm": [800.0, 1600.0],
            "landscape_diversity": [0.20, 0.85],
        },
    }

    # 1. Caso con 23.55 °C (dentro de 5-45 físicos, pero fuera de 14.31-18.69 observados)
    features_out = {
        "crop_area_pct": 50.0,
        "natural_area_pct": 20.0,
        "floral_strips_pct": 5.0,
        "pesticide_level": 30.0,
        "soil_management_score": 60.0,
        "temperature_c": 23.55,
        "precipitation_mm": 1100.0,
        "landscape_diversity": 0.55,
    }

    res_out = store.check_domain(features_out, strict_mode=True)
    assert res_out["is_valid"] is False, "Debió rechazarse 23.55 °C frente a [14.31, 18.69] °C."
    assert any("temperature_c=23.55" in v for v in res_out["violations"])
    assert "joint_support_warning" in res_out
    assert "soporte conjunto" in res_out["joint_support_warning"]
    print("PASS: 23.55 °C rechazado exitosamente contra rango [14.31, 18.69] °C.")

    # 2. Caso con 16.50 °C (dentro del rango observado)
    features_in = dict(features_out)
    features_in["temperature_c"] = 16.50
    res_in = store.check_domain(features_in, strict_mode=True)
    assert res_in["is_valid"] is True, f"16.50 °C debió ser aceptado: {res_in['violations']}"
    print("PASS: 16.50 °C aceptado correctamente dentro de [14.31, 18.69] °C.")

    # 3. Caso de violación de balance de coberturas (suma > 100%)
    features_cov = dict(features_in)
    features_cov["crop_area_pct"] = 80.0
    features_cov["natural_area_pct"] = 20.0
    features_cov["floral_strips_pct"] = 10.0  # Suma 110%
    res_cov = store.check_domain(features_cov, strict_mode=True)
    assert res_cov["is_valid"] is False
    assert any("excede 100%" in v for v in res_cov["violations"])
    print("PASS: Violación de balance de coberturas (110%) rechazada correctamente.")


if __name__ == "__main__":
    test_learned_bounds_rejection()
