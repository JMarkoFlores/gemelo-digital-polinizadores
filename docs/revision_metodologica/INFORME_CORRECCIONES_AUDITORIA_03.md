# Informe de Correcciones Técnicas — Auditoría Metodológica 03

**Proyecto**: Gemelo Digital Agroecológico para Polinizadores — Revisión Metodológica  
**Rama**: `revision-metodologica`  
**Commit base**: `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab`  
**Fecha de finalización**: 28 de octubre de 2026  
**Responsable técnico**: Antigravity (Google DeepMind)  
**Destino editorial**: Revista Ciencia y Tecnología Agropecuaria (AGROSAVIA)  
**Estado general**: VERIFICADO Y APROBADO (76/76 pruebas unitarias e integrales en Docker; smoke run y optimización CLI validados)

---

## 1. Resumen Ejecutivo

Una tercera auditoría técnica independiente sobre la rama `revision-metodologica` evaluó la robustez metodológica, la estabilidad de los contratos de datos y la consistencia matemática del prototipo. La revisión confirmó importantes avances previos en el aislamiento del entorno Docker, el bloqueo ante datasets inválidos, la normalización de redes neuronales, la medición de tiempos reales y el control de dominio en NSGA-II. Sin embargo, detectó siete áreas que requerían corrección obligatoria para alcanzar los estándares de rigor exigidos por la revista *Ciencia y Tecnología Agropecuaria* (AGROSAVIA):

1. **Unificación de selección y reajuste final**: Coexistencia de criterios discordantes entre Streamlit y CLI, y fallo silencioso al deserializar parámetros JSON conteniendo `null`, lo que provocaba sustitución silenciosa por `{}` y modelos finales con hiperparámetros por defecto.
2. **Centralización de la validación y carga de bundles**: Múltiples rutas de carga con deserialización de pickles previa a la comprobación de integridad SHA-256.
3. **Publicación y activación atómicas**: Falta de rollback automático ante fallos durante la exportación y necesidad de recarga atómica en memoria en `ModelStore`.
4. **Flujo científico completo en Streamlit**: Ausencia de conmutador explícito para modo científico estricto vs exploratorio, persistencia incompleta de artefactos de evaluación en Streamlit y textos de interfaz con términos obsoletos.
5. **Contratos de datos y particiones**: Validación incompleta de columnas obligatorias y duplicados de `sample_id` en `audit_dataset`, reducción automática silenciosa de folds ante pocos grupos en modo científico, e información insuficiente en `splits.json` para reconstruir particiones internas.
6. **Representatividad de suites de prueba**: Necesidad de pruebas de paridad en 4 etapas para familias neuronales (DNN y Bottleneck MLP) y pruebas de integración end-to-end con Keras en Docker.
7. **Conteo veraz de evaluaciones en NSGA-II y ejecución smoke**: Confusión entre el número total de evaluaciones realizadas por el algoritmo ($pop\_size \times n\_gen = 2560$) y el tamaño del frente no dominado retornado (64); preservación estricta de evidencias históricas en ejecuciones smoke.

Todas las correcciones fueron implementadas rigurosamente sin placeholders, eliminando sustituciones silenciosas, unificando los puntos de entrada sobre `scientific_core`, y verificando cada bloque mediante pruebas de regresión automatizadas ejecutadas en el contenedor Docker científico (`polinizadores_revision-scientific`). La suite de pruebas de revisión se incrementó a **76 pruebas (100% pasadas)**, y se generó una nueva ejecución smoke limpia (`smoke_20261028_173336`) con bundle exportado (`bundle_ridge_2950de63d7b7`) y optimización genética validada.

---

## 2. Matriz de Hallazgos y Correcciones — Auditoría 03

