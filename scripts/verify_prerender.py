import re

with open('.next/server/app/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("=== PRERENDERED HTML METADATA AUDIT ===")
canonical = re.findall(r'<link[^>]+rel="canonical"[^>]*>', html)
print(f"Canonical ({len(canonical)}): {canonical}")

og_tags = re.findall(r'<meta[^>]+property="og:[^"]+"[^>]*>', html)
print(f"\nOG Tags ({len(og_tags)}):")
for og in og_tags:
    print(" ", og)

twitter_tags = re.findall(r'<meta[^>]+name="twitter:[^"]+"[^>]*>', html)
print(f"\nTwitter Tags ({len(twitter_tags)}):")
for tw in twitter_tags:
    print(" ", tw)

og_images = re.findall(r'<meta[^>]+property="og:image"[^>]*>', html)
print(f"\nTotal og:image declarations: {len(og_images)}")
for im in og_images:
    print("  Primary OG image:", im)
