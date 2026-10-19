# Inventario Técnico del Repositorio: Gemelos Digitales 02

**Repositorio:** `gemelo-digital-polinizadores` (Gemelos Digitales 02)  
**Rama de trabajo exclusiva:** `docs/automatizacion-confluence`  
**Commit analizado:** `0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`  
**Fecha de corte del análisis:** 14 de octubre de 2026  
**Estado de ejecución de pruebas:** Análisis estático, de código fuente, configuración y documentación. **No se ejecutaron servicios en tiempo de ejecución, simulaciones ABM, optimizaciones NSGA-II, entrenamientos de redes neuronales ni llamadas activas a APIs externas.**

---

## 1. Convenciones de Clasificación de Hallazgos

Para garantizar la integridad y trazabilidad técnica, cada elemento registrado en este documento se etiqueta según su origen y estado de constatación:

- `[CÓDIGO]`: Funcionalidad, endpoint, modelo, esquema o componente implementado e inspeccionado directamente en el código fuente.
- `[DOCUMENTO]`: Elemento declarado en la documentación existente ([README.md](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/README.md), [CAMBIOS_FUTUROS.md](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/CAMBIOS_FUTUROS.md), [metadata.json](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/metadata.json)).
- `[VERIFICAR]`: Discrepancia, asunción, elemento no comprobable sin ejecución o material externo faltante.

---

## 2. Arquitectura General y Servicios

El sistema está concebido como una plataforma modular basada en microservicios contenerizados mediante Docker Compose.

### 2.1 Definición de Contenedores y Servicios

Archivo de respaldo: [docker-compose.yml](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/docker-compose.yml) y [docker-compose.prod.yml](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/docker-compose.prod.yml)

| Servicio | Tipo / Imagen Base | Puerto Expuesto | Volumen / Persistencia | Función Principal | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`db`** | `postgres:16-alpine` | `5432:5432` | `postgres_data:/var/lib/postgresql/data` | Persistencia relacional de usuarios y simulaciones | `[CÓDIGO]` |
| **`backend`** | Python 3.11-slim (`./backend`) | `8000:8000` | Local `./backend:/app` + `modelos_ia_volume:/modelos_ia/` | API REST con FastAPI, inferencia TensorFlow, optimización pymoo NSGA-II, control de acceso | `[CÓDIGO]` |
| **`frontend`** | Node/Vite (`./frontend`) | `5173:5173` | Local `./frontend:/app` + `/app/node_modules` | SPA React 18, visualizaciones Leaflet, Diorama 3D (Three.js/Fiber), Recharts | `[CÓDIGO]` |
| **`streamlit`** | Python 3.11 (`./streamlit_app`) | `8501:8501` | Local `./streamlit_app:/app` + `modelos_ia_volume:/modelos_ia/` | Entorno científico interactivo: ingesta, ABM (Mesa), entrenamiento y exportación | `[CÓDIGO]` |
| **`langflow`** | `langflowai/langflow:latest` | `7860:7860` | `langflow_data:/app/langflow` + `./langflow/flows:/app/flows` | Orquestador visual de agentes IA para explicabilidad agroecológica | `[CÓDIGO]` `[VERIFICAR]` *(README declara 4 servicios; hay 5 activos)* |

