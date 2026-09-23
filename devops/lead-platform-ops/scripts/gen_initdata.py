#!/usr/bin/env python3
"""Generate Telegram WebApp initData signed with a bot token (for curl checks).

Usage:
  gen_initdata.py [tg_id]            # uses BOT_TOKEN_WORKER from ~/projects/lead-platform/.env
  TG_ID=<id> TG_USERNAME=<uname> gen_initdata.py   # any user (role checks)
  BOT_TOKEN=<token> gen_initdata.py  # override token
"""
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

ENV_PATH = Path.home() / "projects" / "lead-platform" / ".env"


def load_token() -> str:
    if os.environ.get("BOT_TOKEN"):
        return os.environ["BOT_TOKEN"]
    if ENV_PATH.exists():
        m = re.search(r"^BOT_TOKEN_WORKER=(.+)$", ENV_PATH.read_text(), re.M)
        if m:
            return m.group(1).strip()
    raise SystemExit("BOT_TOKEN not found in env or .env")


def main() -> None:
    token = load_token()
    tg_id = int(os.environ.get("TG_ID", sys.argv[1] if len(sys.argv) > 1 else "350262645"))
    uname = os.environ.get("TG_USERNAME", f"testuser{tg_id}")
    first = os.environ.get("TG_FIRST_NAME", "Test")

    data = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDdF6IQ",
        "user": json.dumps({"id": tg_id, "first_name": first, "username": uname}, ensure_ascii=False),
    }
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check_str = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    data["hash"] = hmac.new(secret_key, check_str.encode(), hashlib.sha256).hexdigest()
    print(urllib.parse.urlencode(data))


if __name__ == "__main__":
    main()
