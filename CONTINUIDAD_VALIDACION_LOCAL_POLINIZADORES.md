# Contexto de continuidad y preparación de la validación local

Versión 1.1 · 28 de octubre de 2026 · Responsable del proyecto: Daniel.

## 1. Propósito y estado de este documento

Este documento transfiere el contexto de una conversación de revisión metodológica a una sesión local de Codex o ChatGPT con acceso al repositorio. Permite preparar pruebas funcionales y evidencias para un artículo de Ingeniería de Software II de Ingeniería de Sistemas.

**La tarea inmediata es comprobar acceso y preparar el entorno; este documento no ordena ejecutar ahora la campaña científica definitiva ni iniciar pruebas interactivas.** La sesión local comenzará con el prompt del apartado 12 y esperará la instrucción de Daniel para pasar a la ejecución funcional.

El archivo `PLAN_REVISION_METODOLOGICA(1).md` corresponde al plan original de implementación y se conserva solo como antecedente. Posteriormente Daniel adjuntó el verdadero `PLAN_VALIDACION_FUNCIONAL.md`, que fue leído y cotejado con el código del último ZIP auditado. Este documento incorpora sus doce casos con los ajustes del apartado 14. No ejecutar literalmente las rutas, controles o expectativas incompatibles del plan original.

La base de este traspaso es el último ZIP auditado, `gemelo-digital-polinizadores-revisionUltimaRevisionActualizada.zip`, el plan funcional recibido, los reportes compartidos y las comprobaciones independientes de la conversación. La sesión local debe comprobar si existen cambios posteriores en código o documentos. Este archivo prepara la siguiente fase; no declara ejecutadas las pruebas pendientes.

## 2. Proyecto y límites del espacio de trabajo

- Repositorio: https://github.com/JMarkoFlores/gemelo-digital-polinizadores
- Carpeta autorizada de revisión: `C:\Users\Daniel\Downloads\gemelo-digital-polinizadores-revision`.
- Rama esperada: `revision-metodologica`.
- Commit base declarado: `1ab7c02abc4176d8ec11c94db6e15c80a885f6ab`.
- Copia histórica protegida: `C:\Users\Daniel\Downloads\gemelo-digital-polinizadores`.
- Proyecto Compose propuesto para revisión: `polinizadores_revision`.

El commit base no identifica por sí solo el código actual: hay modificaciones locales y archivos nuevos. Registrar HEAD, estado de Git, diff y una huella del conjunto relevante de archivos, incluyendo los no rastreados. No ejecutar reset, clean, restauraciones masivas, pull automático o eliminación de volúmenes.

No hacer commit, push, merge, despliegues o publicaciones. No cambiar instalaciones globales para resolver pruebas; utilizar el entorno aislado existente. No imprimir ni copiar secretos de archivos `.env` a informes o capturas.

## 3. Objetivo académico y alcance científico

El proyecto es un prototipo de gemelo digital agroecológico para polinizadores, con simulación multiagente Mesa, modelos sustitutos predictivos y optimización multiobjetivo NSGA-II. El destino editorial trabajado es Ciencia y Tecnología Agropecuaria, AGROSAVIA. No se han vuelto a verificar aquí normas editoriales: este documento no certifica cumplimiento de la revista.

Las ocho entradas del modelo son, en este orden:

```text
crop_area_pct
natural_area_pct
floral_strips_pct
pesticide_level
soil_management_score
temperature_c
precipitation_mm
landscape_diversity
```

Las tres salidas son:

```text
crop_yield_index
pollinator_abundance_index
pollinator_diversity_index
```

Son índices modelados o simulados. No equivalen automáticamente a rendimiento agrícola medido, conteos observados de individuos o diversidad taxonómica validada. Las referencias públicas NASA POWER/GBIF no convierten un dataset sintético en observaciones independientes de campo.

Se comparan Ridge, Random Forest, XGBoost, DNN y un MLP supervisado con cuello de botella identificado por compatibilidad como `autoencoder_mlp`. No describirlo como autoencoder de reconstrucción si ese objetivo no está implementado.

El criterio operativo conjunto es cambio de rendimiento >= 0 y aumento de abundancia >= 20 %, calculado antes de redondear. Superarlo no confirma una hipótesis ecológica ni valida el prototipo en campo. Un resultado factible que no alcance ese umbral puede ser funcionalmente correcto.

## 4. Estado heredado: qué se puede afirmar

Se cerraron las rondas de corrección hasta la Auditoría 07 dentro del alcance revisado. Entre las correcciones comprobadas figuran:

