"""Módulo de renderizado local de activos visuales y conversión matemática.

Proporciona utilidades para:
1. Renderizado local 100% offline de diagramas Mermaid a PNG mediante Headless Chrome.
2. Renderizado local de fórmulas matemáticas complejas LaTeX ($$) a PNG mediante KaTeX + Headless Chrome.
3. Conversión semántica rigurosa de expresiones matemáticas simples ($) a caracteres Unicode explícitos.
4. Auto-recorte inteligente de márgenes blancos mediante Pillow.
5. Generación de nombres deterministas estables y cálculo de huellas SHA-256 para gestión de adjuntos.
6. Generación de fragmentos XHTML para Confluence Storage Format con descripciones accesibles (ac:alt)
   y preservación del código fuente original mediante macros <ac:structured-macro ac:name="expand">.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageChops

TOOLS_DIR = Path(__file__).resolve().parent
RENDERED_ASSETS_DIR = TOOLS_DIR / "rendered_assets"


def get_chrome_executable() -> str:
    """Detecta la ruta al ejecutable de Chrome, Edge o Chromium en el sistema."""
    env_chrome = os.environ.get("CHROME_BIN") or os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if env_chrome and Path(env_chrome).is_file():
        return env_chrome

    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("msedge"),
    ]

    for c in candidates:
        if c and Path(c).is_file():
            return c

    raise RuntimeError(
        "No se encontró un navegador compatible (Chrome / Edge / Chromium) para el renderizado local de diagramas y fórmulas. "
        "Asegúrese de tener Google Chrome o Microsoft Edge instalado o defina la variable CHROME_BIN."
    )


def crop_image_to_content(image_path: Path, padding: int = 16) -> None:
    """Elimina márgenes blancos excesivos alrededor de la figura generada usando Pillow."""
    img = Image.open(image_path).convert("RGB")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(img.width, right + padding)
        bottom = min(img.height, bottom + padding)
        cropped = img.crop((left, top, right, bottom))
        cropped.save(image_path, "PNG")


def compute_file_sha256(file_path: Path) -> str:
    """Calcula el hash SHA-256 del contenido de un archivo en disco."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ==============================================================================
# CONVERSIÓN SEMÁNTICA DE MATEMÁTICAS SIMPLES A UNICODE
# ==============================================================================

# Tabla de reglas de equivalencia semántica estricta LaTeX -> Unicode
UNICODE_RULES: List[Tuple[str, str]] = [
    # Unidades y combinaciones frecuentes
    (r"\^\{\s*\\circ\s*\}\s*(?:\\text\{\s*C\s*\}|C)?", "°C"),
    (r"\^\s*\\circ\s*(?:\\text\{\s*C\s*\}|C)?", "°C"),
    (r"\^2", "²"),
    (r"\^3", "³"),
    # Espaciado y símbolos especiales
    (r"\\;", " "),
    (r"\\,", " "),
    (r"\\_", "_"),
    (r"\\%", "%"),
    # Letras griegas
    (r"\\alpha(?![a-zA-Z])", "α"),
    (r"\\eta(?![a-zA-Z])", "η"),
    (r"\\Delta(?![a-zA-Z])", "Δ"),
    (r"\\mu(?![a-zA-Z])", "μ"),
    (r"\\sigma(?![a-zA-Z])", "σ"),
    # Operadores lógicos y de flechas
    (r"\\land(?![a-zA-Z])", "∧"),
    (r"\\lor(?![a-zA-Z])", "∨"),
    (r"\\leftrightarrow(?![a-zA-Z])", "↔"),
    (r"\\leftarrow(?![a-zA-Z])", "←"),
    (r"\\rightarrow(?![a-zA-Z])", "→"),
    # Operadores y relaciones
    (r"\\sum(?![a-zA-Z])", "∑"),
    (r"\\times(?![a-zA-Z])", "×"),
    (r"\\leq?(?![a-zA-Z])", "≤"),
    (r"\\geq?(?![a-zA-Z])", "≥"),
    (r"\\in(?![a-zA-Z])", "∈"),
    (r"\\neq(?![a-zA-Z])", "≠"),
    (r"\\approx(?![a-zA-Z])", "≈"),
    (r"\\pm(?![a-zA-Z])", "±"),
    # Subíndices numéricos frecuentes
    (r"_1\b", "₁"),
    (r"_2\b", "₂"),
    (r"_3\b", "₃"),
    (r"_4\b", "₄"),
    (r"_5\b", "₅"),
    # Subíndices con texto: _{cand} -> _cand
    (r"_\{([a-zA-Z0-9_]+)\}", r"_\1"),
]


