import cv2
import numpy as np
from PIL import Image

# Let's inspect image5.png (Figure 1)
im5 = Image.open('scratch/extracted_media/image5.png')
print("Image 5 size:", im5.size)

# Let's inspect image1.png (Figure 2)
im1 = Image.open('scratch/extracted_media/image1.png')
print("Image 1 size:", im1.size)

# Let's inspect image6.png (Figure 3)
im6 = Image.open('scratch/extracted_media/image6.png')
print("Image 6 size:", im6.size)
