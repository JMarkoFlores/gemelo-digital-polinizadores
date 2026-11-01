"""
tests/revision/test_audit05_criteria_precision.py
Pruebas de regresión para el Hallazgo 3 de la Auditoría 05:
Evaluación del criterio operativo conjunto antes del redondeo y con precisión numérica completa.

Verifica:
1. Caso reproducido de frontera:
   Línea base: rendimiento=100.0, polinizadores=100.0
   Solución: rendimiento=99.9996, polinizadores=119.9998
   Deltas reales: -0.0004 y 19.9998%
   Deltas redondeados a 3 decimales para presentación: 0.000 y 20.000%
   Resultado exigido: meets_joint_criteria = False (no cumple).
2. Cumplimiento exacto sin degradación:
   Línea base: rendimiento=100.0, polinizadores=100.0
   Solución: rendimiento=100.0000, polinizadores=120.0000
   Deltas reales: 0.0000 y 20.0000%
   Resultado exigido: meets_joint_criteria = True (cumple).
3. Caso netamente superior:
   Línea base: rendimiento=100.0, polinizadores=100.0
   Solución: rendimiento=110.0, polinizadores=140.0
   Resultado exigido: meets_joint_criteria = True (cumple).
4. Caso inferior:
   Línea base: rendimiento=100.0, polinizadores=100.0
   Solución: rendimiento=85.0, polinizadores=125.0
   Resultado exigido: meets_joint_criteria = False (no cumple).
5. Ausencia de soluciones admisibles (infeasible):
   Frente de Pareto vacío.
   Resultado exigido: meets_joint_criteria = None, deltas = None, estado "No evaluable".
"""
from __future__ import annotations

import sys
import types
from unittest.mock import patch
import numpy as np
import pytest

# Shim transparente de pydantic en entornos de prueba científica si no está preinstalado
if "pydantic" not in sys.modules:
    try:
        import pydantic  # noqa: F401
    except ImportError:
        pyd = types.ModuleType("pydantic")

        class BaseModel:
            model_config = {}

            def __init__(self, **kwargs):
                for attr_name, attr_val in self.__class__.__dict__.items():
                    if not attr_name.startswith("_") and not callable(attr_val):
                        setattr(self, attr_name, attr_val)
                for k, v in kwargs.items():
                    setattr(self, k, v)

            @classmethod
            def model_validate(cls, data):
                return cls(**data)

            def model_dump(self):
                return self.__dict__

            @classmethod
            def model_rebuild(cls):
                pass

        def Field(*args, default=None, default_factory=None, **kwargs):
            return default_factory() if default_factory else default

        class EmailStr(str):
            pass

        pyd.BaseModel = BaseModel
        pyd.Field = Field
        pyd.EmailStr = EmailStr
        sys.modules["pydantic"] = pyd

from backend.app.services.optimization import run_simulation, simulation_cache


@pytest.fixture(autouse=True)
def clear_cache():
    simulation_cache.clear()
    yield
    simulation_cache.clear()


def _dummy_predict_targets(rows):
    return np.tile(np.array([100.0, 100.0, 50.0], dtype=np.float32), (len(rows), 1))


def test_reproduced_boundary_false_positive_prevented():
    """
    Reproducción exacta del hallazgo 3:
    Rendimiento con leve degradación (-0.0004) y polinizadores apenas por debajo (+19.9998%).
    Al redondear a 3 decimales daría 0.000 y 20.000%, pero el criterio operativo evaluado
    con precisión flotante estricta debe dar False.
    """
    candidate = {
        "crop_area_pct": 50.0,
        "natural_area_pct": 25.0,
        "floral_strips_pct": 5.0,
        "pesticide_level": 20.0,
        "soil_management_score": 75.0,
        "temperature_c": 22.0,
        "precipitation_mm": 1000.0,
        "landscape_diversity": 0.65,
        "crop_yield_index": 99.9996,
        "pollinator_abundance_index": 119.9998,
        "pollinator_diversity_index": 50.0,
    }

    payload = {
        "pesticide_level": 20.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "bbox": [3.4, -76.6, 3.6, -76.4],
        "test_mode": True,
    }

    with patch("backend.app.services.optimization.model_store.model", object()), \
         patch("backend.app.services.optimization.predict_targets", side_effect=_dummy_predict_targets), \
         patch("backend.app.services.optimization.filter_verified_pareto_front", return_value=[candidate]):

        res = run_simulation(payload)

        # Comprobación crucial: La evaluación se realizó ANTES del redondeo
        assert res["meets_joint_criteria"] is False, (
            "meets_joint_criteria debió ser False porque delta_yield < 0 (-0.0004) y delta_poll < 20% (19.9998%)"
        )
        assert res["hypothesis_status"] == "Criterio operativo de mejora conjunta no alcanzado"

        # Presentación visual redondeada a 3 decimales
        assert res["delta_yield"] == 0.0
        assert res["delta_pollinators"] == 20.0


