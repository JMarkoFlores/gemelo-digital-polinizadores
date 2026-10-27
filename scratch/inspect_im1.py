from PIL import Image
import numpy as np

im = Image.open('scratch/extracted_media/image1.png')
print("Image1 size:", im.size)
w, h = im.size
# Crop 3 subplots (a), (b), (c)
p1 = im.crop((0, 0, w//3, h))
p2 = im.crop((w//3, 0, 2*w//3, h))
p3 = im.crop((2*w//3, 0, w, h))
print("Panel sizes:", p1.size, p2.size, p3.size)
