import docx

doc = docx.Document('Artículo Polinizador Ing Software II.docx')

print("=== ALL PARAGRAPHS WITH FIGURES / TABLES / HEADINGS ===")
for i, p in enumerate(doc.paragraphs):
    txt = p.text.strip()
    if not txt:
        # Check if drawing
        blips = p._p.xpath('.//a:blip')
        if blips:
            rId = blips[0].attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            target = doc.part.rels[rId].target_ref if rId in doc.part.rels else 'unknown'
            print(f"P{i} [IMAGE]: {rId} -> {target}")
        continue
    if any(k in txt.lower() for k in ['figura', 'tabla', 'cuadro']) or p.style.name.startswith('Heading') or txt.isupper():
        print(f"P{i} [{p.style.name}]: {txt}")

print("\n=== ALL TABLES ===")
for t_idx, tbl in enumerate(doc.tables):
    print(f"\n--- TABLE {t_idx} (rows={len(tbl.rows)}, cols={len(tbl.columns)}) ---")
    for r_idx, row in enumerate(tbl.rows):
        cells = [c.text.strip().replace('\n', ' ') for c in row.cells]
        print(f"R{r_idx}: " + " | ".join(cells))
