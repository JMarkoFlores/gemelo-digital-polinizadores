"""
tests/revision/test_domain_integrated_optimization.py
Verifica la integración del dominio aprendido en NSGA-II:
  - Intersección de límites físicos con observed_training_ranges.
  - Error informativo si la intersección es vacía.
  - Penalización severa para candidatos que caigan fuera del dominio.
  - Frente de Pareto libre de extrapolaciones fuera de dominio (Bloque 9 de la Auditoría 02).
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
import pytest

from app.services.model_store import model_store
from app.services.optimization import (
    LandscapeOptimizationProblem,
    filter_verified_pareto_front,
    run_simulation,
)
from scientific_core.contracts import FEATURE_COLUMNS, TARGET_COLUMNS


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
    model_store.model = MockPredictor()
    model_store.model_type = "mock"
    model_store.bundle_id = "bundle_mock_domain_opt"
    model_store.scaler_x = None
    model_store.scaler_y = None
    model_store.metadata = {
        "observed_training_ranges": {
            "crop_area_pct": [20.0, 80.0],          # Físico es [15.0, 85.0] -> Intersección [20.0, 80.0]
            "natural_area_pct": [10.0, 40.0],       # Físico es [min_nat, 50.0] -> Intersección [max(10, min_nat), 40.0]
            "floral_strips_pct": [2.0, 15.0],       # Físico es [1.0, 20.0] -> Intersección [2.0, 15.0]
            "pesticide_level": [5.0, 60.0],         # Físico es [0.0, 80.0] -> Intersección [5.0, 60.0]
            "soil_management_score": [40.0, 90.0],   # Físico es [30.0, 95.0] -> Intersección [40.0, 90.0]
            "temperature_c": [15.0, 30.0],
            "precipitation_mm": [500.0, 2000.0],
            "landscape_diversity": [0.1, 0.95],
        },
        "clima_resumen": {
            "temperature_mean": 23.5,
            "precipitation_annual_mean": 1100.0,
        },
    }
    model_store.allow_test_bundle = True
    yield
    model_store.metadata = {}


def test_optimization_bounds_intersected_with_learned_domain():
    """Los límites de búsqueda de NSGA-II deben ser la intersección exacta de físicos y aprendidos."""
    problem = LandscapeOptimizationProblem(
        context=None,
        baseline_features={"temperature_c": 23.5, "precipitation_mm": 1100.0},
        min_natural_area_pct=15.0,
        climate_scenario="current",
    )

    # Variables de decisión: [crop, nat, flor, pest, soil]
    # crop: max(15, 20)=20.0, min(85, 80)=80.0
    assert problem.xl[0] == pytest.approx(20.0)
    assert problem.xu[0] == pytest.approx(80.0)

    # nat: max(15, 10)=15.0, min(50, 40)=40.0
    assert problem.xl[1] == pytest.approx(15.0)
    assert problem.xu[1] == pytest.approx(40.0)

    # flor: max(1, 2)=2.0, min(20, 15)=15.0
    assert problem.xl[2] == pytest.approx(2.0)
    assert problem.xu[2] == pytest.approx(15.0)

    # pest: max(0, 5)=5.0, min(80, 60)=60.0
    assert problem.xl[3] == pytest.approx(5.0)
    assert problem.xu[3] == pytest.approx(60.0)

    # soil: max(30, 40)=40.0, min(95, 90)=90.0
    assert problem.xl[4] == pytest.approx(40.0)
    assert problem.xu[4] == pytest.approx(90.0)


def test_empty_intersection_raises_informative_error():
    """Si los límites físicos y el rango observado no se intersectan, debe fallar con error explicativo."""
    # Simular que el entrenamiento solo vio crop_area_pct entre 0 y 10 (físico inferior es 15)
    model_store.metadata["observed_training_ranges"]["crop_area_pct"] = [0.0, 10.0]

    with pytest.raises(ValueError, match="Conflicto entre restricciones físicas y dominio aprendido"):
        LandscapeOptimizationProblem(
            context=None,
            baseline_features={"temperature_c": 23.5, "precipitation_mm": 1100.0},
            min_natural_area_pct=15.0,
            climate_scenario="current",
        )


def test_pareto_front_strictly_within_domain():
    """Verifica que la simulación de optimización descarte cualquier candidato fuera de dominio."""
    payload = {
        "pesticide_level": 25.0,
        "min_natural_area_pct": 20.0,
        "climate_scenario": "current",
        "bbox": [3.4, -76.6, 3.6, -76.4],
        "test_mode": True,
    }

    result = run_simulation(payload)
    assert result["status"] == "success"
    pareto_front = result["pareto_front"]

    for sol in pareto_front:
        chk = model_store.check_domain(sol)
        assert chk["is_valid"] is True, f"Solución en Pareto fuera de dominio: {chk['violations']}"
        assert 20.0 <= sol["crop_area_pct"] <= 80.0001
        assert 5.0 <= sol["pesticide_level"] <= 60.0001
