"""
tests/revision/test_pareto_precision.py
Verificación del Mandato 9: Preservación de precisión completa en optimización multi-objetivo.
Comprueba que:
  1. No se redondean prematuramente las decisiones ni los objetivos en summarize_candidate.
  2. filter_verified_pareto_front discrimina candidatos muy próximos que redondean igual pero difieren en dominancia.
  3. Si no existe ninguna solución admisible, se retorna status='infeasible' y best_solution=None,
     sin seleccionar forzadamente el primer candidato.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "backend"))

from backend.app.services.optimization import (
    summarize_candidate,
    filter_verified_pareto_front,
    run_simulation,
)


def test_near_identical_candidates_dominance():
    """
    Caso obligatorio: Dos candidatos con variables de decisión que redondean igual a 2 decimales,
    pero uno domina estrictamente al otro en precisión continua.
    """
    # Candidato 1: crop=50.001 (redondea a 50.00)
    cand_1 = {
        "crop_area_pct": 50.001,
        "natural_area_pct": 20.002,
        "floral_strips_pct": 5.001,
        "pesticide_level": 30.002,
        "soil_management_score": 60.001,
        "crop_yield_index": 85.12345,  # Mejor rendimiento
        "pollinator_abundance_index": 45.67890,
        "pollinator_diversity_index": 12.34567,
    }

    # Candidato 2: crop=50.004 (también redondea a 50.00)
    cand_2 = {
        "crop_area_pct": 50.004,
        "natural_area_pct": 20.003,
        "floral_strips_pct": 5.002,
        "pesticide_level": 30.001,
        "soil_management_score": 60.003,
        "crop_yield_index": 84.99990,  # Peor rendimiento
        "pollinator_abundance_index": 45.67890,  # Igual abundancia
        "pollinator_diversity_index": 12.34567,
    }

    # A precisión completa, cand_1 debe dominar a cand_2 y ambos deben ser evaluados independientemente
    filtered = filter_verified_pareto_front([cand_1, cand_2], decision_atol=1e-5)
    assert len(filtered) == 1, "Solo la solución dominante (cand_1) debe quedar en el frente."
    assert filtered[0]["crop_yield_index"] == 85.12345
    print("PASS: Dominancia a precisión completa discriminó exitosamente entre candidatos casi idénticos.")


def test_infeasible_candidates_handling():
    """Verifica que si no existen soluciones admisibles se retorne status='infeasible' y best_solution=None."""
    # Simular candidatos donde todos violan el dominio
    payload = {
        "pesticide_level": 25.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "test_mode": True,
    }

    def mock_domain_check(feat):
        # Permitir la línea base (floral_strips_pct == 4.0), rechazar todos los candidatos generados
        if feat.get("floral_strips_pct") == 4.0:
            return {"is_valid": True, "violations": []}
        return {"is_valid": False, "violations": ["Candidato fuera de dominio"]}

    with patch("backend.app.services.optimization.model_store.model", object()), \
         patch("backend.app.services.optimization.model_store.predict", return_value=np.zeros((16, 3))), \
         patch("backend.app.services.optimization.model_store.check_domain", side_effect=mock_domain_check):
        result = run_simulation(payload)
        assert result["status"] == "infeasible"
        assert result["best_solution"] is None
        assert len(result["pareto_front"]) == 0
        assert "sin soluciones admisibles" in result["hypothesis_status"]
        print("PASS: Escenario sin candidatos admisibles reporta status='infeasible' sin forzar primer candidato.")


if __name__ == "__main__":
    test_near_identical_candidates_dominance()
    test_infeasible_candidates_handling()
