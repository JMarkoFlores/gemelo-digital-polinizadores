# Guía y Requisitos para la Reproducibilidad Científica

**Documento:** `docs/reproducibilidad.md`  
**Referencia del commit analizado:** [`0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`](https://github.com/JMarkoFlores/gemelo-digital-polinizadores/commit/0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02)  
**Evidencia principal:** [README.md:192-225](../README.md#L192-L225), [backend/requirements.txt](../backend/requirements.txt), [streamlit_app/requirements.txt](../streamlit_app/requirements.txt), [frontend/package.json](../frontend/package.json)

---

## 1. Principio de Reproducibilidad en el Gemelo Digital

Para que un experimento de gemelo digital y optimización agroecológica sea científicamente reproducible, un investigador independiente debe contar con tres elementos fundamentales:
1. **El código fuente completo** de simulación, inferencia y optimización (disponible en este repositorio).
2. **Las especificaciones exactas del entorno de ejecución** y versiones de librerías numéricas (detalladas a continuación).
3. **Los datos de entrada y artefactos de modelos entrenados** (sujeto a las restricciones de disponibilidad analizadas en esta sección).

---

## 2. Pila Tecnológica y Versiones Exactas de Software

El ecosistema científico se basa en versiones fijadas para evitar discrepancias por cambios en APIs de terceros:

| Componente | Paquete / Motor | Versión Fijada | Rol en la Reproducción Científica | Ubicación de Respaldo |
| :--- | :--- | :--- | :--- | :--- |
| **Metamodelo** | `tensorflow` | `2.17.1` | Entrenamiento de la red neuronal subrogada e inferencia en backend | [backend/requirements.txt:9](../backend/requirements.txt#L9) |
| **Optimización** | `pymoo` | `0.6.1.3` | Algoritmo genético NSGA-II multiobjetivo | [backend/requirements.txt:10](../backend/requirements.txt#L10) |
| **Geometría Espacial** | `shapely` | `2.0.6` | Cálculo de centroides, áreas y bounding boxes GeoJSON | [backend/requirements.txt:11](../backend/requirements.txt#L11) |
| **Simulación ABM** | `mesa` | `2.3.4` | Modelo espacial basado en agentes para dinámica de polinizadores | [streamlit_app/requirements.txt:7](../streamlit_app/requirements.txt#L7) |
| **ML Clásico** | `scikit-learn` | `1.5.2` | Normalización, K-Fold CV y modelos baselines (RF, Ridge) | [streamlit_app/requirements.txt:5](../streamlit_app/requirements.txt#L5) |
| **Gradient Boosting** | `xgboost` | `2.1.1` | Regresión de ensamble multiobjetivo | [streamlit_app/requirements.txt:8](../streamlit_app/requirements.txt#L8) |
| **Inferencia Estadística** | `scipy` | `1.14.1` | Shapiro-Wilk, Wilcoxon, T-Student y Test de Friedman | [streamlit_app/requirements.txt:12](../streamlit_app/requirements.txt#L12) |
| **Post-Hoc Estadístico** | `scikit-posthocs` | `0.17.0` | Matriz de p-valores pareados del Test de Nemenyi | [streamlit_app/requirements.txt:14](../streamlit_app/requirements.txt#L14) |
| **Motor de Base de Datos** | `PostgreSQL` | `16-alpine` | Motor de base de datos relacional | [docker-compose.yml:3](../docker-compose.yml#L3) |
| **Interfaz 3D** | `three` / `@react-three/fiber` | `0.169.0` / `8.17.10` | Renderizado WebGL de la maqueta topográfica en 3D | [frontend/package.json:25-27](../frontend/package.json#L25-L27) |

---

## 3. Estado de los Materiales de Auditoría del Artículo Científico

El [README.md:208-225](../README.md#L208-L225) documenta un conjunto de materiales utilizados para auditar y generar los resultados reportados en la publicación científica del proyecto. La inspección del repositorio arroja el siguiente estado de disponibilidad:

| Material de Auditoría | Estado en el Repositorio Git | Justificación Documentada en README | Alternativa de Reproducción |
| :--- | :--- | :--- | :--- |
| **Modelo Histórico `surrogate_20261008_221709`** | ❌ **No disponible en Git** | Preservado localmente por su tamaño y naturaleza binaria para posterior depósito en repositorio abierto (README L208-212). | Se puede generar un modelo sustituto compatible entrenando en Streamlit y exportándolo a `/modelos_ia/modelo_optimizado.h5`. |
| **Carpeta `respaldo_surrogate_...`** | ❌ **No disponible en Git** | No subida al control de versiones por política de exclusión de binarios pesados. | Reconstrucción mediante los scripts del laboratorio Streamlit. |
| **Script `predict_baselines.py`** | ❌ **No disponible en Git** | Formaba parte de la carpeta de auditoría externa. | La predicción de línea base se ejecuta de forma nativa a través de `predict_targets([baseline_features])` en [optimization.py:139-148](../backend/app/services/optimization.py#L139-L148). |
| **Script `prepare_files.py`** | ❌ **No disponible en Git** | Script auxiliar de consumo de API. | Se puede consumir directamente el endpoint `POST /api/simular` con cURL, Postman o scripts en Python con `requests`. |
| **Script `generar_documentacion.py`** | ❌ **No disponible en Git** | Script analítico del frente de Pareto. | La visualización de la dispersión de Pareto se genera dinámicamente en el frontend ([ResultsDashboard.jsx](../frontend/src/components/ResultsDashboard.jsx)). |
| **Datos crudos de MAE por fold** | ❌ **No conservados** | Se declaró en README L224 que los errores desagregados por fold no se conservaron en la base final del entrenamiento. | El módulo [robust_tests.py](../streamlit_app/robust_tests.py) recalcula en vivo la matriz de errores por fold si se ejecuta una nueva corrida de entrenamiento. |

---

## 4. Semillas Estocásticas y Control del Azar

Para mitigar la variabilidad estocástica y asegurar que corridas sucesivas generen los mismos frentes de Pareto y predicciones, el código impone semillas fijas:

1. **Generación de Datasets:** `random_state = 42` ([data_pipeline.py:44](../streamlit_app/data_pipeline.py#L44)).
2. **Simulador ABM:** `seed = scenario.seed = 42 + index` ([pollinator_abm.py:167](../streamlit_app/pollinator_abm.py#L167)).
3. **Entrenamiento de Red Neuronal:** `tf.keras.utils.set_random_seed(random_state)` ([training.py:97](../streamlit_app/training.py#L97)).
4. **Particiones de Validación Cruzada:** `KFold(n_splits=5, shuffle=True, random_state=42)` ([advanced_training.py:116](../streamlit_app/advanced_training.py#L116)).
5. **Algoritmo Genético NSGA-II:** `seed = 42` ([optimization.py:244](../backend/app/services/optimization.py#L244)).

---

## 5. Protocolo de Reproducción Autónoma en Entorno Limpio

Dado que el archivo binario del modelo original no está empaquetado en Git, el procedimiento para reproducir el ciclo analítico completo es:

```text
[1. Ingesta de Datos]
   │  Ejecutar Streamlit (http://localhost:8501)
   │  -> Pestaña 1: Seleccionar región (ej. Valle del Cauca) o Generar Sintético (320 muestras)
   │  -> Marcar opción "Enriquecer con ABM (Mesa)"
   ▼
[2. Modelado y Validación]
   │  -> Pestaña 3: Iniciar entrenamiento con K-Fold CV (k=5)
   │  -> Pestaña 4: Revisar resultados de pruebas Friedman y Nemenyi
   ▼
[3. Exportación del Bundle]
   │  -> Pestaña 5: Presionar "Exportar modelo a /modelos_ia/"
   │  -> Se generan: /modelos_ia/modelo_optimizado.h5 y metadata.json
   ▼
[4. Detección Automática en Backend]
   │  -> El hilo watcher de FastAPI detecta el nuevo mtime en <= 5s
   │  -> /health reporta model_ready: true
   ▼
[5. Inferencia y Optimización NSGA-II]
   │  -> Ingresar a la consola React (http://localhost:5173)
   │  -> Dibujar polígono en el área calibrada y ejecutar simulación
```
*(Nota: Este protocolo describe el flujo previsto según la estructura del código, pero no fue ejecutado dinámicamente en esta fase documental).*
