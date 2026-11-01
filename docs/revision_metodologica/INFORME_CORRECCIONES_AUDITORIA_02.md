# Informe de Correcciones Técnicas — Auditoría Metodológica 02

**Proyecto**: Gemelo Digital Agroecológico — Revisión Metodológica  
**Rama**: `revision-metodologica`  
**Commit base**: `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab`  
**Fecha de finalización**: 2026-10-28  
**Estado general**: VERIFICADO Y APROBADO (51/51 pruebas unitarias y de integración pasando; smoke run y optimización CLI validados)

---

## 1. Resumen Ejecutivo

Una segunda auditoría técnica independiente sobre la rama `revision-metodologica` identificó 10 hallazgos y áreas de robustecimiento en el entorno Docker, la canalización de evaluación, el modelo neuronal de sustitución, la serialización criptográfica del artefacto final, las métricas de rendimiento temporal, la selección agregada de hiperparámetros, la integración con Streamlit, la formulación matemática de cotas en NSGA-II y la completitud de metadatos en manifiestos.

Todas las discrepancias fueron analizadas en el código fuente, corregidas con implementaciones definitivas sin placeholders, verificadas mediante microentrenamientos reales y suites de prueba unitarias e integrales en contenedores Docker aislados, concluyendo con una ejecución smoke limpia (`smoke_20261028_162701`) y la exportación y validación de su bundle universal (`bundle_ridge_7e97cb6c99bc`).

---

## 2. Matriz de Hallazgos y Correcciones

