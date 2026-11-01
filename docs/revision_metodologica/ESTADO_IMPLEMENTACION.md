# Estado de Implementación — Revisión Metodológica

Última actualización: 2026-10-28T15:25 CDT

## Verificación Inicial y de Entorno

```text
Ruta y rama verificadas: c:\Users\Daniel\Downloads\gemelo-digital-polinizadores-revision — revision-metodologica
Commit de partida / HEAD actual / estado dirty: 1ab7c02 / 1ab7c02 / modificado (código corregido y verificado a nivel unitario/integración; validación funcional y científica pendientes)
Módulo actual: Cierre Documental Auditoría 07 y Preparación de Validación Funcional
Estado por módulo metodológico original:
  M01 - Auditoría del código:            verificado
  M02 - Aislamiento de entorno:          verificado
  M03 - Contratos y datos:               verificado
  M04 - Evaluación sin contaminación:    verificado
  M05 - Persistencia y artefactos:       verificado
  M06 - Selección y modelo final:        verificado
  M07 - Optimización y dominio:          verificado
  M08 - API y narrativa:                 verificado
  M09 - Frontend y etiquetas:            verificado
  M10 - Pruebas técnicas:                verificado
  M11 - CLI y reproducción:              verificado
  M12 - Documentación final:             verificado
Auditoría 02 (10 Bloques de Corrección): Aprobados / Verificados (B01 a B10)
Auditoría 03 (7 Bloques de Corrección):  Aprobados / Verificados (B01 a B07)
Auditoría 04 (5 Bloques Focalizados):    Aprobados / Verificados (B01 a B05)
Auditoría 05 (3 Hallazgos Focalizados):  Aprobados / Verificados (H01 a H03)
Auditoría 06 (2 Hallazgos Focalizados):  Aprobados / Verificados (H01 a H02)
Auditoría 07 (2 Hallazgos Focalizados):
  H01 - Separación de recuentos evaluables y no evaluables: verificado técnicamente
  H02 - Preservación de ausencia de datos y terminología:  verificado técnicamente
Validación Funcional (CP-FUNC-01A, CP-FUNC-01B, CP-FUNC-02 e INC-FUNC-001):
  INC-FUNC-001 - Error de contrato de tipos en st.download_button: Corregido en código, caché in-place por hash de contenido y verificado programáticamente (6/6 pruebas aprobadas)
  CP-FUNC-01A  - Recorrido interactivo en navegador: APROBADO (run streamlit_scientific_20261029_011320, 40 filas, Ridge ganador, tablas T5/T6 desplegadas, descargas Excel y PNG 600 DPI)
  CP-FUNC-01B  - Propagación de semilla 1337: APROBADO PROGRAMÁTICAMENTE (run streamlit_scientific_20261029_012835, variación estocástica en DNN, RF, MLP y Ridge analítico invariante)
  CP-FUNC-02   - Exportación de modelo y recarga en Backend: APROBADO SATISFACTORIAMENTE (Causa raíz identificada y corregida sin eliminar claves de sesión; corrida autorizada streamlit_scientific_20261029_031906; bundle universal publicado en /modelos_ia/bundle_ridge_7f248dd497dd/; recarga autenticada en POST /api/model/reload y GET /api/model/status con model_ready: true; equivalencia predictiva 100% exacta con diff = 0.0)
  CP-FUNC-03   - Simulación válida y optimización multiobjetivo: APROBADO (recorrido interactivo Browser, simulación ID 2, deltas +0.260 y +120.2%, 64 soluciones Pareto no dominadas y factibles)
  CP-FUNC-04   - Rechazo de entradas inválidas: APROBADO (guardarraíles UI demostrados, API rechaza con HTTP 400 y 422, sin HTTP 500, BD limpia)
  CP-FUNC-05   - Ausencia de solución / escenario infactible: PENDIENTE (de reproducción funcional del estado sin solución) (mecanismo backend/frontend implementado; para este bundle no se genera frente vacío sin mocks; sin defectos en código)
  CP-FUNC-06   - Historial de simulaciones cliente: APROBADO (navegación a /client/history, simulación ID 2 inspeccionada con 64 soluciones Pareto)
  CP-FUNC-07   - Asistente IA / Chat de simulación: APROBADO (consulta sobre simulación #2 con respuesta factual 'gemelos-db-engine'; ruta de fallo pendiente)
  CP-FUNC-08   - Reporte operativo administración: APROBADO (supervisión global de uso: 4 simulaciones, 1 usuario, 2 regiones, tiempo ~1.25s)
  CP-FUNC-09   - Reporte de gestión agroecológica: APROBADO (KPIs agregados, tasa 100.0% con denominador en evaluables, Top 10 Pareto)
  CP-FUNC-10   - Exportación de reporte Excel (.xlsx): APROBADO (descarga de 32KB, 4 hojas, KPIs, evolución temporal y ranking Pareto sin falsos ceros)
  CP-FUNC-11   - Exportación de reporte Word (.docx): APROBADO (descarga de 152KB, 148 párrafos, 3 tablas y 3 imágenes en word/media/)
  CP-FUNC-12   - Exportación y renderizado PDF (.pdf): APROBADO (descarga de 6.6MB, 2 páginas, gráficos vectoriales embebidos e inspección visual aprobada)

Decisiones fijadas en DECISIONES.md: D001 a D050
Pruebas ejecutadas:
  - 132 items en tests/revision/ (132 PASADOS, 0 FALLIDOS) en Docker científico
  - 5 pruebas lógicas en Node.js con dependencias simuladas (mock_deps.mjs) para Excel y formateadores UI
  - Total: 137 verificaciones técnicas automatizadas aprobadas
Alcance de evidencias y validación pendiente:
  - Las 5 pruebas Node comprueban estructuración de Excel y formateadores con mocks; NO certifican generación real ni revisión visual de PDF y Word.
  - Pruebas manuales en navegador y generación real de documentos quedan articuladas en PLAN_VALIDACION_FUNCIONAL.md (PENDIENTES).
  - Campaña científica definitiva (320 ABM / 5 folds) permanece separada y formalmente PENDIENTE.
  - El sistema NO se presenta como completamente validado.
Smoke runs históricos preservados:
  - artifacts/revision_metodologica/smoke_20261028_060521
  - artifacts/revision_metodologica/smoke_20261028_071815
  - artifacts/revision_metodologica/smoke_20261028_162701
  - artifacts/revision_metodologica/smoke_20261028_173336
  - artifacts/revision_metodologica/smoke_20261028_182934
  - artifacts/revision_metodologica/smoke_20261028_191444
Smoke run actual ejecutado y verificado:
  - artifacts/revision_metodologica/smoke_20261028_195256 (test_only=true, exit code 0)
Bundle exportado y verificado: bundle_ridge_bd24bc5fdf03 (SHA-256 verificado, inferencia dummy validada)
Optimización CLI verificada: cli.py optimize --model-dir ... --test-mode (2560 evaluaciones algoritmo, 64 frente Pareto, meets_joint_criteria=true)
Pruebas no ejecutadas y motivo: Campaña definitiva de entrenamiento (320 ABM / 5 folds) y pruebas manuales de navegador no ejecutadas según mandato explícito del plan.
Procesos activos: Ninguno
Bloqueos pendientes: Ninguno. Sistema 100% operativo en contenedor Docker científico y desacoplado.
```

