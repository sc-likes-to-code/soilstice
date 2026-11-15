import urllib.request
import re
import json

urls = [
    'https://soilstice.vercel.app/',
    'https://soilstice-web.vercel.app/',
    'https://soilstice.vercel.app/evidence',
    'https://soilstice-web.vercel.app/evidence',
    'https://soilstice.vercel.app/robots.txt',
    'https://soilstice-web.vercel.app/robots.txt',
    'https://soilstice.vercel.app/sitemap.xml',
    'https://soilstice-web.vercel.app/sitemap.xml',
    'https://soilstice.vercel.app/og-image.png',
    'https://soilstice-web.vercel.app/og-image.png',
    'https://soilstice.vercel.app/manifest.json',
    'https://soilstice-web.vercel.app/manifest.json',
    'https://soilstice.vercel.app/manifest.webmanifest',
    'https://soilstice-web.vercel.app/manifest.webmanifest',
    'https://soilstice.vercel.app/favicon.ico',
    'https://soilstice-web.vercel.app/favicon.ico',
    'https://soilstice.vercel.app/icon.svg',
    'https://soilstice-web.vercel.app/icon.svg',
]

print("=== DEPLOYMENT AUDIT ===")
for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get('content-type', '')
            length = resp.headers.get('content-length', 'unknown')
            print(f"[{resp.status}] {u} ({content_type}, len={length})")
            if 'html' in content_type and u.endswith('/'):
                html = resp.read().decode('utf-8', errors='ignore')
                title = re.findall(r'<title[^>]*>(.*?)</title>', html, re.I)
                canonical = re.findall(r'<link[^>]+rel=[\'"]canonical[\'"][^>]*>', html, re.I)
                metas = re.findall(r'<meta[^>]+>', html, re.I)
                og_tags = [m for m in metas if 'property="og:' in m or 'property=\'og:' in m or 'name="twitter:' in m or 'name=\'twitter:' in m or 'name="description"' in m]
                ld_json = re.findall(r'<script[^>]+type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', html, re.I | re.DOTALL)
                print(f"  Title: {title}")
                print(f"  Canonical: {canonical}")
                print(f"  OG/Twitter/Meta: {len(og_tags)} found")
                for og in og_tags:
                    print(f"    {og}")
                print(f"  JSON-LD scripts: {len(ld_json)}")
                for j in ld_json:
                    print(f"    JSON-LD: {j[:150]}...")
    except urllib.error.HTTPError as e:
        print(f"[{e.code}] {u} - HTTP Error: {e.reason}")
    except Exception as e:
        print(f"[ERR] {u} - Error: {e}")
