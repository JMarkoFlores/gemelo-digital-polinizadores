# Decisiones Metodológicas y Técnicas

## Registro de Decisiones

### D001 — Rama y punto de partida
- **Fecha**: 2026-10-28
- **Decisión**: Trabajar sobre `revision-metodologica` desde HEAD `1ab7c02`, que coincide con el commit declarado en el plan.
- **Razón**: No hay trabajo posterior; el estado es limpio.
- **Consecuencias**: No se requiere ninguna reconciliación de cambios.

### D002 — Python 3.13.7 detectado
- **Fecha**: 2026-10-28
- **Decisión**: Registrar que el Python del sistema es 3.13.7. TensorFlow puede no ser compatible con esta versión en Windows nativo. Las pruebas que requieran TF se marcarán como `skipped` con motivo.
- **Razón**: TensorFlow históricamente soporta hasta Python 3.12 en releases estables.
- **Consecuencias**: Pruebas de redes Keras se ejecutarán solo dentro de contenedor o se marcarán como pendientes. El código se implementará de forma compatible.

(Decisiones adicionales se añadirán conforme se implementen los módulos)

### D003 — Conclusión de Auditoría Inicial (M01)
- **Fecha**: 2026-10-28
- **Decisión**: Ratificar como confirmados los 13 hallazgos metodológicos y de arquitectura identificados en el plan. Preservar la fórmula unificada de diversidad `calculate_landscape_diversity` existente en `optimization.py` como único punto ya resuelto.
- **Razón**: La inspección directa del código fuente ratificó fuga de datos en `advanced_training.py:66-67`, ausencia de CV anidada, incoherencia en coberturas de paisaje y claims desmedidos en la interfaz.
- **Consecuencias**: Se procede de manera inmediata con M02 (Aislamiento de entorno) y M03 (Contratos y datos).

### D004 — Aislamiento de Entorno Docker (M02)
- **Fecha**: 2026-10-28
- **Decisión**: Eliminar `container_name` fijos en `docker-compose.yml`, parametrizar `DB_PORT` (propuesto 5433), fijar perfil `langflow` para independizar el stack de LLMs remotos, y aislar volúmenes mediante el proyecto Compose `polinizadores_revision` (`polinizadores_revision_modelos_ia_volume`, etc.).
- **Razón**: Evitar colisiones de nombres y reutilización inadvertida de volúmenes o puertos con la copia histórica u otras instancias.
- **Consecuencias**: `docker compose --project-name polinizadores_revision --env-file .env.revision config` valida la resolución correcta y aislada sin tocar servicios activos.

### D005 — Contratos y Generación Coherente de Datos (M03)
- **Fecha**: 2026-10-28
- **Decisión**: Implementar `scientific_core/contracts.py`, `scientific_core/data_audit.py` y `scientific_core/generator.py` para garantizar la física de coberturas excluyentes (suma de cultivo + natural + franjas florales <= 100%) y la consistencia en el cálculo de `landscape_diversity`.
- **Razón**: El generador anterior muestreaba independientemente porcentajes que podían sumar hasta 142%, y la diversidad del paisaje se calculaba de forma distinta entre entrenamiento e inferencia.
- **Consecuencias**: `audit_dataset` rechaza anomalías (NaN, Inf, sumas inválidas, duplicados desordenados). Prueba T02 ejecutada y aprobada.

### D006 — Evaluación Predictiva Sin Contaminación (M04)
- **Fecha**: 2026-10-28
- **Decisión**: Implementar `scientific_core/nested_cv.py` con CV anidada estricta (5 folds externos, 3 internos), eliminando por completo el escalado global de salidas previo al split. En cada partición, `StandardScaler` de salidas se ajusta únicamente sobre los datos de entrenamiento autorizados.
- **Razón**: Corregir el hallazgo crítico H01 (fuga de datos en salidas) y H02 (tuning sobre el dataset completo).
- **Consecuencias**: Pruebas T03 (disyunción y cobertura de folds), T04 (ajuste estricto de escalador), T06 (aislamiento de instancias entre folds), T07 (OOF completo sin NaNs), T08 (reconstrucción descriptiva exacta) y T09 (selección por menor MAE macro) ejecutadas y aprobadas al 100%. Se documenta formalmente que Autoencoder+MLP actúa como un cuello de botella supervisado sin función de reconstrucción no supervisada.

### D007 — Persistencia, Artefactos y Predictor Universal (M05 y M06)
- **Fecha**: 2026-10-28
- **Decisión**: Implementar `scientific_core/persistence.py` (con `manifest.json`, `splits.json`, `oof_predictions.csv`, `fold_metrics.csv` e índice `SHA256SUMS.txt`) y `scientific_core/model_bundle.py` con `UniversalSurrogatePredictor`. Soportar tanto modelos de Scikit-Learn/XGBoost (`.pkl`) como Keras (`.h5`), validando la equivalencia numérica exacta de predicciones antes y después de exportar.
- **Razón**: El backend y scripts anteriores asumían obligatoriamente que el modelo activo era una red Keras `.h5`, impidiendo desplegar un ganador tradicional como Ridge o Random Forest y hardcodeando métricas en 0.
- **Consecuencias**: Pruebas T10 (serialización y re-carga con predicciones idénticas) y T11 (rechazo de metadatos o artefactos incoherentes) ejecutadas y aprobadas al 100%.

### D008 — Escenarios, Dominio, Optimización y Caché (M07)
- **Fecha**: 2026-10-28
- **Decisión**: En `backend/app/services/optimization.py` y `model_store.py`:
  1. Validar estrictamente escenarios climáticos (`current`, `warm`, `dry`, `extreme`) arrojando `ValueError` ante códigos desconocidos en vez de usar silenciosamente el fallback.
  2. Comprobar el dominio de la línea base (rangos univariados y balance físico de coberturas).
  3. Realizar predicciones a precisión completa (`float32`/`float64`) sin redondeo previo de candidatos.
  4. Filtrar el frente de Pareto a precisión completa eliminando soluciones dominadas y duplicadas (`filter_verified_pareto_front`).
  5. Incluir la versión y metadatos del modelo en la clave SHA-256 de caché para invalidar resultados antiguos tras recargar el modelo.
  6. Actualizar terminología en respuestas: "Criterio operativo de mejora conjunta cumplido/no alcanzado".
- **Razón**: Corregir H06 (clima heurístico sin validación, redondeo prematuro), H08 (dominio sin control) e H13 (etiquetas engañosas).
- **Consecuencias**: Pruebas T12 (rechazo de clima/dominio inválido), T13 (diversidad unificada), T14 (filtrado Pareto riguroso) y T15 (invalidación de caché por versión de modelo) ejecutadas y aprobadas al 100%.

### D009 — Evaluación rigurosa de redes y aislamiento de monitorización (Mandato 1)
- **Fecha**: 2026-10-28
- **Decisión**: Implementar formalmente en `scientific_core/nested_cv.py` la evaluación para DNN y Supervised Bottleneck MLP (`autoencoder_mlp`). Para prevenir fuga interna de datos y selección optimista por EarlyStopping, el subconjunto de entrenamiento interno se subparticiona en un núcleo de entrenamiento (80%) y una subpartición de monitorización (20%) respetando los grupos de duplicados. Los transformadores `StandardScaler` se ajustan exclusivamente sobre el núcleo de entrenamiento. El EarlyStopping supervisa únicamente la pérdida de la subpartición de monitorización. Las épocas óptimas alcanzadas se registran por fold interno y su mediana determina la política de épocas para el reajuste externo sobre todo el entrenamiento del fold, prediciendo finalmente en escala original sobre el test externo sin peeking.
- **Razón**: Corregir la discrepancia crítica donde la rama de redes contenía un `pass` y provocaba fallos de tipo al enviar un diccionario a `fit_and_predict_traditional`.
- **Consecuencias**: El código neural queda 100% completo, libre de fuga de datos. La prueba aislada `tests/revision/test_neural_nested_cv.py` verifica matemáticamente el aislamiento, y se documenta el comando exacto para ejecución con TensorFlow en Docker.

