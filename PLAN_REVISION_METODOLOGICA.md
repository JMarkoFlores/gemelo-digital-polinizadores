# Plan de implementación y revisión metodológica del prototipo de polinizadores

Versión del plan: 1.0. Fecha: 28 de octubre de 2026.

## 1. Instrucción principal para el agente

Lee este documento completo antes de editar. Implementa las correcciones necesarias en una sesión de trabajo, avanzando por módulos, verificando y dejando evidencia. No te limites a proponer otro plan: realiza los cambios autorizados y las verificaciones técnicas pequeñas. Resuelve decisiones rutinarias con el protocolo de este documento. Si detectas una contradicción científica que no puede resolverse con el código o los materiales, registra la decisión pendiente y continúa con los módulos independientes; no inventes una solución ni detengas todo el trabajo por un bloqueo parcial.

El objetivo inmediato es **completar la implementación verificable y dejar preparada la ejecución científica corregida**. Todavía NO debes navegar por la aplicación, iniciar una campaña de pruebas manuales, publicar cambios, enviar el artículo ni ejecutar automáticamente la campaña definitiva de entrenamiento. Las pruebas de interfaz y los experimentos definitivos se autorizarán después de auditar esta implementación. Sí debes ejecutar pruebas unitarias e integraciones pequeñas y aisladas cuando el entorno lo permita.

No confundas cuatro estados: implementado, verificado técnicamente, ejecutado como experimento y validado científicamente. Ninguno implica automáticamente el siguiente.

## 2. Proyecto, responsables y alcance

- Repositorio: https://github.com/JMarkoFlores/gemelo-digital-polinizadores
- Espacio de trabajo autorizado: `C:\Users\Daniel\Downloads\gemelo-digital-polinizadores-revision`.
- Rama creada por el usuario: `revision-metodologica`.
- Commit de partida declarado y consultado para preparar este plan: `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab`.
- Copia histórica que NO debe modificarse: `C:\Users\Daniel\Downloads\gemelo-digital-polinizadores`.
- Responsable actual del trabajo: Daniel. Su compañero no ejecutará la implementación.
- Contexto: artículo de Ingeniería de Software II sobre un prototipo de gemelo digital agroecológico, con simulación multiagente Mesa, cinco modelos predictivos y optimización NSGA-II.
- Destino editorial: revista Ciencia y Tecnología Agropecuaria, AGROSAVIA. La publicación requiere resultados y métodos defendibles; el software no debe producir textos que conviertan índices simulados en beneficios agronómicos observados.

Comprueba la ruta, la rama y el estado de Git. Si hay trabajo posterior al commit declarado, NO hagas reset, checkout destructivo ni pull para volver al pasado. Registra la diferencia y trabaja sobre el estado autorizado conservando los cambios locales. La versión local que inspecciones tiene prioridad para determinar qué ya está corregido; este plan no ordena reintroducir comportamientos antiguos.

### Fuera de alcance

- No editar archivos Word ni el Google Docs del artículo.
- No implementar una sincronización real con un agroecosistema, IoT, trabajo de campo, corredores espaciales ni nuevas arquitecturas de aprendizaje.
- No agregar Sobol o una cuantificación de incertidumbre no justificada para aparentar completitud.
- No rediseñar autenticación, administración, informes generales o visualización, salvo cambios necesarios para compatibilidad y coherencia de resultados.
- No ejecutar pruebas manuales en navegador ni generar nuevos videos en esta fase.
- No desplegar, hacer push, merge ni publicar datos externamente.

## 3. Materiales históricos y límites de lo conocido

El usuario dispone de `Evidencias Software Prueba Resultados.zip`. Puede estar extraído en una carpeta externa, por ejemplo `C:\Users\Daniel\Downloads\evidencias-polinizadores-historicas`. Esta ruta es sugerida, no se da por existente. Busca solo en el espacio de trabajo o en la ubicación que el usuario haya indicado; no recorras todo su disco.

Dentro del ZIP, prioriza `paquete_final_v4` como referencia documental. Contiene:

- `archivos_originales_historicos/modelo_optimizado.h5`.
- `archivos_originales_historicos/modelo_optimizado_metadata.json`.
- `archivos_originales_historicos/reporte_modelos.xlsx`.
- `documentacion_final/dataset_entrenamiento.csv`.
- `documentacion_final/manifest_ejecucion.json`.
- `documentacion_final/README_resultados.txt`.
- `documentacion_final/comparacion_linea_base.csv`.
- `documentacion_final/verificacion_ejecucion.json`.
- `documentacion_final/cambios_optimization.patch`.
- `resultados_ejecucion_corregida/solicitud_actual_corregida.json`.
- `resultados_ejecucion_corregida/resultado_actual_corregido.json`.
- `resultados_ejecucion_corregida/soluciones_exportadas.csv`.
- Scripts de auditoría e índice SHA-256.

Hay versiones v3, archivos de recuperación y dos videos. No mezcles sus cifras con v4. La corrección v4 unificó la diversidad de la línea base: 0,721 frente a 0,587 en la regla anterior. No fue un reentrenamiento. El modelo histórico es `surrogate_20261008_221709`. Las métricas históricas y las 64 alternativas NO son objetivos numéricos para la nueva implementación.

El conjunto histórico tiene 320 filas, ocho entradas y tres salidas modeladas. Se emplearon referencias NASA POWER y GBIF para Valle del Cauca y periodo climático 2019–2023, pero las filas no son observaciones independientes de campo. El enriquecimiento ABM histórico se aplicó a las primeras 120 muestras. El intervalo térmico observado fue 14,31–18,69 °C; la optimización histórica usó 23,55 °C. No presentes esas referencias como validación regional del modelo.

