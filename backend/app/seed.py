from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Simulacion, Usuario
from app.security import hash_password


def _ensure_user(db: Session, email: str, password: str, role: str) -> Usuario:
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user:
        return user

    user = Usuario(email=email, password_hash=hash_password(password), rol=role, activo=True)
    db.add(user)
    db.flush()
    return user


def seed_initial_data(db: Session) -> None:
    settings = get_settings()
    admin = _ensure_user(db, settings.admin_email, settings.admin_password, "admin")
    client = _ensure_user(db, settings.client_email, settings.client_password, "cliente")

    if not db.query(Simulacion).filter(Simulacion.usuario_id == client.id).first():
        db.add(
            Simulacion(
                usuario_id=client.id,
                coordenadas_geojson={"type": "Polygon", "coordinates": [[[-78.9, -8.1], [-78.8, -8.1], [-78.8, -8.0], [-78.9, -8.0], [-78.9, -8.1]]]},
                variables_entrada={"pesticidas": 35, "area_natural_minima": 20, "escenario": "actual"},
                metricas_base={"rendimiento": 74.2, "polinizadores": 58.0},
                metricas_optimas={"rendimiento": 77.4, "polinizadores": 71.1},
                frente_pareto=[
                    {"rendimiento": 75.1, "polinizadores": 66.2},
                    {"rendimiento": 76.3, "polinizadores": 69.7},
                ],
            )
        )

    db.commit()