| Bloque / Hallazgo | Descripción del Problema | Corrección Técnica Implementada | Archivos Modificados / Creados | Verificación Técnica | Estado |
|---|---|---|---|---|---|
| **Bloque 1: Unificación de selección y reajuste final** | Streamlit seleccionaba el menor MAE interno de un fold individual en lugar de la media agregada. `advanced_training.py` usaba `ast.literal_eval` que fallaba con JSON conteniendo `null`, asignando `{}` silenciosamente (ej. RF con `n_estimators=3, max_depth=null` terminaba con 100 árboles). | Se extrajo la función canónica `select_final_hyperparameters` compartida entre CLI y Streamlit. Deserialización robusta mediante `parse_params_string` (`null` $\to$ `None`). Validación de cobertura completa de folds, desempates deterministas (MAE $\to$ RMSE $\to$ firma JSON), rechazo de no finitos, y documentación de limitaciones metodológicas de la agregación. | `scientific_core/nested_cv.py`, `streamlit_app/advanced_training.py`, `cli.py` | `tests/revision/test_audit03_final_selection.py` (4 pruebas pasadas). | **APROBADO** |
| **Bloque 2: Centralización de validación y carga de bundles** | Rutas dispares de carga (`load_bundle`, `UniversalSurrogatePredictor.load`, `ModelStore._do_load`). Verificación SHA-256 ocurría durante o tras la deserialización de pickle/h5, exponiendo el sistema a fallos de seguridad o corrupción de memoria. | `scientific_core.model_bundle.load_bundle` se consolidó como única fuente de verdad. Comprobación obligatoria previa de sumas SHA-256 antes de deserializar. Validación estricta de orden en `feature_names` y `target_names`, presencia de escaladores no nulos con dimensiones correctas, esquema y rangos observados. `ModelStore` delega exclusivamente en `load_bundle`. | `scientific_core/model_bundle.py`, `backend/app/services/model_store.py` | `tests/revision/test_audit03_bundle_validation.py` (8 pruebas pasadas). | **APROBADO** |
| **Bloque 3: Publicación y activación atómicas** | Falta de mecanismo de rollback en `export_bundle` ante fallos de escritura o validación intermedia. Posible degradación de `ModelStore` si una recarga fallaba a mitad del proceso. | `export_bundle` implementa backup temporal automático con restauración en caso de error. `bundle_id` se calcula deterministamente a partir del hash de contenido. `ModelStore` actualiza `_active_predictor` de forma atómica mediante asignación de referencia en memoria tras validación total e invalida inmediatamente la caché de simulación (`simulation_cache.clear()`). | `scientific_core/model_bundle.py`, `backend/app/services/model_store.py` | `tests/revision/test_audit03_atomic_publication.py` (2 pruebas pasadas). | **APROBADO** |
| **Bloque 4: Flujo científico completo en Streamlit** | Falta de alternador explícito científico vs exploratorio en Streamlit. Los entrenamientos en UI no persistían la totalidad de artefactos normalizados (`splits.json`, `fold_metrics.csv`, etc.). La exportación no quedaba formalmente ligada al `run_id`. Textos con terminología anticuada. | Selector de modo en UI: "Modo Científico Estricto (AGROSAVIA)" vs "Modo Exploratorio". Persistencia completa de los 11 artefactos normalizados bajo `artifacts/revision_metodologica/<run_id>`. La exportación desde Streamlit actualiza el manifiesto del run. Textos de interfaz auditados y actualizados con terminología precisa. | `streamlit_app/app.py`, `streamlit_app/advanced_training.py` | Inspección de UI y prueba en `tests/revision/test_streamlit_cli_unification.py`. | **APROBADO** |
| **Bloque 5: Contratos de datos y manejo de particiones** | `audit_dataset` no exigía de forma mandatoria la presencia de todas las columnas de entrada y salida, ni detectaba duplicados en `sample_id`. `run_nested_cv` reducía silenciosamente el número de folds si había pocos grupos en modo científico. `splits.json` no guardaba particiones internas. | En `data_audit.py`, validación obligatoria de `FEATURE_COLUMNS` y `TARGET_COLUMNS`, detección de duplicados en `sample_id`, rechazo de DataFrames vacíos y columnas no numéricas. En `nested_cv.py`, prohibición terminante de reducción silenciosa de folds en modo científico (emite `ValueError`). Persistencia exhaustiva de índices de entrenamiento, prueba y particiones internas en `splits_manifest`. | `scientific_core/data_audit.py`, `scientific_core/nested_cv.py` | `tests/revision/test_audit03_data_contract.py` (7 pruebas pasadas). | **APROBADO** |
| **Bloque 6: Suites de prueba representativas** | Ausencia de pruebas de paridad en 4 etapas para familias neuronales (DNN y Bottleneck MLP) y falta de test de integración end-to-end con Keras en Docker. | Creación de suite `test_audit03_parity_neural_all_families.py` con verificación de paridad numérica (< 1e-5) a través de las 4 etapas (evaluación $\to$ predictor pre-exportación $\to$ bundle recargado $\to$ ModelStore) para DNN y Bottleneck MLP. Prueba de integración end-to-end de Nested CV + Refit + Exportación de bundle neural en Docker. | `tests/revision/test_audit03_parity_neural_all_families.py` | 3 pruebas neuronales complejas pasadas en Docker con TensorFlow 2.17.1. | **APROBADO** |
| **Bloque 7: Conteo veraz de evaluaciones y smoke run** | Reporte de 64 candidatos evaluados en NSGA-II cuando en realidad el algoritmo realizaba 2560 evaluaciones ($pop \times gen$). Necesidad de generar un smoke run limpio preservando históricos anteriores. | `LandscapeOptimizationProblem` contabiliza rigurosamente `evaluations_count`. `run_simulation` reporta `algorithm_evaluations_total` (2560), `pareto_solutions_returned` (64) y `pareto_verified_count` (64). Nuevo smoke run `smoke_20261028_173336` ejecutado limpiamente, conservando los 3 runs previos intactos. | `backend/app/services/optimization.py`, `cli.py` | `tests/revision/test_audit03_optimization_evaluations.py` (1 prueba pasada), smoke run validado. | **APROBADO** |

