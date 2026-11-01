# Informe de Correcciones Técnicas — Auditoría Metodológica 07

**Proyecto**: Gemelo Digital Agroecológico para Polinizadores — Revisión Metodológica  
**Rama**: `revision-metodologica`  
**Commit base**: `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab`  
**Fecha de finalización**: 28 de octubre de 2026  
**Responsable técnico**: Antigravity (Google DeepMind)  
**Destino editorial**: Revista Ciencia y Tecnología Agropecuaria (AGROSAVIA)  
**Estado general**: VERIFICADO TÉCNICAMENTE A NIVEL UNITARIO/INTEGRACIÓN (132/132 pruebas automatizadas en Docker; 5/5 pruebas lógicas en Node.js con dependencias simuladas). Validación funcional en navegador, generación física de PDF/Word y campaña científica definitiva PENDIENTES. El sistema NO se presenta como completamente validado.

---

## 1. Resumen Ejecutivo

La Auditoría Metodológica Independiente 07 evaluó la coherencia poblacional y la integridad en la presentación de los informes de gestión (`get_management_report`) y sus consumidores directos en interfaz y exportación documental:

1. **Partición errónea de recuentos en la agregación de gestión**: En `get_management_report`, la métrica `simulaciones_no_cumplen` continuaba calculándose como `total_sims - cumplen_hipotesis`. Esta resta asignaba indebidamente las simulaciones infactibles (sin solución matemática encontrada) a la categoría de "simulaciones que no cumplen", a pesar de que el informe ya las reportaba de forma simultánea como no evaluables. Esto violaba la partición canónica de la población analizada y distorsionaba la interpretación agroecológica de las intervenciones.
2. **Fabricación espuria de ceros ante datos ausentes y distorsión terminológica en consumidores**: En la interfaz React (`AdminReportsPage.jsx`) y en el módulo de exportación de reportes (`generalReportExporters.js`), expresiones como `rendimiento_promedio_optimo?.toFixed(1) || 0` o `v ?? 0` colapsaban las métricas ausentes (`null` / `undefined`) a un cero numérico real (`0.0`), fabricando barras, puntos y filas ficticias cuando no existían simulaciones evaluables. Asimismo, en Excel se etiquetaba el total de registros como "Total Simulaciones Evaluadas" y persistían términos obsoletos como "Hipótesis Comprobada" en PDF y Word.

Bajo un enfoque focalizado y sin alterar el entrenamiento, modelos, bundles, Docker o NSGA-II, se completaron las siguientes soluciones:
- En `report_general_service.py` y `schemas_reports.py`, se implementó la partición canónica estricta:
  $$\text{total} = \text{evaluables} + \text{no evaluables}$$
  $$\text{evaluables} = \text{cumplen} + \text{no cumplen} \implies \text{no cumplen} = \text{evaluables} - \text{cumplen}$$
  Cuando $\text{evaluables} = 0$, $\text{no cumplen} = 0$ y la tasa de cumplimiento es ausente (`None`). Se propagaron `simulaciones_cumplen_hipotesis` y `simulaciones_no_cumplen` a las agregaciones regionales y a la serie temporal de evolución.
- En `generalReportExporters.js` y `AdminReportsPage.jsx`, se implementó discriminación estricta entre ausencia de dato (`null`/`undefined` $\to$ `"N/D"`) y valor numérico real igual a cero (`0.0 pts`, `0.0%`). En Excel, se exponen por separado `Total Registradas`, `Evaluables (con solución)`, `No Evaluables (sin solución)`, `Denominador de la Tasa`, `Cumplen Criterio` y `No Cumplen (evaluables)`, dejando celdas numéricas con `"N/D"` ante datos ausentes.
- Se sustituyó en todos los consumidores la terminología obsoleta ("hipótesis comprobada") por **"criterio operativo de mejora conjunta"** y se explicitó visualmente el denominador de cálculo.

---

## 2. Matriz de Hallazgos y Correcciones — Auditoría 07