| Bloque / Hallazgo | Descripción del Problema | Corrección Implementada | Verificación Técnica | Estado |
|---|---|---|---|---|
| **Bloque 1: Punto de partida y gobernanza** | Necesidad de verificar ruta, rama, commit base, git status sin descartar cambios previos y con agente único. | Verificación de rama `revision-metodologica` sobre commit `1ab7c02`. Registro estructurado de progreso en `ESTADO_IMPLEMENTACION.md`. | Inspección Git y trazabilidad continua. | **APROBADO** |
| **Bloque 2: Entorno científico Docker** | `ModuleNotFoundError: No module named 'scientific_core'` en Streamlit. Falta de dependencias científicas unificadas (5 familias, Mesa, pymoo). | Creación de `requirements-scientific.txt`, `Dockerfile.scientific`, actualización de `Dockerfile` en backend y streamlit con contexto raíz (`/app`) y `PYTHONPATH=/app`. Servicio `scientific` en Compose con prefijo aislado. | `docker compose -p polinizadores_revision run --rm scientific python -c "import scientific_core..."` (Ridge, RF, XGBoost, TF/Keras, Mesa, pymoo verificados). | **APROBADO** |
| **Bloque 3: Auditoría bloquea evaluación** | Si `crop_area_pct = 120` (`audit_passed = false`), `cmd_evaluate` continuaba y completaba con código 0. Fallback silencioso a datos sintéticos si el dataset no existía. | `cli.py` audita antes de evaluar. Si `audit_passed` es False, interrumpe inmediatamente, guarda `data_audit.json` y `dataset.csv`, registra estado `failed` en `manifest.json` y sale con código 1 sin entrenar. Si la ruta del dataset no existe, arroja `FileNotFoundError`. | Suite `test_audit_blocks_eval.py` (2 pruebas aprobadas). | **APROBADO** |
| **Bloque 4: Unificación y microentrenamiento de redes** | Parámetros de redes con nombres discordantes (`hidden_units` vs `layers`, `latent_dim` vs `bottleneck_dim`), caída en `GroupKFold` de monitorización si había 1 grupo, y falta de microentrenamientos reales. | Función `normalize_neural_params` en `nested_cv.py` con mapeo biunívoco de hiperparámetros. Propagación de `max_epochs`, `batch_size`, `patience` a las cuadrículas de búsqueda. Manejo de duplicados con fallback a KFold interno o error informativo. Arquitecturas diferenciadas en config. | Microentrenamientos reales en Keras ejecutados en Docker: suite `test_neural_config_unification.py` (4 pruebas aprobadas). | **APROBADO** |
| **Bloque 5: Robustecimiento de bundles y backend** | Falta de validación estricta de orden en `feature_names` y `target_names`; omisión de `scalers.pkl` si faltaba; sin validación criptográfica de hashes; riesgo de estado corrupto en ModelStore. | `model_bundle.py` valida orden exacto de características y objetivos contra contratos oficiales; arroja `FileNotFoundError` si falta `scalers.pkl` cuando `scaler_x_applied` es True; valida hashes SHA-256 de todos los archivos del bundle; exporta de forma atómica vía directorio temporal. `ModelStore` retiene estado previo si la recarga falla y rechaza bundles `test_only` sin flag explícito. | Suite `test_bundle_hardening.py` (5 pruebas aprobadas). | **APROBADO** |
| **Bloque 6: Tiempos reales de entrenamiento e inferencia** | Tiempos hardcodeados (`0.1` s y `0.01` s) en `advanced_training.py`. Falta de medición real de inferencia. | Medición con `time.perf_counter()` de entrenamiento e inferencia por fold y familia en `nested_cv.py`. Eliminación de constantes fijas en `advanced_training.py`. En `app.py`, renderizado de "No medido" si el valor es None/NaN. | Suite `test_real_time_measurements.py` (2 pruebas aprobadas). | **APROBADO** |
| **Bloque 7: Selección agregada y reproducible** | Selección de hiperparámetros finales vulnerable al sesgo de un único fold externo afortunado. | En `cli.py cmd_export_model`, agregación del MAE macro interno (`mean()`) sobre todos los folds internos de todas las particiones externas en `tuning_results.csv`. Registro de `final_selection_policy` con tabla de candidatos y justificación en metadatos del bundle. | Suite `test_aggregated_hyperparameter_selection.py` (1 prueba aprobada). | **APROBADO** |
| **Bloque 8: Modo científico en Streamlit** | Streamlit permitía entrenar con dependencias incompletas y sin auditar datos. | Parámetro `scientific_mode: bool = False` en `advanced_training.py` que fuerza `allow_missing_dependencies = False`. Auditoría previa de datos en `streamlit_app/app.py` que bloquea el entrenamiento ante inconsistencias. | Inspección de código y prueba unitaria en `test_streamlit_cli_unification.py`. | **APROBADO** |
| **Bloque 9: Dominio aprendido en NSGA-II** | Las cotas de optimización ignoraban los rangos aprendidos (`observed_training_ranges`), evaluando candidatos en zonas de extrapolación no confiable. | En `backend/app/services/optimization.py`, `LandscapeOptimizationProblem` intersecta límites biofísicos con los rangos observados del entrenamiento. Penalización severa (`1e5` a objetivos y `1e3` a restricciones) para individuos fuera de dominio. `filter_verified_pareto_front` garantiza que el frente Pareto cumple estrictamente el dominio aprendido. | Suite `test_domain_integrated_optimization.py` (3 pruebas aprobadas). | **APROBADO** |
| **Bloque 10: Trazabilidad en manifiestos y sumas de verificación** | Manifiesto sobrescribía `started_at_utc` al finalizar; faltaban metadatos del generador y procedencia; sumas SHA-256 incompletas o autorreferenciadas. | En `persistence.py`, preservación inmutable de `started_at_utc`, registro estructurado de `generator_metadata` y `dataset_provenance`, función `update_manifest_bundle` para poblar el bloque `bundle` al exportar. `SHA256SUMS.txt` excluye estrictamente su propio hash. | Suite `test_manifest_bundle_provenance.py` (1 prueba aprobada), smoke test `smoke_20261028_162701` e índice SHA-256 verificado. | **APROBADO** |

---

## 3. Detalle Técnico de las Soluciones Implementadas

### 3.1. Entorno de Ejecución Científico (Docker)

Se resolvieron los problemas de importación y contextos de compilación en Docker:
1. **`requirements-scientific.txt`**: Unifica en un único archivo las versiones de `scikit-learn==1.5.2`, `xgboost==2.1.1`, `tensorflow==2.17.1`, `mesa==2.3.4`, `pymoo==0.6.1.3`, `shapely==2.0.6`, `reportlab==4.2.5` y `pytest==9.2.0`.
2. **`Dockerfile.scientific`**: Imagen base Python 3.11-slim optimizada para tareas de cálculo, evaluación nested CV y optimización genética, con contexto en la raíz del proyecto.
3. **`streamlit_app/Dockerfile` y `backend/Dockerfile`**: Actualizados para fijar el contexto de construcción en la raíz del repositorio (`.`), copiando `scientific_core/` y definiendo `ENV PYTHONPATH=/app`.
4. **`docker-compose.yml`**: Define los tres servicios (`backend`, `streamlit`, `scientific`) operando bajo el prefijo de proyecto `polinizadores_revision`, con volúmenes independientes para prevenir colisiones con despliegues previos.

### 3.2. Auditoría Bloqueante y Rechazo Temprano

