with open('doc_dump.txt', encoding='utf-8') as f:
    text = f.read()

parts = text.split('=== TABLE ')
for p in parts[1:]:
    lines = p.split('\n')
    print('=== TABLE ' + lines[0])
    for l in lines[1:15]:
        print(l)
    print('...')
