# Auditoría Inicial del Código — Revisión Metodológica

**Fecha:** 28 de octubre de 2026  
**Rama:** `revision-metodologica`  
**Commit base auditado:** `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab`  
**Espacio de trabajo:** `C:\Users\Daniel\Downloads\gemelo-digital-polinizadores-revision`  

---

## 1. Clasificación y Resumen de Hallazgos

| ID | Área / Archivo | Hallazgo Reportado en Plan | Estado Auditado | Evidencia en Código y Ubicación |
|---|---|---|---|---|
| H01 | `streamlit_app/advanced_training.py` | `StandardScaler` ajustado sobre todo `y` antes del KFold (fuga de datos) | **CONFIRMADO** | Líneas 66-67: `scaler = StandardScaler(); y_scaled = scaler.fit_transform(y)`. En la línea 146 `y_train, y_val = y_scaled[train_idx], y_scaled[val_idx]`. La escala de validación contiene información del dataset completo. |
| H02 | `streamlit_app/advanced_training.py` y `hyperparameter_tuning.py` | Tuning precede a CV externa; sin CV anidada | **CONFIRMADO** | `advanced_training.py:70-83`: `tune_all_hyperparameters` corre sobre todo `X, y, y_scaled`. `hyperparameter_tuning.py:139, 176, 211`: `search_rf.fit(X, y_scaled)` entrena sobre la matriz global completa. No existe partición anidada externa-interna. |
| H03 | `streamlit_app/advanced_training.py` | Redes usan fold externo como `validation_data` de EarlyStopping | **CONFIRMADO** | Líneas 175-176: `EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)` pasando `validation_data=(X_val, y_val)`. Los pesos retenidos y la parada dependen de la partición de prueba externa. |
| H04 | `streamlit_app/advanced_training.py` | `best_keras_model` se elige por fold externo, no del ganador global | **CONFIRMADO** | Líneas 123-124, 185-188: `best_keras_model` guarda la instancia del fold con mejor R² externo de Keras, independientemente de si el ganador global fue Ridge, RF o XGBoost. Se exporta un modelo entrenado en 80% de datos sin reentrenamiento final completo. |
| H05 | `streamlit_app/test_traceability_pipeline.py`, `app.py` | Marcadores 0.0 en métricas y asignación de MAE a red arbitraria | **CONFIRMADO** | `test_traceability_pipeline.py:48`: `metrics = {"general": {"mae": float(results_df.iloc[0]["CV_MAE_Mean"]), "rmse": 0.0, "r2": 0.0}}`. `app.py:1386`: idéntico patrón de métricas en cero. |
| H06 | `backend/app/services/optimization.py` | Clima heurístico, redondeo previo a inferencia, límites fijos | **CONFIRMADO** | Líneas 133-134: temperatura `23.6 + context.centroid_lat * -0.015` y precipitación fija. Líneas 253-260: redondeo a 3 decimales previo a `predict_targets`. Línea 106: clave de caché solo con payload de solicitud. |
| H07 | `backend/app/services/optimization.py` | Unificación de fórmula de diversidad | **YA CORREGIDO (PRESERVADO)** | Líneas 114-116, 125, 164, 250: `calculate_landscape_diversity` ya se emplea de forma compartida en línea base y candidatos. Se debe preservar y no duplicar. |
| H08 | `backend/app/services/model_store.py` | Control de proximidad regional sin control de dominio univariado/conjunto | **CONFIRMADO** | Líneas 180-234: `check_point_in_region` calcula únicamente distancia Haversine al centroide. No verifica si las 8 características de entrada están en el rango min/max ni el soporte conjunto del dataset de entrenamiento. |
| H09 | `docker-compose.yml` | Nombres de contenedores y volúmenes globales fijos | **CONFIRMADO** | Líneas 4, 22, 50, 65, 75: `container_name: gemelos_db`, `gemelos_backend`, etc. Líneas 88-91: volúmenes `postgres_data`, `modelos_ia_volume`, `langflow_data` sin namespace ni prefijo de revisión. Puerto postgres fijo 5432:5432. |
| H10 | `streamlit_app/data_pipeline.py` | Coberturas pueden sumar > 100% | **CONFIRMADO** | Líneas 49-51 y 334-336: `crop_area` (35-82%), `natural_area` (8-42%), `floral_strips` (2-18%) muestreadas independientemente. La suma puede alcanzar 142%, físicamente imposible para parcelas excluyentes. |
| H11 | `streamlit_app/pollinator_abm.py` | Enriquecimiento parcial no uniforme y diversidad no emergente | **CONFIRMADO** | Líneas 176-196: solo las primeras 120 filas pasan por el ABM (`sample_limit = min(len(enriched), 120)`). Filas 121-320 no se simulan. Líneas 148-155: la diversidad del ABM es una combinación lineal fija de las entradas, no una propiedad emergente de los agentes. |
| H12 | `streamlit_app/robust_tests.py` | Inferencia estadística sobre predicciones OOF como independientes | **CONFIRMADO** | Líneas 98, 104: t-test pareado y Wilcoxon ejecutados sobre N muestras OOF concatenadas (N=320), violando supuesto de observaciones independientes. Se debe distinguir entre análisis descriptivo y confirmatorio, permitiendo `not_performed` justificado. |
| H13 | `frontend/src/` y `backend/app/services/recommendation_service.py` | Afirmaciones de "Hipótesis comprobada" y "Validez asegurada" | **CONFIRMADO** | `ResultsDashboard.jsx:81`, `AdminReportsPage.jsx:547`, `api.js:143`, `recommendation_service.py`. Convierten un criterio heurístico (+20% abundancia simulada con delta rendimiento >= 0) en una comprobación científica de hipótesis agronómica. |

