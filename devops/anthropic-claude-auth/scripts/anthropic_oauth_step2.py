"""Шаг 2 из 2: обмен кода на токены и запись их в home профиля.

Запуск:
  HERMES_HOME=/home/hermes/.hermes/profiles/<name> \
    ~/.hermes/hermes-agent/.venv/bin/python3 anthropic_oauth_step2.py '<code>#<state>'

Код берётся со страницы после «Authorize» — целиком, вместе с частью после `#`
(она проверяется как CSRF-guard, обрезанный код не пройдёт).

СРОК ЖИЗНИ: токен-эндпоинт отдаёт `expires_in` (секунды). Если не записать `expiresAt`,
Hermes считает токен вечным и не обновляет его — а к моменту 401 refresh-токен обычно
уже мёртв, и нужен новый логин. Поэтому expiresAt здесь считается из expires_in.

Чтобы Claude был виден во ВСЕХ профилях (включая default/Telegram), после этого
перепиши токены в формат Claude Code — см. Шаг 4 в SKILL.md (`~/.claude/.credentials.json`).
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/hermes/.hermes/hermes-agent")
from agent import anthropic_credentials as ac  # noqa: E402

STATE_FILE = Path(os.environ.get(
    "ANTHROPIC_OAUTH_STATE",
    os.path.expanduser("~/.hermes/cache/scratch/anthropic_oauth_state.json"),
))

if len(sys.argv) < 2:
    sys.exit("usage: anthropic_oauth_step2.py '<code>#<state>'")

raw = sys.argv[1].strip()
st = json.loads(STATE_FILE.read_text())
code, _, recv_state = raw.partition("#")
if recv_state != st["state"]:
    sys.exit("STATE_MISMATCH: код от другой попытки, запроси новый")

payload = json.dumps({
    "grant_type": "authorization_code",
    "client_id": ac._OAUTH_CLIENT_ID,
    "code": code,
    "state": recv_state,
    "redirect_uri": ac._OAUTH_REDIRECT_URI,
    "code_verifier": st["verifier"],
}).encode()

result = ac._post_oauth_token(payload, content_type="application/json", timeout=25, what="exchange")
access = result.get("access_token") or result.get("accessToken")
refresh = result.get("refresh_token") or result.get("refreshToken")
expires = result.get("expires_at") or result.get("expiresAt")
expires_in = int(result.get("expires_in") or 0)
if not access:
    sys.exit("NO_ACCESS_TOKEN: " + json.dumps(result)[:300])
if not expires:
    if expires_in:
        expires = int((time.time() + expires_in) * 1000)
    else:
        print("WARNING: в ответе нет ни expires_at, ни expires_in — токен сохранён без срока,\n"
              "         авто-обновление работать НЕ будет; сообщи об этом, а не молчи.")

ac._write_hermes_oauth_credentials(access, refresh, expires)
print("SAVED ok: access_token len=%d refresh=%s expires_in=%s expiresAt=%s"
      % (len(access), bool(refresh), expires_in or None, expires))
print("file:", ac._get_hermes_oauth_file())
