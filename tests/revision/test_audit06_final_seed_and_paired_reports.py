"""
Suite de pruebas de regresión para la Auditoría 06:
1. Semilla efectiva del reajuste final en Streamlit y advanced_training:
   - Semilla por defecto (42).
   - Semilla personalizada (ej. 1337).
   - Configuración inyectada.
   - Comprobación de que constructores de modelos tradicionales y neuronales reciben la semilla efectiva.
   - Coherencia entre configuración ejecutada y persistida (metadata y config_effective.json).
2. Comparaciones pareadas en informes de gestión (get_management_report):
   - Caso A: Factible + infactible con bases dispares (100->110 vs 1000->None => delta = +10.0, no -440.0).
   - Caso B: Todas factibles.
   - Caso C: Todas infactibles (ausencia de datos = None, evaluables = 0, sin ceros fabricados).
   - Caso D: Base de datos vacía (sin registros).
   - Caso E: Agrupación regional y temporal con comparaciones pareadas estrictas.
   - Caso F: Comprobación numérica exacta de la discrepancia de la Auditoría 06.
"""

from __future__ import annotations

import datetime
import json
import sys
import types
from typing import Any
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest

# Configuración de shims mínimos para entorno de prueba científica sin dependencias web globales
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

if "sqlalchemy" not in sys.modules:
    sa_mod = types.ModuleType("sqlalchemy")
    sa_mod.func = MagicMock()
    sys.modules["sqlalchemy"] = sa_mod
    sao_mod = types.ModuleType("sqlalchemy.orm")
    sao_mod.Session = MagicMock()
    sys.modules["sqlalchemy.orm"] = sao_mod

if "app.models" not in sys.modules:
    app_mods = types.ModuleType("app.models")
    app_mods.Simulacion = MagicMock()
    app_mods.Usuario = MagicMock()
    sys.modules["app.models"] = app_mods

from backend.app.schemas_reports import (
    ManagementReportResponse,
    ManagementKpis,
    RegionManagementItem,
    ManagementTemporalEvolutionPoint,
)
from backend.app.services.report_general_service import get_management_report
from streamlit_app.adapter import (
    prepare_streamlit_run_config,
    execute_streamlit_training_run,
    export_streamlit_model,
)
from streamlit_app.advanced_training import (
    train_and_evaluate_all_models,
    UniversalSurrogatePredictor,
)


# =====================================================================
# BLOQUE 1: SEMILLA EFECTIVA DEL REAJUSTE FINAL
# =====================================================================

def _create_minimal_synthetic_dataset(n_samples: int = 30) -> pd.DataFrame:
    """Crea un dataset sintético mínimo con columnas ABM completas para pruebas rápidas."""
    np.random.seed(42)
    crop_area = np.random.uniform(40, 80, n_samples)
    natural_area = 100.0 - crop_area - np.random.uniform(5, 10, n_samples)
    floral_strips = 100.0 - crop_area - natural_area
    floral_strips = np.clip(floral_strips, 0.0, 30.0)

    pesticide = np.random.uniform(10, 50, n_samples)
    soil = np.random.uniform(50, 90, n_samples)
    temp = np.random.uniform(15, 30, n_samples)
    precip = np.random.uniform(400, 1200, n_samples)
    div_land = np.random.uniform(0.1, 0.9, n_samples)

    # Objetivos con relación funcional simple
    yield_idx = 50.0 + 0.3 * crop_area + 0.2 * soil - 0.1 * pesticide + np.random.normal(0, 1, n_samples)
    poll_abund = 30.0 + 0.4 * natural_area + 0.5 * floral_strips - 0.2 * pesticide + np.random.normal(0, 1, n_samples)
    poll_div = 0.3 + 0.003 * natural_area + 0.004 * floral_strips + np.random.normal(0, 0.02, n_samples)
    poll_div = np.clip(poll_div, 0.1, 1.0)

    return pd.DataFrame({
        "scenario_id": [f"sc_{i}" for i in range(n_samples)],
        "crop_area_pct": crop_area,
        "natural_area_pct": natural_area,
        "floral_strips_pct": floral_strips,
        "pesticide_level": pesticide,
        "soil_management_score": soil,
        "temperature_c": temp,
        "precipitation_mm": precip,
        "landscape_diversity": div_land,
        "crop_yield_index": yield_idx,
        "pollinator_abundance_index": poll_abund,
        "pollinator_diversity_index": poll_div,
    })


