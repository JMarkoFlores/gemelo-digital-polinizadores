# Guía de Instalación y Despliegue Local

**Documento:** `docs/instalacion.md`  
**Referencia del commit analizado:** [`0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`](https://github.com/JMarkoFlores/gemelo-digital-polinizadores/commit/0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02)  
**Evidencia principal:** [docker-compose.yml](../docker-compose.yml), [docker-compose.prod.yml](../docker-compose.prod.yml), [.env.example](../.env.example), [backend/Dockerfile](../backend/Dockerfile), [frontend/Dockerfile](../frontend/Dockerfile), [streamlit_app/Dockerfile](../streamlit_app/Dockerfile)

---

## 1. Declaración de Estado y Rigor de Verificación

> **Nota de Integridad Técnica:**  
> Las instrucciones de instalación contenidas en este documento corresponden a una **revisión estática y documental** de los archivos de configuración (`docker-compose.yml`, Dockerfiles, dependencias y scripts de arranque).  
> **No se ejecutó `docker compose up`, ni se construyeron imágenes de Docker ni se levantaron contenedores activos en esta etapa de auditoría.** Cualquier comportamiento en tiempo de ejecución debe considerarse como derivado del análisis de configuración y pendiente de verificación en un entorno activo.

---

## 2. Requisitos Previos del Sistema

### 2.1 Software Obligatorio (Entorno Contenerizado Recomendado)
- **Git:** Versión 2.30 o superior.
- **Docker Engine:** Versión 24.0 o superior con soporte de virtualización habilitado en BIOS/UEFI.
- **Docker Compose:** Versión v2.20 o superior (sintaxis `docker compose`).

### 2.2 Requisitos de Hardware Sugeridos
- **Procesador:** CPU de 64 bits con conjunto de instrucciones AVX (requerido para optimización nativa de operaciones matriciales en `tensorflow==2.17.1`). Mínimo 4 núcleos.
- **Memoria RAM:** Mínimo 8 GB (16 GB recomendados para soportar simultáneamente los contenedores de TensorFlow, Langflow y compilación de Vite).
- **Espacio en Disco:** Mínimo 15 GB de espacio libre para capas de imágenes base (Python 3.11-slim, Node 20, Postgres Alpine y Langflow AI) y volúmenes persistentes.

---

## 3. Procedimiento de Despliegue Local con Docker Compose

El despliegue local estándar se gestiona mediante [docker-compose.yml](../docker-compose.yml), el cual orquesta 5 servicios interconectados.

### Paso 1: Obtener el Código Fuente y Seleccionar la Rama
```bash
git clone https://github.com/JMarkoFlores/gemelo-digital-polinizadores.git
cd gemelo-digital-polinizadores
git checkout docs/automatizacion-confluence
```
*(Para despliegues de producción del equipo se utiliza la rama `main`).*

### Paso 2: Configuración de Variables de Entorno
Copia la plantilla de variables de entorno [.env.example](../.env.example) a un archivo `.env` en la raíz del proyecto:
```bash
cp .env.example .env
```
Edita `.env` para personalizar los valores de configuración externa (revisa [configuracion.md](./configuracion.md) para detalles sobre obligatoriedad y propósitos). 

> **Aviso de Seguridad:** Nunca versiones el archivo `.env` en Git. Asegúrate de que permanezca listado dentro de [.gitignore](../.gitignore).

### Paso 3: Construcción y Arranque de Contenedores
Ejecuta la construcción de imágenes y el levantamiento de los 5 contenedores:
```bash
docker compose up --build
```

#### Consideraciones durante la primera compilación:
1. **Compilación de Dependencias Backend y Streamlit:** La instalación de paquetes numéricos pesados (`tensorflow==2.17.1`, `pymoo==0.6.1.3`, `scipy==1.14.1`) en las imágenes derivadas de Debian slim puede tomar entre 4 y 10 minutos dependiendo de la velocidad de conexión a internet y CPU.
2. **Dependencia de Salud de Base de Datos:** El servicio `backend` cuenta con la directiva `depends_on: db: condition: service_healthy` ([docker-compose.yml:42-44](../docker-compose.yml#L42-L44)), por lo que Uvicorn esperará a que PostgreSQL responda afirmativamente a `pg_isready` antes de arrancar.
3. **Instalación de Node Modules en Frontend:** El comando de arranque del contenedor frontend ejecuta `sh -c "npm install && npm run dev -- --host 0.0.0.0 --port 5173"` ([docker-compose.yml:60](../docker-compose.yml#L60)), asegurando la sincronización de dependencias de node_modules en el volumen persistente anónimo.

---

## 4. Direcciones y Puertos de Acceso Local

Una vez completado el levantamiento de los servicios, los puntos de acceso declarados en la arquitectura son:

| Servicio / Interfaz | URL Local por Defecto | Variable de Puerto | Descripción |
| :--- | :--- | :--- | :--- |
| **Frontend Web** | `http://localhost:5173` | `FRONTEND_PORT` | Consola interactiva del usuario (Cliente y Administrador) |
| **Backend API** | `http://localhost:8000` | `BACKEND_PORT` | Raíz del servidor FastAPI |
| **Documentación Swagger** | `http://localhost:8000/docs` | N/A | Interfaz interactiva OpenAPI para pruebas de endpoints |
| **Documentación ReDoc** | `http://localhost:8000/redoc` | N/A | Documentación técnica alternativa generada por FastAPI |
| **Laboratorio Streamlit** | `http://localhost:8501` | `STREAMLIT_PORT` | Entorno científico CRISP-DM para ABM y entrenamiento |
| **Orquestador Langflow** | `http://localhost:7860` | `LANGFLOW_PORT` | Interfaz visual de agentes para recomendaciones agroecológicas |
| **Base de Datos PostgreSQL** | `localhost:5432` | N/A | Acceso directo a base de datos relacional para DBAs |

---

## 5. Datos Iniciales y Siembra de Usuarios (Seed Data)

Archivo de respaldo: [backend/app/seed.py](../backend/app/seed.py)

Durante el inicio de la aplicación backend en `lifespan` ([backend/app/main.py:44-58](../backend/app/main.py#L44-L58)), se ejecuta automáticamente la función `seed_initial_data`:
1. **Creación de Tablas:** Crea las tablas relacionales `usuarios` y `simulaciones` si no existen previamente.
2. **Usuario Administrador:** Crea el usuario con rol `admin` utilizando el email y contraseña configurados en las variables `ADMIN_EMAIL` y `ADMIN_PASSWORD`.
3. **Usuario Cliente:** Crea el usuario con rol `cliente` utilizando el email y contraseña configurados en `CLIENT_EMAIL` y `CLIENT_PASSWORD`.
4. **Simulación de Demostración:** Si el usuario cliente no tiene simulaciones, se inserta una simulación inicial de muestra con polígono en el Valle de Moche/Chicama (`[-78.9, -8.1]`), métricas de base y un frente de Pareto precalculado para permitir la exploración inmediata de la interfaz.

---

## 6. Procedimiento Alternativo: Desarrollo Local sin Docker

Para desarrollo específico en un componente sin aislar en contenedores, se requieren los siguientes entornos individuales:

### Backend Local (Python 3.11):
```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: .\venv\Scripts\activate
pip install -r requirements.txt
# Requiere una instancia de PostgreSQL accesible configurada en DATABASE_URL
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Local (Node 18+ o 20+):
```bash
cd frontend
npm install
npm run dev
```

### Streamlit Local (Python 3.11):
```bash
cd streamlit_app
python -m venv venv
source venv/bin/activate  # En Windows: .\venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

---

## 7. Detención y Limpieza del Entorno

Para detener la ejecución de los servicios conservando la persistencia de datos (PostgreSQL, modelos exportados y configuraciones de Langflow):
```bash
docker compose down
```

Para detener y purgar completamente todos los volúmenes de datos asociados:
```bash
docker compose down -v
```
*(¡Precaución! Este comando eliminará los datos de la base de datos `postgres_data` y los modelos almacenados en `modelos_ia_volume`).*
