import io
import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
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

def build_crisp_og_image():
    # 2x Supersampling canvas dimensions
    W2, H2 = 2400, 1260
    W, H = 1200, 630

    print("Building 2x supersampled master canvas (2400x1260)...")

    # 1. Base photographic layer
    # We load satellite-ag and enhance its dynamic range properly
    raw_sat = Image.open(PUBLIC_DIR / "images" / "features" / "satellite-ag.jpg")
    arr_sat = np.array(raw_sat, dtype=float)
    p2 = np.percentile(arr_sat, 2)
    p98 = np.percentile(arr_sat, 98)
    stretched = np.clip((arr_sat - p2) / (p98 - p2) * 255.0, 0, 255.0)
    curved = 255.0 * ((stretched / 255.0) ** 0.82)
    sat_enhanced = Image.fromarray(curved.astype(np.uint8)).convert("RGBA")
    
    # Also load irrigation.jpg for authentic circular pivot field textures
    raw_irr = Image.open(PUBLIC_DIR / "images" / "features" / "irrigation.jpg").convert("RGBA")

    # Scale both to fill right half and canvas
    # Canvas base: deep rich dark forest green (#0b1f14)
    canvas = Image.new("RGBA", (W2, H2), (11, 31, 20, 255))

    # Scale sat_enhanced to cover canvas
    sw, sh = sat_enhanced.size
    scale = max(W2 / sw, H2 / sh)
    sat_scaled = sat_enhanced.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
    left_c = (sat_scaled.width - W2) // 2
    top_c = (sat_scaled.height - H2) // 2
    sat_cropped = sat_scaled.crop((left_c, top_c, left_c + W2, top_c + H2))

    # Scale irrigation image to cover right section (width ~1400, height ~1260)
    irr_scale = max(1400 / raw_irr.width, H2 / raw_irr.height)
    irr_w, irr_h = int(raw_irr.width * irr_scale), int(raw_irr.height * irr_scale)
    irr_scaled = raw_irr.resize((irr_w, irr_h), Image.Resampling.LANCZOS)
    irr_cropped = irr_scaled.crop((0, (irr_h - H2) // 2, 1400, (irr_h - H2) // 2 + H2))

    # Blend satellite and irrigation on the right
    # Irrigation placed on the right (x from 1000 to 2400)
    irr_mask = Image.new("L", (1400, H2), 0)
    d_imask = ImageDraw.Draw(irr_mask)
    for x in range(1400):
        # smooth horizontal fade in
        t = x / 1400.0
        if t < 0.2:
            alpha = int(t / 0.2 * 180)
        else:
            alpha = 180
        d_imask.line([(x, 0), (x, H2)], fill=alpha)
    
    # Paste agricultural imagery onto canvas
    canvas.paste(sat_cropped, (0, 0))
    canvas.paste(irr_cropped, (1000, 0), irr_mask)

    # 2. Left Editorial Contrast Gradient (Restrained & Smooth)
    # The left 45% needs rich dark forest green for ultra-crisp typography contrast
    # The right 55% reveals the vibrant agricultural fields
    gradient = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d_grad = ImageDraw.Draw(gradient)
    
    for x in range(W2):
        t = x / W2
        if t < 0.42:
            # Solid dark forest green (#0a1c12) for razor-sharp text readability
            alpha = 248
        elif t < 0.70:
            # Smooth photographic ramp
            rel = (t - 0.42) / (0.70 - 0.42)
            # Cubic ease-out curve
            alpha = int(248 - 180 * (rel ** 1.3))
        else:
            # Light ambient tint on far right so fields remain crisp and vivid
            alpha = 68
            
        d_grad.line([(x, 0), (x, H2)], fill=(10, 28, 18, alpha))
        
    canvas = Image.alpha_composite(canvas, gradient)
    draw = ImageDraw.Draw(canvas)

    # 3. High-resolution typography at 2x
    # Fonts
    font_brand = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 68)
    font_cat = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
    font_headline = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 100)
    font_desc = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 40)
    font_badge = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
    font_geo = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 22)

    # 4. Render EXACT official SOILSTICE BrandMark at 2x (160x160 px)
    logo_size_2x = 160
    logo_png_bytes = resvg_py.svg_to_bytes(OFFICIAL_LOGO_SVG, width=logo_size_2x, height=logo_size_2x)
    logo_img = Image.open(io.BytesIO(logo_png_bytes)).convert("RGBA")

    # Placement coordinates at 2x
    left_x = 160
    top_y = 140

    # Paste official logo
    canvas.paste(logo_img, (left_x, top_y), logo_img)

    # Wordmark & Category Label
    wordmark_x = left_x + logo_size_2x + 36
    draw.text((wordmark_x, top_y + 20), "SOILSTICE", font=font_brand, fill=(253, 251, 247, 255))
    draw.text((wordmark_x, top_y + 98), "FIELD RESILIENCE INTELLIGENCE", font=font_cat, fill=(163, 193, 159, 255))

    # Top right subtle accreditation pill
    pill_text = "NASA SPACE APPS CHALLENGE 2026"
    pill_w = 540
    pill_h = 64
    pill_x = W2 - 160 - pill_w
    pill_y = top_y + 36
    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)], radius=32, fill=(15, 42, 27, 220), outline=(60, 110, 75, 240), width=2)
    # Gold accent dot
    draw.ellipse([(pill_x + 24, pill_y + 22), (pill_x + 40, pill_y + 38)], fill=(201, 154, 62, 255))
    draw.text((pill_x + 56, pill_y + 17), pill_text, font=font_badge, fill=(245, 250, 245, 255))

    # Subtle divider rule
    divider_y = top_y + 210
    draw.line([(left_x, divider_y), (W2 - 160, divider_y)], fill=(45, 85, 58, 140), width=2)

    # 5. Main Headline:
    # KNOW THE FIELD.
    # BEFORE THE SEASON.
    hl_y = divider_y + 70
    draw.text((left_x, hl_y), "KNOW THE FIELD.", font=font_headline, fill=(255, 255, 255, 255))
    draw.text((left_x, hl_y + 120), "BEFORE THE SEASON.", font=font_headline, fill=(255, 255, 255, 255))

    # 6. Supporting Text:
    # "Satellite-powered agricultural intelligence for more informed, resilient farming decisions."
    desc_y = hl_y + 280
    desc_line1 = "Satellite-powered agricultural intelligence"
    desc_line2 = "for more informed, resilient farming decisions."
    draw.text((left_x, desc_y), desc_line1, font=font_desc, fill=(215, 235, 220, 255))
    draw.text((left_x, desc_y + 58), desc_line2, font=font_desc, fill=(215, 235, 220, 255))

    # 7. Subtle Geospatial HUD Accents on the right (Tasteful, modern editorial)
    hud_x = W2 - 580
    hud_y = H2 - 200
    # Coordinate badge
    coord_text = "AOI: RENO COUNTY, KS · 38.04°N 97.92°W"
    draw.rounded_rectangle([(hud_x, hud_y), (hud_x + 420, hud_y + 50)], radius=10, fill=(11, 31, 20, 180), outline=(50, 95, 65, 200), width=2)
    draw.text((hud_x + 18, hud_y + 14), coord_text, font=font_geo, fill=(201, 154, 62, 255))

    # 8. Bottom Footer Attribution
    foot_y = H2 - 150
    draw.line([(left_x, foot_y - 25), (W2 - 160, foot_y - 25)], fill=(45, 85, 58, 140), width=2)

    footer_left = "SOILSTICE · SATELLITE-POWERED AGRICULTURAL INTELLIGENCE"
    draw.text((left_x, foot_y), footer_left, font=font_badge, fill=(163, 193, 159, 255))

    domain_text = "soilstice.vercel.app"
    draw.text((W2 - 160 - 240, foot_y), domain_text, font=font_badge, fill=(201, 154, 62, 255))

    # 9. DOWNSAMPLE ONCE USING LANCZOS TO EXACT 1200x630
    print("Downsampling 2x master to 1200x630 via Lanczos filter...")
    final_og = canvas.resize((W, H), Image.Resampling.LANCZOS)

    # Convert to RGB with optimal PNG compression to ensure maximum compatibility
    final_rgb = final_og.convert("RGB")

    # Save to both standard paths and versioned path
    paths = [
        PUBLIC_DIR / "og-image.png",
        PUBLIC_DIR / "og-image-v2.png",
        PUBLIC_DIR / "twitter-image.png",
        APP_DIR / "opengraph-image.png",
    ]
    for p in paths:
        final_rgb.save(p, format="PNG", optimize=True)
        print(f"  Saved {p.name} ({p.stat().st_size} bytes)")

    # 10. Generate a 570x300 preview simulation for quality inspection
    preview_570 = final_rgb.resize((570, 300), Image.Resampling.LANCZOS)
    preview_570.save(PUBLIC_DIR / "og-preview-570.png", format="PNG")
    print("  Saved 570x300 social preview simulation")

if __name__ == "__main__":
    build_crisp_og_image()