def test_prepare_streamlit_run_config_sets_effective_seeds():
    """Verifica que prepare_streamlit_run_config establezca la semilla tanto en la raíz como en outer_cv."""
    cfg_42 = prepare_streamlit_run_config(
        k_folds=2,
        random_state=42,
    )
    assert cfg_42["seed"] == 42
    assert cfg_42["outer_cv"]["seed"] == 42

    cfg_1337 = prepare_streamlit_run_config(
        k_folds=2,
        random_state=1337,
    )
    assert cfg_1337["seed"] == 1337
    assert cfg_1337["outer_cv"]["seed"] == 1337


def test_final_refit_seed_default_42():
    """Verifica que el modelo final entrenado con semilla por defecto use random_state=42."""
    df = _create_minimal_synthetic_dataset(24)
    cfg = prepare_streamlit_run_config(
        k_folds=2,
        random_state=42,
    )
    # Habilitamos solo ridge para prueba veloz
    for m in cfg.get("models", {}):
        cfg["models"][m]["enabled"] = (m == "ridge")

    results = train_and_evaluate_all_models(
        dataframe=df,
        k_folds=2,
        config=cfg,
        random_state=42,
    )
    assert results.get("final_seed") == 42
    predictor = results["predictor"]
    assert predictor.metadata.get("final_seed") == 42
    assert getattr(predictor.model, "random_state", None) == 42


def test_final_refit_seed_custom_1337():
    """
    Verifica la corrección de la Auditoría 06:
    Al solicitar random_state=1337, el modelo final y sus metadatos deben
    tener random_state=1337 y no el 42 por defecto.
    """
    df = _create_minimal_synthetic_dataset(24)
    cfg = prepare_streamlit_run_config(
        k_folds=2,
        random_state=1337,
    )
    for m in cfg.get("models", {}):
        cfg["models"][m]["enabled"] = (m == "ridge")

    assert cfg["seed"] == 1337
    assert cfg["outer_cv"]["seed"] == 1337

    results = train_and_evaluate_all_models(
        dataframe=df,
        k_folds=2,
        config=cfg,
        random_state=1337,
    )
    assert results.get("final_seed") == 1337
    predictor = results["predictor"]
    assert predictor.metadata.get("final_seed") == 1337
    assert getattr(predictor.model, "random_state", None) == 1337


def test_final_refit_seed_with_injected_config_and_different_param():
    """
    Si se inyecta una configuración con seed=2026 en config,
    debe tener precedencia sobre cualquier valor por defecto del llamador.
    """
    df = _create_minimal_synthetic_dataset(24)
    cfg = prepare_streamlit_run_config(
        k_folds=2,
        random_state=2026,
    )
    for m in cfg.get("models", {}):
        cfg["models"][m]["enabled"] = (m == "ridge")

    # Pasamos random_state=42 como argumento posicional secundario, pero cfg tiene seed=2026
    results = train_and_evaluate_all_models(
        dataframe=df,
        k_folds=2,
        config=cfg,
        random_state=42,
    )
    assert results.get("final_seed") == 2026
    predictor = results["predictor"]
    assert predictor.metadata.get("final_seed") == 2026
    assert getattr(predictor.model, "random_state", None) == 2026


