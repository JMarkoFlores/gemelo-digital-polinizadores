import numpy as np
from PIL import Image
import collections

im = Image.open('scratch/extracted_media/image6.png').convert('RGB')
arr = np.array(im)
diff = np.abs(arr[:, :, 0].astype(int) - arr[:, :, 1].astype(int)) + np.abs(arr[:, :, 1].astype(int) - arr[:, :, 2].astype(int))
colored = diff > 30
c_tuples = [tuple(c) for c in arr[colored]]
top_c = collections.Counter(c_tuples).most_common(8)
print("Figure 3 Top colors:", top_c)
