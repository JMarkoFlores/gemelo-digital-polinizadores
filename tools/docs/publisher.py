"""Publicador mínimo y seguro de documentación hacia Confluence Cloud.

Gestiona la publicación y actualización controlada de una única página hija de prueba
en Confluence Cloud REST API v2, con soporte para:
  - Modo verificación de conexión (--check)
  - Modo simulación sin modificaciones (--dry-run)
  - Modo publicación explícita (--publish)
  - Autenticación dual (Basic Auth unscoped / Bearer OAuth scoped)
  - Resolución dinámica de spaceId numérico a partir de la página raíz
  - Control de estado local (.confluence_state.json) y detección de cambios (hash SHA-256)
  - Protección estricta contra sobrescritura de páginas huérfanas o no confirmadas
  - Cero exposición de secretos o cabeceras de autorización en consola o archivos
"""

from __future__ import annotations

import argparse
import datetime
import getpass
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Añadir directorio actual al path para importar módulos hermanos
tools_dir = Path(__file__).resolve().parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from confluence_client import ConfluenceAPIError, ConfluenceClient
from markdown_to_storage import markdown_to_storage


DEFAULT_SITE = "unitru-team-hpj93f6y.atlassian.net"
DEFAULT_ROOT_ID = "2097153"
DEFAULT_TEST_TITLE = "Prueba de publicación automática — GDP"
DEFAULT_FILE = tools_dir / "test_page.md"
DEFAULT_STATE_FILE = tools_dir / ".confluence_state.json"


def load_state(state_path: Path) -> Dict[str, Any]:
    """Carga el archivo de estado local si existe."""
    if not state_path.is_file():
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as err:
        print(f"[ADVERTENCIA] No se pudo leer el archivo de estado local ({state_path}): {err}")
        return {}


def save_state(state_path: Path, state_data: Dict[str, Any]) -> None:
    """Guarda atómicamente el estado local en disco."""
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = state_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
        temp_file.replace(state_path)
    except Exception as err:
        print(f"[ERROR] No se pudo guardar el archivo de estado ({state_path}): {err}", file=sys.stderr)


def calculate_hash(content: str) -> str:
    """Calcula el hash SHA-256 de una cadena de texto para comparación de contenido."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def obtain_credentials(args: argparse.Namespace) -> tuple[Optional[str], str, str, Optional[str]]:
    """Obtiene de forma segura las credenciales desde argumentos, variables de entorno o terminal oculta.

    Nunca imprime ni guarda el token.
    """
    token_type = args.token_type or os.environ.get("CONFLUENCE_TOKEN_TYPE", "unscoped").lower()
    email = args.email or os.environ.get("CONFLUENCE_EMAIL")
    token = args.token or os.environ.get("CONFLUENCE_API_TOKEN")
    cloud_id = args.cloud_id or os.environ.get("CONFLUENCE_CLOUD_ID")

    # Solicitar email si falta (requerido para Basic Auth en ambos modos)
    if not email:
        if sys.stdin.isatty():
            print("[AUTENTICACIÓN] Se requiere el correo de la cuenta Atlassian para la autenticación HTTP Basic con API Token.")
            email = input("Correo electrónico: ").strip()
        else:
            print(
                "[ERROR DE CONFIGURACIÓN] Falta el correo electrónico. "
                "Defina la variable de entorno CONFLUENCE_EMAIL o use el argumento --email.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Solicitar token si falta (entrada oculta con getpass)
    if not token:
        if sys.stdin.isatty():
            print("[AUTENTICACIÓN] Ingrese el API Token personal de Atlassian (la entrada se mantendrá oculta):")
            token = getpass.getpass("API Token: ").strip()
        else:
            print(
                "[ERROR DE CONFIGURACIÓN] Falta el API Token de Confluence. "
                "Defina la variable de entorno CONFLUENCE_API_TOKEN o ejecute en una terminal interactiva.",
                file=sys.stderr,
            )
            sys.exit(1)

    if not token:
        print("[ERROR] El token de API no puede estar vacío.", file=sys.stderr)
        sys.exit(1)

    return email, token, token_type, cloud_id


def build_parser() -> argparse.ArgumentParser:
    """Configura las opciones de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Publicador controlado de documentación técnica hacia Confluence Cloud REST API v2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--check",
        action="store_true",
        help="Comprueba la conectividad, autenticación y resolución del spaceId de la raíz sin modificar nada.",
    )
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la conversión, consulta la raíz y páginas existentes, e informa la acción planificada sin publicar.",
    )
    mode_group.add_argument(
        "--publish",
        action="store_true",
        help="Ejecuta la publicación real (crea la página hija o actualiza su versión si hubo cambios).",
    )

    parser.add_argument(
        "--site",
        default=DEFAULT_SITE,
        help=f"Dominio de Confluence Cloud (predeterminado: {DEFAULT_SITE})",
    )
    parser.add_argument(
        "--root-id",
        default=DEFAULT_ROOT_ID,
        help=f"ID numérico de la página raíz padre en Confluence (predeterminado: {DEFAULT_ROOT_ID})",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FILE,
        help=f"Ruta al archivo Markdown a publicar (predeterminado: {DEFAULT_FILE.name})",
    )
    parser.add_argument(
        "--title",
        default=DEFAULT_TEST_TITLE,
        help=f"Título de la página en Confluence (predeterminado: '{DEFAULT_TEST_TITLE}')",
    )
    parser.add_argument(
        "--token-type",
        choices=["unscoped", "scoped"],
        default=None,
        help="Tipo de API token personal: 'unscoped' (sitio directo) o 'scoped' (api.atlassian.com). Ambos usan HTTP Basic con correo.",
    )
    parser.add_argument(
        "--cloud-id",
        default=None,
        help="Atlassian Cloud ID (requerido únicamente para tokens 'scoped'; se detecta automáticamente si se omite)",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Correo de la cuenta Atlassian (puede suministrarse vía CONFLUENCE_EMAIL)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="API Token personal de Atlassian (se recomienda usar variable de entorno CONFLUENCE_API_TOKEN o entrada oculta)",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help=f"Ruta al archivo de estado local (predeterminado: {DEFAULT_STATE_FILE.name})",
    )

    return parser


