# Guía de Configuración del Sistema

**Documento:** `docs/configuracion.md`  
**Referencia del commit analizado:** [`0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`](https://github.com/JMarkoFlores/gemelo-digital-polinizadores/commit/0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02)  
**Evidencia principal:** [.env.example](../.env.example), [backend/app/config.py](../backend/app/config.py), [docker-compose.yml](../docker-compose.yml), [docker-compose.prod.yml](../docker-compose.prod.yml), [streamlit_app/.streamlit/config.toml](../streamlit_app/.streamlit/config.toml), [frontend/vite.config.js](../frontend/vite.config.js)

---

## 1. Principios de Seguridad y Manejo de Secretos

> **Regla de Seguridad Estricta:**  
> Las credenciales de acceso, contraseñas de bases de datos, claves de cifrado simétrico y tokens de APIs externas (como Groq) se clasifican como **configuración externa confidencial**.  
> **Nunca se deben almacenar secretos en texto plano dentro del repositorio, imágenes de Docker ni en la documentación técnica.** Todos los valores sensibles deben inyectarse en tiempo de despliegue mediante archivos `.env` locales protegidos o administradores de secretos (como AWS Secrets Manager, HashiCorp Vault o Kubernetes Secrets).

---

## 2. Matriz de Variables de Entorno

La siguiente tabla consolida todas las variables reconocidas por el backend FastAPI, el frontend React, el laboratorio Streamlit, Langflow y PostgreSQL, basadas en [backend/app/config.py](../backend/app/config.py) y [docker-compose.yml](../docker-compose.yml).

| Variable de Entorno | Servicios Consumidores | Propósito Técnico | ¿Es Obligatoria? | Valor por Defecto / Formato Esperado | Tipo de Dato / Clasificación |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | `backend` | URI de conexión para SQLAlchemy hacia PostgreSQL. | Obligatoria | `postgresql+psycopg2://usuario:password@host:5432/nombre_db` | Configuración de Red / Credencial Externa |
| `POSTGRES_DB` | `db` | Nombre de la base de datos relacional inicial. | Obligatoria en `db` | `gemelos_db` | Identificador de Sistema |
| `POSTGRES_USER` | `db` | Usuario administrador del motor PostgreSQL. | Obligatoria en `db` | `gemelos_user` | Credencial Externa |
| `POSTGRES_PASSWORD` | `db` | Contraseña del usuario PostgreSQL. | Obligatoria en `db` | Cadena alfanumérica robusta | Secreto Externo |
| `JWT_SECRET` | `backend` | Clave criptográfica para firmar y verificar tokens de sesión Bearer. | Obligatoria en Producción | Cadena secreta de alta entropía (mínimo 32 caracteres) | Secreto Criptográfico |
| `JWT_ALGORITHM` | `backend` | Algoritmo criptográfico simétrico para la firma JWT. | Opcional | `HS256` | Algoritmo Criptográfico |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `backend` | Duración de validez de la sesión autenticada en minutos. | Opcional | `60` | Entero (Minutos) |
| `ADMIN_EMAIL` | `backend` | Correo electrónico asignado al usuario administrador sembrado. | Obligatoria | Formato de correo válido (ej. `admin@empresa.com`) | Identificador de Usuario |
| `ADMIN_PASSWORD` | `backend` | Contraseña inicial para el usuario con rol `admin` ([seed.py](../backend/app/seed.py)). | Obligatoria | Cadena que cumpla política de seguridad (mínimo 8 caracteres) | Secreto Externo |
| `CLIENT_EMAIL` | `backend` | Correo electrónico asignado al usuario cliente inicial sembrado. | Obligatoria | Formato de correo válido (ej. `cliente@empresa.com`) | Identificador de Usuario |
| `CLIENT_PASSWORD` | `backend` | Contraseña inicial para el usuario con rol `cliente` ([seed.py](../backend/app/seed.py)). | Obligatoria | Cadena que cumpla política de seguridad (mínimo 8 caracteres) | Secreto Externo |
| `CORS_ORIGINS` | `backend` | Lista separada por comas de orígenes permitidos por CORS. | Opcional | `http://localhost:5173,http://127.0.0.1:5173` | Lista de URLs / Seguridad Web |
| `GROQ_API_KEY` | `backend`, `langflow` | Llave de API para el servicio de inferencia LLM en la nube de Groq. | Opcional (dispone de fallback local) | Token de API proporcionado por Groq Cloud (`gsk_...`) | Secreto Externo / API Key |
| `GROQ_MODEL` | `backend` | Modelo LLM invocado para chatbot y explicabilidad agroecológica. | Opcional | `llama-3.1-70b-versatile` | Identificador de Modelo |
| `LANGFLOW_URL` | `backend` | URL interna resoluble en red Docker para invocar la API REST de Langflow. | Opcional | `http://langflow:7860` | URL Interna de Red |
| `LANGFLOW_FLOW_ID` | `backend` | Identificador único del flujo ejecutado en Langflow. | Opcional | `asistente-recomendaciones-agroecologicas` | Identificador de Flujo |
| `LANGFLOW_PORT` | Host / Docker | Puerto del host mapeado al puerto 7860 de Langflow. | Opcional | `7860` | Entero (Puerto TCP) |
| `BACKEND_PORT` | Host / Docker | Puerto del host mapeado al servicio FastAPI. | Opcional | `8000` | Entero (Puerto TCP) |
| `FRONTEND_PORT` | Host / Docker | Puerto del host mapeado al servidor web de la interfaz. | Opcional | `5173` | Entero (Puerto TCP) |
| `STREAMLIT_PORT` | Host / Docker | Puerto del host mapeado a la aplicación Streamlit. | Opcional | `8501` | Entero (Puerto TCP) |
| `VITE_API_BASE_URL` | `frontend` | URL base que el cliente HTTP (Axios) utiliza para consultar el backend. | Opcional | `http://localhost:8000` (desarrollo) / `/api` (producción con proxy) | URL de API Pública |
| `MODEL_DIR` | `backend`, `streamlit` | Directorio montado del volumen compartido donde reside el binario `.h5`. | Opcional | `/modelos_ia` | Ruta de Sistema de Archivos |
| `MODEL_FILENAME` | `backend` | Nombre de archivo del metamodelo Keras entrenado. | Opcional | `modelo_optimizado.h5` | Nombre de Archivo |
| `MODEL_METADATA_FILENAME` | `backend` | Nombre de archivo con metadatos JSON y escaladores del modelo. | Opcional | `modelo_optimizado_metadata.json` | Nombre de Archivo |
| `CACHE_TTL_SECONDS` | `backend` | Tiempo de vida en segundos para la caché en memoria de soluciones Pareto. | Opcional | `900` (15 minutos) | Entero (Segundos) |
| `CACHE_MAX_ITEMS` | `backend` | Número máximo de soluciones retenidas en el caché LRU. | Opcional | `64` | Entero (Capacidad) |

---

## 3. Configuración Específica de Componentes

### 3.1 Configuración de Streamlit (`config.toml`)
Archivo de respaldo: [streamlit_app/.streamlit/config.toml](../streamlit_app/.streamlit/config.toml)

El entorno científico utiliza una configuración estricta para garantizar accesibilidad visual y ejecución desatendida en contenedor:
```toml
[theme]
primaryColor        = "#22c55e"   # Verde esmeralda agroecológico
backgroundColor     = "#0f172a"   # Fondo oscuro pizarra (Slate 900)
secondaryBackgroundColor = "#1e293b" # Contenedores y barras laterales (Slate 800)
textColor           = "#f1f5f9"   # Texto de alto contraste (WCAG AA)

[server]
headless = true                   # Desactiva la apertura automática del navegador del host
```

### 3.2 Configuración de Empaquetado Frontend (`vite.config.js`)
Archivo de respaldo: [frontend/vite.config.js](../frontend/vite.config.js)

El empaquetador Vite incluye optimizaciones para carga diferida de bibliotecas pesadas de mapas y gráficos mediante `manualChunks`:
- **`leaflet`:** Agrupa `leaflet`, `react-leaflet` y `leaflet-draw`.
- **`charts`:** Agrupa `recharts`.
- **`documents`:** Agrupa `jspdf`, `docx` y `file-saver`.
- **Proxy de Desarrollo:** Enruta localmente las llamadas `/api` y `/health` hacia el host interno de Docker `http://backend:8000` si se define `VITE_BACKEND_INTERNAL_URL`.

---

## 4. Diferencias entre Entorno de Desarrollo y Producción

Archivo de respaldo: [docker-compose.yml](../docker-compose.yml) vs. [docker-compose.prod.yml](../docker-compose.prod.yml)

| Parámetro / Estrategia | Modo Desarrollo (`docker-compose.yml`) | Modo Producción (`docker-compose.prod.yml`) |
| :--- | :--- | :--- |
| **Recarga de Código (Hot-Reload)** | Habilitada mediante montajes de volumen bind-mount (`./backend:/app`, `./frontend:/app`) y Uvicorn `--reload`. | Deshabilitada. Los contenedores contienen únicamente el código compilado sin bind-mounts del código fuente. |
| **Frontend Servidor Web** | Servidor de desarrollo Vite (`npm run dev -- --host 0.0.0.0`). | Servidor Nginx optimizado compilando estáticos con `Dockerfile.prod` y enrutamiento proxy `/api`. |
| **Variables Obligatorias** | Admite valores de respaldo por defecto si la variable no está en `.env`. | Utiliza interpolación estricta de variables obligatorias (`${DATABASE_URL:?}`, `${JWT_SECRET:?}`). Si falta una variable, Docker Compose aborta el arranque. |
| **Políticas de Reinicio** | Por defecto (`restart: no`). | Resiliente (`restart: unless-stopped`) en todos los servicios. |