---

## 2. Inventario de Dependencias y Scripts de Prueba

- **Scripts de prueba existentes no seguros para ejecución automática:**
  - `streamlit_app/test_traceability_pipeline.py`: Realiza entrenamiento, escribe directamente en `/modelos_ia/modelo_optimizado.h5` y consulta `http://backend:8000/health`.
  - `streamlit_app/test_tuning_benchmark.py`: Ejecuta entrenamientos pesados con y sin tuning.
  - `scratch/test_*.py`: Pruebas ad-hoc, algunas destructivas o dependientes de APIs.
- **Entorno del sistema local:**
  - Python: `3.13.7` (en Windows nativo, TensorFlow oficial tiene soporte limitado a <= 3.12).
  - Los modelos tradicionales (Ridge, Random Forest, XGBoost) funcionan en Python 3.13 con `scikit-learn` y `xgboost`.
  - Se debe garantizar compatibilidad de ejecución en CPU con fallback estructurado para TensorFlow si no está compilado para Python 3.13 en Windows.

---

## 3. Plan de Acción por Módulo

1. **M02 - Aislamiento de Entorno:** Parametrizar compose con nombre de proyecto `polinizadores_revision`, puertos configurables (5433, 8001, 5174, 8502, 7861), volúmenes dedicados `revision_*`, archivo `.env.revision.example`.
2. **M03 - Contratos y Datos:** Módulo compartido de validación de coberturas (suma <= 100), coherencia en `data_pipeline.py`, política explícita de ABM (`historical_audit` vs `corrected`), y CLI de auditoría de dataset con hash SHA-256.
3. **M04 - Evaluación Predictiva Sin Contaminación:** CV anidada (5 folds externos, 3 folds internos), escalado `StandardScaler` ajustado estrictamente en partición de entrenamiento interna/externa, EarlyStopping en subpartición de monitorización interna, predicciones OOF completas inicializadas con NaN.
4. **M05 - Persistencia y Artefactos:** Manifiesto estructurado por ejecución, `splits.json`, `fold_metrics.csv`, `oof_predictions.csv`, `recompute_metrics` reproducible.
5. **M06 - Selección y Modelo Final:** Selección según menor MAE macro externo, reentrenamiento final del modelo ganador sobre todo el dataset, exportación de bundle universal (compatible con Ridge, RF, XGBoost y Keras).
6. **M07 - Optimización, Dominio y Caché:** Inclusión de validador de dominio univariado y soporte de entrenamiento, precisión completa en NSGA-II, caché invalidada por cambio de modelo o versión.
7. **M08 - API y Narrativa:** Actualización de schemas, reemplazo de "Hipótesis comprobada" por "Criterio operativo de mejora conjunta cumplido/no cumplido", separación de recomendaciones narrativas.
8. **M09 - Frontend y Etiquetas:** Refactorización de textos en React para evitar claims no respaldados.
9. **M10 & M11 - Pruebas Técnicas y CLI:** Batería de pruebas unitarias T01-T20 y CLI desacoplada de Streamlit.


