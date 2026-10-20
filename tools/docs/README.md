# Herramienta de Publicación Controlada a Confluence Cloud (REST API v2)

Este directorio contiene el herramental automatizado para la validación, renderizado local de activos visuales, resolución de enlaces y sincronización de documentación técnica desde el repositorio `gemelo-digital-polinizadores` hacia Atlassian Confluence Cloud, utilizando exclusivamente la **API REST v2 oficial**.

La herramienta opera en la rama de trabajo `docs/automatizacion-confluence` bajo el espacio documental **GDP** (`spaceId: 2031619`), subordinando todas las páginas como hijas de la página raíz **2097153** y aislando la página de prueba reservada **2162690**.

---

## 1. Arquitectura y Componentes de `tools/docs/`

```
tools/docs/
├── docs_manifest.json       # Manifiesto canónico versionable con los 12 documentos reales de docs/
├── asset_renderer.py        # Renderizado local 100% offline (Mermaid y KaTeX a PNG) y conversión Unicode
├── link_resolver.py         # Resolutor seguro de enlaces hacia GitHub (código) y Confluence (páginas/anclas)
├── markdown_to_storage.py   # Conversor a XHTML Storage Format con validación estricta y firma de identidad
├── confluence_client.py     # Cliente HTTP seguro para Confluence API v2 (HTTP Basic para ambos modos)
├── publisher.py             # Publicador y validador CLI (modos individual y multi-documento)
├── test_publisher.py        # Suite de 33 pruebas unitarias y de integración simulada (100% aprobadas)
├── requirements.txt         # Dependencias Python aisladas de la herramienta (requests, pillow, matplotlib)
├── package.json             # Dependencias npm locales aisladas (mermaid, katex)
├── test_page.md             # Documento de prueba técnica aislado
├── .confluence_state.json   # Estado local de la página de prueba aislada 2162690 (ignorado en Git)
├── .gitignore               # Exclusiones locales de venv, node_modules y activos renderizados
└── README.md                # Guía técnica de uso y procedimientos
```

### Principios de Seguridad y Operación
1. **Aislamiento Total de Dependencias:** Las dependencias de documentación (`tools/docs/requirements.txt` y `tools/docs/package.json`) son independientes del software principal (FastAPI, React, Streamlit, Docker).
2. **Protección Estricta de Secretos:** Los tokens de API nunca se imprimen, nunca se registran en logs y nunca se guardan en archivos versionados.
3. **Autenticación HTTP Basic Oficial:** Conforme a la documentación oficial de Atlassian, se utiliza HTTP Basic con correo y API Token personal (`unscoped` directo al sitio, o `scoped` hacia `api.atlassian.com`).
4. **Protección de la Página Raíz y Página de Prueba:** La página raíz `2097153` y la página de prueba `2162690` están protegidas contra sobrescritura o reasignación a documentos reales.
5. **Preservación Intacta de Archivos Fuente:** Los 12 archivos Markdown en `docs/` se mantienen 100% intactos en su contenido técnico original.
6. **Renderizado Local 100% Offline (Sin Servicios Externos ni Macros No Confirmadas):**
   - **Diagramas Mermaid:** Renderizados localmente a PNG mediante Headless Chrome y la biblioteca oficial `node_modules/mermaid` (v12.2.0).
   - **Fórmulas Matemáticas Complejas ($$):** Renderizadas localmente a PNG con KaTeX (v0.19.0) y Headless Chrome.
   - **Recorte Inteligente:** Márgenes blancos eliminados automáticamente mediante Pillow (`ImageChops.difference`).
7. **Accesibilidad y Transparencia Técnica:** Cada imagen insertada en Confluence incluye:
   - Texto alternativo descriptivo en `<ac:image ac:alt="...">`.
   - Macro expandible `<ac:structured-macro ac:name="expand">` conteniendo el código fuente original (Mermaid o LaTeX).
8. **Conversión Semántica Rigurosa a Unicode:** Las expresiones matemáticas simples en línea ($...$) se convierten a texto plano Unicode preservando su significado exacto mediante reglas semánticas explícitas. Si una expresión contiene comandos desconocidos, se produce un error explícito en lugar de eliminar delimitadores ciegamente.
9. **Detección de Conflicto Remoto con Huella (`remote_body_hash`):**
   - Al publicar, se guarda el hash SHA-256 del contenido devuelto por la API de Confluence.
   - Antes de actualizar, se compara la versión remota y el hash del cuerpo. Si la página fue editada externamente o por un usuario en Confluence, la actualización se **bloquea inmediatamente** y se reporta el conflicto.
10. **Identidad de Documento Verificable y Recuperación ante Interrupciones:**
    - Cada página incluye una firma de identidad máquina:
      `<!-- confluence-doc-identity: slug={slug}; space_id={space_id}; parent_id={parent_id} -->`
      `<p style="display:none">confluence-doc-identity:slug={slug};space_id={space_id};parent_id={parent_id}</p>`
    - Si la creación de una página fue interrumpida antes de registrar su ID en el manifiesto, el sistema busca páginas con ese título y verifica la firma en su contenido. Si coincide, recupera el ID de forma segura; si el título coincide pero no tiene la firma o hay ambigüedad, **se detiene sin recrear**.

