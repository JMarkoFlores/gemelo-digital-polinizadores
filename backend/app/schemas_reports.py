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
    rendimiento_promedio_base: float
    rendimiento_promedio_optimo: float
    delta_rendimiento_promedio: float
    delta_rendimiento_pct: float
    abundancia_polinizadores_base: float
    abundancia_polinizadores_optima: float
    delta_abundancia_promedio: float
    delta_abundancia_pct: float
    diversidad_polinizadores_base: float
    diversidad_polinizadores_optima: float
    delta_diversidad_promedio: float
    tasa_cumplimiento_hipotesis: float
    simulaciones_cumplen_hipotesis: int
    simulaciones_no_cumplen: int


class ManagementTemporalEvolutionPoint(BaseModel):
    fecha: str
    rendimiento_base: float
    rendimiento_optimo: float
    delta_rendimiento: float
    abundancia_base: float
    abundancia_optima: float
    delta_abundancia: float
    diversidad_base: float
    diversidad_optima: float


class RegionManagementItem(BaseModel):
    region: str
    total_simulaciones: int
    rendimiento_promedio_base: float
    rendimiento_promedio_optimo: float
    abundancia_promedio_base: float
    abundancia_promedio_optimo: float
    diversidad_promedio_base: float
    diversidad_promedio_optimo: float
    tasa_cumplimiento_hipotesis: float


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
