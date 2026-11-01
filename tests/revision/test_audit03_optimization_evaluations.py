"""
tests/revision/test_audit03_optimization_evaluations.py
Pruebas de regresión obligatorias para la Auditoría 03 - Bloque 7:
Distinción explícita entre evaluaciones totales del algoritmo (algorithm_evaluations_total),
soluciones retornadas por el solver (pareto_solutions_returned) y soluciones verificadas (pareto_verified_count).
"""
import numpy as np
import pytest
from app.services.model_store import model_store
from app.services.optimization import run_simulation
from scientific_core.model_bundle import UniversalSurrogatePredictor


class MockPredictor:
    def predict(self, X):
        X_arr = np.asarray(X, dtype=np.float32)
        n = len(X_arr)
        preds = np.zeros((n, 3), dtype=np.float32)
        preds[:, 0] = 100.0 + X_arr[:, 0] * 0.2  # yield
        preds[:, 1] = 50.0 + X_arr[:, 1] * 1.5   # pollinators
        preds[:, 2] = 40.0 + X_arr[:, 4] * 0.3   # diversity
        return preds


@pytest.fixture(autouse=True)
def setup_mock_model_store():
    mock_model = MockPredictor()
    metadata = {
        "observed_training_ranges": {
            "crop_area_pct": [15.0, 85.0],
            "natural_area_pct": [1.0, 50.0],
            "floral_strips_pct": [1.0, 20.0],
            "pesticide_level": [0.0, 80.0],
            "soil_management_score": [30.0, 95.0],
            "temperature_c": [15.0, 35.0],
            "precipitation_mm": [300.0, 2500.0],
            "landscape_diversity": [0.1, 0.95],
        },
        "clima_resumen": {
            "temperature_mean": 23.5,
            "precipitation_annual_mean": 1100.0,
        },
        "test_only": False,
        "bundle_id": "bundle_mock_eval_count",
    }
    predictor = UniversalSurrogatePredictor(
        model=mock_model,
        model_type="ridge",
        scaler_x=None,
        scaler_y=None,
        metadata=metadata,
    )
    model_store._active_predictor = predictor
    model_store.model = mock_model
    model_store.model_type = "ridge"
    model_store.bundle_id = "bundle_mock_eval_count"
    model_store.metadata = metadata
    model_store.allow_test_bundle = True
    model_store.status_message = "Ready"
    yield
    model_store.metadata = {}
    model_store._active_predictor = None


def test_optimization_evaluations_count_distinction():
    """
    Verifica que en una ejecución de optimización:
    1. algorithm_evaluations_total reporta las evaluaciones totales del algoritmo evolutivo (~2560 para 40 gen * 64 pop en pymoo, o 16 en test_mode).
    2. pareto_solutions_returned reporta el tamaño del frente devuelto por el algoritmo.
    3. pareto_verified_count reporta las soluciones no dominadas y válidas retenidas.
    4. pareto_candidates_evaluated se mantiene como alias retrocompatible.
    """
    payload = {
        "pesticide_level": 20.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "test_mode": True,  # Ejecuta simulación controlada
    }
    result = run_simulation(payload)

    assert result["status"] == "success"
    assert "algorithm_evaluations_total" in result
    assert "pareto_solutions_returned" in result
    assert "pareto_verified_count" in result
    assert "pareto_candidates_evaluated" in result

    # Verificar congruencia
    assert result["pareto_candidates_evaluated"] == result["algorithm_evaluations_total"]
    assert result["pareto_solutions_returned"] >= result["pareto_verified_count"]
    assert len(result["pareto_front"]) == result["pareto_verified_count"]
