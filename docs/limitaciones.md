# Limitaciones Técnicas, Científicas y Verificaciones Pendientes

**Documento:** `docs/limitaciones.md`  
**Referencia del commit analizado:** [`0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`](https://github.com/JMarkoFlores/gemelo-digital-polinizadores/commit/0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02)  
**Evidencia principal:** [README.md:220-225](../README.md#L220-L225), [backend/app/services/optimization.py](../backend/app/services/optimization.py), [backend/app/services/model_store.py](../backend/app/services/model_store.py), [streamlit_app/data_pipeline.py](../streamlit_app/data_pipeline.py)

---

## 1. Visión General de Limitaciones

Todo modelo de gemelo digital y optimización agroecológica posee fronteras de validez delimitadas por las hipótesis matemáticas, las resoluciones espaciales y la representatividad de los datos de entrenamiento. En esta sección se diferencian con rigor:
1. **Limitaciones Demostradas en Código o Documentos:** Restricciones inherentes a la arquitectura, los datos o la formulación algorítmica.
2. **Aspectos Pendientes de Verificar:** Hipótesis técnicas o riesgos operacionales que requieren pruebas dinámicas o intervención humana en un entorno activo.

---

## 2. Limitaciones Demostradas en el Código y Datos

### 2.1 Extrapolación Exploratoria y Sesgo Espacial (*Domain Shift*)
- **Evidencia en Documentos:** El [README.md:221](../README.md#L221) señala que ciertas condiciones evaluadas (como escenarios de estrés térmico con temperaturas extremas) se encuentran fuera de la distribución normal observada en el dataset de calibración.
- **Evidencia en Código:** El archivo [backend/app/services/model_store.py:180-234](../backend/app/services/model_store.py#L180-L234) implementa `check_point_in_region`, que calcula la distancia ortodrómica Haversine entre el centroide de la parcela y el centroide de calibración del modelo activo. Si la distancia supera el radio permitido más un $20\%$ de tolerancia (`max_radius_with_tolerance_km`), el backend aborta la simulación con `400 Bad Request`.
- **Impacto Científico:** La red neuronal subrogada (Surrogate DNN) pierde fiabilidad y capacidad de generalización si se realizan inferencias sobre bioclimas marcadamente distintos a la región de entrenamiento (ej. aplicar un modelo calibrado en el Valle del Cauca sobre una zona semiárida o de páramo).

### 2.2 Coberturas de Superficie y Restricciones Físicas
- **Evidencia en Documentos:** El [README.md:222](../README.md#L222) documenta la existencia de registros históricos de entrenamiento en los que la suma de coberturas excedía el $100\%$.
- **Evidencia en Código:** Para corregir esta anomalía en el motor de inferencia, [backend/app/services/optimization.py:161-163](../backend/app/services/optimization.py#L161-L163) impone una corrección forzada en tiempo de evaluación:
  ```python
  remaining = 100.0 - natural_area - floral_strips
  adjusted_crop_area = min(crop_area, remaining)
  ```
  Adicionalmente, el problema genético evalúa la penalización $g_1(X) \le 0$ para descartar individuos de la población que violen la cota física total del paisaje.

### 2.3 Redondeo Numérico y Pérdida de Dominancia Fraccionaria
- **Evidencia en Documentos:** El [README.md:223](../README.md#L223) advierte que existe un redondeo en la exportación de las soluciones.
- **Evidencia en Código:** Las funciones `summarize_candidate` y el bucle de extracción del Pareto en [optimization.py:188-194](../backend/app/services/optimization.py#L188-L194) aplican `round(..., 3)`.
- **Impacto:** Si dos soluciones no dominadas tienen valores de aptitud extremadamente cercanos en precisión de punto flotante de 64 bits (`float64`), el redondeo a 3 decimales puede provocar que una solución parezca idéntica a otra o resulte ligeramente dominada en la tabla visual exportada.

### 2.4 Pérdida de Datos de Errores Desagregados por Fold Históricos
- **Evidencia en Documentos:** El [README.md:224](../README.md#L224) explicita: *"Los resultados de las pruebas de Friedman y Nemenyi están documentados en el Excel de respaldo. No obstante, los errores absolutos (MAE) desagregados por partición o fold necesarios para recalcular la prueba de forma independiente no se conservaron en la versión final de la base de datos de entrenamiento."*
- **Impacto:** Un evaluador externo no puede recalcular numéricamente de forma directa la tabla T8 y T9 del artículo original sin antes ejecutar un nuevo entrenamiento K-Fold completo en el laboratorio Streamlit.

### 2.5 Incompletitud de Conectores Satelitales Automáticos
- **Evidencia en Código:** En [streamlit_app/data_pipeline.py:443-486](../streamlit_app/data_pipeline.py#L443-L486), las funciones `fetch_era5_climate_timeseries` y `fetch_land_use_snapshot` requieren librerías no listadas en `requirements.txt` (`cdsapi`, `earthengine-api`, `geemap`) y tokens de autenticación externos.
- **Impacto:** La ingesta automatizada satelital avanzada no es ejecutable de forma inmediata dentro de los contenedores Docker estándar sin añadir dependencias y claves privadas.

---

## 3. Aspectos Pendientes de Verificar (Requieren Entorno Activo / Intervención Humana)

| Aspecto por Verificar | Descripción del Riesgo Técnico | Acción Humana o de Entorno Requerida |
| :--- | :--- | :--- |
| **Dependencia `matplotlib` en Backend** | El servicio [report_general_export_service.py:7-9](../backend/app/services/report_general_export_service.py#L7-L9) importa `matplotlib` para renderizar gráficos base64, pero `matplotlib` no figura en [backend/requirements.txt](../backend/requirements.txt). | Levantar el contenedor `backend` en un entorno Docker limpio para confirmar si `pymoo` o `tensorflow` la proveen como dependencia transitiva o si es indispensable agregar `matplotlib==3.x` a `requirements.txt`. |
| **Desempeño y Huella de Memoria de `langflow`** | La imagen `langflowai/langflow:latest` puede requerir entre 1.5 GB y 3 GB de RAM en reposo/ejecución. | Verificar el consumo de recursos en servidores con límites estrictos de memoria para evitar reinicios por OOM (*Out Of Memory*). |
| **Propuesta de Cálculo en Hectáreas (`CAMBIOS_FUTUROS.md`)** | El archivo [CAMBIOS_FUTUROS.md:24-31](../CAMBIOS_FUTUROS.md#L24-L31) propone calcular el área en hectáreas mediante `turf.js`. Dicha librería no está en [frontend/package.json](../frontend/package.json). | Definir si se autoriza la incorporación de `@turf/area` en el frontend para implementar la tabla de Plan de Acción en hectáreas solicitada por el usuario. |
| **Persistencia de Semilla en Simulaciones Paralelas** | Si múltiples clientes ejecutan `POST /api/simular` concurrentemente, la función `minimize` usa `seed=42`. | Evaluar si se debe parametrizar la semilla del optimizador genético según el `simulation_id` para evitar determinismo idéntico en parcelas distintas de usuarios concurrentes. |
