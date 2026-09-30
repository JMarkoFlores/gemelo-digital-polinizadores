import os
import re
import time
from pathlib import Path

# Import metadata from existing generator
from generate_word_document import MODULES, FILE_DESCRIPTIONS, get_language

def get_markdown_fence(content, default_lang):
    # Find longest streak of backticks in content
    matches = re.findall(r'`+', content)
    max_backticks = max([len(m) for m in matches], default=0)
    num_ticks = max(3, max_backticks + 1)
    fence = '`' * num_ticks
    return fence, default_lang

def get_fence_lang(filename):
    ext = Path(filename).suffix.lower()
    mapping = {
        ".py": "python",
        ".jsx": "jsx",
        ".js": "javascript",
        ".css": "css",
        ".html": "html",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".md": "markdown",
        ".toml": "toml",
        ".txt": "text",
        ".example": "properties",
        ".dockerignore": "dockerignore",
    }
    if Path(filename).name == "Dockerfile":
        return "dockerfile"
    return mapping.get(ext, "")

def build_markdown_document():
    print("Iniciando la construcción del documento Markdown...")
    t0 = time.time()
    
    # 1. Collect file records
    file_records = []
    total_files = 0
    total_lines = 0
    total_bytes = 0
    
    for mod in MODULES:
        for rel_path in mod["files"]:
            p = Path(rel_path)
            if not p.exists():
                print(f"Advertencia: Archivo no encontrado: {rel_path}")
                continue
            try:
                raw = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raw = p.read_text(encoding="latin-1")
            
            lines = raw.splitlines()
            size = p.stat().st_size
            
            total_files += 1
            total_lines += len(lines)
            total_bytes += size
            
            desc = FILE_DESCRIPTIONS.get(rel_path, "Archivo de código fuente del sistema.")
            lang_label = get_language(rel_path)
            fence_lang = get_fence_lang(rel_path)
            
            file_records.append({
                "module_id": mod["id"],
                "module_name": mod["name"],
                "module_color": mod["color"],
                "rel_path": rel_path,
                "language": lang_label,
                "fence_lang": fence_lang,
                "lines_count": len(lines),
                "size_bytes": size,
                "description": desc,
                "content": raw,
            })
            
    print(f"Estadísticas: {total_files} archivos, {total_lines:,} líneas de código, {total_bytes / (1024*1024):.2f} MB")

    md_lines = []
    
    # Header & Cover
    md_lines.append("# EXPEDIENTE TÉCNICO DE SOFTWARE")
    md_lines.append("# SISTEMA DE GEMELOS DIGITALES AGROECOLÓGICOS PARA POLINIZADORES")
    md_lines.append("## Compilación Integral y Exhaustiva del Código Fuente — Separado por Archivo\n")
    md_lines.append("> **Repositorio Oficial:** `JMarkoFlores / gemelo-digital-polinizadores`  \n"
                    "> **Fecha de Compilación:** Septiembre 2026  \n"
                    "> **Cobertura:** 100% del código fuente, configuración e infraestructura sin truncamiento.\n")
    md_lines.append("---\n")
    
    # Summary Table
    md_lines.append("### 📊 Ficha Técnica del Proyecto\n")
    md_lines.append("| Parámetro | Detalle |")
    md_lines.append("| :--- | :--- |")
    md_lines.append(f"| **Total de Archivos Incluidos** | **{total_files} archivos** |")
    md_lines.append(f"| **Volumen Total de Código** | **{total_lines:,} líneas** |")
    md_lines.append(f"| **Tamaño Total en Disco** | **{total_bytes / 1024:.1f} KB** ({total_bytes / (1024*1024):.2f} MB) |")
    md_lines.append("| **Backend** | Python 3.13, FastAPI, SQLAlchemy, Uvicorn, PostgreSQL, PyJWT, bcrypt |")
    md_lines.append("| **Frontend** | React 18, Vite, Tailwind CSS, Three.js (Dioramas 3D), Leaflet (Mapas), Lucide Icons |")
    md_lines.append("| **Motor de Gemelos Digitales & ML** | Streamlit, Modelos Basados en Agentes (ABM), Scikit-Learn, PyTorch, Plotly, SciPy |")
    md_lines.append("| **Agentes IA & Despliegue** | Langflow (flujos conversacionales agroecológicos), Docker, Docker Compose |")
    md_lines.append("\n---\n")
    
    # Architecture Overview
    md_lines.append("### 🏗️ Arquitectura Modular del Sistema\n")
    md_lines.append(
        "El presente repositorio implementa un gemelo digital completo orientado a la agroecología, "
        "la conservación de hábitats y la optimización de servicios de polinización. La solución "
        "se organiza en 5 componentes arquitectónicos desacoplados:\n\n"
        "1. **Módulo 1: Configuración Raíz e Infraestructura Docker**: Orquestación multi-contenedor con Docker Compose, variables de entorno y documentación técnica.\n"
        "2. **Módulo 2: Backend API REST y Servicios ML (FastAPI)**: API asíncrona de alto rendimiento, modelos relacionales en PostgreSQL con SQLAlchemy, algoritmos de optimización espacial y asistente de recomendaciones.\n"
        "3. **Módulo 3: Frontend Web, Componentes y Visualización 3D (React / Vite)**: Single Page Application (SPA) con mapas interactivos (Leaflet), dioramas tridimensionales (Three.js), tableros ejecutivos y roles de usuario.\n"
        "4. **Módulo 4: Motor de Simulación y Gemelo Digital (Streamlit)**: Plataforma biofísica con simulación basada en agentes (ABM) para polinizadores, pipeline de entrenamiento de modelos híbridos y pruebas estadísticas robustas.\n"
        "5. **Módulo 5: Agentes de IA (Langflow) y Scripts de Soporte**: Flujos declarativos de inferencia agroecológica y pruebas de rangos estadísticos (Nemenyi).\n"
    )
    md_lines.append("---\n")
    
    # Master Table of Contents
    md_lines.append("## 📋 Índice General y Catálogo de Archivos\n")
    md_lines.append("| N° | Módulo | Ruta del Archivo | Lenguaje | Líneas | Propósito / Rol Técnico |")
    md_lines.append("| :---: | :--- | :--- | :---: | ---: | :--- |")
    
    for idx, rec in enumerate(file_records, 1):
        clean_anchor = f"archivo-{idx:02d}---{rec['rel_path'].replace('/', '').replace('.', '').replace('-', '').replace('_', '').lower()}"
        path_link = f"[`{rec['rel_path']}`](#archivo-{idx:02d}--{re.sub(r'[^a-zA-Z0-9]', '', rec['rel_path'].lower())})"
        md_lines.append(
            f"| {idx:02d} | Módulo {rec['module_id']} | {path_link} | {rec['language']} | {rec['lines_count']:,} | {rec['description']} |"
        )
    md_lines.append("\n---\n")

    # Code listings by module
    global_file_counter = 0
    for mod in MODULES:
        md_lines.append(f"# {mod['name']}\n")
        md_lines.append(f"> *{mod['description']}*\n")
        
        mod_records = [r for r in file_records if r["module_id"] == mod["id"]]
        for rec in mod_records:
            global_file_counter += 1
            print(f"[{global_file_counter}/{len(file_records)}] Exportando a Markdown: {rec['rel_path']} ({rec['lines_count']} líneas)...")
            
            anchor_id = f"archivo-{global_file_counter:02d}--{re.sub(r'[^a-zA-Z0-9]', '', rec['rel_path'].lower())}"
            md_lines.append(f'<a id="{anchor_id}"></a>\n')
            md_lines.append(f"## Archivo #{global_file_counter:02d} — `{rec['rel_path']}`\n")
            
            # Metadata table for file
            size_kb = rec['size_bytes'] / 1024.0
            md_lines.append("| Parámetro | Detalle |")
            md_lines.append("| :--- | :--- |")
            md_lines.append(f"| **Ruta Relativa** | `{rec['rel_path']}` |")
            md_lines.append(f"| **Módulo** | Módulo {rec['module_id']} |")
            md_lines.append(f"| **Lenguaje / Formato** | {rec['language']} |")
            md_lines.append(f"| **Líneas de Código** | {rec['lines_count']:,} líneas |")
            md_lines.append(f"| **Tamaño** | {size_kb:.1f} KB ({rec['size_bytes']:,} bytes) |")
            md_lines.append(f"| **Propósito Técnico** | {rec['description']} |")
            md_lines.append("")
            
            # Code block with dynamic fence to prevent markdown breakages
            fence, lang = get_markdown_fence(rec["content"], rec["fence_lang"])
            md_lines.append(f"{fence}{lang}")
            if rec["content"].strip():
                md_lines.append(rec["content"])
            else:
                md_lines.append("# (Archivo vacío)")
            md_lines.append(f"{fence}\n")
            md_lines.append("---\n")

    # Write output Markdown file
    output_filename = "CODIGO_COMPLETO_PROYECTO_GEMELOS_DIGITALES.md"
    print(f"Escribiendo archivo Markdown en '{output_filename}'...")
    final_content = "\n".join(md_lines)
    
    Path(output_filename).write_text(final_content, encoding="utf-8")
    
    # Also save a copy with a simple name
    copy_filename = "CODIGO_COMPLETO_PROYECTO.md"
    Path(copy_filename).write_text(final_content, encoding="utf-8")
    
    total_time = time.time() - t0
    final_size = Path(output_filename).stat().st_size
    print(f"¡Documento Markdown generado con éxito!")
    print(f"Archivo generado: {output_filename}")
    print(f"Copia alternativa: {copy_filename}")
    print(f"Tamaño final: {final_size / 1024:.1f} KB ({final_size / (1024*1024):.2f} MB)")
    print(f"Tiempo total: {total_time:.2f} segundos")
    return output_filename

if __name__ == "__main__":
    build_markdown_document()