### D010 — Unificación de CLI y Streamlit sobre el núcleo científico (Mandato 2)
- **Fecha**: 2026-10-28
- **Decisión**: Adaptar `streamlit_app/advanced_training.py` y `streamlit_app/app.py` para que utilicen exclusivamente `scientific_core.nested_cv.run_nested_cv`, eliminando el sintonizado previo global de hiperparámetros (`tune_all_hyperparameters` antes de CV) y el escalado de salidas global. El modelo ganador se ajusta mediante el protocolo documentado de refit sobre el conjunto de desarrollo completo y se encapsula en un `UniversalSurrogatePredictor`. En `app.py`, la exportación de modelos utiliza `export_bundle` para exportar la familia ganadora real con sus escaladores y metadatos unificados (eliminando la restricción arbitraria que forzaba Keras `.h5` y métricas ficticias).
- **Razón**: Corregir la discrepancia crítica donde Streamlit continuaba ejecutando rutas heredadas con fuga de datos y contratos ficticios.
- **Consecuencias**: `test_streamlit_cli_unification.py` verifica la ejecución sin fugas, la integridad del contrato `results_df`, el cálculo no nulo de métricas y la funcionalidad del predictor universal.

### D011 — Exportación de modelos vinculada a ejecuciones evaluadas (Mandato 3)
- **Fecha**: 2026-10-28
- **Decisión**: Eliminar en `cli.py` la regeneración sintética de datos y parámetros vacíos durante `export-model`. El subcomando ahora exige `--run-dir` o `--run-id` de una ejecución con estado `completed`, verifica la correspondencia criptográfica de `dataset.csv`, recupera la familia ganadora y sus hiperparámetros óptimos desde `tuning_results.csv`, y ejecuta el protocolo documentado de refit final sobre los datos del experimento. Si el run fue una prueba smoke, el bundle resultante queda sellado con `test_only=true`.
- **Razón**: Corregir la discrepancia crítica donde `cli.py export-model` generaba 100 muestras sintéticas no vinculadas a la evaluación científica.
- **Consecuencias**: `test_linked_export.py` verifica el rechazo de runs incompletos, la trazabilidad del dataset y la marcación obligatoria de `test_only`.

### D012 — Contrato único de preprocesamiento y paridad de inferencia (Mandato 4)
- **Fecha**: 2026-10-28
- **Decisión**: Eliminar el condicional que restringía la aplicación de `scaler_x` a Ridge o Redes en `UniversalSurrogatePredictor` y `ModelStore`. Si un transformador `scaler_x` fue ajustado en el entrenamiento (como ocurre en `fit_and_predict_traditional`), se aplica de forma idéntica a todas las familias de modelos (Ridge, Random Forest, XGBoost, DNN, Autoencoder). Se valida formalmente la paridad numérica a través de las 4 etapas: modelo evaluado -> predictor pre-exportación -> predictor recargado -> `ModelStore` de FastAPI.
- **Razón**: Corregir la discrepancia crítica donde Random Forest y XGBoost eran entrenados con entradas escaladas pero recibían entradas crudas en inferencia y backend.
- **Consecuencias**: `test_inference_parity_all_families.py` verifica paridad numérica exacta (diferencia máxima < 4e-6) entre las 4 etapas para familias tradicionales, documentando el comando de verificación en Docker para XGBoost.

### D013 — Agrupamiento estable de duplicados mediante GroupKFold (Mandato 5)
- **Fecha**: 2026-10-28
- **Decisión**: Implementar `compute_feature_groups` en `scientific_core/nested_cv.py` para asignar identificadores enteros estables a filas con vectores de características idénticos (dentro de tolerancia numérica), con independencia de sus `sample_id` o posibles etiquetas estocásticas distintas. Cuando `group_duplicates: true` está activo en la configuración, se utiliza `GroupKFold` tanto para las particiones externas como para las internas y la subpartición de monitorización de redes, impidiendo de forma matemáticamente demostrada que réplicas de un mismo escenario crucen entre entrenamiento y evaluación.
- **Razón**: Corregir la discrepancia donde la configuración declaraba `group_duplicates: true` pero el código ejecutaba `KFold` ordinario, provocando fuga de información entre particiones.
- **Consecuencias**: `test_grouped_duplicates.py` demuestra formalmente que la intersección de grupos entre entrenamiento y test es 0 en todos los folds.

### D014 — Control de dominio basado en rangos observados de entrenamiento (Mandato 6)
- **Fecha**: 2026-10-28
- **Decisión**: Separar conceptual y programáticamente en `contracts.py` y `ModelStore.check_domain` los límites biofísicos generales (`PHYSICAL_BOUNDS`) de los rangos empíricos observados en el dataset de entrenamiento (`observed_training_ranges`). En modo científico estricto, cualquier candidato o línea base que exceda los rangos del dataset entrenado se rechaza como fuera de dominio (ej. 23.55 °C es rechazado si el bundle indica 14.31–18.69 °C, aun estando dentro de los límites físicos 5–45 °C). Se incluye de forma obligatoria la advertencia de que el cumplimiento univariado no demuestra la pertenencia al soporte conjunto multidimensional.
- **Razón**: Corregir la discrepancia donde `check_domain` utilizaba límites generales amplios y permitía extrapolaciones fuera de la distribución del entrenamiento.
- **Consecuencias**: `test_learned_domain_bounds.py` verifica el rechazo específico del caso 23.55 °C vs [14.31, 18.69] °C, la validación de suma de coberturas y la emisión del aviso metodológico de soporte conjunto.

### D015 — Eliminación de fallbacks científicos silenciosos (Mandato 7)
- **Fecha**: 2026-10-28
- **Decisión**: Prohibir de forma terminante que fallos en dependencias clave (Mesa para ABM o pymoo para NSGA-II) deriven en continuación silenciosa en modo científico. Si se solicita `corrected_full` y Mesa falla o no se completa el 100% de las simulaciones, el generador arroja un `RuntimeError` explícito. De igual forma, en `run_simulation`, la ausencia de pymoo en modo científico arroja un error claro impidiendo el uso de muestreos aleatorios como sustituto encubierto de NSGA-II. Los modelos habilitados en configuración que carezcan de librerías instaladas arrojan error en ejecución científica en lugar de ser omitidos silenciosamente. Los dobles de prueba quedan reservados exclusivamente para ejecuciones marcadas con `test_mode=True`.
- **Razón**: Corregir la discrepancia crítica donde el generador devolvía un dataset solicitado como `corrected_full` con cero simulaciones ante fallos del ABM y la optimización recurría a muestreos no rigurosos.
- **Consecuencias**: `test_strict_no_fallbacks.py` verifica la emisión de excepciones explícitas y la detención de procesos ante dependencias faltantes en modo científico.

