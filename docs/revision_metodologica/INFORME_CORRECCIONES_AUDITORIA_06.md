# Informe de Correcciones Técnicas — Auditoría Metodológica 06

**Proyecto**: Gemelo Digital Agroecológico para Polinizadores — Revisión Metodológica  
**Rama**: `revision-metodologica`  
**Commit base**: `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab`  
**Fecha de finalización**: 28 de octubre de 2026  
**Responsable técnico**: Antigravity (Google DeepMind)  
**Destino editorial**: Revista Ciencia y Tecnología Agropecuaria (AGROSAVIA)  
**Estado general**: VERIFICADO Y APROBADO (125/125 pruebas unitarias e integrales en Docker; nuevo smoke run `smoke_20261028_195256`, exportación canónica, validación de bundle y optimización NSGA-II validados al 100%)

---

## 1. Resumen Ejecutivo

La Auditoría Metodológica Independiente 06 examinó dos aspectos cruciales para la reproducibilidad experimental y la solidez estadística del proyecto:

1. **La trazabilidad y coherencia de la semilla pseudoaleatoria en el reajuste final del modelo sustituto**: Se observó que al ejecutar el entrenamiento en la interfaz de Streamlit con una semilla personalizada (por ejemplo, `random_state=1337`), el manifiesto y la configuración efectiva registraban dicha semilla, pero el modelo sustituto final reajustado continuaba inicializándose con la semilla por defecto `42`.
2. **La coherencia matemática en los informes de gestión (`get_management_report`)**: Al calcular los deltas y promedios comparativos entre la línea base y la optimización, el sistema calculaba el promedio base sobre todas las simulaciones históricas (incluyendo simulaciones infactibles sin solución), mientras que el promedio óptimo se calculaba únicamente sobre el subconjunto factible. Esto introducía una severa distorsión estadística por comparación no pareada (por ejemplo, ante una simulación factible con base=100 y óptimo=110, y una simulación infactible con base=1000 y óptimo=None, el sistema calculaba una base promedio de 550 y un delta erróneo de -440 en lugar del verdadero delta pareado de +10).

Bajo un enfoque estrictamente focalizado y de mínima intervención, se resolvieron ambos hallazgos:
- Se sincronizó la derivación de la semilla final canónica a partir de la configuración única efectiva en `advanced_training.py` y `adapter.py`, garantizando que tanto los modelos tradicionales (Random Forest, Ridge, XGBoost) como las arquitecturas neuronales (DNN, Bottleneck Autoencoder+MLP) utilicen de forma verificable la semilla configurada.
- Se refactorizó el servicio de agregación de informes de gestión (`report_general_service.py`) y sus esquemas Pydantic (`schemas_reports.py`) para aplicar el principio de **comparación pareada estricta** sobre la misma subpoblación de simulaciones evaluables. Las estadísticas de línea base de toda la población se preservaron pero se identificaron separadamente (`rendimiento_promedio_base_total`, etc.) sin utilizarlas en el cálculo de deltas. Los denominadores de tasa se explicitaron (`denominador_tasa = "evaluables"`), y ante la ausencia de simulaciones evaluables se devuelve ausencia de datos (`None`) en lugar de métricas o deltas fabricados con ceros.

La suite de pruebas pasó de 113 a **125 pruebas automatizadas**, todas ejecutadas y aprobadas al 100% en el entorno científico aislado Docker (`polinizadores_revision-scientific`). Asimismo, se generó la corrida smoke reproducible `smoke_20261028_195256` con integridad verificada por `sha256sum -c`.

---

## 2. Matriz de Hallazgos y Correcciones — Auditoría 06

