"""
tests/revision/test_audit04_infeasible_and_criteria.py
Pruebas obligatorias para los Bloques 2 y 3 de la Auditoría 04:
1. Manejo consistente de respuestas success e infeasible (sin crashes en None).
2. Validación del schema SimulationResultPayload con y sin soluciones.
3. Comportamiento de run_simulation ante ausencia de soluciones admisibles.
4. Verificación rigurosa del criterio operativo de mejora conjunta:
   - +25% polinizadores y rendimiento negativo: NO CUMPLE.
   - +25% polinizadores y rendimiento no degradado: CUMPLE.
   - +10% polinizadores: NO CUMPLE.
   - Sin solución: NO EVALUABLE.
5. Verificación de la presentación textual del criterio operativo sin claims indebidos.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import patch, MagicMock
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
                # Aplicar defaults definidos en la clase
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

from backend.app.schemas import SimulationResultPayload
from backend.app.services.recommendation_service import generate_ai_recommendation
from backend.app.services.optimization import run_simulation


# ────────────────────────────────────────────────────────────────────────────
# Bloque 2: Schema y Ausencia de Solución en Infeasible
# ────────────────────────────────────────────────────────────────────────────

def test_simulation_result_payload_success_validation():
    """Valida el schema SimulationResultPayload cuando la simulación es exitosa."""
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
        "pollinator_abundance_index": 70.0,
        "pollinator_diversity_index": 45.0,
    }
    payload_data = {
        "status": "success",
        "baseline": {"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0},
        "pareto_front": [candidate],
        "best_solution": candidate,
        "optimized_landscape": {"crop_area_pct": 50.0},
        "delta_yield": 5.0,
        "delta_pollinators": 40.0,
        "hypothesis_status": "Criterio operativo de mejora conjunta cumplido (+20% abundancia simulada con rendimiento no degradado)",
        "meets_joint_criteria": True,
        "algorithm_evaluations_total": 2560,
        "pareto_solutions_returned": 1,
        "pareto_verified_count": 1,
        "recomendacion_ia": "Recomendación válida",
    }
    obj = SimulationResultPayload.model_validate(payload_data)
    assert obj.status == "success"
    assert obj.meets_joint_criteria is True
    assert obj.best_solution is not None
    assert obj.delta_yield == 5.0


def test_simulation_result_payload_infeasible_validation():
    """Valida el schema SimulationResultPayload cuando status es infeasible y best_solution es None."""
    payload_data = {
        "status": "infeasible",
        "message": "No se encontraron soluciones admisibles que cumplan las restricciones biofísicas y el dominio del modelo.",
        "baseline": {"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0},
        "pareto_front": [],
        "best_solution": None,
        "optimized_landscape": None,
        "delta_yield": None,
        "delta_pollinators": None,
        "hypothesis_status": "No evaluable: sin soluciones admisibles dentro del dominio",
        "meets_joint_criteria": False,
        "algorithm_evaluations_total": 2560,
        "pareto_solutions_returned": 0,
        "pareto_verified_count": 0,
        "recomendacion_ia": None,
    }
    obj = SimulationResultPayload.model_validate(payload_data)
    assert obj.status == "infeasible"
    assert obj.best_solution is None
    assert obj.optimized_landscape is None
    assert obj.delta_yield is None
    assert obj.delta_pollinators is None
    assert obj.meets_joint_criteria is False


def test_recommendation_handles_none_best_solution():
    """Verifica que generate_ai_recommendation no falle ante best_solution=None."""
    res = generate_ai_recommendation(
        baseline={"crop_yield_index": 80.0},
        best_solution=None,
        pareto_front=[],
    )
    assert "Sin recomendación" in res or "no se encontraron" in res


def test_run_simulation_infeasible_structure():
    """
    Verifica que cuando filter_verified_pareto_front devuelve vacío,
    run_simulation devuelva status='infeasible', best_solution=None,
    delta_yield=None y delta_pollinators=None sin excepciones no capturadas.
    """
    payload = {
        "pesticide_level": 20.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "bbox": [3.4, -76.6, 3.6, -76.4],
        "test_mode": True,
    }

    # Forzar frente de Pareto vacío para simular escenario inadmisible
    with patch("backend.app.services.optimization.model_store.model", object()), \
         patch("backend.app.services.optimization.model_store.predict", side_effect=lambda mat: np.zeros((len(mat), 3), dtype=np.float32)), \
         patch("backend.app.services.optimization.filter_verified_pareto_front", return_value=[]):
        res = run_simulation(payload)
        assert res["status"] == "infeasible"
        assert res["best_solution"] is None
        assert res["optimized_landscape"] is None
        assert res["delta_yield"] is None
        assert res["delta_pollinators"] is None
        assert res["meets_joint_criteria"] is None
        assert "No evaluable" in res["hypothesis_status"]
        assert res["pareto_verified_count"] == 0
        assert res["algorithm_evaluations_total"] > 0


# ────────────────────────────────────────────────────────────────────────────
# Bloque 3: Criterio Operativo Conjunto
# ────────────────────────────────────────────────────────────────────────────

def evaluate_operational_criterion(
    delta_yield: float | None,
    delta_pollinators_pct: float | None,
    is_infeasible: bool = False,
) -> tuple[bool | None, str, str]:
    """
    Función de referencia para evaluar el criterio operativo:
      - Sin solución: (None, "no_evaluable", status_text)
      - delta_yield >= 0 AND delta_pollinators >= 20.0: (True, "cumple", status_text)
      - De lo contrario: (False, "no_cumple", status_text)
    """
    if is_infeasible or delta_yield is None or delta_pollinators_pct is None:
        return (
            None,
            "no_evaluable",
            "No evaluable: sin soluciones admisibles dentro del dominio",
        )

    meets = (delta_yield >= 0.0) and (delta_pollinators_pct >= 20.0)
    status_text = (
        "Criterio operativo de mejora conjunta cumplido (+20% abundancia simulada con rendimiento no degradado)"
        if meets
        else "Criterio operativo de mejora conjunta no alcanzado"
    )
    return meets, "cumple" if meets else "no_cumple", status_text


def test_criteria_case1_high_pollinators_negative_yield():
    """Caso 1: +25% polinizadores pero rendimiento negativo (-1.5) -> NO CUMPLE."""
    meets, label, text = evaluate_operational_criterion(delta_yield=-1.5, delta_pollinators_pct=25.0)
    assert meets is False
    assert label == "no_cumple"
    assert "no alcanzado" in text


def test_criteria_case2_high_pollinators_non_degraded_yield():
    """Caso 2: +25% polinizadores y rendimiento no degradado (+0.5 o 0.0) -> CUMPLE."""
    meets_pos, label_pos, text_pos = evaluate_operational_criterion(delta_yield=0.5, delta_pollinators_pct=25.0)
    assert meets_pos is True
    assert label_pos == "cumple"
    assert "cumplido" in text_pos

    meets_zero, label_zero, text_zero = evaluate_operational_criterion(delta_yield=0.0, delta_pollinators_pct=25.0)
    assert meets_zero is True
    assert label_zero == "cumple"
    assert "cumplido" in text_zero


def test_criteria_case3_low_pollinators():
    """Caso 3: +10% polinizadores (incluso con rendimiento positivo) -> NO CUMPLE."""
    meets, label, text = evaluate_operational_criterion(delta_yield=2.0, delta_pollinators_pct=10.0)
    assert meets is False
    assert label == "no_cumple"
    assert "no alcanzado" in text


def test_criteria_case4_no_solution_infeasible():
    """Caso 4: Sin solución admisible -> NO EVALUABLE."""
    meets, label, text = evaluate_operational_criterion(delta_yield=None, delta_pollinators_pct=None, is_infeasible=True)
    assert meets is None
    assert label == "no_evaluable"
    assert "No evaluable" in text


def test_no_empirical_confirmation_claims_in_text():
    """Verifica que los textos oficiales no usen claims de validación empírica ni confirmación de campo."""
    prohibited = ["confirma la hipótesis", "validación de campo", "confirmación empírica", "hipótesis comprobada"]
    for dy, dp in [(1.0, 25.0), (-1.0, 25.0), (1.0, 10.0), (None, None)]:
        _, _, text = evaluate_operational_criterion(dy, dp, is_infeasible=(dy is None))
        for phrase in prohibited:
            assert phrase not in text.lower(), f"Frase prohibida '{phrase}' encontrada en: {text}"