### D016 — Procedencia veraz de datos e integridad de versionado (Mandato 8)
- **Fecha**: 2026-10-28
- **Decisión**: Modificar `classify_column_provenance` en `scientific_core/data_audit.py` para condicionar la clasificación de variables a la evidencia real declarada en los metadatos de generación o importación, y no al nombre de la columna. Los datasets generados por `scientific_core.generator` se etiquetan formalmente como `sintetico_generado` (versión `v2_corrected`), preservando la referencia a `v1_historical`, y sus columnas climáticas se clasifican como `variable_climatica_sintetica_calibrada`. Solo se atribuye a NASA POWER o GBIF si existen snapshots o hashes de importación verificados.
- **Razón**: Corregir la discrepancia donde la auditoría clasificaba columnas como provenientes de NASA POWER simplemente por llamarse `temperature_c` o `precipitation_mm`.
- **Consecuencias**: `test_true_provenance.py` verifica la ausencia de claims infundados en datasets sintéticos y la correcta asignación ante evidencia documental.

### D017 — Preservación de precisión en optimización y manejo de inadmisibilidad (Mandato 9)
- **Fecha**: 2026-10-28
- **Decisión**: Eliminar los redondeos prematuros a 2 y 3 decimales en `summarize_candidate` y `filter_verified_pareto_front`. Las variables de decisión y los objetivos de los candidatos se almacenan y comparan con precisión de coma flotante continua (`float32`/`float64`). La deduplicación se realiza con una tolerancia numérica explícita (`decision_atol=1e-5`) y la dominancia de Pareto se evalúa a precisión completa (`objective_tol=1e-7`), evitando descartar soluciones distintas por aproximación superficial. Si ningún candidato cumple el dominio biofísico y de modelo, la función `run_simulation` retorna explícitamente `status='infeasible'` y `best_solution=None`, suprimiendo la asignación forzada del primer candidato.
- **Razón**: Corregir la discrepancia donde el redondeo previo fusionaba candidatos y descartaba soluciones dominantes legítimas, y la ausencia de frente seleccionaba forzadamente candidatos inadmisibles.
- **Consecuencias**: `test_pareto_precision.py` verifica la resolución entre candidatos casi idénticos y el reporte veraz de estados no admisibles.

### D018 — Bundle ID persistente, activación atómica y clave de caché rígida (Mandato 10)
- **Fecha**: 2026-10-28
- **Decisión**: Implementar un identificador persistente `bundle_id` en `UniversalSurrogatePredictor` y `bundle_metadata.json`. En `ModelStore._do_load()`, la carga y validación de integridad se realiza sobre variables locales candidatas antes de conmutar el estado del servicio. Si un bundle nuevo en disco está corrupto o es inválido, el modelo funcional previamente cargado se preserva intacto sin degradar el backend. La clave canónica de caché de simulación (`build_cache_key`) incorpora de forma obligatoria el `bundle_id`, y cualquier conmutación de bundle activa la invalidación completa (`simulation_cache.clear()`).
- **Razón**: Corregir la discrepancia donde la carga fallida destruía el modelo activo y la clave de caché no aislaba rigurosamente diferentes artefactos con versiones idénticas.
- **Consecuencias**: `test_bundle_atomic_cache.py` demuestra la preservación de modelos operativos ante fallos de recarga y el aislamiento estricto de caché.

### D019 — Trazabilidad de ciclo de vida e integridad de artefactos (Mandato 11)
- **Fecha**: 2026-10-28
- **Decisión**: Implementar `init_run_manifest` y `record_run_failure` en `scientific_core/persistence.py` para asegurar que todo experimento comience registrando formalmente el estado `started` con marcas de tiempo UTC. Si ocurre una interrupción o excepción, el manifest se actualiza a `failed` registrando el mensaje de error. Solo tras la generación exitosa y validación de todos los archivos se conmuta a `completed`. `generate_sha256sums` indexa todos los archivos generados en el directorio del run (incluyendo el subdirectorio del bundle si se exporta allí) y excluye estrictamente a `SHA256SUMS.txt` de su propio cálculo.
- **Razón**: Corregir la discrepancia donde los manifiestos no registraban estados preliminares ni fallos, y los hashes del bundle faltaban en el índice de sumas de verificación.
- **Consecuencias**: Nueva ejecución limpia `smoke_20261028_071815` generada sin alterar el directorio histórico, con todos los artefactos y hashes verificados.

### D020 — CLI integral desacoplada con optimización y comandos sincronizados (Mandato 12)
- **Fecha**: 2026-10-28
- **Decisión**: Incorporar el subcomando `optimize` en `cli.py` con parámetros para nivel de pesticidas, área natural mínima, escenario climático, bounding box o archivo GeoJSON, y soporte de `--model-dir`. Sincronizar todos los argumentos y comandos en la documentación con los flags reales del CLI.
- **Razón**: Corregir la discrepancia donde el subcomando `optimize` no estaba implementado en `cli.py` a pesar de estar documentado en los reportes previos.
- **Consecuencias**: `cli.py optimize` probado y operativo tanto en modo científico estricto como en modo desacoplado (`--test-mode`).

### D021 — Entorno científico Docker unificado y resolución de contexto de importación (Auditoría 02, Bloque 2)
- **Fecha**: 2026-10-28
- **Decisión**: Crear `requirements-scientific.txt` consolidando versiones compartidas de Scikit-Learn (1.5.2), XGBoost (2.1.1), TensorFlow (2.17.1), Mesa (2.3.4), pymoo (0.6.1.3), Shapely (2.0.6) y pytest (9.2.0). Construir un servicio `scientific` en `docker-compose.yml` con `Dockerfile.scientific` y reconfigurar los contextos de build de `streamlit_app/Dockerfile` y `backend/Dockerfile` para situar el contexto en la raíz del repositorio (`.`) estableciendo `PYTHONPATH=/app`.
- **Razón**: Resolver el fallo `ModuleNotFoundError: No module named 'scientific_core'` en Streamlit y dotar al proyecto de un entorno aislado donde se pueden ejecutar y verificar las 5 familias de modelos sustitutos y el solucionador genético.
- **Consecuencias**: Acceso reproducible y verificado a `scientific_core`, `cli.py`, `configs` y tests dentro del contenedor Docker sin dependencias globales en el host.

### D022 — Bloqueo mandatorio de evaluación ante inconsistencias en auditoría de datos (Auditoría 02, Bloque 3)
- **Fecha**: 2026-10-28
- **Decisión**: En `cli.py cmd_evaluate`, ejecutar `audit_dataset(df, policy="corrected")` de forma preliminar al entrenamiento. Si `audit_passed` es False (e.g. `crop_area_pct = 120`), detener de inmediato la ejecución, persistir `data_audit.json` y `dataset.csv`, marcar el run con estado `failed` en `manifest.json` y retornar código de salida 1 sin entrenar. Si el archivo indicado en `--dataset` no existe, arrojar un error explícito `FileNotFoundError` en lugar de generar datos sintéticos silenciosamente.
- **Razón**: Eliminar la conducta donde datasets anómalos completaban la evaluación con código de éxito 0 y prevenir la sustitución encubierta de datasets no encontrados.
- **Consecuencias**: Verificado con la suite `tests/revision/test_audit_blocks_eval.py`.