def test_exact_boundary_non_degraded_and_20pct_pollinators():
    """
    Verifica que con delta_yield exactamente 0.0 y delta_pollinators exactamente 20.0%,
    el criterio sí se cumple.
    """
    candidate = {
        "crop_area_pct": 50.0,
        "natural_area_pct": 25.0,
        "floral_strips_pct": 5.0,
        "pesticide_level": 20.0,
        "soil_management_score": 75.0,
        "temperature_c": 22.0,
        "precipitation_mm": 1000.0,
        "landscape_diversity": 0.65,
        "crop_yield_index": 100.0,
        "pollinator_abundance_index": 120.0,
        "pollinator_diversity_index": 50.0,
    }

    payload = {
        "pesticide_level": 20.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "bbox": [3.4, -76.6, 3.6, -76.4],
        "test_mode": True,
    }

    with patch("backend.app.services.optimization.model_store.model", object()), \
         patch("backend.app.services.optimization.predict_targets", side_effect=_dummy_predict_targets), \
         patch("backend.app.services.optimization.filter_verified_pareto_front", return_value=[candidate]):

        res = run_simulation(payload)

        assert res["meets_joint_criteria"] is True
        assert res["delta_yield"] == 0.0
        assert res["delta_pollinators"] == 20.0
        assert "cumplido" in res["hypothesis_status"]


def test_clearly_superior_solution():
    """Verifica cumplimiento inequívoco cuando el rendimiento mejora y polinizadores > 20%."""
    candidate = {
        "crop_area_pct": 50.0,
        "natural_area_pct": 25.0,
        "floral_strips_pct": 5.0,
        "pesticide_level": 20.0,
        "soil_management_score": 75.0,
        "temperature_c": 22.0,
        "precipitation_mm": 1000.0,
        "landscape_diversity": 0.65,
        "crop_yield_index": 110.0,
        "pollinator_abundance_index": 140.0,
        "pollinator_diversity_index": 60.0,
    }

    payload = {
        "pesticide_level": 20.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "bbox": [3.4, -76.6, 3.6, -76.4],
        "test_mode": True,
    }

    with patch("backend.app.services.optimization.model_store.model", object()), \
         patch("backend.app.services.optimization.predict_targets", side_effect=_dummy_predict_targets), \
         patch("backend.app.services.optimization.filter_verified_pareto_front", return_value=[candidate]):

        res = run_simulation(payload)

        assert res["meets_joint_criteria"] is True
        assert res["delta_yield"] == 10.0
        assert res["delta_pollinators"] == 40.0
        assert "cumplido" in res["hypothesis_status"]


def test_clearly_inferior_solution():
    """Verifica no cumplimiento cuando el rendimiento cae marcadamente."""
    candidate = {
        "crop_area_pct": 50.0,
        "natural_area_pct": 25.0,
        "floral_strips_pct": 5.0,
        "pesticide_level": 20.0,
        "soil_management_score": 75.0,
        "temperature_c": 22.0,
        "precipitation_mm": 1000.0,
        "landscape_diversity": 0.65,
        "crop_yield_index": 85.0,
        "pollinator_abundance_index": 125.0,
        "pollinator_diversity_index": 50.0,
    }

    payload = {
        "pesticide_level": 20.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "bbox": [3.4, -76.6, 3.6, -76.4],
        "test_mode": True,
    }

    with patch("backend.app.services.optimization.model_store.model", object()), \
         patch("backend.app.services.optimization.predict_targets", side_effect=_dummy_predict_targets), \
         patch("backend.app.services.optimization.filter_verified_pareto_front", return_value=[candidate]):

        res = run_simulation(payload)

        assert res["meets_joint_criteria"] is False
        assert res["delta_yield"] == -15.0
        assert res["delta_pollinators"] == 25.0
        assert "no alcanzado" in res["hypothesis_status"]


def test_absence_of_solution_infeasible():
    """Verifica que sin soluciones admisibles meets_joint_criteria sea None (no evaluable)."""
    payload = {
        "pesticide_level": 20.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "bbox": [3.4, -76.6, 3.6, -76.4],
        "test_mode": True,
    }

    with patch("backend.app.services.optimization.model_store.model", object()), \
         patch("backend.app.services.optimization.predict_targets", side_effect=_dummy_predict_targets), \
         patch("backend.app.services.optimization.filter_verified_pareto_front", return_value=[]):

        res = run_simulation(payload)

        assert res["status"] == "infeasible"
        assert res["meets_joint_criteria"] is None
        assert res["delta_yield"] is None
        assert res["delta_pollinators"] is None
        assert "No evaluable" in res["hypothesis_status"]
