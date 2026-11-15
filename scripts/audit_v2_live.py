import urllib.request
import re

urls = [
    'https://soilstice.vercel.app/og-image-v2.png',
    'https://soilstice-web.vercel.app/og-image-v2.png',
]

print("=== VERSIONED IMAGE CHECKS ===")
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[{resp.status}] {u} -> Length: {resp.headers.get('Content-Length')}, ETag: {resp.headers.get('ETag')}")
    except Exception as e:
        print(f"ERR {u}: {e}")

print("\n=== HTML TAG CHECKS ===")
for u in ['https://soilstice.vercel.app/', 'https://soilstice-web.vercel.app/']:
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8')
        og_img = re.findall(r'<meta[^>]+property="og:image"[^>]*>', html)
        tw_img = re.findall(r'<meta[^>]+name="twitter:image"[^>]*>', html)
        print(f"{u}:")
        print(f"  OG Image: {og_img}")
        print(f"  Twitter Image: {tw_img}")