def convert_simple_math_to_unicode(expression: str) -> str:
    """Convierte una expresión matemática simple delimitada por $ a texto plano Unicode.

    Aplica reglas semánticas explícitas para preservar el significado matemático exacto.
    Si la expresión contiene construcciones no soportadas o incompletas, levanta ValueError.
    """
    clean = expression.strip()

    # 1. Aplicar reglas semánticas prioritarias (ej. unidades compuestas como ^\circ\text{C})
    for pattern, replacement in UNICODE_RULES:
        clean = re.sub(pattern, replacement, clean)

    # 2. Desenvolver \text{...} y \mathrm{...}
    clean = re.sub(r"\\(?:text|mathrm)\{([^{}]+)\}", r"\1", clean)

    # 3. Aplicar nuevamente reglas por si quedaron comandos tras desenvolvimiento
    for pattern, replacement in UNICODE_RULES:
        clean = re.sub(pattern, replacement, clean)

    # 4. Normalizar espacios
    clean = re.sub(r"\s+", " ", clean).strip()

    # 5. Ajustar espaciado de operadores binarios habituales si quedaron pegados
    clean = re.sub(r"(\w)\s*=\s*(\w|\d)", r"\1 = \2", clean)

    # 6. Comprobar que no hayan quedado barras invertidas (\) sin convertir
    if "\\" in clean:
        raise ValueError(f"Expresión matemática contiene comandos LaTeX no soportados para Unicode: '{expression}' (resultado parcial: '{clean}')")

    return clean


def convert_inline_math_in_text(text: str) -> str:
    """Busca y convierte todas las expresiones matemáticas inline $...$ a Unicode en una línea o párrafo.

    Preserva los bloques de código y código inline.
    """
    # Proteger código inline
    code_spans: List[str] = []

    def save_code(m: re.Match) -> str:
        code_spans.append(m.group(0))
        return f"\x00CODE_{len(code_spans)-1}\x00"

    protected = re.sub(r"`[^`]*`", save_code, text)

    def replace_math(m: re.Match) -> str:
        inner = m.group(1)
        converted = convert_simple_math_to_unicode(inner)
        return converted

    # Detectar $...$ que no sea $$...$$
    converted = re.sub(r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)", replace_math, protected)

    # Restaurar código inline
    for idx, span in enumerate(code_spans):
        converted = converted.replace(f"\x00CODE_{idx}\x00", span)

    return converted


# ==============================================================================
# RENDERIZADO LOCAL DE MERMAID A PNG
# ==============================================================================