---

## 3. Detalle Técnico de las Correcciones Implementadas

### 3.1. Unificación de la Selección y Reajuste Final (Bloque 1)

#### 3.1.1. Diagnóstico y Reproducción del Fallo
En la implementación anterior, mientras que el CLI ejecutaba una selección agregada mediante la media del MAE macro interno, el módulo `advanced_training.py` utilizado por Streamlit seleccionaba la fila con el menor `inner_macro_mae` absoluto entre particiones independientes:
```python
# Código defectuoso anterior en advanced_training.py
best_row = tuning_df.sort_values(by="inner_macro_mae").iloc[0]
raw_params = ast.literal_eval(best_row["params"])
```
Adicionalmente, `nested_cv.py` serializaba la cuadrícula de parámetros utilizando `json.dumps()`, produciendo literales como `{"n_estimators": 3, "max_depth": null}`. Al procesar esta cadena con `ast.literal_eval()`, Python arrojaba un `SyntaxError` (o `ValueError`) debido al identificador `null`, el bloque `except` interceptaba la excepción y sustituía silenciosamente los parámetros por `{}`:
```python
# Fallo silencioso reproducido:
# best_params quedaba en {} y RandomForestRegressor() se instanciaba con n_estimators=100
```

#### 3.1.2. Solución Canónica Implementada
1. **Deserialización Canónica (`parse_params_string`)**:
   Se implementó una rutina en `scientific_core/nested_cv.py` que intenta en primer lugar deserializar mediante `json.loads(params_str)`. En caso de cadenas generadas por representaciones legacy de diccionarios de Python (`None`, comillas simples), las normaliza de forma segura. Si la cadena está corrupta o vacía, arroja un `ValueError` explícito sin recurrir a diccionarios vacíos por defecto.
