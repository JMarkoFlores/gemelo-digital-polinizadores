with open('doc_dump.txt', encoding='utf-8') as f:
    lines = f.readlines()

for i in [28, 29, 30, 31, 32, 33, 34, 38, 39, 40, 41, 42, 43, 44, 47, 48, 54, 55, 56, 57, 58, 59, 60, 61, 65, 66, 67, 68, 69, 70]:
    # find === P{i} ===
    target = f'=== P{i} ===\n'
    if target in lines:
        idx = lines.index(target)
        print(lines[idx].strip())
        print(lines[idx+1].strip())
        print('-'*40)