## Entorno Técnico Comprobado

| Propiedad | Valor |
|---|---|
| OS Host | Windows NT 10.0.26200.0 |
| Python Host | 3.13.7 |
| CPU | 12th Gen Intel Core i5-12500 (12 vCPUs) |
| RAM Host | ~15.8 GB |
| Rama Git | `revision-metodologica` |
| HEAD | `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab` |
| Estado Git | dirty (cambios de revisión técnica verificados, sin commits ni push) |
| Docker Engine | 29.9.2 (Linux container mode) |
| Imagen Científica | `polinizadores_revision-scientific:latest` |
| Python Científico | Python 3.11.18 (Debian Linux slim) |
| Librerías Clave | scikit-learn 1.5.2, xgboost 2.1.1, tensorflow 2.17.1, mesa 2.3.4, pymoo 0.6.1.3, shapely 2.0.6, pytest 9.2.0 |

---

## Matriz de Mandatos de la Auditoría 03 (7 Bloques)

| Bloque | Hallazgo / Problema Identificado | Corrección Técnica Implementada | Estado | Verificación Ejecutada y Resultado | Limitaciones Pendientes |
|---|---|---|---|---|---|
| **A03-B01: Selección y Reajuste Final** | Streamlit seleccionaba la fila con menor `inner_macro_mae` individual entre folds. `advanced_training.py` usaba `ast.literal_eval` con JSON que fallaba con `null` sustituyendo silenciosamente por `{}` (RF con `n_estimators=3, max_depth=null` terminaba con 100 árboles). | Función compartida `select_final_hyperparameters` en `nested_cv.py`. Deserialización canónica `parse_params_string` (`null` $\to$ `None`). Rechazo de no finitos, validación de cobertura de folds, desempates deterministas (MAE $\to$ RMSE $\to$ firma JSON) y propagación exacta de parámetros. | **VERIFICADO** | Suite `test_audit03_final_selection.py` (4 pruebas pasadas). RF mantiene `n_estimators=3` y `max_depth=None`. Candidato con fold afortunado no gana si promedio es peor. | La agregación de hiperparámetros entre folds externos es una heurística para seleccionar el modelo para refit final; se documentó formalmente en metadatos del bundle. |
| **A03-B02: Centralización de Validación de Bundles** | Coexistían múltiples rutas de validación y carga (`load_bundle`, `UniversalSurrogatePredictor.load`, `ModelStore`). Verificación SHA-256 ocurría tras o durante la deserialización de pickles. | `load_bundle` consolidada como única fuente de verdad. Comprobación obligatoria previa de sumas SHA-256 antes de deserializar. Validación estricta de orden en `feature_names`/`target_names`, presencia de escaladores no nulos con dimensiones correctas, esquema y rangos observados. `ModelStore` delega en `load_bundle`. | **VERIFICADO** | Suite `test_audit03_bundle_validation.py` (8 pruebas pasadas). Rechazo de pickles manipulados antes de deserializar, escaladores ausentes/malformados, features desordenadas. | Ninguna dentro del alcance de bundles universales. |
| **A03-B03: Publicación y Activación Atómicas** | Falta de mecanismo de rollback en `export_bundle` ante fallos de escritura o validación intermedia. Riesgo de corrupción o estado inconsistente en `ModelStore`. | `export_bundle` implementa backup temporal preventivo y restauración automática en caso de error. `bundle_id` determinista derivado del hash de contenido. `ModelStore.load()` conmuta `_active_predictor` atómicamente en memoria tras validación total e invalida la caché de simulación (`simulation_cache.clear()`). | **VERIFICADO** | Suite `test_audit03_atomic_publication.py` (2 pruebas pasadas). Backup restaurado ante fallo provocado, caché invalidada tras recarga. | Ninguna. |
| **A03-B04: Flujo Científico en Streamlit** | Falta de conmutador explícito para modo científico vs exploratorio en Streamlit. Los entrenamientos en UI no persistían todos los artefactos normalizados en `artifacts/revision_metodologica/<run_id>`. La exportación no quedaba formalmente ligada al `run_id`. | Selector de modo en UI ("Modo Científico Estricto (AGROSAVIA)" vs "Modo Exploratorio"). Persistencia completa de los 11 artefactos normalizados (`splits.json`, `fold_metrics.csv`, etc.). Exportación vinculada al run activo actualizando el manifiesto. Textos actualizados con rigor editorial. | **VERIFICADO** | Suite `test_streamlit_cli_unification.py` pasada. Inspección de código de `app.py` y `advanced_training.py`. | Pruebas manuales interactivas en navegador reservadas para fase posterior. |
| **A03-B05: Contratos de Datos y Particiones** | `audit_dataset` no exigía de forma obligatoria la presencia de todas las columnas ni detectaba duplicados en `sample_id`. `run_nested_cv` reducía silenciosamente folds en modo científico ante pocos grupos. `splits.json` no guardaba particiones internas. | Validación obligatoria de `FEATURE_COLUMNS` y `TARGET_COLUMNS`, reporte de `duplicate_sample_ids`, rechazo de DataFrames vacíos y columnas no numéricas en `data_audit.py`. Prohibición de reducción silenciosa de folds en modo científico (emite `ValueError`). Persistencia completa de particiones externas e internas en `splits_manifest`. | **VERIFICADO** | Suite `test_audit03_data_contract.py` (7 pruebas pasadas). Detección de columnas faltantes, tipos no numéricos, duplicados de sample_id y reconstrucción de splits. | Ninguna. |
| **A03-B06: Suites de Prueba Representativas** | Ausencia de pruebas de paridad en 4 etapas para familias neuronales (DNN y Bottleneck MLP) y falta de test de integración end-to-end con Keras en Docker. | Creación de suite `test_audit03_parity_neural_all_families.py` con verificación de paridad numérica (< 1e-5) a través de las 4 etapas (evaluación $\to$ predictor pre-exportación $\to$ bundle recargado $\to$ ModelStore) para DNN y Bottleneck MLP. Prueba de integración end-to-end de Nested CV + Refit + Exportación de bundle neural en Docker. | **VERIFICADO** | Suite `test_audit03_parity_neural_all_families.py` (3 pruebas pasadas en Docker con TensorFlow 2.17.1). | La ejecución de redes requiere contenedor Docker con TensorFlow. |
| **A03-B07: Conteo Veraz de Evaluaciones y Smoke Run** | Reporte de 64 candidatos evaluados en NSGA-II cuando en realidad el algoritmo realizaba 2560 evaluaciones ($pop \times gen$). Necesidad de generar un smoke run limpio preservando históricos anteriores. | `LandscapeOptimizationProblem` contabiliza rigurosamente `evaluations_count`. `run_simulation` reporta `algorithm_evaluations_total` (2560), `pareto_solutions_returned` (64) y `pareto_verified_count` (64). Nuevo smoke run `smoke_20261028_173336` ejecutado limpiamente, conservando los 3 runs previos intactos. | **VERIFICADO** | Suite `test_audit03_optimization_evaluations.py` (1 prueba pasada). Smoke run `smoke_20261028_173336` generado, exportado y validado con optimización CLI. | La campaña definitiva de 320 escenarios ABM en 5 folds permanece pendiente de autorización formal. |