| Hallazgo / Fallo Reproducido | Causa Raíz Identificada | Corrección Técnica Implementada | Archivos Modificados / Creados | Verificación Técnica de Regresión | Estado |
|---|---|---|---|---|---|
| **1. Semilla Efectiva del Reajuste Final** | `execute_streamlit_training_run` omitía pasar explícitamente `random_state` al invocar `train_and_evaluate_all_models`, el cual utilizaba su valor predeterminado posicional `random_state=42`, ignorando la semilla provista en el diccionario `config_effective`. | 1. `advanced_training.py` deriva `final_seed` resolviendo en primer lugar la configuración única efectiva: `int(config.get("seed") or config.get("outer_cv", {}).get("seed", random_state))`.<br>2. Se inyecta `seed=final_seed` tanto en `ModelFactory.create_model` como en `fit_and_predict_neural_outer`.<br>3. `adapter.py` propaga `effective_run_seed` en la llamada e inyecta `final_seed` y `seed` en los metadatos exportados del bundle. | `streamlit_app/adapter.py`, `streamlit_app/advanced_training.py` | `tests/revision/test_audit06_final_seed_and_paired_reports.py` (pruebas con semilla 42, semilla personalizada 1337, configuración inyectada 2026, reajuste neuronal con semilla y verificación de metadatos en bundle). | **APROBADO** |
| **2. Comparaciones Pareadas en Informes de Gestión** | `get_management_report` acumulaba las líneas base de todas las simulaciones en una sola lista global (`yield_base_list`), pero solo agregaba valores óptimos para simulaciones factibles (`yield_opt_list`). Al calcular `delta = mean(opt) - mean(base)`, comparaba poblaciones con denominadores y distribuciones no equivalentes. | 1. Implementación de acumuladores duales (totales de población vs. evaluables pareados) para rendimiento, abundancia y diversidad a nivel global, regional y temporal.<br>2. Los promedios base para cálculo de deltas y porcentajes de mejora provienen estrictamente de la población evaluable.<br>3. Los promedios base de toda la población se exponen como métricas separadas (`rendimiento_promedio_base_total`, etc.).<br>4. Se añadieron campos de recuento explícito (`simulaciones_evaluables`, `simulaciones_no_evaluables`, `denominador_tasa: "evaluables"`).<br>5. Si no hay evaluables, los deltas y promedios óptimos se definen como `None` (sin fabricar ceros). | `backend/app/schemas_reports.py`, `backend/app/services/report_general_service.py` | `tests/revision/test_audit06_final_seed_and_paired_reports.py` (Casos A a F: dispares 100->110 vs 1000->None arrojando delta=+10.0, todas factibles, todas infactibles sin ceros espurios, base de datos vacía, desglose regional y temporal pareado, y prueba numérica exacta). | **APROBADO** |

---

## 3. Detalle Técnico de las Correcciones Implementadas

### 3.1. Hallazgo 1: Semilla Efectiva del Reajuste Final

#### 3.1.1. Diagnóstico del Fallo
En `streamlit_app/advanced_training.py`, la función `train_and_evaluate_all_models` poseía la firma:
```python
def train_and_evaluate_all_models(..., random_state: int = 42, config: Optional[Dict[str, Any]] = None):
```
Al ser invocada desde `streamlit_app/adapter.py`:
```python
t_res = train_and_evaluate_all_models(
    dataframe=dataframe,
    config=config_effective,
    scientific_mode=is_scientific,
    # random_state omitido -> utilizaba el default 42
)
```
Cuando un usuario configuraba `random_state=1337`, `prepare_streamlit_run_config` grababa correctamente `"seed": 1337` en `config_effective["outer_cv"]["seed"]`. Sin embargo, en el bloque de reajuste final:
```python
final_trained_model = ModelFactory.create_model(best_family, best_params, seed=random_state)
# random_state era 42, no 1337!
```
Como consecuencia, mientras los folds de la validación cruzada anidada utilizaban la semilla de `config_effective`, el modelo sustituto final persistido y exportado era reajustado con `random_state=42`.

#### 3.1.2. Solución Canónica Implementada
1. **Derivación de Semilla Canónica**: En `train_and_evaluate_all_models`, la semilla final se obtiene directamente desde la configuración efectiva gobernante:
   ```python
   final_seed = int(
       config.get("seed")
       if config.get("seed") is not None
       else config.get("outer_cv", {}).get("seed", random_state)
   )
   ```
2. **Reajuste Tradicional y Neuronal Unificado**:
   - Modelos tradicionales: `ModelFactory.create_model(best_family, best_params, seed=final_seed)`
   - Redes neuronales (DNN / Autoencoder+MLP): `fit_and_predict_neural_outer(..., seed=final_seed)`
3. **Propagación en Adapter y Exportación**:
   - `adapter.py:execute_streamlit_training_run` extrae `effective_run_seed` y lo pasa a `train_and_evaluate_all_models`.
   - `export_streamlit_model` incluye `"final_seed": training_result.get("final_seed")` y `"seed": training_result.get("final_seed")` en el overlay de metadatos del bundle.
   - El objeto `UniversalSurrogatePredictor` almacena `"final_seed": final_seed` en su diccionario `metadata`.

---

### 3.2. Hallazgo 2: Comparaciones Pareadas en Informes de Gestión

