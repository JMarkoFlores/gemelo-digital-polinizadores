import os
from PIL import Image

for fname in ['image1.png', 'image4.png', 'image5.png', 'image6.png', 'image2.png', 'image3.png']:
    fpath = os.path.join('scratch/extracted_media', fname)
    if os.path.exists(fpath):
        im = Image.open(fpath)
        print(f"{fname}: mode={im.mode}, size={im.size}, dpi={im.info.get('dpi')}")