2. **Función Centralizada `select_final_hyperparameters`**:
   Ubicada en `scientific_core/nested_cv.py`, recibe el DataFrame de resultados internos (`tuning_df`) y la familia de modelos:
   - Valida que todas las filas pertenezcan a la familia solicitada.
   - Rechaza DataFrames con puntuaciones no finitas (`NaN` o `Inf`) o columnas faltantes.
   - Si `expected_n_evaluations` es provisto y `allow_adaptation=False`, exige que cada candidato haya sido evaluado en la totalidad de folds esperados ($N_{outer} \times N_{inner}$), previniendo comparaciones desbalanceadas.
   - Agrupa los candidatos por su firma canónica de parámetros JSON (`canonical_params_str`).
   - Calcula métricas agregadas: media y desviación estándar de `inner_macro_mae`, `inner_macro_rmse` y `inner_macro_r2`.
   - **Desempate determinista**:
     1. Menor `mean_inner_macro_mae`.
     2. Menor `mean_inner_macro_rmse`.
     3. Orden lexicográfico ascendente de `canonical_params_str`.
   - Propaga los hiperparámetros seleccionados con sus tipos nativos exactos (e.g., `max_depth: None`).
   - Incluye en la metadata de retorno el bloque `nota_metodologica_agregacion` describiendo que la agregación de hiperparámetros entre folds externos es una heurística para reajuste final y no sustituye la distribución de parámetros del nested CV.

---

### 3.2. Centralización y Seguridad Criptográfica de Bundles (Bloque 2)

#### 3.2.1. Diagnóstico del Riesgo
Anteriormente existían divergencias entre la carga realizada en `UniversalSurrogatePredictor.load()` y la lógica interna de `ModelStore._do_load()`. En ciertos flujos, la comprobación de sumas SHA-256 se realizaba a posteriori de la carga en memoria o quedaba dispersa, lo que representaba un riesgo de ejecución arbitraria mediante pickles manipulados antes de verificar la firma.

#### 3.2.2. Solución Implementada
Se reestructuró `scientific_core/model_bundle.load_bundle` como la única función canónica de carga y validación:
1. **Verificación previa de integridad SHA-256**:
   Antes de invocar `pickle.load` o `keras.models.load_model`, se comprueba la existencia física de cada archivo declarado en `file_hashes` dentro de `bundle_metadata.json` y se calcula su hash SHA-256 en memoria. Si algún archivo falta o la suma no coincide exactamente, la función arroja de inmediato un `ValueError` o `FileNotFoundError` sin proceder a la deserialización.
2. **Validación de esquema y metadatos**:
   - `schema_version` debe ser `"2.0"`.
   - `model_family` debe pertenecer al conjunto admitido (`ridge`, `random_forest`, `xgboost`, `dnn`, `autoencoder_mlp`).
   - `feature_names` y `target_names` deben coincidir exactamente en nombres y orden con `contracts.FEATURE_COLUMNS` y `contracts.TARGET_COLUMNS`.
   - `observed_training_ranges` debe estar presente y contener rangos válidos ($min \le max$) para todas las características de entrada.
3. **Validación de escaladores y prueba de sanidad**:
   - Se comprueba que `scalers.pkl` contenga un diccionario con `scaler_x` y `scaler_y` no nulos, con dimensiones consistentes (`n_features_in_ == 8`, `mean_.shape == (3,)`).
   - Se ejecuta una inferencia dummy con un vector de ceros `(1, 8)` verificando que la salida tenga forma `(1, 3)` y valores finitos.
4. **Delegación total en `ModelStore`**:
   `ModelStore` invoca directamente `load_bundle`. Si la carga falla, captura la excepción, emite un aviso en el registro y mantiene intacto el predictor previo en memoria.

---

### 3.3. Publicación y Activación Atómicas (Bloque 3)

#### 3.3.1. Mecanismo de Backup y Rollback en Exportación
En `scientific_core/model_bundle.export_bundle`:
- Si el directorio de destino final (`bundle_dir`) ya existe en disco, se renombra preventivamente a un directorio de respaldo temporal (`<bundle_dir>_backup_<timestamp>`).
- Se escribe el nuevo bundle en un directorio temporal aislado (`<bundle_dir>_staging_<timestamp>`).
- Se validan todos los archivos, hashes y la inferencia dummy sobre el directorio de staging.
- Tras la validación exitosa, se renombra el staging al destino final y se elimina el backup.
- Si ocurre cualquier excepción durante el proceso, el staging se elimina y el directorio de backup se restaura a su ubicación original de forma automática.

