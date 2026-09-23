#!/usr/bin/env python3
"""
Умное сжатие сессий Hermes — LLM-саммари.

Режимы:
    --summarize  : LLM генерирует осмысленные саммари сессий (через DeepSeek API)
    --compact    : быстрая JSON-сводка без саммари (для совместимости)
    (без флагов) : саммари + ключевые сообщения

Использование:
    python3 compress_sessions.py [--summarize|--compact] [--date YYYY-MM-DD] [--days N]

Зависимости: только stdlib.
API ключ: DEEPSEEK_API_KEY из ~/.hermes/.env или окружения.
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

DB_PATH = Path.home() / ".hermes" / "state.db"
MSK = timezone(timedelta(hours=3))
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MAX_SESSION_LEN = 2000
TIMEOUT = 60


def _read_deepseek_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    env_path = os.path.expanduser("~/.hermes/.env")
    alt_path = os.path.expanduser("~/.hermes/profiles/coach/.env")
    for p in (env_path, alt_path):
        if os.path.exists(p):
            for line in open(p):
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return ""


def call_deepseek(messages: list[dict], model="deepseek-chat") -> str:
    key = _read_deepseek_key()
    if not key:
        return "ERR: no DEEPSEEK_API_KEY"
    payload = json.dumps({"model": model, "messages": messages,
                          "max_tokens": 500, "temperature": 0.3}).encode()
    req = Request(DEEPSEEK_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    })
    resp = json.loads(urlopen(req, timeout=TIMEOUT).read())
    return resp["choices"][0]["message"]["content"]


def get_sessions(cursor, start_ts, end_ts):
    cursor.execute("""
        SELECT id, source, title, started_at, message_count, tool_call_count,
               input_tokens, output_tokens
        FROM sessions WHERE started_at >= ? AND started_at < ?
        ORDER BY started_at
    """, (start_ts, end_ts))
    return [
        {"session_id": r[0], "source": r[1], "title": r[2] or "(без названия)",
         "message_count": r[4] or 0, "tool_call_count": r[5] or 0,
         "input_tokens": r[7] or 0, "output_tokens": r[8] or 0}
        for r in cursor.fetchall()
    ]


def get_session_text(cursor, session_id):
    cursor.execute("""
        SELECT role, content FROM messages
        WHERE session_id = ? AND role IN ('user', 'assistant')
        ORDER BY timestamp
    """, (session_id,))
    lines, total = [], 0
    for r in cursor.fetchall():
        content = (r[1] or "")[:500]
        prefix = "User: " if r[0] == "user" else "Assistant: "
        line = f"{prefix}{content}"
        lines.append(line)
        total += len(line)
        if total > MAX_SESSION_LEN:
            break
    return "\n".join(lines)


def summarize_chunk(sessions, cursor, chunk_start, chunk_size=5):
    chunk = sessions[chunk_start:chunk_start + chunk_size]
    text_parts = []
    for i, sess in enumerate(chunk, chunk_start + 1):
        text = get_session_text(cursor, sess["session_id"])
        if len(text) > 50:
            text_parts.append(f"--- Сессия {i}: {sess['title']} "
                              f"({sess['message_count']} msgs) ---\n{text}")
    if not text_parts:
        return {sess["session_id"]: "(нет данных)" for sess in chunk}

    prompt = (
        "Суммаризируй каждый диалог в 1-2 предложения на русском. "
        "Формат ответа — строго нумерованный список, каждая строка начинается с номера:\n"
        "1. тема: ... решение: ... проблемы: ...\n"
        "2. тема: ... решение: ... проблемы: ...\n\n"
        + "\n\n".join(text_parts)
    )
    try:
        result = call_deepseek([
            {"role": "system", "content": "Ты суммаризатор диалогов. Кратко, по делу, только суть."},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        return {sess["session_id"]: f"(ошибка: {e})" for sess in chunk}

    summaries = {}
    for line in result.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(". ", 1)
        if len(parts) == 2 and parts[0].strip().isdigit():
            n = int(parts[0].strip())
            idx = n - 1
            if 0 <= idx < len(chunk):
                summaries[chunk[idx]["session_id"]] = parts[1].strip()
    # fill missing
    for sess in chunk:
        summaries.setdefault(sess["session_id"], "(нет саммари)")
    return summaries


def summarize_all(sessions, cursor):
    summaries = {}
    for start in range(0, len(sessions), 5):
        summaries.update(summarize_chunk(sessions, cursor, start, 5))
    return summaries


def main():
    parser = argparse.ArgumentParser(description="Умное сжатие сессий Hermes")
    parser.add_argument("--date", type=str, help="YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(json.dumps({"error": f"{DB_PATH} not found"}, ensure_ascii=False))
        sys.exit(0)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    now = datetime.now(MSK)
    if args.date:
        end = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=MSK)
    else:
        end = now

    start = end.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=args.days - 1)
    sessions = get_sessions(cursor, start.timestamp(),
                            (end + timedelta(days=1)).timestamp())

    if args.summarize:
        summaries = summarize_all(sessions, cursor)
        output = {
            "period": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"), "days": args.days},
            "sessions": [{"session_id": s["session_id"], "source": s["source"],
                          "title": s["title"], "message_count": s["message_count"],
                          "tool_call_count": s["tool_call_count"],
                          "summary": summaries.get(s["session_id"], "(нет саммари)")}
                         for s in sessions],
            "summary": {"total_sessions": len(sessions),
                        "total_messages": sum(s["message_count"] for s in sessions),
                        "total_tool_calls": sum(s["tool_call_count"] for s in sessions)},
        }
    elif args.compact:
        output = {
            "period": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"), "days": args.days},
            "sessions": [{"session_id": s["session_id"], "source": s["source"],
                          "title": s["title"], "message_count": s["message_count"],
                          "tool_call_count": s["tool_call_count"]} for s in sessions],
            "summary": {"total_sessions": len(sessions), "total_messages": sum(s["message_count"] for s in sessions),
                        "total_tool_calls": sum(s["tool_call_count"] for s in sessions),
                        "total_input_tokens": sum(s["input_tokens"] for s in sessions),
                        "total_output_tokens": sum(s["output_tokens"] for s in sessions)},
        }
    else:
        summaries = summarize_all(sessions, cursor)
        output = {
            "period": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"), "days": args.days},
            "sessions": [],
            "summary": {"total_sessions": len(sessions), "total_messages": sum(s["message_count"] for s in sessions),
                        "total_tool_calls": sum(s["tool_call_count"] for s in sessions)},
        }
        for s in sessions:
            cursor.execute("""
                SELECT role, content FROM messages
                WHERE session_id = ? AND role IN ('user', 'assistant')
                ORDER BY timestamp
            """, (s["session_id"],))
            rows = cursor.fetchall()
            step = max(1, (len(rows) - 4) // 8) if len(rows) > 8 else 1
            msgs = []
            for i in range(0, len(rows), step):
                msgs.append({"role": rows[i][0], "content": (rows[i][1] or "")[:300]})
                if len(msgs) >= 8:
                    break
            output["sessions"].append({
                "session_id": s["session_id"], "source": s["source"],
                "title": s["title"], "message_count": s["message_count"],
                "tool_call_count": s["tool_call_count"],
                "summary": summaries.get(s["session_id"], "(нет саммари)"),
                "key_messages": msgs,
            })

    conn.close()
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
