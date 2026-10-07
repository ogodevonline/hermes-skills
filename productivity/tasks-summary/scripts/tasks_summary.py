#!/usr/bin/env python3
"""Вывод активных задач из Google Tasks (источник истины с 06.10.2026).

Читает открытые (needsAction) задачи из списков ⛅ TODAY и 📥 BACKLOG через
skills/productivity/google-workspace/scripts/tasks_api.py (OAuth уже настроен,
свой не пишем). Локальная tasks.db больше не используется.
"""
import os
import sys
from pathlib import Path

HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
TASKS_SCRIPTS = HERMES_HOME / "skills" / "productivity" / "google-workspace" / "scripts"
if str(TASKS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TASKS_SCRIPTS))
from tasks_api import get_service  # noqa: E402

TODAY_LIST = "VDhuNDh2enVHY1I3TlBtUQ"                 # ⛅ TODAY
BACKLOG_LIST = "MDM0ODI5NzY3OTIxMTU4MDMzOTQ6MDow"    # 📥 BACKLOG


def fetch_open(service, tasklist):
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


def main():
    try:
        service = get_service()
    except Exception as e:
        print(f"❌ Google Tasks недоступен: {e}")
        return

    active = []
    for list_id, prefix in ((TODAY_LIST, ""), (BACKLOG_LIST, "📥 ")):
        try:
            for t in fetch_open(service, list_id):
                active.append((prefix, t))
        except Exception as e:
            print(f"❌ Ошибка Google Tasks: {e}")
            return

    if not active:
        print("✅ Все задачи выполнены")
        return

    print("📋 **Задачи:**")
    for i, (prefix, t) in enumerate(active, 1):
        raw = t.get("title", "")
        line = raw.replace("❗", "").strip()
        mark = "🔴 " if "❗" in raw else ""
        print(f"{i}. {mark}{prefix}{line}")


if __name__ == "__main__":
    main()