Si no están los materiales históricos, completa la implementación con fixtures y datos de prueba nuevos, identificados como tales. Registra que la comparación histórica queda pendiente. No descargues archivos por adivinación, no reconstruyas métricas faltantes ni cargues automáticamente el modelo histórico en el volumen activo.

El informe del docente es contexto de revisión, no una especificación infalible. Sus observaciones sobre entrenamiento y extrapolación tienen respaldo, pero algunas sobre referencias y páginas faltantes no coincidieron con el Word revisado. No intentes corregir el software para satisfacer observaciones editoriales ajenas a su funcionamiento.

## 4. Reglas de preservación y trabajo autónomo

1. No tocar la carpeta histórica, sus volúmenes, modelos ni archivos. Leer evidencias no autoriza modificarlas.
2. No ejecutar `git reset --hard`, `git clean -fd`, `docker system prune`, eliminación de volúmenes o comandos equivalentes.
3. No cambiar globalmente Python, CUDA, Docker ni paquetes del sistema. Utilizar entorno virtual o contenedores aislados.
4. No guardar secretos, claves API, contraseñas o contenido de `.env` en informes, repositorio ni archivos de resultados. Registrar nombres de variables necesarios y valores científicos no sensibles.
5. No ejecutar en bloque los scripts existentes `test_*.py`: algunos entrenan, consultan APIs y sobrescriben `/modelos_ia`. Inspeccionarlos primero y separar integración destructiva de pruebas aisladas.
6. Mantener la arquitectura actual y realizar cambios concentrados en el flujo científico y sus consumidores.
7. Crear artefactos por ejecución; una ejecución incompleta sigue siendo incompleta. Jamás rellenar faltantes con cero, interpolaciones, resultados históricos o textos inventados.
8. No ajustar semillas, criterios, dominio o dataset para producir un ganador o un aumento de polinizadores deseado.
9. No hacer commits automáticos ni push. Dejar diff revisable y comandos para que el usuario decida su integración.
10. Si una dependencia o acción requiere permisos del entorno, respetarlos. No convertir una prueba bloqueada en una prueba aprobada.

## 5. Continuidad entre modelos y sesiones

Crea desde el principio estos documentos dentro de `docs/revision_metodologica/`:

- `ESTADO_IMPLEMENTACION.md`: punto de reanudación principal.
- `DECISIONES.md`: decisiones metodológicas y técnicas, su razón y sus consecuencias.
- `AUDITORIA_INICIAL.md`: hallazgos reales por archivo y función.
- `INFORME_IMPLEMENTACION.md`: entrega final para auditoría.
- `METODOLOGIA_IMPLEMENTADA.md`: descripción factual del procedimiento final y de qué se ejecutó.

Actualiza `ESTADO_IMPLEMENTACION.md` al terminar cada módulo y antes de una pausa previsible. Incluye:

```text
Ruta y rama verificadas:
Commit de partida / HEAD actual / estado dirty:
Módulo actual:
Estado por módulo: pendiente | en curso | implementado | verificado | bloqueado
Archivos cambiados:
Decisiones ya fijadas y referencia a DECISIONES.md:
Pruebas ejecutadas y ubicación de logs:
Pruebas no ejecutadas y motivo:
Procesos activos: PID o contenedor, comando, run_id, log, forma de consultar estado:
Último resultado comprobado:
Próxima acción concreta:
Bloqueos y alcance que sigue siendo posible:
```

Al reanudar, leer este plan, estado, decisiones, informe y `git diff`; comprobar procesos activos antes de lanzar otros. No reiniciar el proyecto, no borrar cambios de otro modelo y no volver a ejecutar entrenamientos sin comprobar si ya hay una ejecución válida o activa. La reanudación no depende de memoria interna del modelo ni de su razonamiento privado.

## 6. Auditoría del commit y mapa de módulos

Inspecciona estas rutas reales y sus consumidores. Puedes crear módulos compartidos pequeños si evitan duplicación; documenta su ubicación e importación en los distintos contenedores.

| Área | Archivos a revisar | Trabajo principal |
|---|---|---|
| Datos | `streamlit_app/data_pipeline.py` | Procedencia, coherencia de entradas/salidas, snapshots, validaciones |
| Simulación | `streamlit_app/pollinator_abm.py` | Semillas, reglas y política explícita de enriquecimiento |
| Evaluación | `streamlit_app/advanced_training.py` | CV externa, escalado y predicciones externas |
| Ajuste | `streamlit_app/hyperparameter_tuning.py` | Selección interna sin contaminación |
| Entrenamiento/exportación | `streamlit_app/training.py` | Ajuste final, artefactos y transformadores |
| Coordinación UI | `streamlit_app/app.py` | Configuración, estados y compatibilidad |
| Reportes | `streamlit_app/reports.py` | Exportación estructurada y métricas recalculables |
| Estadística | `streamlit_app/robust_tests.py` | Procedencia, límites inferenciales y valores ausentes |
| Carga | `backend/app/services/model_store.py` | Bundle consistente, tipos de modelo y dominio |
| Optimización | `backend/app/services/optimization.py` | Escenarios, restricciones, precisión, caché y selección |
| API | `backend/app/schemas.py`, `backend/app/main.py` | Contratos, errores y campos de trazabilidad |
| Narrativa | servicios de recomendaciones y chat | Separar texto generado y números calculados |
| Consumidores | componentes y páginas de `frontend/src/` | Compatibilidad y etiquetas precisas |
| Entorno | ambos Compose, Dockerfiles y requirements | Aislamiento, reproducibilidad y ejecución CPU |
| Pruebas | scripts existentes, `scratch/`, nuevas pruebas | Evitar falsas pruebas y sobrescrituras |