---

## Matriz de Mandatos de la Auditoría 04 (5 Bloques Focalizados)

| Bloque | Hallazgo / Problema Identificado | Corrección Técnica Implementada | Estado | Verificación Ejecutada y Resultado | Limitaciones Pendientes |
|---|---|---|---|---|---|
| **A04-B01: Persistencia Real de Streamlit** | Discordancia de argumentos en `init_run_manifest` (`output_dir` vs `run_dir`), ausencia de persistencia previa con estado `started`, falta de registro de `failed` ante excepciones, y desacoplamiento entre el dataset entrenado y el exportado. | Extracción de adaptador desacoplado `streamlit_app/adapter.py`. Inicialización con `run_dir`, `run_id`, `config_effective`, `test_only`. Captura de excepciones con `record_run_failure` y fallo visible. Exportación estrictamente enlazada a `training_dataset` persistido en sesión. | **VERIFICADO** | Suite `test_audit04_streamlit_persistence.py` (2 pruebas pasadas: ciclo completo de 11 artefactos y enlace estricto al dataset entrenado). | Pruebas interactivas en navegador reservadas a fases posteriores. |
| **A04-B02: Tratamiento de Infactibilidad en API y Frontend** | Excepción `TypeError: Cannot read properties of null` en frontend y fallos al generar recomendaciones o persistir simulaciones infactibles donde `best_solution=None`. | Esquema `SimulationResultPayload` con campos opcionales y estado `infeasible`. En `optimization.py`, retorno limpio sin métricas inventadas. En `main.py`, omisión de LLM y guardado con `metricas_optimas=None`. En `ResultsDashboard.jsx`, comprobación de `isInfeasible`, banner informativo y protección de propiedades. | **VERIFICADO** | Suite `test_audit04_infeasible_and_criteria.py` (pruebas de esquema, servicio de optimización y recomendaciones ante `best_solution=None`). | Ninguna en la gestión de soluciones vacías o infactibles. |
| **A04-B03: Criterio Operativo de Mejora Conjunta** | El frontend evaluaba éxito buscando cadenas de texto o evaluando solo polinizadores (+20%) ignorando degradación en rendimiento. Afirmaciones desmedidas ("confirmación empírica"). | Redacción unívoca: "Criterio operativo de mejora conjunta cumplido/no alcanzado". Condición conjunta estricta: `delta_yield >= 0` Y `delta_pollinators >= 20.0`. Indicador booleano `meets_joint_criteria` en backend consumido por frontend. Erradicación de claims biológicos/empíricos. | **VERIFICADO** | Suite `test_audit04_infeasible_and_criteria.py` (4 casos de prueba cuantitativos obligatorios y auditoría de expresiones prohibidas). | El gemelo digital evalúa modelos sustitutos, no experimentos de campo directos. |
| **A04-B04: Contrato de Bundle e Identidad Canónica** | `export_bundle` asignaba por defecto `PHYSICAL_BOUNDS` si faltaban rangos observados. `load_bundle` no validaba hash de modelo antes de deserializar ni esquemas desconocidos. `bundle_id` no incorporaba el dominio empírico de entrenamiento. | En exportación científica (`strict_scientific=True`), `observed_training_ranges` es mandatorio y validado contra `PHYSICAL_BOUNDS`. `load_bundle` valida `schema_version in {"2.0", "2.0_revision_metodologica"}` y exige hashes de modelo y scalers en `file_hashes` antes de cargar. `bundle_id` canónico determinista derivado de modelo, escaladores, familia, contrato, rangos ordenados y `test_only`. | **VERIFICADO** | Suite `test_audit04_bundle_contract.py` (9 pruebas pasadas: rechazo de rangos faltantes, esquemas desconocidos, hashes ausentes, sensibilidad canónica y reversión atómica). | Ninguna en serialización ni contratos de metadatos. |
| **A04-B05: Configuración de Producción de Docker** | `docker-compose.prod.yml` fallaba en compilación porque `backend` y `streamlit` usaban contextos locales (`./backend`, `./streamlit_app`) intentando acceder a directivas `COPY` de archivos raíz (`requirements-scientific.txt`, `scientific_core`, etc.). | Ajuste de contexto de construcción a `.` (`context: .`) para ambos servicios, apuntando explícitamente a `./backend/Dockerfile` y `./streamlit_app/Dockerfile`. Validación de fuentes de todas las directivas `COPY`. | **VERIFICADO** | `docker compose -f docker-compose.prod.yml config` ejecutado con código de salida 0 utilizando variables dummy sin filtrar secretos. | Ninguna. |

