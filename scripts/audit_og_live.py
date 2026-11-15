import urllib.request

urls = [
    'https://soilstice.vercel.app/og-image.png',
    'https://soilstice-web.vercel.app/og-image.png',
    'https://soilstice.vercel.app/opengraph-image.png',
    'https://soilstice-web.vercel.app/opengraph-image.png',
    'https://soilstice.vercel.app/icon.svg',
    'https://soilstice-web.vercel.app/icon.svg',
    'https://soilstice.vercel.app/favicon.ico',
    'https://soilstice-web.vercel.app/favicon.ico',
]

for u in urls:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type")
            cl = resp.headers.get("Content-Length")
            etag = resp.headers.get("ETag")
            print(f"[{resp.status}] {u}\n    Type: {ct}, Size: {cl} bytes, ETag: {etag}")
    except Exception as e:
        print(f"ERR {u}: {e}")