Hallazgos constatados en el commit de partida; vuelve a verificarlos localmente:

- `advanced_training.py` ajusta `StandardScaler` de salidas sobre todo `y` antes del KFold.
- El ajuste de hiperparámetros precede a la CV externa; no hay selección anidada.
- Las redes usan el fold externo como `validation_data` de EarlyStopping.
- `best_keras_model` se escoge por el mejor R² de una partición externa, independiente del ganador global.
- Scripts de trazabilidad pueden asociar el MAE del ganador global a una red distinta y usar RMSE/R² iguales a cero como marcadores.
- El optimizador tiene clima heurístico, límites estáticos, redondeo antes de predecir candidatos y caché basada solo en la solicitud.
- La fórmula de diversidad ya está unificada en línea base y candidatos: conservar esta corrección, no duplicarla.
- El control de proximidad regional no controla el dominio de entradas.
- `docker-compose.yml` declara nombres globales como `gemelos_db`, `gemelos_backend`, `gemelos_frontend`, `gemelos_streamlit` y `gemelos_langflow`. Otro directorio de clonación no los aísla.

En `AUDITORIA_INICIAL.md`, clasifica cada punto como confirmado, ya corregido, distinto de lo esperado o no verificable. Vincula cambios con hallazgos; no sustituyas la inspección por este resumen.

## 7. Aislamiento de entorno y recursos

### 7.1 Docker

No arranques el stack completo durante esta fase. Sí valida su configuración y prepara un arranque aislado para después.

- Elimina o parametriza en la copia nueva los `container_name` fijos. Preferir nombres generados por Compose con un proyecto propio, por ejemplo `polinizadores_revision`.
- Verifica resolución de volúmenes con `docker compose ... config`; los volúmenes no deben usar nombres externos o absolutos que apunten al histórico.
- Mantén volúmenes exclusivos de revisión para PostgreSQL, modelos y Langflow; revisa también Compose de producción si puede causar reutilización accidental.
- Parametriza el puerto PostgreSQL además de los otros. Como configuración de revisión propuesta: DB 5433, backend 8001, frontend 5174, Streamlit 8502 y Langflow 7861. Comprueba disponibilidad; los puertos son propuestas, no una obligación si están ocupados.
- Mantén coherentes API URL, CORS y URLs internas entre servicios. Los puertos del host no sustituyen los puertos internos de red Docker.
- Prepara un archivo de ejemplo de variables de revisión sin secretos.
- Separa Langflow como servicio opcional o perfil si es compatible con el flujo actual; la corrección numérica no puede depender de un servicio de texto remoto.
- Registra el comando exacto para levantar y detener SOLO el proyecto de revisión. No borres volúmenes al detener.

### 7.2 Cómputo

- Diseña para CPU y bajo paralelismo; GPU opcional, nunca requisito asumido.
- Detecta y registra Python, sistema operativo, RAM disponible, CPU y versiones. No prometas un tiempo de ejecución sin medirlo.
- Limita hilos de TensorFlow/BLAS/XGBoost y evita paralelismo anidado; comienza con un trabajo por vez.
- Conserva lockfiles existentes, evita actualizaciones globales y justifica nuevas dependencias.
- Revisa compatibilidad de Python/TensorFlow en Windows nativo frente al contenedor Linux; no instales CUDA para intentar resolver una incompatibilidad de versiones.
- Las pruebas unitarias deben ser pequeñas. Las integraciones con TensorFlow se omiten con motivo explícito si no está disponible; implementa pruebas sin esa dependencia cuando sea posible.

## 8. Contratos científicos y datos

### 8.1 Entradas y salidas

Conservar el contrato semántico y su orden:

```text
Entradas:
crop_area_pct
natural_area_pct
floral_strips_pct
pesticide_level
soil_management_score
temperature_c
precipitation_mm
landscape_diversity

Salidas:
crop_yield_index
pollinator_abundance_index
pollinator_diversity_index
```

Los índices no son unidades de rendimiento de campo, conteos observados de individuos ni medidas de diversidad taxonómica validadas. El nivel de plaguicidas es un índice 0–100, no necesariamente un porcentaje. Preservar coeficientes y reglas biofísicas existentes salvo que una incoherencia confirmada requiera cambio, en cuyo caso registrar antes/después y consecuencias.

### 8.2 Auditoría y versionado

Implementa un comando de auditoría que genere tipos, ausentes, infinitos, duplicados, rangos, sumas de coberturas, conteo de violaciones, identificadores de filas y procedencia. Asigna IDs estables y guarda hash SHA-256 del archivo original. Las filas duplicadas que se conserven deben mantenerse en un mismo grupo para evitar copias exactas en train y test; documentar la política. No forzar una conclusión espacial o temporal con un KFold aleatorio.

Separar por columna: dato público consultado, variable muestreada, característica derivada y salida parametrizada o simulada. Guardar snapshots de las respuestas públicas, parámetros de consulta, fecha y fallbacks usados. No consultar APIs en vivo para reproducir un experimento sobre un snapshot ya fijado. Nunca presentar un fallback como consulta pública exitosa.

### 8.3 Política corregida propuesta

Prepara dos rutas explícitas:

1. `historical_audit`: lectura y descripción del CSV preservado; no lo normaliza ni lo sobrescribe. No se declara automáticamente apto para el experimento corregido.
2. `corrected`: dataset nuevo, validado y versionado. Si existen coberturas incoherentes, no renormalices solo las entradas conservando etiquetas antiguas. Implementa generación coherente de entradas y salidas con las fórmulas documentadas, o exclusión justificada con registro de filas, según lo que permita la procedencia disponible. El modo definitivo debe rechazar incoherencias, no ocultarlas.