| Hallazgo / Fallo Reproducido | Causa Raíz Identificada | Corrección Técnica Implementada | Archivos Modificados / Creados | Verificación Técnica de Regresión | Estado |
|---|---|---|---|---|---|
| **1. Recuentos Incoherentes en Informes de Gestión** | `report_general_service.py` calculaba `sims_no_cumplen = total_sims - cumplen_hipotesis`, absorbiendo las simulaciones infactibles en "no cumplen". En cortes regionales y temporales no se desagregaban los recuentos de cumplimiento. | 1. `sims_no_cumplen = (sims_evaluables - cumplen_hipotesis) if sims_evaluables > 0 else 0`.<br>2. Adición de `simulaciones_cumplen_hipotesis` y `simulaciones_no_cumplen` a `RegionManagementItem` y `ManagementTemporalEvolutionPoint`.<br>3. Mantenimiento del denominador explícito `denominador_tasa = "evaluables"`.<br>4. Tasa `None` cuando `evaluables == 0`. | `backend/app/schemas_reports.py`, `backend/app/services/report_general_service.py` | `tests/revision/test_audit07_management_reports_and_exporters.py` (Casos A, B, C, D, F, G ejecutados en Docker). | **APROBADO** |
| **2. Conversión de Métricas Ausentes a Cero y Terminología en Consumidores** | Uso de operadores falsy (`|| 0`) y coalescencia por defecto (`?? 0`) en frontend y exportadores que convertían `null` en `0`. En Excel se denominaba erróneamente al total de registros como "Total Evaluadas" y se imprimían ceros ficticios. | 1. Funciones auxiliares `formatVal`, `formatPct`, `exportVal`, `formatUiMetric` y `formatUiDeltaHint` que devuelven `'N/D'` ante `null`/`undefined` y preservan `0.0`.<br>2. Separación explícita de filas en Excel: total registradas, evaluables, no evaluables, denominador y cumplimiento.<br>3. Sustitución de "hipótesis comprobada" por "criterio operativo de mejora conjunta" en PDF, Word, Excel y React.<br>4. Barra de resumen poblacional agregada a la interfaz React. | `frontend/src/lib/generalReportExporters.js`, `frontend/src/pages/AdminReportsPage.jsx` | `tests/revision/test_audit07_frontend_exporters.mjs` (5 pruebas Node.js validando exportadores PDF, Word, Excel y formateadores UI). | **APROBADO** |

---

## 3. Detalle Técnico de las Correcciones Implementadas

### 3.1. Hallazgo 1: Separar Recuentos Evaluables y No Evaluables

#### 3.1.1. Diagnóstico del Fallo
En `backend/app/services/report_general_service.py`:
```python
# Código anterior defectuoso:
total_sims = len(simulations)
sims_evaluables = len(evaluable_sims)
sims_no_evaluables = total_sims - sims_evaluables
cumplen_hipotesis = sum(1 for s in evaluable_sims if ...)

# ERROR: resta total_sims en lugar de sims_evaluables
sims_no_cumplen = total_sims - cumplen_hipotesis
```
Si una base de datos contenía 1 simulación factible que cumplía el criterio y 1 simulación infactible (sin solución matemática), `total_sims = 2`, `sims_evaluables = 1`, `sims_no_evaluables = 1`, `cumplen_hipotesis = 1`.  
La fórmula errónea calculaba `sims_no_cumplen = 2 - 1 = 1`, reportando que 1 simulación no cumplía y 1 era no evaluable, sumando un recuento espurio de 3 eventos sobre 2 simulaciones reales.

#### 3.1.2. Corrección Canónica Implementada
1. **Regla de Partición Canónica**:
   ```python
   sims_no_cumplen = (sims_evaluables - cumplen_hipotesis) if sims_evaluables > 0 else 0
   ```
2. **Propagación Regional y Temporal**:
   En `comparacion_regiones` y `evolucion_temporal`:
   ```python
   reg_no_cumplen = (reg_eval - reg_cumplen) if reg_eval > 0 else 0
   d_no_cumplen = (d_eval - d_cumplen) if d_eval > 0 else 0
   ```
3. **Ampliación de Esquemas Pydantic**:
   En `backend/app/schemas_reports.py`:
   - `RegionManagementItem`: añadidos `simulaciones_cumplen_hipotesis: int = 0` y `simulaciones_no_cumplen: int = 0`.
   - `ManagementTemporalEvolutionPoint`: añadidos `simulaciones_cumplen_hipotesis: int = 0` y `simulaciones_no_cumplen: int = 0`.

---

### 3.2. Hallazgo 2: Conservar Ausencia de Datos en Pantalla y Exportaciones

#### 3.2.1. Diagnóstico del Fallo
En `AdminReportsPage.jsx`:
```jsx
// Código defectuoso:
{rendimiento_promedio_optimo?.toFixed(1) || 0} pts
// Si rendimiento_promedio_optimo es null o undefined, producía "0 pts"
// Si rendimiento_promedio_optimo es 0.0, toFixed(1) es "0.0" (truthy), pero si fuera 0 producía 0.
```
En `generalReportExporters.js`:
```javascript
// Código defectuoso en Excel:
['Rendimiento Óptimo (kg/ha)', kpis?.rendimiento_promedio_optimo ?? 0],
// Si kpis.rendimiento_promedio_optimo era null, escribía numéricamente 0 en la celda Excel.
```
Asimismo, en Excel la primera fila de resumen se titulaba erróneamente:
`['Total Simulaciones Evaluadas', kpis?.total_simulaciones ?? 0]`  
lo cual confundía el total de registros con el conjunto evaluable.

