from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_role
from app.models import Usuario
from app.schemas_reports import ManagementReportResponse, OperationalReportResponse
from app.services.report_general_service import get_management_report, get_operational_report

settings = get_settings()

router = APIRouter(prefix="/api/admin/reports", tags=["admin-reports"])


@router.get("/operational", response_model=OperationalReportResponse)
async def get_operational_report_endpoint(
    fecha_inicio: datetime | None = Query(None, description="Fecha de inicio (ISO 8601)"),
    fecha_fin: datetime | None = Query(None, description="Fecha de fin (ISO 8601)"),
    region: str | None = Query(None, description="Filtro parcial por nombre o coordenadas de región"),
    usuario_id: int | None = Query(None, description="ID del usuario a filtrar"),
    periodo: str = Query("dia", regex="^(dia|semana|mes)$", description="Agrupación temporal: dia, semana, mes"),
    _: Usuario = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Genera reporte operativo agregado sobre el uso de la plataforma."""
    return get_operational_report(
        db=db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        region=region,
        usuario_id=usuario_id,
        periodo=periodo,
    )


@router.get("/management", response_model=ManagementReportResponse)
async def get_management_report_endpoint(
    fecha_inicio: datetime | None = Query(None, description="Fecha de inicio (ISO 8601)"),
    fecha_fin: datetime | None = Query(None, description="Fecha de fin (ISO 8601)"),
    region: str | None = Query(None, description="Filtro parcial por nombre o coordenadas de región"),
    usuario_id: int | None = Query(None, description="ID del usuario a filtrar"),
    top_n: int = Query(10, ge=1, le=50, description="Cantidad de mejores configuraciones a retornar"),
    _: Usuario = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Genera reporte de gestión agronómica y ecológica agregada."""
    return get_management_report(
        db=db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        region=region,
        usuario_id=usuario_id,
        top_n=top_n,
    )


@router.get("/operational/export")
async def export_operational_report_data(
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
    region: str | None = None,
    usuario_id: int | None = None,
    periodo: str = "dia",
    current_user: Usuario = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna payload enriquecido para exportación estructurada del reporte operativo."""
    report_data = get_operational_report(
        db=db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        region=region,
        usuario_id=usuario_id,
        periodo=periodo,
    )
    return {
        "report_type": "operational",
        "data": report_data.model_dump(),
        "report_context": {
            "generated_at": datetime.utcnow().isoformat(),
            "exported_by": current_user.email,
            "platform": settings.app_name,
        },
    }


@router.get("/management/export")
async def export_management_report_data(
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
    region: str | None = None,
    usuario_id: int | None = None,
    top_n: int = 10,
    current_user: Usuario = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retorna payload enriquecido para exportación estructurada del reporte de gestión."""
    report_data = get_management_report(
        db=db,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        region=region,
        usuario_id=usuario_id,
        top_n=top_n,
    )
    return {
        "report_type": "management",
        "data": report_data.model_dump(),
        "report_context": {
            "generated_at": datetime.utcnow().isoformat(),
            "exported_by": current_user.email,
            "platform": settings.app_name,
        },
    }
