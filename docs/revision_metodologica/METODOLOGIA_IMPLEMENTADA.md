# Metodología Implementada — Gemelo Digital de Polinizadores

Versión: 1.0 (Revisión Metodológica)  
Fecha: 28 de octubre de 2026  
Destino editorial: Revista Ciencia y Tecnología Agropecuaria (AGROSAVIA)  

---

## 1. Comportamiento Histórico y Defectos Confirmados

Durante la auditoría inicial de partida (commit `1ab7c02`), se confirmaron empíricamente trece inconsistencias metodológicas en el código original:

1. **Fuga de datos por escalado global (H01):** `StandardScaler` en `streamlit_app/advanced_training.py` ajustaba la media y varianza sobre el vector completo de salidas `y` antes de dividir las particiones de KFold. Esto provocaba que los datos de validación estuviesen pre-escalados con información global de la distribución.
2. **Ausencia de validación anidada (H02):** La sintonización estocástica de hiperparámetros (`tune_all_hyperparameters`) se ejecutaba sobre el dataset completo antes de la validación cruzada externa, reportando métricas de validación optimistas.
3. **Contaminación en EarlyStopping (H03):** Las redes neuronales recibían el fold externo de evaluación como argumento `validation_data` en el callback `EarlyStopping`, adaptando los pesos retenidos y la época de parada temprana a la partición de prueba externa.
4. **Desacoplamiento entre modelo exportado y ganador global (H04 & H05):** El modelo exportado a `/modelos_ia` correspondía al fold con mejor $R^2$ de Keras, independientemente de si la familia ganadora global había sido Ridge o Random Forest, asociando el MAE global a dicha red y registrando marcadores ficticios `0.0` para RMSE y $R^2$.
5. **Incoherencia física en coberturas del suelo (H10):** Las variables `crop_area_pct` (35–82%), `natural_area_pct` (8–42%) y `floral_strips_pct` (2–18%) se generaban mediante variables aleatorias independientes, cuya suma podía superar el 100% del área de la parcela (hasta 142%), violando la física de partición de superficie.
6. **Discrepancia en diversidad de paisaje (H06/H07):** La función `landscape_diversity` en el optimizador NSGA-II era una función determinista de área natural, franjas florales y suelo, mientras que en el generador de entrenamiento se muestreaba como variable independiente.
7. **Enriquecimiento ABM heterogéneo (H11):** En el dataset histórico solo las primeras 120 filas recibían simulación del modelo basado en agentes (Mesa), mientras que las filas 121 a 320 conservaban los valores biofísicos base sin identificar la discontinuidad en la procedencia.
8. **Inferencia estadística no válida sobre predicciones concatenadas (H12):** `robust_tests.py` aplicaba pruebas $t$-Student pareadas y Wilcoxon sobre predicciones out-of-fold concatenadas tratando 320 muestras dependientes como si fuesen observaciones independientes de campo.
9. **Falso control de dominio y afirmaciones en interfaz (H08 & H13):** La validación de dominio se limitaba a la distancia Haversine a un centroide regional y emitía el mensaje *"Validez ecológica asegurada"*, mientras que el optimizador reportaba *"Hipótesis comprobada"* ante un simple umbral operativo de la heurística.
10. **Colisión de contenedores y volúmenes globales (H09):** `docker-compose.yml` declaraba nombres de contenedor fijos (`gemelos_db`, etc.) y volúmenes no aislados compartidos potencialmente con la copia histórica.

---

## 2. Comportamiento Implementado y Pruebas que lo Respaldan

Se implementó el paquete científico desacoplado `scientific_core/` junto con la refactorización de los consumidores en `backend/` y `streamlit_app/`:

1. **Aislamiento de entorno (M02 - T17):**
   - Parametrización de puertos en `docker-compose.yml`: base de datos (5433), backend (8001), frontend (5174), streamlit (8502) y langflow (7861).
   - Eliminación de `container_name` fijos y aislamiento automático de volúmenes bajo el nombre de proyecto `polinizadores_revision`. Perfil opcional para Langflow.
   - Verificado con `docker compose --project-name polinizadores_revision config` (T17 OK).

2. **Física de coberturas y contratos (`contracts.py` y `generator.py` - M03 - T02):**
   - Coberturas excluyentes: `crop_area_pct + natural_area_pct + floral_strips_pct <= 100.0` estrictamente garantizado en el generador y optimizador.
   - Fórmula unificada de `calculate_landscape_diversity(natural, floral, soil)` compartida entre generador, línea base y candidatos de optimización (T13 OK).
   - Validador riguroso de integridad `audit_dataset` que identifica y rechaza NaNs, valores infinitos, sumas superiores al 100% y agrupa duplicados (T02 OK).

