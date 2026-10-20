"""Publicador controlado y seguro de documentación técnica hacia Confluence Cloud.

Soporta dos modalidades de operación:
1. Modo Prueba Individual (--test / test_page.md):
   Gestiona la página de prueba aislada (ID 2162690) en el espacio GDP sin tocar
   ni reutilizar dicha página para documentos reales.
2. Modo Multi-Documento (--manifest / docs_manifest.json):
   Gestiona los 12 documentos reales de docs/ bajo la raíz existente (ID 2097153, spaceId 2031619).
   - Validación local offline (--validate-docs): compatibilidad estricta y resolución de enlaces.
   - Comprobación de destino remoto (--check): verifica espacio, padre y correspondencia,
     detecta cambios remotos y protege contra adopción de páginas huérfanas.
   - Simulación en seco (--dry-run): muestra la planificación de creación/actualización/bloqueo.
   - Bloqueo estricto de escrituras en etapa de validación.
   - Resiliencia ante fallos parciales: guarda el manifiesto de forma atómica tras cada operación.
"""

from __future__ import annotations

import argparse
import datetime
import getpass
import hashlib
import html
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

tools_dir = Path(__file__).resolve().parent
repo_root = tools_dir.parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

from confluence_client import ConfluenceAPIError, ConfluenceClient
from link_resolver import audit_document_links, resolve_markdown_links
from markdown_to_storage import (
    check_document_compatibility,
    markdown_to_storage,
    validate_storage_xml,
)

try:
    from asset_renderer import RENDERED_ASSETS_DIR
except ImportError:
    RENDERED_ASSETS_DIR = tools_dir / "rendered_assets"

DEFAULT_SITE = "unitru-team-hpj93f6y.atlassian.net"
DEFAULT_ROOT_ID = "2097153"
DEFAULT_SPACE_ID = "2031619"
DEFAULT_TEST_PAGE_ID = "2162690"
DEFAULT_TEST_TITLE = "Prueba de publicación automática — GDP"
DEFAULT_TEST_FILE = tools_dir / "test_page.md"
DEFAULT_STATE_FILE = tools_dir / ".confluence_state.json"
DEFAULT_MANIFEST_FILE = tools_dir / "docs_manifest.json"


def load_state(state_path: Path) -> Dict[str, Any]:
    """Carga el archivo de estado local de la página de prueba."""
    if not state_path.is_file():
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as err:
        print(f"[ADVERTENCIA] No se pudo leer el archivo de estado ({state_path}): {err}")
        return {}


def save_state(state_path: Path, state_data: Dict[str, Any]) -> None:
    """Guarda atómicamente el estado local de la página de prueba."""
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = state_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
        temp_file.replace(state_path)
    except Exception as err:
        print(f"[ERROR] No se pudo guardar el archivo de estado ({state_path}): {err}", file=sys.stderr)


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Carga el manifiesto versionable de documentos técnicos."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"No se encontró el manifiesto documental en: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(manifest_path: Path, manifest_data: Dict[str, Any]) -> None:
    """Guarda atómicamente el manifiesto actualizado en disco."""
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = manifest_path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        temp_file.replace(manifest_path)
    except Exception as err:
        print(f"[ERROR] No se pudo guardar el manifiesto ({manifest_path}): {err}", file=sys.stderr)


