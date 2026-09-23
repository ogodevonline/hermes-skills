#!/usr/bin/env python3
"""DOM-аудит мобильного рендера админки lead-platform (390px).

Вход через httpOnly-cookie сессию (POST /api/auth/telegram), обход страниц
кликами по нижней навигации BottomNav (с 08.09 бургера/drawer нет; прямые
URL /web/schedule -> 404 SPA-fallback). Настройки/Профиль — тоже нижние табы.
Вывод: горизонтальный скролл страницы + элементы за пределами вьюпорта.

Запуск:
  uv pip install --python ~/projects/lead-platform/.venv/bin/python playwright
  ~/projects/lead-platform/.venv/bin/python mobile_audit.py
  BASE_URL=http://localhost:8000 (или туннель) — переменная окружения.
"""
import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

ENV_PATH = Path.home() / "projects" / "lead-platform" / ".env"
BASE = os.environ.get("BASE_URL", "http://localhost:8000")
CHROME_CANDIDATES = sorted(Path.home().glob(".cache/ms-playwright/*/chrome-linux64/chrome"))
CHROME = str(CHROME_CANDIDATES[-1]) if CHROME_CANDIDATES else None
assert CHROME, "chromium not found: ls ~/.cache/ms-playwright/"


def make_initdata() -> str:
    token = re.search(r"^BOT_TOKEN_WORKER=(.+)$", ENV_PATH.read_text(), re.M).group(1).strip()
    data = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDdF6IQ",
        "user": json.dumps({"id": 350262645, "first_name": "Vasily", "username": "vasily"}, ensure_ascii=False),
    }
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(data)


AUDIT_JS = """
() => {
  const vw = document.documentElement.clientWidth
  const out = []; const seen = new Set()
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect()
    if (r.right > vw + 1 || r.left < -1) {
      const key = el.tagName + '.' + (el.className && el.className.toString ? el.className.toString().slice(0, 60) : '')
      if (!seen.has(key)) { seen.add(key); out.push({key, left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width)}) }
    }
  })
  return { vw, docScrollW: document.documentElement.scrollWidth,
           hasHS: document.documentElement.scrollWidth > vw + 1, overflows: out.slice(0, 15) }
}
"""


def main() -> None:
    init = make_initdata()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
        # НЕ is_mobile=True: headless chromium отдаёт layout-viewport 980 и SPA не рендерится.
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        page.goto(f"{BASE}/web/", wait_until="domcontentloaded", timeout=60000)
        status = page.evaluate(
            f"fetch('/api/auth/telegram', {{method:'POST', headers:{{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'}}, credentials:'include', body: JSON.stringify({{init_data: {json.dumps(init)}}})}}).then(r => r.status)"
        )
        print("auth/telegram:", status)
        page.goto(f"{BASE}/web/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        print("landing path:", page.evaluate("() => location.pathname"))

        def nav(label: str) -> bool:
            link = page.locator('[data-testid="crm-bottom-nav"] a:has-text("' + label + '")').first
            if link.count() == 0:
                return False
            link.click()
            page.wait_for_timeout(3000)
            return True

        # табы BottomNav (b3813ac): 4 рабочих + Настройки/Профиль внизу
        for key, label in [("clients", "Клиенты"), ("schedule", "Записи"), ("chat", "Чаты"), ("stats", "Отчёты"), ("settings", "Настройки"), ("profile", "Профиль")]:
            try:
                ok = nav(label)
                data = page.evaluate(AUDIT_JS)
                print(f"\n=== {key} (nav={ok}) ===")
                print(f"vw={data['vw']} docW={data['docScrollW']} hScroll={data['hasHS']}")
                for o in data["overflows"][:10]:
                    print(f"  OUT: {o['key']} L={o['left']} R={o['right']} w={o['w']}")
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {key}: {e}")

        # панель уведомлений: на мобиле — полноэкранный оверлей (0<=left, right<=vw)
        try:
            page.click('[data-testid="crm-notif-bell"]')
            page.wait_for_timeout(600)
            box = page.evaluate("""() => {
              const el = document.querySelector('[data-testid="crm-notif-dropdown"]')
              if (!el) return null
              const r = el.getBoundingClientRect()
              return {left: r.left, right: r.right, vw: innerWidth}
            }""")
            print(f"\n=== notif panel === {box}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL notif: {e}")
        browser.close()


if __name__ == "__main__":
    main()