3. **Evaluación predictiva anidada sin contaminación (`nested_cv.py` - M04 - T03 a T09):**
   - Validación cruzada anidada estricta: 5 folds externos y 3 folds internos dentro de cada partición de entrenamiento externa.
   - El escalado `StandardScaler` de entradas y salidas se ajusta **estrictamente sobre las filas de entrenamiento autorizadas** (T04 OK).
   - Subpartición de monitorización interna para EarlyStopping en redes neuronales, sin acceso a la validación de puntuación interna ni al test externo (T05 OK).
   - Instancias limpias de modelos entre particiones para evitar contaminación de coeficientes (T06 OK).
   - Matriz de predicciones Out-Of-Fold (OOF) completa sin NaNs (T07 OK).
   - Reconstrucción descriptiva exacta de métricas a partir del archivo OOF persistido (T08 OK).
   - Selección objetiva del modelo desplegable gobernada por menor MAE macro en unidades originales (T09 OK).

4. **Persistencia estructurada e índice criptográfico (`persistence.py` - M05):**
   - Creación de jerarquía de artefactos por ejecución bajo `artifacts/revision_metodologica/<run_id>/`:
     - `manifest.json`, `config_effective.json`, `environment.json`, `data_audit.json`, `dataset.csv`, `splits.json`, `tuning_results.csv`, `fold_metrics.csv`, `oof_predictions.csv`, `model_summary.csv`.
     - `SHA256SUMS.txt` que indexa todos los archivos generados excluyéndose a sí mismo.

5. **Predictor universal y serialización (`model_bundle.py` - M06 - T10, T11):**
   - `UniversalSurrogatePredictor`: interfaz agnóstica que soporta Ridge, Random Forest, XGBoost y redes Keras. Recibe matriz (N, 8) y devuelve predicciones (N, 3) en escala original aplicando las transformaciones requeridas sin doble inversión.
   - Verificación de equivalencia numérica exacta antes y después de exportar (tolerancia < 1e-4) (T10 OK).
   - Rechazo controlado de artefactos o metadatos incoherentes (T11 OK).

6. **Dominio, precisión y optimización (`optimization.py`, `model_store.py` - M07 - T12 a T15):**
   - Rechazo trazable con `ValueError` ante códigos climáticos desconocidos o entradas fuera de rango (T12 OK).
   - Predicción a precisión completa sin redondeo de candidatos previo a la inferencia.
   - Filtrado estricto de dominancia de Pareto a precisión completa (`filter_verified_pareto_front`) eliminando soluciones dominadas y duplicadas (T14 OK).
   - Inclusión de la versión del modelo en la clave SHA-256 de caché, garantizando que recargar o cambiar de modelo invalide de inmediato los resultados anteriores (T15 OK).

7. **Desacoplamiento de narrativa y actualización de interfaz (`recommendation_service.py`, `ResultsDashboard.jsx` - M08, M09 - T16):**
   - Recomendaciones narrativas no mutan las métricas estructuradas y declaran explícitamente su origen (`[Origen: ...]`) (T16 OK).
   - Reemplazo de claims no demostrados: *"Hipótesis comprobada"* se sustituye por *"Criterio operativo de mejora conjunta cumplido (+20% abundancia simulada con rendimiento no degradado)"*.
   - Se eliminaron promesas de rentabilidad económica o validación de campo asegurada.

8. **CLI desacoplada de Streamlit (`cli.py` - M11 - T19):**
   - Soporte para subcomandos: `audit-data`, `generate-data`, `evaluate`, `recompute-metrics`, `export-model`, `validate-bundle`, `smoke`.
   - Ejecución del smoke test T19 verificada satisfactoriamente (`artifacts/revision_metodologica/smoke_20261028_060521`).

---

## 3. Configuración Prevista para el Experimento Definitivo

Fijada en `configs/revision_metodologica.json`:

| Parámetro | Configuración Definitiva | Configuración Smoke (Verificación Técnica) |
|---|---|---|
| Muestras del dataset | 320 filas sintéticas/calibradas | 40 filas |
| Política ABM | `corrected_full` (enriquecimiento 100% uniforme) | `corrected_none` |
| Restricción física | `crop + natural + floral <= 100%` estricta | `crop + natural + floral <= 100%` estricta |
| Folds externos (CV) | 5 folds, mezcla pseudoaleatoria semilla 42 | 2 folds, semilla 42 |
| Folds internos (Tuning) | 3 folds, semilla 1042 | 2 folds, semilla 1042 |
| Métrica primaria | Menor MAE macro en unidades originales | Menor MAE macro en unidades originales |
| Familias evaluadas | Ridge, Random Forest, XGBoost, DNN, Autoencoder+MLP | Ridge, Random Forest |
| Presupuesto por familia | 4 combinaciones predefinidas en grilla | 1 combinación base |
| Épocas máximas redes | 30 épocas (batch 24, patience 5) | 2 épocas |
| Paralelismo | 1 proceso secuencial (CPU amigable) | 1 proceso secuencial |
| Modo de ejecución | `test_only: false` | `test_only: true` |

---

## 4. Qué NO se Ejecutó en esta Fase