### D023 — Unificación de nomenclatura y microentrenamientos reales en redes (Auditoría 02, Bloque 4)
- **Fecha**: 2026-10-28
- **Decisión**: Implementar `normalize_neural_params` en `scientific_core/nested_cv.py` para mapear de manera biunívoca `hidden_units` <-> `layers`, `dropout_rate` <-> `dropout`, `latent_dim` <-> `bottleneck_dim`, `regressor_units` <-> `decoder_units` y `early_stopping_patience` <-> `patience`. Propagar parámetros definidos a nivel de familia (`batch_size`, `max_epochs`, `patience`) a las cuadrículas de hiperparámetros. Manejar el caso de pocos grupos de duplicados en la subpartición de monitorización arrojando `ValueError` descriptivo. Definir arquitecturas diferenciadas en `configs/revision_metodologica.json`.
- **Razón**: Resolver discrepancias de nombres entre la configuración JSON y los constructores Keras que provocaban fallos al parsear parámetros, y garantizar microentrenamientos reales reproducibles.
- **Consecuencias**: Microentrenamientos reales ejecutados y verificados en Docker mediante `tests/revision/test_neural_config_unification.py`.

### D024 — Validación criptográfica y endurecimiento de bundles (Auditoría 02, Bloque 5)
- **Fecha**: 2026-10-28
- **Decisión**: En `scientific_core/model_bundle.py`:
  1. Validar estrictamente el orden y nombres de `feature_names` y `target_names` contra `scientific_core.contracts`.
  2. Exigir la presencia física de `scalers.pkl` cuando `scaler_x_applied = True`, arrojando `FileNotFoundError` en lugar de operar en modo degradado con escaladores nulos.
  3. Verificar hashes criptográficos SHA-256 de todos los archivos del bundle contra `file_hashes` registrado en `bundle_metadata.json` al cargar.
  4. Realizar la exportación atómica en directorio temporal antes de consolidar el bundle final.
  5. En `backend/app/services/model_store.py`, retener el modelo previo si una recarga falla, y rechazar bundles marcados con `test_only = True` salvo autorización explícita.
- **Razón**: Prevenir artefactos corruptos, desajustes silenciosos de variables de entrada/salida y caídas de servicio en FastAPI.
- **Consecuencias**: Verificado al 100% en `tests/revision/test_bundle_hardening.py`.

### D025 — Medición real de tiempos de cómputo en entrenamiento e inferencia (Auditoría 02, Bloque 6)
- **Fecha**: 2026-10-28
- **Decisión**: Medir tiempos exactos con `time.perf_counter()` para entrenamiento por fold/familia e inferencia sobre un vector de prueba en `scientific_core/nested_cv.py`. Eliminar las constantes ficticias de `0.1` s y `0.01` s en `streamlit_app/advanced_training.py`. Si los tiempos no están disponibles, devolver `None`/`np.nan` y renderizar "No medido" en Streamlit.
- **Razón**: Eliminar telemetría artificial en informes y asegurar tiempos reales de cómputo para análisis comparativos.
- **Consecuencias**: Verificado en `tests/revision/test_real_time_measurements.py`.

### D026 — Selección agregada y reproducible de hiperparámetros finales (Auditoría 02, Bloque 7)
- **Fecha**: 2026-10-28
- **Decisión**: En `cli.py cmd_export_model`, seleccionar la combinación óptima de hiperparámetros agrupando los registros de `tuning_results.csv` por firma de parámetros y calculando el MAE macro interno medio a través de todas las particiones internas de todas las particiones externas evaluadas. Documentar en `bundle_metadata.json` el bloque `final_selection_policy` con el ranking completo de candidatos y la justificación de elección.
- **Razón**: Corregir el sesgo estadístico que surge al seleccionar hiperparámetros a partir del resultado de un único fold externo favorecido por el particionamiento.
- **Consecuencias**: Verificado en `tests/revision/test_aggregated_hyperparameter_selection.py`.

### D027 — Modo científico y auditoría previa en interfaz Streamlit (Auditoría 02, Bloque 8)
- **Fecha**: 2026-10-28
- **Decisión**: Agregar el parámetro `scientific_mode: bool = False` en `streamlit_app/advanced_training.py`. Cuando está activado, se prohíbe `allow_missing_dependencies`. En `streamlit_app/app.py`, auditar el dataset mediante `audit_dataset` antes de desencadenar el entrenamiento, bloqueando la ejecución si la auditoría detecta anomalías.
- **Razón**: Garantizar paridad metodológica total entre la interfaz interactiva Streamlit y el pipeline de evaluación por CLI.
- **Consecuencias**: Verificado en `tests/revision/test_streamlit_cli_unification.py`.

### D028 — Integración de dominios aprendidos en formulación NSGA-II (Auditoría 02, Bloque 9)
- **Fecha**: 2026-10-28
- **Decisión**: En `backend/app/services/optimization.py`, restringir el espacio de búsqueda de `LandscapeOptimizationProblem` intersectando los límites físicos biofísicos con los rangos observados durante el entrenamiento (`observed_training_ranges`). Asignar penalizaciones severas (`1e5` en objetivos y `1e3` en restricciones) si un candidato viola el dominio aprendido. Filtrar las soluciones del frente de Pareto para garantizar que ninguna solución verificada vulnere las cotas empíricas, y retornar `status: "infeasible"` de forma limpia si no existen soluciones viables.
- **Razón**: Impedir que el optimizador genético converja a regiones donde los modelos sustitutos carecen de validez por extrapolación indebida.
- **Consecuencias**: Verificado en `tests/revision/test_domain_integrated_optimization.py`.

### D029 — Trazabilidad exhaustiva en manifiestos y sumas de verificación (Auditoría 02, Bloque 10)
- **Fecha**: 2026-10-28
- **Decisión**: En `scientific_core/persistence.py`, preservar inmutable `started_at_utc` al finalizar runs; registrar bloques descriptivos de metadatos del generador (`generator_metadata`) y procedencia de columnas (`dataset_provenance`); e implementar `update_manifest_bundle` para registrar la ruta, hash e identificador del bundle en `manifest.json`. Excluir estrictamente `SHA256SUMS.txt` de su propio cálculo de sumas.
- **Razón**: Garantizar auditoría forense completa y trazabilidad criptográfica de todos los artefactos generados.
- **Consecuencias**: Verificado en `tests/revision/test_manifest_bundle_provenance.py` y en el run smoke `smoke_20261028_162701`.

### D030 — Formato de cadenas de ayuda en argparse y validación integral de CLI (Auditoría 02)
- **Fecha**: 2026-10-28
- **Decisión**: Escapar como `%%` el carácter de porcentaje en las cadenas de ayuda de `cli.py` (específicamente en `--min-natural-area-pct`) para evitar colisiones con el interpolador `ArgumentDefaultsHelpFormatter` de `argparse`. Verificar la ejecución de todos los subcomandos (`audit-data`, `generate-data`, `evaluate`, `export-model`, `validate-bundle`, `optimize`, `smoke`).
- **Razón**: `argparse` arrojaba `ValueError: unsupported format character ')' (0x29)` al solicitar ayuda de `cli.py optimize`.
- **Consecuencias**: Subcomando `cli.py optimize` y ayuda de todos los comandos 100% operativos.