#### 3.3.2. Conmutación Atómica en `ModelStore` e Invalidación de Caché
- En `ModelStore.load()`:
  - La carga del nuevo predictor se realiza en una variable local `new_predictor = load_bundle(...)`.
  - Una vez validado, se conmuta el puntero interno `self._active_predictor = new_predictor` de forma atómica en un único paso de ejecución.
  - Inmediatamente después de la conmutación, se invoca `simulation_cache.clear()`, garantizando que ninguna solicitud posterior a la API consuma simulaciones previas generadas con el modelo anterior.

---

### 3.4. Flujo Científico Completo en Streamlit (Bloque 4)

1. **Alternador de Modo Metodológico**:
   En `streamlit_app/app.py`, la barra lateral dispone ahora de un selector de modo:
   - *Modo Científico Estricto (AGROSAVIA)*: Exige validación rigurosa de datos, particionamiento con `GroupKFold`, cálculo con dependencias científicas completas y rechazo ante cualquier inconsistencia.
   - *Modo Exploratorio*: Habilita prototipado rápido con advertencias explícitas en pantalla.
2. **Generación Exhaustiva de Artefactos**:
   Al entrenar desde Streamlit en modo científico, se invoca `run_nested_cv` y se persisten todos los artefactos estructurados en `artifacts/revision_metodologica/<run_id>/`:
   - `manifest.json` (con marcas UTC inmutables y estado `completed`).
   - `config_effective.json`, `environment.json`, `data_audit.json`, `dataset.csv`.
   - `splits.json`, `tuning_results.csv`, `fold_metrics.csv`, `oof_predictions.csv`, `model_summary.csv`.
   - `SHA256SUMS.txt` que indexa todos los archivos generados.
3. **Exportación Vinculada al Run**:
   La exportación desde la interfaz gráfica invoca la rutina oficial de exportación referenciando el `run_id` activo, actualizando el manifiesto con los datos del bundle exportado y sellando el artefacto adecuadamente.
4. **Textos y Etiquetas de Interfaz**:
   Se eliminaron términos obsoletos o que sugerían validaciones en campo no realizadas, alineando los mensajes con las declaraciones formales de AGROSAVIA.

---

### 3.5. Contratos de Datos y Manejo de Particiones (Bloque 5)

1. **Endurecimiento de `audit_dataset`**:
   - Verifica obligatoriamente que todas las 8 columnas de características y las 3 columnas de objetivos estén presentes en el DataFrame. La ausencia de cualquiera genera `audit_passed: false` y un mensaje descriptivo en `missing_columns`.
   - Detecta duplicados en `sample_id` y los reporta en `duplicate_sample_ids`.
   - Rechaza DataFrames vacíos (`len(df) == 0`).
   - Verifica que todas las variables predictoras y objetivos posean tipos numéricos (`float` o `int`).
   - Proporciona alias de compatibilidad (`"valid"`, `"is_valid"`, `"audit_passed"`).
2. **Prohibición de Reducción Silenciosa de Folds**:
   En `scientific_core/nested_cv.py`, si el dataset posee menos grupos de duplicados que el número de folds solicitado (`n_outer_folds`), el sistema en modo científico (`scientific_mode=True` o `allow_adaptation=False`) arroja un `ValueError` descriptivo en lugar de reducir silenciosamente los folds a 2 o 3.
3. **Completitud de `splits_manifest`**:
   El archivo `splits.json` generado ahora almacena la totalidad de la información necesaria para reproducir e inspeccionar las particiones:
   ```json
   {
     "outer_folds": [
       {
         "fold": 1,
         "train_indices": [0, 1, 2, ...],
         "test_indices": [40, 41, ...],
         "inner_splits": [
           {
             "inner_fold": 1,
             "in_train_indices": [0, 1, ...],
             "in_val_indices": [20, 21, ...]
           }
         ]
       }
     ]
   }
   ```

