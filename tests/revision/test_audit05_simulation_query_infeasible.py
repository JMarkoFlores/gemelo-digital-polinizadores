"""
tests/revision/test_audit05_simulation_query_infeasible.py
Pruebas de regresión para el Hallazgo 2 de la Auditoría 05:
Consulta e integridad de simulaciones sin solución óptima (infactibles o no convergentes).

Verifica:
1. Consulta de simulación con solución óptima: retorna métricas óptimas completas y mejoras evaluables.
2. Consulta de simulación sin solución óptima (metricas_optimas=None):
   - No lanza AttributeError ('NoneType' object has no attribute 'get').
   - Representa explícitamente tiene_solucion_optima=False y metricas_optimas=None.
   - No fabrica métricas óptimas copiando la línea base.
   - Retorna mejoras como estado="no_evaluable" con deltas en None.
3. Consulta de simulación inexistente: status="error", encontrada=False.
4. Control de autorización estricto: status="forbidden" para usuarios no administradores ajenos.
5. Consumidor en Chat (generate_local_fallback_reply): respuesta informativa sin claims indebidos.
6. Consumidor en Historial (query_user_simulations_summary): valores óptimos nulos para infactibles.
7. Consumidor en Reportes de Gestión (get_management_report):
   - No clasifica erróneamente simulaciones sin solución como cumplidoras de hipótesis.
   - No introduce números espurios en promedios de optimización.
"""
from __future__ import annotations

from datetime import datetime
import sys
import types
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

if "groq" not in sys.modules:
    groq_mod = types.ModuleType("groq")
    groq_mod.Groq = MagicMock()
    sys.modules["groq"] = groq_mod

if "sqlalchemy" not in sys.modules:
    sa_mod = types.ModuleType("sqlalchemy")
    sa_mod.func = MagicMock()
    sys.modules["sqlalchemy"] = sa_mod
    sao_mod = types.ModuleType("sqlalchemy.orm")
    sao_mod.Session = MagicMock()
    sys.modules["sqlalchemy.orm"] = sao_mod

if "app.config" not in sys.modules:
    app_cfg = types.ModuleType("app.config")
    mock_settings = MagicMock()
    mock_settings.cache_ttl_seconds = 900
    mock_settings.cache_max_items = 64
    mock_settings.model_dir = "/modelos_ia"
    mock_settings.groq_api_key = ""
    mock_settings.groq_model = "llama-3.1-70b-versatile"
    app_cfg.get_settings = MagicMock(return_value=mock_settings)
    sys.modules["app.config"] = app_cfg

if "app.models" not in sys.modules:
    app_mods = types.ModuleType("app.models")
    app_mods.Simulacion = MagicMock()
    app_mods.Usuario = MagicMock()
    sys.modules["app.models"] = app_mods

from backend.app.services.chat_service import (
    query_simulation_details,
    generate_local_fallback_reply,
    query_simulations_summary,
)
from backend.app.services.report_general_service import get_management_report


class DummyUser:
    def __init__(self, user_id: int, email: str, rol: str = "cliente"):
        self.id = user_id
        self.email = email
        self.rol = rol


class DummySimulation:
    def __init__(
        self,
        sim_id: int,
        usuario_id: int,
        metricas_base: dict | None,
        metricas_optimas: dict | None = None,
        frente_pareto: list | None = None,
        variables_entrada: dict | None = None,
        fecha: datetime | None = None,
    ):
        self.id = sim_id
        self.usuario_id = usuario_id
        self.metricas_base = metricas_base or {}
        self.metricas_optimas = metricas_optimas
        self.frente_pareto = frente_pareto or []
        self.variables_entrada = variables_entrada or {"pesticide_level": 20.0, "min_natural_area_pct": 20.0}
        self.fecha = fecha or datetime(2026, 10, 28, 12, 0, 0)


class MockQuery:
    def __init__(self, items: list[DummySimulation]):
        self._items = items

    def filter(self, *args, **kwargs):
        # Para simulación por ID
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)

    def order_by(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._items)


