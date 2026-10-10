"""Отдать OAuth-токены Claude ВСЕМ профилям Hermes (шаг после авторизации).

Профили изолированы: токены, полученные в `hermes -p <name> auth add anthropic`,
лежат только в home этого профиля, и в чате gateway (профиль default) `/model`
Anthropic не покажет. Hermes подхватывает креды как borrowed login из файла
Claude Code — его и пишем (`auth.adopt_external_logins` по умолчанию включён).

Запуск (токены берутся из профиля, куда авторизовались):
  python3 claude_code_credentials.py /home/hermes/.hermes/profiles/<name>/.anthropic_oauth.json

Проверка потом:
  hermes chat -q "ты кто и какая модель?" -m claude-sonnet-4-5-20250929 --provider anthropic
"""
import json
import os
import sys
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1
           else "~/.hermes/.anthropic_oauth.json").expanduser()
dst = Path.home() / ".claude" / ".credentials.json"

d = json.loads(src.read_text())
record = {"claudeAiOauth": {
    "accessToken": d.get("accessToken"),
    "refreshToken": d.get("refreshToken"),
    # expiresAt обязателен: без срока Hermes считает токен вечным и не обновляет его,
    # а к моменту 401 refresh-токен обычно уже мёртв — лечится только новым логином.
    "expiresAt": d.get("expiresAt"),
    "scopes": ["user:inference", "user:profile", "org:create_api_key"],
}}

if not record["claudeAiOauth"]["expiresAt"]:
    print("WARNING: в источнике нет expiresAt — авто-обновление работать не будет.\n"
          "         Сначала переавторизуйся через scripts/anthropic_oauth_step1.py + step2\n"
          "         (step2 пишет expiresAt из expires_in), потом повтори этот скрипт.")

dst.parent.mkdir(parents=True, exist_ok=True)
tmp = dst.with_suffix(dst.suffix + ".tmp")
tmp.write_text(json.dumps(record, indent=2))
os.chmod(tmp, 0o600)
tmp.replace(dst)
print("written:", dst, "| accessToken len:", len(record["claudeAiOauth"]["accessToken"] or ""),
      "| expiresAt:", record["claudeAiOauth"]["expiresAt"])
