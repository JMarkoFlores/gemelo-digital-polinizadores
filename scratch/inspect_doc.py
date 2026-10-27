import docx

doc = docx.Document('Artículo Polinizador Ing Software II.docx')
for i, p in enumerate(doc.paragraphs):
    blips = p._p.xpath('.//a:blip')
    if blips:
        for b in blips:
            rId = b.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            target = doc.part.rels[rId].target_ref if rId in doc.part.rels else 'unknown'
            print(f'P{i}: embed={rId} -> {target} | text: {repr(p.text[:60])}')