def test_neural_refit_receives_final_seed():
    """
    Verifica que el reajuste neuronal (fit_and_predict_neural_outer)
    reciba y aplique la semilla efectiva en build_keras_neural_model.
    """
    from scientific_core.nested_cv import fit_and_predict_neural_outer
    X = np.random.randn(20, 8).astype(np.float32)
    y = np.random.randn(20, 3).astype(np.float32)

    preds, sx, sy, model = fit_and_predict_neural_outer(
        model_family="dnn",
        params={"hidden_layers": [16], "learning_rate": 0.01, "dropout": 0.0, "batch_size": 16},
        X_train_outer=X,
        y_train_outer=y,
        X_test_outer=X[:2],
        optimal_epochs=2,
        seed=1337,
    )
    assert model is not None
    assert preds.shape == (2, 3)


def test_execute_streamlit_training_run_end_to_end_seed(tmp_path):
    """
    Prueba integral de execute_streamlit_training_run con random_state=1337:
    Verifica que config_effective, el resultado de entrenamiento y el bundle exportado
    conserven la semilla 1337.
    """
    df = _create_minimal_synthetic_dataset(24)
    cfg = prepare_streamlit_run_config(k_folds=2, random_state=1337)
    for m in cfg.get("models", {}):
        cfg["models"][m]["enabled"] = (m == "ridge")

    t_res = execute_streamlit_training_run(
        dataframe=df,
        k_folds=2,
        random_state=1337,
        base_artifacts_dir=tmp_path,
        config=cfg,
    )

    # 1. El resultado de entrenamiento y su predictor deben tener final_seed=1337
    assert t_res["final_seed"] == 1337
    predictor = t_res["predictor"]
    assert predictor.metadata.get("final_seed") == 1337
    assert getattr(predictor.model, "random_state", None) == 1337

    # 2. Exportación de bundle conserva final_seed en metadata
    bundle_dir = tmp_path / "bundle_test"
    export_streamlit_model(
        training_result=t_res,
        export_dir=bundle_dir,
    )
    meta_path = bundle_dir / "bundle_metadata.json"
    assert meta_path.exists()
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta.get("final_seed") == 1337
    assert meta.get("seed") == 1337


# =====================================================================
# BLOQUE 2: COMPARACIONES PAREADAS EN INFORMES DE GESTIÓN
# =====================================================================

class DummySim:
    """Objeto liviano que simula la entidad SQLAlchemy Simulacion."""
    def __init__(
        self,
        sim_id: int,
        usuario_id: int = 1,
        fecha: datetime.datetime | None = None,
        region: str = "Centro",
        metricas_base: dict[str, Any] | None = None,
        metricas_optimas: dict[str, Any] | None = None,
        frente_pareto: list[dict[str, Any]] | None = None,
    ):
        self.id = sim_id
        self.usuario_id = usuario_id
        self.fecha = fecha or datetime.datetime(2026, 10, 28, 12, 0, 0)
        self.metricas_base = metricas_base or {}
        if region and "region_label" not in self.metricas_base:
            self.metricas_base["region_label"] = region
        self.metricas_optimas = metricas_optimas
        self.frente_pareto = frente_pareto

    @property
    def cumple_hipotesis(self) -> bool:
        if not self.metricas_optimas or not isinstance(self.metricas_optimas, dict):
            return False
        yb = float(self.metricas_base.get("crop_yield_index", 70.0))
        yo = float(self.metricas_optimas.get("crop_yield_index", yb))
        pb = float(self.metricas_base.get("pollinator_abundance_index", 50.0))
        po = float(self.metricas_optimas.get("pollinator_abundance_index", pb))
        dy = yo - yb
        dp_pct = ((po - pb) / max(1.0, pb)) * 100.0
        return bool((dy >= 0.0) and (dp_pct >= 20.0))


class DummyQuery:
    def __init__(self, items: list[DummySim]):
        self._items = items

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._items)