---

## 2. Matriz de Compatibilidad de los 12 Documentos (100% Compatible)

Tras implementar el renderizado local de Mermaid y LaTeX a PNG y la conversión semántica a Unicode, **los 12 documentos de docs/ son plenamente compatibles y están listos para publicación**:

| Documento | Título Oficial en Confluence | Estado | Enlaces Código | Enlaces Doc | Activos PNG Generados | Validación XML Storage |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `docs/index.md` | Documentación Técnica: Gemelos Digitales de Paisajes Agrícolas y Polinizadores | **LISTO** | 3 (GitHub) | 11 (Confluence) | 0 | VÁLIDO (10.4 KB) |
| `docs/arquitectura.md` | Arquitectura de Software y Sistemas | **LISTO** | 14 (GitHub) | 0 | 1 (`arquitectura-mermaid-1.png`) | VÁLIDO (13.6 KB) |
| `docs/instalacion.md` | Guía de Instalación y Despliegue Local | **LISTO** | 13 (GitHub) | 1 (Confluence) | 0 | VÁLIDO (12.6 KB) |
| `docs/configuracion.md` | Guía de Configuración del Sistema | **LISTO** | 14 (GitHub) | 0 | 0 | VÁLIDO (13.5 KB) |
| `docs/api.md` | Especificación y Catálogo de la API REST | **LISTO** | 44 (GitHub) | 0 | 0 (Unicode: $\ge$, etc.) | VÁLIDO (28.8 KB) |
| `docs/modelo-de-datos.md` | Modelo de Datos y Persistencia Relacional | **LISTO** | 9 (GitHub) | 0 | 1 (`modelo-de-datos-mermaid-1.png`) | VÁLIDO (12.9 KB) |
| `docs/pipeline-cientifico.md`| Pipeline Científico, Modelado y Optimización Multiobjetivo | **LISTO** | 17 (GitHub) | 0 | 10 (1 Mermaid + 9 LaTeX Math) | VÁLIDO (22.4 KB) |
| `docs/pruebas.md` | Inventario y Estado de Pruebas de Software y Validación Estadística | **LISTO** | 16 (GitHub) | 0 | 1 (`pruebas-math-1.png`) | VÁLIDO (12.9 KB) |
| `docs/reproducibilidad.md` | Guía y Requisitos para la Reproducibilidad Científica | **LISTO** | 23 (GitHub) | 0 | 0 | VÁLIDO (12.2 KB) |
| `docs/limitaciones.md` | Limitaciones Técnicas, Científicas y Verificaciones Pendientes | **LISTO** | 16 (GitHub) | 0 | 0 (Unicode: $g_1(X) \le 0$, etc.) | VÁLIDO (10.0 KB) |
| `docs/inventario.md` | Inventario Técnico del Repositorio: Gemelos Digitales 02 | **LISTO** | 111 (GitHub) | 0 | 0 (Unicode: $\sum \le 100\%$, etc.) | VÁLIDO (56.7 KB) |
| `docs/pendientes.md` | Registro de Pendientes, Brechas y Verificaciones Técnicas | **LISTO** | 40 (GitHub) | 0 | 0 | VÁLIDO (21.9 KB) |
| **TOTALES** | **12 de 12 documentos listos para publicación** | **100%** | **320 resueltos** | **12 resueltos** | **13 PNGs generados** | **100% Válido** |

---

## 3. Resolución de Enlaces y Verificación de Anclajes

### Enlaces a Código Fuente
Todos los enlaces relativos hacia el repositorio (`../backend/app/...`, `../docker-compose.yml#L10-L20`) se reescriben como URLs canónicas e inmutables de GitHub:
`https://github.com/JMarkoFlores/gemelo-digital-polinizadores/blob/0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02/{ruta_archivo}#{ancla_linea}`

### Enlaces Inter-Documentales
- **Fase 1 (Antes de asignar IDs):** Se transforman en macros nativas `<ac:link><ri:page ri:content-title="{titulo_destino}"/>[<ac:link-anchor>{ancla}</ac:link-anchor>]<ac:plain-text-link-body><![CDATA[{texto}]]></ac:plain-text-link-body></ac:link>`. Confluence Cloud resuelve el título y la navegación dentro del espacio.
- **Fase 2 (Tras obtener IDs de página):** El manifiesto almacena los `page_id` asignados. Confluence Cloud API v2 normaliza y preserva los enlaces automáticamente mediante la macro nativa sin romper referencias relativas.
- **Verificación de Anclajes:** Las anclas referenciadas se auditan para confirmar que existan como encabezados válidos en el documento destino.

---

## 4. Instalación de Dependencias

### Requisitos Previos
- Python 3.11+
- Node.js 20+ y npm (para Mermaid y KaTeX locales)
- Google Chrome o Microsoft Edge instalado en el sistema

