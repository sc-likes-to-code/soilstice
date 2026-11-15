import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

def prepare_background(width=2400, height=1260):
    # Load satellite-ag
    raw_sat = Image.open('public/images/features/satellite-ag.jpg')
    arr = np.array(raw_sat, dtype=float)
    
    # satellite-ag raw data is concentrated between 8 and 42.
    # We apply robust percentile normalization and curve enhancement:
    p2 = np.percentile(arr, 2)
    p98 = np.percentile(arr, 98)
    stretched = np.clip((arr - p2) / (p98 - p2) * 255.0, 0, 255.0)
    
    # Slight gamma to lift shadow details without washing out
    gamma = 0.85
    curved = 255.0 * ((stretched / 255.0) ** gamma)
    sat_img = Image.fromarray(curved.astype(np.uint8)).convert('RGBA')
    
    # Color balance to rich agricultural landscape: earthy greens, ochre soils
    enhancer = ImageEnhance.Color(sat_img)
    sat_img = enhancer.enhance(1.25)
    
    contrast = ImageEnhance.Contrast(sat_img)
    sat_img = contrast.enhance(1.15)
    
    # Scale to cover 2400x1260
    sw, sh = sat_img.size
    scale = max(width / sw, height / sh)
    sat_scaled = sat_img.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
    
    # Center crop
    cw, ch = sat_scaled.size
    left = (cw - width) // 2
    top = (ch - height) // 2
    sat_cropped = sat_scaled.crop((left, top, left + width, top + height))
    
    sat_cropped.save('public/images/features/test_sat_bg.png')
    print("Prepared background: size=", sat_cropped.size, "mean=", np.array(sat_cropped).mean())

if __name__ == '__main__':
    prepare_background()