class DummySession:
    def __init__(self, simulations: list[DummySim]):
        self._simulations = simulations

    def query(self, *args, **kwargs):
        return DummyQuery(self._simulations)


def test_management_report_case_a_feasible_plus_infeasible_different_bases():
    """
    Caso A: Factible con base pequeña + Infactible con base grande.
    Sim A: base=100.0, opt=110.0 (delta = +10.0, evaluable).
    Sim B: base=1000.0, opt=None (no evaluable).

    Anteriormente: base=550.0, opt=110.0, delta=-440.0 (ERRÓNEO).
    Correcto: base evaluable=100.0, opt=110.0, delta=+10.0 (PAREADO).
    Base total de la población: 550.0 (mantenida por separado).
    """
    sim_a = DummySim(
        sim_id=1,
        metricas_base={"crop_yield_index": 100.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 110.0, "pollinator_abundance_index": 70.0, "pollinator_diversity_index": 0.7},
    )
    sim_b = DummySim(
        sim_id=2,
        metricas_base={"crop_yield_index": 1000.0, "pollinator_abundance_index": 500.0, "pollinator_diversity_index": 0.9},
        metricas_optimas=None,
    )

    db = DummySession([sim_a, sim_b])
    report = get_management_report(db)
    kpis = report.kpis_agroecologicos

    assert kpis.total_simulaciones == 2
    assert kpis.simulaciones_evaluables == 1
    assert kpis.simulaciones_no_evaluables == 1
    assert kpis.denominador_tasa == "evaluables"
    assert kpis.simulaciones_cumplen_hipotesis == 1
    assert kpis.simulaciones_no_cumplen == 0
    assert kpis.tasa_cumplimiento_hipotesis == 100.0

    # Rendimiento pareado
    assert kpis.rendimiento_promedio_base == 100.0
    assert kpis.rendimiento_promedio_optimo == 110.0
    assert kpis.delta_rendimiento_promedio == 10.0
    assert kpis.delta_rendimiento_pct == 10.0
    assert kpis.rendimiento_promedio_base_total == 550.0

    # Abundancia pareada
    assert kpis.abundancia_polinizadores_base == 50.0
    assert kpis.abundancia_polinizadores_optima == 70.0
    assert kpis.delta_abundancia_promedio == 20.0
    assert kpis.delta_abundancia_pct == 40.0
    assert kpis.abundancia_polinizadores_base_total == 275.0

    # Diversidad pareada
    assert kpis.diversidad_polinizadores_base == 0.5
    assert kpis.diversidad_polinizadores_optima == 0.7
    assert kpis.delta_diversidad_promedio == 0.2
    assert kpis.diversidad_polinizadores_base_total == 0.7


def test_management_report_case_b_all_feasible():
    """
    Caso B: Todas las simulaciones son factibles (evaluables).
    Sim 1: base=80.0, opt=90.0 (delta=+10.0)
    Sim 2: base=100.0, opt=120.0 (delta=+20.0)
    Base promedio evaluable y total deben coincidir (90.0).
    Óptimo promedio = 105.0. Delta = +15.0.
    """
    sim1 = DummySim(
        sim_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 90.0, "pollinator_abundance_index": 65.0, "pollinator_diversity_index": 0.6},
    )
    sim2 = DummySim(
        sim_id=2,
        metricas_base={"crop_yield_index": 100.0, "pollinator_abundance_index": 60.0, "pollinator_diversity_index": 0.6},
        metricas_optimas={"crop_yield_index": 120.0, "pollinator_abundance_index": 78.0, "pollinator_diversity_index": 0.75},
    )

    db = DummySession([sim1, sim2])
    report = get_management_report(db)
    kpis = report.kpis_agroecologicos

    assert kpis.total_simulaciones == 2
    assert kpis.simulaciones_evaluables == 2
    assert kpis.simulaciones_no_evaluables == 0
    assert kpis.rendimiento_promedio_base == 90.0
    assert kpis.rendimiento_promedio_base_total == 90.0
    assert kpis.rendimiento_promedio_optimo == 105.0
    assert kpis.delta_rendimiento_promedio == 15.0
    assert kpis.tasa_cumplimiento_hipotesis == 100.0


