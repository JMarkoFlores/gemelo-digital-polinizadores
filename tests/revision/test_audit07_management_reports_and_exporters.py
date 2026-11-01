"""
Suite de pruebas de regresión para la Auditoría 07:
Coherencia de los informes de gestión y sus consumidores.

Casos verificados:
A. Una simulación que cumple y otra no evaluable:
   total=2, evaluables=1, no evaluables=1, cumplen=1, no cumplen=0.
B. Todas no evaluables:
   cumplen=0, no cumplen=0, tasa ausente y métricas óptimas ausentes (None).
C. Todas evaluables:
   cumple + no cumple = evaluables.
D. Sin registros (base de datos vacía):
   total=0, evaluables=0, no evaluables=0, cumplen=0, no cumplen=0, tasa ausente.
E. Diferencia entre una métrica ausente (None) y una métrica real igual a cero (0.0).
F. Conservación de la comparación pareada estricta:
   100->110 junto con 1000->sin solución conserva mejora +10.0.
G. Coherencia en agregaciones regionales y temporales:
   total = evaluables + no evaluables, evaluables = cumplen + no cumplen.
"""

from __future__ import annotations

import datetime
import sys
import types
from typing import Any
from unittest.mock import MagicMock
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


class DummySim:
    """Simulación liviana de la entidad SQLAlchemy Simulacion."""
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


def test_case_a_one_meets_and_one_infeasible():
    """
    Caso A (Auditoría 07):
    Una simulación que cumple y otra no evaluable.
    Ecuaciones requeridas:
    - total = 2 (evaluables + no evaluables)
    - evaluables = 1
    - no evaluables = 1
    - cumplen = 1
    - no cumplen = 0 (evaluables - cumplen = 1 - 1 = 0, no 1)
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
    assert kpis.simulaciones_cumplen_hipotesis == 1
    assert kpis.simulaciones_no_cumplen == 0  # Requerimiento estricto: no cumplen = 0, no 1
    assert kpis.total_simulaciones == kpis.simulaciones_evaluables + kpis.simulaciones_no_evaluables
    assert kpis.simulaciones_evaluables == kpis.simulaciones_cumplen_hipotesis + kpis.simulaciones_no_cumplen
    assert kpis.denominador_tasa == "evaluables"
    assert kpis.tasa_cumplimiento_hipotesis == 100.0


def test_case_b_all_infeasible():
    """
    Caso B (Auditoría 07):
    Todas no evaluables (sin solución).
    - cumplen = 0
    - no cumplen = 0
    - tasa ausente (None, no se fabrica 0%)
    - métricas óptimas y deltas ausentes (None)
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
    assert kpis.simulaciones_no_cumplen == 0  # Evaluables (0) - cumplen (0) = 0
    assert kpis.tasa_cumplimiento_hipotesis is None  # Ausencia de dato, no 0%

    assert kpis.rendimiento_promedio_base is None
    assert kpis.rendimiento_promedio_optimo is None
    assert kpis.delta_rendimiento_promedio is None
    assert kpis.delta_rendimiento_pct is None
    assert kpis.abundancia_polinizadores_base is None
    assert kpis.abundancia_polinizadores_optima is None
    assert kpis.delta_abundancia_promedio is None
    assert kpis.diversidad_polinizadores_base is None
    assert kpis.diversidad_polinizadores_optima is None
    assert kpis.delta_diversidad_promedio is None


def test_case_c_all_evaluable():
    """
    Caso C (Auditoría 07):
    Todas evaluables (1 cumple, 1 no cumple).
    - cumple + no cumple = evaluables
    - evaluables = total (no evaluables = 0)
    """
    sim1 = DummySim(
        sim_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 90.0, "pollinator_abundance_index": 65.0, "pollinator_diversity_index": 0.6},
    )
    sim2 = DummySim(
        sim_id=2,
        metricas_base={"crop_yield_index": 100.0, "pollinator_abundance_index": 60.0, "pollinator_diversity_index": 0.6},
        metricas_optimas={"crop_yield_index": 95.0, "pollinator_abundance_index": 62.0, "pollinator_diversity_index": 0.65},  # dy = -5 -> no cumple
    )

    db = DummySession([sim1, sim2])
    report = get_management_report(db)
    kpis = report.kpis_agroecologicos

    assert kpis.total_simulaciones == 2
    assert kpis.simulaciones_evaluables == 2
    assert kpis.simulaciones_no_evaluables == 0
    assert kpis.simulaciones_cumplen_hipotesis == 1
    assert kpis.simulaciones_no_cumplen == 1
    assert kpis.simulaciones_cumplen_hipotesis + kpis.simulaciones_no_cumplen == kpis.simulaciones_evaluables
    assert kpis.tasa_cumplimiento_hipotesis == 50.0


