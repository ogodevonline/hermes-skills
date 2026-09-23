#!/usr/bin/env python3
"""E2E-проверка контракта «новый клиент + приглашение в бота» на проде.

Подписывает initData САМ внутри процесса (gen_initdata-алгоритм; НЕ копировать
initData из вывода терминала — маска tg_id ломает подпись; ключ HMAC:
`hmac.new(b"WebAppData", token)` — порядок аргументов важен, наоборот -> 401).
Создаёт тестовых клиентов «e2e …», проверяет 422/201+invite/regenerate/400.
Запуск на vdska: python3 check_invite_contract.py
После прогона вычистить: DELETE FROM client_invites WHERE client_user_id IN
(SELECT id FROM users WHERE role='CLIENT' AND name LIKE 'e2e %'); (роль — ВЕРХНИМ
регистром) и те же users.
"""
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError

ENV_PATH = os.path.expanduser("~/projects/lead-platform/.env")
BASE = "http://localhost:8000"


def load_token() -> str:
    m = re.search(r"^BOT_TOKEN_WORKER=(.+)$", open(ENV_PATH).read(), re.M)
    if not m:
        sys.exit("BOT_TOKEN_WORKER not found in .env")
    return m.group(1).strip()


def init_data(token: str, tg_id: int = 350262645) -> str:
    params = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDdF6IQ",
        "user": json.dumps({"id": tg_id, "first_name": "Test",
                            "username": f"testuser{tg_id}"}, ensure_ascii=False),
    }
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    params["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def call(init: str, method: str, path: str, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("X-Telegram-Init-Data", init)
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, data, timeout=15) as r:
            return r.status, json.loads(r.read() or b"null")
    except HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except Exception:
            return e.code, None


def main() -> None:
    init = init_data(load_token())
    url = "/api/admin/clients"
    fails = []

    def check(name, ok, detail=""):
        print(f"{'OK ' if ok else 'FAIL'} {name} {detail}")
        if not ok:
            fails.append(name)

    s, _ = call(init, "POST", url, {"name": "e2e без контакта"})
    check("422 без телефона", s == 422)
    s, r = call(init, "POST", url, {"name": "e2e BT", "no_contact": True})
    check("201 no_contact, invite=null", s == 201 and r.get("invite") is None)
    nc_id = r.get("id")
    s, r = call(init, "POST", url,
                {"name": "e2e Азиза", "phone": "+998 90 666 77 88"})
    link = (r.get("invite") or {}).get("link")
    check("201 + invite.link", s == 201 and bool(link), link or "")
    cid = r.get("id")
    s2, r2 = call(init, "POST", f"{url}/{cid}/invite")
    check("regenerate 200, новый токен", s2 == 200
          and r2.get("link") and r2["link"] != link)
    s3, r3 = call(init, "POST", f"{url}/{nc_id}/invite")
    check("invite без телефона -> 400", s3 == 400,
          (r3 or {}).get("detail", "") or "")
    if fails:
        print("FAILS:", fails)
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