- Separación de entrenamiento, monitorización neuronal, validación interna y evaluación externa; agrupamiento de duplicados y trazabilidad OOF.
- Selección final compartida entre CLI y Streamlit, lectura de parámetros JSON y propagación de configuración y semilla al reajuste.
- Bloqueo de datos inválidos y diferenciación de límites físicos frente a rangos observados.
- Contrato de bundles, comprobación de hashes, coherencia de escalado, recuperación ante publicación fallida y recarga con conservación del predictor anterior.
- Dominio y factibilidad en optimización, filtrado Pareto y diferenciación de evaluaciones del algoritmo frente al tamaño del frente.
- Manejo de ausencia de solución en API, consulta del chat y reportes; separación de métricas ausentes y ceros reales.
- Comparaciones pareadas y recuentos consistentes: total = evaluables + no evaluables; evaluables = cumplen + no cumplen.

El último reporte de implementación declaró 132 pruebas Python aprobadas en Docker y cinco pruebas Node aprobadas. La revisión independiente no repitió aquí toda esa ejecución Docker. Sí ejecutó las cinco pruebas Node de Excel, comprobó las funciones reales de presentación y reprodujo los casos de agregación global, regional y temporal con entradas controladas.

Las cinco pruebas Node usan dependencias simuladas para verificar la preparación de datos de Excel. No certifican archivos ofimáticos físicos, renderizado React, paginación de PDF o apariencia de Word. Las pruebas aisladas tampoco equivalen a una validación completa de la aplicación.

Último smoke conservado auditado: `artifacts/revision_metodologica/smoke_20261028_195256/`. Sus 16 hashes coincidieron. El bundle reportado es `bundle_ridge_bd24bc5fdf03`. Se trata de evidencia técnica de prueba, no del experimento definitivo.

No se ejecutaron en esta fase las pruebas manuales en navegador ni la campaña definitiva. Los números del smoke no deben trasladarse al resumen, tablas de resultados o conclusiones del artículo como hallazgos finales.

## 5. Archivos a leer primero en la sesión local

Leer, sin reconstruir todo el historial ni editar código:

1. `docs/revision_metodologica/ESTADO_IMPLEMENTACION.md`.
2. `docs/revision_metodologica/PLAN_VALIDACION_FUNCIONAL.md`.
3. `docs/revision_metodologica/DECISIONES.md`, priorizando decisiones finales.
4. `docs/revision_metodologica/INFORME_CORRECCIONES_AUDITORIA_07.md` y cierre documental posterior.
5. `docs/revision_metodologica/METODOLOGIA_IMPLEMENTADA.md`.
6. Compose, ejemplos de configuración, CLI y los adaptadores necesarios para los casos concretos.

El plan original puede contener hallazgos ya corregidos y decisiones posteriormente refinadas. No reintroducirlos ni ejecutar otra campaña de implementación. Si este documento y el código difieren, registrar la discrepancia y comprobar el estado local real.

## 6. Ajustes del plan funcional conocidos antes de probar

| Tema | Dato comprobado y tratamiento |
|---|---|
| Recarga del modelo | La ruta del código auditado es `POST /api/model/reload`, no `/api/v1/models/reload`. Requiere autenticación de cliente o administrador. |
| Estado del modelo | Ruta comprobada: `GET /api/model/status`, autenticada. |
| Simulación | Ruta comprobada: `POST /api/simular`. Consultar el schema real para los campos admitidos. |
| Semilla de entrenamiento en pantalla | La llamada del botón utiliza `random_state=42`. Las semillas de widgets de generación de datos no son necesariamente la semilla de entrenamiento. |
| Comprobación con semilla 1337 | Ejecutarla mediante adaptador/prueba programática y etiquetarla como tal. No afirmar que se seleccionó desde un widget inexistente. No modificar la UI solo para hacer pasar el plan. |
| Puertos de revisión | 5433, 8001, 5174 y 8502 son valores del ejemplo de revisión, no valores garantizados en ejecución. Verificar variables efectivas, puertos libres y URLs. |
| Folds y dataset de prueba | Evitar lanzar inadvertidamente la configuración definitiva. Utilizar datos pequeños válidos y una configuración de pruebas identificada. No sustituir silenciosamente la configuración científica. |
| Modelo de prueba en backend | El backend científico rechaza bundles `test_only`. No quitar esa etiqueta para forzar carga. Comprobar rechazo y, si se habilita un entorno de prueba explícito, documentarlo sin alterar producción ni histórico. |
| Resultado de optimización | No se exige una familia ganadora concreta, 64 soluciones ni mejora >=20 %. Sí se exige coherencia, factibilidad y trazabilidad. |
| Ausencia de solución | Puede requerir un escenario o fixture controlado. No inventar una interacción UI si el caso solo se pudo reproducir mediante integración. Distinguir rechazo por dominio de ausencia de soluciones. |
| Navegadores | Registrar navegador y versión realmente probados. No usar el término homologado ni fijar mínimos no comprobados. |

