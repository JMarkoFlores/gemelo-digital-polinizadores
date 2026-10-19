"""Conversor de Markdown a Confluence Storage Format (XHTML).

Este módulo convierte texto Markdown estándar (encabezados, párrafos, listas
ordenadas y desordenadas, tablas, citas y bloques de código) a XHTML compatible
con la API v2 de Confluence Cloud (representación 'storage').

Falla tempranamente con errores explícitos ante Markdown no soportado o malformado
(HTML embebido, listas de tareas, fórmulas matemáticas, notas al pie, bloques
de código no cerrados, tablas malformadas o comillas invertidas sin cerrar),
en lugar de publicar contenido mutilado silenciosamente.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from typing import Tuple


def _escape_xml_text(text: str) -> str:
    """Escapa caracteres especiales XML (&, <, >)."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _check_unsupported_inline(line: str, line_num: int) -> None:
    """Verifica sintaxis inline no soportada o malformada."""
    # 1. Comillas invertidas de código en línea sin cerrar
    # Si la línea tiene un número impar de backticks, hay un bloque inline abierto
    if line.count("`") % 2 != 0:
        raise ValueError(
            f"Sintaxis Markdown no soportada en línea {line_num}: comilla invertida (`) "
            f"de código en línea sin cerrar en '{line}'."
        )

    # 2. Remover contenido dentro de backticks para no confundir código con HTML o extensiones
    stripped = re.sub(r"`[^`]*`", "", line)

    # 3. HTML embebido o etiquetas XML no soportadas
    html_match = re.search(r"<\s*([a-zA-Z][a-zA-Z0-9]*)(?:\s+[^>]*)?>", stripped)
    if html_match:
        tag_name = html_match.group(1)
        raise ValueError(
            f"Markdown no soportado en línea {line_num}: se detectó etiqueta HTML embebida '<{tag_name}>'. "
            "Esta versión del publicador solo admite Markdown estándar puro."
        )

    # 4. Fórmulas matemáticas LaTeX ($ o $$)
    if "$" in stripped:
        raise ValueError(
            f"Markdown no soportado en línea {line_num}: fórmulas matemáticas con delimitador '$' no están soportadas."
        )

    # 5. Notas al pie (footnotes [^1])
    if re.search(r"\[\^[^\]]+\]", stripped):
        raise ValueError(
            f"Markdown no soportado en línea {line_num}: notas al pie (footnotes '[^...]') no están soportadas."
        )


def _format_inline(text: str) -> str:
    """Convierte elementos inline de Markdown a XHTML (negrita, cursiva, código, enlaces).

    Primero escapa caracteres especiales y luego aplica las transformaciones
    de formato para evitar inyecciones XML no deseadas.
    """
    # 1. Escapar texto plano
    escaped = _escape_xml_text(text)

    # 2. Código en línea: `código`
    escaped = re.sub(
        r"`([^`]+)`",
        r"<code>\1</code>",
        escaped,
    )

    # 3. Enlaces: [texto](url)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )

    # 4. Negrita: **texto** o __texto__
    escaped = re.sub(
        r"\*\*([^*]+)\*\*",
        r"<strong>\1</strong>",
        escaped,
    )
    escaped = re.sub(
        r"__([^_]+)__",
        r"<strong>\1</strong>",
        escaped,
    )

    # 5. Cursiva: *texto* o _texto_ (evitando colisión con negrita ya convertida)
    escaped = re.sub(
        r"(?<![*\w])\*([^*]+)\*(?![*\w])",
        r"<em>\1</em>",
        escaped,
    )
    escaped = re.sub(
        r"(?<![_\w])_([^_]+)_(?![_\w])",
        r"<em>\1</em>",
        escaped,
    )

    return escaped


