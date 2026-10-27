import matplotlib.pyplot as plt
from PIL import Image

for img_name in ['image5.png', 'image1.png', 'image6.png', 'image4.png', 'image2.png', 'image3.png']:
    im = Image.open(f'scratch/extracted_media/{img_name}')
    print(f"{img_name}: size={im.size}, mode={im.mode}")