Para el generador corregido, las coberturas se entienden como categorías excluyentes dentro del paisaje: exigir valores no negativos y suma ≤100, explicando la superficie restante cuando sea menor de 100. No exigir suma exactamente 100 si el contrato admite superficie restante. Aplicar las mismas reglas en ABM, baseline, candidatos y exportación. Mantener límites de cultivo sobre la cobertura efectiva, no solo sobre una variable anterior a reparación.

La relación de `landscape_diversity` utilizada al optimizar difiere de su muestreo independiente histórico. Preparar una función compartida/versionada que permita una política consistente en el dataset corregido, la línea base y los candidatos. Cualquier cambio en esa relación cambia el problema modelado y debe registrarse como nuevo protocolo, no como reproducción idéntica del histórico.

No combinar silenciosamente 120 filas enriquecidas y 200 no enriquecidas con una sola descripción de etiquetas. Implementar una política uniforme y configurable para un dataset nuevo: enriquecimiento completo o sin enriquecimiento. Para el protocolo futuro orientado al ABM, proponer enriquecimiento completo, conservando el modo histórico solo para auditoría. No ejecutar ahora las 320 simulaciones; verificar el camino con pocas filas. Registrar índice de fila, semilla y método de etiqueta. Si solo es posible reproducir el enriquecimiento parcial, identificarlo y conservar la heterogeneidad como limitación explícita, sin llamarlo uniforme.

Un CSV corregido solo se vuelve dataset definitivo después de una decisión documentada y ejecución posterior. Implementar el camino no autoriza fabricar nuevos datos ni reutilizar respuestas de campo inexistentes.

## 9. Evaluación predictiva sin contaminación

### 9.1 Configuración previa a resultados

Preparar `configs/revision_metodologica.json` o YAML equivalente. Elegir una sola fuente de configuración, validada y consumida por CLI y Streamlit.

Parámetros propuestos para la futura ejecución definitiva:

| Parámetro | Valor o política |
|---|---|
| Modelos | Ridge, Random Forest, XGBoost, DNN, Autoencoder+MLP |
| CV externa | 5 folds, mezcla con semilla 42; grupos si existen duplicados o dependencia conocida |
| CV interna | 3 folds dentro del entrenamiento externo |
| Métrica principal | media aritmética del MAE en escala original entre las tres salidas |
| Selección | menor MAE macro; desempate por menor RMSE macro y mayor R² macro |
| Igualdad de criterio | mismos folds externos, salidas y criterio para todos los modelos |
| Presupuesto de búsqueda | pequeño y fijado antes de resultados; hasta 4 candidatos por familia como inicio CPU |
| Redes | máximo inicial 30 épocas, batch 24 y patience 5, todos configurables y registrados |
| Paralelismo | 1 por defecto |
| Búsquedas repetidas | no cambiar espacios tras observar el ganador |

Documentar que promediar MAE en escala original da igual peso numérico a los índices, pero depende de sus escalas. Mantener las métricas por salida; no presentar el promedio como una ponderación agronómica validada. No usar métricas secundarias para cambiar retrospectivamente el ganador. No usar una suma arbitraria de R², MAE y RMSE.

La configuración smoke debe ser distinta: pocos registros, dos folds si el tamaño lo permite, un candidato, pocas épocas y simulación mínima. Etiquetarla `test_only`; no sustituye el experimento con cinco folds.

### 9.2 Algoritmo requerido

Para cada fold externo, guardar sus IDs de entrenamiento y evaluación. El fold externo de evaluación no debe intervenir en ninguna decisión de entrenamiento.

Para cada candidato y split interno:

1. Crear modelos y transformadores nuevos.
2. Si se requiere EarlyStopping, separar dentro del entrenamiento interno una subpartición de monitorización. La validación interna que puntúa el candidato NO se usa para parada temprana.
3. Ajustar normalización de entradas y escalado de salidas únicamente con las filas que efectivamente entrenan pesos/parámetros, sin incluir las de monitorización o puntuación.
4. Entrenar, puntuar el candidato sobre validación interna una vez y devolver predicciones a escala original.
5. Guardar puntuación, hiperparámetros, épocas y semillas. No reutilizar un modelo entrenado de otra partición.

Tras elegir los hiperparámetros usando solo los splits internos, reajustar sobre el entrenamiento externo. Para redes, fijar las épocas con una regla predefinida basada en épocas internas, por ejemplo mediana redondeada y acotada; ajustar transformadores con todo el entrenamiento externo y entrenar ese número de épocas sin consultar el test externo. Si se usa otra política válida, debe quedar explícita y no tocar el test.

Predecir una vez el fold externo, invertir transformaciones y calcular métricas por salida. Cada fila tiene una predicción externa por modelo en la CV no repetida. Inicializar arrays con NaN y verificar cobertura; no dejar ceros que oculten filas no evaluadas. La clase elegida no se exporta directamente desde el fold con mejor puntuación.

No llamar a `tune_all_hyperparameters` sobre todo el dataset antes de la CV. Auditar también el tuning de modelos tradicionales, normalización, autoencoder y parada temprana de XGBoost si existe.

### 9.3 Semántica de Autoencoder+MLP

Inspeccionar si el código realmente entrena un autoencoder con reconstrucción o si solo tiene un cuello de botella supervisado. No agregar un autoencoder completo por apariencia. Si no hay objetivo de reconstrucción, documentarlo y etiquetarlo de forma precisa en reportes y mensajes, conservando un identificador compatible si hace falta. La futura redacción debe reflejar lo implementado.

### 9.4 Casos especiales

