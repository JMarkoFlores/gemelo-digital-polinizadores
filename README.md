# Gemelos Digitales 02

Fase 1 del monorepo para una plataforma de gemelo digital de paisajes agricolas y redes de polinizadores.

## Servicios

- `frontend`: React + Vite + Tailwind
- `backend`: FastAPI + PostgreSQL + JWT
- `streamlit`: interfaz base para entrenamiento
- `db`: PostgreSQL

## Arranque rapido

1. Copia `.env.example` a `.env` si quieres personalizar variables.
2. Ejecuta:

```bash
docker compose up --build
```

## URLs

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Streamlit: `http://localhost:8501`

## Credenciales seed

- Admin:
  - Email: `admin@example.com`
  - Password: `Admin12345!`
- Cliente:
  - Email: `cliente@example.com`
  - Password: `Cliente12345!`

## Estructura

- `backend/`: API, modelos, autenticacion y seed data
- `frontend/`: interfaz base para cliente y administrador
- `streamlit_app/`: aplicacion Streamlit base con placeholders del flujo cientifico

## Implementado en Fase 1

- Docker Compose con 4 servicios
- Volumen compartido `/modelos_ia/` entre Streamlit y backend
- Backend FastAPI con:
  - `/health`
  - `/api/auth/register`
  - `/api/auth/login`
  - `/api/auth/me`
- PostgreSQL con tablas `usuarios` y `simulaciones`
- Seed automatico de usuarios admin y cliente
- Frontend base con login, registro, dashboards y rutas protegidas
- Streamlit base con secciones del pipeline cientifico

## Fase 2: entorno de entrenamiento

La app de `streamlit_app/` ahora incluye:

- generador de dataset sintetico listo para uso local
- carga de CSV propio para entrenamiento
- conectores reales preparados y documentados para:
  - GBIF con `pygbif`
  - ERA5 con `cdsapi`
  - Earth Engine / Sentinel-2 con `earthengine-api` y `geemap`
- simulador ABM con `mesa` para dinamica de polinizadores
- entrenamiento de un modelo surrogate con TensorFlow/Keras
- metricas de evaluacion: MAE, RMSE y R2
- exportacion de `modelo_optimizado.h5` a `/modelos_ia/`

### Flujo rapido en Streamlit

1. Abre `http://localhost:8501`
2. Genera un dataset sintetico o carga un CSV compatible
3. Ejecuta una corrida ABM para visualizar recursos y abundancia
4. Inicia el entrenamiento del surrogate
5. Exporta el modelo a `/modelos_ia/modelo_optimizado.h5`

### Columnas minimas del dataset

Entradas:

- `crop_area_pct`
- `natural_area_pct`
- `floral_strips_pct`
- `pesticide_level`
- `soil_management_score`
- `temperature_c`
- `precipitation_mm`
- `landscape_diversity`

Objetivos:

- `crop_yield_index`
- `pollinator_abundance_index`
- `pollinator_diversity_index`

## Fase 3: backend cientifico

El backend ahora incluye:

- carga del modelo `.h5` en `lifespan`
- endpoint de estado y recarga del modelo
- optimizacion multiobjetivo con NSGA-II usando `pymoo`
- endpoint `POST /api/simular`
- persistencia automatica de simulaciones
- historial paginado por usuario
- endpoints de administracion para usuarios y simulaciones
- endpoint `POST /api/chat` con Groq

### Contrato principal de simulacion

Entrada `POST /api/simular`:

- `geometry` o `bbox`
- `pesticide_level`
- `min_natural_area_pct`
- `climate_scenario` en `current | warm | dry | extreme`

Salida principal:

- `baseline`
- `pareto_front`
- `best_solution`
- `optimized_landscape`
- `delta_yield`
- `delta_pollinators`
- `hypothesis_status`

### Endpoints relevantes

- `GET /health`
- `GET /api/model/status`
- `POST /api/model/reload`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/simular`
- `GET /api/simulations/me`
- `GET /api/simulations/me/{id}`
- `GET /api/admin/dashboard`
- `GET /api/admin/users`
- `POST /api/admin/users`
- `PUT /api/admin/users/{id}`
- `DELETE /api/admin/users/{id}`
- `GET /api/admin/simulations`
- `GET /api/admin/simulations/{id}/report`
- `POST /api/chat`

## Fase 4: frontend final

El frontend React ahora incluye:

- flujo cliente con mapa interactivo y dibujo de area
- envio real de `geometry` y `bbox` a `POST /api/simular`
- panel de escenarios con sliders y selector de clima
- vista de resultados con frente de Pareto y comparacion base vs optimo
- historial paginado del cliente con exportacion PDF
- chatbot flotante conectado a `/api/chat`
- panel admin con:
  - metricas globales
  - gestion de usuarios
  - tabla global de simulaciones
  - exportacion PDF y Word
- dark mode, i18n, sidebar retracil y lazy loading

### Flujo completo de uso

1. Levanta todo con `docker compose up --build`
2. Inicia sesion en `http://localhost:5173`
3. Si eres cliente:
   - dibuja un area
   - configura pesticidas, area natural y clima
   - ejecuta la optimizacion
   - revisa resultados e historial
4. Si eres admin:
   - revisa metricas globales
   - administra usuarios
   - consulta simulaciones y exporta reportes

### Credenciales de prueba

- Admin: `admin@example.com` / `Admin12345!`
- Cliente: `cliente@example.com` / `Cliente12345!`

## Siguientes fases

- Fase 3: backend cientifico con carga de `.h5`, NSGA-II, historial y admin
- Fase 4: mapas, resultados, chatbot y reportes finales en React
