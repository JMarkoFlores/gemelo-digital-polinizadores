import numpy as np
from PIL import Image

im = Image.open('scratch/extracted_media/image1.png').convert('L')
arr = np.array(im)
# If bars are horizontal, rows will have large contiguous dark regions
# Let's inspect panel 1
w, h = im.size
p1 = arr[:, :w//3]
print("Panel 1 shape:", p1.shape)
# Count non-white pixels along columns and rows
col_dark = (p1 < 200).sum(axis=0)
row_dark = (p1 < 200).sum(axis=1)
print("Max dark pixels in a row:", row_dark.max(), "in a col:", col_dark.max())