### D031 — Unificación de selección final de hiperparámetros y deserialización canónica (Auditoría 03, Bloque 1)
- **Fecha**: 2026-10-28
- **Decisión**: Centralizar en `scientific_core/nested_cv.py` la función `select_final_hyperparameters` para ser consumida unívocamente por `cli.py` y `streamlit_app/advanced_training.py`. Implementar `parse_params_string` utilizando `json.loads` canónico para deserializar correctamente valores nulos (`null` $\to$ `None`) y rechazar cadenas malformadas con `ValueError`. Exigir cobertura completa de evaluaciones por candidato (`expected_n_evaluations`), rechazar puntuaciones no finitas (`NaN`, `Inf`), establecer desempates deterministas (menor `mean_inner_macro_mae`, menor `mean_inner_macro_rmse`, y orden lexicográfico de JSON canónico), asegurar que los tipos nativos alcancen el modelo final, y documentar la limitación metodológica de la agregación de hiperparámetros entre folds externos en `nota_metodologica_agregacion`.
- **Razón**: Corregir la divergencia donde Streamlit seleccionaba el menor MAE de un único fold afortunado y `ast.literal_eval` sustituía silenciosamente los hiperparámetros con `null` por `{}`, provocando que Random Forest se reajustara con 100 árboles por defecto en lugar de los parámetros optimizados.
- **Consecuencias**: Verificado en `tests/revision/test_audit03_final_selection.py` (4 pruebas pasadas).

### D032 — Centralización de validación y carga en `load_bundle` con comprobación SHA-256 previa (Auditoría 03, Bloque 2)
- **Fecha**: 2026-10-28
- **Decisión**: Establecer `scientific_core.model_bundle.load_bundle` como la única fuente de verdad para la validación y carga de bundles universales. Realizar la verificación estricta de sumas SHA-256 de todos los archivos físicos declarados antes de ejecutar cualquier deserialización mediante `pickle.load` o `keras.models.load_model`. Validar obligatoriamente la presencia y orden exacto de `FEATURE_COLUMNS` y `TARGET_COLUMNS`, la integridad no nula de `scalers.pkl` con sus atributos estadísticos (`mean_`, `scale_`), la existencia de `observed_training_ranges`, y ejecutar una inferencia dummy de sanidad previa a la activación. `ModelStore` delega exclusivamente en `load_bundle`.
- **Razón**: Prevenir vulnerabilidades de ejecución arbitraria mediante pickles corruptos antes de comprobar la integridad criptográfica y eliminar divergencias de validación entre módulos.
- **Consecuencias**: Verificado en `tests/revision/test_audit03_bundle_validation.py` (8 pruebas pasadas).

### D033 — Publicación atómica con respaldo automático y conmutación atómica en ModelStore (Auditoría 03, Bloque 3)
- **Fecha**: 2026-10-28
- **Decisión**: En `scientific_core/model_bundle.export_bundle`, implementar un mecanismo de backup automático previo sobre el directorio destino si ya existe, procesar la escritura en un subdirectorio temporal de staging, y ejecutar la conmutación final solo tras superar la validación de integridad; en caso de cualquier excepción, el staging se destruye y el backup se restaura automáticamente. Generar el identificador `bundle_id` de forma determinista a partir del hash de contenido. En `ModelStore.load()`, conmutar la referencia en memoria `self._active_predictor` de forma atómica e invalidar inmediatamente la caché de simulación (`simulation_cache.clear()`).
- **Razón**: Eliminar el riesgo de corrupción de bundles por fallos transitorios de escritura o interrupción de proceso, y prevenir inconsistencias de caché tras conmutaciones de modelo.
- **Consecuencias**: Verificado en `tests/revision/test_audit03_atomic_publication.py` (2 pruebas pasadas).

### D034 — Flujo científico integral y persistencia completa de artefactos en Streamlit (Auditoría 03, Bloque 4)
- **Fecha**: 2026-10-28
- **Decisión**: Incorporar en la barra lateral de Streamlit un conmutador explícito entre "Modo Científico Estricto (AGROSAVIA)" y "Modo Exploratorio". En modo científico, delegar en `run_nested_cv` y persistir la totalidad de los 11 artefactos estructurados del ciclo de vida en `artifacts/revision_metodologica/<run_id>/` (`manifest.json`, `config_effective.json`, `environment.json`, `data_audit.json`, `dataset.csv`, `splits.json`, `tuning_results.csv`, `fold_metrics.csv`, `oof_predictions.csv`, `model_summary.csv`, `SHA256SUMS.txt`). Vincular la exportación de bundles al `run_id` activo actualizando el manifiesto con la sección `bundle`. Actualizar los textos y etiquetas de la interfaz para eliminar términos obsoletos o claims de campo no fundamentados.
- **Razón**: Garantizar paridad metodológica y trazabilidad de artefactos idéntica entre la ejecución por CLI y la interfaz visual de Streamlit.
- **Consecuencias**: Verificado en `streamlit_app/app.py`, `advanced_training.py` y `test_streamlit_cli_unification.py`.

### D035 — Contratos estrictos de datos en auditoría y prohibición de reducción silenciosa de folds (Auditoría 03, Bloque 5)
- **Fecha**: 2026-10-28
- **Decisión**: En `scientific_core/data_audit.py`, exigir mandatoriamente la presencia de la totalidad de las columnas de `FEATURE_COLUMNS` (8) y `TARGET_COLUMNS` (3), reportar explícitamente duplicados en `sample_id`, rechazar DataFrames vacíos y validar tipos de datos numéricos en todas las variables. En `scientific_core/nested_cv.py`, prohibir de forma terminante la reducción silenciosa de folds en modo científico ante un número insuficiente de grupos de duplicados, arrojando un error `ValueError` descriptivo. Almacenar la información completa de particiones externas e internas en `splits_manifest` (`splits.json`).
- **Razón**: Evitar que datasets incompletos o con duplicados de identificador avancen a entrenamiento, y prevenir alteraciones silenciosas del diseño experimental en validación cruzada.
- **Consecuencias**: Verificado en `tests/revision/test_audit03_data_contract.py` (7 pruebas pasadas).

### D036 — Paridad en 4 etapas para arquitecturas neuronales e integración end-to-end (Auditoría 03, Bloque 6)
- **Fecha**: 2026-10-28
- **Decisión**: Validar la equivalencia numérica rigurosa ($< 10^{-5}$) a través de las 4 etapas del ciclo de inferencia (modelo entrenado $\to$ `UniversalSurrogatePredictor` pre-exportación $\to$ bundle recargado vía `load_bundle` $\to$ `ModelStore` de FastAPI) para las arquitecturas `dnn` y `autoencoder_mlp` (cuello de botella supervisado). Implementar una prueba de integración completa de extremo a extremo que ejecute Nested CV, selección agregada de hiperparámetros, refit final, exportación y validación de bundle neuronal utilizando el runtime real de Keras y TensorFlow en Docker.
- **Razón**: Garantizar que las familias neuronales gocen de la misma verificación exhaustiva y robustez numérica demostrada previamente en las familias lineales y de ensamble.
- **Consecuencias**: Verificado en `tests/revision/test_audit03_parity_neural_all_families.py` (3 pruebas pasadas en Docker).