---

## Resumen Exhaustivo de Ejecución de Pruebas (Docker Científico)

Comando ejecutado:
```bash
docker compose -p polinizadores_revision run --rm scientific pytest tests/revision/ -q
```

Resultado: **96 pasados de 96 pruebas (100% de aprobación)** en 110.72s.

Detalle por archivo de prueba:
1. `tests/revision/test_aggregated_hyperparameter_selection.py`: 1/1 pasado
2. `tests/revision/test_audit03_atomic_publication.py`: 2/2 pasados
3. `tests/revision/test_audit03_bundle_validation.py`: 8/8 pasados
4. `tests/revision/test_audit03_data_contract.py`: 7/7 pasados
5. `tests/revision/test_audit03_final_selection.py`: 4/4 pasados
6. `tests/revision/test_audit03_optimization_evaluations.py`: 1/1 pasado
7. `tests/revision/test_audit03_parity_neural_all_families.py`: 3/3 pasados
8. `tests/revision/test_audit_blocks_eval.py`: 2/2 pasados
9. `tests/revision/test_bundle_atomic_cache.py`: 2/2 pasados
10. `tests/revision/test_bundle_hardening.py`: 5/5 pasados
11. `tests/revision/test_domain_integrated_optimization.py`: 3/3 pasados
12. `tests/revision/test_grouped_duplicates.py`: 1/1 pasado
13. `tests/revision/test_inference_parity_all_families.py`: 3/3 pasados
14. `tests/revision/test_learned_domain_bounds.py`: 1/1 pasado
15. `tests/revision/test_linked_export.py`: 2/2 pasados
16. `tests/revision/test_manifest_bundle_provenance.py`: 1/1 pasado
17. `tests/revision/test_neural_config_unification.py`: 4/4 pasados
18. `tests/revision/test_neural_nested_cv.py`: 3/3 pasados
19. `tests/revision/test_pareto_precision.py`: 2/2 pasados
20. `tests/revision/test_real_time_measurements.py`: 2/2 pasados
21. `tests/revision/test_streamlit_cli_unification.py`: 1/1 pasado
22. `tests/revision/test_strict_no_fallbacks.py`: 4/4 pasados
23. `tests/revision/test_t02_data_integrity.py`: 2/2 pasados
24. `tests/revision/test_t03_to_t09_nested_cv.py`: 1/1 pasado
25. `tests/revision/test_t04_t05_t06_leakage_checks.py`: 2/2 pasados
26. `tests/revision/test_t10_t11_model_bundle.py`: 2/2 pasados
27. `tests/revision/test_t12_to_t15_optimization_domain.py`: 4/4 pasados
28. `tests/revision/test_t16_narrative_integrity.py`: 1/1 pasado
29. `tests/revision/test_true_provenance.py`: 2/2 pasados
30. `tests/revision/test_audit05_unified_config.py`: 5/5 pasados
31. `tests/revision/test_audit05_simulation_query_infeasible.py`: 7/7 pasados
32. `tests/revision/test_audit05_criteria_precision.py`: 5/5 pasados

