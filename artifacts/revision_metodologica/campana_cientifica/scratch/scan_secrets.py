import re
from pathlib import Path

campana_dir = Path("artifacts/revision_metodologica/campana_cientifica")

patterns = [
    re.compile(r'(?i)(password|secret|token|api_key|jwt|groq_api_key)\s*[:=]\s*["\']?([^"\'\s]+)'),
]

found_issues = []
for p in campana_dir.rglob("*"):
    if p.is_file() and not p.is_symlink() and "scratch" not in p.parts:
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            for pat in patterns:
                matches = pat.findall(content)
                for m in matches:
                    found_issues.append((str(p), m))
        except Exception as e:
            pass

print("Scan results for secrets:")
if not found_issues:
    print("No sensitive patterns found in campaign directory.")
else:
    for f, m in found_issues:
        print(f"  {f}: {m}")
