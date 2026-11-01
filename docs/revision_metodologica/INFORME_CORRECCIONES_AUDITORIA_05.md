# Informe de Correcciones Técnicas — Auditoría Metodológica 05

**Proyecto**: Gemelo Digital Agroecológico para Polinizadores — Revisión Metodológica  
**Rama**: `revision-metodologica`  
**Commit base**: `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab`  
**Fecha de finalización**: 28 de octubre de 2026  
**Responsable técnico**: Antigravity (Google DeepMind)  
**Destino editorial**: Revista Ciencia y Tecnología Agropecuaria (AGROSAVIA)  
**Estado general**: VERIFICADO Y APROBADO (113/113 pruebas unitarias e integrales en Docker; nuevo smoke run `smoke_20261028_191444`, exportación canónica, validación de bundle y optimización NSGA-II validados al 100%)

---

## 1. Resumen Ejecutivo

La Auditoría Metodológica Independiente 05 examinó la fidelidad entre la configuración declarada y la efectivamente ejecutada en el adaptador de Streamlit, la estabilidad de las consultas a nivel de API/Chat ante simulaciones infactibles, y la precisión matemática en la evaluación del criterio operativo agroecológico conjunto.

La auditoría confirmó la validez y permanencia de las correcciones previas de las auditorías 01 a 04 (rechazo de modelos modificados por hash en core y backend, recuperación del bundle ante fallos de publicación, rechazo de datasets anómalos o con IDs duplicados, selección final agregada unificada, ciclo de vida de persistencia y 16 hashes de integridad del smoke anterior).

Sin embargo, se identificaron y reprodujeron experimentalmente tres fallos específicos:

1. **Divergencia entre configuración ejecutada y persistida en Streamlit**: `streamlit_app/adapter.py` preparaba `config_effective`, pero `streamlit_app/advanced_training.py` recargaba y transformaba la configuración de manera independiente. Se reprodujo un caso donde `config_effective.json` persistía `group_duplicates=True` mientras que `run_nested_cv` recibía `group_duplicates=False`.
2. **Caída por excepción no capturada en consulta de simulaciones sin solución**: `backend/app/services/chat_service.py` (`query_simulation_details`) invocaba `sim.metricas_optimas.get(...)` asumiendo que `metricas_optimas` siempre era un diccionario. Cuando una simulación resultaba infactible (`metricas_optimas = None`), se producía una excepción fatal `AttributeError: 'NoneType' object has no attribute 'get'`.
3. **Falso cumplimiento en el criterio operativo por redondeo prematuro**: `backend/app/services/optimization.py` (`run_simulation`) calculaba `meets_joint_criteria` sobre deltas ya redondeados a 3 decimales (`round(..., 3)`). Para un escenario límite con línea base (100.0, 100.0) y solución (99.9996, 119.9998), los deltas reales eran -0.0004 y +19.9998%, los cuales se redondeaban visualmente a 0.000 y 20.000%, evaluando erróneamente `meets_joint_criteria = True` (falso positivo).

Bajo el principio de intervención mínima y no regresión, se resolvieron estos tres fallos respetando estrictamente los contratos existentes. La suite completa de pruebas unitarias y de integración pasó a contar con **113 pruebas exitosas (100% de aprobación en 111.38s)**. Asimismo, se generó y validó una nueva corrida smoke reproducible (`smoke_20261028_191444`) con 16 hashes íntegros, verificando la exportación canónica del modelo y la optimización NSGA-II.

---

## 2. Matriz de Hallazgos y Correcciones — Auditoría 05

