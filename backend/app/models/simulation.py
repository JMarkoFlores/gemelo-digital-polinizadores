from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Simulacion(Base):
    __tablename__ = "simulaciones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    coordenadas_geojson: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    variables_entrada: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metricas_base: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metricas_optimas: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    frente_pareto: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    usuario = relationship("Usuario", back_populates="simulaciones")