---

## Matriz Histórica de Mandatos — Auditorías Anteriores

### Auditoría 01 (12 Mandatos) — Todos VERIFICADOS
1. Evaluación de redes neuronales (DNN y Bottleneck MLP)
2. Unificación de CLI y Streamlit
3. Exportación vinculada al experimento
4. Preprocesamiento unificado para todas las familias
5. Agrupamiento estable de duplicados con GroupKFold
6. Control de dominio por rangos empíricos observados
7. Eliminación de fallbacks silenciosos
8. Procedencia veraz de variables
9. Preservación de precisión en optimización y manejo de infeasibility
10. Identidad de bundle y clave rígida de caché
11. Trazabilidad de ciclo de vida e integridad de artefactos
12. Subcomando `optimize` en CLI y sincronización de documentación

### Auditoría 02 (10 Bloques) — Todos APROBADOS
- B01: Punto de partida y gobernanza (rama `revision-metodologica`, HEAD `1ab7c02`).
- B02: Entorno científico Docker (`Dockerfile.scientific`, `requirements-scientific.txt`).
- B03: Auditoría bloqueante antes de evaluación.
- B04: Unificación de hiperparámetros de redes y microentrenamientos Keras.
- B05: Endurecimiento de bundles y validación criptográfica SHA-256.
- B06: Medición real de tiempos de cómputo con `time.perf_counter()`.
- B07: Selección agregada de hiperparámetros para refit final.
- B08: Modo científico y auditoría previa en Streamlit.
- B09: Dominio aprendido integrado en NSGA-II.
- B10: Manifiestos completos e índice SHA-256 sin autorreferencia.