| Hallazgo / Fallo Reproducido | Causa Raíz Identificada | Corrección Técnica Implementada | Archivos Modificados / Creados | Verificación Técnica de Regresión | Estado |
|---|---|---|---|---|---|
| **1. Configuración Única para Ejecución y Persistencia** | `adapter.py` y `advanced_training.py` duplicaban la lógica de lectura y transformación del protocolo. Al recibir `group_duplicates=False`, la persistencia grababa `True` pero el entrenamiento ejecutaba `False`. | Se implementó un flujo de configuración única. `prepare_streamlit_run_config` construye el objeto canónico y `execute_streamlit_training_run` lo transmite directamente a `train_and_evaluate_all_models` y a `save_run_artifacts`. En modo científico (`scientific_mode=True`), se rechaza explícitamente con `ValueError` cualquier solicitud con `group_duplicates=False` para prevenir fuga de datos. En modo exploratorio, se respeta `group_duplicates=False` idénticamente en ejecución y persistencia. | `streamlit_app/adapter.py`, `streamlit_app/advanced_training.py` | `tests/revision/test_audit05_unified_config.py` (5 pruebas pasadas: paridad de configuración en False y True, rechazo en modo científico, defaults de splits y compatibilidad con configs inyectados). | **APROBADO** |
| **2. Consulta de Simulaciones Sin Solución (Infactibles)** | `query_simulation_details` intentaba llamar `.get()` directamente sobre `sim.metricas_optimas` sin verificar si era `None`. | Verificación `has_opt = sim.metricas_optimas is not None and isinstance(sim.metricas_optimas, dict)`. Si es `False`, retorna explícitamente `tiene_solucion_optima: False`, `metricas_optimas: None` y `mejoras: {"delta_rendimiento": None, "delta_polinizadores_porcentaje": None, "estado": "no_evaluable"}` sin fabricar datos falsos. Se preservaron las comprobaciones de autorización por rol y propiedad. Se ajustaron los consumidores en `chat_service.py` (`generate_local_fallback_reply`, `query_simulations_summary`) y `report_general_service.py` (`get_management_report`) para no distorsionar promedios ni contar falsos éxitos. | `backend/app/models/simulation.py`, `backend/app/services/chat_service.py`, `backend/app/services/report_general_service.py` | `tests/revision/test_audit05_simulation_query_infeasible.py` (7 pruebas pasadas: simulación con solución, simulación sin solución sin crash, registro inexistente, control de autorización, generación de fallback, resumen de usuario y reporte de gestión). | **APROBADO** |
| **3. Criterio Operativo Antes del Redondeo** | En `optimization.py`, `meets_joint_criteria` evaluaba `delta_yield >= 0 and delta_pollinators >= 20.0` después de haber aplicado `round(raw, 3)`. | Evaluación a precisión numérica flotante completa (`raw_delta_yield >= 0.0 and raw_delta_pollinators >= 20.0`) **antes** de cualquier redondeo. El redondeo a 3 decimales se reserva exclusivamente para los campos de presentación visual (`delta_yield`, `delta_pollinators`). Ante simulaciones infactibles, se asigna `meets_joint_criteria: None`, `delta_yield: None`, `delta_pollinators: None` y estado "No evaluable: sin soluciones admisibles dentro del dominio". | `backend/app/services/optimization.py` | `tests/revision/test_audit05_criteria_precision.py` (5 pruebas pasadas: caso de frontera de la auditoría prevenido, frontera exacta, solución claramente superior, solución inferior y ausencia de solución infactible). | **APROBADO** |

---

## 3. Detalle Técnico de las Correcciones Implementadas

### 3.1. Hallazgo 1: Configuración Única para Ejecución y Persistencia en Streamlit

#### 3.1.1. Diagnóstico del Fallo
En la implementación anterior de Streamlit convivían dos rutinas desacopladas de preparación de configuración:
1. `streamlit_app/adapter.py:prepare_streamlit_run_config` preparaba un diccionario `config_effective` y forzaba `outer_cv["group_duplicates"] = True`.
2. `streamlit_app/advanced_training.py:train_and_evaluate_all_models` no recibía `config_effective`, sino que leía de nuevo el archivo YAML/JSON desde disco o generaba valores predeterminados internos donde `group_duplicates` no quedaba sincronizado.

Esto provocó que ante una solicitud en modo exploratorio con `group_duplicates=False`:
- `config_effective.json` se guardaba con `group_duplicates=True`.
- `scientific_core/nested_cv.py:run_nested_cv` recibía y ejecutaba `group_duplicates=False`.

#### 3.1.2. Solución Canónica Implementada
1. **Unificación de Parámetros**: `train_and_evaluate_all_models` acepta un parámetro explícito `config: Optional[Dict[str, Any]] = None` y `group_duplicates: Optional[bool] = None`. Si `config` es provisto, no se recarga ninguna configuración ni se alteran sus parámetros.
2. **Propagación Directa en el Adaptador**: `execute_streamlit_training_run` construye una única `config_effective` mediante `prepare_streamlit_run_config` (o consume la provista por el llamador) y pasa exactamente esa misma instancia de diccionario a:
   - `init_run_manifest(..., config_effective=config_effective)`
   - `train_and_evaluate_all_models(..., config=config_effective)`
   - `save_run_artifacts(..., config_effective=config_effective)`