#### 3.2.1. Diagnóstico del Fallo
En `backend/app/services/report_general_service.py`, la rutina `get_management_report` recolectaba métricas de la siguiente manera:
```python
# Código anterior defectuoso:
for s in simulations:
    yb = _extract_metric(s.metricas_base, "crop_yield_index", ...)
    yield_base_list.append(yb) # <- Siempre agregaba la base de TODAS las simulaciones

    if has_opt:
        yo = _extract_metric(s.metricas_optimas, "crop_yield_index", ...)
        yield_opt_list.append(yo) # <- Solo agregaba óptimos de simulaciones factibles

# Luego calculaba:
delta_rendimiento = mean(yield_opt_list) - mean(yield_base_list)
```
Esto violaba el principio de comparación estadística válida al comparar dos poblaciones distintas:
- `yield_base_list` contenía la línea base de simulaciones tanto factibles como infactibles.
- `yield_opt_list` contenía únicamente las simulaciones factibles.

Ante un escenario con dos simulaciones:
- Simulación A (factible): Base = 100.0, Óptimo = 110.0 (mejora real: +10.0).
- Simulación B (infactible): Base = 1000.0, Óptimo = None (sin solución admisible).
El algoritmo calculaba:
- `Base promedio` = (100 + 1000) / 2 = 550.0.
- `Óptimo promedio` = 110.0 / 1 = 110.0.
- `Delta rendimiento` = 110.0 - 550.0 = **-440.0** (degradación masiva ficticia).

#### 3.2.2. Solución Canónica Implementada
1. **Separación de Poblaciones y Comparación Pareada Estricta**:
   - Población total: Se registran las líneas base totales para describir a toda la cohorte (`rendimiento_promedio_base_total`, `abundancia_polinizadores_base_total`, `diversidad_polinizadores_base_total`).
   - Subpoblación evaluable (pareada): Para cada simulación con solución factible (`has_opt == True`), se extrae simultáneamente su base (`yb`) y su óptimo (`yo`). Los promedios base y óptimos para calcular deltas y mejoras porcentuales se calculan **estrictamente sobre esta misma subpoblación**:
     ```python
     yb_eval_mean = _mean(yield_base_eval_list)
     yo_eval_mean = _mean(yield_opt_eval_list)
     dy_mean = round(yo_eval_mean - yb_eval_mean, 3)
     ```
     En el ejemplo de prueba: `yb_eval_mean = 100.0`, `yo_eval_mean = 110.0`, `dy_mean = +10.0`.
2. **Denominadores Explícitos y Recuentos Poblacionales**:
   - Se incorporaron a `ManagementKpis`, `RegionManagementItem` y `ManagementTemporalEvolutionPoint`:
     - `simulaciones_evaluables`: Número de simulaciones con optimización factible.
     - `simulaciones_no_evaluables`: Número de simulaciones infactibles o sin optimización.
     - `denominador_tasa = "evaluables"`: La tasa de cumplimiento de la hipótesis agroecológica se calcula sobre el total evaluable:
       $$\text{tasa\_cumplimiento} = \frac{\text{cumplen\_hipotesis}}{\text{simulaciones\_evaluables}} \times 100$$
3. **Ausencia de Datos sin Fabricación de Ceros Espurios**:
   - Cuando no existen simulaciones evaluables (`simulaciones_evaluables == 0`), los campos óptimos y deltas se definen como `None` (indicando formalmente ausencia de datos evaluables), evitando mostrar ceros que induzcan a pensar que no hubo mejoras cuando en realidad no hubo soluciones factibles.
4. **Consistencia en Agrupaciones Regionales y Temporales**:
   - El mismo principio pareado se implementó rigurosamente en las tablas de evolución temporal (`evolucion_temporal`) y de comparación regional (`comparacion_regiones`).

---

## 4. Resultados de Verificación y Pruebas de Regresión

### 4.1. Pruebas Unitarias y de Integración en Contenedor Científico Aislado

Se ejecutó la suite completa en el contenedor Docker `polinizadores_revision-scientific`:
```bash
docker compose -p polinizadores_revision run --rm scientific pytest tests/revision/ -v
```

**Resultado consolidado**:
```
=============== 125 passed, 139140 warnings in 111.19s (0:01:51) ===============
```
- **Total de pruebas ejecutadas**: 125.
- **Aprobadas**: 125 (100%).
- **Fallidas**: 0.
- **Omitidas**: 0.

### 4.2. Pruebas Específicas de la Auditoría 06 (`test_audit06_final_seed_and_paired_reports.py`)

