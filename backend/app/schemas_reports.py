from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class OperationalFilterParams(BaseModel):
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    region: str | None = None
    usuario_id: int | None = None
    periodo: str = Field(default="dia", description="Agrupación temporal: dia, semana, mes")


class OperationalSummary(BaseModel):
    total_simulaciones: int
    usuarios_activos: int
    regiones_cubiertas: int
    tiempo_promedio_segundos: float | None = None
    tiempo_promedio_disponible: bool = False
    tiempo_estimado_segundos: float = 1.25


class TemporalTrendPoint(BaseModel):
    periodo: str
    simulaciones: int
    acumulado: int


class UserRankingItem(BaseModel):
    usuario_id: int
    email: str
    rol: str
    total_simulaciones: int
    ultima_simulacion: str | None = None


class RegionDistributionItem(BaseModel):
    region: str
    total: int
    porcentaje: float


class OperationalReportResponse(BaseModel):
    filtros: dict[str, Any]
    resumen: OperationalSummary
    tendencia_temporal: list[TemporalTrendPoint]
    ranking_usuarios: list[UserRankingItem]
    distribucion_regiones: list[RegionDistributionItem]


class ManagementKpis(BaseModel):
    total_simulaciones: int
    simulaciones_evaluables: int = 0
    simulaciones_no_evaluables: int = 0
    rendimiento_promedio_base: float | None = None
    rendimiento_promedio_optimo: float | None = None
    delta_rendimiento_promedio: float | None = None
    delta_rendimiento_pct: float | None = None
    abundancia_polinizadores_base: float | None = None
    abundancia_polinizadores_optima: float | None = None
    delta_abundancia_promedio: float | None = None
    delta_abundancia_pct: float | None = None
    diversidad_polinizadores_base: float | None = None
    diversidad_polinizadores_optima: float | None = None
    delta_diversidad_promedio: float | None = None
    tasa_cumplimiento_hipotesis: float | None = None
    denominador_tasa: str = "evaluables"
    simulaciones_cumplen_hipotesis: int = 0
    simulaciones_no_cumplen: int = 0
    rendimiento_promedio_base_total: float | None = None
    abundancia_polinizadores_base_total: float | None = None
    diversidad_polinizadores_base_total: float | None = None


class ManagementTemporalEvolutionPoint(BaseModel):
    fecha: str
    total_simulaciones: int = 0
    simulaciones_evaluables: int = 0
    simulaciones_no_evaluables: int = 0
    simulaciones_cumplen_hipotesis: int = 0
    simulaciones_no_cumplen: int = 0
    rendimiento_base: float | None = None
    rendimiento_optimo: float | None = None
    delta_rendimiento: float | None = None
    abundancia_base: float | None = None
    abundancia_optima: float | None = None
    delta_abundancia: float | None = None
    diversidad_base: float | None = None
    diversidad_optima: float | None = None
    delta_diversidad: float | None = None
    rendimiento_base_total: float | None = None
    abundancia_base_total: float | None = None
    diversidad_base_total: float | None = None


class RegionManagementItem(BaseModel):
    region: str
    total_simulaciones: int
    simulaciones_evaluables: int = 0
    simulaciones_no_evaluables: int = 0
    simulaciones_cumplen_hipotesis: int = 0
    simulaciones_no_cumplen: int = 0
    rendimiento_promedio_base: float | None = None
    rendimiento_promedio_optimo: float | None = None
    delta_rendimiento_promedio: float | None = None
    abundancia_promedio_base: float | None = None
    abundancia_promedio_optimo: float | None = None
    delta_abundancia_promedio: float | None = None
    diversidad_promedio_base: float | None = None
    diversidad_promedio_optimo: float | None = None
    delta_diversidad_promedio: float | None = None
    tasa_cumplimiento_hipotesis: float | None = None
    denominador_tasa: str = "evaluables"
    rendimiento_promedio_base_total: float | None = None
    abundancia_promedio_base_total: float | None = None
    diversidad_promedio_base_total: float | None = None


class ParetoConfigurationItem(BaseModel):
    rank: int
    simulacion_id: int
    region: str
    fecha: str
    crop_yield_index: float
    pollinator_abundance_index: float
    pollinator_diversity_index: float
    crop_area_pct: float
    natural_area_pct: float
    floral_strips_pct: float
    pesticide_level: float
    soil_management_score: float
    score: float


class ManagementReportResponse(BaseModel):
    filtros: dict[str, Any]
    kpis_agroecologicos: ManagementKpis
    evolucion_temporal: list[ManagementTemporalEvolutionPoint]
    comparacion_regiones: list[RegionManagementItem]
    top_configuraciones_pareto: list[ParetoConfigurationItem]