### Procedimiento en PowerShell
```powershell
# 1. Navegar a la carpeta de herramientas
cd tools/docs

# 2. Instalar dependencias npm locales (Mermaid y KaTeX)
npm install

# 3. Crear y activar entorno virtual Python
python -m venv venv
.\venv\Scripts\Activate.ps1

# 4. Instalar dependencias Python (requests, pillow, matplotlib)
pip install -r requirements.txt
```

---

## 5. Ejecución de Pruebas Automatizadas

La suite incluye **41 pruebas unitarias y de integración simulada**:
- Modos de autenticación HTTP Basic con API Token personal (unscoped y scoped).
- Renderizado local de Mermaid y KaTeX a PNG con recorte Pillow.
- Conversión semántica de expresiones matemáticas a Unicode y manejo de errores.
- Generación de estructura XHTML accesible (`<ac:image>` + `<ac:structured-macro ac:name="expand">`).
- Detección y bloqueo ante conflictos remotos (`remote_body_hash` y versiones divergentes).
- Recuperación segura de páginas creadas tras interrupciones de red mediante firma de identidad.
- Bloqueo y detención ante páginas huérfanas o títulos ambiguos.
- Operaciones de escritura de `--publish --multi` (creación de páginas y subida de adjuntos).
- Ausencia total de escrituras en `--check --multi` y `--dry-run --multi`.
- Idempotencia: repetición sin cambios no duplica páginas ni recarga adjuntos idénticos.
- Sincronización de adjuntos por contenido SHA-256 vs registro de última subida exitosa (`published_sha256`).
- Omisión de adjuntos existentes con contenido comprobado idéntico.
- Actualización de adjuntos existentes vía endpoint oficial (`POST /wiki/rest/api/content/{page_id}/child/attachment/{attachment_id}/data`).
- Actualización de adjuntos cuando la imagen cambia localmente pero el cuerpo de la página se mantiene sin cambios.
- Detección e informe ante modificaciones remotas inesperadas o información insuficiente de comparación.
- Resiliencia y reanudación segura tras fallos en la subida de adjuntos sin duplicar páginas.
- Persistencia inmediata de IDs y hashes de publicación en el manifiesto ante fallos parciales.
- Validación integral de los 12 documentos reales.

```powershell
python -m unittest test_publisher.py
```
**Resultado comprobado:**
```text
Ran 41 tests in 36.338s
OK
```

---

## 6. Comandos Exactos para Validación, Simulación y Publicación

### Paso 1: Validación Local Integral Offline (`--validate-docs`)
Valida la existencia, convierte a Confluence Storage Format, renderiza los 13 activos visuales a PNG, audita los 332 enlaces y valida el XML resultante con `ElementTree` sin red ni credenciales:
```powershell
python publisher.py --validate-docs
```

### Paso 2: Configuración Segura de Credenciales (Sesión Actual)
```powershell
$env:CONFLUENCE_EMAIL = "su-correo@universidad.edu.pe"
$secureToken = Read-Host "Ingrese API Token personal de Atlassian" -AsSecureString
$env:CONFLUENCE_API_TOKEN = [System.Net.NetworkCredential]::new("", $secureToken).Password
$env:CONFLUENCE_TOKEN_TYPE = "unscoped"
```

### Paso 3: Comprobación Remota Multi-Documento (`--check --multi`)
Verifica la conexión con Confluence Cloud, valida que la raíz `2097153` pertenezca al `spaceId: 2031619`, confirma que la página de prueba `2162690` esté protegida y audita el estado de cada una de las 12 páginas (sin escrituras):
```powershell
python publisher.py --check --multi
```

### Paso 4: Simulación en Seco Multi-Documento (`--dry-run --multi`)
Ejecuta la validación previa de los 12 documentos y muestra el plan de creación de páginas y subida de adjuntos sin realizar ninguna llamada de escritura:
```powershell
python publisher.py --dry-run --multi
```

### Paso 5: Publicación Real Multi-Documento (`--publish --multi`)
Ejecuta la sincronización completa en Confluence Cloud:
1. Valida los 12 documentos y sus recursos localmente antes de escribir.
2. Crea las páginas bajo la raíz `2097153` en el espacio `2031619`.
3. Sube los 13 archivos PNG correspondientes a sus páginas.
4. Resuelve los enlaces inter-documentales a macros nativas `<ac:link>` y comprueba el XML final.
5. Guarda cada ID obtenido inmediatamente en `docs_manifest.json` para garantizar resiliencia.
6. Registra versiones, hashes locales y huellas remotas (`remote_body_hash`).
7. Muestra el resumen tabular final y concluye con código `0` si todo está sincronizado o código `1` si queda incompleto.
```powershell
python publisher.py --publish --multi
```

### Paso 6: Modo Prueba Individual Preservado (`--test`)
Permite continuar validando la página de prueba aislada `2162690` (`test_page.md`):
```powershell
python publisher.py --check --test
python publisher.py --dry-run --test
```
