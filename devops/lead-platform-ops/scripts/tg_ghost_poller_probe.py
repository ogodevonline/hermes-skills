#!/usr/bin/env python3
"""Призрак-поллер Telegram: честная проверка держателя long-poll сессии.

Мгновенный 409 (<5 c из 30 ожидаемых) = активный конкурирующий getUpdates где-то
есть (не «старые TCP»). ok:true = сессия свободна.
НЕ использовать offset=-1 как доказательство отсутствия призрака — он не ждёт
и не конкурирует по polling-сессии (ложноотрицательный результат, урок 09.09).

Запуск: python3 tg_ghost_poller_probe.py  (токены читает из ~/projects/lead-platform/.env)
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ENV = Path.home() / "projects/lead-platform/.env"
API = "https://api.telegram.org/bot{token}/getUpdates?timeout=30&limit=1"


def tokens() -> dict[str, str]:
    text = ENV.read_text()
    out = {}
    for kind in ("CLIENT", "WORKER"):
        m = re.search(rf"^BOT_TOKEN_{kind}=(\S+)", text, re.MULTILINE)
        if m:
            out[kind] = m.group(1).strip('"\'')
    return out


def probe(token: str) -> tuple[str, float]:
    req = urllib.request.Request(API.format(token=token))
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = json.loads(r.read())
    except Exception as exc:  # noqa: BLE001
        return f"ERROR {exc}", time.monotonic() - t0
    dt = time.monotonic() - t0
    if body.get("ok"):
        return f"OK (сессия свободна; {len(body['result'])} pending)", dt
    return f"{body.get('error_code')} {body.get('description','')}", dt


def main() -> int:
    toks = tokens()
    if not toks:
        print(f"нет BOT_TOKEN_* в {ENV}", file=sys.stderr)
        return 2
    rc = 0
    for kind, tok in toks.items():
        verdict, dt = probe(tok)
        ghost = "409" in verdict and dt < 5
        print(f"{kind} ({tok[:10]}...): {verdict} за {dt:.1f} c"
              + ("  => ПРИЗРАК АКТИВЕН — искать поллер на других машинах"
                 if ghost else ""))
        rc = 1 if ghost else rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