3. **Regla Metodológica Estricta de Agrupamiento (Decisión D043)**:
   En modo científico (`scientific_mode=True`), no se permite desactivar `group_duplicates`. Si el usuario o llamador intenta pasar `group_duplicates=False`, la función lanza inmediatamente un error explicativo:
   ```python
   if scientific_mode:
       if not requested_group_duplicates:
           raise ValueError(
               "Configuración científica rechazada: 'group_duplicates' no puede ser False en modo científico estricto. "
               "El protocolo metodológico exige agrupar instancias duplicadas mediante GroupKFold para prevenir fuga de datos."
           )
   ```
   En modo exploratorio (`scientific_mode=False`), se respeta fielmente la elección del usuario (`group_duplicates=False` o `True`) tanto en la ejecución como en el archivo `config_effective.json`.

---

### 3.2. Hallazgo 2: Consulta de Simulaciones Sin Solución en Chat, Historial y Reportes

#### 3.2.1. Diagnóstico del Fallo
En `backend/app/services/chat_service.py`, la función `query_simulation_details` extraía métricas del modelo optimizado asumiendo la presencia incondicional de datos:
```python
# Código vulnerable previo:
yo = _extract_metric(sim.metricas_optimas, "crop_yield_index", "rendimiento", default=0.0)
# Luego accedía a propiedades del diccionario:
"area_cultivo_pct": sim.metricas_optimas.get("crop_area_pct") # <- Fallo si metricas_optimas es None
```
Cuando un usuario del gemelo digital consultaba en el chat una simulación que había resultado infactible (`status: "infeasible"`, `metricas_optimas: None`), el sistema lanzaba:
`AttributeError: 'NoneType' object has no attribute 'get'`

Además, existía el riesgo metodológico de que otros servicios (historial de usuario o reportes gerenciales) asumieran erróneamente que una simulación infactible correspondía a métricas en cero o iguales a la línea base, distorsionando el cómputo de la tasa de éxito de la hipótesis agroecológica.

#### 3.2.2. Solución Canónica Implementada
1. **Modelo de Base de Datos**: En `backend/app/models/simulation.py`, se formalizó `metricas_optimas` como anulable:
   ```python
   metricas_optimas: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
   ```
2. **Consulta Segura en Chat Service**: En `query_simulation_details`, se evalúa explícitamente `has_opt = sim.metricas_optimas is not None and isinstance(sim.metricas_optimas, dict)`. Si `has_opt` es `False`:
   - Se retorna `tiene_solucion_optima: False` y `metricas_optimas: None`.
   - Se asigna `mejoras: {"delta_rendimiento": None, "delta_polinizadores_porcentaje": None, "estado": "no_evaluable"}`.
   - Se incluye un mensaje pedagógico claro: *"La simulación no produjo una solución óptima admisible (infactible o sin convergencia)."*
   - Se conservan estrictamente los controles de autorización por rol (`admin` vs `cliente`) y pertenencia (`sim.usuario_id == user.id`), devolviendo `status: "forbidden"` con `acceso_denegado: True` si un cliente intenta ver registros ajenos.
3. **Consumo en el Generador Local de Chat (`generate_local_fallback_reply`)**: Ante `not sim.get("tiene_solucion_optima")`, genera una respuesta transparente explicando que la simulación resultó infactible dentro de las restricciones impuestas y que no existen métricas óptimas evaluables.
4. **Resumen de Usuario (`query_simulations_summary`)**: En la lista de últimas simulaciones, las infactibles muestran `rendimiento_optimo: None`, `polinizadores_optimos: None` y `tiene_solucion_optima: False`.
5. **Reporte General de Gestión (`get_management_report`)**: En `backend/app/services/report_general_service.py`, las simulaciones con `metricas_optimas = None`:
   - No se suman a `cumplen_hipotesis` (no cumplen la hipótesis).
   - No se agregan a las listas de promedios óptimos (`yield_opt_list`, `poll_opt_list`), asegurando que el rendimiento y la abundancia promedio óptima representen únicamente las configuraciones viables reales.

---

### 3.3. Hallazgo 3: Criterio Operativo Evaluado a Precisión Completa Antes del Redondeo

