# Inventario y Estado de Pruebas de Software y Validación Estadística

**Documento:** `docs/pruebas.md`  
**Referencia del commit analizado:** [`0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02`](https://github.com/JMarkoFlores/gemelo-digital-polinizadores/commit/0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02)  
**Evidencia principal:** [streamlit_app/robust_tests.py](../streamlit_app/robust_tests.py), [streamlit_app/test_traceability_pipeline.py](../streamlit_app/test_traceability_pipeline.py), [streamlit_app/test_tuning_benchmark.py](../streamlit_app/test_tuning_benchmark.py), [scratch/test_nemenyi.py](../scratch/test_nemenyi.py), [backend/requirements.txt](../backend/requirements.txt), [frontend/package.json](../frontend/package.json)

---

## 1. Declaración de Ejecución de Pruebas

> **Declaración de Integridad Metodológica:**  
> En cumplimiento estricto de las directrices del proyecto:  
> **1. Ninguna prueba unitaria, funcional, estadística o de integración fue ejecutada durante la elaboración de este documento.**  
> **2. No se presentan como ejecutadas pruebas que no hayan sido realizadas.**  
> La información presentada a continuación corresponde exclusivamente al **inventario estático del código fuente** de las pruebas encontradas y al análisis de los métodos implementados en el repositorio.

---

## 2. Clasificación de Pruebas en el Repositorio

| Categoría | Estado de Existencia en Código | Estado de Ejecución en este Análisis | Ubicación de Respaldo |
| :--- | :--- | :--- | :--- |
| **Pruebas Estadísticas e Inferenciales** | `[CÓDIGO]` Implementadas en interfaz UI de Streamlit | **No ejecutadas** (requieren entrenamiento interactivo previo) | [streamlit_app/robust_tests.py](../streamlit_app/robust_tests.py) |
| **Scripts de Auditoría y Trazabilidad** | `[CÓDIGO]` Presentes como scripts autónomos de consola | **No ejecutados** (requieren contenedor backend activo) | [streamlit_app/test_traceability_pipeline.py](../streamlit_app/test_traceability_pipeline.py) |
| **Scripts de Benchmark de Rendimiento** | `[CÓDIGO]` Presentes como scripts autónomos de consola | **No ejecutados** | [streamlit_app/test_tuning_benchmark.py](../streamlit_app/test_tuning_benchmark.py) |
| **Script Aislado de Prueba Nemenyi** | `[CÓDIGO]` Presente en carpeta scratch | **No ejecutado** | [scratch/test_nemenyi.py](../scratch/test_nemenyi.py) |
| **Suite de Pruebas Unitarias Backend** | ❌ **Ausente** (no existe `pytest` ni directorio `tests/`) | **Inexistente** | [backend/requirements.txt](../backend/requirements.txt) |
| **Suite de Pruebas Unitarias Frontend** | ❌ **Ausente** (no existe `vitest`, `jest` ni archivos `*.test.jsx`) | **Inexistente** | [frontend/package.json](../frontend/package.json) |
| **Pruebas End-to-End (E2E)** | ❌ **Ausente** (no existe Cypress ni Playwright) | **Inexistente** | Estructura general |
| **Pipeline Automatizado en CI/CD** | ❌ **Ausente** (no existe `.github/workflows/`) | **Inexistente** | `.github/` no existe |

---

## 3. Protocolo de Pruebas Estadísticas Inferenciales (Fase 5 CRISP-DM)

Archivo de respaldo: [streamlit_app/robust_tests.py](../streamlit_app/robust_tests.py)

El módulo `robust_tests.py` contiene la lógica matemática para someter las arquitecturas evaluadas a 7 pruebas inferenciales cruzadas para determinar si la superioridad del modelo propuesto es estadísticamente significativa o atribuible al azar:

### 3.1 Pruebas Pareadas sobre Predicciones Out-of-Fold (Tabla T7)
Se comparan los errores absolutos del modelo ganador (*Baseline*) frente a cada competidor:

1. **Test de Shapiro-Wilk (`stats.shapiro`):**  
   Evalúa la hipótesis nula de normalidad en la distribución de los residuos. Si el $p\text{-valor} > 0.05$, se asume distribución normal y se habilita la prueba paramétrica T-Student. Si $p \le 0.05$, se recurre a Wilcoxon.
2. **T-Student Apareado (`stats.ttest_rel`):**  
   Prueba paramétrica para muestras dependientes sobre los errores absolutos out-of-fold.
3. **Wilcoxon Signed-Rank (`stats.wilcoxon`):**  
   Prueba no paramétrica basada en rangos con signo para muestras apareadas.
4. **Tamaño del Efecto ($D$ de Cohen, función `cohen_d`):**  
   Calcula la magnitud estandarizada de la diferencia de error entre modelos:
   $$d = \frac{\bar{x}_{\text{competidor}} - \bar{x}_{\text{baseline}}}{s_{\text{diferencia}}}$$
   Valores positivos indican superioridad del baseline ($|d| < 0.2$ trivial, $0.2 \le |d| < 0.5$ pequeño, $0.5 \le |d| < 0.8$ mediano, $|d| \ge 0.8$ grande).
5. **Corrección de Bonferroni:**  
   Ajusta el umbral de significancia base ($\alpha = 0.05$) dividiéndolo entre el número de contrastes independientes ($\alpha_{adj} = 0.05 / (M - 1)$) para controlar la tasa de error por familia (FWER).

### 3.2 Análisis de Varianza Multimodelo Global (Tablas T8, T9 y Figuras F10, F11)

1. **Test de Friedman (`stats.friedmanchisquare`):**  
   Prueba no paramétrica ómnibus sobre los errores agregados por fold ($k=5$). Evalúa si al menos una arquitectura difiere significativamente del conjunto. Genera la **Tabla de Rangos Promedio por Modelo (T8)** y el gráfico de barras **F10**.
2. **Análisis Post-Hoc de Nemenyi (`scikit_posthocs.posthoc_nemenyi_friedman`):**  
   Si y solo si el Test de Friedman rechaza la hipótesis nula global ($p < 0.05$), se calcula la **Matriz Simétrica de $p$-valores de Nemenyi (T9)** y el mapa de calor **F11**, identificando formalmente qué pares específicos presentan divergencia estadística real.

> **Nota Metodológica del Código ([robust_tests.py:140-142](../streamlit_app/robust_tests.py#L140-L142)):**  
> *"Estas pruebas asumen independencia entre observaciones; al proceder de validación cruzada, dicha independencia es parcial, lo que puede subestimar la varianza real de los errores (Dietterich, 1998; Nadeau & Bengio, 2003). Los resultados deben interpretarse como una referencia complementaria al Test de Friedman/Nemenyi, que sí opera correctamente a nivel de fold."*

---

## 4. Scripts Autónomos de Prueba y Verificación

### 4.1 Script `test_traceability_pipeline.py`
Archivo: [streamlit_app/test_traceability_pipeline.py](../streamlit_app/test_traceability_pipeline.py)
- **Alcance:** Prueba de consola que ejecuta en secuencia:
  1. Generación de dataset sintético (320 muestras, semilla 42, con enriquecimiento ABM).
  2. Entrenamiento con validación cruzada ($k=3$) mediante `train_and_evaluate_all_models`.
  3. Exportación de `modelo_optimizado.h5` y enriquecimiento de metadatos de trazabilidad en `/modelos_ia/`.
  4. Pausa de espera de 6 segundos y consulta HTTP a `GET http://backend:8000/health` para comprobar que el hilo observador del backend recargó la versión.
  5. Repite el ciclo completo utilizando el dataset público real de Valle del Cauca (GBIF + NASA POWER).
- **Limitación actual:** Requiere que el contenedor `backend` esté resoluble en red; no utiliza aserciones formales tipo `assert` con códigos de salida para integración continua.

### 4.2 Script `test_tuning_benchmark.py`
Archivo: [streamlit_app/test_tuning_benchmark.py](../streamlit_app/test_tuning_benchmark.py)
- **Alcance:** Mide y compara el tiempo de cómputo y el $R^2$ alcanzado entre:
  - Modo sin tuning (valores fijos de hiperparámetros).
  - Modo con tuning (búsqueda aleatoria de hiperparámetros + NAS).
- **Propósito:** Evaluar la factibilidad de activar la sintonización en demostraciones en vivo en clase versus reservarlo únicamente para reportes finales.

---

## 5. Vacíos de Testing y Verificaciones Pendientes

Para que el proyecto alcance un nivel de madurez técnica de grado de producción, se identifican las siguientes brechas que requieren intervención humana y desarrollo de pruebas formales:

1. **Implementación de Tests Unitarios en Backend:**  
   Configurar `pytest` y `httpx.AsyncClient` para probar de forma aislada y mockeada:
   - Registro, login y expiración de tokens JWT en `/api/auth/*`.
   - Control de acceso por roles (cliente bloqueado en endpoints `/api/admin/*`).
   - Algoritmo de validación espacial de radio geodésico (`check_point_in_region`).
2. **Implementación de Tests de Componentes en Frontend:**  
   Configurar Vitest con React Testing Library para validar:
   - Renderizado condicional de tarjetas métricas ante diferentes respuestas del optimizador.
   - Manejo de errores de conexión con el backend mediante `StatusBanner`.
   - Conversión y validación de geometrías GeoJSON en `MapSelectionCard`.
3. **Automatización de CI/CD:**  
   Definir un workflow de GitHub Actions que ejecute linting (`flake8`/`ruff`, `eslint`) y pruebas unitarias automáticas ante cada pull request hacia `main`.
