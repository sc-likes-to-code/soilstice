import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import resvg_py

OUT_DIR = "public"
APP_DIR = "src/app"

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
  <circle cx="50" cy="50" r="48" fill="#143320" stroke="#2d5e3c" stroke-width="2.5"/>
  <path d="M50 20 A30 30 0 0 1 80 50" stroke="#86efac" stroke-width="3" stroke-linecap="round" stroke-dasharray="2 6"/>
  <path d="M50 82 V42" stroke="#4ade80" stroke-width="6.5" stroke-linecap="round"/>
  <path d="M50 58 C40 52 32 54 28 62 C28 48 42 42 50 48" fill="#86efac"/>
  <path d="M50 46 C58 38 68 40 72 48 C72 34 58 30 50 36" fill="#4ade80"/>
  <circle cx="50" cy="24" r="5" fill="#facc15"/>
</svg>"""

def create_og_image():
    W, H = 1200, 630
    # Canvas
    img = Image.new("RGBA", (W, H), (10, 24, 16, 255))

    # Background photo texture
    bg_path = "public/images/features/satellite-ag.jpg"
    if os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGBA")
        # Resize & crop to 1200x630
        bg = bg.resize((W, int(W * bg.height / bg.width)), Image.Resampling.LANCZOS)
        if bg.height > H:
            top = (bg.height - H) // 2
            bg = bg.crop((0, top, W, top + H))
        elif bg.height < H:
            bg = bg.resize((int(H * bg.width / bg.height), H), Image.Resampling.LANCZOS)
            left = (bg.width - W) // 2
            bg = bg.crop((left, 0, left + W, H))
        
        # Desaturate slightly and darken
        enhancer = ImageEnhance.Color(bg)
        bg = enhancer.enhance(0.4)
        bg = bg.filter(ImageFilter.GaussianBlur(1.5))
        
        # Overlay with dark green gradient
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d_over = ImageDraw.Draw(overlay)
        for y in range(H):
            # Gradient from deep forest green at top to dark midnight green at bottom
            alpha = int(195 + 45 * (y / H)) # 195 -> 240
            r = int(10 + (y / H) * 4)
            g = int(27 - (y / H) * 8)
            b = int(18 - (y / H) * 6)
            d_over.line([(0, y), (W, y)], fill=(r, g, b, alpha))
        
        bg.paste(overlay, (0, 0), overlay)
        img.paste(bg, (0, 0))

    draw = ImageDraw.Draw(img)

    # Decorative tech grid lines
    grid_color = (74, 222, 128, 18)
    for x in range(60, W, 120):
        draw.line([(x, 40), (x, H - 40)], fill=grid_color, width=1)
    for y in range(60, H, 100):
        draw.line([(40, y), (W - 40, y)], fill=grid_color, width=1)

    # Render vector emblem via resvg
    logo_size = 80
    logo_png_bytes = resvg_py.svg_to_bytes(SVG_CONTENT, width=logo_size, height=logo_size)
    import io
    logo_im = Image.open(io.BytesIO(logo_png_bytes)).convert("RGBA")
    img.paste(logo_im, (70, 65), logo_im)

    # Fonts
    font_serif_large = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 52)
    font_serif_med = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 28)
    font_sans_bold = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 34)
    font_sans_tag = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 16)
    font_sans_body = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
    font_mono_small = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 14)
    font_mono_badge = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)

    # Brand Title Next to Logo
    draw.text((165, 76), "SOILSTICE", font=font_sans_bold, fill=(253, 251, 247, 255))
    draw.text((166, 114), "FIELD RESILIENCE INTELLIGENCE", font=font_mono_badge, fill=(134, 239, 172, 220))

    # Top Right Tag: NASA Space Apps Challenge 2026
    badge_text = "NASA SPACE APPS CHALLENGE 2026"
    badge_w = 320
    draw.rounded_rectangle([(W - 70 - badge_w, 75), (W - 70, 115)], radius=8, fill=(18, 48, 30, 230), outline=(52, 94, 65, 255), width=1)
    # Green glowing dot
    draw.ellipse([(W - 70 - badge_w + 14, 92), (W - 70 - badge_w + 20, 98)], fill=(74, 222, 128, 255))
    draw.text((W - 70 - badge_w + 28, 86), badge_text, font=font_mono_badge, fill=(220, 245, 228, 255))

    # Horizontal divider under header
    draw.line([(70, 160), (W - 70, 160)], fill=(45, 80, 56, 180), width=1)

    # Eyebrow Tagline
    draw.text((70, 188), "SATELLITE-POWERED AGRICULTURAL INTELLIGENCE", font=font_sans_tag, fill=(250, 204, 21, 240))

    # Main Hero Title
    draw.text((70, 220), "Know the field before the season.", font=font_serif_large, fill=(253, 251, 247, 255))

    # Descriptive Subtitle
    body_1 = "Explainable field-level intelligence uniting NASA Earth observations,"
    body_2 = "USDA SSURGO soil surveys, and 20-year Cropland Data Layer sequences."
    draw.text((70, 298), body_1, font=font_sans_body, fill=(200, 225, 210, 240))
    draw.text((70, 328), body_2, font=font_sans_body, fill=(200, 225, 210, 240))

    # Scientific Evidence Cards at Bottom
    chips = [
        ("NASA POWER", "Daily Agrometeorology", "Live API"),
        ("USDA SSURGO", "0-150 cm Soil Profile", "Verified"),
        ("USDA NASS CDL", "20-Year Crop Sequences", "Verified"),
        ("LIEBIG ENGINE", "Law of Minimum Scoring", "Active"),
    ]

    chip_y = 410
    card_w = 250
    card_h = 130
    gap = 20
    start_x = 70

    for i, (src, desc, st) in enumerate(chips):
        cx = start_x + i * (card_w + gap)
        # Card background
        draw.rounded_rectangle([(cx, chip_y), (cx + card_w, chip_y + card_h)], radius=10, fill=(15, 38, 25, 210), outline=(42, 85, 55, 230), width=1)
        # Status pill
        draw.rounded_rectangle([(cx + card_w - 75, chip_y + 12), (cx + card_w - 14, chip_y + 30)], radius=9, fill=(22, 60, 36, 255))
        draw.text((cx + card_w - 68, chip_y + 15), st, font=font_mono_small, fill=(134, 239, 172, 255))
        # Title & detail
        draw.text((cx + 16, chip_y + 15), src, font=font_sans_tag, fill=(253, 251, 247, 255))
        draw.text((cx + 16, chip_y + 44), desc, font=font_sans_body, fill=(185, 215, 195, 230))
        # Sub-detail
        draw.line([(cx + 16, chip_y + 82), (cx + card_w - 16, chip_y + 82)], fill=(32, 68, 45, 180), width=1)
        draw.text((cx + 16, chip_y + 94), "Multi-depth analysis", font=font_mono_small, fill=(130, 175, 145, 200))

    # Bottom Footer Status Bar
    draw.line([(70, 570), (W - 70, 570)], fill=(45, 80, 56, 180), width=1)
    coord_text = "AOI: RENO COUNTY, KS · LAT 38.04° N  LON -97.92° W · EPSG:4326 · SOILSTICE.VERCEL.APP"
    draw.text((70, 584), coord_text, font=font_mono_small, fill=(134, 239, 172, 190))
    draw.text((W - 270, 584), "Field Resilience Intelligence", font=font_mono_small, fill=(200, 220, 210, 180))

    # Outer border
    draw.rectangle([(0, 0), (W - 1, H - 1)], outline=(52, 102, 68, 255), width=2)

    # Save to public and app dirs
    og_png_path = os.path.join(OUT_DIR, "og-image.png")
    app_og_path = os.path.join(APP_DIR, "opengraph-image.png")
    twitter_path = os.path.join(OUT_DIR, "twitter-image.png")

    img.save(og_png_path, "PNG", optimize=True)
    img.save(app_og_path, "PNG", optimize=True)
    img.save(twitter_path, "PNG", optimize=True)
    print(f"Generated OG Image: {og_png_path} ({W}x{H})")

def generate_png_icons():
    # Sizes needed: 16, 32, 180, 192, 512
    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }
    for filename, sz in sizes.items():
        png_bytes = resvg_py.svg_to_bytes(SVG_CONTENT, width=sz, height=sz)
        pub_path = os.path.join(OUT_DIR, filename)
        with open(pub_path, "wb") as f:
            f.write(png_bytes)
        print(f"Generated {pub_path} ({sz}x{sz})")

if __name__ == "__main__":
    create_og_image()
    generate_png_icons()