#### 3.3.1. Diagnóstico del Fallo
En `backend/app/services/optimization.py` (`run_simulation`), el cálculo del criterio operativo conjunto se estructuraba del siguiente modo:
```python
# Código previo vulnerable a errores de frontera:
delta_yield = round(raw_delta_yield, 3)
delta_pollinators = round(raw_delta_pollinators, 3)

meets_joint_criteria = bool(delta_yield >= 0.0 and delta_pollinators >= 20.0)
```
Caso reproducido por la Auditoría 05:
- Rendimiento base: 100.0 | Rendimiento candidato: 99.9996 $\to$ `raw_delta_yield = -0.0004` (degradación)
- Polinizadores base: 100.0 | Polinizadores candidato: 119.9998 $\to$ `raw_delta_pollinators = 19.9998%` (< 20%)
- Al aplicar `round(..., 3)`:
  - `delta_yield = 0.000` ($\ge 0.0 \to$ True)
  - `delta_pollinators = 20.000` ($\ge 20.0 \to$ True)
  - `meets_joint_criteria = True` **(Falso positivo en frontera)**

#### 3.3.2. Solución Canónica Implementada
Se desacopló la lógica de evaluación científica de la lógica de presentación visual:
```python
raw_delta_yield = float(best_candidate["crop_yield_index"] - baseline["crop_yield_index"])
base_abund = max(1.0, float(baseline["pollinator_abundance_index"]))
raw_delta_pollinators = float(((best_candidate["pollinator_abundance_index"] - baseline["pollinator_abundance_index"]) / base_abund) * 100.0)

# Evaluación a precisión numérica COMPLETA antes de cualquier redondeo de visualización (Auditoría 05, Hallazgo 3)
meets_joint_criteria = bool(raw_delta_yield >= 0.0 and raw_delta_pollinators >= 20.0)
hypothesis_status = (
    "Criterio operativo de mejora conjunta cumplido (+20% abundancia simulada con rendimiento no degradado)"
    if meets_joint_criteria
    else "Criterio operativo de mejora conjunta no alcanzado"
)

# Redondeo para representación visual exclusivamente
delta_yield = round(raw_delta_yield, 3)
delta_pollinators = round(raw_delta_pollinators, 3)
```
Adicionalmente, ante ausencia de solución viable (`not pareto_front`):
```python
"delta_yield": None,
"delta_pollinators": None,
"hypothesis_status": "No evaluable: sin soluciones admisibles dentro del dominio",
"meets_joint_criteria": None,
```
Esto asegura que ni el backend ni el frontend confundan una simulación infactible con una simulación que "no cumplió" cuantitativamente los objetivos.

---

## 4. Verificación Integral del Sistema

### 4.1. Pruebas Unitarias y de Regresión Específicas de Auditoría 05

Se ejecutaron las 17 pruebas focalizadas de la Auditoría 05 en el contenedor científico aislado:
```bash
docker compose -p polinizadores_revision run --rm scientific pytest \
  tests/revision/test_audit05_unified_config.py \
  tests/revision/test_audit05_simulation_query_infeasible.py \
  tests/revision/test_audit05_criteria_precision.py -v
```
**Resultado**:
```
tests/revision/test_audit05_unified_config.py::test_parity_between_executed_and_persisted_config_group_duplicates_false PASSED
tests/revision/test_audit05_unified_config.py::test_parity_between_executed_and_persisted_config_group_duplicates_true PASSED
tests/revision/test_audit05_unified_config.py::test_scientific_mode_rejects_group_duplicates_false PASSED
tests/revision/test_audit05_unified_config.py::test_scientific_mode_defaults_to_group_duplicates_true PASSED
tests/revision/test_audit05_unified_config.py::test_advanced_training_respects_passed_config PASSED
tests/revision/test_audit05_simulation_query_infeasible.py::test_query_simulation_details_with_solution PASSED
tests/revision/test_audit05_simulation_query_infeasible.py::test_query_simulation_details_without_solution PASSED
tests/revision/test_audit05_simulation_query_infeasible.py::test_query_simulation_details_not_found PASSED
tests/revision/test_audit05_simulation_query_infeasible.py::test_query_simulation_details_unauthorized_access PASSED
tests/revision/test_audit05_simulation_query_infeasible.py::test_chat_fallback_generation_without_solution PASSED
tests/revision/test_audit05_simulation_query_infeasible.py::test_user_simulations_summary_with_missing_solution PASSED
tests/revision/test_audit05_simulation_query_infeasible.py::test_get_management_report_with_infeasible_simulations PASSED
tests/revision/test_audit05_criteria_precision.py::test_reproduced_boundary_false_positive_prevented PASSED
tests/revision/test_audit05_criteria_precision.py::test_exact_boundary_non_degraded_and_20pct_pollinators PASSED
tests/revision/test_audit05_criteria_precision.py::test_clearly_superior_solution PASSED
tests/revision/test_audit05_criteria_precision.py::test_clearly_inferior_solution PASSED
tests/revision/test_audit05_criteria_precision.py::test_absence_of_solution_infeasible PASSED

====================== 17 passed in 5.16s ======================
```

