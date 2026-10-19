# Herramienta de Publicación Controlada a Confluence Cloud (REST API v2)

Este directorio contiene la herramienta automatizada para la publicación y sincronización de documentación técnica desde el repositorio hacia Atlassian Confluence Cloud, utilizando exclusivamente la **API REST v2 oficial**.

La herramienta opera en la rama de trabajo `docs/automatizacion-confluence` y publica de forma controlada una única página hija de prueba bajo la página raíz designada en el espacio documental **GDP**.

---

## 1. Arquitectura y Componentes

```
tools/docs/
├── requirements.txt         # Dependencias aisladas de la herramienta (requests>=2.31.0)
├── test_page.md             # Documento Markdown de prueba técnica (título, listas, tabla, código)
├── markdown_to_storage.py   # Conversor de Markdown a XHTML Storage Format con validación estricta
├── confluence_client.py     # Cliente HTTP seguro para Confluence API v2 (HTTP Basic para ambos modos)
├── publisher.py             # Publicador CLI (modos --check, --dry-run y --publish)
├── test_publisher.py        # Suite de 16 pruebas unitarias y validaciones de flujo local
├── .confluence_state.json   # Archivo de estado local (excluido de Git vía .gitignore)
└── README.md                # Guía técnica de uso y procedimientos
```

### Principios de Seguridad y Operación
1. **Aislamiento Total:** Dependencias propias e independientes de la aplicación central (FastAPI, Streamlit, etc.).
2. **Protección de Secretos:** Los tokens de API nunca se imprimen, nunca se registran en logs y nunca se guardan en archivos versionados. Si no se configuran variables de entorno, la terminal solicita el token con entrada oculta (`getpass`).
3. **HTTP Basic Authentication Exclusiva:** Según la [documentación oficial de Atlassian](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/), los API tokens personales de Atlassian se autentican mediante **HTTP Basic Authentication** (`base64(correo:token)`), tanto si son tokens sin ámbitos como con ámbitos. No deben confundirse con tokens de acceso OAuth 2.0 (Bearer).
4. **Resolución Dinámica de `spaceId`:** Confluence Cloud API v2 requiere el identificador numérico de espacio (`spaceId`), no la clave literal `GDP`. La herramienta consulta la página raíz (`2097153`) y extrae dinámicamente su `spaceId`.
5. **Validación Estricta de Markdown:** El conversor falla tempranamente ante sintaxis malformada o no soportada (HTML embebido, listas de tareas, fórmulas matemáticas, notas al pie, tablas inconsistentes o bloques de código sin cerrar), evitando publicar contenido mutilado silenciosamente.
6. **Protección contra Sobrescrituras Huérfanas:** Si en Confluence ya existe una página con el título objetivo pero no está confirmada en el estado local (`.confluence_state.json`), el publicador se detiene de inmediato para evitar sobrescrituras accidentales.
7. **Idempotencia y Versionado:** Compara el hash SHA-256 del contenido generado. Si no hay cambios, omite la actualización sin incrementar versión ni consumir llamadas innecesarias a la API.

---

## 2. Métodos de Autenticación con API Token Personal

La herramienta admite ambas variantes de API Token personal de Atlassian, utilizando siempre HTTP Basic con su correo electrónico:

### Modo A: API Token personal sin ámbitos (Unscoped — Predeterminado)
Token personal estándar creado desde la cuenta de Atlassian.
- **Autenticación:** HTTP Basic (`base64(correo:token)`).
- **Ruta de conexión:** Directa al sitio:
  ```
  https://unitru-team-hpj93f6y.atlassian.net/wiki/api/v2/
  ```

### Modo B: API Token personal con ámbitos (Scoped)
Token personal configurado con granular scopes / restricciones de ámbito.
- **Autenticación:** HTTP Basic (`base64(correo:token)`).
- **Ruta de conexión:** Oficial de Atlassian para tokens con ámbito:
  ```
  https://api.atlassian.com/ex/confluence/{cloudId}/wiki/api/v2/
  ```
- **Obtención del `cloudId`:**
  - **Detección Automática:** La herramienta consulta el endpoint público del sitio:
    ```
    https://unitru-team-hpj93f6y.atlassian.net/_edge/tenant_info
    ```
    El cual retorna el identificador: `11c5602c-78c2-4910-b6ad-b839e136bcaa`.
  - **Asignación Explícita:** Mediante el argumento `--cloud-id` o la variable `CONFLUENCE_CLOUD_ID`.

---

## 3. Instalación del Entorno en PowerShell

Abra su terminal PowerShell en la raíz del repositorio:

```powershell
# 1. Navegar a la carpeta de herramientas
cd tools/docs

# 2. Crear entorno virtual aislado (excluido en .gitignore)
python -m venv venv

# 3. Activar el entorno virtual
.\venv\Scripts\Activate.ps1

# 4. Instalar las dependencias de documentación
pip install -r requirements.txt

# 5. Ejecutar la suite de pruebas unitarias
python test_publisher.py
```

---

## 4. Configuración Segura de Variables de Entorno

Puede configurar sus credenciales temporalmente en la sesión de PowerShell para no tener que ingresarlas en cada comando:

### Opción 1: API Token personal sin ámbitos (Directo al sitio)
```powershell
$env:CONFLUENCE_EMAIL = "su-correo@universidad.edu.pe"
$secureToken = Read-Host "Ingrese API Token personal de Atlassian" -AsSecureString
$env:CONFLUENCE_API_TOKEN = [System.Net.NetworkCredential]::new("", $secureToken).Password
$env:CONFLUENCE_TOKEN_TYPE = "unscoped"
```

