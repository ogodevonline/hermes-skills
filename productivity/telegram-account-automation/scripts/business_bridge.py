#!/usr/bin/env python3
"""Мост Telegram Business (Secretary Mode): входящие в личку + отправка от имени владельца.

Работает на штатном Bot API — api_id/api_hash НЕ нужны.
Требует: в @BotFather -> Bot Settings -> Secretary Mode включён,
и в аккаунте: Settings -> Telegram Business -> Chatbots -> добавлен username бота.

ВАЖНО: один и тот же токен нельзя поллить из двух процессов (Telegram отдаёт
апдейты только одному). Этот бот должен быть ОТДЕЛЬНЫМ от Hermes-бота.

Статус проверки: --help, getMe, getUpdates прогнаны живьём; ветки
business_message/send требуют включённого Secretary Mode.

Команды:
  poll                 слушать апдейты, складывать в inbox.sqlite3
  inbox [--limit N]    показать последние входящие
  send --to ID --text  отправить от имени владельца (только чаты с входящим за 24ч)
  chats                список подключений и право can_reply
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
CONF = BASE / "config.json"
DB = BASE / "inbox.sqlite3"


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_chat_id: int | None = None

    @classmethod
    def load(cls) -> "Config":
        if not CONF.exists():
            sys.exit(f"Нет {CONF}. Создай: {{\"bot_token\": \"...\", \"owner_chat_id\": 123}}")
        raw = json.loads(CONF.read_text())
        return cls(bot_token=raw["bot_token"], owner_chat_id=raw.get("owner_chat_id"))


def api(cfg: Config, method: str, **params: Any) -> dict:
    url = f"https://api.telegram.org/bot{cfg.bot_token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": e.read().decode(errors="replace")}


def init_db() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.execute(
        """CREATE TABLE IF NOT EXISTS messages (
            msg_id INTEGER, chat_id INTEGER, sender TEXT, text TEXT,
            ts INTEGER, direction TEXT, business_connection_id TEXT,
            PRIMARY KEY (msg_id, direction, chat_id))"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS connections (
            connection_id TEXT PRIMARY KEY, user_id INTEGER, can_reply INTEGER, ts INTEGER)"""
    )
    con.commit()
    return con


def store_message(con: sqlite3.Connection, m: dict, direction: str, conn_id: str | None) -> None:
    chat = m.get("chat", {})
    sender = m.get("from", {})
    name = " ".join(filter(None, [sender.get("first_name"), sender.get("last_name")])) or str(
        sender.get("username") or sender.get("id") or chat.get("id")
    )
    con.execute(
        "INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?,?,?)",
        (
            m.get("message_id", 0),
            chat.get("id", 0),
            name,
            m.get("text", "[не текст]"),
            m.get("date", 0),
            direction,
            conn_id,
        ),
    )
    con.commit()


def handle_update(con: sqlite3.Connection, upd: dict) -> str | None:
    conn = upd.get("business_connection")
    if conn:
        rights = conn.get("rights", {})
        con.execute(
            "INSERT OR REPLACE INTO connections VALUES (?,?,?,?)",
            (conn["id"], conn.get("user", {}).get("id", 0), int(bool(rights.get("can_reply"))), int(time.time())),
        )
        con.commit()
        return f"подключение: can_reply={rights.get('can_reply')}"

    msg = upd.get("business_message")
    if msg:
        store_message(con, msg, "in", msg.get("business_connection_id"))
        who = msg.get("from", {})
        return f"входящее от {who.get('first_name', '?')}: {msg.get('text', '')[:80]}"
    return None


def cmd_poll(cfg: Config) -> None:
    con = init_db()
    offset = 0
    print("слушаю... (Ctrl+C для выхода)", flush=True)
    while True:
        try:
            res = api(
                cfg,
                "getUpdates",
                offset=offset,
                timeout=50,
                allowed_updates=json.dumps(
                    ["business_connection", "business_message", "edited_business_message"]
                ),
            )
        except Exception as e:  # сеть отвалилась — ждём и повторяем
            print(f"ошибка сети: {e}", flush=True)
            time.sleep(5)
            continue
        if not res.get("ok"):
            print(f"ошибка API: {res.get('description') or res.get('error')}", flush=True)
            time.sleep(5)
            continue
        for upd in res.get("result", []):
            offset = upd["update_id"] + 1
            note = handle_update(con, upd)
            if note:
                print(note, flush=True)


def cmd_inbox(_: Config, limit: int) -> None:
    con = init_db()
    rows = con.execute(
        "SELECT ts, sender, text, chat_id FROM messages WHERE direction='in' ORDER BY ts DESC LIMIT ?", (limit,)
    ).fetchall()
    if not rows:
        print("пусто")
    for ts, sender, text, chat_id in rows:
        print(f"[{time.strftime('%d.%m %H:%M', time.localtime(ts))}] chat_id={chat_id} {sender}: {text}")


def cmd_chats(_: Config) -> None:
    con = init_db()
    rows = con.execute(
        "SELECT connection_id, can_reply, datetime(ts,'unixepoch') FROM connections ORDER BY ts DESC"
    ).fetchall()
    if not rows:
        print("нет подключений — Secretary Mode не активирован или бот не добавлен в аккаунт")
    for cid, can_reply, ts in rows:
        print(f"{cid} can_reply={bool(can_reply)} ({ts})")


def cmd_send(cfg: Config, to: int, text: str) -> None:
    con = init_db()
    row = con.execute("SELECT connection_id, can_reply FROM connections ORDER BY ts DESC LIMIT 1").fetchone()
    if not row:
        sys.exit("Нет активного business-подключения")
    conn_id, can_reply = row
    if not can_reply:
        sys.exit("Бот подключён без права can_reply — выдай право в настройках Telegram Business")
    res = api(cfg, "sendMessage", chat_id=to, text=text, business_connection_id=conn_id)
    if not res.get("ok"):
        sys.exit(f"не отправлено: {res.get('description') or res.get('error')}")
    store_message(con, res["result"], "out", conn_id)
    print(f"отправлено в chat_id={to}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("poll")
    sub.add_parser("chats")
    pi = sub.add_parser("inbox")
    pi.add_argument("--limit", type=int, default=20)
    ps = sub.add_parser("send")
    ps.add_argument("--to", type=int, required=True)
    ps.add_argument("--text", required=True)
    args = p.parse_args()

    cfg = Config.load()
    if args.cmd == "poll":
        cmd_poll(cfg)
    elif args.cmd == "chats":
        cmd_chats(cfg)
    elif args.cmd == "inbox":
        cmd_inbox(cfg, args.limit)
    elif args.cmd == "send":
        cmd_send(cfg, args.to, args.text)


if __name__ == "__main__":
    main()
