#!/usr/bin/env python3
"""Universal Reminders — задачи из Google Tasks, привычки и периодика из SQLite.
Запускается cron'ом каждый час (08:00-00:00 МСК). Отправляет напоминания в Telegram.

Источник ЗАДАЧ с 06.10.2026 — Google Tasks (список ⛅ TODAY) через
skills/productivity/google-workspace/scripts/tasks_api.py (OAuth уже настроен).
Привычки — из Google Tasks (🌱 HABITS). Локальной базы нет.
Крон Hermes «reminders-hourly» зовёт `reminders.py --stdout`.

Режим без отправки: `python3 reminders.py --dry-run` — печатает открытые задачи
из Google и то, что было бы отправлено, но Telegram не трогает.
"""

import os
os.environ['TZ'] = 'Europe/Moscow'
import time
time.tzset()
import re
import sys
import requests
from datetime import datetime
from pathlib import Path

HERMES_HOME = os.path.expanduser("~/.hermes")

# Google Tasks: список ⛅ TODAY (источник истины для задач)
TASKS_SCRIPTS = Path(HERMES_HOME) / "skills" / "productivity" / "google-workspace" / "scripts"
TODAY_LIST_ID = "VDhuNDh2enVHY1I3TlBtUQ"  # ⛅ TODAY
# Время напоминания у задачи Google Tasks задаётся в notes строкой reminder:HH:MM
REMINDER_RE = re.compile(r"reminder[:=]\s*(\d{1,2}:\d{2})", re.IGNORECASE)

if str(TASKS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TASKS_SCRIPTS))
from tasks_api import get_service  # noqa: E402  (свой OAuth не пишем)


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


# ─── ЗАДАЧИ: Google Tasks ────────────────────────────────────────────────

def fetch_open_tasks(service, tasklist):
    """Все открытые (needsAction) задачи списка, с пагинацией."""
    items, token = [], None
    while True:
        kw = {"tasklist": tasklist, "showCompleted": False, "maxResults": 100}
        if token:
            kw["pageToken"] = token
        res = service.tasks().list(**kw).execute()
        items += res.get("items", [])
        token = res.get("nextPageToken")
        if not token:
            return items


def parse_reminder(notes: str):
    """Время напоминания из notes задачи Google: 'reminder:18:00' -> '18:00'."""
    if not notes:
        return None
    m = REMINDER_RE.search(notes)
    if not m:
        return None
    hh, mm = m.group(1).split(":")
    return f"{int(hh):02d}:{int(mm):02d}"


def check_tasks(dry_run=False):
    """Открытые задачи Google Tasks (⛅ TODAY) с напоминанием на текущее время."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today_str = now.strftime("%Y-%m-%d")
    messages = []
    try:
        service = get_service()
        tasks = fetch_open_tasks(service, TODAY_LIST_ID)
    except Exception as e:
        print(f"⚠️ Ошибка Google Tasks: {e}")
        return messages

    if dry_run:
        print(f"🔎 Открытые задачи Google Tasks (⛅ TODAY): {len(tasks)}")
        for t in tasks:
            due = (t.get("due") or "")[:10] or "-"
            rem = parse_reminder(t.get("notes") or "") or "-"
            print(f"   • {t.get('title', '')} | due={due} | reminder={rem}")

    for t in tasks:
        due = (t.get("due") or "")[:10]
        if due and due != today_str:
            continue
        reminder = parse_reminder(t.get("notes") or "")
        if reminder != current_time:
            continue
        raw_title = t.get("title", "")
        msg = f"⏰ Задача: {raw_title.replace('❗', '').strip()}"
        if "❗" in raw_title:
            msg += " [приоритет: H]"
        messages.append(msg)
    return messages


# ─── ПРИВЫЧКИ: Google Tasks (🌱 HABITS) ───

HABITS_LIST_ID = "Y0c3NGFIRThRTnlWNFRpMg"  # 🌱 HABITS
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
HOURLY_RE = re.compile(r"каждый час", re.IGNORECASE)
HOURLY_WINDOW = (8, 22)


def check_habits():
    """Неотмеченные привычки дня из Google HABITS.

    Крон зовёт скрипт раз в час (HH:00), сверяем только час:
    «18:30 · ...» придёт в 18:00. «каждый час» — каждый час в окне 08–22.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    messages = []
    try:
        cards = fetch_open_tasks(get_service(), HABITS_LIST_ID)
    except Exception as e:
        print(f"⚠️ Ошибка Google HABITS: {e}")
        return messages
    for t in cards:
        if (t.get("due") or "")[:10] != today_str:
            continue
        title = (t.get("title") or "").strip()
        if HOURLY_RE.search(title):
            if HOURLY_WINDOW[0] <= now.hour <= HOURLY_WINDOW[1]:
                messages.append(f"🔄 {title}")
            continue
        m = TIME_RE.search(title)
        if m and int(m.group(1)) == now.hour:
            messages.append(f"✅ Привычка: {title}")
    return messages


def main():
    dry_run = ("--dry-run" in sys.argv) or ("--no-send" in sys.argv)
    stdout_mode = "--stdout" in sys.argv  # крон Hermes --no-agent: stdout уходит в Telegram
    msgs = check_tasks(dry_run=dry_run) + check_habits()
    if stdout_mode:
        if msgs:
            print("\n".join(msgs))
        return
    print(f"🔔 Reminders check at {datetime.now().strftime('%H:%M')} МСК")
    if dry_run:
        print("🧪 DRY-RUN (НЕ отправлено):\n" + ("\n".join(msgs) or "нет уведомлений"))
        return
    if msgs:
        ok = send_telegram("\n".join(msgs))
        print("✅ Отправлено" if ok else "❌ Ошибка отправки")
    else:
        print("✅ Нет уведомлений на этот раз")


if __name__ == "__main__":
    main()