### D037 — Contabilización rigurosa de evaluaciones en NSGA-II y preservación de corridas smoke (Auditoría 03, Bloque 7)
- **Fecha**: 2026-10-28
- **Decisión**: En `backend/app/services/optimization.py`, registrar mediante un contador interno en `LandscapeOptimizationProblem` el número exacto de llamadas a la función objetivo (`evaluations_count`). Reportar con rigor matemático `algorithm_evaluations_total` ($pop\_size \times n\_gen = 2560$), `pareto_solutions_returned` (64) y `pareto_verified_count` (64), eliminando la ambigüedad que sugería que el algoritmo solo evaluaba 64 candidatos. En `cli.py optimize`, reflejar claramente estas métricas. Preservar de forma inmutable las corridas smoke anteriores (`smoke_20261028_060521`, `smoke_20261028_071815`, `smoke_20261028_162701`) al generar la nueva corrida `smoke_20261028_173336`.
- **Razón**: Corregir la imprecisión metodológica en el reporte de la búsqueda estocástica multiobjetivo y respetar la trazabilidad histórica de todas las evidencias generadas.
- **Consecuencias**: Verificado en `tests/revision/test_audit03_optimization_evaluations.py` y corrida smoke `smoke_20261028_173336` validada.

### D038 — Persistencia real del ciclo de vida y adaptador desacoplado en Streamlit (Auditoría 04, Bloque 1)
- **Fecha**: 2026-10-28
- **Decisión**: Extraer la lógica de ciclo de vida de Streamlit a un módulo de servicio desacoplado y comprobable `streamlit_app/adapter.py` (`prepare_streamlit_run_config`, `execute_streamlit_training_run`, `export_streamlit_model`). Corregir la discrepancia de argumentos en `init_run_manifest` (usando `run_dir`, `run_id`, `config_effective`, `test_only`), inicializar el manifiesto con estado `started` antes de entrenar, capturar excepciones registrando `failed` con `record_run_failure` y fallar visiblemente en la interfaz ante cualquier error. Persistir los 11 artefactos normalizados en `artifacts/revision_metodologica/<run_id>/`. Vincular la exportación del bundle exclusivamente al dataset real utilizado durante el entrenamiento (`training_dataset` persistido en sesión/run), prohibiendo reexportar basándose en el estado volátil de la interfaz.
- **Razón**: Corregir fallos de firma en `init_run_manifest`, la ausencia de persistencia real en Streamlit, y el riesgo metodológico de exportar bundles asociados a datasets alterados o desvinculados del entrenamiento.
- **Consecuencias**: Verificado en `tests/revision/test_audit04_streamlit_persistence.py` (2 pruebas pasadas).

### D039 — Tratamiento formal de infactibilidad y ausencia de soluciones óptimas en API y Frontend (Auditoría 04, Bloque 2)
- **Fecha**: 2026-10-28
- **Decisión**: Adaptar `backend/app/schemas.py` (`SimulationResultPayload`), `backend/app/services/optimization.py`, `backend/app/main.py` y `frontend/src/components/ResultsDashboard.jsx` para gestionar limpiamente escenarios donde el optimizador NSGA-II retorna `status: "infeasible"` y `best_solution: None`. Se prohíbe terminantemente fabricar métricas en cero o asignar propiedades a `None`. En el backend, `/api/simular` almacena la simulación con `metricas_optimas = None`, omite el servicio de recomendación por LLM y retorna un estado descriptivo con el motivo de infactibilidad. En el frontend, el dashboard verifica `isInfeasible`, renderiza un banner informativo claro, protege el acceso a atributos anidados y omite gráficos que carecen de soporte.
- **Razón**: Evitar excepciones no controladas (`TypeError: Cannot read properties of null`), datos ficticios en base de datos y mensajes de error rotos cuando las restricciones de paisaje impiden hallar soluciones factibles.
- **Consecuencias**: Verificado en `tests/revision/test_audit04_infeasible_and_criteria.py` (casos de validación de esquema, servicio de optimización e interfaz de recomendaciones).

### D040 — Criterio operativo de mejora conjunta y prohibición de afirmaciones empíricas desmedidas (Auditoría 04, Bloque 3)
- **Fecha**: 2026-10-28
- **Decisión**: Establecer que la condición de éxito agronómico y ecológico requiere el cumplimiento simultáneo de dos condiciones cuantitativas: `delta_yield >= 0` (rendimiento no degradado) Y `delta_pollinators >= 20.0` (+20% abundancia simulada). El backend calcula e inyecta el booleano estructurado `meets_joint_criteria`, el cual es consumido directamente por el frontend `ResultsDashboard.jsx` sin recurrir a búsquedas frágiles de texto o subcadenas. Redactar el estado unívocamente como "Criterio operativo de mejora conjunta cumplido/no alcanzado". Se prohíbe de forma terminante afirmar o insinuar "confirmación empírica", "validación en campo" o "comprobación biológica".
- **Razón**: Erradicar discrepancias donde mejoras en polinizadores con caídas catastróficas en rendimiento se reportaban falsamente como éxito agroecológico, y preservar la integridad epistémica del gemelo digital.
- **Consecuencias**: Verificado en `tests/revision/test_audit04_infeasible_and_criteria.py` (casos cuantitativos obligatorios y auditoría de texto libre de claims prohibidos).

### D041 — Contrato estricto de bundle, rangos observados canónicos e identidad determinista (Auditoría 04, Bloque 4)
- **Fecha**: 2026-10-28
- **Decisión**: En `scientific_core/model_bundle.py`:
  1. En exportación científica (`strict_scientific=True`), prohibir el fallback automático de `observed_training_ranges` a `PHYSICAL_BOUNDS`; exigir que provengan obligatoriamente del entrenamiento registrado y validar la presencia de las 8 características, finitud, $min \le max$ y compatibilidad con cotas biofísicas.
  2. En `load_bundle`, validar obligatoriamente que `schema_version` pertenezca a `{"2.0", "2.0_revision_metodologica"}`.
  3. Exigir la presencia y hash explícito del modelo y de `scalers.pkl` en `file_hashes` antes de iniciar la deserialización.
  4. Derivar el identificador canónico `bundle_id` de forma determinista incorporando: hash del modelo, hash de escaladores, familia de modelo, contrato de preprocesamiento, orden lexicográfico canónico de `observed_training_ranges` y marca `test_only`.
  5. Preservar la publicación atómica con reversión automática ante fallos de escritura o autovalidación.
- **Razón**: Corregir la omisión silenciosa de rangos reales de entrenamiento, evitar la reutilización inadvertida de `bundle_id` entre datasets con distintos dominios empíricos, y blindar el bundle ante esquemas incompatibles o artefactos sin hash declarado.
- **Consecuencias**: Verificado en `tests/revision/test_audit04_bundle_contract.py` (9 pruebas pasadas).

### D042 — Alineación de contextos de construcción y directivas COPY en Compose de producción (Auditoría 04, Bloque 5)
- **Fecha**: 2026-10-28
- **Decisión**: En `docker-compose.prod.yml`, ajustar el contexto de construcción de los servicios `backend` y `streamlit` a la raíz del repositorio (`context: .`), especificando sus respectivos archivos Dockerfile (`dockerfile: ./backend/Dockerfile` y `dockerfile: ./streamlit_app/Dockerfile`). Garantizar que todas las directivas `COPY` dentro de ambos Dockerfiles dispongan de sus archivos de origen accesibles dentro del contexto del build (`scientific_core`, `configs`, `cli.py`, etc.).
- **Razón**: Prevenir fallos de compilación en entornos de despliegue donde `docker-compose.prod.yml` intentaba copiar recursos transversales situados fuera de los subdirectorios locales de backend o streamlit.
- **Consecuencias**: Validado mediante `docker compose -f docker-compose.prod.yml config` con código de salida 0.

