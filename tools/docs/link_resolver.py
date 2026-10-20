"""Resolutor seguro de enlaces para la documentación técnica de Confluence Cloud.

Transforma:
1. Enlaces a código fuente ('../backend/app/...', '../docker-compose.yml') en URLs canónicas
   inmutables de GitHub apuntando al commit de código documentado (0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02),
   preservando anclas de líneas (#L10-L20).
2. Enlaces inter-documentales ('./arquitectura.md', 'api.md#endpoints') en enlaces nativos
   de Confluence Cloud Storage Format (<ac:link><ri:page ri:content-title="..."/></ac:link>),
   resolviendo la navegación entre páginas incluso antes de que existan sus IDs numéricos.

Garantiza que ninguna ruta relativa local no resuelta sea enviada a Confluence.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_REPO_URL = "https://github.com/JMarkoFlores/gemelo-digital-polinizadores"
DEFAULT_DOCUMENTED_COMMIT = "0d62f6634e1eb4a5066a2bd9e76efe2cb00fee02"


def _build_doc_lookup(manifest_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Construye un índice de búsqueda rápida para los documentos del manifiesto."""
    lookup: Dict[str, Dict[str, Any]] = {}
    for doc in manifest_data.get("documents", []):
        file_path = doc.get("file", "")
        file_name = Path(file_path).name
        slug = doc.get("slug", "")
        lookup[file_path] = doc
        lookup[file_name] = doc
        lookup[f"./{file_name}"] = doc
        lookup[slug] = doc

    # Si es un manifiesto parcial (ej. pruebas unitarias), completar con el manifiesto canónico
    canon_file = Path(__file__).resolve().parent / "docs_manifest.json"
    if canon_file.is_file():
        try:
            with open(canon_file, "r", encoding="utf-8") as f:
                canon_data = json.load(f)
            for doc in canon_data.get("documents", []):
                file_path = doc.get("file", "")
                file_name = Path(file_path).name
                slug = doc.get("slug", "")
                if file_path not in lookup:
                    lookup[file_path] = doc
                if file_name not in lookup:
                    lookup[file_name] = doc
                if f"./{file_name}" not in lookup:
                    lookup[f"./{file_name}"] = doc
                if slug not in lookup:
                    lookup[slug] = doc
        except Exception:
            pass

    return lookup


def audit_document_links(
    markdown_text: str,
    source_file: str,
    manifest_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Audita todos los enlaces de un archivo y los categoriza sin modificarlos."""
    lookup = _build_doc_lookup(manifest_data)
    repo_url = manifest_data.get("metadata", {}).get("repo_url", DEFAULT_REPO_URL)
    code_commit = manifest_data.get("metadata", {}).get("documented_code_commit", DEFAULT_DOCUMENTED_COMMIT)

    lines = markdown_text.splitlines()
    in_code_block = False

    code_links: List[Tuple[str, str, str]] = []
    doc_links: List[Tuple[str, str, str]] = []
    external_links: List[Tuple[str, str]] = []
    unresolved_links: List[Tuple[str, str, int]] = []

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Extraer enlaces Markdown: [texto](url)
        matches = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
        for link_text, raw_target in matches:
            target = raw_target.strip()
            if target.startswith("http://") or target.startswith("https://") or target.startswith("mailto:"):
                external_links.append((link_text, target))
            elif target.startswith("#"):
                # Ancla interna de la misma página
                pass
            elif target.startswith("../"):
                # Enlace a código fuente relativo
                clean_path = target[3:]  # Remover '../'
                resolved_url = f"{repo_url}/blob/{code_commit}/{clean_path}"
                code_links.append((link_text, target, resolved_url))
            else:
                # Posible enlace a documento técnico
                clean_target = target.lstrip("./")
                file_part = clean_target.split("#")[0]
                if file_part in lookup:
                    matched_doc = lookup[file_part]
                    doc_links.append((link_text, target, matched_doc["title"]))
                else:
                    unresolved_links.append((link_text, target, line_idx))

    return {
        "source_file": source_file,
        "total_links": len(code_links) + len(doc_links) + len(external_links) + len(unresolved_links),
        "code_links": code_links,
        "doc_links": doc_links,
        "external_links": external_links,
        "unresolved_links": unresolved_links,
        "is_clean": len(unresolved_links) == 0,
    }


def resolve_markdown_links(
    markdown_text: str,
    source_file: str,
    manifest_data: Dict[str, Any],
) -> str:
    """Resuelve todos los enlaces relativos de código y documentación en el texto Markdown.

    - Código ('../...'): se transforma a URL canónica de GitHub con commit documentado.
    - Documentos ('./*.md'): se sustituye el enlace por un marcador seguro que luego
      se convierte al elemento XML nativo <ac:link><ri:page .../></ac:link>.

    Lanza ValueError si se encuentra alguna ruta relativa no reconocida.
    """
    lookup = _build_doc_lookup(manifest_data)
    repo_url = manifest_data.get("metadata", {}).get("repo_url", DEFAULT_REPO_URL)
    code_commit = manifest_data.get("metadata", {}).get("documented_code_commit", DEFAULT_DOCUMENTED_COMMIT)

    lines = markdown_text.splitlines()
    in_code_block = False
    resolved_lines: List[str] = []

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            resolved_lines.append(line)
            continue
        if in_code_block:
            resolved_lines.append(line)
            continue

        def replace_link(match: re.Match) -> str:
            link_text = match.group(1)
            raw_target = match.group(2).strip()

            if raw_target.startswith("http://") or raw_target.startswith("https://") or raw_target.startswith("mailto:"):
                return match.group(0)

            if raw_target.startswith("#"):
                return match.group(0)

            # Enlace a archivo de código fuente
            if raw_target.startswith("../"):
                clean_path = raw_target[3:]
                github_url = f"{repo_url}/blob/{code_commit}/{clean_path}"
                return f"[{link_text}]({github_url})"

            # Enlace a otro documento técnico
            clean_target = raw_target.lstrip("./")
            file_part = clean_target.split("#")[0]
            anchor_part = clean_target.split("#")[1] if "#" in clean_target else ""

            if file_part in lookup:
                matched_doc = lookup[file_part]
                target_title = matched_doc["title"]
                # Formato intermedio delimitado para conversión precisa en XHTML
                if anchor_part:
                    return f"__CONFLUENCE_LINK_TITLE__{target_title}__ANCHOR__{anchor_part}__TEXT__{link_text}__ENDLINK__"
                else:
                    return f"__CONFLUENCE_LINK_TITLE__{target_title}__TEXT__{link_text}__ENDLINK__"

            raise ValueError(
                f"Error en {source_file}:{line_idx}: ruta relativa no resuelta '{raw_target}'. "
                "No corresponde a ningún archivo del repositorio ni documento del manifiesto."
            )

        # Aplicar reemplazo sobre enlaces Markdown en la línea
        resolved_line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, line)
        resolved_lines.append(resolved_line)

    return "\n".join(resolved_lines)
