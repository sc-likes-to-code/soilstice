import io
from pathlib import Path
import resvg_py
from PIL import Image

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="512" height="512">
  <circle cx="16" cy="16" r="15" fill="#1d3a29" />
  <path d="M4 20.5c4-1.2 8-1.2 12 0s8 1.2 12 0" stroke="#c99a3e" stroke-width="1.6" fill="none" stroke-linecap="round" />
  <path d="M5.5 24.5c3.5-1 7-1 10.5 0s7 1 10.5 0" stroke="#a3c19f" stroke-width="1.4" fill="none" stroke-linecap="round" opacity=".8" />
  <path d="M16 19.5V10.5" stroke="#e3ecdd" stroke-width="1.6" stroke-linecap="round" />
  <path d="M16 14c-3.6.2-5.4-1.6-5.6-4.6 3.4-.2 5.3 1.4 5.6 4.6Z" fill="#a3c19f" />
  <path d="M16 12.4c.2-3.3 2.2-5 5.6-4.9-.1 3.1-2.1 4.9-5.6 4.9Z" fill="#e3ecdd" />
</svg>"""

root = Path(__file__).resolve().parent.parent

# 1. Write SVG icons
svg_paths = [
    root / "src" / "app" / "icon.svg",
    root / "public" / "icon.svg",
    root / "public" / "logo.svg",
]
for p in svg_paths:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(SVG_CONTENT, encoding="utf-8")
    print(f"Wrote SVG to {p}")

# 2. Render 512x512 high-res master PNG
png_bytes = resvg_py.svg_to_bytes(SVG_CONTENT)
master_img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

# 3. Save standard icon sizes
sizes = {
    root / "public" / "icon-512.png": 512,
    root / "public" / "icon-192.png": 192,
    root / "public" / "apple-touch-icon.png": 180,
    root / "src" / "app" / "apple-icon.png": 180,
}

for path, size in sizes.items():
    resized = master_img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(path, format="PNG")
    print(f"Wrote {size}x{size} PNG to {path}")

# 4. Generate multi-resolution ICO file (16, 32, 48)
ico_sizes = [(16, 16), (32, 32), (48, 48)]
ico_paths = [
    root / "src" / "app" / "favicon.ico",
    root / "public" / "favicon.ico",
]
for p in ico_paths:
    master_img.save(p, format="ICO", sizes=ico_sizes)
    print(f"Wrote multi-res ICO to {p}")

print("All favicon and logo assets generated successfully!")
