"""
tests/revision/test_t16_narrative_integrity.py
Prueba técnica T16: Verificar que el servicio de recomendaciones narrativas
no muta los números estructurados ni afirma validación de campo inexistente.
"""
import sys
import copy
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "backend"))

import os
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"

from app.services.recommendation_service import generate_ai_recommendation


def test_t16_narrative_does_not_mutate_numbers_or_claim_validation():
    baseline = {
        "crop_yield_index": 72.5,
        "pollinator_abundance_index": 45.0,
        "pesticide_level": 30.0,
        "natural_area_pct": 20.0,
    }
    best_solution = {
        "crop_yield_index": 73.0,
        "pollinator_abundance_index": 56.0,
        "crop_area_pct": 58.0,
        "natural_area_pct": 26.0,
        "floral_strips_pct": 12.0,
        "pesticide_level": 10.0,
        "soil_management_score": 85.0,
    }
    pareto_front = [
        best_solution,
        {"crop_yield_index": 80.0, "pollinator_abundance_index": 40.0},
        {"crop_yield_index": 65.0, "pollinator_abundance_index": 70.0},
    ]

    base_copy = copy.deepcopy(baseline)
    sol_copy = copy.deepcopy(best_solution)
    pareto_copy = copy.deepcopy(pareto_front)

    recommendation = generate_ai_recommendation(baseline, best_solution, pareto_front)

    # 1. Comprobar que los objetos no fueron mutados
    assert baseline == base_copy, "El diccionario baseline fue mutado por la generación de narrativa"
    assert best_solution == sol_copy, "El diccionario best_solution fue mutado por la narrativa"
    assert pareto_front == pareto_copy, "El frente de Pareto fue mutado por la narrativa"

    # 2. Comprobar que la narrativa incluye el origen
    assert "[Origen:" in recommendation, "La recomendación no declara explícitamente su origen"

    # 3. Comprobar que no afirma rentabilidad económica ni comprobación de campo
    lowered = recommendation.lower()
    assert "rentabilidad económica asegurada" not in lowered
    assert "validado en campo" not in lowered
    print("T16 PASSED: La narrativa incluye origen, no muta métricas numéricas y no afirma validación de campo.")


if __name__ == "__main__":
    test_t16_narrative_does_not_mutate_numbers_or_claim_validation()
    print("T16 passed successfully!")
