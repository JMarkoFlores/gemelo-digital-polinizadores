# Especificación y Catálogo de la API REST

**Documento:** `docs/api.md`  
**Referencia del commit analizado:** [`0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`](https://github.com/JMarkoFlores/gemelo-digital-polinizadores/commit/0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02)  
**Evidencia principal:** [backend/app/main.py](../backend/app/main.py), [backend/app/routers/admin_reports.py](../backend/app/routers/admin_reports.py), [backend/app/schemas.py](../backend/app/schemas.py), [backend/app/schemas_reports.py](../backend/app/schemas_reports.py)

---

## 1. Resumen y Conteo de Endpoints

El backend FastAPI expone un total de **28 rutas** por combinación única de método HTTP y URI, organizadas en dos categorías:

- **Rutas Propias de la Aplicación:** **25 endpoints** (21 definidos en `main.py` y 4 incorporados mediante el router `admin_reports.py`).
- **Rutas Autogeneradas por FastAPI:** **3 endpoints** destinados a la documentación interactiva OpenAPI y especificación JSON.

---

## 2. Autenticación y Convenciones de Acceso

Las solicitudes a rutas protegidas deben incluir la cabecera HTTP estándar:
```http
Authorization: Bearer <token_jwt>
```
El token se obtiene a través de `POST /api/auth/login` o `POST /api/auth/register`. La autorización de roles (RBAC) se evalúa mediante la dependencia `require_role(...)` ([backend/app/dependencies.py](../backend/app/dependencies.py)).

Códigos de estado HTTP devueltos por la API:
- `200 OK`: Solicitud procesada exitosamente.
- `201 Created`: Recurso creado exitosamente (usuarios, registros).
- `400 Bad Request`: Error en parámetros de entrada, geometría no válida o payload malformado.
- `401 Unauthorized`: Token ausente, inválido, expirado o credenciales erróneas.
- `403 Forbidden`: Permisos insuficientes para el rol de usuario o acceso a simulaciones ajenas.
- `404 Not Found`: Recurso no encontrado en base de datos.
- `409 Conflict`: Conflicto de unicidad (ej. correo electrónico ya registrado).
- `503 Service Unavailable`: Metamodelo IA no cargado en memoria o servicio analítico no disponible.

---

## 3. Catálogo de Rutas Propias de la Aplicación (25 Endpoints)

### 3.1 Módulo de Autenticación y Perfil
Archivo: [backend/app/main.py:110-140](../backend/app/main.py#L110-L140)

#### 1. `POST /api/auth/register`
- **Finalidad:** Registra una nueva cuenta de usuario en el sistema.
- **Autenticación requerida:** Pública (sin token).
- **Esquema de Entrada:** [UserRegister](../backend/app/schemas.py#L7-L10) (`email`: EmailStr, `password`: str $\ge 8$, `rol`: "cliente" \| "admin" — nota: el código fuerza rol "cliente" por seguridad aunque se solicite admin).
- **Esquema de Salida:** [TokenResponse](../backend/app/schemas.py#L42-L46) (`access_token`: str, `token_type`: "bearer", `user`: [UserResponse](../backend/app/schemas.py#L32-L40)).
- **Código de Estado:** `201 Created` (o `409 Conflict` si el email ya existe).

#### 2. `POST /api/auth/login`
- **Finalidad:** Autentica credenciales de usuario y genera el token de sesión JWT.
- **Autenticación requerida:** Pública (sin token).
- **Esquema de Entrada:** [UserLogin](../backend/app/schemas.py#L13-L16) (`email`: EmailStr, `password`: str).
- **Esquema de Salida:** [TokenResponse](../backend/app/schemas.py#L42-L46).
- **Códigos de Estado:** `200 OK`, `401 Unauthorized` (credenciales inválidas), `403 Forbidden` (usuario inactivo).

#### 3. `GET /api/auth/me`
- **Finalidad:** Retorna los datos de identidad y rol del usuario actualmente autenticado.
- **Autenticación requerida:** Bearer Token (Cualquier rol activo).
- **Esquema de Entrada:** Ninguno (lee token en cabecera).
- **Esquema de Salida:** [UserResponse](../backend/app/schemas.py#L32-L40) (`id`, `email`, `rol`, `activo`, `fecha_creacion`).
- **Código de Estado:** `200 OK`.

---

### 3.2 Módulo de Gestión del Metamodelo IA y Prevención de Sesgo Espacial
Archivo: [backend/app/main.py:141-182](../backend/app/main.py#L141-L182)

#### 4. `POST /api/model/reload`
- **Finalidad:** Fuerza al backend a releer el archivo binario `modelo_optimizado.h5` y `modelo_optimizado_metadata.json` desde `/modelos_ia/` sin reiniciar el contenedor.
- **Autenticación requerida:** Bearer Token (Roles: `admin`, `cliente`).
- **Esquema de Entrada:** Ninguno.
- **Esquema de Salida:** `dict` (`model_ready`, `model_status`, `model_version`, `fuente_datos`, `region_name`, `region_bounds`, `data_source_summary`).
- **Código de Estado:** `200 OK`.

#### 5. `GET /api/model/status`
- **Finalidad:** Consulta el estado operativo del metamodelo en memoria, su procedencia y límites territoriales.
- **Autenticación requerida:** Bearer Token (Roles: `admin`, `cliente`).
- **Esquema de Entrada:** Ninguno.
- **Esquema de Salida:** `dict` (`model_ready`, `model_status`, `model_version`, `fuente_datos`, `region_name`, `region_bounds`, `data_source_summary`, `requested_by`).
- **Código de Estado:** `200 OK`.

#### 6. `GET /api/model/region-check`
- **Finalidad:** Evalúa si las coordenadas de un punto o centroide de parcela caen dentro del radio agroecológico para el que fue calibrado el modelo, alertando ante riesgos de *Domain Shift*.
- **Autenticación requerida:** Bearer Token (Roles: `admin`, `cliente`).
- **Parámetros Query:**
  - `lat`: float (Latitud a validar).
  - `lon`: float (Longitud a validar).
  - `tolerance`: float (Margen sobre el radio máximo, default 0.2 [0.0 a 1.0]).
- **Esquema de Salida:** `dict` (`has_restriction`: bool, `is_valid`: bool, `distance_km`: float, `allowed_radius_km`: float, `max_radius_with_tolerance_km`: float, `region_name`: str, `message`: str).
- **Código de Estado:** `200 OK`.

---

### 3.3 Módulo de Topografía y Elevación Real
Archivo: [backend/app/main.py:183-192](../backend/app/main.py#L183-L192)

#### 7. `POST /api/terrain/elevation-grid`
- **Finalidad:** Consulta elevación topográfica real en una grilla de 10x10 puntos sobre el polígono para alimentar la maqueta 3D (Open-Elevation API / Open-Meteo).
- **Autenticación requerida:** Bearer Token (Roles: `admin`, `cliente`).
- **Esquema de Entrada:** [TerrainElevationRequest](../backend/app/schemas.py#L149-L152) (`geometry`: GeoJSON dict opcional, `bbox`: list[float] de 4 elementos opcional).
- **Esquema de Salida:** [TerrainElevationResponse](../backend/app/schemas.py#L154-L166) (`available`: bool, `source`: str, `min_elevation_m`, `max_elevation_m`, `elevation_range_m`, `mean_elevation_m`, `grid`: list[[ElevationCell](../backend/app/schemas.py#L139-L147)], `matrix`: list[list[float]], `normalized_matrix`: list[list[float]], `message`: str).
- **Código de Estado:** `200 OK`.

---

### 3.4 Módulo de Simulación y Optimización Multiobjetivo
Archivo: [backend/app/main.py:193-254](../backend/app/main.py#L193-L254)

#### 8. `POST /api/simular`
- **Finalidad:** Valida la zona geográfica, evalúa el estado base, ejecuta el algoritmo **NSGA-II** (`pymoo`), selecciona la solución óptima de compromiso, genera recomendaciones agroecológicas (Langflow/IA) y persiste el resultado en PostgreSQL.
- **Autenticación requerida:** Bearer Token (Roles: `cliente`, `admin`).
- **Esquema de Entrada:** [SimulationRequest](../backend/app/schemas.py#L73-L79) (`geometry`: dict opcional, `bbox`: list[float] opcional, `pesticide_level`: float [0-100], `min_natural_area_pct`: float [0-100], `climate_scenario`: "current" \| "warm" \| "dry" \| "extreme").
- **Esquema de Salida:** [SimulationResultPayload](../backend/app/schemas.py#L95-L107) (`baseline`: dict, `pareto_front`: list[[SimulationCandidate](../backend/app/schemas.py#L81-L93)], `best_solution`: dict, `optimized_landscape`: dict, `delta_yield`: float, `delta_pollinators`: float, `hypothesis_status`: str, `model_version`: str, `cache_hit`: bool, `recomendacion_ia`: str).
- **Códigos de Estado:** `200 OK`, `400 Bad Request` (geometría inválida o fuera de rango agroecológico), `503 Service Unavailable` (modelo no cargado).

#### 9. `GET /api/simulations/me`
- **Finalidad:** Retorna el listado histórico paginado de simulaciones pertenecientes al usuario autenticado.
- **Autenticación requerida:** Bearer Token (Roles: `cliente`, `admin`).
- **Parámetros Query:** `page` (int $\ge 1$, default 1), `page_size` (int [1-100], default 10).
- **Esquema de Salida:** [PaginatedResponse](../backend/app/schemas.py#L48-L53) con items de tipo [SimulationResponse](../backend/app/schemas.py#L55-L66).
- **Código de Estado:** `200 OK`.

#### 10. `GET /api/simulations/me/{simulation_id}`
- **Finalidad:** Obtiene el detalle completo y frente de Pareto de una simulación específica.
- **Autenticación requerida:** Bearer Token (Roles: `cliente`, `admin`). Valida que la simulación pertenezca al usuario (o que el usuario sea administrador).
- **Parámetros Path:** `simulation_id` (int).
- **Esquema de Salida:** [SimulationResponse](../backend/app/schemas.py#L55-L66).
- **Códigos de Estado:** `200 OK`, `403 Forbidden` (simulación de otro usuario), `404 Not Found`.

---

### 3.5 Módulo de Asistencia Inteligente y Chatbot
Archivo: [backend/app/main.py:368-385](../backend/app/main.py#L368-L385)

#### 11. `POST /api/chat`
- **Finalidad:** Asistente conversacional agroecológico con pre-retrieval contra PostgreSQL y control estricto de roles.
- **Autenticación requerida:** Bearer Token (Roles: `cliente`, `admin`).
- **Esquema de Entrada:** [ChatRequest](../backend/app/schemas.py#L115-L118) (`message`: str [1-2000 chars], `history`: list[[ChatMessage](../backend/app/schemas.py#L110-L113)]).
- **Esquema de Salida:** [ChatResponse](../backend/app/schemas.py#L120-L123) (`reply`: str en Markdown, `model`: str).
- **Código de Estado:** `200 OK`.

---

### 3.6 Módulo de Administración y Gestión de Usuarios
Archivo: [backend/app/main.py:255-367](../backend/app/main.py#L255-L367)

#### 12. `GET /api/admin/dashboard`
- **Finalidad:** Retorna métricas globales de la plataforma: total de usuarios, usuarios activos, simulaciones del mes en curso y ranking de las 5 regiones con más actividad.
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Esquema de Salida:** [AdminDashboardResponse](../backend/app/schemas.py#L132-L137).
- **Código de Estado:** `200 OK`.

#### 13. `GET /api/admin/users`
- **Finalidad:** Lista paginada de todos los usuarios registrados con soporte de búsqueda por correo.
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Query:** `page` (int, default 1), `page_size` (int, default 10), `search` (str opcional).
- **Esquema de Salida:** [PaginatedResponse](../backend/app/schemas.py#L48-L53) con items [UserResponse](../backend/app/schemas.py#L32-L40).
- **Código de Estado:** `200 OK`.

#### 14. `POST /api/admin/users`
- **Finalidad:** Creación administrativa directa de usuarios con asignación explícita de rol.
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Esquema de Entrada:** [UserCreate](../backend/app/schemas.py#L18-L23) (`email`, `password` $\ge 8$, `rol`: "cliente" \| "admin", `activo`: bool).
- **Esquema de Salida:** [UserResponse](../backend/app/schemas.py#L32-L40).
- **Código de Estado:** `201 Created` (o `409 Conflict`).

#### 15. `PUT /api/admin/users/{user_id}`
- **Finalidad:** Actualización de atributos de un usuario (email, rol, estado activo o reseteo de contraseña).
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Path:** `user_id` (int).
- **Esquema de Entrada:** [UserUpdate](../backend/app/schemas.py#L25-L30) (todos los campos opcionales).
- **Esquema de Salida:** [UserResponse](../backend/app/schemas.py#L32-L40).
- **Código de Estado:** `200 OK` (o `404 Not Found`).

#### 16. `DELETE /api/admin/users/{user_id}`
- **Finalidad:** Eliminación de una cuenta de usuario y borrado en cascada de sus simulaciones asociadas.
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Path:** `user_id` (int).
- **Esquema de Salida:** `dict` (`deleted`: True, `user_id`: int).
- **Código de Estado:** `200 OK` (o `404 Not Found`).

#### 17. `GET /api/admin/simulations`
- **Finalidad:** Auditoría global de simulaciones en la plataforma con filtros multicriterio por usuario, región y rango de fechas.
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Query:** `page`, `page_size`, `user_id`, `region`, `start_date`, `end_date`.
- **Esquema de Salida:** [PaginatedResponse](../backend/app/schemas.py#L48-L53) con items [SimulationResponse](../backend/app/schemas.py#L55-L66).
- **Código de Estado:** `200 OK`.

#### 18. `GET /api/admin/simulations/{simulation_id}/report`
- **Finalidad:** Genera el payload de contexto enriquecido para la exportación individual de una simulación desde la vista de administración.
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Path:** `simulation_id` (int).
- **Esquema de Salida:** `dict` (`simulation`: SimulationResponse, `user`: UserResponse, `report_context`: dict).
- **Código de Estado:** `200 OK`.

---

### 3.7 Módulo de Reportes Ejecutivos Agregados
Archivo: [backend/app/routers/admin_reports.py:21-143](../backend/app/routers/admin_reports.py#L21-L143)

#### 19. `GET /api/admin/reports/operational`
- **Finalidad:** Genera métricas agregadas operativas sobre el uso del sistema (tendencia temporal acumulada, ranking de usuarios más activos y distribución geográfica de parcelas).
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Query:** `fecha_inicio`, `fecha_fin`, `region`, `usuario_id`, `periodo` ("dia" \| "semana" \| "mes").
- **Esquema de Salida:** [OperationalReportResponse](../backend/app/schemas_reports.py#L45-L51).
- **Código de Estado:** `200 OK`.

#### 20. `GET /api/admin/reports/management`
- **Finalidad:** Genera informe de gestión agronómica agregada (rendimientos promedio base vs. óptimo, ganancias ecológicas de polinizadores, tasa de cumplimiento de la hipótesis $\ge 20\%$ y top configuraciones no dominadas).
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Query:** `fecha_inicio`, `fecha_fin`, `region`, `usuario_id`, `top_n` (int [1-50], default 10).
- **Esquema de Salida:** [ManagementReportResponse](../backend/app/schemas_reports.py#L111-L117).
- **Código de Estado:** `200 OK`.

#### 21. `GET /api/admin/reports/operational/export`
- **Finalidad:** Retorna el payload enriquecido del reporte operativo incluyendo figuras renderizadas por Matplotlib codificadas en Base64 (`trend_chart_base64`, `regions_chart_base64`).
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Query:** Filtros operacionales (`fecha_inicio`, `fecha_fin`, `region`, `usuario_id`, `periodo`).
- **Esquema de Salida:** `dict` (`report_type`: "operational", `data`: dict, `charts`: dict, `report_context`: dict).
- **Código de Estado:** `200 OK`.

#### 22. `GET /api/admin/reports/management/export`
- **Finalidad:** Retorna el payload enriquecido del reporte de gestión incluyendo gráficos estadísticos en Base64 (`evolution_chart_base64`, `regional_chart_base64`).
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Parámetros Query:** Filtros de gestión (`fecha_inicio`, `fecha_fin`, `region`, `usuario_id`, `top_n`).
- **Esquema de Salida:** `dict` (`report_type`: "management", `data`: dict, `charts`: dict, `report_context`: dict).
- **Código de Estado:** `200 OK`.

---

### 3.8 Módulo de Healthchecks y Sondeo de Red
Archivo: [backend/app/main.py:95-108](../backend/app/main.py#L95-L108) y [main.py:386-394](../backend/app/main.py#L386-L394)

#### 23. `GET /health`
- **Finalidad:** Comprobación de salud pública e informe del estado del metamodelo cargado en memoria.
- **Autenticación requerida:** Pública (sin token).
- **Esquema de Salida:** `dict` (`status`: "ok", `service`: "backend", `model_ready`: bool, `model_version`: str, `model_status`: str, `fuente_datos`: str, `region_name`: str, `region_bounds`: dict).
- **Código de Estado:** `200 OK`.

#### 24. `GET /api/admin/ping`
- **Finalidad:** Comprobación rápida de conectividad y validez de credenciales con alcance de administrador.
- **Autenticación requerida:** Bearer Token (Rol exclusivo: `admin`).
- **Esquema de Salida:** `{"status": "ok", "scope": "admin"}`.
- **Código de Estado:** `200 OK`.

#### 25. `GET /api/client/ping`
- **Finalidad:** Comprobación rápida de conectividad y validez de credenciales con alcance de cliente.
- **Autenticación requerida:** Bearer Token (Roles: `cliente`, `admin`).
- **Esquema de Salida:** `{"status": "ok", "scope": "client"}`.
- **Código de Estado:** `200 OK`.

---

## 4. Rutas Autogeneradas por FastAPI para Documentación (3 Rutas)

FastAPI registra de forma automática estas rutas en tiempo de inicialización de la aplicación ([backend/app/main.py:62](../backend/app/main.py#L62)):

| Método | Ruta | Finalidad Técnica | Autenticación | Esquema / Formato de Salida |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/docs` | Interfaz interactiva Swagger UI para exploración y ejecución de peticiones REST. | Pública | HTML / JavaScript (Swagger UI CDN) |
| `GET` | `/redoc` | Documentación técnica estática basada en ReDoc. | Pública | HTML / JavaScript (ReDoc CDN) |
| `GET` | `/openapi.json` | Especificación formal del esquema de la API conforme al estándar OpenAPI 3.1. | Pública | Objeto JSON con esquemas de rutas y modelos Pydantic |