Las 12 pruebas desarrolladas para esta auditoría verificaron exhaustivamente cada caso límite:
1. `test_prepare_streamlit_run_config_sets_effective_seeds`: **APROBADO**.
2. `test_final_refit_seed_default_42`: **APROBADO** (semilla 42 verificada en predictor).
3. `test_final_refit_seed_custom_1337`: **APROBADO** (semilla personalizada 1337 verificada en predictor y modelo final).
4. `test_final_refit_seed_with_injected_config_and_different_param`: **APROBADO** (precedencia de config sobre parámetro secundario).
5. `test_neural_refit_receives_final_seed`: **APROBADO** (reajuste de red neuronal con semilla efectiva).
6. `test_execute_streamlit_training_run_end_to_end_seed`: **APROBADO** (ciclo completo Streamlit y bundle con semilla 1337).
7. `test_management_report_case_a_feasible_plus_infeasible_different_bases`: **APROBADO** (pareado 100->110 vs 1000->None da delta=+10.0 y base total=550.0).
8. `test_management_report_case_b_all_feasible`: **APROBADO** (todas factibles).
9. `test_management_report_case_c_all_infeasible`: **APROBADO** (todas infactibles retornan None y evaluables=0).
10. `test_management_report_case_d_no_records`: **APROBADO** (base vacía).
11. `test_management_report_case_e_regional_and_temporal_paired`: **APROBADO** (agregación regional y temporal pareada).
12. `test_management_report_case_f_exact_reproduction_100_110_and_1000_none`: **APROBADO** (eliminación de la distorsión numérica de la auditoría).

### 4.3. Nueva Corrida de Humo Reproducible (`smoke_20261028_195256`)

Se ejecutó el protocolo completo de verificación CLI en modo smoke:
1. **Entrenamiento y Evaluación**:
   ```bash
   python cli.py smoke
   # Run ID: smoke_20261028_195256 | Ganador: ridge
   ```
2. **Exportación Canónica de Bundle**:
   ```bash
   python cli.py export-model --run-id smoke_20261028_195256 --output-dir artifacts/revision_metodologica/smoke_20261028_195256/bundle --force-test-bundle
   # Bundle ID: bundle_ridge_bd24bc5fdf03
   ```
3. **Validación Formal de Bundle**:
   ```bash
   python cli.py validate-bundle --bundle-dir artifacts/revision_metodologica/smoke_20261028_195256/bundle --allow-test-bundle
   # Bundle válido | Predicción de prueba generada con éxito
   ```
4. **Optimización NSGA-II con Bundle**:
   ```bash
   python cli.py optimize --model-dir artifacts/revision_metodologica/smoke_20261028_195256/bundle --test-mode
   # Evaluaciones: 2560 | Soluciones devueltas: 64 | Frente verificado: 64
   # Mejor solución: Rendimiento=106.19, Abundancia=119.48
   ```
5. **Verificación Criptográfica de Integridad**:
   ```bash
   sha256sum -c SHA256SUMS.txt
   # 16/16 archivos con estado OK
   ```

---

## 5. Decisiones Metodológicas Incorporadas

Se formalizan dos nuevas decisiones en `DECISIONES.md`:
- **D046: Semilla canónica efectiva gobernante del reajuste final**: La semilla del reajuste final (tanto tradicional como neuronal) se deriva directamente del objeto de configuración efectiva único y no de parámetros posicionales secundarios o valores por defecto del llamador. Se persiste explícitamente en el manifiesto y en los metadatos del bundle universal (`final_seed`).
- **D047: Principio de comparación pareada estricta en informes de gestión**: Los cálculos comparativos (deltas y porcentajes de mejora) en informes agregados de gestión se realizan exclusivamente sobre el conjunto de simulaciones que cuentan con soluciones factibles evaluables. Las métricas base de toda la cohorte se preservan con denominación explícita separada (`_base_total`), y los denominadores de tasa se explicitan formalmente (`denominador_tasa = "evaluables"`).

---

## 6. Limitaciones Metodológicas y Próximos Pasos

1. **Campaña Definitiva No Ejecutada**: En cumplimiento estricto del alcance asignado, no se ha ejecutado la campaña final de 320 escenarios ABM ni los 5 folds definitivos. Todos los modelos y artefactos generados en esta fase permanecen formalmente etiquetados con `test_only = true` o `is_test_bundle = true`.
2. **Entorno Aislado**: Todas las verificaciones se realizaron dentro de Docker (`polinizadores_revision-scientific`), sin realizar modificaciones a paquetes globales de Windows.
3. **Evidencias Históricas Preservadas**: Las corridas históricas previas (`smoke_20261028_060521`, `smoke_20261028_071815`, `smoke_20261028_162701`, `smoke_20261028_173336`, `smoke_20261028_182934`, `smoke_20261028_191444`) se mantienen íntegras en el repositorio sin sobrescritura.
