import docx

doc = docx.Document('Artículo Polinizador Ing Software II.docx')
for i, p in enumerate(doc.paragraphs):
    t = p.text
    if any(k in t for k in ['118,251', '102,871', '106,669', '85,031', '55,428', '41,091', '3,481', 'surrogate_20261008', '20261008']):
        print(f"P{i}: {t[:120]}...")
