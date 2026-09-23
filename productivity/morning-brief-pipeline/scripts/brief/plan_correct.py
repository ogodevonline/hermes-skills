#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan correct — коррекция плана дня.

Утилита для утренней коррекции плана: перенос, добавление, удаление пунктов.

Использование:
  plan_correct.py --show [YYYY-MM-DD]         — показать план
  plan_correct.py --add "11:00|Зубы" [--date YYYY-MM-DD]  — добавить
  plan_correct.py --remove N [--date YYYY-MM-DD]           — удалить (1-based)
  plan_correct.py --move N HH:MM [--date YYYY-MM-DD]       — перенести
  plan_correct.py --done N [--date YYYY-MM-DD]              — отметить
  plan_correct.py --edit "текст" [--date YYYY-MM-DD]        — перезаписать план
"""

import sys
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from plan_utils import (
    PlanItem, parse_plan_text, format_plan_table,
    load_plan, update_plan, save_plan,
)

MSK = ZoneInfo("Europe/Moscow")


def get_date(args):
    """Извлечь дату из аргументов."""
    for i, a in enumerate(args):
        if a == "--date" and i + 1 < len(args):
            return args[i + 1]
    return datetime.now(MSK).strftime("%Y-%m-%d")


def strip_flag(args, flag):
    """Удалить флаг и его значение из списка аргументов."""
    result = []
    skip = False
    for i, a in enumerate(args):
        if skip:
            skip = False
            continue
        if a == flag:
            skip = True
            continue
        result.append(a)
    return result


def cmd_show(date_str):
    items = load_plan(date_str)
    print(f"📋 План дня — {date_str}")
    print()
    if not items:
        print("❌ План не задан. Создай через --add или --edit")
        return
    print(format_plan_table(items))
    print()
    print(f"  Всего: {len(items)} пунктов")


def cmd_add(date_str, rest):
    parts = rest.split("|", 1)
    if len(parts) != 2:
        print("❌ Формат: --add \"Время|Действие\" (например \"11:00|Зубы\")")
        return

    time_str, action = parts
    time_str = time_str.strip()
    action = action.strip()

    # Нормализовать время
    if re.match(r"^\d{1,2}$", time_str):
        time_str = f"{time_str.zfill(2)}:00"
    elif re.match(r"^\d{1,2}:\d{2}$", time_str):
        time_str = f"{int(time_str.split(':')[0]):02d}:{time_str.split(':')[1]}"
    else:
        print(f"❌ Неверный формат времени: {time_str}. Используй HH:MM")
        return

    items = load_plan(date_str)
    item = PlanItem(time=time_str, action=action)
    items.append(item)
    items.sort(key=lambda x: x.time)
    update_plan(date_str, items, f"plan add {date_str}")

    print(f"✅ Добавлено: {time_str} — {action}")
    print()
    cmd_show(date_str)


def cmd_remove(date_str, rest):
    try:
        idx = int(rest.strip()) - 1
    except ValueError:
        print("❌ Индекс должен быть числом (1-based)")
        return

    items = load_plan(date_str)
    if idx < 0 or idx >= len(items):
        print(f"❌ Нет пункта #{idx + 1}. Всего: {len(items)}")
        return

    removed = items.pop(idx)
    update_plan(date_str, items, f"plan remove {date_str}")

    print(f"✅ Удалён: {removed.time} — {removed.action}")
    print()
    cmd_show(date_str)


def cmd_move(date_str, rest):
    parts = rest.strip().split()
    if len(parts) != 2:
        print("❌ Формат: --move ИНДЕКС НОВОЕ_ВРЕМЯ")
        return

    try:
        idx = int(parts[0]) - 1
    except ValueError:
        print("❌ Индекс должен быть числом (1-based)")
        return

    new_time = parts[1]
    if re.match(r"^\d{1,2}$", new_time):
        new_time = f"{new_time.zfill(2)}:00"
    elif not re.match(r"^\d{2}:\d{2}$", new_time):
        print(f"❌ Неверный формат времени: {new_time}")
        return

    items = load_plan(date_str)
    if idx < 0 or idx >= len(items):
        print(f"❌ Нет пункта #{idx + 1}")
        return

    item = items[idx]
    old_time = item.time
    item.time = new_time
    items.sort(key=lambda x: x.time)
    update_plan(date_str, items, f"plan move {date_str}")

    print(f"✅ Перенесён: {old_time} → {new_time} — {item.action}")
    print()
    cmd_show(date_str)


def cmd_done(date_str, rest):
    try:
        idx = int(rest.strip()) - 1
    except ValueError:
        print("❌ Индекс должен быть числом (1-based)")
        return

    items = load_plan(date_str)
    if idx < 0 or idx >= len(items):
        print(f"❌ Нет пункта #{idx + 1}")
        return

    item = items[idx]
    item.status = "done"
    update_plan(date_str, items, f"plan done {date_str}")

    print(f"✅ Выполнено: {item.time} — {item.action}")
    print()
    cmd_show(date_str)


def cmd_edit(date_str, text):
    """Перезаписать план из диктовки (полная замена)."""
    items = parse_plan_text(text)
    if not items:
        print("❌ Не удалось распарсить текст. Формат: \"в 11 зубы, в 12 IMEI\"")
        return

    save_plan(date_str, items, f"plan edit {date_str}")
    print(f"✅ План обновлён — {len(items)} пунктов")
    print()
    cmd_show(date_str)


def cmd_help():
    print("""Plan Correct — коррекция плана дня

  Использование:
    plan_correct.py --show [--date YYYY-MM-DD]        — показать план
    plan_correct.py --add "11:00|Зубы" [--date ...]    — добавить пункт
    plan_correct.py --remove N [--date ...]             — удалить пункт (1-based)
    plan_correct.py --move N HH:MM [--date ...]         — перенести пункт
    plan_correct.py --done N [--date ...]                — отметить выполненным
    plan_correct.py --edit "в 11 зубы, в 12 IMEI"       — перезаписать план
    plan_correct.py --help                               — эта справка

  По умолчанию — план на сегодня.
  """)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        cmd_help()
        return

    date_str = get_date(args)
    cmd = args[0]

    # Извлекаем аргумент после команды (всё до --date)
    rest_parts = []
    for i, a in enumerate(args[1:]):
        if a == "--date":
            break
        rest_parts.append(a)
    rest = " ".join(rest_parts).strip()

    if cmd == "--show":
        cmd_show(date_str)
    elif cmd == "--add":
        cmd_add(date_str, rest)
    elif cmd == "--remove":
        cmd_remove(date_str, rest)
    elif cmd == "--move":
        cmd_move(date_str, rest)
    elif cmd == "--done":
        cmd_done(date_str, rest)
    elif cmd == "--edit":
        cmd_edit(date_str, rest)
    else:
        print(f"❌ Неизвестная команда: {cmd}")
        cmd_help()


if __name__ == "__main__":
    main()