### D043 — Configuración única de ejecución y persistencia con rechazo estricto en modo científico (Auditoría 05, Hallazgo 1)
- **Fecha**: 2026-10-28
- **Decisión**: Unificar la creación de la configuración en un único objeto canónico preparado por `streamlit_app/adapter.py:prepare_streamlit_run_config` y consumido directamente sin reinterpretación por `streamlit_app/advanced_training.py:train_and_evaluate_all_models` y `scientific_core/nested_cv.py:run_nested_cv`. La misma instancia de configuración se persiste en `config_effective.json` y en el manifiesto de la corrida. En modo científico estricto (`scientific_mode=True`), rechazar explícitamente con `ValueError` cualquier solicitud con `group_duplicates=False`, garantizando que nunca se desactive el agrupamiento por `GroupKFold` para evitar fuga de datos entre particiones. En modo exploratorio (`scientific_mode=False`), respetar fielmente `group_duplicates=False` tanto en la llamada a `run_nested_cv` como en la persistencia física en `config_effective.json`.
- **Razón**: Erradicar la divergencia metodológica detectada donde `config_effective.json` reportaba `group_duplicates=True` mientras que el entrenamiento se ejecutaba con `group_duplicates=False`.
- **Consecuencias**: Verificado en `tests/revision/test_audit05_unified_config.py` (5 pruebas pasadas en Docker).

### D044 — Representación formal y manejo seguro de simulaciones sin solución óptima en Chat y Reportes (Auditoría 05, Hallazgo 2)
- **Fecha**: 2026-10-28
- **Decisión**: En `backend/app/models/simulation.py`, explicitar `metricas_optimas: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)`. En `backend/app/services/chat_service.py` (`query_simulation_details`), verificar la presencia válida de `sim.metricas_optimas`. Ante simulaciones infactibles o sin convergencia:
  1. No invocar `.get()` sobre `None` (eliminando el fallo `AttributeError: 'NoneType' object has no attribute 'get'`).
  2. No fabricar métricas óptimas copiando los valores de la línea base.
  3. Devolver explícitamente `tiene_solucion_optima: False`, `metricas_optimas: None`, y `mejoras: {"delta_rendimiento": None, "delta_polinizadores_porcentaje": None, "estado": "no_evaluable"}`.
  4. Preservar intactas las comprobaciones de autorización por rol y propiedad.
  5. En `generate_local_fallback_reply`, explicar de manera transparente que la simulación resultó infactible sin inventar mejoras.
  6. En `query_simulations_summary` y `report_general_service.py` (`get_management_report`), tratar los registros infactibles como no cumplidores de hipótesis, evitando divisiones por cero, falsos positivos o sesgos en los promedios globales de rendimiento y abundancia.
- **Razón**: Resolver la caída del servicio de chat al consultar simulaciones infactibles y garantizar la veracidad de los reportes estadísticos y resúmenes de usuario.
- **Consecuencias**: Verificado en `tests/revision/test_audit05_simulation_query_infeasible.py` (7 pruebas pasadas en Docker).

### D045 — Evaluación del criterio operativo conjunto a precisión numérica completa antes del redondeo (Auditoría 05, Hallazgo 3)
- **Fecha**: 2026-10-28
- **Decisión**: En `backend/app/services/optimization.py` (`run_simulation`), evaluar la condición booleana del criterio operativo conjunto `meets_joint_criteria = bool(raw_delta_yield >= 0.0 and raw_delta_pollinators >= 20.0)` utilizando la precisión flotante estricta completa (`raw_delta_yield` y `raw_delta_pollinators`) ANTES de efectuar cualquier redondeo para presentación. Los redondeos a 3 decimales (`round(..., 3)`) quedan reservados exclusivamente para los campos de visualización `delta_yield` y `delta_pollinators`. Ante simulaciones infactibles (sin frente de Pareto admisible), asignar `meets_joint_criteria: None`, `delta_yield: None` y `delta_pollinators: None` con estado "No evaluable: sin soluciones admisibles dentro del dominio".
- **Razón**: Eliminar falsos positivos en la frontera matemática (ej. degradación leve de -0.0004 y ganancia de 19.9998% que al redondearse prematuramente a 0.000 y 20.000% simulaban erróneamente un cumplimiento del criterio conjunto).
- **Consecuencias**: Verificado en `tests/revision/test_audit05_criteria_precision.py` (5 pruebas pasadas en Docker).

### D046 — Semilla canónica efectiva gobernante del reajuste final (Auditoría 06, Hallazgo 1)
- **Fecha**: 2026-10-28
- **Decisión**: En `streamlit_app/advanced_training.py` (`train_and_evaluate_all_models`), derivar la semilla final `final_seed` directamente a partir de la configuración única efectiva inyectada (`int(config.get("seed") or config.get("outer_cv", {}).get("seed", random_state))`). Utilizar dicha semilla de forma obligatoria en la creación y reajuste tanto de modelos tradicionales (`ModelFactory.create_model(..., seed=final_seed)`) como de arquitecturas neuronales (`fit_and_predict_neural_outer(..., seed=final_seed)`). En `streamlit_app/adapter.py`, propagar `effective_run_seed` a `train_and_evaluate_all_models` e inyectar `"final_seed"` y `"seed"` en los metadatos exportados del bundle.
- **Razón**: Eliminar la contradicción metodológica detectada donde `execute_streamlit_training_run` recibía `random_state=1337` y lo persistía en `outer_cv.seed=1337`, pero el modelo final persistido se entrenaba con la semilla predeterminada `42` debido al valor por defecto del argumento en `advanced_training.py`.
- **Consecuencias**: Verificado en `tests/revision/test_audit06_final_seed_and_paired_reports.py` (pruebas de semilla 42, 1337, inyectada 2026, reajuste neuronal y exportación de bundle).

### D047 — Principio de comparación pareada estricta en informes agregados de gestión (Auditoría 06, Hallazgo 2)
- **Fecha**: 2026-10-28
- **Decisión**: En `backend/app/services/report_general_service.py` (`get_management_report`), calcular los promedios base, promedios óptimos, deltas y porcentajes de mejora estrictamente sobre la misma subpoblación de simulaciones con soluciones factibles evaluables (`simulaciones_evaluables`). Mantener las estadísticas de línea base de toda la cohorte identificadas por separado (`rendimiento_promedio_base_total`, `abundancia_polinizadores_base_total`, `diversidad_polinizadores_base_total`) sin utilizarlas en el cálculo de deltas contra óptimos de una subpoblación menor. Aplicar el mismo criterio pareado en agrupaciones globales, regionales y temporales. Incorporar en `schemas_reports.py` los campos explícitos `simulaciones_evaluables`, `simulaciones_no_evaluables` y `denominador_tasa = "evaluables"`. Ante la ausencia de comparaciones evaluables (`simulaciones_evaluables == 0`), retornar ausencia de datos (`None`) y recuento evaluable 0, sin fabricar deltas con ceros espurios.
- **Razón**: Erradicar la severa distorsión estadística en comparaciones no pareadas donde la presencia de simulaciones infactibles con líneas base elevadas generaba deltas artificialmente negativos (ej. base evaluable=100, óptimo=110 arrojaba delta=-440 debido a una base total poblacional de 550 proveniente de un registro infactible con base=1000).
- **Consecuencias**: Verificado en `tests/revision/test_audit06_final_seed_and_paired_reports.py` (Casos A a F, incluyendo la comprobación numérica exacta del escenario de la auditoría).