- Conservar métricas por salida y por fold; distinguir media de métricas por fold de métricas calculadas sobre OOF reunido.
- R² no definido o métricas inválidas se registran como ausentes con razón, no como 0 ni 1.
- Fallos de modelos no se eliminan silenciosamente para ordenar la tabla.
- Para inferir superioridad del ganador elegido entre familias, reconocer el sesgo de selección entre familias: la CV externa por familia no convierte su mejor promedio en evaluación independiente del ganador final. Si se evalúa un procedimiento de selección completo, la familia también debe seleccionarse dentro de cada entrenamiento externo. No afirmar que esta extensión se ejecutó si solo se compararon familias.

## 10. Persistencia y esquema de resultados

Separar la lógica científica de widgets Streamlit. La CLI debe ejecutar el mismo núcleo, sin emular una sesión UI. Los widgets pueden ser adaptadores de progreso opcionales.

Estructura sugerida, adaptable sin perder contenido:

```text
artifacts/revision_metodologica/<run_id>/
  manifest.json
  config_effective.json
  environment.json
  data_audit.json
  dataset.csv
  row_provenance.csv
  splits.json
  tuning_results.csv
  fold_metrics.csv
  oof_predictions.csv
  model_summary.csv
  statistics.json
  model_bundle/
  optimization/
    request.json
    baseline.json
    candidates.csv
    pareto_verified.csv
    selected_solution.json
    validation.json
  logs/
  figures/
  SHA256SUMS.txt
```

No crear archivos científicos como si existieran antes de ejecutarlos: usar estado pendiente y rutas previstas en el manifiesto. El estado de una ejecución puede ser `started`, `partial`, `failed`, `completed`; los datos smoke llevan además `test_only=true`. Escribir resultados incrementalmente con reemplazo atómico cuando sea posible. No sobrescribir un `run_id` completado. Reanudar únicamente si configuración, datos y código son compatibles; si cambian, crear otro ID.

Esquema mínimo de `fold_metrics.csv`: `run_id, dataset_hash, model_id, outer_fold, target, n_train, n_test, mae, rmse, r2, seed, status`.

Esquema mínimo de `oof_predictions.csv`: `run_id, model_id, outer_fold, sample_id, target, y_true, y_pred, residual`. No confundir target observado en el CSV con observación real de campo.

Guardar hardware, librerías, versión de Python, sistema, tiempos realmente medidos, HEAD, estado dirty y hash o copia del diff de código relevante sin secretos. Un commit base con cambios locales no identifica por sí solo el código ejecutado.

El índice de hashes no se incluye a sí mismo. Regenerarlo al cerrar una ejecución y no modificar después los archivos declarados sin cambiar versión. Proporcionar `recompute_metrics` que reconstruya estadísticas descriptivas desde OOF y verifique coincidencia con la tabla guardada, sin reentrenar.

No persistir rutas privadas irrelevantes ni secretos del entorno. Conservar suficiente precisión numérica en los archivos; redondear solo al presentar.

## 11. Estadística defendible

La implementación mínima debe priorizar MAE, RMSE y R² por salida, métricas agregadas definidas, dispersión descriptiva por folds y trazabilidad de predicciones.

- No convertir cinco folds con entrenamiento solapado en cinco experimentos independientes.
- No llamar intervalo de confianza a la desviación entre folds.
- No hacer bootstrap ingenuo sobre cinco métricas correlacionadas ni sobre predicciones OOF como si desapareciera la dependencia del entrenamiento. Una extensión inferencial requiere definir unidad de muestreo y supuestos.
- Guardar para Friedman/Nemenyi los datos de entrada exactos, rangos, opciones, estadísticos, p-valores y software; distinguir pruebas exploratorias de evidencia confirmatoria.
- Si no se justifican sus supuestos, permitir omitir la inferencia por defecto y exportar `not_performed` con razón metodológica. Eso es preferible a un p-valor fabricado o interpretado en exceso.
- No obligar p<0,05, superioridad neuronal, significancia de todos los pares ni equivalencia por ausencia de significancia.
- No reconstruir los errores históricos faltantes a partir de medias.
- Actualizar el texto automático de reportes para respetar el estado real del análisis.

Si se agregan tamaños de efecto descriptivos, definir su cálculo y alcance, sin llamarlos efectos agronómicos. No implementar más pruebas de las necesarias para la pregunta del estudio.

## 12. Selección y entrenamiento final del modelo

Implementar una política explícita de selección basada en el criterio fijado. La opción por defecto propuesta es desplegar la familia con menor MAE macro externo, con el alcance descriptivo y las limitaciones del apartado 9.4. No imponer una red ganadora. Mantener también la comparación de la mejor red como análisis secundario claramente rotulado, sin sustituir al ganador global.

Para el modelo final:

1. Con la familia seleccionada, elegir hiperparámetros mediante CV interna sobre los datos de desarrollo disponibles, sin reusar el mejor fold externo como artefacto final.
2. Fijar épocas para redes por regla interna documentada.
3. Ajustar transformadores y modelo final según ese protocolo.
4. Exportar un bundle íntegro. El modelo final entrenado con todos los datos no tiene una métrica de test independiente adicional por el solo hecho de exportarse.

Si el ganador es Ridge, Random Forest o XGBoost, soportar su carga/predicción en backend mediante una interfaz pequeña y común. Usar formatos apropiados y compatibles, documentando que artefactos pickle/joblib solo se cargan desde el directorio local controlado, no desde cargas arbitrarias de usuarios. Evitar una infraestructura de plugins innecesaria.

Contrato del predictor: recibir una matriz de ocho características en orden declarado y devolver tres salidas en escala original. No invertir el escalado dos veces. Para Keras, registrar si la normalización está embebida; para otros modelos, conservar el pipeline completo o transformadores externos vinculados.