class MockSession:
    def __init__(self, simulation_store: dict[int, DummySimulation] | None = None, all_sims: list[DummySimulation] | None = None):
        self._store = simulation_store or {}
        self._all_sims = all_sims or list(self._store.values())

    def query(self, model):
        class _FilterQuery:
            def __init__(self, parent):
                self.parent = parent

            def filter(self, expr):
                class _FirstQuery:
                    def __init__(self, store, parent_all):
                        self.store = store
                        self.parent_all = parent_all

                    def first(self):
                        for sim in self.store.values():
                            return sim
                        return None

                    def all(self):
                        return self.parent_all

                    def order_by(self, *args, **kwargs):
                        return self

                    def scalar(self):
                        return len(self.parent_all)

                    def count(self):
                        return len(self.parent_all)

                return _FirstQuery(self.parent._store, self.parent._all_sims)

            def order_by(self, *args, **kwargs):
                return self

            def all(self):
                return self.parent._all_sims

            def count(self):
                return len(self.parent._all_sims)

            def scalar(self):
                return len(self.parent._all_sims)

        return _FilterQuery(self)


def test_query_simulation_details_with_solution():
    """Caso 1: Registro con solución óptima."""
    sim = DummySimulation(
        sim_id=101,
        usuario_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={
            "crop_yield_index": 85.0,
            "pollinator_abundance_index": 70.0,
            "pollinator_diversity_index": 0.65,
            "crop_area_pct": 55.0,
            "natural_area_pct": 25.0,
            "floral_strips_pct": 5.0,
            "pesticide_level": 15.0,
            "soil_management_score": 80.0,
        },
        frente_pareto=[{"crop_yield_index": 85.0, "pollinator_abundance_index": 70.0}],
    )
    db = MockSession(simulation_store={101: sim})
    user = DummyUser(user_id=1, email="user1@example.com", rol="cliente")

    res = query_simulation_details(db, user, 101)

    assert res["status"] == "success"
    assert res["encontrada"] is True
    assert res["tiene_solucion_optima"] is True
    assert res["metricas_optimas"] is not None
    assert res["metricas_optimas"]["rendimiento"] == 85.0
    assert res["metricas_optimas"]["abundancia_polinizadores"] == 70.0
    assert res["mejoras"]["estado"] == "evaluable"
    assert res["mejoras"]["delta_rendimiento"] == 5.0
    assert res["mejoras"]["delta_polinizadores_porcentaje"] == "+40.0%"
    assert res["total_soluciones_pareto"] == 1


def test_query_simulation_details_without_solution():
    """
    Caso 2: Registro sin solución óptima (metricas_optimas=None).
    Verifica que no ocurra AttributeError y no se fabriquen métricas falsas.
    """
    sim = DummySimulation(
        sim_id=102,
        usuario_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas=None,
        frente_pareto=[],
    )
    db = MockSession(simulation_store={102: sim})
    user = DummyUser(user_id=1, email="user1@example.com", rol="cliente")

    # Esta llamada previamente lanzaba AttributeError: 'NoneType' object has no attribute 'get'
    res = query_simulation_details(db, user, 102)

    assert res["status"] == "success"
    assert res["encontrada"] is True
    assert res["tiene_solucion_optima"] is False
    assert res["metricas_optimas"] is None
    assert res["mejoras"]["delta_rendimiento"] is None
    assert res["mejoras"]["delta_polinizadores_porcentaje"] is None
    assert res["mejoras"]["estado"] == "no_evaluable"
    assert "no produjo una solución óptima admisible" in res["mensaje"]
    assert res["total_soluciones_pareto"] == 0


def test_query_simulation_details_not_found():
    """Caso 3: Registro inexistente en la BD."""
    db = MockSession(simulation_store={})
    user = DummyUser(user_id=1, email="user1@example.com", rol="cliente")

    res = query_simulation_details(db, user, 999)

    assert res["status"] == "error"
    assert res["encontrada"] is False
    assert "No se encontró la simulación #999" in res["mensaje"]


def test_query_simulation_details_unauthorized_access():
    """Caso 4: Acceso no autorizado (usuario no admin intentando ver simulación ajena)."""
    sim = DummySimulation(
        sim_id=201,
        usuario_id=2,  # Pertenece al usuario 2
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0},
        metricas_optimas=None,
    )
    db = MockSession(simulation_store={201: sim})

    # Cliente 1 (ajeno)
    client_user = DummyUser(user_id=1, email="client1@example.com", rol="cliente")
    res_forbidden = query_simulation_details(db, client_user, 201)
    assert res_forbidden["status"] == "forbidden"
    assert res_forbidden["acceso_denegado"] is True

    # Usuario Administrador (autorizado globalmente)
    admin_user = DummyUser(user_id=99, email="admin@example.com", rol="admin")
    res_admin = query_simulation_details(db, admin_user, 201)
    assert res_admin["status"] == "success"
    assert res_admin.get("acceso_denegado") is not True


