# Registro de Pendientes, Brechas y Verificaciones Técnicas

**Repositorio:** `gemelo-digital-polinizadores` (Gemelos Digitales 02)  
**Rama de trabajo exclusiva:** `docs/automatizacion-confluence`  
**Commit analizado:** `0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`  
**Fecha de corte:** 14 de octubre de 2026  
**Finalidad:** Consolidar todas las discrepancias técnicas, vacíos de documentación, riesgos de dependencias, materiales científicos ausentes y tareas de verificación requeridas antes de estructurar la publicación en Confluence.

---

## 1. Convenciones de Clasificación

Cada entrada de este informe se cataloga según su origen y naturaleza:
- `[CÓDIGO]`: Hecho comprobado mediante análisis estático del código fuente.
- `[DOCUMENTO]`: Declaración extraída de los documentos del repositorio ([README.md](../README.md), [CAMBIOS_FUTUROS.md](../CAMBIOS_FUTUROS.md), etc.).
- `[PENDIENTE DE VERIFICAR]`: Elemento no validado, hipótesis no contrastada en ejecución, o discrepancia que requiere intervención/confirmación.

---

## 2. Discrepancias entre Documentación y Código (Gaps Técnicos)

| ID | Área | Declarado en Documentación `[DOCUMENTO]` | Observado en Código `[CÓDIGO]` | Impacto / Riesgo Técnico | Estado y Acción Requerida `[PENDIENTE DE VERIFICAR]` | Archivo de Respaldo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | Infraestructura | README.md indica 4 servicios (`frontend`, `backend`, `streamlit`, `db`). | [docker-compose.yml](../docker-compose.yml) y [docker-compose.prod.yml](../docker-compose.prod.yml) definen **5 servicios**, incluyendo `langflow` con volumen `langflow_data`. | La documentación de despliegue omite un contenedor con consumo de memoria y puertos (`7860`). | Actualizar la documentación técnica para reflejar los 5 servicios y documentar la función de Langflow. | [docker-compose.yml:73-87](../docker-compose.yml#L73-L87) |
| **GAP-02** | Conector GBIF | README.md afirma conectar GBIF mediante `pygbif`. | [streamlit_app/data_pipeline.py](../streamlit_app/data_pipeline.py) usa `requests` llamando a la API REST pública de GBIF (`https://api.gbif.org/v1/occurrence/search`). `pygbif` no está instalado. | Quien intente seguir la documentación buscará una dependencia inexistente. | Corregir en la documentación: la ingesta usa la API HTTP directa de GBIF sin biblioteca cliente externa. | [streamlit_app/data_pipeline.py:165-186](../streamlit_app/data_pipeline.py#L165-L186) |
| **GAP-03** | Conectores Satelitales y Climáticos | README.md presenta como preparados los conectores ERA5 (`cdsapi`) y Sentinel-2 (`earthengine-api`, `geemap`). | Las funciones existen en el código pero lanzan `RuntimeError` si se invocan porque los paquetes no forman parte de [streamlit_app/requirements.txt](../streamlit_app/requirements.txt) y exigen credenciales externas ausentes. | Flujo bloqueante si el usuario asume que puede ejecutarlos dentro del contenedor estándar. | Clasificar explícitamente estas funciones como "conectores experimentales que requieren dependencias y credenciales de terceros no incluidas en el contenedor base". | [streamlit_app/data_pipeline.py:443-486](../streamlit_app/data_pipeline.py#L443-L486) |
| **GAP-04** | Catálogo de Endpoints de la API | README.md documenta 17 endpoints. | El código de FastAPI implementa **25 endpoints**, dejando fuera los reportes ejecutivos agregados (`/api/admin/reports/...`), la verificación anti-sesgo regional (`/api/model/region-check`), la elevación topográfica (`/api/terrain/elevation-grid`) y los pings de salud. | Falta de documentación en Swagger/Confluence de los módulos más avanzados. | Registrar la totalidad de los 25 endpoints con sus contratos Pydantic en la documentación de Confluence. | [backend/app/main.py:60-394](../backend/app/main.py#L60-L394), [admin_reports.py:18-143](../backend/app/routers/admin_reports.py#L18-L143) |
| **GAP-05** | Componentes de Visualización Frontend | README.md menciona mapas y resultados. | El frontend incluye un **Diorama 3D interactivo en Three.js** ([LandscapeDiorama3D.jsx](../frontend/src/components/LandscapeDiorama3D.jsx)) deformado por relieve topográfico real, verificación espacial dinámica y un exportador a Word y Excel. | Capacidades de alto valor técnico no están acreditadas en la descripción del proyecto. | Documentar formalmente la pila de visualización 3D (`@react-three/fiber`, `@react-three/drei`) y el algoritmo de deformación topográfica. | [frontend/src/components/LandscapeDiorama3D.jsx](../frontend/src/components/LandscapeDiorama3D.jsx) |

---

## 3. Materiales Científicos Externos Faltantes (Reproducción Bloqueada)

El análisis del [README.md:192-226](../README.md#L192-L226) detalla un protocolo de auditoría científica para respaldar un artículo de investigación. Sin embargo, los siguientes recursos **no existen en el repositorio Git analizado**:

| Material Declarado | Función Descrita | Estado en el Repositorio | Consecuencia para la Reproducción |
| :--- | :--- | :--- | :--- |
| **`respaldo_surrogate_20261008_221709/`** | Carpeta consolidada que preserva la corrida original del modelo, correcciones y archivos analíticos. | `[PENDIENTE DE VERIFICAR]` **Ausente en Git**. (README aclara que se preservó localmente por tamaño). | No se puede validar la firma SHA/binario exacto del modelo histórico sin acceso al repositorio de datos externo. |
| **`scripts_auditoria/predict_baselines.py`** | Script para calcular comparaciones de línea base sin sesgos en el contenedor backend y generar `comparacion_linea_base.json`. | `[PENDIENTE DE VERIFICAR]` **Ausente en Git**. | La predicción debe reconstruirse a partir de la lógica interna de [optimization.py](../backend/app/services/optimization.py). |
| **`scripts_auditoria/prepare_files.py`** | Script de ingesta automatizada que consume la API con credenciales `API_EMAIL` y `API_PASSWORD`. | `[PENDIENTE DE VERIFICAR]` **Ausente en Git**. | No existe el script de automatización del benchmark fuera del código de aplicación. |
| **`scripts_auditoria/generar_documentacion.py`** | Script para analizar el frente de Pareto contra los límites del dataset. | `[PENDIENTE DE VERIFICAR]` **Ausente en Git**. | El análisis de límites del Pareto debe realizarse manualmente o mediante los gráficos del frontend. |
| **Errores MAE desagregados por fold históricos** | Datos crudos para recalcular de forma independiente las pruebas de Friedman y Nemenyi del artículo científico. | `[PENDIENTE DE VERIFICAR]` **Ausente en Git** (declarado explícitamente en README L224 como limitación). | Solo es posible recalcular estas pruebas ejecutando una nueva sesión de entrenamiento en [streamlit_app/robust_tests.py](../streamlit_app/robust_tests.py). |

---

## 4. Riesgos de Dependencias e Integración en Entornos Limpios

### 4.1 Dependencia no declarada en Backend: `matplotlib`
- **Hallazgo:** El archivo [backend/app/services/report_general_export_service.py:7-9](../backend/app/services/report_general_export_service.py#L7-L9) ejecuta:
  ```python
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  ```
- **Riesgo:** `matplotlib` **no está listado** en [backend/requirements.txt](../backend/requirements.txt). Si `pymoo` o `tensorflow` no lo arrastran como dependencia transitiva en una instalación limpia de Docker (`pip install --no-cache-dir -r requirements.txt`), los endpoints de exportación de reportes `/api/admin/reports/*/export` fallarán con `ModuleNotFoundError`.
- **Acción requerida `[PENDIENTE DE VERIFICAR]`:** Confirmar en contenedor si `matplotlib` se instala transitivamente por `pymoo` o si es necesario agregarlo explícitamente a `requirements.txt`.

### 4.2 Falta de `turf.js` para cálculos en Frontend
- **Hallazgo:** En [CAMBIOS_FUTUROS.md:24-31](../CAMBIOS_FUTUROS.md#L24-L31) se especifica el requerimiento de calcular el área real en hectáreas del GeoJSON usando `@turf/area` o Turf.js.
- **Riesgo:** [frontend/package.json](../frontend/package.json) no tiene instalado `@turf/turf` ni `@turf/area`.
- **Acción requerida `[PENDIENTE DE VERIFICAR]`:** La funcionalidad solicitada en `CAMBIOS_FUTUROS.md` (Plan de Acción Recomendado en hectáreas) no ha sido implementada todavía en el código actual.

### 4.3 Clave de API Groq no obligatoria pero crítica para LLM
- **Hallazgo:** `GROQ_API_KEY` está vacía en `.env.example`.
- **Comportamiento observado:**
  - En [chat_service.py](../backend/app/services/chat_service.py): si no hay clave, activa el motor fallback local `gemelos-db-engine`.
  - En [recommendation_service.py](../backend/app/services/recommendation_service.py): si no hay clave y Langflow no responde, activa la recomendación heurística determinista.
- **Acción requerida `[PENDIENTE DE VERIFICAR]`:** Documentar claramente que el sistema es resiliente y opera sin costo alguno en modo local, pero requiere `GROQ_API_KEY` para activar respuestas con lenguaje natural generativo.

---

## 5. Vacíos en Pruebas Automatizadas y Calidad de Software

En apego a la directriz de **no presentar como ejecutadas pruebas que no hayan sido realizadas**, se deja constancia del estado real del testing:

| Tipo de Prueba | Estado Actual en Repositorio | Observación Técnica |
| :--- | :--- | :--- |
| **Pruebas Unitarias Backend** | ❌ **No existen** | No hay framework de pruebas (`pytest` no está en `backend/requirements.txt`), ni directorio `tests/` en el backend. |
| **Pruebas Unitarias Frontend** | ❌ **No existen** | No hay configuración de Vitest o Jest en `frontend/package.json`. No hay archivos `*.test.jsx` ni `*.spec.jsx`. |
| **Pruebas End-to-End (E2E)** | ❌ **No existen** | No hay suites de Cypress, Playwright o Selenium configuradas. |
| **Scripts de Prueba Standalone** | ⚠️ **Existen como scripts sueltos sin aserciones formales** | [test_traceability_pipeline.py](../streamlit_app/test_traceability_pipeline.py), [test_tuning_benchmark.py](../streamlit_app/test_tuning_benchmark.py) y [test_nemenyi.py](../scratch/test_nemenyi.py) son utilitarios de consola que imprimen resultados, pero no forman parte de un arnés de pruebas automatizado con código de salida (exit code) en CI. |
| **Pruebas Estadísticas Inferenciales** | 🟡 **Implementadas en código de UI, no ejecutadas en esta auditoría** | Las pruebas de Shapiro-Wilk, T-Student, Wilcoxon, Cohen's D, Friedman y Nemenyi residen en [robust_tests.py](../streamlit_app/robust_tests.py) y dependen de que el usuario lance interactivamente el entrenamiento en Streamlit. |

---

## 6. Estado de los Requerimientos de `CAMBIOS_FUTUROS.md`

El documento [CAMBIOS_FUTUROS.md](../CAMBIOS_FUTUROS.md) contiene instrucciones para desarrollos futuros sobre la app cliente. Se constata su grado de avance actual en el código analizado:

| Requerimiento en `CAMBIOS_FUTUROS.md` | Estado en Código Actual | Detalle Técnico Observado |
| :--- | :--- | :--- |
| **1. Zoom en las vistas 2D** | `[PENDIENTE DE VERIFICAR]` Parcial | [ExpandableMapCard.jsx](../frontend/src/components/ExpandableMapCard.jsx) permite maximizar la tarjeta del mapa a pantalla completa, pero la interacción de controles de zoom granular independientes en Leaflet requiere revisión. |
| **2. Gestión general en admin (no solo individual por usuario)** | `[CÓDIGO]` **Implementado** | En [AdminReportsPage.jsx](../frontend/src/pages/AdminReportsPage.jsx) y [admin_reports.py](../backend/app/routers/admin_reports.py) ya existen reportes operativos y de gestión agronómica agregados a nivel plataforma, filtrables por fechas y regiones. |
| **3. Plan de Acción Recomendado (Tabla en hectáreas y acciones imperativas)** | `[PENDIENTE DE VERIFICAR]` **No implementado** | En [ResultsDashboard.jsx](../frontend/src/components/ResultsDashboard.jsx) los resultados se muestran en porcentajes relativos de cobertura (`crop_area_pct`, etc.). No existe la tabla de conversión a hectáreas absolutas mediante Turf.js ni las frases imperativas redactadas para agricultores ("Reducir pesticidas en X hectáreas"). |

---

## 7. Matriz de Tareas Priorizadas antes de Documentar en Confluence

| Prioridad | Tarea Técnica / Documental | Justificación | Dependencia / Archivo Asociado |
| :--- | :--- | :--- | :--- |
| **ALTA** | Sincronizar catálogo de endpoints entre backend y documentación | Evitar que los desarrolladores o auditores desconozcan los 8 endpoints agregados de reportes y servicios. | [main.py](../backend/app/main.py), [admin_reports.py](../backend/app/routers/admin_reports.py) |
| **ALTA** | Declarar el 5to contenedor (`langflow`) en la arquitectura técnica | Un despliegue en servidor fallará si no se contemplan los requerimientos de CPU/RAM de la imagen de Langflow. | [docker-compose.yml](../docker-compose.yml) |
| **ALTA** | Alertar la ausencia de la carpeta `respaldo_surrogate_...` para reproducibilidad científica | Garantizar honestidad intelectual y definir el enlace hacia el futuro repositorio de datos abierto. | [README.md:208-212](../README.md#L208-L212) |
| **MEDIA** | Validar la dependencia de `matplotlib` en backend | Evitar fallos silenciosos en la exportación de reportes PDF/Word ejecutivos en entornos de producción limpios. | [requirements.txt](../backend/requirements.txt), [report_general_export_service.py](../backend/app/services/report_general_export_service.py) |
| **MEDIA** | Aclarar la naturaleza de los conectores ERA5 y Sentinel-2 | Explicar que la ingestión operativa por defecto se apoya en NASA POWER y GBIF REST API para no frustrar al usuario con fallos de `cdsapi` o `ee`. | [data_pipeline.py](../streamlit_app/data_pipeline.py) |
| **BAJA** | Documentar el estado de los requerimientos de `CAMBIOS_FUTUROS.md` | Dejar trazado el roadmap de frontend respecto al cálculo geodésico en hectáreas y el Plan de Acción. | [CAMBIOS_FUTUROS.md](../CAMBIOS_FUTUROS.md), [ResultsDashboard.jsx](../frontend/src/components/ResultsDashboard.jsx) |

---
*Fin del documento de pendientes y brechas técnicas. Generado para la rama `docs/automatizacion-confluence` bajo el commit `0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`.*