---

### 3.6. Suites de Prueba de Paridad Neural (Bloque 6)

Se implementó el archivo `tests/revision/test_audit03_parity_neural_all_families.py` con 3 pruebas completas ejecutadas directamente sobre el runtime de TensorFlow 2.17.1 en Docker:
1. **Paridad Numérica DNN (4 etapas)**:
   Verifica que las predicciones generadas por un modelo DNN Keras sean numéricamente idénticas (tolerancia absoluta $< 10^{-5}$) entre:
   - Etapa 1: Modelo Keras entrenado en memoria.
   - Etapa 2: `UniversalSurrogatePredictor` pre-exportación.
   - Etapa 3: `UniversalSurrogatePredictor` recargado desde disco vía `load_bundle`.
   - Etapa 4: `ModelStore` en backend FastAPI tras conmutación atómica.
2. **Paridad Numérica Bottleneck MLP (`autoencoder_mlp`) (4 etapas)**:
   Verifica la misma cadena de paridad para la arquitectura de cuello de botella supervisado, garantizando que el paso por el espacio latente y la inversión del escalador de salida mantengan fidelidad matemática exacta.
3. **Integración End-to-End Neural**:
   Ejecuta un ciclo completo de validación cruzada anidada con DNN sobre un dataset sintético calibrado, selecciona hiperparámetros mediante la función agregada, ejecuta el refit final, exporta el bundle, valida el bundle con SHA-256 e inferencia dummy, y confirma que el predictor recargado genera predicciones válidas y finitas.

---

### 3.7. Conteo Veraz de Evaluaciones en NSGA-II y Smoke Run Limpio (Bloque 7)

#### 3.7.1. Distinción Matemática de Evaluaciones
En `backend/app/services/optimization.py`:
- `LandscapeOptimizationProblem` mantiene un contador interno `self.evaluations_count += len(x)` incrementado en cada llamada al método `_evaluate`.
- Para un tamaño de población de 64 individuos y 40 generaciones, el algoritmo evalúa un total de:
  $$\text{Evaluaciones Totales} = \text{pop\_size} \times \text{n\_gen} = 64 \times 40 = 2560$$
- El frente de Pareto no dominado devuelto tiene una cardinalidad máxima acotada por `pop_size` (64 soluciones).
- `run_simulation` y el CLI ahora reportan explícitamente:
  - `algorithm_evaluations_total`: 2560
  - `pareto_solutions_returned`: 64
  - `pareto_verified_count`: 64
  - `pareto_candidates_evaluated`: 2560 (alias de compatibilidad)

#### 3.7.2. Smoke Run Limpio `smoke_20261028_173336`
Se ejecutó la prueba smoke integral sin alterar ni sobreescribir los runs anteriores (`smoke_20261028_060521`, `smoke_20261028_071815`, `smoke_20261028_162701`), generando el directorio `artifacts/revision_metodologica/smoke_20261028_173336`:
- 11 artefactos normalizados generados con sumas SHA-256 comprobadas.
- Bundle universal exportado: `bundle_ridge_2950de63d7b7`.
- Validación de bundle exitosa con `cli.py validate-bundle --allow-test-bundle`.
- Optimización con NSGA-II verificada: estado `success`, 2560 evaluaciones del algoritmo, 64 soluciones en frente de Pareto verificado.

---

## 4. Evidencias de Verificación Técnica

### 4.1. Ejecución de la Suite Completa de Pruebas (Docker Científico)

Comando ejecutado en el contenedor aislado:
```bash
docker compose -p polinizadores_revision run --rm scientific pytest tests/revision/ -v
```

