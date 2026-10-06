#!/usr/bin/env python3
"""Генерация картинок через KiloCode gateway. Батч по списку промптов.

Использование:
    python3 kilo_image.py                 # прогнать CANDIDATES
    python3 kilo_image.py 01-example      # только выбранные по имени
"""
import base64, json, os, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ENV = os.path.expanduser("~/.hermes/.env")
KEY = next(l.split("=", 1)[1].strip().strip('"').strip("'")
           for l in open(ENV) if l.startswith("KILOCODE_API_KEY="))
URL = "https://api.kilo.ai/api/gateway/v1/chat/completions"
OUT = os.environ.get("KILO_IMAGE_OUT", os.path.expanduser("~/.hermes/cache/scratch/kilo-images"))
os.makedirs(OUT, exist_ok=True)

STYLE = ("Flat vector app icon, square 1:1 composition, premium SaaS branding, crisp clean geometry, "
         "soft ambient shadow, subtle glossy highlight, high contrast, centered with generous margins, "
         "no photorealism, no mockup, no watermark, no signature.")

CANDIDATES = [
    ("01-example", "google/gemini-3.1-flash-image",
     f"{STYLE} Subject: <object, background, accent.>"),
]


def gen(item):
    name, model, prompt = item
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json"})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=300).read().decode())
    except urllib.error.HTTPError as e:
        return name, "HTTP %s: %s" % (e.code, e.read().decode()[:200])
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    url = None
    for m in (msg.get("images") or []):          # картинка тут, НЕ в content
        u = (m.get("image_url") or {}).get("url") if isinstance(m, dict) else None
        if u and u.startswith("data:"):
            url = u
            break
    if not url:
        return name, "no image"
    ext = url.split(";")[0].split("/")[1]
    path = f"{OUT}/{name}.{ext}"
    open(path, "wb").write(base64.b64decode(url.split(",", 1)[1]))
    cost = (data.get("usage") or {}).get("cost_details", {}).get("upstream_inference_cost")
    return name, f"ok {os.path.getsize(path)} cost={cost}"


if __name__ == "__main__":
    only = sys.argv[1:] or None
    todo = [c for c in CANDIDATES if not only or c[0] in only]
    with ThreadPoolExecutor(max_workers=6) as ex:
        for name, res in ex.map(gen, todo):
            print(f"{name}: {res}", flush=True)