Se eliminó la posibilidad de entrenar modelos sobre datos corruptos o no auditados:
```python
# cli.py (cmd_evaluate)
audit_res = audit_dataset(df, policy="corrected")
if not audit_res.get("audit_passed", False):
    logger.error("Auditoría de dataset fallida. Cancelando evaluación...")
    # Registro de auditoría y manifest fallido sin entrenar
    record_run_failure(run_dir, "Auditoría de dataset fallida")
    return 1
```
Si el usuario especifica una ruta inexistente con `--dataset`, el sistema arroja inmediatamente un `FileNotFoundError` trazable en lugar de sustituir silenciosamente el archivo por datos sintéticos.

### 3.3. Unificación de Redes y Microentrenamientos

Se corrigieron las discordancias en la nomenclatura de hiperparámetros entre `configs/revision_metodologica.json` y `nested_cv.py`:
- `normalize_neural_params` mapea de forma transparente `hidden_units` a `layers`, `dropout_rate` a `dropout`, `latent_dim` a `bottleneck_dim`, `regressor_units` a `decoder_units` y `early_stopping_patience` a `patience`.
- Se propagan los hiperparámetros definidos a nivel de familia (`batch_size`, `max_epochs`, `early_stopping_patience`) a las combinaciones individuales de la cuadrícula si no fueron sobreescritos.
- En la subpartición de monitorización para EarlyStopping, si `group_duplicates` contiene menos de 2 grupos para dividir, se arroja un `ValueError` descriptivo.
- Se configuraron arquitecturas claramente diferenciadas:
  - `dnn`: Capas densas [64, 32] con Dropout(0.2).
  - `autoencoder_mlp`: Cuello de botella supervisado con dimensión latente 4 y decodificador [32].
- Cuatro microentrenamientos reales en Keras ejecutados y validados en `tests/revision/test_neural_config_unification.py`.

### 3.4. Endurecimiento de Bundles y Prevención de Degradación

1. **Orden estricto de columnas**: Se verifica que `feature_names` y `target_names` coincidan exactamente en nombre y posición con las definiciones oficiales en `scientific_core.contracts`.
2. **Presencia mandatoria de escaladores**: Si `scaler_x_applied = True`, el archivo `scalers.pkl` es estrictamente obligatorio. La ausencia del archivo genera un `FileNotFoundError`, impidiendo que el predictor opere sin estandarizar.
3. **Validación criptográfica**: Al cargar un bundle con `UniversalSurrogatePredictor.load()`, se calcula el hash SHA-256 de cada archivo físico (`model_*.pkl`/`.h5`, `scalers.pkl`) y se compara contra los hashes registrados en `bundle_metadata.json`. Si hay discrepancia, se arroja un `ValueError` por alteración de integridad.
4. **Exportación atómica**: La exportación escribe primero en un subdirectorio temporal, valida el artefacto cargándolo y ejecutando una inferencia dummy, y sólo tras la validación exitosa lo mueve atómicamente a su destino final.
5. **Resiliencia en FastAPI**: `ModelStore` preserva el modelo previamente activo si una nueva carga falla, evitando caídas del servicio web.

### 3.5. Medición Real de Tiempos de Entrenamiento e Inferencia

Se eliminaron las constantes hardcodeadas (`0.1` s y `0.01` s):
- En `nested_cv.py`, cada fold y familia registra `training_duration_seconds` y `inference_duration_seconds` utilizando `time.perf_counter()`.
- En `advanced_training.py`, los tiempos provienen de las métricas reales del CV anidado.
- Si por alguna razón el tiempo no estuviera disponible, se devuelve `None` y Streamlit muestra `"No medido"`.

### 3.6. Selección de Hiperparámetros Agregada

Para prevenir la selección de un hiperparámetro que haya obtenido buen rendimiento por azar en una partición externa particular:
- En `cli.py cmd_export_model`, se carga `tuning_results.csv` que almacena los resultados de cada fold interno evaluado.
- Se agrupan los candidatos por su firma serializada de parámetros y se calcula el `inner_macro_mae` medio a través de todas las particiones.
- La configuración con el menor error medio agregado es seleccionada para el refit final.
- La justificación y el resumen de candidatos evaluados se almacena en `final_selection_policy` dentro de `bundle_metadata.json`.

### 3.7. Modo Científico en Streamlit

- Se introdujo `scientific_mode: bool = False` en `advanced_training.py`. Cuando está activo, prohíbe `allow_missing_dependencies`.
- En `streamlit_app/app.py`, la acción de entrenamiento ejecuta primero `audit_dataset(df, policy="corrected")`. Si la auditoría no aprueba, se bloquea la ejecución y se notifica la razón técnica al usuario.

### 3.8. Integración del Dominio Aprendido en NSGA-II