Para estricto cumplimiento del plan y las instrucciones del usuario:
1. **NO se ejecutó la campaña definitiva de entrenamiento con 5 folds y 320 simulaciones ABM completas.** Se verificó la viabilidad del camino mediante fixtures y el smoke test T19.
2. **NO se realizaron pruebas manuales en navegador ni navegación UI.** Se auditó y corrigió el código fuente del frontend estáticamente.
3. **NO se realizaron commits de Git, push a repositorios remotos ni publicación de datos.**
4. **NO se editaron documentos Word ni archivos de manuscrito.**
5. **NO se incorporó cuantificación de incertidumbre (Sobol) no justificada ni arquitecturas adicionales.**

---

## 5. Limitaciones Científicas que Permanecen

El artículo y los reportes técnicos deben consignar honestamente las siguientes limitaciones:
1. **Naturaleza de los datos:** Las 320 muestras se generan a partir de distribuciones estadísticas calibradas con NASA POWER y GBIF, pero **no representan observaciones de campo individuales independientes**.
2. **Diversidad del ABM:** La variable `pollinator_diversity_index` en el modelo Mesa no es una propiedad emergente del comportamiento de agentes, sino una combinación lineal de las características del paisaje.
3. **Optimización operacional:** El frente de Pareto y la solución seleccionada corresponden a un compromiso matemático bajo modelos subrogados y reglas de puntuación predefinidas, no a prescripciones agronómicas empíricamente validadas en parcelas reales.
4. **Semántica de Autoencoder:** La arquitectura rotulada como Autoencoder+MLP actúa como un cuello de botella supervisado sin reconstrucción no supervisada del espacio de entrada.


---

## 6. Correcciones Metodológicas de Segunda Fase (Mandatos 1 a 12)

Tras la auditoría independiente, se implementaron de forma definitiva doce mandatos metodológicos con pruebas unitarias aisladas:

1. **Evaluación completa de redes neuronales (DNN y Supervised Bottleneck MLP):**
   - Búsqueda interna de hiperparámetros anidada dentro del entrenamiento del fold externo.
   - Subpartición interna de monitorización (20%) separada de la partición de validación interna que puntúa candidatos (80% core train), respetando los grupos de duplicados.
   - `StandardScaler` ajustado exclusivamente sobre los datos de entrenamiento autorizados (core train).
   - EarlyStopping sin acceso a la validación de puntuación ni al test externo.
   - Registro de épocas óptimas por partición interna; la mediana de épocas determina la política para el reajuste externo.
   - Reajuste externo sobre todo el entrenamiento del fold prediciendo sobre el test externo en escala original.

2. **Unificación de Streamlit y CLI sobre el núcleo científico:**
   - `streamlit_app/advanced_training.py` adaptado para delegar directamente en `scientific_core.nested_cv.run_nested_cv`.
   - Eliminación del sintonizado previo global de hiperparámetros antes de la CV externa.
   - Contratos unificados: `results_df`, `best_overall`, `predictor` y `target_scaler` construidos a partir de métricas reales de validación cruzada anidada, eliminando marcadores ficticios `0.0`.
   - Exportación desde la UI mediante `export_bundle` exportando la familia ganadora real (ya sea tradicional o neuronal) con sus escaladores y metadatos.

3. **Exportación vinculada estrictamente al experimento:**
   - `cli.py export-model` exige un run evaluado con estado `completed`.
   - Verificación de integridad criptográfica de `dataset.csv` contra el hash del manifiesto.
   - Refit documentado sobre los datos identificados del experimento utilizando los mejores hiperparámetros de la CV.
   - Marcación obligatoria de `test_only=true` en el bundle si el run de origen fue un smoke test.

4. **Contrato único de preprocesamiento e inferencia multi-familia:**
   - `scaler_x` y `scaler_y` aplicados de manera homogénea a Ridge, Random Forest, XGBoost y Redes Neuronales en `UniversalSurrogatePredictor` y `ModelStore`.
   - Verificación de paridad numérica exacta (tolerancia < 4e-6) entre el modelo evaluado, el predictor pre-exportación, el bundle recargado y el backend FastAPI.

5. **Agrupamiento estable de duplicados (GroupKFold):**
   - Agrupamiento de filas mediante `compute_feature_groups` según la tupla de características de entrada.
   - Particiones externas, internas y de monitorización gobernadas por `GroupKFold`, garantizando que ninguna réplica de un mismo escenario cruce entre entrenamiento y evaluación.

6. **Control de dominio basado en rangos observados de entrenamiento:**
   - Diferenciación formal entre `PHYSICAL_BOUNDS` (límites físicos generales) y `observed_training_ranges` (mínimos y máximos empíricos del dataset entrenado).
   - Rechazo en modo científico de valores fuera del rango observado (ej. 23.55 °C rechazado ante un rango de 14.31–18.69 °C).
   - Advertencia explícita en el API sobre las limitaciones del cumplimiento univariado frente al soporte conjunto multidimensional.

7. **Eliminación de fallbacks silenciosos en ejecución científica:**
   - Excepción explícita `RuntimeError` ante fallos de ABM con política `corrected_full` o falta de dependencias (Mesa, pymoo) en ejecución científica.
   - Supresión de la omisión automática de modelos habilitados si faltan dependencias.
   - Restricción estricta de dobles de prueba a ejecuciones con `test_mode=True`.