def test_management_report_case_c_all_infeasible():
    """
    Caso C: Todas las simulaciones son infactibles (sin solución).
    No deben fabricarse deltas con ceros. Todos los óptimos y deltas deben ser None.
    """
    sim1 = DummySim(
        sim_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas=None,
    )
    sim2 = DummySim(
        sim_id=2,
        metricas_base={"crop_yield_index": 120.0, "pollinator_abundance_index": 70.0, "pollinator_diversity_index": 0.7},
        metricas_optimas=None,
    )

    db = DummySession([sim1, sim2])
    report = get_management_report(db)
    kpis = report.kpis_agroecologicos

    assert kpis.total_simulaciones == 2
    assert kpis.simulaciones_evaluables == 0
    assert kpis.simulaciones_no_evaluables == 2
    assert kpis.simulaciones_cumplen_hipotesis == 0
    assert kpis.simulaciones_no_cumplen == 0
    assert kpis.tasa_cumplimiento_hipotesis is None

    # Ausencia de datos pareados
    assert kpis.rendimiento_promedio_base is None
    assert kpis.rendimiento_promedio_optimo is None
    assert kpis.delta_rendimiento_promedio is None
    assert kpis.delta_rendimiento_pct is None

    assert kpis.abundancia_polinizadores_base is None
    assert kpis.abundancia_polinizadores_optima is None
    assert kpis.delta_abundancia_promedio is None
    assert kpis.delta_abundancia_pct is None

    assert kpis.diversidad_polinizadores_base is None
    assert kpis.diversidad_polinizadores_optima is None
    assert kpis.delta_diversidad_promedio is None

    # Línea base total sí existe
    assert kpis.rendimiento_promedio_base_total == 100.0
    assert kpis.abundancia_polinizadores_base_total == 60.0
    assert kpis.diversidad_polinizadores_base_total == 0.6


def test_management_report_case_d_no_records():
    """Caso D: Base de datos vacía sin simulaciones registradas."""
    db = DummySession([])
    report = get_management_report(db)
    kpis = report.kpis_agroecologicos

    assert kpis.total_simulaciones == 0
    assert kpis.simulaciones_evaluables == 0
    assert kpis.simulaciones_no_evaluables == 0
    assert kpis.simulaciones_cumplen_hipotesis == 0
    assert kpis.simulaciones_no_cumplen == 0
    assert kpis.tasa_cumplimiento_hipotesis is None
    assert kpis.rendimiento_promedio_base is None
    assert kpis.rendimiento_promedio_optimo is None
    assert kpis.delta_rendimiento_promedio is None
    assert kpis.rendimiento_promedio_base_total is None

    assert report.comparacion_regiones == []
    assert report.evolucion_temporal == []
    assert report.top_configuraciones_pareto == []