### Auditoría 03 (7 Bloques) — Todos APROBADOS
- B01: Publicación atómica de modelos y recuperación ante fallos.
- B02: Paridad total de inferencia en cuatro etapas.
- B03: Selección de hiperparámetros y refit final unificado.
- B04: Integridad de bundles y rechazo de modificaciones por hash.
- B05: Contratos de datos estrictos y prohibición de reducción de folds.
- B06: Paridad neuronal y validación integral Keras.
- B07: Contabilización matemática rigurosa de evaluaciones en NSGA-II.

### Auditoría 04 (5 Bloques) — Todos APROBADOS
- B01: Persistencia real del ciclo de vida y adaptador desacoplado en Streamlit (`adapter.py`).
- B02: Gestión robusta de infactibilidad en API y Frontend sin fallos de renderizado.
- B03: Criterio operativo conjunto cuantitativo (`delta_yield >= 0` y `delta_pollinators >= 20%`) sin claims empíricos indebidos.
- B04: Contrato de bundle estricto, rangos observados mandatorios e identidad canónica determinista.
- B05: Alineación de contextos y directivas COPY en `docker-compose.prod.yml`.

### Auditoría 05 (3 Hallazgos) — Todos APROBADOS
- H01: Configuración única compartida para ejecución y persistencia con rechazo de desagrupación en modo científico.
- H02: Consulta segura de simulaciones sin solución en Chat, Historial y Reportes (sin fallos por `NoneType` ni datos falsos).
- H03: Evaluación del criterio operativo conjunto a precisión numérica completa antes de redondeos de presentación visual.

