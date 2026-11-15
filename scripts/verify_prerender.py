import re

with open('.next/server/app/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("=== PRERENDERED HOMEPAGE INSPECTION ===")
print("Title:", re.findall(r'<title[^>]*>(.*?)</title>', html))
print("Canonical:", re.findall(r'<link[^>]+rel="canonical"[^>]*>', html))
print("Description:", re.findall(r'<meta[^>]+name="description"[^>]*>', html))
print("Robots:", re.findall(r'<meta[^>]+name="robots"[^>]*>', html))
print("\nOG Tags:")
for m in re.findall(r'<meta[^>]+property="og:[^"]+"[^>]*>', html):
    print(" ", m)

print("\nTwitter Tags:")
for m in re.findall(r'<meta[^>]+name="twitter:[^"]+"[^>]*>', html):
    print(" ", m)

print("\nIcons & Manifest:")
for m in re.findall(r'<link[^>]+rel="(?:icon|apple-touch-icon|manifest|mask-icon)"[^>]*>', html):
    print(" ", m)

print("\nJSON-LD scripts:")
for s in re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
    print(" ", s[:100], "...")

print("\n=== EVIDENCE PAGE INSPECTION ===")
with open('.next/server/app/evidence.html', 'r', encoding='utf-8') as f:
    ev_html = f.read()
print("Evidence Title:", re.findall(r'<title[^>]*>(.*?)</title>', ev_html))
print("Evidence Canonical:", re.findall(r'<link[^>]+rel="canonical"[^>]*>', ev_html))
print("Evidence OG URL:", re.findall(r'<meta[^>]+property="og:url"[^>]*>', ev_html))

