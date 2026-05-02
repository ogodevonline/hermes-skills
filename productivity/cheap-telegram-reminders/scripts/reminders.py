#!/usr/bin/env python3
"""Universal Reminders — читает задачи, привычки и периодику из SQLite.
Запускается cron'ом каждый час (08:00-00:00 МСК). Отправляет напоминания в Telegram."""

import os
os.environ['TZ'] = 'Europe/Moscow'
import time
time.tzset()
import sqlite3
import requests
from datetime import datetime
from pathlib import Path

HERMES_HOME = os.path.expanduser("~/.hermes")
DB = Path(HERMES_HOME) / "tasks" / "tasks.db"

def getenv(key, default=None):
    env_file = Path(HERMES_HOME) / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    return default

def send_telegram(text):
    token = getenv("TELEGRAM_BOT_TOKEN")
    chat_id = getenv("TELEGRAM_ALLOWED_USERS", "350262645")
    if not token or token.startswith("***"):
        print("❌ TELEGRAM_BOT_TOKEN не найден")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(url, json=data, timeout=10)
        if r.ok:
            return True
        print(f"❌ Telegram API: {r.text}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
    return False

def get_db():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    return conn

def is_today_right_day(weekdays: str) -> bool:
    """Проверка дня недели. weekdays: 'Пн,Ср,Пт' или пусто (каждый день)."""
    if not weekdays:
        return True
    day_map = {
        "пн": 0, "вт": 1, "ср": 2, "чт": 3,
        "пт": 4, "сб": 5, "вс": 6,
    }
    today_weekday = datetime.now().weekday()
    for d in weekdays.split(","):
        d = d.strip().lower()[:3]
        if d in day_map and day_map[d] == today_weekday:
            return True
    return False

def check_tasks():
    """Задачи с time-based reminder на текущее время."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    messages = []
    try:
        conn = get_db()
        today_str = now.strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT name, reminder, duration, priority FROM tasks "
            "WHERE due_date = ? AND status = 'pending' AND reminder = ?",
            (today_str, current_time)
        ).fetchall()
        conn.close()
        for row in rows:
            msg = f"⏰ Задача: {row['name']}"
            if row["duration"]:
                msg += f" ⏱{row['duration']}"
            msg += f" [приоритет: {row['priority']}]"
            messages.append(msg)
    except Exception as e:
        print(f"⚠️ Ошибка SQLite tasks: {e}")
    return messages

def check_habits():
    """Привычки на текущее время (из SQLite)."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    messages = []
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT id, name, time, weekdays FROM habits WHERE time = ?",
            (current_time,)
        ).fetchall()
        conn.close()
        for row in rows:
            weekdays = row["weekdays"] or ""
            if is_today_right_day(weekdays):
                messages.append(f"✅ Привычка: {row['name']}")
    except Exception as e:
        print(f"⚠️ Ошибка SQLite habits: {e}")
    return messages

def check_periodic():
    """Периодические задачи — с защитой от дублей через last_sent_hour."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_hour = now.hour
    messages = []
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT id, name, every, start_time, end_time, last_sent_hour "
            "FROM periodic"
        ).fetchall()
        for row in rows:
            if not (row["start_time"] <= current_time <= row["end_time"]):
                continue
            if row["last_sent_hour"] == current_hour:
                continue
            messages.append(f"🔄 Периодическое: {row['name']} (каждые {row['every']})")
            conn.execute(
                "UPDATE periodic SET last_sent_hour = ? WHERE id = ?",
                (current_hour, row["id"])
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Ошибка SQLite periodic: {e}")
    return messages

def main():
    print(f"🔔 Reminders check at {datetime.now().strftime('%H:%M')} МСК")
    all_messages = []
    all_messages.extend(check_tasks())
    all_messages.extend(check_habits())
    all_messages.extend(check_periodic())
    if all_messages:
        text = "\n".join(all_messages)
        print(f"📤 Отправка {len(all_messages)} уведомлений:\n{text}")
        success = send_telegram(text)
        print(f"{'✅' if success else '❌'} Отправлено" if success else "❌ Ошибка отправки")
    else:
        print("✅ Нет уведомлений на этот раз")

if __name__ == "__main__":
    main()