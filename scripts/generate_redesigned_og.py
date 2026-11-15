import io
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import resvg_py

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT / "public"
APP_DIR = ROOT / "src" / "app"

# The EXACT official SOILSTICE BrandMark from src/components/layout/brand.tsx
OFFICIAL_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="512" height="512">
  <circle cx="16" cy="16" r="15" fill="#1d3a29" />
  <path d="M4 20.5c4-1.2 8-1.2 12 0s8 1.2 12 0" stroke="#c99a3e" stroke-width="1.6" fill="none" stroke-linecap="round" />
  <path d="M5.5 24.5c3.5-1 7-1 10.5 0s7 1 10.5 0" stroke="#a3c19f" stroke-width="1.4" fill="none" stroke-linecap="round" opacity=".8" />
  <path d="M16 19.5V10.5" stroke="#e3ecdd" stroke-width="1.6" stroke-linecap="round" />
  <path d="M16 14c-3.6.2-5.4-1.6-5.6-4.6 3.4-.2 5.3 1.4 5.6 4.6Z" fill="#a3c19f" />
  <path d="M16 12.4c.2-3.3 2.2-5 5.6-4.9-.1 3.1-2.1 4.9-5.6 4.9Z" fill="#e3ecdd" />
</svg>"""

def update_all_brand_icons():
    """Ensure all favicon and app icons use the exact official BrandMark."""
    print("Updating all brand icons with official BrandMark...")
    # 1. SVGs
    for p in [PUBLIC_DIR / "icon.svg", PUBLIC_DIR / "logo.svg", APP_DIR / "icon.svg"]:
        p.write_text(OFFICIAL_LOGO_SVG, encoding="utf-8")
        print(f"  Wrote {p.name}")

    # 2. Master high-res raster
    png_bytes = resvg_py.svg_to_bytes(OFFICIAL_LOGO_SVG, width=512, height=512)
    master = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

    # 3. Sizes
    sizes = {
        PUBLIC_DIR / "icon-512.png": 512,
        PUBLIC_DIR / "icon-192.png": 192,
        PUBLIC_DIR / "apple-touch-icon.png": 180,
        APP_DIR / "apple-icon.png": 180,
        PUBLIC_DIR / "favicon-32x32.png": 32,
        PUBLIC_DIR / "favicon-16x16.png": 16,
    }
    for path, sz in sizes.items():
        im = master.resize((sz, sz), Image.Resampling.LANCZOS)
        im.save(path, format="PNG")
        print(f"  Saved {path.name} ({sz}x{sz})")

    # 4. Multi-resolution ICO
    ico_sizes = [(16, 16), (32, 32), (48, 48)]
    for p in [PUBLIC_DIR / "favicon.ico", APP_DIR / "favicon.ico"]:
        master.save(p, format="ICO", sizes=ico_sizes)
        print(f"  Saved {p.name}")

def create_redesigned_og_image():
    W, H = 1200, 630
    print("Rendering redesigned 1200x630 OG image...")

    # Base background: Deep rich forest tone
    base = Image.new("RGBA", (W, H), (14, 38, 25, 255))

    # Real aerial/satellite imagery of farmland
    sat_path = PUBLIC_DIR / "images" / "features" / "satellite-ag.jpg"
    if sat_path.exists():
        sat = Image.open(sat_path).convert("RGBA")
        # Resize to cover 1200x630
        sat_w, sat_h = sat.size
        scale = max(W / sat_w, H / sat_h)
        new_w, new_h = int(sat_w * scale), int(sat_h * scale)
        sat = sat.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Crop to 1200x630, focusing on the rich center-right field patterns
        left = max(0, new_w - W)
        top = (new_h - H) // 2
        sat = sat.crop((left, top, left + W, top + H))

        # Color grade the satellite image: enhance contrast, rich earthy green & amber tones
        enhancer = ImageEnhance.Color(sat)
        sat = enhancer.enhance(0.75)
        bright = ImageEnhance.Brightness(sat)
        sat = bright.enhance(0.65)

        base.paste(sat, (0, 0))

    # Apply a smooth, professional photographic vignette / dark gradient overlay
    # From deep solid forest on left (#0c2015) to semi-transparent on right to reveal the satellite fields
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d_vig = ImageDraw.Draw(vignette)
    for x in range(W):
        # Progression from 0 to 1
        t = x / W
        if t < 0.45:
            alpha = int(245 - 20 * (t / 0.45)) # 245 -> 225 (solid readable left zone)
        elif t < 0.75:
            # Smooth transition
            rel = (t - 0.45) / 0.30
            alpha = int(225 - 110 * rel) # 225 -> 115
        else:
            rel = (t - 0.75) / 0.25
            alpha = int(115 - 55 * rel) # 115 -> 60 (clear satellite view on far right)
        
        # Deep forest tint
        d_vig.line([(x, 0), (x, H)], fill=(12, 32, 21, alpha))

    base = Image.alpha_composite(base, vignette)
    draw = ImageDraw.Draw(base)

    # Fonts - Refined contemporary sans-serif
    font_brand = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 34)
    font_tag = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 15)
    font_headline = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 54)
    font_subheadline = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 26)
    font_desc = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 19)
    font_meta = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
    font_meta_bold = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 14)

    # 1. Render EXACT Official BrandMark at 88x88 px
    logo_size = 88
    logo_png_bytes = resvg_py.svg_to_bytes(OFFICIAL_LOGO_SVG, width=logo_size, height=logo_size)
    logo_img = Image.open(io.BytesIO(logo_png_bytes)).convert("RGBA")

    # Left margin alignment
    margin_x = 90
    top_y = 75

    base.paste(logo_img, (margin_x, top_y), logo_img)

    # Brand Title & Wordmark
    brand_text_x = margin_x + logo_size + 20
    draw.text((brand_text_x, top_y + 14), "SOILSTICE", font=font_brand, fill=(251, 248, 242, 255))
    draw.text((brand_text_x, top_y + 54), "FIELD RESILIENCE INTELLIGENCE", font=font_tag, fill=(163, 193, 159, 240))

    # NASA Space Apps Pill on top right
    nasa_badge_text = "NASA SPACE APPS CHALLENGE 2026"
    badge_w = 300
    badge_x = W - 90 - badge_w
    badge_y = top_y + 24
    draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + 36)], radius=18, fill=(18, 48, 30, 210), outline=(60, 110, 75, 230), width=1)
    # Subtle accent dot
    draw.ellipse([(badge_x + 14, badge_y + 13), (badge_x + 22, badge_y + 21)], fill=(201, 154, 62, 255))
    draw.text((badge_x + 30, badge_y + 10), nasa_badge_text, font=font_meta_bold, fill=(240, 248, 240, 240))

    # Subtle horizontal separator line
    draw.line([(margin_x, top_y + 115), (W - 90, top_y + 115)], fill=(45, 80, 56, 120), width=1)

    # 2. Eyebrow: Small supporting text
    eyebrow_y = top_y + 145
    draw.text((margin_x, eyebrow_y), "SATELLITE-POWERED AGRICULTURAL INTELLIGENCE", font=font_tag, fill=(201, 154, 62, 250))

    # 3. Main Headline:
    # "KNOW THE FIELD"
    # "BEFORE THE SEASON."
    hl_y = eyebrow_y + 35
    draw.text((margin_x, hl_y), "KNOW THE FIELD", font=font_headline, fill=(251, 248, 242, 255))
    draw.text((margin_x, hl_y + 64), "BEFORE THE SEASON.", font=font_headline, fill=(251, 248, 242, 255))

    # 4. Supporting Description:
    sub_y = hl_y + 145
    draw.text((margin_x, sub_y), "Field Resilience Intelligence", font=font_subheadline, fill=(227, 236, 221, 250))

    desc_line = "Explainable field-level intelligence uniting NASA Earth observations, USDA soil surveys and 20-year crop records."
    draw.text((margin_x, sub_y + 42), desc_line, font=font_desc, fill=(185, 212, 185, 230))

    # 5. Bottom Satellite/Agronomic Provenance Metadata Bar
    foot_y = 540
    draw.line([(margin_x, foot_y - 18), (W - 90, foot_y - 18)], fill=(45, 80, 56, 120), width=1)

    # Provenance tags
    prov_text = "NASA POWER Agrometeorology  ·  USDA NRCS SSURGO  ·  USDA NASS Cropland Data Layer  ·  NASA SRTM"
    draw.text((margin_x, foot_y), prov_text, font=font_meta, fill=(163, 193, 159, 220))

    domain_tag = "soilstice.vercel.app"
    draw.text((W - 90 - 130, foot_y), domain_tag, font=font_meta_bold, fill=(201, 154, 62, 240))

    # Output paths
    out_paths = [
        PUBLIC_DIR / "og-image.png",
        PUBLIC_DIR / "twitter-image.png",
        APP_DIR / "opengraph-image.png",
    ]
    for p in out_paths:
        base.save(p, "PNG", optimize=True)
        print(f"Saved redesigned OG image to {p}")

if __name__ == "__main__":
    update_all_brand_icons()
    create_redesigned_og_image()