### Opción 2: API Token personal con ámbitos (Vía api.atlassian.com con cloudId)
```powershell
$env:CONFLUENCE_EMAIL = "su-correo@universidad.edu.pe"
$secureToken = Read-Host "Ingrese Scoped API Token personal" -AsSecureString
$env:CONFLUENCE_API_TOKEN = [System.Net.NetworkCredential]::new("", $secureToken).Password
$env:CONFLUENCE_TOKEN_TYPE = "scoped"
$env:CONFLUENCE_CLOUD_ID = "11c5602c-78c2-4910-b6ad-b839e136bcaa"
```

> **Nota de Seguridad:** Si decide no definir las variables de entorno, el publicador le solicitará de forma interactiva el correo y el token por terminal (con máscara de caracteres oculta para el token vía `getpass`).

---

## 5. Instrucciones de Ejecución Paso a Paso

### Paso 1: Comprobación de Conexión y Resolución (`--check`)
Valida la conectividad con el sitio de Atlassian, la autenticación HTTP Basic y la lectura de la página raíz (`ID: 2097153`) sin alterar ningún documento ni crear páginas:

```powershell
python publisher.py --check
```

**Salida esperada:**
```text
======================================================================
  PUBLICADOR DE DOCUMENTACIÓN A CONFLUENCE CLOUD (API v2)
======================================================================
Sitio objetivo       : https://unitru-team-hpj93f6y.atlassian.net
Tipo de autenticación: API Token Personal (UNSCOPED) con HTTP Basic Auth
Ruta base API v2     : https://unitru-team-hpj93f6y.atlassian.net/wiki/api/v2
Usuario autenticado  : su-correo@universidad.edu.pe
Página raíz (padre)  : ID 2097153
Título objetivo      : 'Prueba de publicación automática — GDP'
----------------------------------------------------------------------
[CONEXIÓN] Consultando metadatos de la página raíz ID 2097153...
[OK] Raíz verificada : 'Documentación Técnica - GDP' (ID: 2097153, Versión: 1)
[OK] Space ID resuelto: 54321 (Espacio documental 'GDP')
----------------------------------------------------------------------
[VERIFICACIÓN EXITOSA] Conexión establecida, autenticación válida y spaceId numérico resuelto.
```

---

### Paso 2: Simulación en Seco (`--dry-run`)
Convierte `test_page.md` a XHTML, valida la estructura XML y la ausencia de sintaxis no soportada, consulta si existe la página hija o el estado previo, y reporta la acción planificada sin modificar Confluence:

```powershell
python publisher.py --dry-run
```

**Salida esperada (primera ejecución):**
```text
[CONVERSIÓN] Procesando Markdown (2751 caracteres)...
[OK] XML generado validado: 3499 caracteres XHTML | SHA-256: 9ea2f759cd2f...
[BÚSQUEDA] Verificando si existe previamente una página titulada 'Prueba de publicación automática — GDP'...
----------------------------------------------------------------------
[DRY-RUN] ACCIÓN PLANIFICADA: CREACIÓN DE NUEVA PÁGINA HIJA
  - Título            : 'Prueba de publicación automática — GDP'
  - Página padre (ID) : 2097153
  - Espacio (spaceId) : <spaceId_numerico>
  - Hash del contenido: 9ea2f759cd2f...
Simulación concluida sin modificar Confluence.
```

---

### Paso 3: Publicación Explícita (`--publish`)
Ejecuta la creación real de la página en Confluence y guarda el estado en `.confluence_state.json`:

```powershell
python publisher.py --publish
```

**Salida esperada:**
```text
[PUBLICACIÓN] Creando nueva página hija bajo la raíz ID 2097153...
----------------------------------------------------------------------
[ÉXITO] Página de prueba creada satisfactoriamente!
  - ID asignado       : 3145729
  - Título            : 'Prueba de publicación automática — GDP'
  - Versión           : 1
  - Página padre (ID) : 2097153
  - Espacio (spaceId) : <spaceId_numerico>
  - Estado local      : Guardado en .confluence_state.json
```

---

## 6. Verificación de Idempotencia y Conservación de ID

Uno de los requisitos clave es comprobar que las ejecuciones posteriores no duplican páginas y mantienen exactamente el mismo ID:

### Comprobación A: Publicación sin cambios (Omitida / Idempotente)
Si ejecuta nuevamente el publicador sin modificar `test_page.md`:

```powershell
python publisher.py --publish
```

**Salida esperada:**
```text
[ESTADO LOCAL] Página previamente registrada con ID 3145729 (Versión previa: 1).
----------------------------------------------------------------------
[OMITIDO] El contenido generado es IDÉNTICO al último publicado (SHA-256: 9ea2f759cd2f...).
Página ID 3145729 se mantiene en versión 1. No se realizaron llamadas de escritura.
```

### Comprobación B: Actualización con cambios (Mismo ID, Nueva Versión)
Si edita `test_page.md` (por ejemplo, agregando una línea de texto) y vuelve a publicar:

```powershell
python publisher.py --publish
```

**Salida esperada:**
```text
[ESTADO LOCAL] Página previamente registrada con ID 3145729 (Versión previa: 1).
[PUBLICACIÓN] Actualizando página ID 3145729 de v1 a v2...
----------------------------------------------------------------------
[ÉXITO] Página ID 3145729 actualizada correctamente a versión 2.
Estado local persistido en .confluence_state.json.
```

### Comprobación C: Inspección del Archivo de Estado
Puede inspeccionar el estado persistido localmente con PowerShell:

```powershell
Get-Content .confluence_state.json | ConvertFrom-Json | Format-List
```

El archivo muestra el `page_id` preservado, el `space_id` numérico, el `root_id` padre y el número de versión actual.