def main() -> None:
    """Punto de entrada principal del publicador."""
    parser = build_parser()
    args = parser.parse_args()

    # 1. Obtener credenciales de forma segura
    email, token, token_type, cloud_id = obtain_credentials(args)

    # 2. Inicializar cliente Confluence
    try:
        client = ConfluenceClient(
            site_domain=args.site,
            email=email,
            api_token=token,
            token_type=token_type,
            cloud_id=cloud_id,
        )
    except Exception as err:
        print(f"[ERROR DE INICIALIZACIÓN] {err}", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print("  PUBLICADOR DE DOCUMENTACIÓN A CONFLUENCE CLOUD (API v2)")
    print("=" * 70)
    print(f"Sitio objetivo       : https://{args.site}")
    print(f"Tipo de autenticación: API Token Personal ({token_type.upper()}) con HTTP Basic Auth")
    print(f"Ruta base API v2     : {client.base_url}")
    print(f"Usuario autenticado  : {email}")
    print(f"Página raíz (padre)  : ID {args.root_id}")
    print(f"Título objetivo      : '{args.title}'")
    print(f"Archivo Markdown     : {args.file}")
    print(f"Archivo de estado    : {args.state_file}")
    print("-" * 70)

    # 3. Consultar la página raíz para obtener el spaceId numérico
    print(f"[CONEXIÓN] Consultando metadatos de la página raíz ID {args.root_id}...")
    try:
        root_data = client.get_page(str(args.root_id))
    except ConfluenceAPIError as err:
        print(f"[ERROR DE CONEXIÓN / AUTENTICACIÓN] No fue posible consultar la página raíz: {err}", file=sys.stderr)
        sys.exit(1)

    root_title = root_data.get("title", "<sin título>")
    space_id = str(root_data.get("spaceId", ""))
    root_version = root_data.get("version", {}).get("number", "?")

    if not space_id:
        print(
            f"[ERROR] La respuesta de Confluence para la página {args.root_id} no incluyó 'spaceId'. "
            "Verifique los permisos de lectura de la cuenta sobre el espacio.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[OK] Raíz verificada : '{root_title}' (ID: {args.root_id}, Versión: {root_version})")
    print(f"[OK] Space ID resuelto: {space_id} (Espacio documental 'GDP')")

    # Si es modo check, salimos airosos aquí
    if args.check:
        print("-" * 70)
        print("[VERIFICACIÓN EXITOSA] Conexión establecida, autenticación válida y spaceId numérico resuelto.")
        print("El entorno está listo para simulación (--dry-run) o publicación (--publish).")
        print("=" * 70)
        sys.exit(0)

    # 4. Validar existencia del archivo Markdown y convertir a Confluence Storage Format
    if not args.file.is_file():
        print(f"[ERROR] No se encontró el archivo Markdown en: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            md_content = f.read()
    except Exception as err:
        print(f"[ERROR] No se pudo leer el archivo {args.file}: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"[CONVERSIÓN] Procesando Markdown ({len(md_content)} caracteres)...")
    try:
        extracted_title, storage_xml = markdown_to_storage(md_content)
    except Exception as err:
        print(f"[ERROR DE CONVERSIÓN] Falló la conversión a Confluence Storage Format: {err}", file=sys.stderr)
        sys.exit(1)

    content_hash = calculate_hash(storage_xml)
    page_title = args.title or extracted_title or DEFAULT_TEST_TITLE
    print(f"[OK] XML generado validado: {len(storage_xml)} caracteres XHTML | SHA-256: {content_hash[:12]}...")

    # 5. Cargar estado local para determinar propiedad
    state = load_state(args.state_file)
    known_page_id = state.get("page_id")
    known_space_id = state.get("space_id")
    stored_hash = state.get("content_sha256")
    last_version = state.get("version", 0)

    # Regla estricta de seguridad: Nunca sobrescribir la raíz
    if known_page_id and str(known_page_id) == str(args.root_id):
        print("[ERROR FATAL DE SEGURIDAD] El ID registrado en el estado coincide con la página raíz. Abortando.", file=sys.stderr)
        sys.exit(1)

    # 6. Evaluar escenario de publicación: Actualización vs Creación
    if known_page_id:
        print(f"[ESTADO LOCAL] Página previamente registrada con ID {known_page_id} (Versión previa: {last_version}).")
        # Verificar existencia en Confluence
        try:
            current_remote = client.get_page(str(known_page_id))
        except ConfluenceAPIError as err:
            print(f"[ERROR] La página registrada ID {known_page_id} no pudo consultarse en Confluence: {err}", file=sys.stderr)
            sys.exit(1)

        remote_version = current_remote.get("version", {}).get("number", 1)
        next_version = remote_version + 1

        # Comprobar si el contenido ha cambiado
        if stored_hash == content_hash:
            print("-" * 70)
            print(f"[OMITIDO] El contenido generado es IDÉNTICO al último publicado (SHA-256: {content_hash[:12]}...).")
            print(f"Página ID {known_page_id} se mantiene en versión {remote_version}. No se realizaron llamadas de escritura.")
            print("=" * 70)
            sys.exit(0)

        # Contenido difiere -> Plan de actualización
        if args.dry_run:
            print("-" * 70)
            print("[DRY-RUN] ACCIÓN PLANIFICADA: ACTUALIZACIÓN DE PÁGINA EXISTENTE")
            print(f"  - ID de la página      : {known_page_id}")
            print(f"  - Título               : '{page_title}'")
            print(f"  - Versión actual       : {remote_version}")
            print(f"  - Siguiente versión    : {next_version}")
            print(f"  - Hash previo          : {stored_hash[:12] if stored_hash else 'ninguno'}...")
            print(f"  - Nuevo hash           : {content_hash[:12]}...")
            print("Simulación concluida sin modificar Confluence.")
            print("=" * 70)
            sys.exit(0)

        # Publicación real: Actualizar
        print(f"[PUBLICACIÓN] Actualizando página ID {known_page_id} de v{remote_version} a v{next_version}...")
        try:
            update_res = client.update_page(
                page_id=str(known_page_id),
                space_id=space_id,
                title=page_title,
                parent_id=str(args.root_id),
                storage_xml=storage_xml,
                next_version=next_version,
                version_message=f"Actualización automática de prueba — {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
            )
        except ConfluenceAPIError as err:
            print(f"[ERROR AL ACTUALIZAR] {err}", file=sys.stderr)
            print("No se realizaron reintentos automáticos para evitar inconsistencias.", file=sys.stderr)
            sys.exit(1)

        new_version = update_res.get("version", {}).get("number", next_version)
        state_data = {
            "page_id": str(known_page_id),
            "space_id": space_id,
            "root_id": str(args.root_id),
            "title": page_title,
            "content_sha256": content_hash,
            "version": new_version,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        save_state(args.state_file, state_data)
        print("-" * 70)
        print(f"[ÉXITO] Página ID {known_page_id} actualizada correctamente a versión {new_version}.")
        print(f"Estado local persistido en {args.state_file}.")
        print("=" * 70)
        sys.exit(0)

    else:
        # No hay registro local. Buscar si ya existe una página con el mismo título en el espacio.
        print(f"[BÚSQUEDA] Verificando si existe previamente una página titulada '{page_title}' en spaceId {space_id}...")
        try:
            existing_pages = client.search_pages_by_title(title=page_title, space_id=space_id)
        except ConfluenceAPIError as err:
            print(f"[ERROR] No fue posible verificar la existencia de páginas previas: {err}", file=sys.stderr)
            sys.exit(1)

        if existing_pages:
            found = existing_pages[0]
            found_id = found.get("id")
            print("!" * 70)
            print("[ALERTA DE SEGURIDAD - PÁGINA HUÉRFANA O SIN PROPIEDAD CONFIRMADA]")
            print(f"Se encontró una página existente con el título '{page_title}' (ID: {found_id})")
            print(f"en el espacio {space_id}, pero NO está registrada en el estado local ({args.state_file.name}).")
            print("Para proteger la documentación existente de sobrescrituras no deseadas:")
            print("  1. Si desea que este publicador gestione esa página, registre manualmente su ID:")
            print(f'     echo \'{{"page_id": "{found_id}", "space_id": "{space_id}", "root_id": "{args.root_id}"}}\' > {args.state_file}')
            print("  2. O elimínela manualmente de Confluence si fue creada por error.")
            print("La operación se detiene sin realizar cambios.")
            print("!" * 70)
            sys.exit(1)

        # No existe página con ese título -> Plan de creación
        if args.dry_run:
            print("-" * 70)
            print("[DRY-RUN] ACCIÓN PLANIFICADA: CREACIÓN DE NUEVA PÁGINA HIJA")
            print(f"  - Título            : '{page_title}'")
            print(f"  - Página padre (ID) : {args.root_id} ('{root_title}')")
            print(f"  - Espacio (spaceId) : {space_id}")
            print(f"  - Hash del contenido: {content_hash[:12]}...")
            print("Simulación concluida sin modificar Confluence.")
            print("=" * 70)
            sys.exit(0)

        # Publicación real: Crear página
        print(f"[PUBLICACIÓN] Creando nueva página hija bajo la raíz ID {args.root_id}...")
        try:
            create_res = client.create_page(
                space_id=space_id,
                title=page_title,
                parent_id=str(args.root_id),
                storage_xml=storage_xml,
            )
        except ConfluenceAPIError as err:
            print(f"[ERROR AL CREAR PÁGINA] {err}", file=sys.stderr)
            print("No se reintenta automáticamente para no crear páginas duplicadas.", file=sys.stderr)
            sys.exit(1)

        new_page_id = str(create_res.get("id"))
        created_version = create_res.get("version", {}).get("number", 1)

        state_data = {
            "page_id": new_page_id,
            "space_id": space_id,
            "root_id": str(args.root_id),
            "title": page_title,
            "content_sha256": content_hash,
            "version": created_version,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        save_state(args.state_file, state_data)

        print("-" * 70)
        print(f"[ÉXITO] Página de prueba creada satisfactoriamente!")
        print(f"  - ID asignado       : {new_page_id}")
        print(f"  - Título            : '{page_title}'")
        print(f"  - Versión           : {created_version}")
        print(f"  - Página padre (ID) : {args.root_id}")
        print(f"  - Espacio (spaceId) : {space_id}")
        print(f"  - Estado local      : Guardado en {args.state_file}")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
