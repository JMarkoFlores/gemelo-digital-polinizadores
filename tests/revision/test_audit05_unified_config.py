"""
tests/revision/test_audit05_unified_config.py
Pruebas de regresión para el Hallazgo 1 de la Auditoría 05:
Configuración única para ejecución y persistencia en Streamlit.

Verifica:
1. Paridad estricta entre la configuración recibida por run_nested_cv y la guardada en config_effective.json.
2. Comportamiento con group_duplicates=False en modo exploratorio (ambos persisten y ejecutan con False).
3. Paridad con group_duplicates=True en modo exploratorio.
4. Rechazo explícito con ValueError si se intenta group_duplicates=False en modo científico estricto.
5. Preservación del modo científico por defecto con group_duplicates=True.
6. Compatibilidad cuando se inyecta un config preconstruido a train_and_evaluate_all_models.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest

import scientific_core.nested_cv
from streamlit_app.adapter import (
    prepare_streamlit_run_config,
    execute_streamlit_training_run,
)
from streamlit_app.advanced_training import train_and_evaluate_all_models


@pytest.fixture
def minimal_dataset() -> pd.DataFrame:
    """Dataset sintético mínimo con columnas válidas del contrato."""
    rng = np.random.default_rng(2026)
    n = 24
    crop = rng.uniform(40.0, 60.0, size=n)
    nat = rng.uniform(15.0, 25.0, size=n)
    flor = rng.uniform(3.0, 8.0, size=n)
    pest = rng.uniform(10.0, 40.0, size=n)
    soil = rng.uniform(60.0, 90.0, size=n)
    temp = rng.uniform(20.0, 28.0, size=n)
    prec = rng.uniform(800.0, 1200.0, size=n)
    div = (nat / 100.0) * 0.5 + (flor / 100.0) * 0.3 + (soil / 100.0) * 0.2

    y_yield = crop * 1.5 + soil * 0.3 - pest * 0.2
    y_abund = nat * 2.0 + flor * 3.0 - pest * 0.5
    y_div = div * 100.0

    data = {
        "sample_id": [f"SMP_{i:04d}" for i in range(n)],
        "crop_area_pct": crop,
        "natural_area_pct": nat,
        "floral_strips_pct": flor,
        "pesticide_level": pest,
        "soil_management_score": soil,
        "temperature_c": temp,
        "precipitation_mm": prec,
        "landscape_diversity": div,
        "crop_yield_index": y_yield,
        "pollinator_abundance_index": y_abund,
        "pollinator_diversity_index": y_div,
    }
    return pd.DataFrame(data)


def test_parity_between_executed_and_persisted_config_group_duplicates_false(minimal_dataset: pd.DataFrame):
    """
    Verifica que en modo exploratorio con group_duplicates=False:
    1. run_nested_cv recibe exactamente group_duplicates=False.
    2. config_effective.json persiste exactamente group_duplicates=False.
    3. No existe divergencia entre la configuración ejecutada y la persistida.
    """
    fast_base_config = {
        "models": {
            "ridge": {"enabled": True, "param_grid": [{"alpha": 1.0}]},
        },
        "inner_cv": {"n_splits": 2},
    }

    with tempfile.TemporaryDirectory() as tmp_artifacts:
        artifacts_dir = Path(tmp_artifacts)
        captured_configs = []

        real_run_nested_cv = scientific_core.nested_cv.run_nested_cv

        def spy_run_nested_cv(df, config, *args, **kwargs):
            captured_configs.append(config)
            return real_run_nested_cv(df, config, *args, **kwargs)

        with patch("streamlit_app.advanced_training.run_nested_cv", side_effect=spy_run_nested_cv):
            res = execute_streamlit_training_run(
                dataframe=minimal_dataset,
                k_folds=2,
                tune_hyperparameters=False,
                scientific_mode=False,
                group_duplicates=False,
                random_state=42,
                base_artifacts_dir=artifacts_dir,
                config=prepare_streamlit_run_config(
                    k_folds=2,
                    tune_hyperparameters=False,
                    scientific_mode=False,
                    group_duplicates=False,
                    random_state=42,
                    base_config=fast_base_config,
                ),
            )

            assert len(captured_configs) == 1, "run_nested_cv debió invocarse exactamente una vez"
            executed_config = captured_configs[0]

            run_dir = Path(res["run_dir"])
            persisted_config_path = run_dir / "config_effective.json"
            assert persisted_config_path.is_file(), "config_effective.json debe existir físicamente"

            with open(persisted_config_path, "r", encoding="utf-8") as f:
                persisted_config = json.load(f)

            # Comprobar group_duplicates en ejecución y persistencia
            assert executed_config["outer_cv"]["group_duplicates"] is False
            assert persisted_config["outer_cv"]["group_duplicates"] is False

            # Comprobar igualdad estricta de la configuración ejecutada vs persistida
            assert executed_config == persisted_config


def test_parity_between_executed_and_persisted_config_group_duplicates_true(minimal_dataset: pd.DataFrame):
    """
    Verifica paridad total cuando group_duplicates=True explícito.
    """
    fast_base_config = {
        "models": {
            "ridge": {"enabled": True, "param_grid": [{"alpha": 1.0}]},
        },
        "inner_cv": {"n_splits": 2},
    }

    with tempfile.TemporaryDirectory() as tmp_artifacts:
        artifacts_dir = Path(tmp_artifacts)
        captured_configs = []

        real_run_nested_cv = scientific_core.nested_cv.run_nested_cv

        def spy_run_nested_cv(df, config, *args, **kwargs):
            captured_configs.append(config)
            return real_run_nested_cv(df, config, *args, **kwargs)

        with patch("streamlit_app.advanced_training.run_nested_cv", side_effect=spy_run_nested_cv):
            res = execute_streamlit_training_run(
                dataframe=minimal_dataset,
                k_folds=2,
                tune_hyperparameters=False,
                scientific_mode=False,
                group_duplicates=True,
                random_state=42,
                base_artifacts_dir=artifacts_dir,
                config=prepare_streamlit_run_config(
                    k_folds=2,
                    tune_hyperparameters=False,
                    scientific_mode=False,
                    group_duplicates=True,
                    random_state=42,
                    base_config=fast_base_config,
                ),
            )

            executed_config = captured_configs[0]
            with open(Path(res["run_dir"]) / "config_effective.json", "r", encoding="utf-8") as f:
                persisted_config = json.load(f)

            assert executed_config["outer_cv"]["group_duplicates"] is True
            assert persisted_config["outer_cv"]["group_duplicates"] is True
            assert executed_config == persisted_config


def test_scientific_mode_rejects_group_duplicates_false(minimal_dataset: pd.DataFrame):
    """
    Verifica que en modo científico estricto (scientific_mode=True):
    Si se solicita group_duplicates=False, se rechaza expresamente con ValueError
    y NO se inicia el entrenamiento.
    """
    # 1. En prepare_streamlit_run_config directamente
    with pytest.raises(ValueError, match="no puede ser False en modo científico estricto"):
        prepare_streamlit_run_config(
            scientific_mode=True,
            group_duplicates=False,
        )

    # 2. En execute_streamlit_training_run
    with tempfile.TemporaryDirectory() as tmp_artifacts:
        with pytest.raises(ValueError, match="no puede ser False en modo científico estricto"):
            execute_streamlit_training_run(
                dataframe=minimal_dataset,
                scientific_mode=True,
                group_duplicates=False,
                base_artifacts_dir=Path(tmp_artifacts),
            )


def test_scientific_mode_defaults_to_group_duplicates_true():
    """
    Verifica que en modo científico estricto, la configuración por defecto
    obliga group_duplicates=True y fija splits reproducibles.
    """
    cfg = prepare_streamlit_run_config(scientific_mode=True)
    assert cfg["scientific_mode"] is True
    assert cfg["outer_cv"]["group_duplicates"] is True
    assert cfg["outer_cv"]["n_splits"] == 5
    assert cfg["inner_cv"]["n_splits"] == 3


def test_advanced_training_respects_passed_config(minimal_dataset: pd.DataFrame):
    """
    Verifica que train_and_evaluate_all_models acepta un config preconstruido,
    no lo sobreescribe ni lo refactoriza, y lo retorna exactamente en config_effective.
    """
    fast_base_config = {
        "models": {
            "ridge": {"enabled": True, "param_grid": [{"alpha": 1.0}]},
        },
        "inner_cv": {"n_splits": 2},
    }
    custom_config = prepare_streamlit_run_config(
        k_folds=2,
        tune_hyperparameters=False,
        scientific_mode=False,
        group_duplicates=False,
        random_state=999,
        base_config=fast_base_config,
    )
    # Marcar un campo identificador único
    custom_config["test_custom_marker"] = "custom_audit05_marker"

    captured_configs = []
    real_run_nested_cv = scientific_core.nested_cv.run_nested_cv

    def spy_run_nested_cv(df, config, *args, **kwargs):
        captured_configs.append(config)
        return real_run_nested_cv(df, config, *args, **kwargs)

    with patch("streamlit_app.advanced_training.run_nested_cv", side_effect=spy_run_nested_cv):
        results = train_and_evaluate_all_models(
            dataframe=minimal_dataset,
            config=custom_config,
        )

        assert len(captured_configs) == 1
        assert captured_configs[0]["test_custom_marker"] == "custom_audit05_marker"
        assert captured_configs[0]["outer_cv"]["group_duplicates"] is False
        assert results["config_effective"]["test_custom_marker"] == "custom_audit05_marker"
        assert results["config_effective"] is custom_config