Puertos externos e internos de Docker son diferentes. Verificar también API URL, CORS y que backend/Streamlit compartan exclusivamente el volumen de modelos de revisión. Langflow es opcional; los cálculos no deben depender de sus credenciales.

Comando orientativo de inspección, solo si el archivo existe:

```powershell
docker compose --project-name polinizadores_revision --env-file .env.revision config --services
```

No publicar la configuración completa si puede contener secretos. El arranque de servicios corresponde a la fase funcional posterior, no al prompt inicial de acceso.

## 7. Matriz de validación funcional ajustada al plan recibido

Cada caso se ejecutará después de la comprobación de acceso y de la instrucción de inicio de Daniel. Utilizar datos y cuentas de prueba aislados.

| Caso | Acción y resultado esperado | Evidencias mínimas |
|---|---|---|
| CP-FUNC-01 | Entrenamiento pequeño en Streamlit con semilla 42 del botón y folds externos disponibles; finalización y persistencia coherentes. Añadir subcaso programático separado con semilla 1337. | Capturas de entradas/resultado, run_id, dataset y hash, configuración, métricas y OOF; metadatos de semilla final del bundle. |
| CP-FUNC-02 | Exportación y recarga autenticada por las rutas reales: bundle íntegro, identidad activa correcta y predicciones consistentes. Diferenciar rechazo intencional de test_only de error de carga. | Metadatos, hashes, estado antes/después y respuesta de recarga. |
| CP-FUNC-03 | Optimización factible usando geometría/bbox, manejo y escenario climático realmente admitidos: frente admisible y criterio conjunto fiel a los números, alcance o no el umbral. | Solicitud JSON, respuesta, baseline, frente y solución con precisión conservada, captura. |
| CP-FUNC-04 | Entradas inválidas: CSV con coberturas incoherentes y caso de clima/dominio no admitido, por las interfaces que realmente expongan esos datos. | Entrada utilizada, rechazo visible/API y constancia de que no se trató como ejecución exitosa. |
| CP-FUNC-05 | Sin soluciones: estado no evaluable, óptimo ausente, sin excepción y sin mejoras fabricadas. | Fixture o escenario controlado, método de reproducción, respuesta, registro recuperado y captura si se recorrió UI. |
| CP-FUNC-06 | Chat e historial de una simulación factible: consulta por su ID, datos fieles y narrativa identificada. | ID de registro, pregunta/respuesta y capturas; no capturar credenciales. |
| CP-FUNC-07 | Chat e historial de una simulación sin solución: valores no evaluables sin caídas ni mejoras inventadas. | Pregunta, respuesta, ID consultado y origen de narrativa; comprobación de autorización. |
| CP-FUNC-08 | Informe mixto controlado: comprobar total=evaluables+no evaluables y evaluables=cumplen+no cumplen. Con un caso que cumple y otro no evaluable: 2=1+1; cumplen=1, no cumplen=0 y tasa=100 % de evaluables. Añadir un evaluable que no cumple para cubrir las tres categorías. | Datos controlados identificados, respuesta de reporte y captura de pantalla. |
| CP-FUNC-09 | Informe sin evaluables o sin registros: N/D frente a cero real, denominador visible y sin puntos ficticios. Conservar comparación pareada 100→110 junto con 1000→sin solución. | Casos, respuesta JSON y vistas global/regional/temporal pertinentes. |
| CP-FUNC-10 | Descargar y abrir Excel real: hojas y celdas correctas, recuentos separados, cero numérico distinto de N/D y deltas coherentes. | XLSX original, hash, inspección de valores/tipos y capturas de apertura cuando sea posible. |
| CP-FUNC-11 | Descargar PDF real: texto, tablas, rótulos, paginación y legibilidad sin solapamientos. | PDF original, hash y páginas revisadas/renderizadas; registrar lector/herramienta. |
| CP-FUNC-12 | Descargar Word real: apertura, contenido, tablas, títulos y notas de denominador; sin pérdida de información. | DOCX original, hash y revisión visual. Si se utiliza conversión, distinguirla de apertura en Word/Writer. |

Las capturas muestran lo que la interfaz presenta; no sustituyen datos estructurados ni verificaciones científicas. Una descarga detectada no demuestra que el archivo sea válido. Si la herramienta no puede capturar video, no afirmar que se grabó: utilizar capturas secuenciales con bitácora, o registrar una grabación realizada por Daniel como evidencia distinta.