def markdown_to_storage(markdown_text: str) -> Tuple[str, str]:
    """Convierte texto Markdown a XHTML Confluence Storage Format.

    Falla con ValueError si detecta elementos no soportados o malformados.

    Retorna:
        Tuple[str, str]: (titulo_extraido, xhtml_storage)
    """
    lines = markdown_text.splitlines()
    extracted_title = ""
    output_parts: list[str] = []

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
                    f"Error de sintaxis en línea {code_start_line}: bloque de código cercado "
                    "no fue cerrado con '```' antes del final del archivo."
                )

            code_content = "\n".join(code_lines)
            # Confluence macro de código
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

        # Validar sintaxis inline en líneas fuera de bloques de código
        _check_unsupported_inline(line, current_line_num)

        # Separador horizontal: --- o *** o ___
        if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", line):
            output_parts.append("<hr/>")
            i += 1
            continue

        # Título de nivel 1 (# Titulo)
        if line.startswith("# "):
            title_text = line[2:].strip()
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
            output_parts.append(f"<h{level}>{_format_inline(heading_text)}</h{level}>")
            i += 1
            continue

        # Cita (Blockquote: > texto)
        if line.startswith(">"):
            quote_lines = []
            while i < n and lines[i].strip().startswith(">"):
                quote_line = lines[i].strip()
                _check_unsupported_inline(quote_line, i + 1)
                quote_lines.append(quote_line[1:].strip())
                i += 1
            quote_text = " ".join(quote_lines)
            output_parts.append(f"<blockquote><p>{_format_inline(quote_text)}</p></blockquote>")
            continue

        # Tablas Markdown (| col1 | col2 |)
        if line.startswith("|"):
            table_start_line = current_line_num
            table_lines: list[tuple[int, str]] = []
            while i < n and lines[i].strip().startswith("|"):
                table_lines.append((i + 1, lines[i].strip()))
                i += 1

            if len(table_lines) < 2:
                raise ValueError(
                    f"Tabla Markdown incompleta o malformada en línea {table_start_line}: "
                    "debe contener al menos una fila de cabecera y una fila separadora (| --- |)."
                )

            # Validar fila separadora
            sep_line_num, sep_line = table_lines[1]
            if not re.match(r"^\|(?:\s*:?-+:?\s*\|)+$", sep_line):
                raise ValueError(
                    f"Fila separadora de tabla inválida en línea {sep_line_num}: '{sep_line}'. "
                    "Se requiere formato separador Markdown estándar (| --- | --- |)."
                )

            header_cells = [c.strip() for c in table_lines[0][1].strip("|").split("|")]
            num_cols = len(header_cells)
            sep_cells = [c.strip() for c in sep_line.strip("|").split("|")]
            if len(sep_cells) != num_cols:
                raise ValueError(
                    f"Número de columnas inconsistente en tabla en línea {sep_line_num}: "
                    f"la cabecera tiene {num_cols} columnas y el separador define {len(sep_cells)} columnas."
                )

            rows: list[list[str]] = []
            for row_line_num, row_str in table_lines[2:]:
                _check_unsupported_inline(row_str, row_line_num)
                row_cells = [c.strip() for c in row_str.strip("|").split("|")]
                if len(row_cells) != num_cols:
                    raise ValueError(
                        f"Fila de tabla con número de celdas inconsistente en línea {row_line_num}: "
                        f"se esperaban {num_cols} celdas pero se encontraron {len(row_cells)} en '{row_str}'."
                    )
                rows.append(row_cells)

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
                f"Sintaxis Markdown no soportada en línea {current_line_num}: "
                f"listas de tareas ('{line}') no están admitidas en esta versión."
            )

        # Lista desordenada (- item o * item)
        if re.match(r"^[\-\*]\s+(.+)$", line):
            list_items = []
            while i < n and re.match(r"^[\-\*]\s+(.+)$", lines[i].strip()):
                item_line = lines[i].strip()
                if re.match(r"^[\-\*]\s+\[[ xX]\]", item_line):
                    raise ValueError(
                        f"Sintaxis Markdown no soportada en línea {i + 1}: listas de tareas no admitidas."
                    )
                _check_unsupported_inline(item_line, i + 1)
                item_content = re.match(r"^[\-\*]\s+(.+)$", item_line).group(1)
                list_items.append(f"<li>{_format_inline(item_content)}</li>")
                i += 1
            output_parts.append(f"<ul>{''.join(list_items)}</ul>")
            continue

        # Lista ordenada (1. item)
        if re.match(r"^\d+\.\s+(.+)$", line):
            list_items = []
            while i < n and re.match(r"^\d+\.\s+(.+)$", lines[i].strip()):
                item_line = lines[i].strip()
                _check_unsupported_inline(item_line, i + 1)
                item_content = re.match(r"^\d+\.\s+(.+)$", item_line).group(1)
                list_items.append(f"<li>{_format_inline(item_content)}</li>")
                i += 1
            output_parts.append(f"<ol>{''.join(list_items)}</ol>")
            continue

        # Párrafo ordinario: acumula líneas continuas hasta línea vacía o bloque
        para_lines = []
        while i < n and lines[i].strip() and not _is_block_start(lines[i].strip()):
            p_line = lines[i].strip()
            _check_unsupported_inline(p_line, i + 1)
            para_lines.append(p_line)
            i += 1

        if para_lines:
            para_text = " ".join(para_lines)
            output_parts.append(f"<p>{_format_inline(para_text)}</p>")

    storage_xml = "\n".join(output_parts)

    # Validar que el storage generado es XML bien formado
    validate_storage_xml(storage_xml)

    return extracted_title, storage_xml


def _is_block_start(line: str) -> bool:
    """Determina si la línea inicia un nuevo bloque estructural."""
    if line.startswith("#"):
        return True
    if line.startswith("```"):
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