Resultado obtenido:
```text
============================= test session starts ==============================
platform linux -- Python 3.11.18, pytest-9.2.0, pluggy-1.7.0
rootdir: /app
plugins: platformdirs-4.13.7, anyio-4.15.1
collected 76 items

tests/revision/test_aggregated_hyperparameter_selection.py .             [  1%]
tests/revision/test_audit03_atomic_publication.py ..                     [  3%]
tests/revision/test_audit03_bundle_validation.py ........                [ 14%]
tests/revision/test_audit03_data_contract.py .......                     [ 23%]
tests/revision/test_audit03_final_selection.py ....                      [ 28%]
tests/revision/test_audit03_optimization_evaluations.py .                [ 30%]
tests/revision/test_audit03_parity_neural_all_families.py ...           [ 34%]
tests/revision/test_audit_blocks_eval.py ..                              [ 36%]
tests/revision/test_bundle_atomic_cache.py ..                            [ 39%]
tests/revision/test_bundle_hardening.py .....                            [ 46%]
tests/revision/test_domain_integrated_optimization.py ...                [ 50%]
tests/revision/test_grouped_duplicates.py .                              [ 51%]
tests/revision/test_inference_parity_all_families.py ...                 [ 55%]
tests/revision/test_learned_domain_bounds.py .                           [ 56%]
tests/revision/test_linked_export.py ..                                  [ 59%]
tests/revision/test_manifest_bundle_provenance.py .                      [ 60%]
tests/revision/test_neural_config_unification.py ....                    [ 65%]
tests/revision/test_neural_nested_cv.py ...                              [ 69%]
tests/revision/test_pareto_precision.py ..                               [ 72%]
tests/revision/test_real_time_measurements.py ..                         [ 75%]
tests/revision/test_streamlit_cli_unification.py .                       [ 76%]
tests/revision/test_strict_no_fallbacks.py ....                          [ 81%]
tests/revision/test_t02_data_integrity.py ..                             [ 84%]
tests/revision/test_t03_to_t09_nested_cv.py .                            [ 85%]
tests/revision/test_t04_t05_t06_leakage_checks.py ..                     [ 88%]
tests/revision/test_t10_t11_model_bundle.py ..                           [ 90%]
tests/revision/test_t12_to_t15_optimization_domain.py ....               [ 96%]
tests/revision/test_t16_narrative_integrity.py .                         [ 97%]
tests/revision/test_true_provenance.py ..                                [100%]

====================== 76 passed, 30724 warnings in 39.08s ======================
```
**Tasa de éxito**: 76/76 pruebas superadas (100% de aprobación).

---

### 4.2. Ejecución y Validación de la Corrida Smoke (`smoke_20261028_173336`)

1. **Ejecución del smoke test**:
   ```bash
   docker compose -p polinizadores_revision run --rm scientific python cli.py smoke
   ```
   *Salida del sistema*:
   ```text
   2026-10-28 17:33:36,442 [INFO] === EJECUTANDO SMOKE TEST T19 (test_only=true) ===
   2026-10-28 17:33:36,455 [INFO] Iniciando evaluación predictiva [run_id: smoke_20261028_173336] (test_only=True)...
   2026-10-28 17:33:36,455 [INFO] Dataset generado para evaluación: 40 filas
   2026-10-28 17:33:36,462 [INFO] [CV] Iniciando Fold Externo 1/2...
   2026-10-28 17:33:36,482 [INFO] [CV] Iniciando Fold Externo 2/2...
   2026-10-28 17:33:36,589 [INFO] Ejecución completada con éxito. Artefactos guardados en: artifacts/revision_metodologica/smoke_20261028_173336
   2026-10-28 17:33:36,590 [INFO] Ganador seleccionado (menor MAE macro): ridge
   ```

2. **Exportación atómica del bundle**:
   ```bash
   docker compose -p polinizadores_revision run --rm scientific python cli.py export-model \
     --run-dir artifacts/revision_metodologica/smoke_20261028_173336 \
     --output-dir artifacts/revision_metodologica/smoke_20261028_173336/bundle \
     --force-test-bundle
   ```
   *Salida del sistema*:
   ```text
   2026-10-28 17:33:57,211 [INFO] Bundle universal exportado y verificado en: /app/artifacts/revision_metodologica/smoke_20261028_173336/bundle
   2026-10-28 17:33:57,212 [INFO] Identificador persistente de bundle: bundle_ridge_2950de63d7b7
   ```