No prometer exhaustividad: esta matriz establece cobertura explícita. Cualquier prueba bloqueada se registra como tal, no como aprobada. Un caso reproducido solo con mocks no equivale a un recorrido real por navegador, API y base de datos.

## 8. Dataset y modelo para la fase funcional

La elección debe fijarse y registrarse antes del recorrido. Priorizar 24–40 filas coherentes, con suficientes grupos para las particiones internas y de monitorización. Un presupuesto reducido de prueba no debe reemplazar ni sobrescribir `configs/revision_metodologica.json`.

No iniciar una campaña definitiva desde la UI por usar el rótulo «científico». Inspeccionar el código y configuración efectiva antes de pulsar el botón. Comenzar por el flujo pequeño; ampliar a las familias necesarias con un presupuesto explícito. No deshabilitar familias silenciosamente ni presentar su ausencia como comparación de cinco modelos.

Para la prueba UI con semilla 42 y la prueba programática con semilla 1337, conservar ejecuciones diferentes y sus etiquetas. La creación y activación de un bundle de revisión debe preservar cualquier bundle anterior del mismo entorno. Nunca reemplazar el histórico.

Los resultados de la fase funcional deben permanecer identificados en el acta como pruebas, incluso si por su modo de ejecución el bundle no lleva `test_only`. Ese campo por sí solo no convierte un experimento en evidencia científica definitiva.

## 9. Evidencias y registro de incidencias

Directorio previsto en la copia de revisión:

```text
artifacts/revision_metodologica/validacion_funcional/<sesion_unica>/
  contexto_y_entorno.json
  casos.csv
  bitacora.md
  incidencias.md
  capturas/
  descargas/
  solicitudes_y_respuestas/
  referencias_runs_y_bundles/
  logs/
  SHA256SUMS.txt
```

Crear solo archivos efectivamente obtenidos. Conservar originales y registrar cualquier copia anonimizada. No incluir contraseñas, tokens, claves API ni cookies.

Por caso registrar: ID, versión/huella de código, fecha y zona horaria, operador/agente, navegador, cuenta de prueba por rol, dataset y hash, configuración y semillas, run_id, bundle_id, pasos, esperado, observado, estado, archivos de evidencia, incidencia y repetición relacionada.

Estados: APROBADO, FALLIDO, BLOQUEADO, OMITIDO y NO EJECUTADO. Definir el motivo de cada caso no aprobado. Registrar si la evidencia es UI real, API real, integración controlada, inspección de archivo o mock.

Al aparecer un defecto, guardar evidencia antes de corregir. Vincular prueba anterior y posterior con las versiones de código correspondientes. No reiniciar toda la auditoría ni repetir entrenamientos ajenos al fallo. Usar pruebas focalizadas y una regresión proporcional al cambio.

## 10. Separación de la campaña científica definitiva

La campaña posterior requiere una instrucción de Daniel y protocolo fijado: dataset, origen, política ABM, configuración, familias, búsqueda, semillas, métricas, dominio y almacenamiento.

La propuesta vigente contempla 320 escenarios y enriquecimiento ABM uniforme `corrected_full`, CV externa de cinco folds e interna de tres. Las 320 simulaciones ABM generan/enriquecen el dataset; no debe describirse automáticamente como 320 × 5 simulaciones ABM. La CV evalúa modelos sobre las particiones del dataset. Cualquier regeneración por fold debe declararse y justificarse si realmente se implementa.

No usar el smoke como dataset definitivo, no ajustar semillas para obtener mejora y no forzar que gane una red. Comparar familias por menor MAE macro en escala original, conservar resultados por salida y documentar el sesgo de seleccionar una familia con esas comparaciones. No atribuir al modelo final reajustado una nueva métrica de test independiente por haberlo exportado.

Para el artículo, relacionar cada afirmación con artefactos definitivos: datos y procedencia, configuración, OOF, métricas por fold y salida, selección final, bundle y optimizaciones. Mantener simulaciones, interpretación operativa y validación de campo claramente diferenciadas. El Word vigente deberá ser confirmado por Daniel antes de editarlo.

## 11. Criterio de cierre funcional

Cerrar cada caso con evidencia o limitación explícita. No exigir resultados favorables, significancia estadística, una cantidad fija de soluciones o una familia ganadora. Se exige que el comportamiento observado corresponda al contrato y que los resultados sean trazables.

La inspección de documentos reales y los recorridos interactivos pendientes deben resolverse o quedar justificados antes de declarar validación funcional completada. Ese cierre no constituye aprobación editorial ni validación agronómica del prototipo.