def calculate_hash(content: str) -> str:
    """Calcula el hash SHA-256 de una cadena de texto para comparación de contenido."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def extract_attachment_info(res: Any) -> Tuple[Optional[str], int]:
    """Extrae el ID y número de versión del adjunto a partir de la respuesta del API de Confluence."""
    if not isinstance(res, dict):
        return None, 1
    if "results" in res and isinstance(res["results"], list) and len(res["results"]) > 0:
        first = res["results"][0]
        att_id = str(first.get("id", "")) if first.get("id") else None
        v = 1
        if isinstance(first.get("version"), dict):
            v = first["version"].get("number", 1)
        elif isinstance(first.get("version"), int):
            v = first["version"]
        return att_id, v
    att_id = str(res.get("id", "")) if res.get("id") else None
    v = 1
    if isinstance(res.get("version"), dict):
        v = res["version"].get("number", 1)
    elif isinstance(res.get("version"), int):
        v = res["version"]
    return att_id, v



def obtain_credentials(args: argparse.Namespace) -> tuple[Optional[str], str, str, Optional[str]]:
    """Obtiene de forma segura las credenciales desde argumentos, variables de entorno o terminal oculta."""
    token_type = args.token_type or os.environ.get("CONFLUENCE_TOKEN_TYPE", "unscoped").lower()
    email = args.email or os.environ.get("CONFLUENCE_EMAIL")
    token = args.token or os.environ.get("CONFLUENCE_API_TOKEN")
    cloud_id = args.cloud_id or os.environ.get("CONFLUENCE_CLOUD_ID")

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


# ==============================================================================
# VALIDACIÓN LOCAL OFFLINE MULTI-DOCUMENTO
# ==============================================================================


def run_local_validation(manifest_path: Path) -> int:
    """Ejecuta una validación integral fuera de línea de los 12 documentos del manifiesto.

    No requiere credenciales ni acceso a red. Evalúa:
    1. Existencia del archivo en disco.
    2. Renderizado local de diagramas Mermaid a PNG y fórmulas LaTeX ($$) a PNG.
    3. Conversión semántica de expresiones matemáticas simples ($) a Unicode.
    4. Resolución estricta de enlaces a código fuente hacia GitHub (commit documentado).
    5. Resolución de enlaces inter-documentales hacia macros nativas <ac:link><ri:page .../></ac:link>.
    6. Conversión a XHTML y validación del árbol XML con ElementTree.
    """
    print("=" * 80)
    print("  VALIDACIÓN LOCAL INTEGRAL DE DOCUMENTACIÓN TÉCNICA (DOCS/)")
    print("=" * 80)
    print(f"Manifiesto de control: {manifest_path}")

    try:
        manifest = load_manifest(manifest_path)
    except Exception as err:
        print(f"[ERROR FATAL] Falló la lectura del manifiesto: {err}", file=sys.stderr)
        return 1

    docs_list = manifest.get("documents", [])
    print(f"Total de documentos registrados en manifiesto: {len(docs_list)}")
    print(f"Commit de código documentado referenciado   : {manifest['metadata'].get('documented_code_commit')}")
    print("-" * 80)

    ready_count = 0
    blocked_count = 0
    total_code_links = 0
    total_doc_links = 0
    total_attachments = 0
    unresolved_link_count = 0

    print(f"{'Documento':<26} | {'Estado':<8} | {'Enlaces (Code/Doc)':<18} | {'Adjuntos':<10} | {'Validación XML':<16}")
    print("-" * 80)

    for doc in docs_list:
        file_rel = doc.get("file", "")
        file_abs = repo_root / file_rel

        if not file_abs.is_file():
            print(f"{file_rel:<26} | NO EXISTE | Archivo no encontrado en disco")
            blocked_count += 1
            continue

        raw_md = file_abs.read_text(encoding="utf-8")

        # 1. Auditoría de enlaces
        link_audit = audit_document_links(raw_md, file_rel, manifest)
        n_code = len(link_audit["code_links"])
        n_doc = len(link_audit["doc_links"])
        n_unres = len(link_audit["unresolved_links"])
        total_code_links += n_code
        total_doc_links += n_doc
        unresolved_link_count += n_unres

        # 2. Conversión, renderizado de activos y validación XML completa
        try:
            title, storage_xml, atts = markdown_to_storage(
                raw_md,
                source_file=file_rel,
                manifest_data=manifest,
                return_attachments=True,
            )
            validate_storage_xml(storage_xml)
            n_atts = len(atts)
            total_attachments += n_atts
            ready_count += 1
            xml_status = f"VÁLIDO ({len(storage_xml)} B)"
            print(f"{file_rel:<26} | LISTO    | Code:{n_code:<3} Doc:{n_doc:<3}    | {n_atts:<10} | {xml_status}")
            if n_atts > 0:
                for a in atts:
                    print(f"   + [ADJUNTO PNG]: {a['filename']} ({a['size_bytes']} B, SHA-256: {a['sha256'][:16]}...)")
        except Exception as err:
            blocked_count += 1
            print(f"{file_rel:<26} | BLOQUEADO| Code:{n_code:<3} Doc:{n_doc:<3}    | 0          | ERROR")
            print(f"   -> [MOTIVO]: {err}")

    print("-" * 80)
    print("RESUMEN DE AUDITORÍA LOCAL:")
    print(f"  - Documentos compatibles y listos para publicar: {ready_count} / {len(docs_list)}")
    print(f"  - Documentos bloqueados por errores o incompatibilidad: {blocked_count}")
    print(f"  - Activos visuales generados localmente (PNG)   : {total_attachments}")
    print(f"  - Enlaces a código resueltos hacia GitHub       : {total_code_links}")
    print(f"  - Enlaces entre documentos resueltos a Confluence : {total_doc_links}")
    print(f"  - Enlaces relativos huérfanos o sin resolver     : {unresolved_link_count}")
    print("=" * 80)

    if unresolved_link_count > 0 or blocked_count > 0:
        print("[ADVERTENCIA] Existen bloqueos o enlaces relativos no resueltos.", file=sys.stderr)
        return 1

    return 0


# ==============================================================================
# MODO MULTI-DOCUMENTO CON VERIFICACIÓN REMOTA
# ==============================================================================


def run_multi_document_mode(args: argparse.Namespace) -> None:
    """Gestiona la comprobación remota, planificación y publicación de los 12 documentos reales."""
    manifest_path = args.manifest or DEFAULT_MANIFEST_FILE
    manifest = load_manifest(manifest_path)
    metadata = manifest.get("metadata", {})

    target_space_id = str(metadata.get("space_id", DEFAULT_SPACE_ID))
    target_root_id = str(metadata.get("root_page_id", DEFAULT_ROOT_ID))
    test_page_id = str(metadata.get("test_page_id", DEFAULT_TEST_PAGE_ID))

    # 1. Pre-validación local obligatoria antes de operar remotamente en modo publicación o simulación
    if args.publish or args.dry_run:
        print("\n" + "=" * 80)
        print("  FASE 1/3: PRE-VALIDACIÓN LOCAL INTEGRAL DE LOS 12 DOCUMENTOS Y ACTIVOS")
        print("=" * 80)
        val_code = run_local_validation(manifest_path)
        if val_code != 0:
            print(
                "\n[ERROR FATAL]: La validación local de documentos falló. Operación abortada sin escrituras.",
                file=sys.stderr,
            )
            sys.exit(1)
        print("\n[OK]: Pre-validación local superada con éxito.")

    email, token, token_type, cloud_id = obtain_credentials(args)

    print("\n" + "=" * 80)
    print("  GESTIÓN MULTI-DOCUMENTO DE CONFLUENCE CLOUD (API v2)")
    print("=" * 80)
    print(f"Sitio objetivo       : https://{args.site}")
    print(f"Espacio esperado     : GDP (spaceId numérico: {target_space_id})")
    print(f"Página raíz (padre)  : ID {target_root_id}")
    print(f"Página de prueba     : ID {test_page_id} (PROTEGIDA - no se reutiliza para docs reales)")
    print(f"Manifiesto           : {manifest_path}")
    print(f"Modo de ejecución    : {'PUBLICACIÓN REAL (--publish)' if args.publish else ('SIMULACIÓN PLANIFICADA (--dry-run)' if args.dry_run else 'VERIFICACIÓN REMOTA (--check)')}")
    print("-" * 80)

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

    # 2. Comprobar la página raíz padre en Confluence
    print(f"[CONEXIÓN] Consultando metadatos de la página raíz padre ID {target_root_id}...")
    try:
        root_data = client.get_page(target_root_id)
    except ConfluenceAPIError as err:
        print(f"[ERROR FATAL] No fue posible acceder a la página raíz {target_root_id}: {err}", file=sys.stderr)
        sys.exit(1)

    remote_space_id = str(root_data.get("spaceId", ""))
    root_title = root_data.get("title", "")
    if remote_space_id != target_space_id:
        print(
            f"[ERROR DE INTEGRIDAD] El spaceId devuelto por la raíz ({remote_space_id}) "
            f"no coincide con el configurado en el manifiesto ({target_space_id}). Abortando.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[OK] Raíz verificada : '{root_title}' (ID: {target_root_id}, SpaceId: {remote_space_id})")

    # 3. Comprobar que la página de prueba aislada exista y esté protegida
    try:
        test_remote = client.get_page(test_page_id)
        print(f"[OK] Página de prueba: '{test_remote.get('title')}' (ID: {test_page_id}, v{test_remote.get('version', {}).get('number')}) - Reservada exclusivamente para pruebas.")
    except Exception as err:
        print(f"[ADVERTENCIA] No se pudo verificar la página de prueba reservada ID {test_page_id}: {err}")

    # 4. Iterar sobre los documentos del manifiesto
    print("-" * 80)
    print("PROCESAMIENTO Y SINCRONIZACIÓN DE DOCUMENTOS:")
    print("-" * 80)

    docs_list = manifest.get("documents", [])
    manifest_modified = False

    created_pages = 0
    updated_pages = 0
    skipped_pages = 0
    blocked_pages = 0
    uploaded_attachments = 0
    updated_attachments = 0
    skipped_attachments = 0
    total_errors = 0

    for doc in docs_list:
        doc_file = doc["file"]
        doc_slug = doc.get("slug", Path(doc_file).stem)
        doc_title = doc["title"]
        known_id = doc.get("page_id")
        declared_status = doc.get("status")

        # Regla estricta: ninguna entrada real puede apuntar a la página raíz ni a la de prueba
        if known_id and str(known_id) in [target_root_id, test_page_id]:
            print(f"[ERROR FATAL] Documento '{doc_file}' tiene asignado un ID reservado ({known_id}). Abortando.", file=sys.stderr)
            sys.exit(1)

        print(f"\n>> Documento: {doc_file} ('{doc_title}')")

        if declared_status == "blocked":
            print(f"   [ESTADO]: BLOQUEADO LOCALMENTE - {doc.get('block_reason', 'Incompatibilidad de sintaxis')}")
            print("   -> Acción: Omitido de la publicación remota para proteger la fidelidad documental.")
            blocked_pages += 1
            total_errors += 1
            continue

        file_abs = repo_root / doc_file
        if not file_abs.is_file():
            print(f"   [ERROR]: El archivo {doc_file} no existe en disco.", file=sys.stderr)
            blocked_pages += 1
            total_errors += 1
            continue

        raw_text = file_abs.read_text(encoding="utf-8")
        try:
            _, local_storage, atts = markdown_to_storage(raw_text, doc_file, manifest, return_attachments=True)
            validate_storage_xml(local_storage)
        except Exception as conv_err:
            print(f"   [ERROR]: Falló la conversión/validación XML de {doc_file}: {conv_err}", file=sys.stderr)
            blocked_pages += 1
            total_errors += 1
            continue

        local_hash = calculate_hash(local_storage)
        remote_page = None
        just_created = False

        if not known_id:
            # No tiene ID asignado: buscar si existe una página huérfana con el mismo título
            print("   [BÚSQUEDA]: Sin ID en manifiesto. Verificando páginas huérfanas en Confluence...")
            try:
                matches = client.search_pages_by_title(doc_title, space_id=target_space_id)
            except ConfluenceAPIError as err:
                print(f"   [ERROR]: Falló la búsqueda de páginas existentes: {err}")
                blocked_pages += 1
                total_errors += 1
                continue

            if matches:
                if len(matches) > 1:
                    print(f"   [ERROR FATAL - AMBIGÜEDAD]: Se encontraron {len(matches)} páginas con el título '{doc_title}'. Deteniendo.")
                    sys.exit(1)

                orphan = matches[0]
                orphan_id = str(orphan.get("id"))
                # Comprobar la firma de identidad verificable en el contenido remoto
                try:
                    cand_page = client.get_page(orphan_id, body_format="storage")
                    cand_body = cand_page.get("body", {}).get("storage", {}).get("value", "")
                    cand_space = str(cand_page.get("spaceId", ""))
                    cand_parent = str(cand_page.get("parentId", ""))
                except Exception as cand_err:
                    print(f"   [ERROR]: No se pudo examinar el contenido de la página encontrada ID {orphan_id}: {cand_err}")
                    sys.exit(1)

                identity_signature = f"confluence-doc-identity:slug={doc_slug};space_id={target_space_id};parent_id={target_root_id}"
                has_identity = (identity_signature in cand_body) or (f"slug={doc_slug}" in cand_body and f"parent_id={target_root_id}" in cand_body)

                if has_identity:
                    print(f"   [RECUPERACIÓN SEGURA DE IDENTIDAD]: Se verificó la identidad de la página ID {orphan_id}.")
                    print(f"      Firma coincidente: slug='{doc_slug}', spaceId='{cand_space}', parentId='{cand_parent}'.")
                    print("      -> Adoptando ID en manifiesto de forma segura (interrupción previa recuperada con éxito).")
                    doc["page_id"] = orphan_id
                    doc["version"] = cand_page.get("version", {}).get("number", 1)
                    doc["remote_body_hash"] = calculate_hash(cand_body)
                    known_id = orphan_id
                    remote_page = cand_page
                    manifest_modified = True
                    save_manifest(manifest_path, manifest)
                    if args.check:
                        print(f"   [ESTADO]: IDENTIDAD RECUPERADA (ID {orphan_id}). No requiere acción en check.")
                        continue
                else:
                    print(f"   [ALERTA DE SEGURIDAD - PÁGINA HUÉRFANA NO VERIFICADA]: Se encontró página con título idéntico (ID: {orphan_id})")
                    print("      pero NO contiene la firma de identidad verificable del documento.")
                    print("      -> No se adopta automáticamente para evitar sobrescribir páginas no vinculadas. Deteniendo.")
                    sys.exit(1)
            else:
                if args.check:
                    print(f"   [ESTADO]: LISTO PARA CREACIÓN como nueva página hija de la raíz {target_root_id}.")
                    continue
                elif args.dry_run:
                    print(f"   [DRY-RUN] Plan: CREAR página '{doc_title}' bajo raíz {target_root_id}.")
                    created_pages += 1
                elif args.publish:
                    print(f"   [PUBLICACIÓN]: Creando página '{doc_title}' bajo raíz {target_root_id}...")
                    try:
                        create_res = client.create_page(
                            space_id=target_space_id,
                            title=doc_title,
                            parent_id=target_root_id,
                            storage_xml=local_storage,
                        )
                        new_id = str(create_res.get("id"))
                        created_v = create_res.get("version", {}).get("number", 1)
                        print(f"   [ÉXITO]: Página creada con ID {new_id} (versión {created_v}).")
                    except ConfluenceAPIError as err:
                        print(f"   [ERROR]: Falló la creación de la página '{doc_title}': {err}")
                        total_errors += 1
                        blocked_pages += 1
                        continue

                    try:
                        post_page = client.get_page(new_id, body_format="storage")
                        remote_body = post_page.get("body", {}).get("storage", {}).get("value", "")
                    except Exception:
                        remote_body = local_storage

                    remote_hash = calculate_hash(remote_body)
                    doc["page_id"] = new_id
                    doc["version"] = created_v
                    doc["content_sha256"] = local_hash
                    doc["remote_body_hash"] = remote_hash
                    manifest_modified = True
                    save_manifest(manifest_path, manifest)
                    created_pages += 1
                    known_id = new_id
                    just_created = True

        # Si la página ya existía previamente
        if known_id and not just_created:
            if remote_page is None:
                try:
                    remote_page = client.get_page(str(known_id), body_format="storage")
                except ConfluenceAPIError as err:
                    print(f"   [ERROR]: El ID {known_id} registrado en el manifiesto no existe en Confluence: {err}")
                    total_errors += 1
                    blocked_pages += 1
                    continue

            r_space = str(remote_page.get("spaceId", ""))
            r_parent = str(remote_page.get("parentId", ""))
            r_title = remote_page.get("title", "")
            r_version = remote_page.get("version", {}).get("number", 0)

            # Comprobar pertenencia al espacio y jerarquía
            if r_space != target_space_id:
                print(f"   [ALERTA DE SEGURIDAD]: La página ID {known_id} pertenece al espacio {r_space}, no a {target_space_id}!")
                total_errors += 1
                blocked_pages += 1
                continue
            if r_parent != target_root_id:
                print(f"   [ALERTA DE JERARQUÍA]: La página ID {known_id} tiene como padre {r_parent}, no la raíz {target_root_id}!")
                total_errors += 1
                blocked_pages += 1
                continue
            if r_title != doc_title:
                print(f"   [ALERTA DE CORRESPONDENCIA]: El título remoto ('{r_title}') no coincide con el manifiesto ('{doc_title}')!")
                total_errors += 1
                blocked_pages += 1
                continue

            # Detección de edición remota posterior
            remote_body = remote_page.get("body", {}).get("storage", {}).get("value", "")
            current_remote_hash = calculate_hash(remote_body)
            stored_remote_hash = doc.get("remote_body_hash")
            stored_local_version = doc.get("version", 0)

            has_remote_conflict = False
            if stored_local_version > 0 and r_version > stored_local_version:
                has_remote_conflict = True
            if stored_remote_hash and current_remote_hash != stored_remote_hash:
                has_remote_conflict = True

            if has_remote_conflict:
                print(f"   [CONFLICTO REMOTO DETECTADO - ACTUALIZACIÓN BLOQUEADA]:")
                print(f"      Versión local registrada: v{stored_local_version} (Hash remoto registrado: {stored_remote_hash[:16] if stored_remote_hash else 'N/A'}...)")
                print(f"      Versión remota actual   : v{r_version} (Hash remoto actual    : {current_remote_hash[:16]}...)")
                print("      -> Causa: La página fue editada en Confluence con posterioridad a la última publicación.")
                print("      -> Acción: Se bloquea la actualización para evitar sobrescribir los cambios remotos.")
                blocked_pages += 1
                total_errors += 1
                continue

            stored_content_hash = doc.get("content_sha256")
            is_identical = (stored_content_hash and local_hash == stored_content_hash and r_version == stored_local_version)

            if is_identical:
                print(f"   [ESTADO]: SIN CAMBIOS (v{r_version}, hash SHA-256 coincide). No requiere actualización.")
                skipped_pages += 1
            else:
                next_v = r_version + 1
                if args.check:
                    print(f"   [ESTADO]: REQUIERE ACTUALIZACIÓN (remoto: v{r_version} -> siguiente: v{next_v}).")
                elif args.dry_run:
                    print(f"   [DRY-RUN] Plan: ACTUALIZAR página '{doc_title}' (v{r_version} -> v{next_v}).")
                    updated_pages += 1
                elif args.publish:
                    print(f"   [PUBLICACIÓN]: Actualizando página ID {known_id} (v{r_version} -> v{next_v})...")
                    try:
                        update_res = client.update_page(
                            page_id=str(known_id),
                            space_id=target_space_id,
                            title=doc_title,
                            parent_id=target_root_id,
                            storage_xml=local_storage,
                            next_version=next_v,
                            version_message="Actualización automática de documentación técnica",
                        )
                        new_v = update_res.get("version", {}).get("number", next_v)
                        print(f"   [ÉXITO]: Página ID {known_id} actualizada a versión {new_v}.")
                    except ConfluenceAPIError as err:
                        print(f"   [ERROR]: Falló la actualización de la página ID {known_id}: {err}")
                        total_errors += 1
                        blocked_pages += 1
                        continue

                    try:
                        post_page = client.get_page(str(known_id), body_format="storage")
                        new_remote_body = post_page.get("body", {}).get("storage", {}).get("value", "")
                    except Exception:
                        new_remote_body = local_storage

                    doc["version"] = new_v
                    doc["content_sha256"] = local_hash
                    doc["remote_body_hash"] = calculate_hash(new_remote_body)
                    manifest_modified = True
                    save_manifest(manifest_path, manifest)
                    updated_pages += 1

        # Manejo de adjuntos para la página (known_id)
        req_attachments = doc.get("attachments", [])
        if req_attachments:
            if not known_id and args.dry_run:
                # En dry-run si la página no existía, planificar la subida de los adjuntos
                for att in req_attachments:
                    print(f"      [DRY-RUN] Plan: SUBIR adjunto '{att['filename']}' tras creación de página.")
                    uploaded_attachments += 1
            elif not known_id and args.check:
                for att in req_attachments:
                    print(f"      [ADJUNTO PENDIENTE]: '{att['filename']}' requiere carga tras creación de página.")
            elif known_id:
                print(f"   [ADJUNTOS]: Verificando {len(req_attachments)} archivo(s) adjunto(s) para la página ID {known_id}...")
                try:
                    remote_atts = client.get_attachments(str(known_id))
                    remote_att_map = {ra.get("title"): ra for ra in remote_atts}
                except Exception as att_err:
                    print(f"      [ADVERTENCIA]: No se pudieron consultar adjuntos remotos: {att_err}")
                    remote_att_map = {}

                for att in req_attachments:
                    att_name = att["filename"]
                    att_path = RENDERED_ASSETS_DIR / att_name

                    if not att_path.is_file():
                        print(f"      [ERROR]: Archivo de activo local no encontrado: {att_path}")
                        total_errors += 1
                        continue

                    current_local_sha256 = hashlib.sha256(att_path.read_bytes()).hexdigest()
                    remote_att = remote_att_map.get(att_name)

                    if remote_att is None:
                        if args.check:
                            print(f"      [ADJUNTO NO EXISTE]: '{att_name}' no existe en Confluence (requiere subida inicial).")
                        elif args.dry_run:
                            print(f"      [DRY-RUN] Plan: SUBIR adjunto '{att_name}' a página ID {known_id}.")
                            uploaded_attachments += 1
                        elif args.publish:
                            print(f"      [PUBLICACIÓN]: Subiendo nuevo adjunto '{att_name}' a página ID {known_id}...")
                            try:
                                res = client.upload_attachment(
                                    page_id=str(known_id),
                                    file_path=att_path,
                                    comment=f"Adjunto generado automáticamente para {doc_file}",
                                )
                                res_att_id, res_v = extract_attachment_info(res)
                                att["published_sha256"] = current_local_sha256
                                att["attachment_id"] = res_att_id or (str(remote_att.get("id")) if remote_att else None)
                                att["published_version"] = res_v
                                manifest_modified = True
                                save_manifest(manifest_path, manifest)
                                uploaded_attachments += 1
                                print(f"      [ÉXITO]: Adjunto '{att_name}' subido satisfactoriamente (ID: {att.get('attachment_id')}, v{res_v}).")
                            except Exception as upl_err:
                                print(f"      [ERROR]: Falló la subida del adjunto '{att_name}': {upl_err}")
                                total_errors += 1
                    else:
                        remote_att_id = str(remote_att.get("id", ""))
                        remote_v = remote_att.get("version", {}).get("number", 1) if isinstance(remote_att.get("version"), dict) else 1
                        last_published_sha256 = att.get("published_sha256")
                        last_published_v = att.get("published_version")

                        has_sufficient_info = (last_published_sha256 is not None)
                        has_unexpected_remote_change = (last_published_v is not None and remote_v > last_published_v)
                        is_content_identical = (has_sufficient_info and not has_unexpected_remote_change and current_local_sha256 == last_published_sha256)

                        if is_content_identical:
                            print(f"      [ADJUNTO SIN CAMBIOS]: '{att_name}' (ID: {remote_att_id}, v{remote_v}) comprobado idéntico (SHA-256 coincidente). Omitiendo recarga.")
                            skipped_attachments += 1
                        else:
                            if not has_sufficient_info:
                                print(f"      [INFORMACIÓN INSUFICIENTE]: '{att_name}' existe en Confluence (ID: {remote_att_id}, v{remote_v}) pero no cuenta con registro previo de subida exitosa (published_sha256).")
                                print("      -> Acción: No se asume sincronizado solo por el nombre. Se programará actualización.")
                            elif has_unexpected_remote_change:
                                print(f"      [MODIFICACIÓN REMOTA INESPERADA]: Se detectó versión remota v{remote_v} en '{att_name}' superior a la registrada v{last_published_v}.")
                                print("      -> Acción: No se declara sincronizado solo por el nombre. Se programará actualización.")
                            else:
                                print(f"      [ADJUNTO MODIFICADO]: Contenido local de '{att_name}' modificado (hash previo: {last_published_sha256[:12]}... -> actual: {current_local_sha256[:12]}...).")

                            if args.check:
                                print(f"      [ADJUNTO REQUIERE ACTUALIZACIÓN]: '{att_name}' requiere actualizar su contenido en Confluence.")
                            elif args.dry_run:
                                next_att_v = remote_v + 1
                                print(f"      [DRY-RUN] Plan: ACTUALIZAR adjunto '{att_name}' (ID {remote_att_id}, v{remote_v} -> v{next_att_v}) en página ID {known_id}.")
                                updated_attachments += 1
                            elif args.publish:
                                print(f"      [PUBLICACIÓN]: Actualizando adjunto existente '{att_name}' (ID {remote_att_id}) en página ID {known_id}...")
                                try:
                                    res = client.update_attachment(
                                        page_id=str(known_id),
                                        attachment_id=remote_att_id,
                                        file_path=att_path,
                                        comment=f"Actualización automática de adjunto para {doc_file}",
                                    )
                                    res_att_id, res_v = extract_attachment_info(res)
                                    actual_v = res_v if res_v > remote_v else (remote_v + 1)
                                    att["published_sha256"] = current_local_sha256
                                    att["attachment_id"] = remote_att_id
                                    att["published_version"] = actual_v
                                    manifest_modified = True
                                    save_manifest(manifest_path, manifest)
                                    updated_attachments += 1
                                    print(f"      [ÉXITO]: Adjunto '{att_name}' actualizado satisfactoriamente (ID: {remote_att_id}, versión remota: v{actual_v}).")
                                except Exception as upd_err:
                                    print(f"      [ERROR]: Falló la actualización del adjunto '{att_name}': {upd_err}")
                                    total_errors += 1

    if manifest_modified:
        save_manifest(manifest_path, manifest)
        print("\n[MANIFIESTO ACTUALIZADO]: Se guardaron todos los cambios de manifiesto en disco.")

    print("\n" + "=" * 80)
    if args.publish:
        print("RESUMEN FINAL DE PUBLICACIÓN MULTI-DOCUMENTO:")
        print(f"  - Páginas creadas con éxito     : {created_pages}")
        print(f"  - Páginas actualizadas          : {updated_pages}")
        print(f"  - Páginas omitidas (sin cambios): {skipped_pages}")
        print(f"  - Páginas bloqueadas/conflictos : {blocked_pages}")
        print(f"  - Adjuntos PNG subidos          : {uploaded_attachments}")
        print(f"  - Adjuntos PNG actualizados     : {updated_attachments}")
        print(f"  - Adjuntos PNG omitidos         : {skipped_attachments}")
        print(f"  - Errores totales               : {total_errors}")
        print("=" * 80)

        total_processed = created_pages + updated_pages + skipped_pages
        if total_errors > 0 or blocked_pages > 0 or total_processed < len(docs_list):
            print("\n[PUBLICACIÓN INCOMPLETA]: Se detectaron errores o bloqueos durante la publicación.", file=sys.stderr)
            sys.exit(1)
        else:
            print("\n[PUBLICACIÓN EXITOSA]: Los 12 documentos y sus activos se encuentran sincronizados en Confluence Cloud.")
            return

    elif args.dry_run:
        print("RESUMEN DEL PLAN DE PUBLICACIÓN (DRY-RUN):")
        print(f"  - Páginas a crear               : {created_pages}")
        print(f"  - Páginas a actualizar          : {updated_pages}")
        print(f"  - Páginas a omitir (sin cambios): {skipped_pages}")
        print(f"  - Páginas bloqueadas            : {blocked_pages}")
        print(f"  - Adjuntos PNG a subir          : {uploaded_attachments}")
        print(f"  - Adjuntos PNG a actualizar     : {updated_attachments}")
        print(f"  - Adjuntos PNG a omitir         : {skipped_attachments}")
        print(f"  - Errores detectados            : {total_errors}")
        print("=" * 80)
        print("[DRY-RUN EXITOSO]: Planificación completada. No se realizaron escrituras en Confluence.")
        return

    elif args.check:
        print("RESUMEN DE VERIFICACIÓN REMOTA (CHECK):")
        print(f"  - Documentos verificados        : {len(docs_list)}")
        print(f"  - Páginas sin cambios           : {skipped_pages}")
        print(f"  - Páginas bloqueadas            : {blocked_pages}")
        print(f"  - Adjuntos PNG omitidos         : {skipped_attachments}")
        print(f"  - Errores detectados            : {total_errors}")
        print("=" * 80)
        print("[CHECK EXITOSO]: Verificación remota concluida. No se realizaron escrituras en Confluence.")
        return


# ==============================================================================
# MODO PRUEBA INDIVIDUAL (PRESERVADO)
# ==============================================================================


def run_single_test_mode(args: argparse.Namespace) -> None:
    """Ejecuta el flujo original de prueba controlada de página única (test_page.md)."""
    email, token, token_type, cloud_id = obtain_credentials(args)

    print("=" * 70)
    print("  PUBLICADOR DE PRUEBA A CONFLUENCE CLOUD (API v2)")
    print("=" * 70)
    print(f"Sitio objetivo       : https://{args.site}")
    print(f"Tipo de autenticación: API Token Personal ({token_type.upper()}) con HTTP Basic Auth")
    print(f"Usuario autenticado  : {email}")
    print(f"Página raíz (padre)  : ID {args.root_id}")
    print(f"Título objetivo      : '{args.title}'")
    print(f"Archivo Markdown     : {args.file}")
    print(f"Archivo de estado    : {args.state_file}")
    print("-" * 70)

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

    print(f"[CONEXIÓN] Consultando metadatos de la página raíz ID {args.root_id}...")
    try:
        root_data = client.get_page(str(args.root_id))
    except ConfluenceAPIError as err:
        print(f"[ERROR DE CONEXIÓN / AUTENTICACIÓN] No fue posible consultar la página raíz: {err}", file=sys.stderr)
        sys.exit(1)

    root_title = root_data.get("title", "<sin título>")
    space_id = str(root_data.get("spaceId", ""))
    root_version = root_data.get("version", {}).get("number", "?")

    print(f"[OK] Raíz verificada : '{root_title}' (ID: {args.root_id}, Versión: {root_version})")
    print(f"[OK] Space ID resuelto: {space_id} (Espacio documental 'GDP')")

    if args.check:
        print("-" * 70)
        print("[VERIFICACIÓN EXITOSA] Conexión establecida, autenticación válida y spaceId resuelto.")
        print("=" * 70)
        sys.exit(0)

    if not args.file.is_file():
        print(f"[ERROR] No se encontró el archivo Markdown en: {args.file}", file=sys.stderr)
        sys.exit(1)

    md_content = args.file.read_text(encoding="utf-8")
    extracted_title, storage_xml = markdown_to_storage(md_content, str(args.file))
    content_hash = calculate_hash(storage_xml)
    page_title = args.title or extracted_title or DEFAULT_TEST_TITLE

    state = load_state(args.state_file)
    known_page_id = state.get("page_id")
    stored_hash = state.get("content_sha256")
    last_version = state.get("version", 0)

    if known_page_id and str(known_page_id) == str(args.root_id):
        print("[ERROR FATAL DE SEGURIDAD] El ID registrado coincide con la raíz. Abortando.", file=sys.stderr)
        sys.exit(1)

    if known_page_id:
        print(f"[ESTADO LOCAL] Página de prueba registrada con ID {known_page_id} (Versión previa: {last_version}).")
        current_remote = client.get_page(str(known_page_id))
        remote_version = current_remote.get("version", {}).get("number", 1)
        next_version = remote_version + 1

        if stored_hash == content_hash:
            print("-" * 70)
            print(f"[OMITIDO] Contenido IDÉNTICO al último publicado (SHA-256: {content_hash[:12]}...).")
            print(f"Página ID {known_page_id} se mantiene en versión {remote_version}. Sin llamadas de escritura.")
            print("=" * 70)
            sys.exit(0)

        if args.dry_run:
            print("-" * 70)
            print("[DRY-RUN] ACCIÓN PLANIFICADA: ACTUALIZACIÓN DE PÁGINA DE PRUEBA")
            print(f"  - ID: {known_page_id} | Versión actual: {remote_version} -> Siguiente: {next_version}")
            print("=" * 70)
            sys.exit(0)

        # Publicación real
        update_res = client.update_page(
            page_id=str(known_page_id),
            space_id=space_id,
            title=page_title,
            parent_id=str(args.root_id),
            storage_xml=storage_xml,
            next_version=next_version,
            version_message="Actualización automática de prueba",
        )
        new_v = update_res.get("version", {}).get("number", next_version)
        save_state(args.state_file, {
            "page_id": str(known_page_id),
            "space_id": space_id,
            "root_id": str(args.root_id),
            "title": page_title,
            "content_sha256": content_hash,
            "version": new_v,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        print(f"[ÉXITO] Página ID {known_page_id} actualizada a versión {new_v}.")
        sys.exit(0)

    else:
        # Buscar si ya existe una página huérfana con el mismo título en el espacio
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
            print("  1. Si desea que este publicador gestione esa página, registre manualmente su ID en el estado local.")
            print("  2. O elimínela manualmente de Confluence si fue creada por error.")
            print("La operación se detiene sin realizar cambios.")
            print("!" * 70)
            sys.exit(1)

        # Creación si no existe
        if args.dry_run:
            print("[DRY-RUN] ACCIÓN PLANIFICADA: CREACIÓN DE NUEVA PÁGINA DE PRUEBA")
            sys.exit(0)

        create_res = client.create_page(
            space_id=space_id,
            title=page_title,
            parent_id=str(args.root_id),
            storage_xml=storage_xml,
        )
        new_id = str(create_res.get("id"))
        created_v = create_res.get("version", {}).get("number", 1)
        save_state(args.state_file, {
            "page_id": new_id,
            "space_id": space_id,
            "root_id": str(args.root_id),
            "title": page_title,
            "content_sha256": content_hash,
            "version": created_v,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        print(f"[ÉXITO] Página de prueba creada con ID {new_id} (v{created_v}).")
        sys.exit(0)


def build_parser() -> argparse.ArgumentParser:
    """Configura los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Publicador y validador de documentación técnica hacia Confluence Cloud REST API v2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--validate-docs",
        action="store_true",
        help="Ejecuta la validación local offline completa de los 12 documentos reales sin requerir credenciales ni red.",
    )
    mode_group.add_argument(
        "--check",
        action="store_true",
        help="Comprueba la conectividad, credenciales y resolución remota de IDs en Confluence.",
    )
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la conversión, consulta la raíz y páginas existentes, e informa la acción planificada.",
    )
    mode_group.add_argument(
        "--publish",
        action="store_true",
        help="Ejecuta la publicación en Confluence Cloud (creación/actualización real y carga de adjuntos).",
    )

    parser.add_argument(
        "--multi",
        action="store_true",
        help="Activa el modo multi-documento para gestionar los 12 documentos reales mediante el manifiesto.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Fuerza el modo de prueba individual utilizando test_page.md y .confluence_state.json.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_FILE,
        help=f"Ruta al archivo de manifiesto documental (predeterminado: {DEFAULT_MANIFEST_FILE.name})",
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
        default=DEFAULT_TEST_FILE,
        help=f"Ruta al archivo Markdown individual a publicar (predeterminado: {DEFAULT_TEST_FILE.name})",
    )
    parser.add_argument(
        "--title",
        default=DEFAULT_TEST_TITLE,
        help=f"Título de la página individual (predeterminado: '{DEFAULT_TEST_TITLE}')",
    )
    parser.add_argument(
        "--token-type",
        choices=["unscoped", "scoped"],
        default=None,
        help="Tipo de token: 'unscoped' (sitio directo) o 'scoped' (api.atlassian.com). Ambos usan HTTP Basic.",
    )
    parser.add_argument(
        "--cloud-id",
        default=None,
        help="Atlassian Cloud ID (para tokens 'scoped'; se detecta automáticamente si se omite)",
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Correo de la cuenta Atlassian (o variable CONFLUENCE_EMAIL)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="API Token personal de Atlassian (o variable CONFLUENCE_API_TOKEN)",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help=f"Ruta al archivo de estado local de prueba (predeterminado: {DEFAULT_STATE_FILE.name})",
    )

    return parser


def main() -> None:
    """Punto de entrada principal."""
    parser = build_parser()
    args = parser.parse_args()

    # 1. Modo validación local offline
    if args.validate_docs:
        manifest_path = args.manifest or DEFAULT_MANIFEST_FILE
        code = run_local_validation(manifest_path)
        sys.exit(code)

    # 2. Determinar si se opera en modo multi-documento o individual
    is_multi = args.multi or (not args.test and args.manifest != DEFAULT_MANIFEST_FILE)

    if is_multi:
        run_multi_document_mode(args)
    else:
        run_single_test_mode(args)


if __name__ == "__main__":
    main()