### 2.2 Volúmenes Compartidos y Persistencia
- `postgres_data`: Persistencia de base de datos PostgreSQL ([docker-compose.yml:89](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/docker-compose.yml#L89)).
- `modelos_ia_volume`: Volumen compartido montado en `/modelos_ia/` entre el contenedor de **Streamlit** (productor del modelo `.h5` y metadatos JSON) y el contenedor de **Backend** (consumidor del modelo con recarga en caliente por hilo observador mtime) ([docker-compose.yml:90](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/docker-compose.yml#L90), [model_store.py:41-86](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/model_store.py#L41-L86)).
- `langflow_data`: Persistencia interna de esquemas y ejecuciones de Langflow ([docker-compose.yml:91](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/docker-compose.yml#L91)).

### 2.3 Variables de Configuración del Entorno
Archivos de respaldo: [.env.example](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/.env.example) y [backend/app/config.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py)

| Variable | Valor por Defecto / Configurado | Descripción | Respaldado en |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+psycopg2://gemelos_user:gemelos_password@db:5432/gemelos_db` | Cadena de conexión SQLAlchemy | [config.py:15](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L15) |
| `JWT_SECRET` | `change-me-in-production` | Llave simétrica de firma de tokens JWT | [config.py:16](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L16) |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de encriptación de token | [config.py:17](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L17) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Tiempo de vida del token (minutos) | [config.py:18](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L18) |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Orígenes permitidos en CORS | [config.py:19](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L19) |
| `ADMIN_EMAIL` | `admin@example.com` | Email del usuario administrador inicial | [config.py:20](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L20) |
| `ADMIN_PASSWORD` | `Admin12345!` | Contraseña del admin sembrado | [config.py:21](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L21) |
| `CLIENT_EMAIL` | `cliente@example.com` | Email del usuario cliente inicial | [config.py:22](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L22) |
| `CLIENT_PASSWORD` | `Cliente12345!` | Contraseña del cliente sembrado | [config.py:23](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L23) |
| `GROQ_API_KEY` | `""` (opcional/vacía por defecto) | Clave de API para inferencia LLM en Groq | [config.py:24](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L24) |
| `GROQ_MODEL` | `llama-3.1-70b-versatile` | Modelo LLM usado en Groq | [config.py:25](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L25) |
| `MODEL_DIR` | `/modelos_ia` | Ruta compartida del modelo entrenado | [config.py:26](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L26) |
| `MODEL_FILENAME` | `modelo_optimizado.h5` | Nombre del archivo binario del modelo Keras | [config.py:27](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L27) |
| `MODEL_METADATA_FILENAME` | `modelo_optimizado_metadata.json` | Metadatos y escaladores del modelo activo | [config.py:28](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L28) |
| `CACHE_TTL_SECONDS` | `900` (15 minutos) | Tiempo de expiración de caché de optimizaciones | [config.py:29](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L29) |
| `CACHE_MAX_ITEMS` | `64` | Capacidad máxima de entradas en memoria del caché LRU | [config.py:30](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L30) |
| `LANGFLOW_URL` | `http://langflow:7860` | URL interna del contenedor Langflow | [config.py:31](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L31) |
| `LANGFLOW_FLOW_ID` | `asistente-recomendaciones-agroecologicas` | ID del flujo en Langflow para recomendaciones | [config.py:32](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/config.py#L32) |
| `VITE_API_BASE_URL` | `http://localhost:8000` (dev) / `/api` (prod) | Base URL de la API consumida por el frontend | [docker-compose.yml:52](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/docker-compose.yml#L52), [docker-compose.prod.yml:48](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/docker-compose.prod.yml#L48) |

---

## 3. Backend (FastAPI): Servicios, Endpoints, Modelos y Lógica de Negocio

El backend está construido con FastAPI 0.115.0 y SQLAlchemy 2.0.35, organizado bajo el paquete [backend/app/](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/).

### 3.1 Inventario de Endpoints REST

Archivos de respaldo: [backend/app/main.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/main.py) y [backend/app/routers/admin_reports.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/routers/admin_reports.py)

| Método | Endpoint | Roles Permitidos | Parámetros / Payload de Entrada | Respuesta / Schema | Descripción Técnica |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Público | Ninguno | `dict` (status, model_ready, model_version, fuente_datos, region_name, bounds) | Healthcheck general y estado del modelo cargado en memoria |
| `POST` | `/api/auth/register` | Público | [UserRegister](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L7-L10) (`email`, `password`, `rol`) | [TokenResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L42-L46) | Registro de usuario (fuerza rol cliente si solicita admin) |
| `POST` | `/api/auth/login` | Público | [UserLogin](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L13-L16) (`email`, `password`) | [TokenResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L42-L46) | Autenticación con JWT Bearer token |
| `GET` | `/api/auth/me` | Autenticado | Header `Authorization: Bearer <token>` | [UserResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L32-L40) | Retorna los datos del usuario autenticado |
| `POST` | `/api/model/reload` | `admin`, `cliente` | Ninguno | `dict` (estado de recarga en memoria) | Fuerza al hilo observador a releer el binario `.h5` de `/modelos_ia/` |
| `GET` | `/api/model/status` | `admin`, `cliente` | Ninguno | `dict` (metadatos, fuente_datos, versión, región) | Consulta estado detallado y procedencia del modelo |
| `GET` | `/api/model/region-check` | `admin`, `cliente` | Query: `lat`, `lon`, `tolerance` | `dict` (`has_restriction`, `is_valid`, `distance_km`, `message`) | Valida si un punto geográfico no sufre Domain Shift respecto al entrenamiento |
| `POST` | `/api/terrain/elevation-grid` | `admin`, `cliente` | [TerrainElevationRequest](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L149-L152) (`geometry`, `bbox`) | [TerrainElevationResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L154-L166) | Obtiene matriz 10x10 de elevación real (Open-Elevation / Open-Meteo) |
| `POST` | `/api/simular` | `cliente`, `admin` | [SimulationRequest](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L73-L79) (`geometry`, `bbox`, `pesticide_level`, `min_natural_area_pct`, `climate_scenario`) | [SimulationResultPayload](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L95-L107) | Ejecuta NSGA-II multiobjetivo (40 gen, pop 64), enriquece con IA y persiste en BD |
| `GET` | `/api/simulations/me` | `cliente`, `admin` | Query: `page`, `page_size` | [PaginatedResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L48-L53) ([SimulationResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L55-L66)[]) | Historial paginado de simulaciones del usuario en sesión |
| `GET` | `/api/simulations/me/{id}` | `cliente`, `admin` | Path: `simulation_id` | [SimulationResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L55-L66) | Detalle de simulación individual (valida pertenencia de usuario o rol admin) |
| `GET` | `/api/admin/dashboard` | `admin` | Ninguno | [AdminDashboardResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L132-L137) | Métricas agregadas: total_usuarios, activos, simulaciones del mes, top_regiones |
| `GET` | `/api/admin/users` | `admin` | Query: `page`, `page_size`, `search` | [PaginatedResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L48-L53) ([UserResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L32-L40)[]) | Listado paginado de usuarios con filtro por búsqueda |
| `POST` | `/api/admin/users` | `admin` | [UserCreate](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L18-L23) (`email`, `password`, `rol`, `activo`) | [UserResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L32-L40) | Creación manual de usuarios desde panel de administración |
| `PUT` | `/api/admin/users/{id}` | `admin` | Path: `user_id`, Body: [UserUpdate](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L25-L30) | [UserResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L32-L40) | Edición de rol, email, estado activo o cambio de contraseña |
| `DELETE` | `/api/admin/users/{id}` | `admin` | Path: `user_id` | `dict` (`deleted: true`, `user_id`) | Eliminación de usuario y cascada sobre sus simulaciones |
| `GET` | `/api/admin/simulations` | `admin` | Query: `page`, `page_size`, `user_id`, `region`, `start_date`, `end_date` | [PaginatedResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L48-L53) | Tabla global de simulaciones con filtros multicriterio |
| `GET` | `/api/admin/simulations/{id}/report` | `admin` | Path: `simulation_id` | `dict` (simulation, user, report_context) | Payload estructurado para exportación individual de reporte administrativo |
| `GET` | `/api/admin/reports/operational` | `admin` | Query: `fecha_inicio`, `fecha_fin`, `region`, `usuario_id`, `periodo` | [OperationalReportResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas_reports.py#L45-L51) | Reporte operativo agregado: ranking de usuarios, tendencia temporal, regiones |
| `GET` | `/api/admin/reports/management` | `admin` | Query: `fecha_inicio`, `fecha_fin`, `region`, `usuario_id`, `top_n` | [ManagementReportResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas_reports.py#L111-L117) | Reporte agronómico y ecológico: KPIs globales, deltas, tasa de hipótesis, top Pareto |
| `GET` | `/api/admin/reports/operational/export` | `admin` | Query de filtros operativos | `dict` (data, charts en base64 generados con matplotlib, context) | Payload enriquecido con imágenes base64 para reportes PDF/Word externos |
| `GET` | `/api/admin/reports/management/export` | `admin` | Query de filtros de gestión | `dict` (data, charts en base64 generados con matplotlib, context) | Payload enriquecido con gráficos de evolución y regiones para exportación |
| `POST` | `/api/chat` | `cliente`, `admin` | [ChatRequest](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L115-L118) (`message`, `history`) | [ChatResponse](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/schemas.py#L120-L123) | Chatbot con LLM Groq o fallback local conectado a PostgreSQL |
| `GET` | `/api/admin/ping` | `admin` | Ninguno | `dict` (`status: ok, scope: admin`) | Healthcheck autenticado para administradores |
| `GET` | `/api/client/ping` | `cliente`, `admin` | Ninguno | `dict` (`status: ok, scope: client`) | Healthcheck autenticado para clientes |

### 3.2 Entidades y Esquema de Base de Datos Relacional

#### Modelo `Usuario`
Archivo: [backend/app/models/user.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/models/user.py)
- Tabla: `usuarios`
- Columnas:
  - `id`: Entero, Clave Primaria autonumérica.
  - `email`: `String(255)`, único, no nulo, indexado.
  - `password_hash`: `String(255)`, no nulo (hash bcrypt generado mediante passlib).
  - `rol`: `String(20)`, no nulo (`admin` o `cliente`).
  - `fecha_creacion`: `DateTime`, default `datetime.utcnow`.
  - `activo`: `Boolean`, default `True`.
- Relación: `simulaciones = relationship("Simulacion", back_populates="usuario", cascade="all, delete-orphan")`.

#### Modelo `Simulacion`
Archivo: [backend/app/models/simulation.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/models/simulation.py)
- Tabla: `simulaciones`
- Columnas:
  - `id`: Entero, Clave Primaria autonumérica.
  - `usuario_id`: Clave Foránea referenciando `usuarios.id`, indexado, no nulo.
  - `coordenadas_geojson`: `JSON`, no nulo (geometría GeoJSON del polígono analizado).
  - `variables_entrada`: `JSON`, no nulo (parámetros de entrada de pesticidas, área natural mínima y escenario climático).
  - `metricas_base`: `JSON`, no nulo (estado inicial evaluado).
  - `metricas_optimas`: `JSON`, no nulo (mejor solución no dominada seleccionada del frente de Pareto).
  - `frente_pareto`: `JSON`, no nulo (lista de soluciones no dominadas generadas por NSGA-II).
  - `fecha`: `DateTime`, default `datetime.utcnow`.
- Relación: `usuario = relationship("Usuario", back_populates="simulaciones")`.

### 3.3 Servicios Internos del Backend
- **`model_store`** ([backend/app/services/model_store.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/model_store.py)): Administra el ciclo de vida del modelo Keras `.h5`. Implementa un `threading.Thread` en segundo plano (`start_watcher`) con polling cada 5 segundos para recargar el modelo cuando Streamlit exporte una versión nueva a `/modelos_ia/` sin requerir reinicio del contenedor. Incluye verificación de distancia geodésica Haversine (`check_point_in_region`) para detectar Domain Shift.
- **`optimization`** ([backend/app/services/optimization.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/optimization.py)): Implementa el problema multiobjetivo `LandscapeOptimizationProblem` usando `pymoo.algorithms.moo.nsga2.NSGA2` (población = 64, generaciones = 40). Evalúa 2 funciones objetivo a minimizar (`-crop_yield`, `-pollinator_abundance`) con restricciones de área ($\sum \text{coberturas} \le 100\%$ y área natural $\ge \text{mínimo}$). Usa un caché en memoria LRU de 900s (`TimedCache`).
- **`recommendation_service`** ([backend/app/services/recommendation_service.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/recommendation_service.py)): Genera explicabilidad de trade-offs agroecológicos. Dispone de un esquema en cascada de 3 niveles: 1) llamada HTTP a Langflow REST API (`/api/v1/run/...`), 2) fallback directo a Groq API con el template agronómico estructurado, 3) fallback heurístico determinista analítico basado en las cifras cuantitativas del frente de Pareto.
- **`chat_service`** ([backend/app/services/chat_service.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/chat_service.py)): Orquestador del chatbot con pre-retrieval dinámico contra PostgreSQL (consultas de simulaciones específicas por ID, conteo de simulaciones del usuario, usuarios activos con control estricto de roles RBAC). Soporta Groq LLM e implementa un motor de respuestas contextuales de base de datos (`gemelos-db-engine`) si `GROQ_API_KEY` no está provista.
- **`terrain_service`** ([backend/app/services/terrain_service.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/terrain_service.py)): Consulta elevación real en grilla 10x10 para el polígono delimitado. Consume Open-Elevation API como primera opción, Open-Meteo Elevation API como segunda opción y genera relieve plano en caso de indisponibilidad.
- **`report_general_service`** y **`report_general_export_service`** ([backend/app/services/report_general_service.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/report_general_service.py), [report_general_export_service.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/report_general_export_service.py)): Agregación estadística de simulaciones por periodo temporal, ranking de usuarios y generación de gráficos matplotlib renderizados en base64 para reportes ejecutivos.

---

## 4. Frontend (React 18 + Vite + TailwindCSS)

El frontend está implementado como una aplicación de una sola página (SPA) con carga diferida (`React.lazy`) y diseño responsivo adaptativo con modo oscuro e internacionalización.

### 4.1 Páginas y Mapeo de Rutas
Archivo de respaldo: [frontend/src/App.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/App.jsx)

| Ruta URL | Componente / Página | Rol Requerido | Funcionalidad |
| :--- | :--- | :--- | :--- |
| `/login` | [LoginPage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/LoginPage.jsx) | Público | Formulario de autenticación con email y contraseña |
| `/register` | [RegisterPage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/RegisterPage.jsx) | Público | Formulario de registro de nuevas cuentas cliente |
| `/client` | [ClientDashboard.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/ClientDashboard.jsx) (redirige a [ClientOptimizePage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/ClientOptimizePage.jsx)) | `cliente`, `admin` | Consola interactiva: mapa para dibujar lote, configuración de escenarios, ejecución y visualización de Pareto |
| `/client/history` | [ClientHistoryPage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/ClientHistoryPage.jsx) | `cliente`, `admin` | Tabla paginada de simulaciones del cliente con exportación de fichas PDF individuales |
| `/admin` | [AdminDashboard.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/AdminDashboard.jsx) (redirige a [AdminHomePage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/AdminHomePage.jsx)) | `admin` | Panel principal con KPIs globales, usuarios activos y distribución de parcelas por región |
| `/admin/users` | [AdminUsersPage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/AdminUsersPage.jsx) | `admin` | CRUD administrativo de usuarios (creación, edición de rol/estado, reseteo de clave, eliminación) |
| `/admin/simulations` | [AdminSimulationsPage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/AdminSimulationsPage.jsx) | `admin` | Auditoría global de simulaciones con filtros por fecha, región y usuario; exportación de reportes |
| `/admin/reports` | [AdminReportsPage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/AdminReportsPage.jsx) | `admin` | Reportes ejecutivos agregados: operativos y de gestión agronómica con exportación a PDF, Word y Excel |

### 4.2 Componentes UI Especializados
Archivos en [frontend/src/components/](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/components/):
- **`MapSelectionCard.jsx`**: Mapa interactivo Leaflet con Leaflet Draw. Permite dibujar polígonos agrícolas, calcula centroides y valida en tiempo real si el polígono cae dentro del radio de validez agroecológica del modelo entrenado.
- **`LandscapeDiorama3D.jsx`**: Maqueta 3D interactiva renderizada mediante Three.js (`@react-three/fiber` y `@react-three/drei`). Representa una grilla 10x10 donde las celdas reflejan la distribución proporcional de cultivos, área natural y franjas florales, deformadas verticalmente por la topografía real obtenida de la API de elevación.
- **`ResultsDashboard.jsx`**: Cuadro de mando de resultados que presenta:
  - Tarjetas de impacto: Delta de Rendimiento, Delta de Abundancia de Polinizadores, Cumplimiento de Hipótesis ($\ge 20\%$) y Estado de Caché.
  - Comparativa espacial en modo satélite 2D, diorama 3D o vista dual.
  - Gráfico de dispersión del Frente de Pareto (Recharts).
  - Tarjeta de desglose de la mejor solución y acordeón de recomendación agronómica explicable.
  - Gráfico de trayectoria temporal/evolutiva entre estado base y óptimo.
- **`ChatWidget.jsx`**: Asistente conversacional flotante disponible en todas las vistas protegidas. Soporta historial conversacional y atajos de consulta rápida.
- **`ReportExportBar.jsx`**: Barra de utilidades para exportar reportes ejecutivos en formatos PDF (jsPDF), Word (docx) y Excel (xlsx).

---

## 5. Entorno Científico y Pipeline de ML (Streamlit)

El laboratorio de modelado científico reside en [streamlit_app/](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/) y expone una interfaz visual alineada con las 6 fases de la metodología **CRISP-DM**.

### 5.1 Fases Metodológicas Implementadas
Archivo: [streamlit_app/app.py:149-191](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/app.py#L149-L191)

1. **Fase 1: Comprensión del Negocio (Business Understanding)**: Formalización de hipótesis científica ($+20\%$ polinizadores protegiendo rendimiento) y parámetros del problema.
2. **Fase 2: Comprensión de los Datos (Data Understanding)**: Análisis exploratorio (EDA), estadísticas descriptivas (T1-T3) y correlaciones bivariadas (F1-F3).
3. **Fase 3: Preparación de los Datos (Data Preparation)**:
   - Ingesta de 3 modalidades: 1) Sintético estocástico, 2) CSV propio del usuario, 3) Integración pública real (GBIF API + NASA POWER API).
   - Enriquecimiento opcional mediante simulación ABM (Mesa).
4. **Fase 4: Modelado (Modeling)**:
   - Comparativa de 5 arquitecturas: DNN Surrogate, Autoencoder+MLP, Random Forest, XGBoost y Ridge Regression.
   - Sintonización de hiperparámetros mediante RandomizedSearchCV y búsqueda de arquitecturas neuronales (NAS).
   - Validación cruzada K-Fold ($k=5$).
5. **Fase 5: Evaluación (Evaluation)**:
   - Protocolo estadístico inferencial riguroso: normalidad (Shapiro-Wilk), pruebas pareadas (T-Student, Wilcoxon), tamaño del efecto (D de Cohen con corrección de Bonferroni), varianza multimodelo global (Test de Friedman, T8/F10) y comparaciones post-hoc pareadas (Test de Nemenyi, T9/F11).
6. **Fase 6: Despliegue (Deployment)**:
   - Exportación del bundle `modelo_optimizado.h5` y `modelo_optimizado_metadata.json` al volumen compartido `/modelos_ia/` para su consumo inmediato por el backend FastAPI.
   - Descarga de reportes científicos en Excel (`openpyxl`), Word (`python-docx`) y PDF (`reportlab`).

### 5.2 Contrato de Variables del Dataset Científico
Archivo de respaldo: [streamlit_app/data_pipeline.py:10-25](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/data_pipeline.py#L10-L25)

#### Variables de Entrada (8 features):
1. `crop_area_pct`: Porcentaje de cobertura de cultivo agrícola ($[35, 82]\%$).
2. `natural_area_pct`: Porcentaje de vegetación natural o bosque conservado ($[8, 42]\%$).
3. `floral_strips_pct`: Porcentaje de bordes o franjas florales para polinizadores ($[2, 18]\%$).
4. `pesticide_level`: Nivel o índice de uso de agroquímicos/pesticidas ($[5, 95]$).
5. `soil_management_score`: Puntuación de prácticas de salud y conservación del suelo ($[35, 95]$).
6. `temperature_c`: Temperatura media ambiental ($^\circ\text{C}$).
7. `precipitation_mm`: Precipitación anual acumulada ($\text{mm}$).
8. `landscape_diversity`: Índice de heterogeneidad espacial del paisaje ($[0.2, 0.95]$).

#### Variables Objetivo (3 targets):
1. `crop_yield_index`: Índice de rendimiento productivo del cultivo agrícola.
2. `pollinator_abundance_index`: Índice de abundancia poblacional de polinizadores.
3. `pollinator_diversity_index`: Índice de riqueza o diversidad de especies polinizadoras.

### 5.3 Simulación Basada en Agentes (ABM)
Archivo de respaldo: [streamlit_app/pollinator_abm.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/pollinator_abm.py)
- Framework: `mesa 2.3.4` (`Agent`, `Model`, `MultiGrid`, `RandomActivation`).
- Modelo: `PollinatorLandscapeModel`.
- Comportamiento del agente `PollinatorAgent`:
  - Desplazamiento en vecindad de Moore hacia celdas con mayor oferta de recursos florales.
  - Consumo de energía y penalización por exposición a agroquímicos (`hazard_map`).
  - Dinámica demográfica: reproducción asexual/división si la energía supera 6.2 unidades bajo probabilidad dependiente de la diversidad paisajística; muerte por inanición o toxicidad si la energía desciende de 0.35.

---

## 6. Orquestación de Agentes con Langflow

Archivo de respaldo: [langflow/flows/asistente_recomendaciones_agroecologicas.json](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/langflow/flows/asistente_recomendaciones_agroecologicas.json)

- Contenedor: `langflowai/langflow:latest` en el puerto 7860.
- Componentes del flujo:
  1. `DatosOptimizacionInput`: Nodo de entrada que recibe el payload con `frente_pareto`, `solucion_elegida` y `linea_base`.
  2. `ParetoTradeoffFormatter`: Componente Python personalizado que procesa las métricas extremas del frente (máximo rendimiento vs. máxima biodiversidad) y calcula los deltas porcentuales.
  3. `PromptTemplateAgroecologico`: Genera la instrucción con las directrices de fundamentación agronómica para el LLM.
  4. `GroqLLMComponent`: Ejecuta la inferencia en `llama-3.1-70b-versatile` para redactar la justificación técnica en 3 párrafos compactos.

---

## 7. Pruebas y Scripts de Validación Existentes

Archivo de respaldo: inspección de estructura del repositorio

| Archivo | Tipo de Prueba / Propósito | Estado de Ejecución en este Análisis |
| :--- | :--- | :--- |
| [streamlit_app/robust_tests.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/robust_tests.py) | Pruebas estadísticas inferenciales multimodelo integradas en la UI de Streamlit | `[CÓDIGO]` Inspeccionado estáticamente. **No ejecutado**. |
| [streamlit_app/test_traceability_pipeline.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/test_traceability_pipeline.py) | Script autónomo de prueba empírica del pipeline sintético y público con exportación y verificación de `/health` | `[CÓDIGO]` Inspeccionado estáticamente. **No ejecutado**. |
| [streamlit_app/test_tuning_benchmark.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/test_tuning_benchmark.py) | Benchmark comparativo de tiempos y desempeño: modo fijo vs. modo con hyperparameter tuning | `[CÓDIGO]` Inspeccionado estáticamente. **No ejecutado**. |
| [scratch/test_nemenyi.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/scratch/test_nemenyi.py) | Script de prueba aislado para validación del cálculo de la matriz de p-valores de Nemenyi | `[CÓDIGO]` Inspeccionado estáticamente. **No ejecutado**. |
| Suite de Pruebas Unitarias Backend (`pytest`) | No existe directorio `tests/` ni configuración en `backend/` | `[VERIFICAR]` **Ausente** en el repositorio. |
| Suite de Pruebas Frontend (`jest`/`vitest`) | No hay scripts de test ni dependencias de pruebas en `frontend/package.json` | `[VERIFICAR]` **Ausente** en el repositorio. |
| CI/CD Automated Pipelines | No hay directorio `.github/workflows/` configurado | `[VERIFICAR]` **Ausente** en el repositorio. |

---

## 8. Documentos Existentes en el Repositorio

| Archivo | Tipo | Resumen del Contenido |
| :--- | :--- | :--- |
| [README.md](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/README.md) | Markdown | Descripción del monorepo, fases 1 a 4, instrucciones de arranque, endpoints declarados y notas de auditoría científica. |
| [metadata.json](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/metadata.json) | JSON | Identificador del proyecto: "Gemelos Digitales - Polinizadores" y capacidades declaradas. |
| [CAMBIOS_FUTUROS.md](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/CAMBIOS_FUTUROS.md) | Markdown | Especificación técnica de mejoras pendientes: zoom 2D, gestión general en admin y bloque de "Plan de Acción Recomendado". |
| [CODIGO_COMPLETO_PROYECTO.md](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/CODIGO_COMPLETO_PROYECTO.md) | Markdown (~840 KB) | Consolidación exhaustiva del código fuente del proyecto para auditoría. |
| [CODIGO_COMPLETO_PROYECTO.docx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/CODIGO_COMPLETO_PROYECTO.docx) | Word binario (~230 KB) | Versión Word del consolidado de código del proyecto. |
| [CODIGO_COMPLETO_PROYECTO_GEMELOS_DIGITALES.md](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/CODIGO_COMPLETO_PROYECTO_GEMELOS_DIGITALES.md) | Markdown (~840 KB) | Duplicado del archivo consolidado de código del proyecto. |
| [CODIGO_COMPLETO_PROYECTO_GEMELOS_DIGITALES.docx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/CODIGO_COMPLETO_PROYECTO_GEMELOS_DIGITALES.docx) | Word binario (~230 KB) | Duplicado en formato Word del archivo consolidado de código. |
| [EJEMPLO_DE_OTRO_PROYECTO.docx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/EJEMPLO_DE_OTRO_PROYECTO.docx) | Word binario (~214 KB) | Documento de referencia de estructura o formato de otro proyecto previo. |
| [LICENSE](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/LICENSE) | Texto | Licencia de código abierto MIT aplicable al código fuente desarrollado. |

---

## 9. Contraste Exhaustivo: README.md vs. Código Actual

| Aspecto Declarado en README.md | Realidad Observada en el Código Fuente | Estado | Discrepancia / Detalle Técnico |
| :--- | :--- | :--- | :--- |
| **Servicios Docker** (L5-10): Declara 4 servicios (`frontend`, `backend`, `streamlit`, `db`). | Existen 5 servicios activos en [docker-compose.yml](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/docker-compose.yml#L1-L87): `db`, `backend`, `frontend`, `streamlit` y **`langflow`**. | `Desactualizado` | README no menciona el contenedor `langflow` ni su volumen `langflow_data`. |
| **Conector GBIF** (L64): Declara uso de conector `pygbif`. | [streamlit_app/data_pipeline.py:165-186](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/data_pipeline.py#L165-L186) utiliza la librería estándar `requests` consultando directamente la API REST pública de GBIF (`api.gbif.org`). `pygbif` no está en [requirements.txt](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/requirements.txt). | `Discrepancia de implementación` | La funcionalidad existe pero la biblioteca declarada en el documento no es la usada. |
| **Conector ERA5** (L65): Declara conector preparado para ERA5 con `cdsapi`. | La función `fetch_era5_climate_timeseries` existe ([data_pipeline.py:443-463](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/data_pipeline.py#L443-L463)), pero `cdsapi` no está instalado en `requirements.txt` y requiere archivo `.cdsapirc` externo. | `Parcial / No ejecutable directo` | Requiere dependencias y credenciales de Copernicus no provistas. En su lugar se implementó `fetch_nasa_power_climate`. |
| **Conector Sentinel-2** (L66): Declara conectores para Earth Engine y Sentinel-2 con `earthengine-api` y `geemap`. | La función `fetch_land_use_snapshot` existe ([data_pipeline.py:466-486](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/data_pipeline.py#L466-L486)), pero ni `earthengine-api` ni `geemap` están en `requirements.txt` y requiere token de cuenta Google Earth Engine. | `Parcial / No ejecutable directo` | Requiere autenticación externa no incluida en el contenedor. |
| **Inventario de Endpoints Backend** (L131-150): Lista 17 endpoints. | El backend implementa **25 endpoints** reales. No están listados en el README: `/api/admin/reports/operational`, `/api/admin/reports/management`, `/api/admin/reports/operational/export`, `/api/admin/reports/management/export`, `/api/model/region-check`, `/api/terrain/elevation-grid`, `/api/admin/ping`, `/api/client/ping`. | `Incompleto en documento` | Los módulos de reportes administrativos agregados y elevación topográfica se agregaron con posterioridad al README. |
| **Páginas del Frontend** (L153-166): Menciona flujo cliente, historial, chatbot y panel admin. | Se implementaron además: Diorama 3D con Three.js ([LandscapeDiorama3D.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/components/LandscapeDiorama3D.jsx)), verificación espacial anti Domain Shift, y página completa de reportes agregados con exportación multiplataforma ([AdminReportsPage.jsx](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/frontend/src/pages/AdminReportsPage.jsx)). | `Enriquecido en código` | El frontend cuenta con más capacidades que las resumidas en el documento. |
| **Carpeta Consolidada de Auditoría** (L208-212): Cita la carpeta local `respaldo_surrogate_20261008_221709/` y scripts en `scripts_auditoria/`. | Ninguna de estas carpetas ni los scripts (`predict_baselines.py`, `prepare_files.py`, `generar_documentacion.py`) existen dentro del repositorio Git ni en el árbol de archivos rastreados. | `No disponible en repo` | Los materiales se conservaron de forma externa y no forman parte del repositorio actual. |

---

## 10. Materiales Externos Necesarios para la Reproducción Científica

Para una reproducción íntegra e independiente del ciclo científico completo (desde el reentrenamiento y validación estadística hasta la optimización NSGA-II), se requieren los siguientes insumos externos no alojados en el repositorio:

| Recurso Externo Requerido | Función en el Flujo Científico | ¿Disponible en Repositorio? | Mecanismo Alternativo o Sustituto Disponible |
| :--- | :--- | :--- | :--- |
| **Modelo base preservado `surrogate_20261008_221709`** | Inferencia del surrogate para evaluación sin necesidad de reentrenar | ❌ No disponible en Git (declarado en README L209 como local externo) | Puede reentrenarse un nuevo modelo surrogate desde Streamlit o generarse vía [streamlit_app/test_traceability_pipeline.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/test_traceability_pipeline.py). |
| **Scripts de auditoría del artículo (`scripts_auditoria/`)** | `predict_baselines.py`, `prepare_files.py`, `generar_documentacion.py` | ❌ No disponibles en Git | Funcionalidad equivalente de predicción de línea base se encuentra en [optimization.py:118-148](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/optimization.py#L118-L148). |
| **Credenciales de Copernicus (`.cdsapirc`)** | Descarga de reanálisis climático ERA5 horario | ❌ No disponibles | Sustituido de forma operativa por la API pública gratuita de NASA POWER ([data_pipeline.py:222-286](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/data_pipeline.py#L222-L286)). |
| **Credenciales de Google Earth Engine** | Extracción de imágenes medianas Sentinel-2 | ❌ No disponibles | El pipeline permite usar matrices sintéticas o polígonos geoespaciales interactivos en Leaflet sin bloquear el flujo. |
| **Clave de API Groq (`GROQ_API_KEY`)** | Generación de recomendaciones explicables enriquecidas y chatbot con LLM | ❌ No incluida (esperada en variable de entorno) | Tanto [recommendation_service.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/recommendation_service.py) como [chat_service.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/chat_service.py) disponen de un motor de fallback determinista 100% funcional sin clave externa. |
| **Servicio Open-Elevation / Open-Meteo** | Provisión de cotas altimétricas para el Diorama 3D | 🌐 Servicio web público externo | Si la API externa no responde o falla la red, [terrain_service.py:203-231](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/backend/app/services/terrain_service.py#L203-L231) conmuta automáticamente a una grilla plana de respaldo. |
| **Base de datos desagregada por fold de MAEs históricos** | Recálculo independiente de pruebas de Friedman y Nemenyi reportadas en el Excel de respaldo | ❌ No disponible en la versión final (declarado en README L224) | El entorno Streamlit ([robust_tests.py](file:///c:/Users/Daniel/Downloads/gemelo-documentacion/streamlit_app/robust_tests.py)) recalcula en vivo las pruebas completas al ejecutar un nuevo entrenamiento con K-Fold. |

---
*Fin del documento de inventario técnico. Generado para la rama `docs/automatizacion-confluence` bajo el commit `0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`.*