3. **Validación de integridad del bundle**:
   ```bash
   docker compose -p polinizadores_revision run --rm scientific python cli.py validate-bundle \
     --bundle-dir artifacts/revision_metodologica/smoke_20261028_173336/bundle \
     --allow-test-bundle
   ```
   *Salida del sistema*:
   ```text
   2026-10-28 17:34:09,332 [INFO] Validando bundle en: artifacts/revision_metodologica/smoke_20261028_173336/bundle
   2026-10-28 17:34:09,355 [INFO] Bundle válido. Bundle ID: bundle_ridge_2950de63d7b7 | Tipo: ridge. Predicción test: [[80.94597625732422, 66.6535415649414, 44.796966552734375]]
   ```

4. **Optimización multiobjetivo con distinción de evaluaciones**:
   ```bash
   docker compose -p polinizadores_revision run --rm scientific python cli.py optimize \
     --model-dir artifacts/revision_metodologica/smoke_20261028_173336/bundle \
     --test-mode
   ```
   *Salida del sistema*:
   ```text
   2026-10-28 17:34:25,123 [INFO] Model loaded successfully: artifacts/revision_metodologica/smoke_20261028_173336/bundle/model_ridge.pkl (bundle: bundle_ridge_2950de63d7b7 | tipo: ridge | fuente_datos: calibrado_revision | región: Valle del Cauca (Colombia) | registros: 40)
   2026-10-28 17:34:25,123 [INFO] Ejecutando optimización de paisaje con payload: {'pesticide_level': 20.0, 'min_natural_area_pct': 20.0, 'climate_scenario': 'current', 'bbox': [3.4, -76.6, 3.6, -76.4], 'test_mode': True}
   2026-10-28 17:34:25,299 [INFO] Estado de optimización: success
   2026-10-28 17:34:25,299 [INFO] Evaluaciones totales del algoritmo (NSGA-II): 2560 | Soluciones en frente Pareto retornado: 64 | Frente Pareto verificado: 64
   2026-10-28 17:34:25,300 [INFO] Mejor solución: Rendimiento=106.19, Abundancia=119.48
   2026-10-28 17:34:25,300 [INFO] Delta Rendimiento: 0.674 | Delta Abundancia: 92.456%
   2026-10-28 17:34:25,300 [INFO] Estado de hipótesis: Criterio operativo de mejora conjunta cumplido (+20% abundancia simulada con rendimiento no degradado)
   ```

---

## 5. Conclusiones y Cumplimiento de Mandatos

1. **Unificación y Consistencia Metodológica**: Tanto la CLI como la aplicación de Streamlit operan bajo una única lógica matemática para la evaluación anidada, el escalado, la selección agregada de hiperparámetros y la exportación de modelos.
2. **Seguridad y Cero Supresiones Silenciosas**: Se eliminaron todas las sustituciones silenciosas por diccionarios vacíos o valores por defecto. Parámetros malformados, hashes discordantes o datos corruptos generan excepciones explícitas y detenciones controladas.
3. **Resiliencia Operativa**: Las cargas y exportaciones de bundles son estrictamente atómicas con rollback automático, garantizando que el servicio de inferencia no experimente caídas ni estados transitorios corruptos.
4. **Veracidad en Informes**: La distinción entre evaluaciones totales de algoritmos evolutivos (2560) y soluciones no dominadas (64) proporciona una descripción matemáticamente rigurosa para la futura publicación científica.
5. **Listo para la Campaña Definitiva**: Con 76 pruebas automatizadas aprobadas y un entorno Docker completamente validado, el sistema se encuentra en condiciones óptimas para ejecutar la campaña definitiva de 320 escenarios ABM en 5 folds cuando el usuario lo disponga.
