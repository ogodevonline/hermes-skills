#!/usr/bin/env python3
"""Контактный лист из картинок каталога: крупно + как выглядит в списке чатов.

Использование: python3 make_sheet.py <каталог> [заголовок]
Склейка через chromium headless (PIL в окружении нет).
"""
import glob, os, subprocess, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
TITLE = sys.argv[2] if len(sys.argv) > 2 else "Варианты"
CHROME = next((os.path.join(d, "chrome-linux64", "chrome")
               for d in glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/"))
               if os.path.exists(os.path.join(d, "chrome-linux64", "chrome"))), None)
assert CHROME, "chromium not found"

names = sorted(f for f in os.listdir(OUT) if f.lower().endswith((".png", ".jpg", ".webp")))
cards = []
for f in names:
    small = "".join(f'<img src="{f}" width="{s}" height="{s}"/>' for s in (96, 64, 40))
    cards.append(f'<div class="card"><img class="big" src="{f}"/><div class="meta">'
                 f'<div class="name">{f}</div><div class="row">{small}</div></div></div>')

html = f"""<html><head><meta charset="utf-8"><style>
body {{ margin:0; background:#0A0B10; color:#EAEAF2; font:600 20px "DejaVu Sans", sans-serif; }}
.wrap {{ padding:26px; }} h1 {{ font-size:28px; margin:0 0 20px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:22px; }}
.card {{ background:#14161E; border-radius:18px; padding:14px; }}
.big {{ width:300px; height:300px; border-radius:14px; display:block; object-fit:cover; }}
.meta {{ margin-top:10px; }} .name {{ color:#9AA0B6; font-size:19px; margin-bottom:10px; }}
.row img {{ margin-right:12px; vertical-align:middle; border-radius:8px; }}
</style></head><body><div class="wrap"><h1>{TITLE}</h1>
<div class="grid">{''.join(cards)}</div></div></body></html>"""
open(os.path.join(OUT, "sheet.html"), "w").write(html)
subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1", "--window-size=1520,1150",
                f"--screenshot={os.path.join(OUT, 'sheet.png')}",
                f"file://{os.path.join(OUT, 'sheet.html')}"], capture_output=True, timeout=180)
print("sheet:", os.path.join(OUT, "sheet.png"), "| files:", len(names))
