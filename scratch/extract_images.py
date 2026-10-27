import zipfile
import os
from PIL import Image

out_dir = 'scratch/extracted_media'
os.makedirs(out_dir, exist_ok=True)

with zipfile.ZipFile('Artículo Polinizador Ing Software II.docx') as z:
    for name in z.namelist():
        if name.startswith('word/media/'):
            filename = os.path.basename(name)
            target_path = os.path.join(out_dir, filename)
            with open(target_path, 'wb') as f:
                f.write(z.read(name))
            im = Image.open(target_path)
            print(f'{filename}: size={im.size}, format={im.format}, mode={im.mode}')