Para evitar extrapolaciones arbitrarias de los modelos sustitutos:
1. `LandscapeOptimizationProblem` define sus cotas inferiores y superiores (`xl` y `xu`) a partir de la intersección entre los límites biofísicos generales (`PHYSICAL_BOUNDS`) y los rangos observados durante el entrenamiento (`observed_training_ranges`).
2. Si un candidato se desvía de los rangos observados, su función de evaluación asigna una penalización de `1e5` a las funciones objetivo y `1e3` a las restricciones biofísicas.
3. El filtrado del frente de Pareto (`filter_verified_pareto_front`) valida exhaustivamente que ninguna solución viole los límites aprendidos.
4. Si todas las soluciones resultan inviables, el optimizador devuelve `status: "infeasible"` y `best_solution: None` de forma controlada sin excepciones no capturadas.

### 3.9. Manifiestos y Sumas de Verificación Trazables

- `persistence.py` preserva inmutable la marca de tiempo original `started_at_utc`.
- Al generar el dataset, se registran los bloques `generator_metadata` y `dataset_provenance` con notas metodológicas que explicitan que se trata de datos sintéticos calibrados sin atribuciones indebidas a GBIF o NASA POWER sin ingesta comprobada.
- Al exportar el bundle, se invoca `update_manifest_bundle(run_dir, bundle_info)` para completar la sección `bundle` en `manifest.json`.
- `SHA256SUMS.txt` se genera tras completar el run y tras exportar el bundle, garantizando que el archivo `SHA256SUMS.txt` no aparezca dentro de sí mismo.

---

## 4. Evidencias de Verificación Técnica

### 4.1. Suite Completa de Pruebas Unitarias e Integración (Docker)

Comando ejecutado:
```bash
docker compose -p polinizadores_revision run --rm scientific pytest tests/revision/
```

Resultado:
```text
============================= test session starts ==============================
platform linux -- Python 3.11.18, pytest-9.2.0, pluggy-1.7.0
rootdir: /app
plugins: platformdirs-4.13.7, anyio-4.15.1
collected 51 items

tests/revision/test_aggregated_hyperparameter_selection.py .             [  1%]
tests/revision/test_audit_blocks_eval.py ..                              [  5%]
tests/revision/test_bundle_atomic_cache.py ..                            [  9%]
tests/revision/test_bundle_hardening.py .....                            [ 19%]
tests/revision/test_domain_integrated_optimization.py ...                [ 25%]
tests/revision/test_grouped_duplicates.py .                              [ 27%]
tests/revision/test_inference_parity_all_families.py ...                 [ 33%]
tests/revision/test_learned_domain_bounds.py .                           [ 35%]
tests/revision/test_linked_export.py ..                                  [ 39%]
tests/revision/test_manifest_bundle_provenance.py .                      [ 41%]
tests/revision/test_neural_config_unification.py ....                    [ 49%]
tests/revision/test_neural_nested_cv.py ...                              [ 54%]
tests/revision/test_pareto_precision.py ..                               [ 58%]
tests/revision/test_real_time_measurements.py ..                         [ 62%]
tests/revision/test_streamlit_cli_unification.py .                       [ 64%]
tests/revision/test_strict_no_fallbacks.py ....                          [ 72%]
tests/revision/test_t02_data_integrity.py ..                             [ 76%]
tests/revision/test_t03_to_t09_nested_cv.py .                            [ 78%]
tests/revision/test_t04_t05_t06_leakage_checks.py ..                     [ 82%]
tests/revision/test_t10_t11_model_bundle.py ..                           [ 86%]
tests/revision/test_t12_to_t15_optimization_domain.py ....               [ 94%]
tests/revision/test_t16_narrative_integrity.py .                         [ 96%]
tests/revision/test_true_provenance.py ..                                [100%]

====================== 51 passed, 30724 warnings in 9.75s ======================
```
**Resultado**: 51/51 pruebas superadas exitosamente (100% de aprobación).

### 4.2. Ejecución Limpia de Smoke Test (T19)

Comando ejecutado:
```bash
docker compose -p polinizadores_revision run --rm scientific python cli.py smoke
```

Salida:
```text
2026-10-28 16:27:01,068 [INFO] === EJECUTANDO SMOKE TEST T19 (test_only=true) ===
2026-10-28 16:27:01,082 [INFO] Iniciando evaluación predictiva [run_id: smoke_20261028_162701] (test_only=True)...
2026-10-28 16:27:01,082 [INFO] Dataset generado para evaluación: 40 filas
2026-10-28 16:27:01,089 [INFO] [CV] Iniciando Fold Externo 1/2...
2026-10-28 16:27:01,111 [INFO] [CV] Iniciando Fold Externo 2/2...
2026-10-28 16:27:01,242 [INFO] Ejecución completada con éxito. Artefactos guardados en: artifacts/revision_metodologica/smoke_20261028_162701
2026-10-28 16:27:01,243 [INFO] Ganador seleccionado (menor MAE macro): ridge
```

