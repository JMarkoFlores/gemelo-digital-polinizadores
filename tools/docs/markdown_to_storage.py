"""Conversor de Markdown a Confluence Storage Format (XHTML).

Este módulo convierte texto Markdown estándar (encabezados, párrafos, listas
ordenadas y desordenadas, tablas, citas y bloques de código) a XHTML compatible
con la API v2 de Confluence Cloud (representación 'storage').

Características:
1. Protección estricta de fragmentos de código inline contra colisiones de formato
   (evita corrupción de patrones como `*.test.jsx` o `user_id`).
2. Resolución automática de enlaces relativos a código fuente hacia GitHub y de
   enlaces inter-documentales hacia macros nativas <ac:link><ri:page .../></ac:link>.
3. Renderizado local de diagramas Mermaid a PNG con nombres estables y código fuente expandible.
4. Renderizado local de fórmulas matemáticas complejas LaTeX ($$) a PNG con descripciones accesibles.
5. Conversión semántica rigurosa de expresiones matemáticas simples ($) a caracteres Unicode explícitos.
6. Inyección de identidad verificable de documento (comentario y tag oculto) para recuperación ante interrupciones.
7. Validación rigurosa de XML bien formado mediante xml.etree.ElementTree.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from asset_renderer import (
        convert_inline_math_in_text,
        create_confluence_image_storage,
        render_latex_math_to_png,
        render_mermaid_to_png,
    )
    from link_resolver import resolve_markdown_links
except ImportError:
    from .asset_renderer import (  # type: ignore
        convert_inline_math_in_text,
        create_confluence_image_storage,
        render_latex_math_to_png,
        render_mermaid_to_png,
    )
    from .link_resolver import resolve_markdown_links  # type: ignore


def _escape_xml_text(text: str) -> str:
    """Escapa caracteres especiales XML (&, <, >)."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def check_document_compatibility(
    markdown_text: str,
    file_name: str = "",
    manifest_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evalúa si un documento es 100% compatible para conversión y publicación a Confluence Storage.

    Valida:
    - Conversión de enlaces de código y páginas Confluence.
    - Renderizado local de diagramas Mermaid a PNG.
    - Renderizado local de fórmulas matemáticas complejas a PNG.
    - Conversión semántica de expresiones simples a Unicode.
    - Validación del árbol XML XHTML resultante con ElementTree.
    """
    reasons: List[str] = []

    # 1. Comprobar imágenes embebidas en Markdown
    for img_m in re.finditer(r"!\[(.*?)\]\((.*?)\)", markdown_text):
        alt = img_m.group(1)
        src = img_m.group(2)
        reasons.append(f"Contiene imagen embebida no procesada: ![{alt}]({src})")

    # 2. Intentar conversión completa para validar sintaxis, diagramas y fórmulas
    try:
        title, storage_xml = markdown_to_storage(
            markdown_text,
            source_file=file_name,
            manifest_data=manifest_data,
        )
        validate_storage_xml(storage_xml)
    except Exception as err:
        reasons.append(f"Error de conversión/validación: {err}")

    is_ready = len(reasons) == 0
    return {
        "file": file_name,
        "status": "ready" if is_ready else "blocked",
        "is_ready": is_ready,
        "reasons": reasons,
    }


def _check_unsupported_inline(line: str, line_num: int) -> None:
    """Verifica sintaxis inline no soportada o malformada."""
    # 1. Comillas invertidas de código en línea sin cerrar
    if line.count("`") % 2 != 0:
        raise ValueError(
            f"Sintaxis Markdown no soportada en línea {line_num}: comilla invertida (`) "
            f"de código en línea sin cerrar en '{line}'."
        )

    # 2. Remover contenido dentro de backticks y marcadores Confluence
    stripped = re.sub(r"`[^`]*`", "", line)
    stripped = re.sub(r"__CONFLUENCE_LINK_TITLE__.*?__ENDLINK__", "", stripped)

    # 3. HTML embebido o etiquetas XML no soportadas
    html_match = re.search(r"<\s*([a-zA-Z][a-zA-Z0-9]*)(?:\s+[^>]*)?>", stripped)
    if html_match:
        tag_name = html_match.group(1)
        raise ValueError(
            f"Markdown no soportado en línea {line_num}: se detectó etiqueta HTML embebida '<{tag_name}>'. "
            "Esta versión del publicador solo admite Markdown estándar puro."
        )

    # 4. Fórmulas matemáticas LaTeX ($ o $$) que no pudieron ser convertidas a Unicode
    if "$" in stripped:
        raise ValueError(
            f"Markdown no soportado en línea {line_num}: fórmulas matemáticas con delimitador '$' "
            f"remanente sin regla de conversión a Unicode en: '{line}'."
        )

    # 5. Notas al pie (footnotes [^1])
    if re.search(r"\[\^[^\]]+\]", stripped):
        raise ValueError(
            f"Markdown no soportado en línea {line_num}: notas al pie (footnotes '[^...]') no están soportadas."
        )


def _format_inline(text: str) -> str:
    """Convierte elementos inline de Markdown a XHTML (negrita, cursiva, código, enlaces).

    Utiliza sustitución por marcadores protegidos para evitar que fragmentos
    de código (ej. `*.test.jsx` o `user_id`) sean alterados por reglas de cursiva/negrita.
    """
    # 1. Extraer marcadores de enlaces Confluence generados por link_resolver
    confluence_links: List[str] = []

    def save_confluence_link(m: re.Match) -> str:
        full_match = m.group(0)
        title_match = re.search(r"__CONFLUENCE_LINK_TITLE__(.*?)__(?:ANCHOR__(.*?)__)?TEXT__(.*?)__ENDLINK__", full_match)
        if title_match:
            c_title = html.escape(title_match.group(1))
            c_anchor = html.escape(title_match.group(2)) if title_match.group(2) else ""
            c_text = html.escape(title_match.group(3))
            if c_anchor:
                xml_link = (
                    f'<ac:link><ri:page ri:content-title="{c_title}"/>'
                    f"<ac:link-anchor>{c_anchor}</ac:link-anchor>"
                    f"<ac:plain-text-link-body><![CDATA[{c_text}]]></ac:plain-text-link-body></ac:link>"
                )
            else:
                xml_link = (
                    f'<ac:link><ri:page ri:content-title="{c_title}"/>'
                    f"<ac:plain-text-link-body><![CDATA[{c_text}]]></ac:plain-text-link-body></ac:link>"
                )
            confluence_links.append(xml_link)
            return f"\x00CFLINK_{len(confluence_links)-1}\x00"
        return full_match

    text = re.sub(r"__CONFLUENCE_LINK_TITLE__.*?__ENDLINK__", save_confluence_link, text)

    # 2. Escapar texto plano para XML
    escaped = _escape_xml_text(text)

    # 3. Proteger fragmentos de código inline (`código`)
    codes: List[str] = []

    def save_code(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00CODE_{len(codes)-1}\x00"

    escaped = re.sub(r"`([^`]+)`", save_code, escaped)

    # 4. Enlaces Markdown estándar: [texto](url)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )

    # 5. Negrita: **texto** o __texto__
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", escaped)

    # 6. Cursiva: *texto* o _texto_
    escaped = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<em>\1</em>", escaped)
    escaped = re.sub(r"(?<![_\w])_([^_]+)_(?![_\w])", r"<em>\1</em>", escaped)

    # 7. Restaurar fragmentos de código inline como <code>...</code>
    for idx, c in enumerate(codes):
        escaped = escaped.replace(f"\x00CODE_{idx}\x00", f"<code>{c}</code>")

    # 8. Restaurar enlaces Confluence
    for idx, cflink in enumerate(confluence_links):
        escaped = escaped.replace(f"\x00CFLINK_{idx}\x00", cflink)

    return escaped


def markdown_to_storage(
    markdown_text: str,
    source_file: str = "documento.md",
    manifest_data: Optional[Dict[str, Any]] = None,
    return_attachments: bool = False,
) -> Union[Tuple[str, str], Tuple[str, str, List[Dict[str, Any]]]]:
    """Convierte texto Markdown a XHTML Confluence Storage Format.

    Args:
        markdown_text: Contenido en formato Markdown.
        source_file: Nombre o ruta del archivo de origen para trazabilidad de errores.
        manifest_data: Datos del manifiesto para resolver enlaces relativos a GitHub o Confluence.
        return_attachments: Si es True, retorna también la lista de adjuntos generados.

    Retorna:
        Tuple[str, str]: (titulo_extraido, xhtml_storage) por defecto,
        o Tuple[str, str, List[Dict[str, Any]]] si return_attachments=True.
    """
    # Si se suministra el manifiesto, resolver enlaces de código y páginas Confluence primero
    if manifest_data:
        markdown_text = resolve_markdown_links(markdown_text, source_file, manifest_data)

    doc_slug = Path(source_file).stem
    manifest_meta = manifest_data.get("metadata", {}) if manifest_data else {}
    space_id = str(manifest_meta.get("space_id", "2031619"))
    parent_id = str(manifest_meta.get("root_page_id", "2097153"))

    lines = markdown_text.splitlines()
    extracted_title = ""
    output_parts: List[str] = []
    generated_attachments: List[Dict[str, Any]] = []

    mermaid_counter = 0
    math_counter = 0

    # Inyectar marcador de identidad verificable de documento en el encabezado del storage
    identity_marker = (
        f"<!-- confluence-doc-identity: slug={doc_slug}; space_id={space_id}; parent_id={parent_id} -->\n"
        f'<p style="display:none">confluence-doc-identity:slug={doc_slug};space_id={space_id};parent_id={parent_id}</p>'
    )
    output_parts.append(identity_marker)

    i = 0
    n = len(lines)

    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()
        current_line_num = i + 1

        # Línea vacía
        if not line:
            i += 1
            continue

        # Bloque de código cercado (```lang ... ```)
        if line.startswith("```"):
            code_start_line = current_line_num
            lang = line[3:].strip()
            code_lines = []
            i += 1
            closed = False
            while i < n:
                if lines[i].strip().startswith("```"):
                    closed = True
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1

            if not closed:
                raise ValueError(
                    f"Error de sintaxis en {source_file}:{code_start_line}: bloque de código cercado "
                    "no fue cerrado con '```' antes del final del archivo."
                )

            code_content = "\n".join(code_lines)

            # Caso especial: Bloque Mermaid -> renderizar a PNG local
            if lang.lower() == "mermaid":
                mermaid_counter += 1
                img_filename = f"{doc_slug}-mermaid-{mermaid_counter}.png"
                alt_desc = f"Diagrama Mermaid {mermaid_counter}: {extracted_title or doc_slug}"
                asset_meta = render_mermaid_to_png(code_content, img_filename)
                generated_attachments.append(asset_meta)
                img_storage = create_confluence_image_storage(
                    filename=img_filename,
                    alt_text=alt_desc,
                    source_code=code_content,
                    source_lang="text",
                    expand_title=f"Código fuente del diagrama Mermaid ({img_filename})",
                )
                output_parts.append(img_storage)
                continue

            macro_lang = f'<ac:parameter ac:name="language">{html.escape(lang)}</ac:parameter>' if lang else ""
            macro = (
                '<ac:structured-macro ac:name="code" ac:schema-version="1">'
                f"{macro_lang}"
                '<ac:parameter ac:name="linenumbers">true</ac:parameter>'
                f"<ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body>"
                "</ac:structured-macro>"
            )
            output_parts.append(macro)
            continue

        # Bloque de fórmula matemática LaTeX ($$ ... $$)
        if line.startswith("$$"):
            math_counter += 1
            math_start_line = current_line_num

            # Comprobar si se abre y cierra en la misma línea: $$ formula $$
            if line.endswith("$$") and len(line) >= 4:
                formula_code = line[2:-2].strip()
                i += 1
            else:
                # Multilínea
                first_part = line[2:].strip()
                math_lines = [first_part] if first_part else []
                i += 1
                closed = False
                while i < n:
                    cur_str = lines[i].strip()
                    if cur_str.endswith("$$"):
                        closed = True
                        rem = cur_str[:-2].strip()
                        if rem:
                            math_lines.append(rem)
                        i += 1
                        break
                    math_lines.append(lines[i])
                    i += 1

                if not closed:
                    raise ValueError(
                        f"Error de sintaxis en {source_file}:{math_start_line}: bloque de fórmula LaTeX "
                        "no fue cerrado con '$$' antes del final del archivo."
                    )
                formula_code = "\n".join(math_lines).strip()

            img_filename = f"{doc_slug}-math-{math_counter}.png"
            alt_desc = f"Fórmula matemática {math_counter}: {doc_slug}"
            asset_meta = render_latex_math_to_png(formula_code, img_filename)
            generated_attachments.append(asset_meta)
            img_storage = create_confluence_image_storage(
                filename=img_filename,
                alt_text=alt_desc,
                source_code=formula_code,
                source_lang="latex",
                expand_title=f"Expresión matemática LaTeX ({img_filename})",
            )
            output_parts.append(img_storage)
            continue

        # Separador horizontal: --- o *** o ___
        if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", line):
            output_parts.append("<hr/>")
            i += 1
            continue

        # Título de nivel 1 (# Titulo)
        if line.startswith("# "):
            title_text = line[2:].strip()
            title_text = convert_inline_math_in_text(title_text)
            _check_unsupported_inline(title_text, current_line_num)
            if not extracted_title:
                extracted_title = title_text
            output_parts.append(f"<h1>{_format_inline(title_text)}</h1>")
            i += 1
            continue

        # Encabezados de niveles 2 a 6 (##, ###, etc.)
        header_match = re.match(r"^(#{2,6})\s+(.+)$", line)
        if header_match:
            level = len(header_match.group(1))
            heading_text = header_match.group(2).strip()
            heading_text = convert_inline_math_in_text(heading_text)
            _check_unsupported_inline(heading_text, current_line_num)
            output_parts.append(f"<h{level}>{_format_inline(heading_text)}</h{level}>")
            i += 1
            continue

        # Cita (Blockquote: > texto)
        if line.startswith(">"):
            quote_lines = []
            while i < n and lines[i].strip().startswith(">"):
                quote_line = lines[i].strip()
                quote_content = quote_line[1:].strip()
                quote_content = convert_inline_math_in_text(quote_content)
                _check_unsupported_inline(quote_content, i + 1)
                quote_lines.append(quote_content)
                i += 1
            quote_text = " ".join(quote_lines)
            output_parts.append(f"<blockquote><p>{_format_inline(quote_text)}</p></blockquote>")
            continue

        # Tablas Markdown (| col1 | col2 |)
        if line.startswith("|"):
            table_start_line = current_line_num
            table_lines: List[Tuple[int, str]] = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append((i + 1, lines[i].strip()))
                i += 1

            if len(table_lines) < 2:
                raise ValueError(
                    f"Tabla Markdown incompleta o malformada en {source_file}:{table_start_line}: "
                    "debe contener al menos una fila de cabecera y una fila separadora (| --- |)."
                )

            sep_line_num, sep_line = table_lines[1]
            if not re.match(r"^\|(?:\s*:?-+:?\s*\|)+$", sep_line):
                raise ValueError(
                    f"Fila separadora de tabla inválida en {source_file}:{sep_line_num}: '{sep_line}'. "
                    "Se requiere formato separador Markdown estándar (| --- | --- |)."
                )

            raw_header_cells = [c.strip() for c in table_lines[0][1].strip("|").split("|")]
            num_cols = len(raw_header_cells)
            sep_cells = [c.strip() for c in sep_line.strip("|").split("|")]
            if len(sep_cells) != num_cols:
                raise ValueError(
                    f"Número de columnas inconsistente en tabla en {source_file}:{sep_line_num}: "
                    f"la cabecera tiene {num_cols} columnas y el separador define {len(sep_cells)} columnas."
                )

            header_cells = [convert_inline_math_in_text(c) for c in raw_header_cells]
            for hc in header_cells:
                _check_unsupported_inline(hc, table_lines[0][0])

            rows: List[List[str]] = []
            for row_line_num, row_str in table_lines[2:]:
                raw_row_cells = [c.strip() for c in row_str.strip("|").split("|")]
                if len(raw_row_cells) != num_cols:
                    raise ValueError(
                        f"Fila de tabla con número de celdas inconsistente en {source_file}:{row_line_num}: "
                        f"se esperaban {num_cols} celdas pero se encontraron {len(raw_row_cells)} en '{row_str}'."
                    )
                converted_row_cells = [convert_inline_math_in_text(c) for c in raw_row_cells]
                for cell in converted_row_cells:
                    _check_unsupported_inline(cell, row_line_num)
                rows.append(converted_row_cells)

            table_html = ["<table><thead><tr>"]
            for hc in header_cells:
                table_html.append(f"<th>{_format_inline(hc)}</th>")
            table_html.append("</tr></thead><tbody>")
            for r in rows:
                table_html.append("<tr>")
                for cell in r:
                    table_html.append(f"<td>{_format_inline(cell)}</td>")
                table_html.append("</tr>")
            table_html.append("</tbody></table>")
            output_parts.append("".join(table_html))
            continue

        # Listas de tareas no soportadas (- [ ] o - [x])
        if re.match(r"^[\-\*]\s+\[[ xX]\]", line):
            raise ValueError(
                f"Sintaxis Markdown no soportada en {source_file}:{current_line_num}: "
                f"listas de tareas ('{line}') no están admitidas en esta versión."
            )

        # Lista desordenada (- item o * item)
        if re.match(r"^[\-\*]\s+(.+)$", line):
            list_items = []
            while i < n and re.match(r"^[\-\*]\s+(.+)$", lines[i].strip()):
                item_line = lines[i].strip()
                if re.match(r"^[\-\*]\s+\[[ xX]\]", item_line):
                    raise ValueError(
                        f"Sintaxis Markdown no soportada en {source_file}:{i + 1}: listas de tareas no admitidas."
                    )
                item_content = re.match(r"^[\-\*]\s+(.+)$", item_line).group(1)
                item_content = convert_inline_math_in_text(item_content)
                _check_unsupported_inline(item_content, i + 1)
                list_items.append(f"<li>{_format_inline(item_content)}</li>")
                i += 1
            output_parts.append(f"<ul>{''.join(list_items)}</ul>")
            continue

        # Lista ordenada (1. item)
        if re.match(r"^\d+\.\s+(.+)$", line):
            list_items = []
            while i < n and re.match(r"^\d+\.\s+(.+)$", lines[i].strip()):
                item_line = lines[i].strip()
                item_content = re.match(r"^\d+\.\s+(.+)$", item_line).group(1)
                item_content = convert_inline_math_in_text(item_content)
                _check_unsupported_inline(item_content, i + 1)
                list_items.append(f"<li>{_format_inline(item_content)}</li>")
                i += 1
            output_parts.append(f"<ol>{''.join(list_items)}</ol>")
            continue

        # Párrafo ordinario: acumula líneas continuas hasta línea vacía o bloque
        para_lines = []
        while i < n and lines[i].strip() and not _is_block_start(lines[i].strip()):
            p_line = lines[i].strip()
            p_line = convert_inline_math_in_text(p_line)
            _check_unsupported_inline(p_line, i + 1)
            para_lines.append(p_line)
            i += 1

        if para_lines:
            para_text = " ".join(para_lines)
            output_parts.append(f"<p>{_format_inline(para_text)}</p>")

    storage_xml = "\n".join(output_parts)

    # Validar que el storage generado es XML bien formado
    validate_storage_xml(storage_xml)

    if return_attachments:
        return extracted_title, storage_xml, generated_attachments
    return extracted_title, storage_xml


def _is_block_start(line: str) -> bool:
    """Determina si la línea inicia un nuevo bloque estructural."""
    if line.startswith("#"):
        return True
    if line.startswith("```"):
        return True
    if line.startswith("$$"):
        return True
    if line.startswith(">"):
        return True
    if line.startswith("|"):
        return True
    if re.match(r"^[\-\*]\s+", line):
        return True
    if re.match(r"^\d+\.\s+", line):
        return True
    if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", line):
        return True
    return False


def validate_storage_xml(storage_xml: str) -> None:
    """Comprueba que el XML producido sea sintácticamente válido.

    Envuelve el cuerpo en un elemento raíz con los espacios de nombres XML
    habituales de Confluence (ac y ri) para validar macros y etiquetas.
    """
    wrapper = (
        '<root xmlns:ac="http://atlassian.com/content" '
        'xmlns:ri="http://atlassian.com/resource/identifier">\n'
        f"{storage_xml}\n"
        "</root>"
    )
    try:
        ET.fromstring(wrapper)
    except ET.ParseError as err:
        raise ValueError(f"Error de validación XML en el storage generado: {err}") from err
