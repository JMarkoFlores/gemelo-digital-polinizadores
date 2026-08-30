from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    rol: Literal["admin", "cliente"] = "cliente"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    rol: Literal["admin", "cliente"] = "cliente"
    activo: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    rol: Literal["admin", "cliente"] | None = None
    activo: bool | None = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    rol: str
    activo: bool
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class SimulationResponse(BaseModel):
    id: int
    usuario_id: int
    coordenadas_geojson: dict[str, Any]
    variables_entrada: dict[str, Any]
    metricas_base: dict[str, Any]
    metricas_optimas: dict[str, Any]
    frente_pareto: list[dict[str, Any]]
    fecha: datetime

    model_config = {"from_attributes": True}


class GeometryPayload(BaseModel):
    type: str
    coordinates: Any


class SimulationRequest(BaseModel):
    geometry: dict[str, Any] | None = None
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    pesticide_level: float = Field(ge=0, le=100)
    min_natural_area_pct: float = Field(ge=0, le=100)
    climate_scenario: Literal["current", "warm", "dry", "extreme"] = "current"


class SimulationCandidate(BaseModel):
    crop_area_pct: float
    natural_area_pct: float
    floral_strips_pct: float
    pesticide_level: float
    soil_management_score: float
    temperature_c: float
    precipitation_mm: float
    landscape_diversity: float
    crop_yield_index: float
    pollinator_abundance_index: float
    pollinator_diversity_index: float


class SimulationResultPayload(BaseModel):
    baseline: dict[str, Any]
    pareto_front: list[SimulationCandidate]
    best_solution: dict[str, Any]
    optimized_landscape: dict[str, Any]
    delta_yield: float
    delta_pollinators: float
    hypothesis_status: str
    model_version: str | None = None
    cache_hit: bool = False

    model_config = {"protected_namespaces": ()}


class ChatRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    model: str


class SimulationFilters(BaseModel):
    user_id: int | None = None
    region: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class AdminDashboardResponse(BaseModel):
    total_users: int
    active_users: int
    simulations_this_month: int
    top_regions: list[dict[str, Any]]


TokenResponse.model_rebuild()
