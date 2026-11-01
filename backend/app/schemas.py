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
    metricas_optimas: dict[str, Any] | None = None
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
    status: str = "success"
    message: str | None = None
    baseline: dict[str, Any]
    pareto_front: list[SimulationCandidate] = Field(default_factory=list)
    best_solution: dict[str, Any] | None = None
    optimized_landscape: dict[str, Any] | None = None
    delta_yield: float | None = None
    delta_pollinators: float | None = None
    hypothesis_status: str | None = None
    meets_joint_criteria: bool | None = None
    algorithm_evaluations_total: int | None = None
    pareto_solutions_returned: int | None = None
    pareto_candidates_evaluated: int | None = None
    pareto_verified_count: int | None = None
    model_version: str | None = None
    bundle_id: str | None = None
    cache_hit: bool = False
    recomendacion_ia: str | None = None

    model_config = {"protected_namespaces": ()}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


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


class ElevationCell(BaseModel):
    x: int
    z: int
    lat: float
    lon: float
    elevation_m: float
    rel_elevation_m: float
    normalized: float


class TerrainElevationRequest(BaseModel):
    geometry: dict[str, Any] | None = None
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)


class TerrainElevationResponse(BaseModel):
    available: bool
    source: str
    min_elevation_m: float
    max_elevation_m: float
    elevation_range_m: float
    mean_elevation_m: float
    grid: list[ElevationCell]
    matrix: list[list[float]]
    normalized_matrix: list[list[float]]
    message: str


TokenResponse.model_rebuild()