## 12. Prompt inicial para pegar en la sesión local

```text
Estamos continuando el proyecto gemelo-digital-polinizadores para un
artículo de Ingeniería de Software II destinado a AGROSAVIA.

Lee completo CONTINUIDAD_VALIDACION_LOCAL_POLINIZADORES.md, incluido
su apartado 14 de ajustes al plan, y después
docs/revision_metodologica/ESTADO_IMPLEMENTACION.md y
docs/revision_metodologica/PLAN_VALIDACION_FUNCIONAL.md.

Carpeta autorizada:
C:\Users\Daniel\Downloads\gemelo-digital-polinizadores-revision
Rama esperada: revision-metodologica.
Base histórica: 1ab7c02abc4176d8ec11c94db6e15c80a885f6ab.
El trabajo actual incluye cambios locales posteriores: consérvalos.

Tu tarea ahora es únicamente comprobar capacidades y preparar el inicio:
1. Comprueba carpeta, rama, HEAD, estado y archivos nuevos, sin cambiar código.
2. Identifica las herramientas reales de archivos, terminal y navegador.
3. Comprueba Docker y enumera servicios/contenedores de revisión existentes.
   No arranques servicios ni sustituyas modelos todavía.
4. Contrasta el plan funcional con el código local: salud GET /health,
   recarga POST /api/model/reload, estado GET /api/model/status,
   autenticación, semilla 42 del botón, comprobación programática separada
   de semilla 1337, artefactos reales y puertos efectivos.
   No implementes controles ni endpoints nuevos solo para satisfacer
   pasos incorrectos del plan de Antigravity.
5. Indica qué URLs de localhost podrías abrir con las herramientas disponibles.
   No supongas que un navegador cloud puede acceder al localhost de Daniel.
6. Si hay una página de revisión ya disponible y las herramientas lo permiten,
   abre únicamente su página inicial, sin autenticarte ni activar acciones.
   Registra esa apertura como comprobación de acceso, no como caso funcional.
7. Resume capacidades confirmadas, diferencias del plan y bloqueos concretos.

No ejecutes todavía casos funcionales, entrenamientos, campaña definitiva,
modificaciones, commits, push o publicaciones. No explores la copia histórica.
No imprimas secretos. No prometas control del mouse, video ni acceso a apps
si esas herramientas no están disponibles.

No reinicies la implementación del plan metodológico original. Las correcciones
hasta Auditoría 07 ya tienen evidencias de revisión; comprueba diferencias locales
antes de reabrir módulos. Tras este inventario, espera la instrucción de Daniel
para comenzar el recorrido funcional y la captura de evidencias.
```

## 13. Acciones de Daniel para transferir el contexto

1. Guardar este archivo dentro de la carpeta de revisión con su mismo nombre, sin sustituir documentos históricos.
2. Abrir esa carpeta en la sesión local elegida y adjuntar/referenciar este Markdown.
3. Pegar el prompt del apartado 12.
4. Revisar el inventario de capacidades y diferencias antes de indicar el comienzo de las pruebas.

El cotejo del plan adjuntado ya se completó para preparar este documento. No es necesario volver a enviar el repositorio por estos ajustes documentales. La primera sesión local debe verificar el estado actual y las capacidades reales antes del inicio funcional.

## 14. Correcciones concretas al plan funcional de Antigravity

Estos ajustes sustituyen los pasos incompatibles del documento recibido, conservando sus doce identificadores y su propósito. No constituyen cambios de código ni resultados de ejecución.

