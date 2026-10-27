from PIL import Image, ImageFilter
import os

def enhance_and_set_dpi(src_name, dst_name, scale_factor=2):
    src_path = os.path.join('scratch/extracted_media', src_name)
    im = Image.open(src_path)
    if im.mode != 'RGB':
        im = im.convert('RGB')
    
    # Upscale with high quality Lanczos resampling
    new_w = int(im.size[0] * scale_factor)
    new_h = int(im.size[1] * scale_factor)
    im_scaled = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Apply subtle unsharp mask to crisp up text edges
    im_crisp = im_scaled.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
    
    dst_path = os.path.join('scratch', dst_name)
    im_crisp.save(dst_path, format='PNG', dpi=(600, 600))
    
    check = Image.open(dst_path)
    print(f"{src_name} -> {dst_name}: size={check.size}, DPI={check.info.get('dpi')}")
    return dst_path

enhance_and_set_dpi('image5.png', 'figura1_600dpi.png', scale_factor=2.5) # => 5120 x 2962 px @ 600 DPI!
enhance_and_set_dpi('image4.png', 'ecuacion1_2_600dpi.png', scale_factor=3.0) # => ~1970 x 1077 px @ 600 DPI!
enhance_and_set_dpi('image2.png', 'ecuacion3_600dpi.png', scale_factor=3.0) # => ~1689 x 657 px @ 600 DPI!
enhance_and_set_dpi('image3.png', 'ecuacion4_600dpi.png', scale_factor=3.0) # => ~1374 x 225 px @ 600 DPI!