Metadatos mínimos:

```text
schema_version, bundle_id, model_type, model_version,
feature_names, target_names, preprocessing_contract,
dataset_hash, dataset_version, run_id, training_protocol,
hyperparameters, final_training_seed, epochs_if_applicable,
evaluation_reference, metrics_scope,
feature_bounds, joint_domain_policy, derivation_rules_version,
geographic_reference, data_provenance,
library_versions, code_commit, code_dirty_hash, artifact_hashes
```

No usar métricas del ganador global como si pertenecieran a una red distinta. No guardar cero para métricas no calculadas. Corregir este comportamiento en scripts de trazabilidad y en `app.py`.

La recarga debe ser coherente: exportar a un directorio nuevo y activar mediante manifiesto/puntero atómico o equivalente. Verificar artefactos y esquema antes de cambiar el modelo activo; no leer un `.h5` nuevo con metadatos antiguos. Mantener el bundle anterior si la nueva carga falla y reportar el error. Un cálculo en curso debe usar una sola instantánea de modelo y metadatos, incluso si el watcher detecta otra versión.

Preparar prueba de igualdad de predicciones antes/después de exportar con tolerancia justificada por tipo de modelo. El soporte del modelo histórico puede ser de compatibilidad explícita; no se le atribuyen metadatos de dominio que no trae.

## 13. Escenarios, dominio y optimización

### 13.1 Origen del escenario

Separar el contexto geográfico del escenario ambiental. El clima histórico se deriva de heurísticas de latitud/longitud: no etiquetarlo como clima observado NASA. Un escenario corregido debe traer temperatura y precipitación explícitas o derivarse de un snapshot y regla documentados. Guardar procedencia y unidades.

No sustituir silenciosamente 23,55 °C por 18,69 °C ni por la media entrenada para pasar validaciones: sería otro escenario. Si se propone un escenario de referencia basado en estadísticas del dataset, etiquetarlo como referencia modelada, no como medición del polígono. Preparar su construcción; no afirmar que se ejecutó.

Conservar perturbaciones warm/dry/extreme si siguen siendo útiles, pero admitir que algunas queden fuera de dominio. Rechazar códigos desconocidos en vez de tratarlos silenciosamente como current.

Auditar `parse_geometry`: la aproximación por bounding box y el mínimo histórico de 1 km² no son un área medida exacta. No presentar ese mínimo como superficie real. Separar área aproximada mostrada del parámetro heurístico de presión si se conserva; registrar método. Si corriges el cálculo geométrico, documentar el cambio sin convertirlo en una tarea GIS ajena al alcance.

### 13.2 Admisibilidad

El modo científico principal debe bloquear entradas sin metadatos suficientes o fuera de las condiciones admitidas. Distinguir:

- proximidad geográfica a la referencia;
- cumplimiento de rangos univariados;
- coherencia de coberturas y variables derivadas;
- soporte conjunto observado, que no queda demostrado solo con mínimos y máximos.

Guardar diagnósticos por variable y reglas aplicadas. Intersectar límites de decisión con restricciones físicas y límites del dataset correspondiente. Si la intersección es vacía, devolver un error informativo; no relajar reglas automáticamente. La diversidad derivada también debe cumplir dominio. Mantener cultivo efectivo dentro de los límites aunque una reparación de suma lo reduzca.

Para el soporte conjunto, implementar al menos una advertencia explícita y, si es viable sin sobreingeniería, un diagnóstico de distancia a vecinos en espacio normalizado con umbral calibrado solo sobre desarrollo y documentado. No llamarlo prueba de seguridad ni intervalo de incertidumbre. No introducir un umbral arbitrario y después afirmar validez científica. La validación ecológica seguirá pendiente.

Un modo exploratorio fuera de dominio es opcional; no es necesario construirlo ahora. Si ya existe y se conserva, debe ser explícito, no predeterminado, rotulado en toda la salida y separado del experimento principal. Nunca ocultar extrapolaciones.

### 13.3 NSGA-II y selección

- Conservar inicialmente población 64, 40 generaciones y semilla 42 como parámetros del protocolo definitivo, configurables. Smoke usa una escala mucho menor.
- Mantener dos objetivos: maximizar rendimiento y abundancia predichos. Diversidad es salida secundaria y parte de la puntuación si se conserva esa regla.
- Usar la misma construcción de características en evaluación, línea base y candidatos; registrar su versión.
- No redondear entradas antes de inferir, filtrar o puntuar.
- Validar la línea base antes de compararla; no compararla fuera de dominio con candidatos admitidos.
- Validar restricciones con tolerancia numérica explícita, índices finitos y manejo de resultado vacío o una única solución.
- Recalcular predicciones para las características efectivamente exportadas con precisión completa.
- Guardar candidatos originales; después eliminar duplicados y filtrar no dominancia a precisión completa. Conservar el frente verificado y un informe de violaciones. No borrar evidencias originales para ocultar problemas.
- Elegir la solución por puntuación solo sobre candidatos admisibles del frente verificado. No llamarla punto de rodilla.
- La regla histórica da bonificación 120 al cumplir cambio de rendimiento ≥0 y abundancia ≥20%, más cambio porcentual de abundancia, 1,4 por cambio en rendimiento y 0,1 por diversidad. Puede conservarse como regla operativa predefinida, no como hipótesis científica ni utilidad económica validada.
- Documentar el denominador de cambios porcentuales y qué hacer con una línea base cero/no positiva; no usar un denominador de protección sin describirlo como tal.
- Calcular cambios con precisión completa, redondear solo vistas.
- No prometer 64 soluciones finales: población, duplicados, convergencia y filtros pueden producir otra cantidad.
- Si no se encuentra mejora conjunta, reportar ese hecho; no cambiar la puntuación ni reintentar semillas hasta obtenerla.

