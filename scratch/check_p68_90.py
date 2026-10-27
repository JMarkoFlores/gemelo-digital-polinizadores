with open('doc_dump.txt', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(68, 90):
    target = f'=== P{i} ===\n'
    if target in lines:
        idx = lines.index(target)
        print(f"P{i}: {lines[idx+1].strip()}")
