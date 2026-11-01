"""
tests/revision/test_audit03_final_selection.py
Pruebas de regresión obligatorias para la Auditoría 03 - Bloque 1:
Unificación de la selección y reajuste final entre CLI y Streamlit.
"""
import json
import pytest
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from scientific_core.nested_cv import (
    ModelFactory,
    parse_params_string,
    select_final_hyperparameters,
)


def test_audit03_rf_null_params_preserved_in_refit():
    """
    Prueba A: Random Forest con n_estimators=3 y max_depth=null mantiene
    esos valores exactos en el reajuste y no cae silenciosamente a {} ni a 100 árboles.
    """
    raw_json = '{"n_estimators": 3, "max_depth": null}'
    parsed = parse_params_string(raw_json)
    assert parsed == {"n_estimators": 3, "max_depth": None}
    assert parsed["n_estimators"] == 3
    assert parsed["max_depth"] is None

    # Simular tuning records con 2 folds y este candidato
    records = [
        {"model_family": "random_forest", "outer_fold": 0, "params": raw_json, "inner_macro_mae": 0.25, "inner_macro_rmse": 0.30},
        {"model_family": "random_forest", "outer_fold": 1, "params": raw_json, "inner_macro_mae": 0.27, "inner_macro_rmse": 0.32},
    ]
    df_records = pd.DataFrame(records)

    best_params, optimal_epochs, selection_policy = select_final_hyperparameters(
        df_records, model_family="random_forest", expected_n_evaluations=2
    )
    assert best_params == {"n_estimators": 3, "max_depth": None}
    assert selection_policy["selected_params"] == {"n_estimators": 3, "max_depth": None}

    # Instanciar modelo vía ModelFactory
    model = ModelFactory.create_model("random_forest", best_params, random_state=42)
    assert isinstance(model, RandomForestRegressor)
    assert model.n_estimators == 3
    assert model.max_depth is None


def test_audit03_lucky_fold_candidate_does_not_win():
    """
    Prueba B: Un candidato con un fold excepcionalmente favorable (lucky fold)
    no gana si su promedio a través de todos los folds es peor que el de un candidato consistente.
    """
    params_lucky = '{"alpha": 0.01}'
    params_consistent = '{"alpha": 1.0}'

    records = [
        # Fold 0: lucky fold tiene un error mínimo artificial de 0.05
        {"model_family": "ridge", "outer_fold": 0, "params": params_lucky, "inner_macro_mae": 0.05, "inner_macro_rmse": 0.08},
        {"model_family": "ridge", "outer_fold": 0, "params": params_consistent, "inner_macro_mae": 0.15, "inner_macro_rmse": 0.20},
        # Fold 1: lucky fold colapsa a 0.60, consistente se mantiene en 0.16
        {"model_family": "ridge", "outer_fold": 1, "params": params_lucky, "inner_macro_mae": 0.60, "inner_macro_rmse": 0.70},
        {"model_family": "ridge", "outer_fold": 1, "params": params_consistent, "inner_macro_mae": 0.16, "inner_macro_rmse": 0.21},
    ]
    # Promedio MAE:
    # lucky: (0.05 + 0.60) / 2 = 0.325
    # consistent: (0.15 + 0.16) / 2 = 0.155 (GANADOR)
    df_records = pd.DataFrame(records)

    best_params, optimal_epochs, selection_policy = select_final_hyperparameters(
        df_records, model_family="ridge", expected_n_evaluations=2
    )
    assert best_params == {"alpha": 1.0}
    assert selection_policy["candidates"][0]["mean_inner_macro_mae"] == pytest.approx(0.155)
    assert selection_policy["selected_params"] == {"alpha": 1.0}


def test_audit03_cli_streamlit_parity_selection():
    """
    Prueba C: CLI y Streamlit producen idéntica selección sobre el mismo conjunto de datos y tuning records.
    """
    records = [
        {"model_family": "ridge", "outer_fold": 0, "params": '{"alpha": 0.1}', "inner_macro_mae": 0.20, "inner_macro_rmse": 0.25},
        {"model_family": "ridge", "outer_fold": 0, "params": '{"alpha": 1.0}', "inner_macro_mae": 0.22, "inner_macro_rmse": 0.28},
        {"model_family": "ridge", "outer_fold": 1, "params": '{"alpha": 0.1}', "inner_macro_mae": 0.21, "inner_macro_rmse": 0.26},
        {"model_family": "ridge", "outer_fold": 1, "params": '{"alpha": 1.0}', "inner_macro_mae": 0.23, "inner_macro_rmse": 0.29},
    ]
    df_records = pd.DataFrame(records)

    # Invocación 1 (como en CLI)
    params_cli, _, policy_cli = select_final_hyperparameters(df_records, model_family="ridge", expected_n_evaluations=2)
    # Invocación 2 (como en Streamlit advanced_training)
    params_st, _, policy_st = select_final_hyperparameters(df_records, model_family="ridge", expected_n_evaluations=2)

    assert params_cli == params_st
    assert json.dumps(params_cli, sort_keys=True) == json.dumps(params_st, sort_keys=True)
    assert policy_cli["selected_params"] == policy_st["selected_params"]


def test_audit03_malformed_params_raise_traceable_error():
    """
    Prueba D: Parámetros malformados o no serializables no se reemplazan en silencio por {}
    sino que lanzan ValueError trazable.
    """
    # 1. Parámetros malformados sintácticamente
    with pytest.raises(ValueError, match="cadena malformada"):
        parse_params_string("INVALID_JSON_AND_NOT_PYTHON_DICT {{{")

    # 2. Puntuaciones no finitas (NaN / Inf) en tuning records
    records_nan = [
        {"model_family": "ridge", "outer_fold": 0, "params": '{"alpha": 1.0}', "inner_macro_mae": float("nan"), "inner_macro_rmse": 0.2},
        {"model_family": "ridge", "outer_fold": 1, "params": '{"alpha": 1.0}', "inner_macro_mae": 0.2, "inner_macro_rmse": 0.2},
    ]
    with pytest.raises(ValueError, match="no finitas"):
        select_final_hyperparameters(pd.DataFrame(records_nan), model_family="ridge", expected_n_evaluations=2)

    # 3. Cobertura incompleta sin flag de adaptación
    records_incomplete = [
        {"model_family": "ridge", "outer_fold": 0, "params": '{"alpha": 1.0}', "inner_macro_mae": 0.2, "inner_macro_rmse": 0.2},
        # Falta fold 1 (se requieren 2 evaluaciones)
    ]
    with pytest.raises(ValueError, match="cobertura"):
        select_final_hyperparameters(pd.DataFrame(records_incomplete), model_family="ridge", expected_n_evaluations=2, allow_adaptation=False)