---

## 4. Auditoría de Segunda Fase (Discrepancias y Mandatos Obligatorios)

Una auditoría independiente identificó 12 discrepancias críticas entre los reportes preliminares y la implementación real del código. Todas fueron confirmadas y corregidas en esta revisión:

| Mandato | Diagnóstico en Auditoría | Corrección Implementada | Verificación Aislada |
|---|---|---|---|
| 1. Evaluación de Redes | `pass` en rama neuronal de `nested_cv.py` y fallo de tipos con diccionarios en `fit_and_predict_traditional`. | Implementación completa de DNN y Bottleneck MLP con subpartición de monitorización interna (EarlyStopping) y política de épocas derivada de CV interna. | `tests/revision/test_neural_nested_cv.py` (Mocked test OK, comando Docker para TF documentado). |
| 2. Unificar CLI y Streamlit | `app.py` seguía invocando `advanced_training.py` con tuning global pre-CV y métricas ficticias. | `advanced_training.py` adaptado para delegar en `run_nested_cv`; `app.py` consume `results_df` real y exporta `UniversalSurrogatePredictor`. | `tests/revision/test_streamlit_cli_unification.py` |
| 3. Vincular Exportación al Experimento | `cli.py export-model` generaba 100 muestras al azar sin vincularse a la evaluación. | `export-model` exige `--run-dir`/`--run-id` completado, valida hashes, recupera la familia ganadora y sus hiperparámetros, y marca smoke como `test_only`. | `tests/revision/test_linked_export.py` |
| 4. Transformaciones RF y XGBoost | Inferencia omitía `scaler_x` para Random Forest y XGBoost a pesar de haber sido entrenados con entradas estandarizadas. | Contrato único de preprocesamiento en `UniversalSurrogatePredictor` y `ModelStore`. Paridad de 4 etapas demostrada (diferencia < 4e-6). | `tests/revision/test_inference_parity_all_families.py` |
| 5. Agrupamiento de Duplicados | Configuración declaraba `group_duplicates: true` pero el código ejecutaba `KFold` ordinario. | Implementación de `compute_feature_groups` y `GroupKFold` en splits externos, internos y de monitorización. 0% fuga demostrado. | `tests/revision/test_grouped_duplicates.py` |
| 6. Control de Dominio del Modelo | `ModelStore.check_domain` utilizaba límites generales en vez de rangos aprendidos del dataset. | Separación entre `PHYSICAL_BOUNDS` y `observed_training_ranges` en bundle y `ModelStore`. Caso 23.55 °C vs [14.31, 18.69] °C rechazado. | `tests/revision/test_learned_domain_bounds.py` |
| 7. Eliminar Fallbacks Silenciosos | Fallos de ABM continuaban con 0 simulaciones y falta de pymoo hacía muestreo aleatorio. | Excepción explícita `RuntimeError` ante ausencia de Mesa o pymoo en ejecución científica. Dobles restringidos a `test_mode=True`. | `tests/revision/test_strict_no_fallbacks.py` |
| 8. Procedencia de Datos Veraz | Columnas se etiquetaban como NASA POWER por su nombre sin evidencia de importación. | Clasificación veraz condicionada a evidencia o snapshots. Datasets sintéticos etiquetados como `v2_corrected` sin claims infundados. | `tests/revision/test_true_provenance.py` |
| 9. Conservar Precisión en Optimización | Redondeo prematuro a 2 y 3 decimales descartaba soluciones legítimas y seleccionaba candidatos no admisibles. | Precisión continua (`float32`/`float64`) en decisiones, objetivos y dominancia. Estado explícito `status='infeasible'` cuando no hay solución admisible. | `tests/revision/test_pareto_precision.py` |
| 10. Identidad de Bundle y Caché | Carga fallida destruía el modelo activo en memoria y la caché colisionaba entre bundles. | `bundle_id` persistente, recarga atómica preservando el modelo previo y clave de caché rígida vinculada al `bundle_id` con invalidación inmediata. | `tests/revision/test_bundle_atomic_cache.py` |
| 11. Trazabilidad y Artefactos | Manifiestos no registraban estados preliminares y `SHA256SUMS.txt` omitía bundles o se auto-referenciaba. | Manifiesto de ciclo de vida (`started`, `completed`, `failed`), nuevo run smoke limpio `smoke_20261028_071815` y `SHA256SUMS.txt` completo sin auto-referencia. | `cli.py smoke` y `persistence.py` |
| 12. Alineación CLI y Documentación | Subcomando `optimize` no existía en CLI y documentación divergía de flags reales. | Implementación de `cli.py optimize`, soporte `--model-dir` y sincronización total de reportes. | `cli.py optimize` y suite de 16 tests aprobados. |

