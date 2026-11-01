import hashlib
from pathlib import Path

campana_dir = Path(__file__).resolve().parent.parent

files_to_hash = []
for p in sorted(campana_dir.rglob("*")):
    if p.is_file() and not p.is_symlink() and "scratch" not in p.parts and p.name != "SHA256SUMS.txt":
        files_to_hash.append(p)

lines = []
for f in files_to_hash:
    rel_p = f.relative_to(campana_dir).as_posix()
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    lines.append(f"{h.hexdigest()}  {rel_p}")

out_path = campana_dir / "SHA256SUMS.txt"
out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Generated SHA256SUMS.txt with {len(lines)} files.")