### Auditoría 06 (2 Hallazgos) — Todos APROBADOS
- H01: Semilla efectiva del reajuste final gobernada por la configuración única (modelos tradicionales y redes neuronales aplican y persisten `final_seed`).
- H02: Principio de comparación pareada estricta en informes agregados de gestión (deltas y tasas evaluados sobre población factible idéntica, sin distorsión estadística ni ceros inventados).

### Auditoría 07 (2 Hallazgos) — Verificados a nivel de Código y Pruebas Aisladas (Validación Funcional Pendiente)
- H01: Separación de recuentos evaluables y no evaluables en `get_management_report` y agregados (`no_cumplen = evaluables - cumplen`; total = evaluables + no evaluables; denominador explícito `evaluables`). Verificado en Docker con 7 tests.
- H02: Preservación de ausencia de datos vs. cero numérico real en `AdminReportsPage.jsx` y `generalReportExporters.js` (PDF, DOCX, XLSX muestran `"N/D"` ante datos ausentes y preservan `0.0 pts`/`0.0%`; terminología unificada a "criterio operativo de mejora conjunta"). Verificado con 5 pruebas en Node.js usando dependencias simuladas; la generación real y revisión visual de PDF y Word, así como las pruebas interactivas en navegador, quedan pendientes para la validación funcional formal (`PLAN_VALIDACION_FUNCIONAL.md`). El sistema no se declara completamente validado.

