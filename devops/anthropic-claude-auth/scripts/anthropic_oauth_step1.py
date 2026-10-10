"""Шаг 1 из 2: ссылка авторизации Claude + сохранение PKCE-состояния на диск.

Зачем отдельный шаг: `hermes -p <name> auth add anthropic --type oauth` держит
`code_verifier` в памяти процесса, и если процесс завершился, пока пользователь
добывал код (а он отвечает не мгновенно), код становится мусором. Здесь verifier
сохраняется в файл, поэтому ждать можно сколько угодно.

Запуск:
  HERMES_HOME=/home/hermes/.hermes/profiles/<name> \
    ~/.hermes/hermes-agent/.venv/bin/python3 anthropic_oauth_step1.py

Печатает ссылку для пользователя. Отдавать дословно, без обрезки: она привязана
к сохранённому состоянию.
"""
import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, "/home/hermes/.hermes/hermes-agent")
from agent import anthropic_credentials as ac  # noqa: E402

STATE_FILE = Path(os.environ.get(
    "ANTHROPIC_OAUTH_STATE",
    os.path.expanduser("~/.hermes/cache/scratch/anthropic_oauth_state.json"),
))

verifier, challenge = ac._generate_pkce()
state = secrets.token_urlsafe(32)
params = {
    "code": "true",
    "client_id": ac._OAUTH_CLIENT_ID,
    "response_type": "code",
    "redirect_uri": ac._OAUTH_REDIRECT_URI,
    "scope": ac._OAUTH_SCOPES,
    "code_challenge": challenge,
    "code_challenge_method": "S256",
    "state": state,
}
url = "https://claude.ai/oauth/authorize?" + urlencode(params)

STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
STATE_FILE.write_text(json.dumps({"verifier": verifier, "state": state, "url": url}))
os.chmod(STATE_FILE, 0o600)

print(url)
print("state saved to:", STATE_FILE, file=sys.stderr)