### 4.2. Ejecución Completa de la Suite de Regresión (113 Pruebas)

Se ejecutó la totalidad de las pruebas acumuladas en `tests/revision/`:
```bash
docker compose -p polinizadores_revision run --rm scientific pytest tests/revision/ -q
```
**Resultado**:
```
........................................................................ [ 63%]
.........................................                                [100%]
113 passed, 139140 warnings in 111.38s (0:01:51)
```
- **Total de pruebas ejecutadas**: 113
- **Aprobadas**: 113 (100%)
- **Fallidas**: 0
- **Omitidas**: 0

### 4.3. Nueva Corrida Smoke Verificada (`smoke_20261028_191444`)

Se ejecutó el pipeline completo de smoke test, exportación canónica, autovalidación de bundle y optimización:
1. `python cli.py smoke` $\to$ Generó `artifacts/revision_metodologica/smoke_20261028_191444` (Ganador: `ridge`).
2. `python cli.py export-model --run-id smoke_20261028_191444 --output-dir artifacts/revision_metodologica/smoke_20261028_191444/bundle --force-test-bundle` $\to$ Exportó `bundle_ridge_bd24bc5fdf03`.
3. `python cli.py validate-bundle --bundle-dir artifacts/revision_metodologica/smoke_20261028_191444/bundle --allow-test-bundle` $\to$ Bundle válido.
4. `python cli.py optimize --model-dir artifacts/revision_metodologica/smoke_20261028_191444/bundle --test-mode` $\to$ 2560 evaluaciones, 64 soluciones en frente de Pareto, mejor solución con rendimiento 106.19 y abundancia 119.48, cumpliendo el criterio operativo conjunto (`meets_joint_criteria: true`).
5. `sha256sum -c SHA256SUMS.txt` $\to$ 16 artefactos normalizados con integridad criptográfica verificada (OK).

### 4.4. Historial Completo de Corridas Smoke Preservadas

| Identificador de Corrida | Auditoría de Origen | Modelo Ganador | Evaluaciones NSGA-II | Soluciones Pareto | Hash Integrity | Estado |
|---|---|---|---|---|---|---|
| `smoke_20261028_060521` | Auditoría 01 | Ridge | 2560 | 64 | 16/16 OK | Preservado |
| `smoke_20261028_071815` | Auditoría 02 | Ridge | 2560 | 64 | 16/16 OK | Preservado |
| `smoke_20261028_162701` | Auditoría 03 | Ridge | 2560 | 64 | 16/16 OK | Preservado |
| `smoke_20261028_173336` | Auditoría 03 bis | Ridge | 2560 | 64 | 16/16 OK | Preservado |
| `smoke_20261028_182934` | Auditoría 04 | Ridge | 2560 | 64 | 16/16 OK | Preservado |
| `smoke_20261028_191444` | Auditoría 05 | Ridge | 2560 | 64 | 16/16 OK | **ACTIVO (Verificado)** |

---

## 5. Decisiones Metodológicas Incorporadas

Las decisiones de diseño asociadas a esta auditoría quedaron formalmente registradas en `docs/revision_metodologica/DECISIONES.md`:
- **D043**: *Configuración única de ejecución y persistencia con rechazo estricto en modo científico*.
- **D044**: *Representación formal y manejo seguro de simulaciones sin solución óptima en Chat y Reportes*.
- **D045**: *Evaluación del criterio operativo conjunto a precisión numérica completa antes del redondeo*.

---

## 6. Alcance Restante y Declaración de Límites

De conformidad con las restricciones técnicas y metodológicas del proyecto:
1. **No se ejecutó la campaña definitiva de entrenamiento**: El dataset definitivo de 320 escenarios ABM en 5 folds externos permanece reservado para la etapa final de publicación editorial.
2. **No se realizaron pruebas manuales en navegador**: Toda la verificación de Streamlit, FastAPI y modelos se realizó de forma reproducible y programática mediante pruebas de integración en Docker.
3. **No se realizaron commits ni push a repositorios remotos**: El espacio de trabajo local conserva todos los cambios listos para inspección o empaquetado formal.
4. **No se alteró el entorno global de Windows**: Todas las dependencias científicas y ejecuciones se mantuvieron confinadas en el contenedor Docker oficial `polinizadores_revision-scientific`.