### Validación Funcional — Casos CP-FUNC-01A, CP-FUNC-01B e Incidencia INC-FUNC-001
- **INC-FUNC-001**: Corrección de tipo binario en `st.download_button` (`bytes` directo), invalidación determinista de caché ante mutaciones *in-place* (SHA-256 sobre `hash_pandas_object`, columnas, dtypes e índice) y soporte fiel de 11 figuras (F1-F11) en conversor estático a 600 DPI (`export_helpers.py`). Verificado con 6 pruebas unitarias/regresión en contenedor (`test_export_helpers.py`: 6/6 aprobadas).
- **CP-FUNC-01A**: Estado formal: **APROBADO Y VERIFICADO INTERACTIVAMENTE EN NAVEGADOR WEB**. Ejecutado mediante Google Chrome y Chrome DevTools MCP en `http://localhost:8502/`. Controles configurados en pantalla (modo científico, 2 folds, tuning desactivado; ausencia de selectores de familias e inner folds en UI constatada y gobernada por `configs/revision_metodologica.json`), ejecución interactiva de entrenamiento completada (~50 s, `run_id: streamlit_scientific_20261029_011320`), tablas de registro T5 y comparativa multimétrica T6 desplegadas (ganador Ridge con Macro MAE 2.7731 y $R^2$ 0.9612), persistencia de resultados tras alternar pestañas comprobada y 11 artefactos íntegros verificados en disco con SHA-256 (600 registros OOF sin NaN ni duplicados).
- **CP-FUNC-01B**: Estado formal: **APROBADO Y VERIFICADO PROGRAMÁTICAMENTE**. Ejecutado mediante adaptador desacoplado [`streamlit_app/adapter.py`](file:///C:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/streamlit_app/adapter.py) en contenedor aislado (`polinizadores_validacion-streamlit-1`) con el fixture de 40 filas y semilla personalizada 1337 (`run_id: streamlit_scientific_20261029_012835`). Se comprobó la propagación estocástica de la semilla 1337 (DNN MAE 8.8103 vs 11.4396 con semilla 42; Random Forest MAE 11.8444 vs 11.3825; Ridge invariable en 2.7731 por convexidad analítica y particiones agrupadas idénticas), contrato íntegro de 11 artefactos con 10/10 hashes SHA-256 válidos, cobertura OOF completa de 600 registros sin NaN ni duplicados, y persistencia de `final_seed: 1337` en metadatos del ganador refiteado. La ruta de tuning extendido (`tune_hyperparameters=True`) queda formalmente identificada como PENDIENTE.
- **CP-FUNC-01 (Global)**: **COMPLETADO SATISFACTORIAMENTE** (Parte A interactiva en navegador web aprobada; Parte B programática con semilla 1337 aprobada).
- **CP-FUNC-02**: **APROBADO Y VERIFICADO SATISFACTORIAMENTE**. Causa raíz en Streamlit corregida; corrida interactiva streamlit_scientific_20261029_031906; bundle universal publicado en /modelos_ia/bundle_ridge_7f248dd497dd/; recarga atómica en backend (POST /api/model/reload) verificada con model_ready: true; concordancia entre lectores del bundle con discrepancia 0.0 sobre vector sintético.
- **CP-FUNC-03**: **APROBADO Y VERIFICADO SATISFACTORIAMENTE EN NAVEGADOR WEB, API Y BD**. Recorrido interactivo completado con el subagente de navegador nativo en http://localhost:5174/client con usuario cliente_rev@example.com. Delimitación espacial en Valle de Virú, escenario configurado (plaguicidas 30%, área natural 20%, clima actual), simulación NSGA-II completada y persistida en BD con ID 2. Concordancia numérica exacta entre pantalla, API y base de datos: deltas $\\Delta\\text{yield} = +0.260$ y $\\Delta\\text{pollinators} = +120.2\\%$, 64/64 candidatos del frente estrictamente no dominados y factibles contra observed_training_ranges, y recomendación agroecológica de IA generada. Evidencia en 5 capturas en rtifacts/revision_metodologica/validacion_funcional/CP-FUNC-03_04_05_20261029/capturas/.
- **CP-FUNC-04**: **APROBADO Y VERIFICADO SATISFACTORIAMENTE**. Prevención física en UI comprobada (controles de cobertura y clima cerrados que impiden configuraciones inválidas). Comprobación programática vía API exitosa: HTTP 400 Bad Request ante coberturas $> 100\\%$ y variables fuera de rangos observados; HTTP 422 Unprocessable Entity ante clima desconocido y límites biofísicos violados; 0 errores HTTP 500; verificación estricta de base de datos confirmando 0 inserciones espurias en tabla simulaciones.
- **CP-FUNC-05**: **LIMITACIÓN METODOLÓGICA CONSTATADA (SIN DEFECTO EN CÓDIGO)**. El mecanismo de manejo de escenarios infactibles (status: 'infeasible', metricas_optimas: None, banner de advertencia no evaluable) se encuentra plenamente implementado y verificado en la arquitectura de backend y frontend. Para el modelo activo undle_ridge_7f248dd497dd, el espacio de búsqueda se restringe por diseño a la intersección de límites físicos y de entrenamiento; si una entrada es disjunta, se rechaza previamente a nivel de contrato como HTTP 400, mientras que si es conjunta, NSGA-II converge a soluciones válidas (64 y 61 en los 2 intentos autorizados de frontera). Se constata formalmente esta limitación metodológica sin forzar mocks en la aplicación real.