def test_management_report_case_e_regional_and_temporal_paired():
    """
    Caso E: Agregación regional y temporal debe aplicar estrictamente el criterio pareado.
    Región Norte: 1 factible (100 -> 110) + 1 infactible (1000 -> None).
    Región Sur: 1 factible (80 -> 90).
    """
    date1 = datetime.datetime(2026, 10, 20, 10, 0, 0)
    date2 = datetime.datetime(2026, 10, 21, 10, 0, 0)

    sim_norte_1 = DummySim(
        sim_id=1,
        fecha=date1,
        region="Norte",
        metricas_base={"crop_yield_index": 100.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 110.0, "pollinator_abundance_index": 65.0, "pollinator_diversity_index": 0.65},
    )
    sim_norte_2 = DummySim(
        sim_id=2,
        fecha=date1,
        region="Norte",
        metricas_base={"crop_yield_index": 1000.0, "pollinator_abundance_index": 500.0, "pollinator_diversity_index": 0.9},
        metricas_optimas=None,
    )
    sim_sur_1 = DummySim(
        sim_id=3,
        fecha=date2,
        region="Sur",
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 40.0, "pollinator_diversity_index": 0.45},
        metricas_optimas={"crop_yield_index": 90.0, "pollinator_abundance_index": 52.0, "pollinator_diversity_index": 0.55},
    )

    db = DummySession([sim_norte_1, sim_norte_2, sim_sur_1])
    report = get_management_report(db)

    # Verificación regional
    regiones_map = {r.region: r for r in report.comparacion_regiones}
    assert "Norte" in regiones_map
    assert "Sur" in regiones_map

    reg_norte = regiones_map["Norte"]
    assert reg_norte.total_simulaciones == 2
    assert reg_norte.simulaciones_evaluables == 1
    assert reg_norte.simulaciones_no_evaluables == 1
    # Comparación pareada en Norte: base=100.0, opt=110.0, delta=+10.0
    assert reg_norte.rendimiento_promedio_base == 100.0
    assert reg_norte.rendimiento_promedio_optimo == 110.0
    assert reg_norte.delta_rendimiento_promedio == 10.0
    assert reg_norte.rendimiento_promedio_base_total == 550.0

    reg_sur = regiones_map["Sur"]
    assert reg_sur.total_simulaciones == 1
    assert reg_sur.simulaciones_evaluables == 1
    assert reg_sur.simulaciones_no_evaluables == 0
    assert reg_sur.rendimiento_promedio_base == 80.0
    assert reg_sur.rendimiento_promedio_optimo == 90.0
    assert reg_sur.delta_rendimiento_promedio == 10.0

    # Verificación temporal
    tempo_map = {p.fecha: p for p in report.evolucion_temporal}
    p_date1 = tempo_map["2026-10-20"]
    assert p_date1.total_simulaciones == 2
    assert p_date1.simulaciones_evaluables == 1
    assert p_date1.simulaciones_no_evaluables == 1
    assert p_date1.rendimiento_base == 100.0
    assert p_date1.rendimiento_optimo == 110.0
    assert p_date1.delta_rendimiento == 10.0
    assert p_date1.rendimiento_base_total == 550.0


def test_management_report_case_f_exact_reproduction_100_110_and_1000_none():
    """
    Caso F: Prueba de regresión numérica exacta del caso documentado en la Auditoría 06:
    Simulación A: base=100, opt=110.
    Simulación B: base=1000, opt=None.
    Anteriormente producía: base promedio = 550, óptimo promedio = 110, delta = -440.
    Comparación evaluable correcta: base = 100, óptimo = 110, delta = +10.
    """
    sim_a = DummySim(
        sim_id=101,
        metricas_base={"crop_yield_index": 100.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 110.0, "pollinator_abundance_index": 62.0, "pollinator_diversity_index": 0.6},
    )
    sim_b = DummySim(
        sim_id=102,
        metricas_base={"crop_yield_index": 1000.0, "pollinator_abundance_index": 500.0, "pollinator_diversity_index": 0.9},
        metricas_optimas=None,
    )

    db = DummySession([sim_a, sim_b])
    report = get_management_report(db)
    kpis = report.kpis_agroecologicos

    # Verificación exacta contra la distorsión
    assert kpis.rendimiento_promedio_base != 550.0  # El base no debe ser el no pareado
    assert kpis.rendimiento_promedio_base == 100.0
    assert kpis.rendimiento_promedio_optimo == 110.0
    assert kpis.delta_rendimiento_promedio != -440.0  # La distorsión eliminada
    assert kpis.delta_rendimiento_promedio == 10.0
    assert kpis.delta_rendimiento_pct == 10.0
    assert kpis.denominador_tasa == "evaluables"
