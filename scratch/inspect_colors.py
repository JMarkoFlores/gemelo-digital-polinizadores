import numpy as np
from PIL import Image

im = Image.open('scratch/extracted_media/image1.png').convert('RGB')
arr = np.array(im)
# Find colored pixels (not white/gray)
diff = np.abs(arr[:, :, 0].astype(int) - arr[:, :, 1].astype(int)) + np.abs(arr[:, :, 1].astype(int) - arr[:, :, 2].astype(int))
colored = diff > 30
y_idx, x_idx = np.where(colored)
print("Colored pixel count:", len(y_idx))
if len(y_idx) > 0:
    print(f"X range: {x_idx.min()} to {x_idx.max()} (width {im.size[0]})")
    print(f"Y range: {y_idx.min()} to {y_idx.max()} (height {im.size[1]})")
    # Sample some colors
    unique_colors = np.unique(arr[colored], axis=0)
    print("Number of distinct colors:", len(unique_colors))
    # print top colors
    import collections
    c_tuples = [tuple(c) for c in arr[colored]]
    top_c = collections.Counter(c_tuples).most_common(5)
    print("Top colors:", top_c)
