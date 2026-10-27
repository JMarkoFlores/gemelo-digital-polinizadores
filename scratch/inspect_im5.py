from PIL import Image
import numpy as np

im = Image.open('scratch/extracted_media/image5.png')
print("Image 5 size:", im.size)
# Let's inspect where text/boxes are located by vertical and horizontal projections
arr = np.array(im.convert('L'))
print("Min, max, mean:", arr.min(), arr.max(), arr.mean())

# Check left and right halves (a and b)
w, h = im.size
left_half = im.crop((0, 0, w//2, h))
right_half = im.crop((w//2, 0, w, h))
print("Left half size:", left_half.size, "Right half size:", right_half.size)