| Apartado del plan recibido | Ajuste para ejecutar sobre el sistema auditado |
|---|---|
| Estado «APROBADO PARA EJECUCIÓN» y «100% verificado» | Interpretar como preparación documental de Antigravity, no como certificación global ni instrucción para iniciar ahora. Distinguir resultados reportados y comprobaciones independientes. |
| Windows 11, Engine 29.x, navegadores «homologados» | Inventariar el sistema, versiones y capacidades reales. No exigir versiones inventadas por el plan ni actualizar el equipo sin necesidad. |
| PostgreSQL 15 | El Compose auditado declara `postgres:16-alpine`. Comprobar la imagen realmente ejecutada y registrar su versión. |
| Nombres `polinizadores_revision_db`, etc. | No asumir nombres exactos. Consultar servicios `db`, `backend`, `frontend`, `streamlit`, `scientific` y nombres generados por Compose. |
| Salud `GET /api/v1/health` | La ruta real es `GET /health` en el backend; con puerto de revisión confirmado, `http://localhost:8001/health`. |
| `pg_isready ... -U postgres` | Utilizar el usuario y base efectivos de revisión. Preferir el healthcheck del servicio o `docker compose ... exec db ...` con variables internas; no exponer sus valores sensibles. |
| CP-01: selector lateral y botón «Entrenar y Evaluar Sustitutos» | El modo y folds externos están en la sección de entrenamiento; el botón observado es «Entrenar y comparar modelos». Localizar controles por el estado real, no por rótulos imaginados. |
| CP-01: semilla 1337 desde UI; seleccionar folds internos y familias | El botón pasa 42; la UI auditada no expone allí esos tres controles como indica el plan. Cubrir semilla 1337 y configuración de familias/folds internos mediante adaptador/configuración de prueba explícita, como evidencia programática separada. |
| CP-01: lista de 11 archivos | La lista real al cerrar evaluación es: `manifest.json`, `config_effective.json`, `environment.json`, `data_audit.json`, `dataset.csv`, `splits.json`, `tuning_results.csv`, `fold_metrics.csv`, `oof_predictions.csv`, `model_summary.csv` y `SHA256SUMS.txt`. El bundle es una exportación posterior. No exigir archivos inexistentes como `evaluation_timings.csv`. |
| CP-01: `manifest.final_seed=1337` obligatorio | Verificar la semilla en configuración, constructor/modelo final y metadatos de exportación donde realmente se registra. No exigir una clave adicional en manifest que el contrato no declara. |
| CP-02: bundle ZIP y botón de producción | El flujo exporta un directorio de bundle al volumen `/modelos_ia` en el contenedor. No exigir un ZIP ni un nombre de carpeta que no existe. El botón observado es «Exportar modelo entrenado»; cotejar localmente. |
| CP-02: `/api/v1/models/reload` y `/active` sin autenticación | Utilizar `POST /api/model/reload` y `GET /api/model/status` con la autenticación de prueba y el rol admitido. No pegar tokens en evidencias. Comparar identidad/versión realmente activada; un HTTP 200 por sí solo no prueba que se haya cargado el modelo solicitado. |
| CP-03/04: introducir cultivo, franjas, temperatura y precipitación en la solicitud de optimización | `SimulationRequest` admite `geometry` o `bbox`, `pesticide_level`, `min_natural_area_pct` y `climate_scenario`. Las otras características se construyen internamente. Probar cobertura inválida desde el CSV/auditoría donde corresponda y registrar clima y dominio efectivos; no añadir campos arbitrarios a la API. |
| CP-03: éxito asociado a mejora conjunta | Una solución factible que no alcanza +20% sigue siendo un resultado funcional válido si se representa correctamente. No modificar semillas, límites o datos para producir un banner favorable. |
| CP-05: «condiciones desfavorables» garantizan infactibilidad | Fijar un caso reproducible. Un valor fuera de dominio puede producir rechazo antes de optimizar, no `infeasible`. Si hace falta una fixture de integración, identificarla y no presentarla como una optimización natural ejecutada por el usuario. |
| CP-05: comprobar `metricas_optimas IS NULL` y criterio almacenado | Comprobar el valor recuperado por ORM/API y la serialización JSON: JSON null y SQL NULL no son necesariamente equivalentes. `meets_joint_criteria` está en la respuesta; no exigir una columna persistente no declarada. Conservar respuesta e ID de registro. |
| CP-06/07: seleccionar siempre una simulación en un control del chat | Verificar el flujo real. Si consulta por ID o extrae el ID del mensaje, utilizarlo y registrar la pregunta exacta; no asumir un selector inexistente. |
| CP-06: lenguaje «probabilístico» | Exigir lenguaje de predicción/simulación, sin inventar probabilidades, confianza o causalidad que el modelo no cuantifica. |
| CP-10: ejemplo de cero en kg/ha | Usar las unidades/índices implementados. El índice de rendimiento no se convierte en kg/ha por su nombre. |
| CP-10 a CP-12: maquetación y apertura | Son verificaciones reales pendientes. Conservar archivos descargados y abrirlos con herramientas disponibles. Si Daniel realiza la apertura o inspección humana, registrarlo como tal; la revisión del agente no sustituye una firma humana. |
| Campaña «320 ABM × 5 × 3» | Separar la generación uniforme de 320 escenarios ABM del entrenamiento/evaluación con cinco folds externos y tres internos. No multiplicar simulaciones ABM salvo que el procedimiento realmente las regenere. |

Para las pruebas negativas de PDF/Word/Excel, incluir una cohorte sin evaluables y otra con un cero calculado real. No fijar la extensión o el nombre exacto descargado como criterio si el exportador usa nombres con marca temporal: registrar el nombre real y su hash.

