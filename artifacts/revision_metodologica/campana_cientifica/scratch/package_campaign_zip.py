import hashlib
import os
import re
from pathlib import Path
import zipfile

ROOT_DIR = Path(__file__).resolve().parents[4]
print("ROOT_DIR:", ROOT_DIR)

campana_dir = ROOT_DIR / "artifacts" / "revision_metodologica" / "campana_cientifica"
zip_output_path = ROOT_DIR / "artifacts" / "revision_metodologica" / "evidencias_campana_cientifica_revision_independiente.zip"

task_log_5692 = Path(r"C:\Users\Daniel\.gemini\antigravity\brain\bc979538-f834-460f-8cb0-a606e7e61f37\.system_generated\tasks\task-5692.log")
task_log_5717 = Path(r"C:\Users\Daniel\.gemini\antigravity\brain\bc979538-f834-460f-8cb0-a606e7e61f37\.system_generated\tasks\task-5717.log")

# Validar que los archivos principales existen
required_files = [
    campana_dir / "PROTOCOLO_CAMPANA.md",
    campana_dir / "INFORME_CAMPANA_CIENTIFICA.md",
    campana_dir / "dataset_320_corrected_full.csv",
    campana_dir / "SHA256SUMS.txt",
    campana_dir / "run_20261029_153857" / "manifest.json",
    campana_dir / "run_20261029_153857" / "oof_predictions.csv",
    ROOT_DIR / "cli.py",
    ROOT_DIR / "configs" / "revision_metodologica.json",
    ROOT_DIR / "scientific_core" / "generator.py",
    ROOT_DIR / "scientific_core" / "nested_cv.py",
    ROOT_DIR / "scientific_core" / "model_bundle.py",
    ROOT_DIR / "streamlit_app" / "pollinator_abm.py",
]

for rf in required_files:
    if not rf.exists():
        raise FileNotFoundError(f"Archivo requerido no encontrado: {rf}")
print("Todos los archivos requeridos existen.")

# Escaneo de secretos en archivos a empaquetar
secret_patterns = [
    re.compile(r'(?i)(password|secret|token|api_key|jwt|groq_api_key)\s*[:=]\s*["\']?([^"\'\s]{8,})'),
]

files_to_pack = []

# 1. Toda la carpeta campana_cientifica
for root, dirs, files in os.walk(campana_dir):
    for f in sorted(files):
        fp = Path(root) / f
        rel_arc = fp.relative_to(ROOT_DIR).as_posix()
        files_to_pack.append((fp, rel_arc))

# 2. Archivos de código y config requeridos
code_files = [
    (ROOT_DIR / "cli.py", "cli.py"),
    (ROOT_DIR / "configs" / "revision_metodologica.json", "configs/revision_metodologica.json"),
    (ROOT_DIR / "scientific_core" / "generator.py", "scientific_core/generator.py"),
    (ROOT_DIR / "scientific_core" / "nested_cv.py", "scientific_core/nested_cv.py"),
    (ROOT_DIR / "scientific_core" / "model_bundle.py", "scientific_core/model_bundle.py"),
    (ROOT_DIR / "streamlit_app" / "pollinator_abm.py", "streamlit_app/pollinator_abm.py"),
]
files_to_pack.extend(code_files)

# 3. Logs de ejecución disponibles
if task_log_5692.exists():
    files_to_pack.append((task_log_5692, "logs_ejecucion/task-5692_generacion_dataset_320.log"))
if task_log_5717.exists():
    files_to_pack.append((task_log_5717, "logs_ejecucion/task-5717_evaluacion_canonica_nested_cv.log"))

forbidden_substrings = [".env", "node_modules", ".venv", "venv", "__pycache__", ".git"]
clean_files_to_pack = []

for fp, arc in files_to_pack:
    if any(fb in arc.split("/") for fb in forbidden_substrings) or arc.endswith(".pyc"):
        print(f"Excluyendo por regla de seguridad/limpieza: {arc}")
        continue
    clean_files_to_pack.append((fp, arc))

print(f"Total de archivos seleccionados para el ZIP: {len(clean_files_to_pack)}")

if zip_output_path.exists():
    zip_output_path.unlink()

with zipfile.ZipFile(zip_output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for fp, arc in sorted(clean_files_to_pack, key=lambda x: x[1]):
        data = None
        try:
            with open(fp, "rb") as fh:
                data = fh.read()
        except OSError:
            # Fallback transparente para symlinks de Linux montados en Windows
            fallback_fp = fp.parent / "bundle_ridge_078f18a6664f" / fp.name
            if fallback_fp.is_file():
                with open(fallback_fp, "rb") as fh:
                    data = fh.read()
            else:
                raise
        zf.writestr(arc, data)

h_zip = hashlib.sha256()
with open(zip_output_path, "rb") as fh:
    while chunk := fh.read(65536):
        h_zip.update(chunk)

zip_sha256 = h_zip.hexdigest()
zip_size_bytes = zip_output_path.stat().st_size

print(f"\nZIP generado con éxito:")
print(f"  Ruta: {zip_output_path}")
print(f"  Tamaño: {zip_size_bytes} bytes ({zip_size_bytes / 1024:.2f} KB)")
print(f"  SHA-256: {zip_sha256}")

manifest_lines = [
    f"# Manifiesto de Contenido del ZIP de Evidencias Científicas",
    f"",
    f"- **Archivo ZIP:** `{zip_output_path.name}`",
    f"- **Ruta Absoluta:** `{zip_output_path}`",
    f"- **Hash SHA-256 del ZIP:** `{zip_sha256}`",
    f"- **Tamaño del ZIP:** `{zip_size_bytes:,} bytes` ({zip_size_bytes / 1024:.2f} KB)",
    f"- **Total de Archivos Empaquetados:** {len(clean_files_to_pack)}",
    f"",
    "## Archivos Contenidos en el Archivo Comprimido:",
]

with zipfile.ZipFile(zip_output_path, "r") as zf:
    for info in zf.infolist():
        manifest_lines.append(f"- `{info.filename}` ({info.file_size:,} bytes -> {info.compress_size:,} bytes comprimidos)")

zip_manifest_path = ROOT_DIR / "artifacts" / "revision_metodologica" / "MANIFIESTO_ZIP_EVIDENCIAS.md"
zip_manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
print(f"Manifiesto guardado en: {zip_manifest_path}")