8. **Procedencia veraz de datos:**
   - La clasificación de variables en `data_audit.py` se deriva de evidencia de generación o importación, no del nombre de columna.
   - Identificación de datasets sintéticos como `v2_corrected` sin atribución a NASA POWER o GBIF salvo que existan snapshots verificados.
   - Preservación de la versión histórica `v1_historical`.

9. **Preservación de precisión en optimización multi-criterio:**
   - Almacenamiento y procesamiento continuo de decisiones y objetivos a precisión flotante completa (`float32`/`float64`).
   - Deduplicación con tolerancia continua (`decision_atol=1e-5`) y dominancia de Pareto sin redondeos preliminares (`objective_tol=1e-7`).
   - Respuesta explícita `status='infeasible'` cuando ningún candidato cumple el dominio biofísico, suprimiendo la selección forzada del primer candidato.

10. **Identidad persistente de bundle, carga atómica y caché estricta:**
    - Generación de `bundle_id` persistente y trazable en metadatos.
    - Carga atómica en `ModelStore`: validación previa en variables locales para preservar intacto el modelo anterior ante fallos de disco.
    - Clave de caché vinculada al `bundle_id` con invalidación inmediata al conmutar de modelo.

11. **Trazabilidad y estados de ciclo de vida:**
    - Manifiestos de ciclo de vida: inicialización en `started`, actualización a `failed` ante errores, y cierre en `completed` al persistir todos los artefactos.
    - `SHA256SUMS.txt` que indexa todos los archivos generados y el subdirectorio de bundle sin auto-referencia.

12. **Alineación de CLI y comandos de reproducción:**
    - Subcomando `cli.py optimize` disponible para ejecución desde terminal con soporte de escenarios, restricciones de manejo y `--model-dir`.
    - Documentación técnica sincronizada con los flags reales de ejecución.

---

## 7. Robustecimiento de Tercera Fase (Auditoría 02: 10 Bloques)

Para resolver definitivamente las discrepancias detectadas en la segunda auditoría técnica independiente, se implementaron diez bloques adicionales de endurecimiento y verificación en contenedor:

1. **Entorno de ejecución científico unificado y reproducible:**
   - Creación de `requirements-scientific.txt` que consolida Scikit-Learn (1.5.2), XGBoost (2.1.1), TensorFlow (2.17.1), Mesa (2.3.4), pymoo (0.6.1.3), Shapely (2.0.6) y pytest (9.2.0).
   - Configuración de `Dockerfile.scientific` y adaptación de los Dockerfiles de Streamlit y backend para construir desde la raíz con `PYTHONPATH=/app`.
   - Definición del servicio `scientific` en `docker-compose.yml` bajo el proyecto `polinizadores_revision`, eliminando colisiones de volumen y puerto.

2. **Auditoría de datos como compuerta de bloqueo (Gatekeeper):**
   - En `cli.py cmd_evaluate`, ejecución obligatoria de `audit_dataset(df, policy="corrected")`.
   - Si la auditoría falla (`audit_passed = false`), el proceso se cancela inmediatamente con código de salida 1, generando `data_audit.json` y marcando el manifiesto como `failed` sin entrenar ningún modelo sustituto.
   - Si el archivo indicado en `--dataset` no existe, se arroja `FileNotFoundError` impidiendo sustituciones silenciosas de datos.

3. **Unificación de hiperparámetros y microentrenamientos reales en redes:**
   - Función `normalize_neural_params` en `nested_cv.py` que estandariza la nomenclatura (`hidden_units` / `layers`, `dropout_rate` / `dropout`, `latent_dim` / `bottleneck_dim`, `regressor_units` / `decoder_units`, `early_stopping_patience` / `patience`).
   - Propagación de hiperparámetros de familia (`batch_size`, `max_epochs`, `patience`) a las cuadrículas individuales.
   - Manejo robusto de la subpartición de monitorización para EarlyStopping cuando hay pocos grupos de duplicados.
   - Arquitecturas diferenciadas en configuración y 4 microentrenamientos reales en Keras validados en Docker.

4. **Validación criptográfica y atomicidad de bundles:**
   - Validación estricta de la presencia y orden de `feature_names` y `target_names` contra contratos.
   - Presencia obligatoria de `scalers.pkl` cuando `scaler_x_applied = True`, arrojando `FileNotFoundError` si falta.
   - Validación de hashes criptográficos SHA-256 de todos los archivos componentes al cargar un bundle.
   - Exportación atómica mediante subdirectorio temporal y verificación de predicción dummy previa a la consolidación.
   - Retención del modelo operativo previo en `ModelStore` si la recarga de un bundle corrupto falla.

5. **Medición fidedigna de tiempos de cómputo:**
   - Medición con `time.perf_counter()` de duración de entrenamiento por fold y familia, así como latencia de inferencia sobre muestra unitaria.
   - Eliminación de tiempos ficticios (0.1 s y 0.01 s) en `streamlit_app/advanced_training.py`.
   - Tratamiento de valores nulos como "No medido" en interfaces de reporte.