#### 3.2.2. Solución Implementada
1. **Funciones Formateadoras Robustas**:
   - `formatVal(v, decimals = 1, unit = '')`: Retorna `'N/D'` si `v === null || v === undefined`. Si es numérico (incluido `0`), formatea con los decimales y la unidad correspondientes (ej. `'0.0 pts'`).
   - `formatPct(v, decimals = 1)`: Retorna `'N/D'` ante ausencia de datos (evita `'N/D%'`), y `${v.toFixed(decimals)}%` si es numérico (ej. `'0.0%'`).
   - `exportVal(v)`: En Excel, si `v === null || v === undefined`, retorna `'N/D'`. Si es número finito, retorna el número directo para permitir cálculos posteriores.
   - `formatUiMetric(val, unit, decimals)` y `formatUiDeltaHint(delta, pct)`: En React, devuelven `'N/D'` ante ausencia de datos y muestran correctamente valores numéricos cero.
2. **Desglose Poblacional Visible en UI y Excel**:
   - Se añadió un bloque de resumen en la interfaz:
     - Total Registradas: `kpis.total_simulaciones`
     - Evaluables: `kpis.simulaciones_evaluables`
     - No Evaluables: `kpis.simulaciones_no_evaluables`
     - Denominador de la Tasa: `kpis.denominador_tasa`
     - Cumplen: `kpis.simulaciones_cumplen_hipotesis`
     - No Cumplen: `kpis.simulaciones_no_cumplen`
   - En Excel se crearon filas separadas y se corrigió el encabezado:
     - `Total Simulaciones Registradas`
     - `Simulaciones Evaluables (con solución)`
     - `Simulaciones No Evaluables (sin solución)`
     - `Denominador de la Tasa de Cumplimiento`
     - `Simulaciones que Cumplen Criterio Operativo`
     - `Simulaciones que No Cumplen Criterio (evaluables)`
3. **Unificación Terminológica**:
   - Se reemplazó toda referencia a "hipótesis comprobada" por **"criterio operativo de mejora conjunta"** en `exportManagementReportToPdf`, `exportManagementReportToDocx`, `exportManagementReportToExcel` y `AdminReportsPage.jsx`.

---

## 4. Evidencias de Verificación y Pruebas de Regresión

### 4.1. Pruebas Focalizadas de la Auditoría 07

Se desarrollaron dos suites de pruebas especializadas:
1. `tests/revision/test_audit07_management_reports_and_exporters.py` (Backend y lógica de agregación en Python).
2. `tests/revision/test_audit07_frontend_exporters.mjs` (Lógica de exportación y formateo en JavaScript / Node.js).

| Caso de Prueba | Descripción del Escenario | Resultado Obtenido | Estado |
|---|---|---|---|
| **Caso A** | 1 cumple, 1 no evaluable (infactible sin solución). | `total=2`, `evaluables=1`, `no_evaluables=1`, `cumplen=1`, `no_cumplen=0`, `tasa=100.0%`, `denominador="evaluables"`. | **APROBADO** |
| **Caso B** | Todas no evaluables (2 simulaciones infactibles). | `total=2`, `evaluables=0`, `no_evaluables=2`, `cumplen=0`, `no_cumplen=0`, `tasa=None`, métricas óptimas y deltas `=None`. | **APROBADO** |
| **Caso C** | Todas evaluables (1 cumple, 1 no cumple). | `total=2`, `evaluables=2`, `no_evaluables=0`, `cumplen=1`, `no_cumplen=1`, `tasa=50.0%`. | **APROBADO** |
| **Caso D** | Base de datos vacía (sin simulaciones). | `total=0`, `evaluables=0`, `no_evaluables=0`, `cumplen=0`, `no_cumplen=0`, métricas `=None`, listas vacías. | **APROBADO** |
| **Caso E** | Distinción entre métrica ausente (`None`/`null`) y numérica cero (`0.0`). | `formatVal(0) == "0.0 pts"`, `formatVal(None) == "N/D"`, `formatPct(0) == "0.0%"`, `formatPct(None) == "N/D"`. En Excel, `0` es numérico y `None` es `"N/D"`. | **APROBADO** |
| **Caso F** | Conservación del cálculo pareado (100 $\to$ 110 junto con 1000 $\to$ None). | Delta de rendimiento = `+10.0`, `no_cumplen=0`, `cumplen=1`, `evaluables=1`, `no_evaluables=1`. | **APROBADO** |
| **Caso G** | Consistencia en cortes regional y temporal. | En regiones y puntos temporales: `evaluables = cumplen + no_cumplen`, tasas no vacías calculadas sobre evaluables locales. | **APROBADO** |

