"""
tests/revision/test_t12_to_t15_optimization_domain.py
Pruebas técnicas T12, T13, T14 y T15: Dominio, consistencia de diversidad, filtrado Pareto y caché.
"""
import sys
import tempfile
import shutil
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "backend"))

# Mock settings si get_settings no está inicializado
import os
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"

from scientific_core.contracts import calculate_landscape_diversity, validate_coverage
from app.services.optimization import (
    climate_adjustments,
    calculate_landscape_diversity as opt_calculate_landscape_diversity,
    filter_verified_pareto_front,
    build_cache_key,
    TimedCache,
)
from backend.app.services.model_store import ModelStore


def test_t12_climate_and_domain_error():
    """
    T12: Verifica que escenarios climáticos desconocidos o entradas fuera de dominio
    generan una excepción trazable (ValueError) en lugar de silenciarse.
    """
    # 1. Escenario climático no reconocido
    unknown_passed = False
    try:
        climate_adjustments("invalid_climate_scenario_code")
        unknown_passed = True
    except ValueError as e:
        assert "Escenario climático desconocido" in str(e)
    assert not unknown_passed, "Debe rechazar escenarios climáticos desconocidos"

    # 2. Dominio univariado fuera de rango
    store = ModelStore()
    invalid_features = {
        "crop_area_pct": 120.0,  # Excede 100%
        "natural_area_pct": 20.0,
        "floral_strips_pct": 10.0,
        "temperature_c": 60.0,   # Excede 45°C
    }
    check = store.check_domain(invalid_features)
    assert check["is_valid"] is False
    assert len(check["violations"]) >= 2
    print("T12 PASSED: Clima y dominio fuera de rango rechazan con excepción trazable.")


def test_t13_landscape_diversity_consistency():
    """
    T13: Verifica que la función biofísica de diversidad es idéntica en contratos,
    generador de datos, línea base y optimización.
    """
    test_cases = [
        (20.0, 8.0, 70.0),
        (35.0, 14.0, 90.0),
        (5.0, 2.0, 40.0),
    ]
    for nat, flor, soil in test_cases:
        div_core = calculate_landscape_diversity(nat, flor, soil)
        div_opt = opt_calculate_landscape_diversity(nat, flor, soil)
        assert abs(div_core - div_opt) < 1e-6, f"Discrepancia en diversidad: {div_core} vs {div_opt}"
    print("T13 PASSED: Misma función de diversidad en contratos y optimización.")


def test_t14_pareto_front_filtration():
    """
    T14: Verifica que las soluciones dominadas y duplicadas se eliminan correctamente
    para producir un frente no dominado verificado.
    """
    candidates = [
        # A: (yield=80, abund=70)
        {"crop_area_pct": 50.0, "natural_area_pct": 20.0, "floral_strips_pct": 8.0, "pesticide_level": 30.0, "soil_management_score": 70.0, "crop_yield_index": 80.0, "pollinator_abundance_index": 70.0, "pollinator_diversity_index": 25.0},
        # B: (yield=85, abund=75) -> Domina estrictamente a A
        {"crop_area_pct": 52.0, "natural_area_pct": 22.0, "floral_strips_pct": 8.0, "pesticide_level": 25.0, "soil_management_score": 75.0, "crop_yield_index": 85.0, "pollinator_abundance_index": 75.0, "pollinator_diversity_index": 28.0},
        # C: (yield=70, abund=90) -> No dominada por B (mayor abundancia)
        {"crop_area_pct": 40.0, "natural_area_pct": 30.0, "floral_strips_pct": 12.0, "pesticide_level": 15.0, "soil_management_score": 85.0, "crop_yield_index": 70.0, "pollinator_abundance_index": 90.0, "pollinator_diversity_index": 35.0},
        # D: Copia duplicada de B
        {"crop_area_pct": 52.0, "natural_area_pct": 22.0, "floral_strips_pct": 8.0, "pesticide_level": 25.0, "soil_management_score": 75.0, "crop_yield_index": 85.0, "pollinator_abundance_index": 75.0, "pollinator_diversity_index": 28.0},
    ]

    verified = filter_verified_pareto_front(candidates)
    # A debe ser eliminada (dominada por B). D debe ser eliminada (duplicada).
    # Solo deben quedar B y C.
    assert len(verified) == 2, f"Se esperaban 2 soluciones en el frente verificado, se obtuvieron {len(verified)}"
    yields = [sol["crop_yield_index"] for sol in verified]
    assert 80.0 not in yields, "La solución A dominada no fue filtrada"
    assert 85.0 in yields
    assert 70.0 in yields
    print("T14 PASSED: Soluciones dominadas y duplicadas filtradas a precisión completa.")


def test_t15_cache_invalidation_on_model_change():
    """
    T15: Verifica que la clave de caché cambia cuando cambia la versión del modelo,
    evitando que se reutilicen resultados anteriores de otro modelo.
    """
    payload = {"min_natural_area_pct": 20.0, "pesticide_level": 30.0, "climate_scenario": "current"}

    key_v1 = build_cache_key(payload, model_version="surrogate_v1")
    key_v2 = build_cache_key(payload, model_version="surrogate_v2")

    assert key_v1 != key_v2, "La clave de caché no debe coincidir entre versiones distintas de modelo"

    cache = TimedCache(ttl_seconds=60, max_items=10)
    cache.set(key_v1, {"sim_result": "from_model_1"})

    # Consultar con clave v2
    assert cache.get(key_v2) is None, "Caché de modelo anterior devuelta erróneamente para modelo nuevo"
    print("T15 PASSED: Cambio de modelo invalida automáticamente la caché previa.")


if __name__ == "__main__":
    test_t12_climate_and_domain_error()
    test_t13_landscape_diversity_consistency()
    test_t14_pareto_front_filtration()
    test_t15_cache_invalidation_on_model_change()
    print("All optimization and domain tests passed successfully!")