6. **Selección de hiperparámetros agregada sobre todos los folds internos:**
   - En `cli.py cmd_export_model`, agregación del MAE macro interno (`mean()`) sobre todos los folds internos de todas las particiones externas en `tuning_results.csv`.
   - Prevención del sesgo de partición única y registro detallado de `final_selection_policy` con el ranking de candidatos evaluados.

7. **Alineación de Streamlit con modo científico y auditoría previa:**
   - Soporte de `scientific_mode` en `advanced_training.py` que prohíbe omisiones silenciosas de dependencias.
   - Ejecución preliminar de `audit_dataset` en la UI de Streamlit, bloqueando el entrenamiento si existen inconsistencias en el dataset.

8. **Integración matemática del dominio aprendido en NSGA-II:**
   - Intersección de límites físicos generales (`PHYSICAL_BOUNDS`) con los rangos observados durante el entrenamiento (`observed_training_ranges`) en las cotas de `LandscapeOptimizationProblem`.
   - Asignación de penalizaciones severas (`1e5` en objetivos y `1e3` en restricciones) si un candidato viola las cotas aprendidas.
   - Filtrado exhaustivo en `filter_verified_pareto_front` para garantizar que toda solución del frente Pareto cumpla el dominio empírico.
   - Manejo controlado de casos sin solución admisible retornando `status: "infeasible"`.

9. **Trazabilidad de ciclo de vida y procedencia en manifiestos:**
   - Preservación inmutable de `started_at_utc` en `manifest.json`.
   - Incorporación de metadatos del generador (`generator_metadata`) y procedencia de columnas (`dataset_provenance`) aclarando la naturaleza sintética calibrada del dataset.
   - Actualización del bloque `bundle` al exportar el modelo (`update_manifest_bundle`).
   - Cálculo de sumas SHA-256 excluyendo estrictamente `SHA256SUMS.txt` de su propio cómputo.

10. **Aprobación integral de pruebas y ejecución limpia de smoke test:**
    - 51/51 pruebas unitarias y de integración superadas al 100% en el contenedor científico.
    - Ejecución limpia de smoke test (`smoke_20261028_162701`) con generación de todos los artefactos, exportación del bundle universal (`bundle_ridge_7e97cb6c99bc`) y verificación del solucionador NSGA-II por CLI.

---

## 8. Consolidación de la Auditoría 03: Robustecimiento de Contratos, Selección Unificada y Conteo de Evaluaciones

En una tercera fase de revisión metodológica independiente, se implementaron siete bloques de robustecimiento:

1. **Unificación de selección y reajuste final:**
   - Creación de la función canónica `select_final_hyperparameters` compartida por CLI y Streamlit.
   - Deserialización segura `parse_params_string` (`null` $\to$ `None`) que elimina el fallo silencioso donde `ast.literal_eval` sustituía parámetros válidos por `{}`.
   - Desempates deterministas y propagación comprobada de los tipos nativos seleccionados al modelo reajustado.
   - Documentación explícita de las limitaciones metodológicas de la agregación entre folds externos.

2. **Centralización de la validación y carga en `load_bundle`:**
   - `load_bundle` se consolidó como única fuente de verdad consumida por `ModelStore` y la CLI.
   - Comprobación estricta previa de sumas SHA-256 antes de proceder a la deserialización de pickles o modelos H5, mitigando riesgos de seguridad e integridad.
   - Validación mandatoria de escaladores no nulos con sus dimensiones estadísticas, esquema 2.0 y coincidencia estricta de orden en variables.

3. **Publicación y activación atómicas:**
   - Respaldo temporal automático previo durante `export_bundle` con restauración ante fallos intermedios.
   - Conmutación atómica de la referencia en memoria en `ModelStore` e invalidación inmediata de la caché de simulación (`simulation_cache.clear()`).

4. **Flujo científico completo en Streamlit:**
   - Conmutador en interfaz entre "Modo Científico Estricto (AGROSAVIA)" y "Modo Exploratorio".
   - Persistencia completa de los 11 artefactos estandarizados en `artifacts/revision_metodologica/<run_id>/` tras cada entrenamiento.
   - Vinculación explícita de la exportación de modelos con el run de origen.

5. **Contratos de datos y preservación del diseño experimental:**
   - Exigencia estricta de presencia y tipo numérico para todas las 8 columnas de características y 3 de objetivos en `audit_dataset`.
   - Detección y reporte explícito de `duplicate_sample_ids` y rechazo de datasets vacíos.
   - Prohibición de reducción silenciosa de folds en modo científico ante pocos grupos.
   - Persistencia de la estructura jerárquica de particiones externas e internas en `splits.json`.