### 4.2. Resultados de Ejecución

#### Pruebas Backend y Científicas (Docker):
```text
docker compose -p polinizadores_revision run --rm scientific pytest tests/revision/ -v
============================= 132 passed in 105.12s =============================
```

#### Pruebas Frontend y Exportadores (Node.js con Mocks Aislados):
```text
node --loader ./tests/revision/loader.mjs tests/revision/test_audit07_frontend_exporters.mjs
=== Test Suite Auditoria 07: Exporters and Formatters ===
[PASS] Caso E: Formatter distinctions (zero vs null)
[PASS] Caso A: Exporters with 1 cumple, 1 no evaluable
[PASS] Caso B: Exporters with all non-evaluable (null metrics)
[PASS] Caso F: Preserving delta +10.0 and correct counts
[PASS] Terminological consistency: No 'Hipotesis' in exported structures
=== ALL 5 FRONTEND EXPORTER TESTS PASSED ===
```

> [!IMPORTANT]
> **Alcance de las Pruebas Node.js**: Las 5 pruebas automatizadas en Node.js validan exclusivamente la estructuración de celdas para Excel (`exportManagementReportToExcel`), la presencia de etiquetas canónicas y la lógica de las funciones de formato (`formatVal`, `formatPct`, `exportVal`) mediante dependencias simuladas en memoria (`mock_deps.mjs`). **No certifican la generación física de archivos binarios ni la maquetación visual ni estética de documentos PDF y Word**. Dicha validación requiere interacción en navegador y revisión visual de archivos reales en la fase funcional.

---

## 5. Tabla de Estado de Verificaciones

| Componente / Prueba | Tipo de Prueba | Clasificación | Observaciones |
|---|---|---|---|
| `test_audit07_management_reports_and_exporters.py` (7 tests) | Integración backend | **APROBADO** | Casos A a G verificados en Docker. |
| `test_audit07_frontend_exporters.mjs` (5 tests) | Lógica de datos frontend (Mocks) | **APROBADO (MOCKS)** | Estructuración Excel y formateadores UI validados con mocks. No certifica PDF/Word real. |
| Generación real y revisión visual de PDF y Word | Prueba documental funcional | **PENDIENTE (NO EJECUTADO)** | Requiere descarga de archivos reales y revisión visual humana en navegador. |
| Pruebas manuales en navegador (Streamlit / React) | UI interactiva end-to-end | **PENDIENTE (NO EJECUTADO)** | Definidas en `PLAN_VALIDACION_FUNCIONAL.md`. |
| `test_audit06_final_seed_and_paired_reports.py` (19 tests) | Regresión backend | **APROBADO** | Semilla efectiva y comparaciones pareadas verificadas. |
| `test_audit05_simulation_query_infeasible.py` (1 test) | Regresión backend | **APROBADO** | Adaptado a la ecuación de recuento de Auditoría 07. |
| Resto de suite `tests/revision/` (105 tests) | Regresión global | **APROBADO** | Model store, hashes, CLI, Streamlit adapter, NSGA-II. |
| Campaña definitiva (320 escenarios ABM, 5 folds) | Cómputo intensivo científico | **PENDIENTE (NO EJECUTADO)** | Separada de las pruebas funcionales; pendiente de autorización formal. |

---

## 6. Conclusiones y Cumplimiento

1. **Partición Poblacional Canónica**: Se eliminó la distorsión estadística en los informes de gestión. Las simulaciones infactibles ya no engrosan artificialmente las simulaciones que "no cumplen".
2. **Fidelidad de la Lógica de Presentación**: Las funciones de transformación y la estructura tabular de Excel representan con precisión la ausencia de datos (`"N/D"`), diferenciándola del cero real (`0.0 pts`, `0.0%`) y explicitando el denominador evaluable.
3. **Rigurosidad Metodológica para AGROSAVIA**: Toda la terminología del sistema se alineó con la naturaleza de modelos de sustitución y optimización biofísica, reemplazando aseveraciones inductivas inválidas por criterios operativos de mejora agroecológica verificable.
4. **Estado Real de Validación**: El sistema cuenta con correcciones verificadas técnicamente a nivel de código y pruebas automáticas aisladas. **No se presenta como completamente validado**. La validación funcional interactiva (incluyendo la generación y revisión visual real de PDF, Word y Excel) y la campaña definitiva de entrenamiento experimental quedan articuladas en el `PLAN_VALIDACION_FUNCIONAL.md` para su posterior ejecución autorizada.