def test_case_d_no_records():
    """
    Caso D (Auditoría 07):
    Sin registros (base de datos vacía).
    - total = 0, evaluables = 0, no evaluables = 0, cumplen = 0, no cumplen = 0.
    - tasa ausente (None).
    """
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

    assert report.comparacion_regiones == []
    assert report.evolucion_temporal == []
    assert report.top_configuraciones_pareto == []


def test_case_e_distinction_between_absent_and_real_zero():
    """
    Caso E (Auditoría 07):
    Diferencia entre una métrica ausente (None) y una métrica real igual a cero (0.0).
    - Simulación con delta exacto 0.0 (rendimiento 100->100):
      delta_rendimiento_promedio == 0.0 (número real 0.0, no ausente).
    - Simulación infactible (None):
      delta_rendimiento_promedio is None (ausencia de dato).
    """
    # 1. Simulación con variación real de 0.0 (óptimo == base)
    sim_zero_delta = DummySim(
        sim_id=1,
        metricas_base={"crop_yield_index": 100.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 100.0, "pollinator_abundance_index": 60.0, "pollinator_diversity_index": 0.5},
    )
    db_zero = DummySession([sim_zero_delta])
    kpis_zero = get_management_report(db_zero).kpis_agroecologicos

    assert kpis_zero.delta_rendimiento_promedio == 0.0
    assert kpis_zero.delta_rendimiento_promedio is not None
    assert kpis_zero.delta_rendimiento_pct == 0.0

    # 2. Simulación infactible sin solución
    sim_infeasible = DummySim(
        sim_id=2,
        metricas_base={"crop_yield_index": 100.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas=None,
    )
    db_infeasible = DummySession([sim_infeasible])
    kpis_infeasible = get_management_report(db_infeasible).kpis_agroecologicos

    assert kpis_infeasible.delta_rendimiento_promedio is None
    assert kpis_infeasible.delta_rendimiento_pct is None
    assert kpis_infeasible.rendimiento_promedio_optimo is None


def test_case_f_preservation_of_paired_comparison():
    """
    Caso F (Auditoría 07):
    Conservación de la comparación pareada de la Auditoría 06:
    100->110 junto con 1000->None conserva mejora +10.0 (no distorsionada a -440).
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
    kpis = get_management_report(db).kpis_agroecologicos

    assert kpis.rendimiento_promedio_base == 100.0
    assert kpis.rendimiento_promedio_optimo == 110.0
    assert kpis.delta_rendimiento_promedio == 10.0
    assert kpis.delta_rendimiento_pct == 10.0
    assert kpis.rendimiento_promedio_base_total == 550.0


def test_case_g_regional_and_temporal_category_coherence():
    """
    Caso G (Auditoría 07):
    Comprobación de categorías coherentes en regiones y evolución temporal.
    Region A: 1 cumple + 1 no cumple + 1 no evaluable (total=3, eval=2, no_eval=1, cumplen=1, no_cumplen=1)
    """
    date1 = datetime.datetime(2026, 10, 28, 10, 0, 0)
    s1 = DummySim(
        sim_id=1, fecha=date1, region="Valle",
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 90.0, "pollinator_abundance_index": 65.0, "pollinator_diversity_index": 0.6}, # cumple
    )
    s2 = DummySim(
        sim_id=2, fecha=date1, region="Valle",
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 70.0, "pollinator_abundance_index": 55.0, "pollinator_diversity_index": 0.6}, # no cumple
    )
    s3 = DummySim(
        sim_id=3, fecha=date1, region="Valle",
        metricas_base={"crop_yield_index": 100.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas=None, # no evaluable
    )

    db = DummySession([s1, s2, s3])
    report = get_management_report(db)

    # Regional
    reg = report.comparacion_regiones[0]
    assert reg.total_simulaciones == 3
    assert reg.simulaciones_evaluables == 2
    assert reg.simulaciones_no_evaluables == 1
    assert reg.simulaciones_cumplen_hipotesis == 1
    assert reg.simulaciones_no_cumplen == 1
    assert reg.total_simulaciones == reg.simulaciones_evaluables + reg.simulaciones_no_evaluables
    assert reg.simulaciones_evaluables == reg.simulaciones_cumplen_hipotesis + reg.simulaciones_no_cumplen
    assert reg.tasa_cumplimiento_hipotesis == 50.0

    # Temporal
    tempo = report.evolucion_temporal[0]
    assert tempo.total_simulaciones == 3
    assert tempo.simulaciones_evaluables == 2
    assert tempo.simulaciones_no_evaluables == 1
    assert tempo.simulaciones_cumplen_hipotesis == 1
    assert tempo.simulaciones_no_cumplen == 1
    assert tempo.total_simulaciones == tempo.simulaciones_evaluables + tempo.simulaciones_no_evaluables
    assert tempo.simulaciones_evaluables == tempo.simulaciones_cumplen_hipotesis + tempo.simulaciones_no_cumplen