6. **Paridad en 4 etapas para arquitecturas neuronales:**
   - Verificación de equivalencia numérica estricta ($< 10^{-5}$) entre el modelo evaluado, el predictor pre-exportación, el bundle recargado y el `ModelStore` de FastAPI para `dnn` y `autoencoder_mlp`.
   - Prueba de integración end-to-end con Keras validada en el runtime de Docker.

7. **Distinción matemática en optimización y smoke run actual:**
   - Distinción explícita en `optimization.py` y CLI entre las evaluaciones totales realizadas por el algoritmo NSGA-II ($pop\_size \times n\_gen = 2560$) y el número de soluciones no dominadas en el frente de Pareto devuelto (64).
   - Generación de la corrida smoke limpia `smoke_20261028_173336`, preservando intactos todos los registros y artefactos de las corridas históricas previas.
   - Suite total de pruebas de regresión ampliada a 76 items (100% de aprobación en contenedor científico).

---

## 9. Consolidación de la Auditoría 04: Adaptador de Streamlit, Infactibilidad, Criterio Conjunto, Identidad Canónica y Docker Prod

En la cuarta fase de revisión metodológica focalizada, se corrigieron los fallos reproducidos en 5 bloques específicos:

1. **Persistencia real en Streamlit y adaptador desacoplado (`streamlit_app/adapter.py`):**
   - Resolución de la discordancia en la firma de `init_run_manifest` (`output_dir` vs `run_dir`).
   - Inicialización obligatoria del manifiesto con estado `started` previo al cómputo y registro de estado `failed` (`record_run_failure`) ante excepciones no controladas.
   - Enlace estricto entre la exportación de modelos y el dataset efectivamente utilizado durante el entrenamiento (`training_dataset` persistido), bloqueando la posibilidad de exportar con datasets alterados en el estado volátil de la interfaz.
   - Persistencia completa de los 11 artefactos normalizados del ciclo de vida en `artifacts/revision_metodologica/<run_id>/`.

2. **Tratamiento robusto de infactibilidad en API y Frontend:**
   - Enriquecimiento del esquema `SimulationResultPayload` para admitir de forma opcional `best_solution: None` y `status: "infeasible"`.
   - Prevención de excepciones `TypeError` al intentar leer propiedades nulas en `backend/app/main.py` y `recommendation_service.py`, almacenando la simulación sin métricas inventadas en base de datos.
   - En `frontend/src/components/ResultsDashboard.jsx`, incorporación de banderas protectoras `isInfeasible`, renderizado de banner informativo de restricciones insatisfechas y protección contra lecturas indebidas de propiedades.

3. **Criterio operativo de mejora conjunta y prohibición de afirmaciones desmedidas:**
   - Definición rigurosa de la condición de éxito agronómico y ecológico: cumplimiento simultáneo de `delta_yield >= 0` (rendimiento no degradado) Y `delta_pollinators >= 20.0` (+20% abundancia simulada).
   - Indicador estructurado `meets_joint_criteria` calculado en backend y consumido directamente en frontend, sustituyendo búsquedas frágiles de cadenas en texto libre.
   - Fraseo obligatorio: *"Criterio operativo de mejora conjunta cumplido/no alcanzado"*. Erradicación de claims sobre "confirmación empírica" o "validación de campo" en toda la interfaz.

4. **Contrato de bundle e identidad canónica determinista:**
   - En exportación científica (`strict_scientific=True`), prohibición del fallback por defecto de `observed_training_ranges` a `PHYSICAL_BOUNDS`; validación obligatoria de las 8 características, finitud, $min \le max$ y compatibilidad con cotas biofísicas.
   - Validación mandatoria en `load_bundle` de versiones de esquema soportadas (`schema_version in {"2.0", "2.0_revision_metodologica"}`).
   - Exigencia estricta de hash de modelo y `scalers.pkl` en `file_hashes` antes de iniciar la deserialización.
   - Derivación determinista del `bundle_id` incorporando los hashes de modelo y escaladores, familia, contrato de preprocesamiento, orden lexicográfico canónico de rangos observados y marca `test_only`.

5. **Alineación de contextos de compilación en Docker Compose de Producción:**
   - Configuración de `context: .` en `docker-compose.prod.yml` para los servicios `backend` y `streamlit`, apuntando a `./backend/Dockerfile` y `./streamlit_app/Dockerfile`.
   - Garantía de que todas las directivas `COPY` dispongan de sus fuentes en el contexto raíz sin fallos de compilación.

6. **Verificación integral y preservación histórica:**
   - Suite completa de regresión ampliada a 96 items en `tests/revision/` (96 pasados, 0 fallidos, 100% de éxito).
   - Generación de la corrida smoke `smoke_20261028_182934`, exportación de bundle `bundle_ridge_bd24bc5fdf03`, validación de integridad SHA-256 (16 hashes deterministas) y optimización NSGA-II validada por CLI. Preservación intacta de las 4 corridas smoke anteriores.

---

## 10. Consolidación de la Auditoría 05: Configuración Única en Streamlit, Consulta Segura de Infactibles y Precisión Flotante

En la quinta fase de revisión metodológica focalizada, se resolvieron tres discrepancias técnicas reproducidas:

1. **Configuración única para ejecución y persistencia en Streamlit (`streamlit_app/adapter.py`, `advanced_training.py`):**
   - Eliminación de la doble preparación divergente del protocolo de entrenamiento.
   - Creación canónica mediante `prepare_streamlit_run_config` y transmisión directa a `train_and_evaluate_all_models` y `save_run_artifacts`.
   - En modo científico estricto (`scientific_mode=True`), rechazo formal con `ValueError` si se solicita `group_duplicates=False`, garantizando que `GroupKFold` agrupe siempre instancias repetidas para evitar fugas entre particiones.
   - En modo exploratorio (`scientific_mode=False`), respeto estricto y sincronizado de `group_duplicates=False` tanto en la llamada a `run_nested_cv` como en la persistencia física en `config_effective.json`.

2. **Consulta e integridad de simulaciones sin solución en Chat, Historial y Reportes:**
   - Formalización de `metricas_optimas: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)` en `backend/app/models/simulation.py`.
   - En `backend/app/services/chat_service.py` (`query_simulation_details`), verificación rigurosa de tipo antes de acceder a atributos de métricas óptimas, erradicando la excepción fatal `AttributeError: 'NoneType' object has no attribute 'get'`.
   - Retorno explícito de `tiene_solucion_optima: False`, `metricas_optimas: None` y `mejoras: {"delta_rendimiento": None, "delta_polinizadores_porcentaje": None, "estado": "no_evaluable"}`, prohibiendo la fabricación espuria de valores copiando la línea base.
   - Preservación estricta del control de acceso por rol y pertenencia (`status="forbidden"`).
   - Generación transparente en el chat de un mensaje explicativo de infactibilidad biofísica sin claims erróneos.
   - En `backend/app/services/report_general_service.py` (`get_management_report`), tratamiento seguro de simulaciones infactibles: se contabilizan en el total pero no suman a la tasa de cumplimiento de la hipótesis ni sesgan los promedios globales de optimización.

3. **Evaluación del criterio operativo a precisión numérica completa antes del redondeo:**
   - En `backend/app/services/optimization.py` (`run_simulation`), cálculo y comparación de `raw_delta_yield >= 0.0 and raw_delta_pollinators >= 20.0` a nivel de precisión flotante estricta previa a cualquier redondeo.
   - Eliminación de falsos positivos en frontera (ej. caída de rendimiento de -0.0004 y aumento de polinizadores de 19.9998% que al redondearse a 0.000 y 20.000% evaluaban erróneamente cumplimiento).
   - Restricción del redondeo a 3 decimales (`round(..., 3)`) exclusivamente a los campos de salida visual (`delta_yield`, `delta_pollinators`).
   - Asignación de `meets_joint_criteria: None`, deltas en `None` y estado *"No evaluable: sin soluciones admisibles dentro del dominio"* ante corridas infactibles.

4. **Verificación integral y preservación histórica:**
   - Suite total de pruebas ampliada a **113 items en `tests/revision/` (113 pasados, 0 fallidos, 100% de éxito en 111.38s)**.
   - Generación de la corrida smoke limpia `smoke_20261028_191444`, exportación de bundle `bundle_ridge_bd24bc5fdf03`, validación criptográfica de integridad SHA-256 (16 hashes deterministas verificados con `sha256sum -c`) y optimización evolutiva NSGA-II verificada por CLI. Preservación inmutable de las 5 corridas smoke históricas anteriores.


---

## 11. Consolidación de la Auditoría 06: Semilla Efectiva Canónica del Reajuste Final y Comparaciones Pareadas en Gestión

En la sexta fase de revisión metodológica focalizada, se resolvieron y verificaron dos discrepancias adicionales detectadas por la auditoría independiente:

1. **Semilla efectiva gobernante del reajuste final en Streamlit (`advanced_training.py`, `adapter.py`):**
   - Resolución de la semilla final canónica `final_seed` directamente desde el objeto único de configuración efectiva (`int(config.get("seed") or config.get("outer_cv", {}).get("seed", random_state))`).
   - Aplicación estricta de `final_seed` en la inicialización y entrenamiento de modelos tradicionales (`ModelFactory.create_model(..., seed=final_seed)`) y arquitecturas neuronales (`fit_and_predict_neural_outer(..., seed=final_seed)`).
   - Inyección y preservación formal de `final_seed` en los metadatos de predicción (`UniversalSurrogatePredictor.metadata`), en el manifiesto de la corrida y en los metadatos exportados del bundle (`bundle_metadata.json`), erradicando la contradicción donde el modelo final persistido se ajustaba con la semilla predeterminada 42 a pesar de haberse solicitado una semilla personalizada (ej. 1337).