def render_mermaid_to_png(
    mermaid_code: str,
    output_filename: str,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Renderiza un bloque de código Mermaid a un archivo PNG local usando Headless Chrome.

    Retorna un diccionario con metadatos:
    - filename: nombre del archivo PNG generado
    - path: ruta absoluta al archivo
    - sha256: hash SHA-256 del archivo
    - dimensions: (width, height)
    - size_bytes: tamaño del archivo en bytes
    """
    target_dir = output_dir or RENDERED_ASSETS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / output_filename

    chrome_bin = get_chrome_executable()
    mermaid_js = (TOOLS_DIR / "node_modules" / "mermaid" / "dist" / "mermaid.min.js").resolve()
    if not mermaid_js.is_file():
        raise FileNotFoundError(
            f"No se encontró la biblioteca Mermaid en: {mermaid_js}. "
            "Asegúrese de ejecutar 'npm install' en 'tools/docs'."
        )

    # Generar HTML autocontenido
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="{mermaid_js.as_uri()}"></script>
<script>
mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
</script>
<style>
body {{
    background: white;
    margin: 0;
    padding: 24px;
    display: inline-block;
    font-family: Arial, sans-serif;
}}
</style>
</head>
<body>
<div class="mermaid">
{mermaid_code}
</div>
</body>
</html>
"""

    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as tf:
        temp_html_path = Path(tf.name)
        tf.write(html_content)

    try:
        cmd = [
            chrome_bin,
            "--headless",
            "--disable-gpu",
            "--virtual-time-budget=3000",
            f"--screenshot={out_file.resolve()}",
            temp_html_path.as_uri(),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not out_file.is_file() or out_file.stat().st_size == 0:
            raise RuntimeError(f"Fallo en la generación de captura de Mermaid para {output_filename}")

        crop_image_to_content(out_file, padding=16)

        with Image.open(out_file) as img:
            dims = img.size

        return {
            "filename": output_filename,
            "path": str(out_file.resolve()),
            "sha256": compute_file_sha256(out_file),
            "dimensions": dims,
            "size_bytes": out_file.stat().st_size,
            "content_type": "image/png",
        }
    finally:
        if temp_html_path.is_file():
            temp_html_path.unlink()


# ==============================================================================
# RENDERIZADO LOCAL DE FÓRMULAS MATEMÁTICAS COMPLEJAS A PNG
# ==============================================================================


def render_latex_math_to_png(
    latex_formula: str,
    output_filename: str,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Renderiza una fórmula matemática LaTeX ($$) a PNG local usando KaTeX y Headless Chrome.

    Retorna un diccionario con metadatos:
    - filename: nombre del archivo PNG generado
    - path: ruta absoluta al archivo
    - sha256: hash SHA-256 del archivo
    - dimensions: (width, height)
    - size_bytes: tamaño del archivo en bytes
    """
    target_dir = output_dir or RENDERED_ASSETS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / output_filename

    chrome_bin = get_chrome_executable()
    katex_js = (TOOLS_DIR / "node_modules" / "katex" / "dist" / "katex.min.js").resolve()
    katex_css = (TOOLS_DIR / "node_modules" / "katex" / "dist" / "katex.min.css").resolve()

    if not katex_js.is_file() or not katex_css.is_file():
        raise FileNotFoundError(
            f"No se encontró KaTeX en: {TOOLS_DIR / 'node_modules' / 'katex'}. "
            "Asegúrese de ejecutar 'npm install' en 'tools/docs'."
        )

    # Generar HTML con KaTeX
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="{katex_css.as_uri()}">
<script src="{katex_js.as_uri()}"></script>
<style>
body {{
    background: white;
    margin: 0;
    padding: 24px;
    font-size: 26px;
    display: inline-block;
    color: #172B4D;
}}
</style>
</head>
<body>
<div id="math-container"></div>
<script>
try {{
    katex.render({repr(latex_formula.strip())}, document.getElementById('math-container'), {{
        displayMode: true,
        throwOnError: true
    }});
}} catch (err) {{
    document.body.innerHTML = '<div style="color:red;font-size:16px;">ERROR: ' + err.toString() + '</div>';
}}
</script>
</body>
</html>
"""

    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as tf:
        temp_html_path = Path(tf.name)
        tf.write(html_content)

    try:
        cmd = [
            chrome_bin,
            "--headless",
            "--disable-gpu",
            "--virtual-time-budget=2000",
            f"--screenshot={out_file.resolve()}",
            temp_html_path.as_uri(),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not out_file.is_file() or out_file.stat().st_size == 0:
            raise RuntimeError(f"Fallo en la generación de imagen para fórmula {output_filename}")

        crop_image_to_content(out_file, padding=16)

        with Image.open(out_file) as img:
            dims = img.size

        return {
            "filename": output_filename,
            "path": str(out_file.resolve()),
            "sha256": compute_file_sha256(out_file),
            "dimensions": dims,
            "size_bytes": out_file.stat().st_size,
            "content_type": "image/png",
        }
    finally:
        if temp_html_path.is_file():
            temp_html_path.unlink()


# ==============================================================================
# GENERACIÓN DE FRAGMENTOS XML CONFLUENCE STORAGE FORMAT
# ==============================================================================


def create_confluence_image_storage(
    filename: str,
    alt_text: str,
    source_code: str,
    source_lang: str = "text",
    expand_title: str = "Ver código fuente",
) -> str:
    """Crea la estructura XHTML Confluence Storage Format para una imagen adjunta con descripción y fuente expandible.

    Cumple con:
    1. Etiqueta nativa <ac:image ac:alt="..."> con referencia a adjunto <ri:attachment ri:filename="..."/>.
    2. Macro expandible <ac:structured-macro ac:name="expand"> conteniendo el código fuente original.
    3. Texto alternativo accesible para lectores de pantalla.
    """
    esc_filename = html.escape(filename)
    esc_alt = html.escape(alt_text)
    esc_expand_title = html.escape(expand_title)
    esc_lang = html.escape(source_lang)

    storage = (
        f'<p><ac:image ac:alt="{esc_alt}">'
        f'<ri:attachment ri:filename="{esc_filename}"/>'
        "</ac:image></p>\n"
        '<ac:structured-macro ac:name="expand" ac:schema-version="1">\n'
        f'  <ac:parameter ac:name="title">{esc_expand_title}</ac:parameter>\n'
        "  <ac:rich-text-body>\n"
        '    <ac:structured-macro ac:name="code" ac:schema-version="1">\n'
        f'      <ac:parameter ac:name="language">{esc_lang}</ac:parameter>\n'
        '      <ac:parameter ac:name="linenumbers">true</ac:parameter>\n'
        f"      <ac:plain-text-body><![CDATA[{source_code.strip()}]]></ac:plain-text-body>\n"
        "    </ac:structured-macro>\n"
        "  </ac:rich-text-body>\n"
        "</ac:structured-macro>"
    )
    return storage
