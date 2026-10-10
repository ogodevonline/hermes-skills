"""Проверка OAuth-доступа к Anthropic и реальный список моделей аккаунта.

Зачем: отличает «токен живой» от «токен протух» за один вызов и показывает,
какие модели реально доступны подписке (каталог в `/model` бывает fallback-списком
и свежих моделей не содержит).

Запуск:
  python3 anthropic_live_models.py [путь к .anthropic_oauth.json]
  (по умолчанию ~/.hermes/profiles/<name>/.anthropic_oauth.json — передай явно)
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1
           else "~/.hermes/.anthropic_oauth.json").expanduser()
d = json.loads(src.read_text())
rec = d.get("claudeAiOauth", d)
tok = rec.get("accessToken")

# Без anthropic-beta: oauth-2025-04-20 запрос с OAuth-токеном не проходит.
req = urllib.request.Request(
    "https://api.anthropic.com/v1/models?limit=50",
    headers={
        "Authorization": "Bearer " + tok,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "claude-code/2.0.0",
    },
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        ids = [m["id"] for m in json.load(r)["data"]]
        print("OK, доступно моделей:", len(ids))
        for i in ids:
            print("   ", i)
except urllib.error.HTTPError as e:
    body = e.read()[:200].decode("utf-8", "ignore")
    print("HTTP", e.code, body)
    if e.code == 401:
        print("→ токен протух или не обновляется: проверь expiresAt в файле и в "
              "~/.claude/.credentials.json; при invalid_grant нужен новый логин "
              "(anthropic_oauth_step1.py + step2).")