### 13.4 Caché y concurrencia

Clave de caché: solicitud canónica, bundle/modelo, contrato de características y configuración del optimizador. Cambiar de modelo invalida resultados previos. Capturar una instantánea del predictor para toda la ejecución. No devolver un resultado cacheado calculado con un modelo anterior ni mutar el objeto cacheado al añadir narrativa.

Los errores de dominio o ausencia de solución deben atravesar API y frontend sin convertirse en respuesta exitosa con datos inventados.

## 14. Interfaz, API y generación de texto

Implementar cambios de contrato y etiquetas, sin navegar por la UI en esta fase.

- Actualizar schemas y consumidores cuando se agreguen versiones, dominios, estados o campos de resultados.
- Conservar compatibilidad razonable o documentar migraciones; no cambiar nombres de campos sin revisar todas sus referencias.
- Reemplazar «Hipótesis comprobada» por «Criterio operativo de mejora conjunta cumplido/no cumplido», o equivalente. No es una prueba estadística ni de campo.
- Usar «índice predicho», «cambio del índice» y «configuración seleccionada»; no prometer rentabilidad, conservación observada o dosis reales de plaguicidas.
- Mapas y vista 3D representan composiciones ilustrativas; no demuestran optimización de conectividad o corredores. Mantener separadas las mallas 10×10 visual y 18×18 ABM.
- Las recomendaciones narrativas deben incluir origen: servicio de IA o fallback heurístico. No deben alterar baseline, predicciones, frente, puntuaciones o cambios numéricos.
- Mantener resultados estructurados como fuente única y añadir narrativa en un campo separado.
- No fabricar especies, prácticas modeladas o causalidades en plantillas. Cuando se mencionan sugerencias generales, identificarlas como recomendaciones no validadas y sujetas a revisión especializada.
- No añadir una bandera `validated=true` por superar un control geográfico o de rangos.
- Mantener el sistema numérico utilizable sin credenciales de un proveedor LLM.
- Revisar reportes descargables, chat, tarjetas, leyendas y respuestas API para que no contradigan el alcance.

## 15. Verificaciones técnicas a ejecutar ahora

Organiza pruebas pequeñas y deterministas, con fixtures temporales. No hagas una campaña larga ni arranques servicios productivos. Usa mocks para dominio y NSGA cuando sea adecuado, y pruebas reales pequeñas para serialización y formas de matrices.

| ID | Comprobación | Evidencia esperada |
|---|---|---|
| T01 | Rama/ruta y archivos históricos protegidos | Registro sin cambios externos |
| T02 | Dataset con NaN, infinitos, cobertura inválida y duplicados | Rechazo/agrupamiento explícito y reporte |
| T03 | IDs de train/test y tres niveles internos | Disjuntos y cobertura correcta |
| T04 | Escalado y normalización solo con entrenamiento permitido | Instrumentación de IDs o estadísticas comprobadas |
| T05 | EarlyStopping no recibe validación de puntuación ni test externo | Verificación de conjuntos usados |
| T06 | Instancias nuevas entre folds | Sin estado aprendido compartido |
| T07 | OOF completo, una predicción por fila/modelo | Conteos y ausencia de NaN inesperados |
| T08 | Métricas reconstruidas desde OOF | Coincidencia con tolerancia declarada |
| T09 | Selección respeta el criterio fijado | Casos donde ganan familias distintas |
| T10 | Bundle tradicional y Keras | Predicciones iguales antes/después si dependencias disponibles |
| T11 | Metadatos/artefactos incoherentes | Carga rechazada sin perder modelo válido |
| T12 | Clima o entradas fuera de rango | Error trazable, sin clipping silencioso |
| T13 | Diversidad y coberturas consistentes | Misma función en generador/base/candidatos |
| T14 | Soluciones dominadas, duplicadas o vacías | Filtrado y estados correctos |
| T15 | Cambios de modelo y caché | No reutilizar resultado anterior |
| T16 | Narrativa/fallback | No modificar números ni afirmar validación |
| T17 | Compose de revisión | Contenedores, volúmenes y puertos aislados |
| T18 | Sintaxis, imports y build de frontend | Comandos y códigos de salida reales |
| T19 | Smoke de núcleo científico | Run nuevo `test_only=true`, sin modelo activo reemplazado |
| T20 | Documentación y checkpoint | Otro modelo puede identificar el siguiente paso |

T04 y T05 deben probar el comportamiento, no limitarse a buscar cadenas en el código. Los mocks no demuestran exactitud estadística ni funcionamiento completo de TensorFlow: identifica qué parte cubre cada prueba.

Ejecuta compilación/importación de módulos modificados, pruebas focalizadas y build/lint disponible del frontend. No actualices paquetes automáticamente para resolver cada warning. Registra fallos preexistentes por separado y corrige los introducidos por tus cambios.

Las pruebas que requieren dependencias ausentes deben quedar `not_run` o `skipped` con motivo. No reportar «todas pasaron» si faltan las esenciales; marcar el estado global como verificación parcial.

## 16. CLI y reproducción a preparar

Implementa comandos desacoplados de Streamlit para:

1. Auditar datos históricos o corregidos.
2. Construir un dataset nuevo desde snapshots/configuración.
3. Ejecutar evaluación smoke o definitiva.
4. Recalcular métricas y análisis desde archivos persistidos.
5. Ajustar/exportar el modelo final.
6. Validar el bundle.
7. Ejecutar optimización smoke o definitiva.
8. Generar tablas y figuras desde resultados, sin números codificados manualmente.

