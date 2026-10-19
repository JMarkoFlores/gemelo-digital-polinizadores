# Documentación Técnica: Gemelos Digitales de Paisajes Agrícolas y Polinizadores

**Proyecto:** Gemelos Digitales 02 (`gemelo-digital-polinizadores`)  
**Rama de trabajo:** `docs/automatizacion-confluence`  
**Commit base del código analizado:** [`0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`](https://github.com/JMarkoFlores/gemelo-digital-polinizadores/commit/0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02)  
**Commit de inicio de documentación:** [`965e661314ef74b5fe653c06ef00646a251ce167`](https://github.com/JMarkoFlores/gemelo-digital-polinizadores/commit/965e661314ef74b5fe653c06ef00646a251ce167)  
**Fecha de corte:** Octubre 2026  

---

## 1. Alcance y Propósito del Sistema

Gemelos Digitales 02 es una plataforma orientada a la toma de decisiones agroecológicas para optimizar la coexistencia entre la productividad agrícola y la conservación de la biodiversidad de polinizadores (redes de *Apoidea / Hymenoptera*).

El sistema integra:
1. **Un laboratorio de modelado científico en Streamlit**, estructurado según el estándar metodológico **CRISP-DM**, que permite ingestar datos climáticos y de biodiversidad, simular dinámicas ecológicas basadas en agentes (ABM con Mesa), entrenar redes neuronales subrogadas (Surrogate DNN) y someter las arquitecturas a pruebas estadísticas inferenciales rigurosas.
2. **Un backend científico en FastAPI**, que carga el modelo sustituto entrenado, implementa el algoritmo genético multiobjetivo **NSGA-II** (`pymoo`) para explorar el Frente de Pareto entre rendimiento agrícola y abundancia de polinizadores, previene el sesgo espacial (*Domain Shift*), integra un orquestador de agentes IA para explicabilidad y persiste las corridas en PostgreSQL.
3. **Una interfaz web cliente y administrativa en React 18**, con cartografía satelital interactiva (Leaflet), maquetas topográficas 3D en WebGL (Three.js / React Three Fiber), chatbot conversacional de soporte agronómico y herramientas de auditoría y exportación de reportes ejecutivos.

---

## 2. Convenciones de Evidencia y Rigor Documental

Toda la documentación técnica se fundamenta exclusivamente en evidencias comprobadas en el código fuente. Se aplican las siguientes etiquetas de trazabilidad:

- **`[CÓDIGO]`**: Funcionalidad, arquitectura, endpoint o esquema verificado directamente en los archivos de la base de código.
- **`[DOCUMENTO]`**: Elemento declarado en la documentación previa ([README.md](../README.md), [CAMBIOS_FUTUROS.md](../CAMBIOS_FUTUROS.md), [metadata.json](../metadata.json)).
- **`[PENDIENTE DE VERIFICAR]`**: Asunción, discrepancia o aspecto que requiere confirmación o intervención humana.

> **Aviso de Integridad Metodológica:** En esta etapa de análisis documental **no se ejecutaron servicios, pruebas automatizadas, contenedores, simulaciones ni entrenamientos**. Las descripciones corresponden al análisis estático y estructural del código.

---

## 3. Estructura de la Documentación

Esta documentación técnica se organiza en los siguientes volúmenes modulares:

| Documento | Descripción y Contenido Principal |
| :--- | :--- |
| **[inventario.md](./inventario.md)** | Inventario técnico exhaustivo: catálogo de endpoints, servicios, entidades, componentes, contraste README vs. código y materiales externos. |
| **[pendientes.md](./pendientes.md)** | Matriz de discrepancias técnicas (GAPs), dependencias en riesgo, vacíos de testing y requerimientos pendientes. |
| **[arquitectura.md](./arquitectura.md)** | Arquitectura de contenedores (Docker Compose), canales de comunicación, volúmenes de persistencia y flujo de datos inter-servicios. |
| **[instalacion.md](./instalacion.md)** | Requisitos del sistema, procedimiento de despliegue local y diferenciación entre instrucciones revisadas y ejecución comprobada. |
| **[configuracion.md](./configuracion.md)** | Variables de entorno, obligatoriedad, servicios consumidores y directrices de seguridad para secretos externos. |
| **[api.md](./api.md)** | Catálogo completo de los 25 endpoints propios y las 3 rutas generadas por FastAPI, con contratos Pydantic, autenticación y respuestas. |
| **[modelo-de-datos.md](./modelo-de-datos.md)** | Esquema relacional de base de datos (PostgreSQL / SQLAlchemy), entidades `Usuario` y `Simulacion`, tipos JSON y relaciones ORM. |
| **[pipeline-cientifico.md](./pipeline-cientifico.md)** | Flujo CRISP-DM, ingesta (Sintético, GBIF, NASA POWER), simulación ABM, metamodelo Keras y optimizador NSGA-II. |
| **[pruebas.md](./pruebas.md)** | Inventario de pruebas existentes, pruebas estadísticas de robustez (Friedman, Nemenyi), scripts de benchmark y vacíos de testing. |
| **[reproducibilidad.md](./reproducibilidad.md)** | Requisitos para reproducir el ciclo científico, versiones de librerías, materiales ausentes en el repositorio y protocolo alternativo. |
| **[limitaciones.md](./limitaciones.md)** | Limitaciones matemáticas y computacionales demostradas (Domain Shift, extrapolación, conectores incompletos) y aspectos por verificar. |

---

## 4. Mapa del Repositorio

```text
gemelo-digital-polinizadores/
├── .env.example                       # Plantilla de variables de entorno (sin secretos)
├── docker-compose.yml                 # Orquestación local (5 servicios: db, backend, frontend, streamlit, langflow)
├── docker-compose.prod.yml            # Orquestación para producción
├── package.json                       # Scripts auxiliares raíz
├── README.md                          # Documentación introductoria original
├── CAMBIOS_FUTUROS.md                 # Propuestas de requerimientos pendientes
├── metadata.json                      # Metadatos del proyecto
├── backend/                           # API REST FastAPI + Inferencia + NSGA-II
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/                           # Código de la aplicación backend
├── frontend/                          # SPA React 18 + Vite + TailwindCSS + Three.js
│   ├── Dockerfile
│   ├── Dockerfile.prod
│   ├── package.json
│   └── src/                           # Componentes, vistas y estado
├── streamlit_app/                     # Laboratorio de modelado científico CRISP-DM
│   ├── Dockerfile
│   ├── requirements.txt
│   └── *.py                           # Pipeline, ABM, entrenamiento, pruebas estadísticas
├── langflow/                          # Flujo visual de agentes para recomendaciones agroecológicas
│   └── flows/
└── docs/                              # Documentación técnica normalizada
    ├── index.md                       # Índice y alcance (este documento)
    ├── inventario.md                  # Inventario técnico inicial y trazabilidad
    ├── pendientes.md                  # Registro de brechas, GAPs y tareas técnicas
    ├── arquitectura.md                # Componentes y comunicaciones
    ├── instalacion.md                 # Procedimiento de instalación
    ├── configuracion.md               # Variables de entorno y ajustes
    ├── api.md                         # Catálogo de endpoints
    ├── modelo-de-datos.md             # Entidades y base de datos
    ├── pipeline-cientifico.md         # Pipeline de ML y simulación
    ├── pruebas.md                     # Pruebas y validaciones estadísticas
    ├── reproducibilidad.md            # Artefactos y reproducibilidad
    └── limitaciones.md                # Limitaciones demostradas y pendientes
```