### D048 — Partición canónica de recuentos de gestión: evaluables vs. no evaluables (Auditoría 07, Hallazgo 1)
- **Fecha**: 2026-10-28
- **Decisión**: En `backend/app/services/report_general_service.py` (`get_management_report`), aplicar la partición formal estricta de poblaciones:
  1. `total_simulaciones = simulaciones_evaluables + simulaciones_no_evaluables`.
  2. `simulaciones_evaluables = simulaciones_cumplen_hipotesis + simulaciones_no_cumplen`.
  3. En consecuencia, `simulaciones_no_cumplen = (simulaciones_evaluables - simulaciones_cumplen_hipotesis) if simulaciones_evaluables > 0 else 0`.
  4. La tasa de cumplimiento de criterio operativo utiliza como denominador explícito las simulaciones evaluables (`denominador_tasa = "evaluables"`).
  5. Cuando `simulaciones_evaluables == 0`, `tasa_cumplimiento_hipotesis = None` y `simulaciones_no_cumplen = 0` (no se fabrica 0%).
  6. En `RegionManagementItem` y `ManagementTemporalEvolutionPoint` (`backend/app/schemas_reports.py`), incorporar explícitamente `simulaciones_cumplen_hipotesis` y `simulaciones_no_cumplen` calculados bajo la misma partición canónica.
- **Razón**: Corregir el cálculo anterior donde `simulaciones_no_cumplen = total_sims - cumplen_hipotesis`, el cual sumaba las simulaciones infactibles a "no cumplen" a pesar de contarlas simultáneamente como no evaluables, inflando artificialmente el conjunto que no cumplía el criterio y violando la partición disyunta de la cohorte.
- **Consecuencias**: Verificado en `tests/revision/test_audit07_management_reports_and_exporters.py` (Casos A a G aprobados en Docker).

### D049 — Preservación de ausencia de datos vs. cero numérico real y alineación terminológica en consumidores (Auditoría 07, Hallazgo 2)
- **Fecha**: 2026-10-28
- **Decisión**: En `frontend/src/lib/generalReportExporters.js` y `frontend/src/pages/AdminReportsPage.jsx`:
  1. Reemplazar operadores de fallback indiscriminados (`|| 0` y `?? 0`) por funciones de formateo que diferencian estrictamente entre ausencia de valor (`null` / `undefined` $\to$ `"N/D"`) y cero numérico real (`0.0 pts`, `0.0%`).
  2. En exportación a Excel, mantener valores numéricos reales (incluido `0.0`) y asignar `"N/D"` ante datos ausentes, evitando generar celdas con ceros ficticios.
  3. En Excel, renombrar "Total Simulaciones Evaluadas" a "Total Simulaciones Registradas", y desglosar explícitamente: Total Registradas, Evaluables (con solución), No Evaluables (sin solución), Denominador de la Tasa, Cumplen Criterio y No Cumplen (evaluables).
  4. En React (`AdminReportsPage.jsx`), incorporar una barra de resumen poblacional de cohorte que hace visible la partición completa y el denominador de tasa.
  5. Unificar la terminología en todos los exportadores (PDF, DOCX, XLSX) e interfaz, sustituyendo el término inadecuado "hipótesis comprobada" por "criterio operativo de mejora conjunta".
- **Razón**: Prevenir la representación engañosa de métricas no evaluables como si fueran ceros absolutos (e.g. rendimiento óptimo 0 kg/ha) y clarificar la naturaleza de optimización biofísica para revisores y comités editoriales.
- **Consecuencias**: Verificado a nivel lógico en `tests/revision/test_audit07_frontend_exporters.mjs` (5 pruebas Node.js aprobadas con dependencias simuladas; la generación física y revisión visual de PDF/Word queda sujeta al plan de validación funcional manual).

### D050 — Compatibilidad de tipos de descarga en Streamlit, caché con detección in-place y fallback gráfico fiel a 600 DPI (Validación Funcional, INC-FUNC-001)
- **Fecha**: 2026-10-28
- **Decisión**: En `streamlit_app/export_helpers.py`:
  1. En `render_table_with_excel` y `render_high_res_chart`, entregar directamente datos de tipo `bytes` al widget `st.download_button` en lugar de objetos función callables (`_excel_callable`, `_data_callable`).
  2. Implementar un mecanismo de caché en memoria sobre `st.session_state` basado en huella digital criptográfica determinista SHA-256 (`_compute_dataframe_fingerprint`) calculada sobre `pd.util.hash_pandas_object(raw_df, index=include_index)` junto con columnas, dtypes e índice serializado. Esto garantiza la detección inmediata de mutaciones de celdas *in-place* que conservan `id(df)`, `shape` y columnas, invalidando la caché y exportando siempre el contenido real actualizado.
  3. En `_plotly_to_matplotlib_png`, dar soporte fiel a las 11 figuras utilizadas en la aplicación (F1 a F11):
     - Heatmaps (F1, F4, F11): alineación espacial `origin='upper'`, mapeo de colormaps (Viridis, YlGnBu, RdBu_r), renderizado de texto numérico por celda (`texttemplate="%{z:.3f}"`, `text_auto`) con contraste lumínico automático (blanco/negro) y ticks explícitos.
     - Histograma con marginal (F2): layout dual con boxplot horizontal marginal superior y panel inferior de histograma + KDE compartiendo el eje X.
     - Boxplots multivariables (F3): unificación en un solo llamado `ax.boxplot` con colores individuales y trazado de líneas de umbral $\pm 3\sigma$.
     - Trayectoria poblacional (F5): resolución de `trace.x=None` derivando a `range(len(y))` para evitar discrepancia dimensional en `ax.plot`.
     - Barras agrupadas (F6): cálculo de offsets por serie bajo `barmode="group"`, paleta diferenciada y leyenda.
     - Formas geométricas (F7, F8): renderizado de diagonales $y=x$ y líneas cero de residuo $y=0$ desde `fig.layout.shapes`.
     - Barras con texto (F10) y horizontales (F9).
     - Manejo seguro de arreglos NumPy en colores de marcadores/líneas (`_resolve_color`).
  4. Incorporar un aviso visible de salvaguarda en el lienzo en caso de suministrarse figuras con componentes no reproducibles fielmente, evitando generar salidas engañosas.
- **Razón**: Corregir la excepción fatal `RuntimeError: Invalid binary data format: <class 'function'>` de Streamlit 1.38.0 y cerrar rigurosamente los riesgos de obsolescencia de caché ante mutaciones *in-place* y de distorsión en la conversión gráfica estática.
- **Consecuencias**: Verificado en el contenedor Streamlit con suite completa de 6 pruebas unitarias y de regresión (`test_export_helpers.py`: 6/6 aprobadas), generación e inspección programática de archivos en contenedor (`T2_muestra_datos.xlsx`, `T3_estadisticas_descriptivas.xlsx`, `F1_matriz_correlaciones_600dpi.png`), y ejecución programática completa del entrenamiento funcional CP-FUNC-01A (`run_id: streamlit_scientific_20261028_224312`). El estado de CP-FUNC-01A se cataloga formalmente como "Verificación programática completada; recorrido interactivo pendiente" sin marcarse como aprobado como prueba UI, expresando la ausencia de controladores de navegador (Selenium/Playwright/Puppeteer) en el entorno. Se reconocen las limitaciones del conversor estático Plotly->Matplotlib (densidad física 600 DPI certificada sin garantía de equivalencia CSS/DOM con el cliente Plotly) y de la caché en `session_state` (volátil ante F5 y consumo de RAM).