No es obligatorio crear ocho scripts: un comando con subcomandos es suficiente. Registrar `--help`, ejemplos Windows PowerShell y Docker, rutas relativas/absolutas admitidas y códigos de salida. Los nombres concretos deben corresponder a la implementación real, no a ejemplos ficticios.

La configuración definitiva debe fijarse por archivo; no activar modo rápido o reducir folds de forma automática por falta de RAM. Si no se puede ejecutar, informar y conservar la configuración.

Al generar gráficos científicos, usar librerías de gráficos y archivos de datos. No utilizar imágenes generativas. Evitar incrustar identificadores personales en capturas; no hay pruebas de navegador autorizadas ahora.

## 17. Entregables de esta fase y relación con el artículo

Al finalizar, dejar:

1. Código corregido en la rama de revisión y diff verificable.
2. Configuraciones smoke y definitiva claramente separadas.
3. CLI preparada y documentación de comandos exactos.
4. Pruebas técnicas y sus logs.
5. Un smoke nuevo cuando sea viable, nunca presentado como resultado publicable.
6. Documentos de auditoría, decisiones, estado, metodología e informe de implementación.
7. Lista de módulos modificados y de incompatibilidades que requieren atención.
8. Lista concreta para la siguiente fase: servicios a iniciar, prueba manual, dataset a aprobar, ejecución científica y estimación medida de recursos.

En `METODOLOGIA_IMPLEMENTADA.md`, separar:

- comportamiento histórico y defectos confirmados;
- comportamiento implementado y pruebas que lo respaldan;
- configuración prevista para el experimento definitivo;
- qué NO se ejecutó;
- limitaciones científicas que permanecen.

Preparar un mapa para el artículo: sección afectada, cambio de método, archivo de evidencia futuro y estado. La Tabla 3, Figura 2, pruebas estadísticas, Figura 3, abstract y conclusiones NO se actualizan con cifras smoke. No afirmar que ya se corrigió empíricamente una métrica por haber cambiado código.

Para la futura disponibilidad de datos, preparar formatos abiertos CSV/JSON, diccionario de datos, README, licencias y hashes. El depósito externo y las firmas de autoría quedan fuera de esta fase. Registrar el uso del agente en desarrollo para que los autores puedan declarar posteriormente el alcance real de la IA.

## 18. Criterios de terminación

Completar una tabla final con cada requisito y su evidencia. Solo marcar «implementación completada y técnicamente verificada» cuando todos los módulos críticos estén implementados y las pruebas esenciales hayan sido ejecutadas satisfactoriamente. Si faltan dependencias o pruebas, entregar «implementación completada con verificación parcial» o «implementación parcial», según corresponda.

No se exige:

- que el mejor R² supere 0,47;
- que gane DNN;
- que existan 64 soluciones finales;
- que se alcance +20 % de abundancia;
- que Friedman sea significativo;
- que se completen hoy los entrenamientos definitivos;
- que el sistema esté validado para uso agronómico real.

Sí se exige que el código implemente el protocolo sin contaminación, que los modelos y cifras no se mezclen, que el dominio se trate explícitamente, que las evidencias se puedan reconstruir y que todo lo no probado quede identificado.

Entrega final en el chat del editor:

```text
Estado global:
Rama y base:
Módulos implementados:
Decisiones principales:
Pruebas ejecutadas y resultado:
Pruebas no ejecutadas:
Ubicación de informes y run smoke:
Procesos que siguen activos:
Comandos de la siguiente fase:
Pendientes para auditoría:
```

## 19. Orden de ejecución recomendado

1. Verificar workspace, Git y preservación; crear checkpoint.
2. Auditar el código; guardar hallazgos y contrato actual.
3. Aislar configuración de entorno sin arrancar todo Docker.
4. Implementar contratos, auditoría y políticas de datos.
5. Refactorizar evaluación y tuning sin fuga.
6. Persistir OOF, métricas y reproducción descriptiva/estadística.
7. Implementar selección, entrenamiento final y bundle.
8. Adaptar carga, escenarios, dominio, NSGA y caché.
9. Actualizar API, UI, narrativa y reportes.
10. Ejecutar pruebas focalizadas y smoke aislado.
11. Corregir regresiones; preparar configuraciones definitivas y documentación.
12. Consolidar estado e informe; terminar sin navegador, push ni campaña final.

No esperar confirmación entre esos pasos por decisiones rutinarias. Mantener checkpoints para que una interrupción de cuota no obligue a empezar de cero. Si hay límites de tiempo, priorizar la corrección integral del núcleo y registrar honestamente lo que falta; no sustituirla por cambios cosméticos.

## 20. Fuentes técnicas de consulta

Estas fuentes apoyan principios del plan, no certifican la implementación local. Consultar la documentación que corresponda a las versiones instaladas.

- Repositorio y commit base: https://github.com/JMarkoFlores/gemelo-digital-polinizadores/tree/1ab7c02abc4176d8ec11c94db6e15c80a885f6ab
- scikit-learn, errores comunes y prevención de fuga: https://scikit-learn.org/stable/common_pitfalls.html
- scikit-learn, validación anidada: https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html
- Keras, EarlyStopping: https://keras.io/api/callbacks/early_stopping/
- Docker Compose, nombres de proyecto: https://docs.docker.com/compose/how-tos/project-name/
- Antigravity, selección y cambio de modelo: https://antigravity.google/docs/models/
- Revista, preparación del manuscrito: https://revistacta.agrosavia.co/index.php/revista/manuscrito
- Revista, ciencia abierta: https://revistacta.agrosavia.co/index.php/revista/OpenScience

Las instrucciones de formato y envío de la revista pertenecen a la etapa editorial. Este archivo es una especificación de implementación y verificación técnica del sistema.