---

## 5. Auditoría de Tercera Fase (Auditoría 02: 10 Bloques de Robustecimiento y Verificación Docker)

Una segunda ronda de auditoría técnica independiente identificó 10 áreas adicionales de robustecimiento en torno al entorno de contenedores Docker, la compuerta de auditoría de datos, la unificación de redes y bundles criptográficos:

1. **Docker y entorno científico ejecutable:** Creación de `requirements-scientific.txt`, `Dockerfile.scientific`, y servicio `scientific` en `docker-compose.yml` resolviendo `ModuleNotFoundError: No module named 'scientific_core'` en Streamlit.
2. **Auditoría de datos como bloqueo temprano:** `cli.py cmd_evaluate` audita antes de evaluar; si falla, detiene la ejecución con código 1 y manifest `failed` sin entrenar. `FileNotFoundError` si el dataset no existe.
3. **Unificación y microentrenamientos reales en redes:** Estandarización de parámetros con `normalize_neural_params`, propagación de hiperparámetros de familia y 4 microentrenamientos reales en Keras validados en Docker.
4. **Endurecimiento de bundles:** Validación estricta del orden de características, presencia obligatoria de `scalers.pkl`, verificación de hashes criptográficos SHA-256 y exportación atómica en directorio temporal.
5. **Medición fidedigna de tiempos:** Eliminación de tiempos fijos (0.1 s y 0.01 s) y medición real con `time.perf_counter()` en entrenamiento e inferencia.
6. **Selección de hiperparámetros agregada:** Promedio de MAE macro interno sobre todos los folds internos de todas las particiones externas en `cli.py export-model`.
7. **Modo científico en Streamlit:** `scientific_mode` estricto y auditoría previa bloqueante en la interfaz de usuario.
8. **Integración del dominio aprendido en NSGA-II:** Intersección de cotas físicas y aprendidas en `LandscapeOptimizationProblem`, con penalización de `1e5` para candidatos fuera de dominio.
9. **Trazabilidad en manifiestos:** Preservación de `started_at_utc`, inclusión de `generator_metadata` y `dataset_provenance`, y actualización de sección `bundle`.
10. **Verificación técnica integral:** 51/51 pruebas unitarias e integrales aprobadas en Docker, smoke run limpio (`smoke_20261028_162701`), exportación y validación de bundle (`bundle_ridge_7e97cb6c99bc`) y prueba de optimización multiobjetivo verificada.