def test_chat_fallback_generation_without_solution():
    """
    Caso 5: Generación de respuesta de respaldo en Chat sin solución óptima.
    Verifica que explique claramente la infactibilidad sin inventar valores.
    """
    sim_data = {
        "status": "success",
        "encontrada": True,
        "tiene_solucion_optima": False,
        "simulacion_id": 102,
        "fecha": "2026-10-28 12:00:00",
        "region": "Parcela Norte",
        "variables_entrada": {"nivel_pesticidas": 30.0, "area_natural_minima_pct": 10.0},
        "metricas_base": {"rendimiento": 75.0, "abundancia_polinizadores": 40.0},
        "metricas_optimas": None,
        "mejoras": {"delta_rendimiento": None, "delta_polinizadores_porcentaje": None, "estado": "no_evaluable"},
        "total_soluciones_pareto": 0,
    }
    user = DummyUser(user_id=1, email="user1@example.com", rol="cliente")
    db = MockSession()
    structured = {"simulation_query": sim_data}

    reply = generate_local_fallback_reply("¿Cómo me fue en la simulación 102?", user, db, structured)

    assert "simulación infactible" in reply.lower() or "no se encontró una solución viable" in reply.lower()
    assert "no hay métricas óptimas ni mejoras evaluables" in reply.lower()
    assert "0 configuraciones admisibles" in reply.lower()


def test_user_simulations_summary_with_missing_solution():
    """
    Caso 6: Historial de usuario con mezclas de simulaciones exitosas e infactibles.
    """
    sim_ok = DummySimulation(
        sim_id=1,
        usuario_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0},
        metricas_optimas={"crop_yield_index": 85.0, "pollinator_abundance_index": 65.0},
    )
    sim_infeasible = DummySimulation(
        sim_id=2,
        usuario_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0},
        metricas_optimas=None,
    )

    db = MockSession(all_sims=[sim_ok, sim_infeasible])
    user = DummyUser(user_id=1, email="user1@example.com", rol="cliente")

    summary = query_simulations_summary(db, user)
    recents = summary["ultimas_simulaciones"]

    assert len(recents) == 2
    # La simulación 1 tiene solución
    assert recents[0]["id"] == 1
    assert recents[0]["tiene_solucion_optima"] is True
    assert recents[0]["rendimiento_optimo"] == 85.0

    # La simulación 2 no tiene solución y sus óptimos son None
    assert recents[1]["id"] == 2
    assert recents[1]["tiene_solucion_optima"] is False
    assert recents[1]["rendimiento_optimo"] is None
    assert recents[1]["polinizadores_optimos"] is None


def test_get_management_report_with_infeasible_simulations():
    """
    Caso 7: Reporte general de gestión ante simulaciones infactibles:
    - Sim 1: Cumple hipótesis (delta_y >= 0, delta_p >= 20%).
    - Sim 2: No cumple hipótesis (delta_y < 0).
    - Sim 3: Infactible (metricas_optimas=None) -> NO CUMPLE ni suma a promedios óptimos.
    """
    sim1 = DummySimulation(
        sim_id=1,
        usuario_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 82.0, "pollinator_abundance_index": 65.0, "pollinator_diversity_index": 0.7},
    )
    sim2 = DummySimulation(
        sim_id=2,
        usuario_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas={"crop_yield_index": 70.0, "pollinator_abundance_index": 55.0, "pollinator_diversity_index": 0.6},
    )
    sim3 = DummySimulation(
        sim_id=3,
        usuario_id=1,
        metricas_base={"crop_yield_index": 80.0, "pollinator_abundance_index": 50.0, "pollinator_diversity_index": 0.5},
        metricas_optimas=None,
    )

    db = MockSession(all_sims=[sim1, sim2, sim3])

    report = get_management_report(db)
    kpis = report.kpis_agroecologicos

    assert kpis.total_simulaciones == 3
    assert kpis.simulaciones_evaluables == 2
    assert kpis.simulaciones_no_evaluables == 1
    assert kpis.simulaciones_cumplen_hipotesis == 1
    assert kpis.simulaciones_no_cumplen == 1
    assert kpis.denominador_tasa == "evaluables"
    assert kpis.tasa_cumplimiento_hipotesis == 50.0

    # El promedio óptimo de rendimiento solo debe promediar las simulaciones con solución (82 + 70) / 2 = 76.0
    assert kpis.rendimiento_promedio_optimo == 76.0