No iniciar la campaña definitiva automáticamente al completar los casos. Primero consolidar el acta con evidencias, bloqueos y limitaciones y recibir la instrucción de Daniel para esa fase. No inventar firmas ni marcar casos bloqueados como aprobados para alcanzar «12/12».

## 15. Estado Actual de Ejecución de la Validación Funcional (Local)

1. **INC-FUNC-001**: **CORREGIDA Y COMPROBADA**. Tipos binarios válidos en `st.download_button`, invalidación estricta de caché in-place por hash de contenido e índices, y renderizador de 11 figuras a 600 DPI. 6/6 pruebas aprobadas en contenedor (`streamlit_app/test_export_helpers.py`).
2. **CP-FUNC-01A (Entrenamiento y exploración interactiva en navegador web)**: **APROBADO Y VERIFICADO**. Ejecutado mediante Google Chrome nativo con Chrome DevTools MCP en `http://localhost:8502/`. Fixture de 40 filas, semilla fija 42, 2 folds, sin enriquecimiento ABM, tuning apagado. Corrida interactiva completada (`run_id: streamlit_scientific_20261029_011320`), tablas T5 y T6 desplegadas, persistencia entre pestañas verificada y 11 artefactos íntegros con SHA-256 verificado. Descargas de `T2_muestra_datos.xlsx` y `F1_matriz_correlaciones_600dpi.png` validadas byte a byte.
3. **CP-FUNC-01B (Propagación programática de semilla personalizada 1337)**: **APROBADO Y VERIFICADO PROGRAMÁTICAMENTE**. Ejecutado mediante el adaptador científico (`streamlit_app/adapter.py`) en el contenedor aislado con semilla inyectada 1337 (`run_id: streamlit_scientific_20261029_012835`). Propagación estocástica confirmada en DNN (MAE 8.8103 vs 11.4396), RF (MAE 11.8444 vs 11.3825), Autoencoder (MAE 13.5271 vs 14.0086) y Ridge invariante (2.7731) por solución analítica cerrada. 11 artefactos íntegros con 10/10 hashes SHA-256 validados, 600 filas OOF sin NaN ni duplicados y `final_seed: 1337` en metadatos del ganador refiteado.
4. **CP-FUNC-01 (Caso Completo)**: **COMPLETADO SATISFACTORIAMENTE**. La ruta de tuning extendido (`tune_hyperparameters=True`) permanece formalmente identificada como PENDIENTE de prueba controlada.
5. **CP-FUNC-02 (Exportación de bundle y recarga atómica en Backend)**: **APROBADO Y VERIFICADO SATISFACTORIAMENTE**.
   - **Diagnóstico de Causa Raíz**: Refutada empíricamente la hipótesis del guion bajo (`_`) en `st.session_state`. Causa real identificada: en el commit base `1ab7c02`, `render_dataset_tab()` ejecutaba incondicionalmente `st.session_state.training_result = None` ante cualquier rerun con CSV presente.
   - **Pruebas Automatizadas**: 34/34 pruebas aprobadas en contenedor `scientific` (18 de bundles, validación, hardening e interacción simulada + 16 de contratos, persistencia y atomicidad).
   - **Recorrido Interactivo en Navegador**: Ejecutada la única corrida interactiva autorizada con fixture de 40 filas (`run_id: streamlit_scientific_20261029_031906`, Ridge ganador). Clic único en "Exportar modelo entrenado" en Pestaña 5: estado preservado sin reinicio, banner verde emitido y visor JSON visualizado.
   - **Publicación en Volumen Docker**: Creado `/modelos_ia/bundle_ridge_7f248dd497dd/` y conmutado atómicamente el puntero `/modelos_ia/active_bundle.json`.
   - **Recarga Autenticada en Backend (`http://localhost:8001/`)**: `POST /api/model/reload` y `GET /api/model/status` retornan `model_ready: true`, versión `bundle_ridge_7f248dd497dd` y metadatos con rangos observados. `GET /health` responde 200 OK.
   - **Equivalencia Predictiva**: Discrepancia absoluta de $0.0$ ($100\%$ coincidencia numérica) entre `UniversalSurrogatePredictor` y `ModelStore.predict` para el vector de prueba evaluado.
   - **Evidencias**: Acta y 5 capturas en `artifacts/revision_metodologica/validacion_funcional/CP-FUNC-02_final_20261028/` con `SHA256SUMS.txt`.


