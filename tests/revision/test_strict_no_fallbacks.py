"""
tests/revision/test_strict_no_fallbacks.py
Verificación del Mandato 7: Eliminación de fallbacks silenciosos en ejecución científica.
Comprueba que:
  1. Enriquecimiento ABM 'corrected_full' sin Mesa produce un error explícito y no continúa silenciosamente con 0 simulaciones.
  2. Optimización multiobjetivo sin pymoo produce un error explícito en modo científico.
  3. Modelos habilitados en CV sin dependencias instaladas producen un error explícito en lugar de omitirse silenciosamente.
  4. Los dobles de prueba quedan restringidos exclusivamente al modo test explícito.
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

from scientific_core.generator import generate_coherent_dataset
from scientific_core.nested_cv import run_nested_cv
from backend.app.services.optimization import run_simulation


def test_generator_rejects_missing_abm_in_scientific_mode():
    """Verifica que si falla el ABM con policy='corrected_full' en modo científico, se arroje RuntimeError."""
    # Provocar fallo en la importación de streamlit_app.pollinator_abm simulando ausencia de Mesa
    with patch.dict(sys.modules, {"streamlit_app.pollinator_abm": None}):
        try:
            generate_coherent_dataset(n_samples=10, abm_policy="corrected_full", test_mode=False)
            assert False, "Debió arrojar RuntimeError al faltar dependencia ABM en modo científico."
        except RuntimeError as e:
            assert "Fallo en enriquecimiento ABM solicitado" in str(e)
            print("PASS: Generator arrojó RuntimeError explícito ante fallo de ABM sin fallback silencioso.")


def test_generator_rejects_incoherent_simulation_count():
    """Verifica que no se admita max_abm_simulations menor a n_samples si se exige 'corrected_full'."""
    try:
        generate_coherent_dataset(n_samples=50, abm_policy="corrected_full", max_abm_simulations=10, test_mode=False)
        assert False, "Debió rechazar n_sims < n_samples para corrected_full."
    except ValueError as e:
        assert "exige 50 simulaciones" in str(e)
        print("PASS: Generator rechazó conteo incoherente para corrected_full.")


def test_optimization_rejects_missing_pymoo_in_scientific_mode():
    """Verifica que la optimización científica sin pymoo arroje RuntimeError en vez de muestreo aleatorio heurístico."""
    with patch("backend.app.services.optimization.NSGA2", None), \
         patch("backend.app.services.optimization.model_store.model", object()), \
         patch("backend.app.services.optimization.model_store.predict", return_value=np.zeros((1, 3))):
        payload = {
            "pesticide_level": 25.0,
            "min_natural_area_pct": 20.0,
            "climate_scenario": "current",
            "test_mode": False,  # Modo científico estricto
        }
        try:
            run_simulation(payload)
            assert False, "Debió arrojar RuntimeError ante la ausencia de pymoo en modo científico."
        except RuntimeError as e:
            assert "requiere la biblioteca 'pymoo'" in str(e)
            print("PASS: Optimización arrojó RuntimeError explícito ante ausencia de pymoo.")


def test_nested_cv_rejects_missing_model_dependencies_in_scientific_mode():
    """Verifica que si un modelo habilitado carece de dependencia en modo científico, se arroje RuntimeError."""
    df, _ = generate_coherent_dataset(n_samples=15, abm_policy="corrected_none")
    config = {
        "outer_cv": {"n_splits": 2, "seed": 42},
        "inner_cv": {"n_splits": 2, "seed": 1042},
        "allow_missing_dependencies": False,  # Modo científico estricto
        "models": {
            "xgboost": {"enabled": True, "param_grid": [{}]},
        },
    }

    import scientific_core.nested_cv
    with patch.object(scientific_core.nested_cv, "xgb", None):
        try:
            run_nested_cv(df, config)
            assert False, "Debió arrojar RuntimeError al habilitar XGBoost sin estar disponible en modo científico."
        except RuntimeError as e:
            err_msg = str(e).lower()
            assert "xgboost" in err_msg and ("no disponible" in err_msg or "dependencias" in err_msg or "ausentes" in err_msg)
            print("PASS: Nested CV arrojó RuntimeError explícito por modelo sin dependencias simulado.")


if __name__ == "__main__":
    test_generator_rejects_missing_abm_in_scientific_mode()
    test_generator_rejects_incoherent_simulation_count()
    test_optimization_rejects_missing_pymoo_in_scientific_mode()
    test_nested_cv_rejects_missing_model_dependencies_in_scientific_mode()
