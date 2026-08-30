from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine, get_db
from app.dependencies import get_current_user, require_role
from app.models import Simulacion, Usuario
from app.schemas import (
    AdminDashboardResponse,
    ChatRequest,
    ChatResponse,
    PaginatedResponse,
    SimulationRequest,
    SimulationResponse,
    SimulationResultPayload,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.seed import seed_initial_data
from app.security import create_access_token, hash_password, verify_password
from app.services.chat_service import generate_chat_reply
from app.services.model_store import model_store
from app.services.optimization import run_simulation

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
    model_store.load()
    # Auto-reload model whenever Streamlit exports a new .h5 to the shared volume
    model_store.start_watcher(poll_interval=5.0)
    app.state.model_store = model_store
    yield
    model_store.stop_watcher()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def paginate(query, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return total, items


def get_user_or_404(db: Session, user_id: int) -> Usuario:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_simulation_or_404(db: Session, simulation_id: int) -> Simulacion:
    simulation = db.query(Simulacion).filter(Simulacion.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    return simulation


@app.get("/health")
async def healthcheck():
    return {
        "status": "ok",
        "service": "backend",
        "model_ready": model_store.is_ready,
        "model_version": model_store.version,
        "model_status": model_store.status_message,
    }


@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(Usuario).filter(Usuario.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    role = "cliente" if payload.rol == "admin" else payload.rol
    user = Usuario(email=payload.email, password_hash=hash_password(payload.password), rol=role, activo=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.email)
    return TokenResponse(access_token=token, user=user)


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
    token = create_access_token(user.email)
    return TokenResponse(access_token=token, user=user)


@app.get("/api/auth/me", response_model=UserResponse)
async def me(current_user: Usuario = Depends(get_current_user)):
    return current_user


@app.post("/api/model/reload")
async def reload_model(_: Usuario = Depends(require_role("admin", "cliente"))):
    """Force the backend to re-read the model file from disk.
    Accessible to both admin and cliente so the React frontend can
    trigger a reload after Streamlit exports the model.
    """
    model_store.reload()
    return {"model_ready": model_store.is_ready, "model_status": model_store.status_message, "model_version": model_store.version}


@app.get("/api/model/status")
async def model_status(current_user: Usuario = Depends(require_role("admin", "cliente"))):
    return {
        "model_ready": model_store.is_ready,
        "model_status": model_store.status_message,
        "model_version": model_store.version,
        "requested_by": current_user.email,
    }


@app.post("/api/simular", response_model=SimulationResultPayload)
async def simular(
    payload: SimulationRequest,
    current_user: Usuario = Depends(require_role("cliente", "admin")),
    db: Session = Depends(get_db),
):
    if not model_store.is_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=model_store.status_message)

    try:
        result = run_simulation(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    simulation = Simulacion(
        usuario_id=current_user.id,
        coordenadas_geojson=result["baseline"]["geometry"],
        variables_entrada=payload.model_dump(),
        metricas_base=result["baseline"],
        metricas_optimas=result["best_solution"],
        frente_pareto=result["pareto_front"],
    )
    db.add(simulation)
    db.commit()
    return result


@app.get("/api/simulations/me", response_model=PaginatedResponse)
async def list_my_simulations(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: Usuario = Depends(require_role("cliente", "admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Simulacion).filter(Simulacion.usuario_id == current_user.id).order_by(Simulacion.fecha.desc())
    total, items = paginate(query, page, page_size)
    return PaginatedResponse(items=[SimulationResponse.model_validate(item).model_dump() for item in items], total=total, page=page, page_size=page_size)


@app.get("/api/simulations/me/{simulation_id}", response_model=SimulationResponse)
async def get_my_simulation(
    simulation_id: int,
    current_user: Usuario = Depends(require_role("cliente", "admin")),
    db: Session = Depends(get_db),
):
    simulation = get_simulation_or_404(db, simulation_id)
    if simulation.usuario_id != current_user.id and current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this simulation")
    return simulation


@app.get("/api/admin/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(_: Usuario = Depends(require_role("admin")), db: Session = Depends(get_db)):
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    total_users = db.query(func.count(Usuario.id)).scalar() or 0
    active_users = db.query(func.count(Usuario.id)).filter(Usuario.activo.is_(True)).scalar() or 0
    simulations_this_month = db.query(func.count(Simulacion.id)).filter(Simulacion.fecha >= month_start).scalar() or 0

    rows = db.query(Simulacion.metricas_base).all()
    regions: dict[str, int] = {}
    for (metricas_base,) in rows:
        region = (metricas_base or {}).get("region_label", "unknown")
        regions[region] = regions.get(region, 0) + 1
    top_regions = [{"region": region, "count": count} for region, count in sorted(regions.items(), key=lambda item: item[1], reverse=True)[:5]]
    return AdminDashboardResponse(
        total_users=total_users,
        active_users=active_users,
        simulations_this_month=simulations_this_month,
        top_regions=top_regions,
    )


@app.get("/api/admin/users", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    _: Usuario = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Usuario).order_by(Usuario.fecha_creacion.desc())
    if search:
        query = query.filter(Usuario.email.ilike(f"%{search}%"))
    total, items = paginate(query, page, page_size)
    return PaginatedResponse(items=[UserResponse.model_validate(item).model_dump() for item in items], total=total, page=page, page_size=page_size)


@app.post("/api/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, _: Usuario = Depends(require_role("admin")), db: Session = Depends(get_db)):
    existing = db.query(Usuario).filter(Usuario.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = Usuario(email=payload.email, password_hash=hash_password(payload.password), rol=payload.rol, activo=payload.activo)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.put("/api/admin/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, payload: UserUpdate, _: Usuario = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes:
        user.email = changes["email"]
    if "rol" in changes:
        user.rol = changes["rol"]
    if "activo" in changes:
        user.activo = changes["activo"]
    if changes.get("password"):
        user.password_hash = hash_password(changes["password"])
    db.commit()
    db.refresh(user)
    return user


@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, _: Usuario = Depends(require_role("admin")), db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    db.delete(user)
    db.commit()
    return {"deleted": True, "user_id": user_id}


@app.get("/api/admin/simulations", response_model=PaginatedResponse)
async def list_all_simulations(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user_id: int | None = None,
    region: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    _: Usuario = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(Simulacion).order_by(Simulacion.fecha.desc())
    if user_id is not None:
        query = query.filter(Simulacion.usuario_id == user_id)
    if start_date is not None:
        query = query.filter(Simulacion.fecha >= start_date)
    if end_date is not None:
        query = query.filter(Simulacion.fecha <= end_date)
    if region:
        query = query.filter(Simulacion.metricas_base["region_label"].astext.ilike(f"%{region}%"))

    total, items = paginate(query, page, page_size)
    return PaginatedResponse(items=[SimulationResponse.model_validate(item).model_dump() for item in items], total=total, page=page, page_size=page_size)


@app.get("/api/admin/simulations/{simulation_id}/report")
async def simulation_report_data(simulation_id: int, _: Usuario = Depends(require_role("admin")), db: Session = Depends(get_db)):
    simulation = get_simulation_or_404(db, simulation_id)
    user = get_user_or_404(db, simulation.usuario_id)
    return {
        "simulation": SimulationResponse.model_validate(simulation).model_dump(),
        "user": UserResponse.model_validate(user).model_dump(),
        "report_context": {
            "generated_at": datetime.utcnow().isoformat(),
            "model_version": model_store.version,
            "platform": settings.app_name,
        },
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, current_user: Usuario = Depends(require_role("cliente", "admin"))):
    try:
        reply, model_name = generate_chat_reply(payload.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Chat provider error: {exc}") from exc
    return ChatResponse(reply=reply, model=model_name)


@app.get("/api/admin/ping")
async def admin_ping(_: Usuario = Depends(require_role("admin"))):
    return {"status": "ok", "scope": "admin"}


@app.get("/api/client/ping")
async def client_ping(_: Usuario = Depends(require_role("cliente", "admin"))):
    return {"status": "ok", "scope": "client"}