6. **CP-FUNC-03 (Simulación válida y optimización multiobjetivo en frontend)**: **APROBADO Y VERIFICADO SATISFACTORIAMENTE**.
   - **Recorrido Interactivo en Navegador**: Ejecutado con `Browser Automation Specialist` sobre `http://localhost:5174/client` con usuario autenticado `cliente_rev@example.com`. Modelo activo verificado: `bundle_ridge_7f248dd497dd (ridge)`. Geometría seleccionada: Valle de Virú (polígono de 4 vértices). Escenario: plaguicidas $30\%$, área natural mínima $20\%$, clima actual.
   - **Ejecución y Persistencia**: Simulación ejecutada con NSGA-II y persistida en BD con `simulation_id: 2` (fecha `2026-10-29T06:07:38.584513`).
   - **Coherencia Numérica UI-API-BD**: Concordancia exacta entre pantalla, API y BD:
     * Línea Base: Rendimiento $104.9177$ (UI $104.92$), Abundancia $55.5233$ (UI $55.52$).
     * Óptimo: Rendimiento $105.1775$ (UI $105.18$), Abundancia $122.2550$ (UI $122.25$), Diversidad $76.5746$ (UI $76.57$).
     * Deltas: $\Delta\text{yield} = +0.2598$ (UI $+0.260$), $\Delta\text{pollinators} = +120.1868\%$ (UI $+120.2\%$, denominador exacto base $55.5233$).
     * Criterio Conjunto: Cumplido ($\ge 0$ y $\ge 20\%$).
   - **Factibilidad y No Dominancia**: 64/64 soluciones del frente cumplen coberturas $\le 100\%$ y rangos observados de entrenamiento. Propiedad de no dominancia estricta verificada (0 soluciones dominadas).
   - **Recomendación Agroecológica**: Generada por IA y renderizada correctamente en interfaz y BD.
   - **Evidencias**: 5 capturas en `artifacts/revision_metodologica/validacion_funcional/CP-FUNC-03_04_05_20261029/capturas/`.

7. **CP-FUNC-04 (Rechazo de entradas inválidas)**: **APROBADO Y VERIFICADO SATISFACTORIAMENTE**.
   - **Guardarraíles en UI**: Demostrada la prevención física en frontend (sliders restringidos a $[0, 100]$ y $[5, 45]$; menú desplegable de clima cerrado a 4 escenarios válidos; no permite combinaciones arbitrarias de cobertura $> 100\%$).
   - **Verificación Programática vía API (`POST /api/simular`)**:
     * Cobertura $> 100\%$ (`min_natural_area_pct=95.0%` $\to$ suma $119\%$): Rechazado con HTTP 400 Bad Request y detalle `"Suma de coberturas excede 100% (119.00%)"`.
     * Clima desconocido (`"artico"`): Rechazado con HTTP 422 Unprocessable Entity por validación Pydantic Literal.
     * Plaguicidas $> 100\%$ ($150\%$): Rechazado con HTTP 422 Unprocessable Entity por validación Pydantic Field.
     * Plaguicidas fuera de rango observado de entrenamiento ($95.0 > 91.06$): Rechazado con HTTP 400 Bad Request y detalle explicativo de fuera de rango.
   - **Integridad de BD y Ausencia de HTTP 500**: 0 errores 500. Conteo en tabla `simulaciones` inalterado (1 inicial, 1 final). Ninguna entrada inválida generó registro de simulación.

8. **CP-FUNC-05 (Ausencia de solución / escenario infactible)**: **PENDIENTE DE REPRODUCCIÓN FUNCIONAL DEL ESTADO SIN SOLUCIÓN**.
   - **Análisis de Contrato**: El problema de optimización acota la búsqueda al intervalo $[xl, xu] = [\max(p_{\min}, \text{obs}_{\min}), \min(p_{\max}, \text{obs}_{\max})]$. Si una entrada fuerza restricciones contradictorias o disjuntas ($xl > xu$), el contrato lanza `ValueError` y la API rechaza upfront con HTTP 400 antes de optimizar. Si las restricciones son conjuntas ($xl \le xu$), el espacio es convexo y no vacío.
   - **Intentos Justificados en Frontera (Presupuesto: 2 intentos autorizados)**:
     * Intento 1 (`min_natural_area_pct = 39.1%`, frontera de $39.15\%$): NSGA-II encontró 64 soluciones admisibles.
     * Intento 2 (`pesticide_level = 91.0%`, frontera de $91.06\%$ + clima extremo): NSGA-II encontró 61 soluciones admisibles.
   - **Mecanismo Implementado**: El flujo para `status: "infeasible"` existe en código backend, BD (`metricas_optimas: null`) y banner UI (`ResultsDashboard`), pero para el modelo activo `bundle_ridge_7f248dd497dd` no ocurre de forma natural sin mockear la aplicación real. Siguiendo el mandato de auditoría, se registra esta limitación sin forzar mocks.
