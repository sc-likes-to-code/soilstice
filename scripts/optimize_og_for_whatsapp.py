import os
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT / "public"

def optimize_for_whatsapp():
    src_png = PUBLIC_DIR / "og-image-v2.png"
    if not src_png.exists():
        src_png = PUBLIC_DIR / "og-image.png"

    print(f"Reading source artwork from: {src_png}")
    im = Image.open(src_png).convert("RGB")
    
    assert im.size == (1200, 630), f"Expected (1200, 630) but got {im.size}"

    # Target: Quality 92 with 4:4:4 chroma subsampling (subsampling=0) to prevent text edge degradation
    out_targets = [
        PUBLIC_DIR / "og-image-whatsapp.jpg",
        PUBLIC_DIR / "og-image-whatsapp-v1.jpg",
    ]

    for target in out_targets:
        im.save(
            target,
            format="JPEG",
            quality=92,
            progressive=True,
            optimize=True,
            subsampling=0,
        )
        sz = target.stat().st_size
        print(f"Saved {target.name}: {sz} bytes ({sz / 1024:.1f} KB)")
        assert sz < 300 * 1024, f"File size {sz} exceeds 300 KB limit!"

    # Also generate a 300x158 WhatsApp Android mobile card simulation preview
    mobile_sim = im.resize((300, 158), Image.Resampling.LANCZOS)
    mobile_sim.save(PUBLIC_DIR / "og-whatsapp-preview-300.jpg", format="JPEG", quality=90, optimize=True)
    print("Saved og-whatsapp-preview-300.jpg mobile simulation preview.")

if __name__ == "__main__":
    optimize_for_whatsapp()