2. **Principio de comparación pareada estricta en informes de gestión (`get_management_report`, `schemas_reports.py`):**
   - Eliminación de la distorsión estadística no pareada en el cálculo de deltas y tasas de mejora agroecológica.
   - Separación estricta entre la población total de simulaciones y la subpoblación con soluciones factibles evaluables:
     - Las líneas base totales de toda la cohorte se preservan con denominación explícita (`rendimiento_promedio_base_total`, `abundancia_polinizadores_base_total`, `diversidad_polinizadores_base_total`).
     - Los promedios base para el cálculo de deltas y porcentajes de mejora provienen estrictamente de las mismas simulaciones evaluables que aportaron valores óptimos.
     - En el escenario de discrepancia de la auditoría (Sim A con base=100, óptimo=110 junto a Sim B infactible con base=1000, óptimo=None), el delta evaluable resulta exactamente en **+10.0** (y no en el erróneo -440.0 previo).
   - Incorporación de campos de recuento explícito (`simulaciones_evaluables`, `simulaciones_no_evaluables`) y especificación explícita del denominador de tasa (`denominador_tasa = "evaluables"`).
   - Ausencia de datos formal (`None`) ante cero simulaciones evaluables, prohibiendo la fabricación artificial de deltas con ceros espurios.
   - Aplicación idéntica del criterio pareado en agregaciones globales, regionales y temporales.

3. **Verificación técnica integral y preservación histórica:**
   - Suite total de pruebas ampliada a **125 items en `tests/revision/` (125 pasados, 0 fallidos, 100% de éxito en 111.19s)**.
   - Generación de la corrida smoke limpia `smoke_20261028_195256`, exportación de bundle canónico `bundle_ridge_bd24bc5fdf03`, validación formal de bundle, optimización evolutiva NSGA-II verificada por CLI e integridad criptográfica total comprobada (16/16 archivos validados con `sha256sum -c`). Preservación inmutable de las 6 corridas smoke históricas anteriores.


---

## 12. Consolidación de la Auditoría 07: Coherencia Poblacional en Informes de Gestión y Preservación de Ausencia de Datos en Consumidores

En la séptima fase de revisión metodológica focalizada, se resolvieron las discrepancias identificadas en la partición de recuentos de gestión y la representación de datos ausentes en interfaz y exportadores:

1. **Partición Canónica de Recuentos de Gestión (`report_general_service.py`, `schemas_reports.py`):**
   - Corrección de la fórmula de simulaciones que no cumplen el criterio conjunto: `simulaciones_no_cumplen = (simulaciones_evaluables - simulaciones_cumplen_hipotesis) if simulaciones_evaluables > 0 else 0`.
   - Garantía de la identidad de conservación poblacional: `total_simulaciones = simulaciones_evaluables + simulaciones_no_evaluables`, donde `simulaciones_evaluables = simulaciones_cumplen_hipotesis + simulaciones_no_cumplen`.
   - Propagación de los recuentos `simulaciones_cumplen_hipotesis` y `simulaciones_no_cumplen` a las agregaciones por región (`RegionManagementItem`) y a la serie de evolución temporal (`ManagementTemporalEvolutionPoint`).
   - Mantenimiento explícito del denominador de tasa (`denominador_tasa = "evaluables"`), asegurando que ante cero evaluables la tasa permanezca como `None` (sin inventar 0%).

2. **Preservación de Ausencia de Datos vs. Cero Real y Corrección Terminológica en Consumidores (`generalReportExporters.js`, `AdminReportsPage.jsx`):**
   - Discriminación rigurosa entre valor ausente (`null` o `undefined` $\to$ `"N/D"`) y valor numérico real igual a cero (`0.0 pts`, `0.0%`).
   - En exportación a Excel, erradicación de fallbacks que convertían `null` a `0`. Desglose formal de filas para total registradas, evaluables, no evaluables, denominador de tasa, cumplimiento y no cumplimiento. Corrección del rótulo engañoso "Total Simulaciones Evaluadas" por "Total Simulaciones Registradas".
   - En la página de administración (`AdminReportsPage.jsx`), incorporación de una barra de resumen poblacional visible y formateadores de tarjetas de métricas que presentan `"N/D"` ante ausencia de soluciones factibles.
   - Reemplazo exhaustivo de la expresión no científica "hipótesis comprobada" por **"criterio operativo de mejora conjunta"** en exportadores (PDF, Word, Excel) y componentes visuales.

3. **Verificación Técnica de Código y Alcance de Evidencias:**
   - 132 pruebas automatizadas en `tests/revision/` aprobadas al 100% en Docker científico (incluyendo suite `test_audit07_management_reports_and_exporters.py` con Casos A a G).
   - 5 pruebas lógicas en Node.js para formateadores y estructura Excel (`test_audit07_frontend_exporters.mjs`), comprobando fidelidad de datos con dependencias simuladas. **No certifican la generación física ni la revisión visual de documentos PDF y Word**.
   - Total: **137 verificaciones técnicas automatizadas a nivel de código**.
   - **Estado de validación**: Las pruebas manuales en navegador (Streamlit / React), la generación física de PDF/Word y la campaña científica definitiva (320 ABM / 5 folds) permanecen formalmente pendientes y quedan articuladas en el `PLAN_VALIDACION_FUNCIONAL.md`. El sistema no se declara completamente validado.
