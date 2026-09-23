#!/usr/bin/env bash
# Генерирует initData супер-админа lead-platform для curl-проверки админских API
# (например GET /api/admin/leads, /api/admin/site). Подпись по схеме Telegram Web App
# (HMAC-SHA256), токен — BOT_TOKEN_WORKER из ~/projects/lead-platform/.env.
#
# Использование:
#   INITDATA=$(~/.hermes/skills/lead-platform-ops/scripts/gen_initdata.sh)
#   curl -s http://localhost:8000/api/admin/leads -H "X-Telegram-Init-Data: $INITDATA"
#
# Переопределить пользователя: TG_ID=350262645 ~/.../gen_initdata.sh
set -euo pipefail

ENV_FILE="${LEAD_PLATFORM_ENV:-$HOME/projects/lead-platform/.env}"
TG_ID="${TG_ID:-350262645}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ENV not found: $ENV_FILE" >&2
  exit 1
fi

# .env не виден через os.getenv вне контейнера — подгружаем явно
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

TOKEN="${BOT_TOKEN_WORKER:-}"
if [[ -z "$TOKEN" ]]; then
  echo "BOT_TOKEN_WORKER is empty in $ENV_FILE" >&2
  exit 1
fi

python3 - "$TOKEN" "$TG_ID" <<'PYEOF'
import hashlib, hmac, sys, time
from urllib.parse import urlencode

token, tg_id = sys.argv[1], int(sys.argv[2])

def sign(tok: str, dcs: str) -> str:
    secret = hmac.new(b"WebAppData", tok.encode(), hashlib.sha256).digest()
    return hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()

pairs = {
    "auth_date": str(int(time.time())),
    "query_id": "AAHdF6IQAAAAAN0XohD2ZrOC",
    "user": '{"id":%d,"first_name":"Vasiliy","username":"vasya"}' % tg_id,
}
data_check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
pairs["hash"] = sign(token, data_check)
print(urlencode(pairs))
PYEOF
