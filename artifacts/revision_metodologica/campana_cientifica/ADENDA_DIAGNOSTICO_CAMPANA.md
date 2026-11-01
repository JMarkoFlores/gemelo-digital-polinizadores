# Adenda Metodológica y Documental: Diagnóstico Crítico de la Campaña Científica

**Proyecto:** Gemelo Digital Agroecológico para la Gestión de Polinizadores  
**Rama:** `revision-metodologica`  
**Entorno Aislado:** Docker Compose `polinizadores_validacion`  
**Fecha de Emisión:** 2026-10-29  
**Referencia de Corrida Auditada:** `run_20261029_153857`  
**Dataset Evaluado:** `dataset_320_corrected_full.csv` (SHA-256: `0467f8ba1f04c6b9b5d5947074479acada6fdc259029219224e2bf1b4b7abb64`)  
**Estado:** ADENDA DOCUMENTAL INDEPENDIENTE (Sin alteración de código, artefactos ni hashes previos)

---

## 1. Naturaleza Analítica de la Diversidad en `PollinatorLandscapeModel.run()`

En la documentación preliminar de la campaña se describió la variable `pollinator_diversity_index` como una propiedad emergente derivada del simulador de agentes Mesa. La inspección directa del código fuente en [`streamlit_app/pollinator_abm.py`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/streamlit_app/pollinator_abm.py#L174-L184) revela lo siguiente:

1. **Procedimiento en el Simulador:** A pesar de que los agentes (`PollinatorAgent`) se mueven, consumen recursos florales y se reproducen o mueren sobre la cuadrícula espacial de $18 \times 18$, el método `run()` de `PollinatorLandscapeModel` **no calcula** un índice de diversidad taxonómica, riqueza de especies ni entropía de Shannon sobre los agentes activos.
2. **Fórmula Determinista Implementada:** La diversidad devuelta por el simulador es calculada mediante una ecuación lineal directa evaluada sobre los parámetros del escenario:
   $$\text{abm\_diversity} = \text{clip}\left(8.0 + 0.38 \times \text{natural\_area\_pct} + 0.55 \times \text{floral\_strips\_pct} + 14.0 \times \text{landscape\_diversity} - 0.08 \times \text{pesticide\_level}, \, 4.0, \, 55.0\right)$$
3. **Combinación en el Objetivo Final:** En [`scientific_core/generator.py`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/scientific_core/generator.py#L83-L91), la variable objetivo `pollinator_diversity_index` se construye combinando:
   $$\text{div\_index\_base} = \text{clip}\left(0.85 \times \text{natural} + 1.6 \times \text{floral} - 0.35 \times \text{pesticide} + 38.0 \times \text{landscape\_diversity} + \epsilon_{\text{div}}, \, 2.0, \, 98.0\right)$$
   con $\epsilon_{\text{div}} \sim N(0, 2.0)$, y ponderándola con la salida del ABM:
   $$\mathbf{\text{pollinator\_diversity\_index} = \text{round}\left(0.30 \times \text{div\_index\_base} + 0.70 \times \text{abm\_diversity}, \, 2\right)}$$

> [!NOTE]
> **Consecuencia Analítica:** Dado que ambos términos ponderados son combinaciones lineales de las mismas variables de entrada (con ruido normal e intervalos de acotamiento), la variable objetivo resultante es esencialmente un hiperplano lineal analítico con ruido gaussiano y truncamiento en los extremos. Esto aclara por qué los modelos lineales regularizados (Ridge) alcanzaron un coeficiente de determinación de $R^2 = 0.996$ y un MAE de $0.492$ sobre este objetivo.

---

## 2. Saturación de Abundancia: Compatibilidad vs Causalidad en el Éxito de Ridge

En [`dataset_320_corrected_full.csv`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/artifacts/revision_metodologica/campana_cientifica/dataset_320_corrected_full.csv), la variable `abm_pollinator_abundance` toma el valor idéntico de **$120.0$ en las 320 filas** del conjunto de datos debido a la aplicación de `np.clip(mean_population * 1.25, 8, 120)` sobre poblaciones medias que superaron el umbral de 120.

Como consecuencia:
$$\text{pollinator\_abundance\_index} = \text{round}\left(0.35 \times \text{abundancia\_analitica} + 0.65 \times 120.0, \, 2\right) = \mathbf{0.35 \times \text{abundancia\_analitica} + 78.0}$$

### Precisiones Epistémicas sobre este Hallazgo:
- **Compatibilidad Empírica:** La degradación del término ABM a una constante aditiva fija ($+78.0$) es plenamente **compatible** con la facilidad que tuvo Ridge Regression para modelar la abundancia ($R^2 = 0.977$, $\text{MAE} = 1.232$), dado que eliminó la variabilidad estocástica y las dinámicas espaciales no lineales que el modelo ABM pretendía inyectar.
- **Ausencia de Prueba Causal Absoluta:** Esta compatibilidad **no constituye una prueba causal estricta** de que la saturación haya sido la única razón por la que Ridge superó a las redes neuronales (DNN) o ensambles de árboles (XGBoost, Random Forest).
- **No Linealidades Residuales en la Ecuación Base:** La respuesta analítica base contiene componentes no estrictamente lineales:
  1. Acotamiento no lineal inferior y superior mediante `np.clip(..., 5.0, 195.0)`.
  2. Redondeo discreto a dos decimales (`np.round(..., 2)`).
  3. Ruido pseudoaleatorio gaussiano aditivo ($\epsilon \sim N(0, 3.5)$).
  4. Interacción con `crop_yield_index`, el cual a su vez integra un acoplamiento aditivo de $+0.03 \times \text{abundancia}$.
- **Conclusión:** El benchmark demostró que Ridge aproxima eficazmente esta parametrización concreta del simulador, pero no autoriza a generalizar que los modelos lineales sean superiores a arquitecturas profundas ante simuladores ecológicos no saturados.

---

## 3. Delimitación Estricta del Diagnóstico de Poblaciones Brutas ($N=5$)

En la sección de diagnóstico se ejecutó el script [`scratch/diagnostico_abm_5_escenarios.py`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/artifacts/revision_metodologica/campana_cientifica/scratch/diagnostico_abm_5_escenarios.py) para observar el comportamiento de las poblaciones sin transformar.

1. **Valores Observados en los 5 Escenarios Reproducidos:**
   - Escenario 1 (`sample_id=1`, Seed=42): `mean_population` = **609.77** (escalado: 762.21 $\to$ clip: 120.00).
   - Escenario 2 (`sample_id=2`, Seed=43): `mean_population` = **478.70** (escalado: 598.38 $\to$ clip: 120.00).
   - Escenario 3 (`sample_id=3`, Seed=44): `mean_population` = **672.40** (escalado: 840.50 $\to$ clip: 120.00).
   - Escenario 4 (`sample_id=4`, Seed=45): `mean_population` = **616.73** (escalado: 770.92 $\to$ clip: 120.00).
   - Escenario 5 (`sample_id=5`, Seed=46): `mean_population` = **297.90** (escalado: 372.38 $\to$ clip: 120.00).
2. **Prohibición de Extrapolación:**
   - El rango bruto observado ($297.90$ a $672.40$) **aplica estricta y exclusivamente a estos 5 escenarios reproducidos**.
   - **No se extrapola este intervalo numérico a los restantes 315 escenarios del dataset**, ya que sus trayectorias individuales y poblaciones medias brutas nunca fueron registradas en el disco ni en los metadatos.
   - La única certeza empírica sobre las 315 filas restantes es que `mean_population * 1.25 >= 120.0`, lo que produjo el valor saturado $120.0$ en el CSV.
3. **Estado de Conservación del Script y sus Resultados:**
   - El script generador [`scratch/diagnostico_abm_5_escenarios.py`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/artifacts/revision_metodologica/campana_cientifica/scratch/diagnostico_abm_5_escenarios.py) se conserva físicamente en el repositorio.
   - Sus resultados de salida se registraron en la salida estándar de consola (capturada en los registros de la conversación), pero **no se guardaron en un archivo de texto independiente** en el momento de su ejecución. De conformidad con las normas de integridad, no se reconstruye dicho archivo de forma retrospectiva.

---

## 4. Instanciación Específica de `GroupKFold` en la Campaña

La partición externa de validación cruzada en esta campaña se configuró mediante la siguiente instrucción en [`scientific_core/nested_cv.py`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/scientific_core/nested_cv.py#L634):
```python
outer_splitter = GroupKFold(n_splits=n_outer_splits)
outer_splits = list(outer_splitter.split(X, y, groups=feature_groups))
```
Bajo la versión instalada de scikit-learn (1.5.2) en el contenedor `polinizadores_validacion`:
- La clase `GroupKFold` no implementa ni acepta parámetros de barajado (`shuffle=True`) ni semilla pseudoaleatoria (`random_state`).
- En consecuencia, la división de los datos en los 5 folds externos fue **determinista y dependiente del orden de los grupos de características**, sin barajado estocástico.
- Esta descripción se limita a la instanciación concreta evaluada en este entorno y evita juicios universales sobre otras versiones o variantes de la librería.

---

## 5. Desagregación Rigurosa de los Tiempos de Ejecución

Los tiempos reportados en `fold_metrics.csv` y `model_summary.csv` deben interpretarse bajo el alcance exacto de las líneas de código que los computaron:

1. **Tiempo de Reajuste Externo (`train_time_seconds`):**
   - Medido entre `t_train_start` y `t_train_end` en [`scientific_core/nested_cv.py`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/scientific_core/nested_cv.py#L829-L854).
   - **Alcance real:** Mide el tiempo de reajuste (*fit*) del modelo ganador de la CV interna sobre las 256 muestras del conjunto de entrenamiento externo **MÁS la inferencia del fold de prueba ciego completo de 64 muestras** (`preds_test = model.predict(X_test_outer)`).
   - **Exclusión:** Excluye completamente el tiempo invertido en la búsqueda de hiperparámetros (evaluación de los candidatos del grid a través de los 3 folds internos).
2. **Tiempo de Inferencia Puntual (`infer_time_seconds`):**
   - Medido entre `t_infer_start` y `t_infer_end` en [`scientific_core/nested_cv.py`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/scientific_core/nested_cv.py#L859-L866).
   - **Alcance real:** Mide una **inferencia puntual adicional sobre una sola muestra ($N=1$, `sample_in = X_test_outer[:1]`)**, incluyendo la normalización de entrada (`StandardScaler.transform`) y la desnormalización de salida (`inverse_transform`).
   - **Exclusión:** Tampoco guarda relación con el tiempo de búsqueda del bucle interno.

---

## 6. Limitaciones Metodológicas Concretas y Frontera de Prerregistro

Se rectifica la afirmación previa de "ningún riesgo metodológico" asociada a conservar la campaña actual, sustituyéndola por la declaración explícita de sus **limitaciones operacionales y epistémicas concretas**:

1. **Limitaciones Concretas de Conservar la Campaña Actual:**
   - **Pérdida de Dinámica ABM en Abundancia:** Al fijarse `abm_pollinator_abundance = 120.0`, el experimento evaluó un sustituto entrenado contra un target simplificado lineal más ruido y constante, perdiendo la oportunidad de testear la capacidad del algoritmo frente a fenómenos espaciales emergentes.
   - **Validez Externa Restringida:** Los hallazgos comparativos son válidos únicamente para este régimen de generación y no permiten predecir el comportamiento de los modelos ante datasets donde el simulador conserve varianza poblacional dinámica.
   - **Constructo de Diversidad No Taxonómico:** La diversidad modelada es una transformación matemática de entradas y no un índice biológico de estructura comunitaria.
2. **Distinción entre Protocolo Local Previo y Prerregistro Público:**
   - El documento [`PROTOCOLO_CAMPANA.md`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/artifacts/revision_metodologica/campana_cientifica/PROTOCOLO_CAMPANA.md) redactado antes de la corrida constituye un **protocolo local previo** de disciplina interna dentro del repositorio del proyecto.
   - **NO CONSTITUYE un prerregistro público formal.** Un prerregistro público formal exige el depósito previo en plataformas públicas independientes de ciencia abierta (ej. Open Science Framework - OSF, AsPredicted), con sellado de tiempo criptográfico inmutable de terceros y acceso público antes de la toma o generación de datos.
   - Esta distinción debe mantenerse explícita para no inducir a confusión sobre los estándares de ciencia abierta aplicados.

---

## 7. Región Territorial Injustificada en la Exportación CLI

Se documenta la presencia de una asignación geográfica hardcodeada en [`cli.py`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/cli.py#L396-L397):
```python
"fuente_datos": "calibrado_revision",
"region_name": "Valle del Cauca (Colombia)",
```
- Al invocarse `python cli.py export-model` para generar [`bundle_ridge_campana/bundle_ridge_078f18a6664f`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/artifacts/revision_metodologica/campana_cientifica/bundle_ridge_campana/bundle_ridge_078f18a6664f), el script inyectó de forma fija `"region_name": "Valle del Cauca (Colombia)"` en `bundle_metadata.json`.
- Esta asignación carece de justificación empírica o geográfica, dado que el modelo fue entrenado sobre un dataset estrictamente sintético sin coordenadas ni muestras agronómicas de dicho territorio. En cualquier uso posterior del bundle, esta etiqueta debe considerarse un artefacto técnico no representativo de la validez territorial del modelo.

---

## 8. Tabla Epistémica de Afirmaciones

A continuación se categorizan formalmente las afirmaciones técnicas derivadas de la campaña:

| N° | Afirmación Evaluada | Estado Epistémico | Justificación / Evidencia en Código y Datos |
| :-: | :--- | :---: | :--- |
| **1** | En las 320 filas de `dataset_320_corrected_full.csv`, `abm_pollinator_abundance` es exactamente $120.0$. | **RESPALDADA** | Verificación univariada directa sobre el CSV: media = 120.0, std = 0.0, 320/320 ocurrencias. |
| **2** | La contribución de `abm_pollinator_abundance` al objetivo final es un offset constante de $+78.0$. | **RESPALDADA** | Deducción matemática directa: $0.65 \times 120.0 = 78.0$ en la fórmula de ponderación del generador. |
| **3** | La diversidad devuelta por `PollinatorLandscapeModel.run()` no es un cálculo taxonómico emergente sobre agentes. | **RESPALDADA** | Inspección de `pollinator_abm.py`: se evalúa una fórmula lineal paramétrica sobre las 4 variables de entrada del escenario. |
| **4** | Las series y valores brutos de `mean_population` para los 320 escenarios no se conservaron en disco. | **RESPALDADA** | Inspección de columnas del CSV y metadatos JSON: solo se persistió la columna post-clip. |
| **5** | En los 5 escenarios reproducidos como diagnóstico posterior, `mean_population` osciló entre $297.90$ y $672.40$. | **RESPALDADA** | Ejecución de `scratch/diagnostico_abm_5_escenarios.py` en el contenedor con las semillas y parámetros originales. |
| **6** | La partición exterior se ejecutó mediante `GroupKFold(n_splits=5)` determinista y sin barajado estocástico. | **RESPALDADA** | Línea 634 de `nested_cv.py` e inspección de scikit-learn 1.5.2 (donde `GroupKFold` no admite `shuffle`). |
| **7** | `train_time_seconds` mide el refit externo (256 filas) más la predicción del test fold (64 filas), excluyendo el tuning interno. | **RESPALDADA** | Líneas 829-854 de `nested_cv.py`: el cronómetro abarca `fit_and_predict_...` del fold externo. |
| **8** | `infer_time_seconds` mide la inferencia y desescalado de una sola muestra puntual ($N=1$), excluyendo tuning. | **RESPALDADA** | Líneas 858-866 de `nested_cv.py`: `sample_in = X_test_outer[:1]`. |
| **9** | Los hiperparámetros de Ridge variaron por fold en la validación cruzada ($\alpha = 1.0$ en Folds 0-1, $\alpha = 0.1$ en Folds 2-4). | **RESPALDADA** | `tuning_results.csv` y `splits.json`: selecciones del bucle interno independientes por fold. |
| **10** | `cli.py export-model` estampa `"Valle del Cauca (Colombia)"` como texto fijo en los metadatos del bundle exportado. | **RESPALDADA** | Línea 397 de `cli.py` y contenido de `bundle_metadata.json`. |
| **11** | La saturación a 120 facilitó la predicción lineal de Ridge sobre la abundancia. | **ADMISIBLE CON LIMITACIONES** | Compatible con los datos al convertir el target en una relación predominantemente lineal con ruido, pero sujeta a la presencia de clipping y redondeo en la base analítica. |
| **12** | Ridge es el modelo con mejor fidelidad de aproximación para este dataset sintético concreto. | **ADMISIBLE CON LIMITACIONES** | Demostrado numéricamente en esta corrida ($1.288$ vs $1.713$ en DNN), pero condicionado a la estructura predominantemente lineal inducida en el dataset. |
| **13** | Conservar la campaña es una decisión metodológica viable documentando sus limitaciones. | **ADMISIBLE CON LIMITACIONES** | Válido como reporte transparente de desempeño del prototipo, pero con las limitaciones severas de pérdida de dinámica ABM en abundancia. |
| **14** | Las 320 poblaciones brutas de la campaña cayeron todas dentro del rango $[297.90, 672.40]$. | **NO SUSTENTADA** | Inferencia inválida: solo se muestrearon 5 de las 320 corridas; las 315 restantes permanecen no observadas. |
| **15** | La saturación de abundancia prueba causalmente que Ridge siempre será superior a otros modelos en este dominio. | **NO SUSTENTADA** | No hay prueba causal aislada; la ventaja empírica no garantiza superioridad si el simulador opera sin saturación. |
| **16** | El componente ABM aportó variabilidad poblacional emergente a la abundancia de la campaña. | **NO SUSTENTADA** | Refutada empíricamente: la varianza de la columna ABM en el dataset evaluado es cero. |
| **17** | La campaña contó con un prerregistro público formal de ciencia abierta. | **NO SUSTENTADA** | Existió un protocolo local previo en el repositorio, pero no un depósito pre-experimental en un registro público de terceros. |
| **18** | El modelo final exportado posee validez geográfica empírica en el Valle del Cauca. | **NO SUSTENTADA** | Refutada: el modelo se entrenó con un dataset sintético y la etiqueta regional es un texto fijo en el código de exportación. |

---

## 9. Hash Criptográfico de la Adenda

El contenido de esta adenda documental se conserva de forma inmutable e independiente en el archivo [`artifacts/revision_metodologica/campana_cientifica/ADENDA_DIAGNOSTICO_CAMPANA.md`](file:///c:/Users/Daniel/Downloads/gemelo-digital-polinizadores-revision/artifacts/revision_metodologica/campana_cientifica/ADENDA_DIAGNOSTICO_CAMPANA.md).

- **Ruta del Archivo:** `artifacts/revision_metodologica/campana_cientifica/ADENDA_DIAGNOSTICO_CAMPANA.md`
- **Registro de Integridad:** El hash SHA-256 se certifica de forma externa e independiente en el informe de entrega para garantizar inmutabilidad sin paradojas de autorreferencia.