Artefactos generados en `artifacts/revision_metodologica/smoke_20261028_162701`:
- `config_effective.json`
- `dataset.csv`
- `data_audit.json`
- `environment.json`
- `fold_metrics.csv`
- `manifest.json` (con `status: "completed"`, `test_only: true`, `generator_metadata` y `dataset_provenance`)
- `model_summary.csv`
- `oof_predictions.csv`
- `splits.json`
- `tuning_results.csv`
- `SHA256SUMS.txt`

### 4.3. Exportación y Validación de Bundle

Comandos ejecutados:
```bash
docker compose -p polinizadores_revision run --rm scientific python cli.py export-model \
  --run-dir artifacts/revision_metodologica/smoke_20261028_162701 \
  --output-dir artifacts/revision_metodologica/smoke_20261028_162701/bundle_exported \
  --force-test-bundle

docker compose -p polinizadores_revision run --rm scientific python cli.py validate-bundle \
  --bundle-dir artifacts/revision_metodologica/smoke_20261028_162701/bundle_exported
```

Salida de exportación y validación:
```text
2026-10-28 16:27:25,357 [INFO] Bundle universal exportado y verificado en: /app/artifacts/revision_metodologica/smoke_20261028_162701/bundle_exported
2026-10-28 16:27:25,357 [INFO] Identificador persistente de bundle: bundle_ridge_7e97cb6c99bc

2026-10-28 16:27:38,163 [INFO] Validando bundle en: artifacts/revision_metodologica/smoke_20261028_162701/bundle_exported
2026-10-28 16:27:38,185 [INFO] Bundle válido. Bundle ID: bundle_ridge_7e97cb6c99bc | Tipo: ridge. Predicción test: [[80.94597625732422, 66.6535415649414, 44.796966552734375]]
```

### 4.4. Optimización Multiobjetivo (NSGA-II) con Bundle Exportado

Comando ejecutado:
```bash
docker compose -p polinizadores_revision run --rm scientific python cli.py optimize \
  --model-dir artifacts/revision_metodologica/smoke_20261028_162701/bundle_exported \
  --test-mode
```

Salida:
```text
2026-10-28 16:28:58,949 [INFO] Model loaded successfully: artifacts/revision_metodologica/smoke_20261028_162701/bundle_exported/model_ridge.pkl (bundle: bundle_ridge_7e97cb6c99bc | tipo: ridge | fuente_datos: calibrado_revision | región: Valle del Cauca (Colombia) | registros: 40)
2026-10-28 16:28:58,949 [INFO] Ejecutando optimización de paisaje con payload: {'pesticide_level': 20.0, 'min_natural_area_pct': 20.0, 'climate_scenario': 'current', 'bbox': [3.4, -76.6, 3.6, -76.4], 'test_mode': True}
2026-10-28 16:28:59,119 [INFO] Estado de optimización: success
2026-10-28 16:28:59,120 [INFO] Candidatos evaluados: 64 | Frente Pareto verificado: 64
2026-10-28 16:28:59,120 [INFO] Mejor solución: Rendimiento=106.19, Abundancia=119.48
2026-10-28 16:28:59,120 [INFO] Delta Rendimiento: 0.674 | Delta Abundancia: 92.456%
2026-10-28 16:28:59,120 [INFO] Estado de hipótesis: Criterio operativo de mejora conjunta cumplido (+20% abundancia simulada con rendimiento no degradado)
```

---

## 5. Conclusiones y Estado del Sistema

1. **Robustez y rigor científico**: Todos los hallazgos de la auditoría 02 fueron resueltos en su totalidad. El flujo de trabajo no presenta fallbacks silenciosos, pérdidas de precisión, fugas de datos entre particiones ni contratos incoherentes.
2. **Aislamiento absoluto**: El contenedor `scientific` permite ejecutar pruebas, evaluaciones y optimizaciones de manera independiente, desacoplada de la máquina host y preservando intactas las evidencias históricas del proyecto.
3. **Disponibilidad para la campaña definitiva**: El sistema está completamente preparado y verificado para ejecutar la futura campaña de entrenamiento definitiva (320 escenarios ABM en 5 folds) cuando sea autorizada formalmente por el usuario.
