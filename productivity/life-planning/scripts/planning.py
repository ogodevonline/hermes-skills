#!/usr/bin/env python3
"""Сборщик данных для Life Planning.

Читает:
  1. Obsidian дневники за период (задачи ✅, привычки ✅, 8 сфер, рефлексия)
  2. MEMORY.md — все факты
  3. USER.md — профиль
  4. Планы из Планирование/ — 4 предыдущих + текущий

Не вызывает t list / t habits — дневники содержат всё.
Выдаёт JSON.
"""

import json, sys, datetime, re
from pathlib import Path

HOME = Path.home()
DIARY = HOME / "hermes-vault" / "Дневник"
PLANS = HOME / "hermes-vault" / "Планирование"
PROJECTS = HOME / "hermes-vault" / "Проекты"
MEMORY_FILE = HOME / ".hermes" / "memories" / "MEMORY.md"
USER_FILE = HOME / ".hermes" / "memories" / "USER.md"
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
SPHERE_EMOJIS = r'[💼❤️👨‍👩‍👧📚💪🏠🤝🎮🎯]'


def parse_diary(path):
    """Парсит дневник: задачи ✅, привычки ✅, 8 сфер, рефлексия."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    result = {
        "date": path.stem,
        "done_tasks": [],
        "done_habits": [],
        "spheres": {},
        "reflections": {}
    }

    in_section = None  # tasks / habits / spheres / none

    for line in lines:
        # Определение секции
        if re.match(r'^#{1,3}\s', line):
            if "Задач" in line:
                in_section = "tasks"
            elif "Привыч" in line:
                in_section = "habits"
            elif "Восемь сфер" in line or "8 сфер" in line:
                in_section = "spheres"
            elif "Рефлекс" in line:
                in_section = "reflections"
            else:
                in_section = None
            continue

        # Задачи ✅
        if in_section == "tasks" and line.strip().startswith("✅"):
            result["done_tasks"].append(line.strip())

        # Привычки ✅
        if in_section == "habits" and line.strip().startswith("✅"):
            result["done_habits"].append(line.strip())

        # Сферы: | 💼 Карьера | 7 | текст | или | 💼 Карьера | текст |
        if in_section == "spheres":
            m = re.search(r'\|\s*' + SPHERE_EMOJIS + r'\s*(.+?)\s*\|\s*(\d+)\s*\|', line)
            if m:
                result["spheres"][m.group(1).strip()] = {"score": int(m.group(2))}
                continue
            m = re.search(r'\|\s*' + SPHERE_EMOJIS + r'\s*(.+?)\s*\|\s*(.+?)\s*\|', line)
            if m:
                result["spheres"][m.group(1).strip()] = {"comment": m.group(2).strip()}

    # Рефлексия (5 вопросов) — ищем **1. ...?** текст
    for q in range(1, 6):
        m = re.search(
            r'\*\*' + str(q) + r'\.\s*(.+?)\?\*\*\s*\n(.+?)(?:\n\n|\Z)',
            text, re.DOTALL
        )
        if m:
            result["reflections"][f"q{q}"] = m.group(2).strip()

    return result


def get_diaries(period="week", now=None):
    """Собирает дневники за период (от now назад)."""
    if now is None:
        now = datetime.date.today()
    if not DIARY.exists():
        return []
    days = {"week": 7, "month": 30, "quarter": 90, "year": 365, "5y": 1825, "10y": 3650}.get(period, 7)
    entries = []
    for i in range(days):
        d = now - datetime.timedelta(days=i)
        f = DIARY / f"{d.isoformat()}.md"
        if f.exists():
            parsed = parse_diary(f)
            if parsed:
                entries.append(parsed)
    return entries


def get_plans(period="week", now=None, count=5):
    """Читает ВСЕ файлы планов из Планирование/ + проекты из Проекты/."""
    result = {}

    # Читаем всё из Планирование/
    if PLANS.exists():
        for f in sorted(PLANS.glob("*.md"), reverse=True):
            result[f.stem] = f.read_text(encoding="utf-8", errors="replace")

    # Добавляем проекты из Проекты/
    if PROJECTS.exists():
        for f in sorted(PROJECTS.rglob("*.md")):
            rel = str(f.relative_to(PROJECTS))
            if rel == "README.md":
                continue
            result[rel] = f.read_text(encoding="utf-8", errors="replace")

    return result


def read_text_files():
    """Читает MEMORY.md и USER.md."""
    result = {"memory": [], "user_profile": []}
    if MEMORY_FILE.exists():
        text = MEMORY_FILE.read_text(encoding="utf-8", errors="replace")
        result["memory"] = [s.strip() for s in text.split("§") if s.strip()]
    if USER_FILE.exists():
        text = USER_FILE.read_text(encoding="utf-8", errors="replace")
        result["user_profile"] = [s.strip() for s in text.split("§") if s.strip()]
    return result


def generate(period="week", now=None):
    if now is None:
        now = datetime.date.today()
    elif isinstance(now, str):
        now = datetime.date.fromisoformat(now)

    diaries = get_diaries(period, now)
    plans = get_plans(period, now)
    user = read_text_files()

    # Сводка по сферам из дневников
    sphere_summary = {}
    for d in diaries:
        for sphere, data in d["spheres"].items():
            if sphere not in sphere_summary:
                sphere_summary[sphere] = {"comments": [], "scores": []}
            if "comment" in data:
                sphere_summary[sphere]["comments"].append(data["comment"])
            if "score" in data:
                sphere_summary[sphere]["scores"].append(data["score"])
    for s in sphere_summary:
        if sphere_summary[s]["scores"]:
            sc = sphere_summary[s]["scores"]
            sphere_summary[s]["avg"] = round(sum(sc) / len(sc), 1)

    # Статистика по неделе
    week_stats = {"days_with_diary": len(diaries), "total_done_tasks": 0, "total_done_habits": 0}
    for d in diaries:
        week_stats["total_done_tasks"] += len(d["done_tasks"])
        week_stats["total_done_habits"] += len(d["done_habits"])

    data = {
        "meta": {
            "period": period,
            "date": now.isoformat(),
            "day_of_week": WEEKDAYS[now.weekday()]
        },
        "week_stats": week_stats,
        "sphere_summary": sphere_summary,
        "diaries": [
            {
                "date": d["date"],
                "done_tasks_count": len(d["done_tasks"]),
                "done_tasks": d["done_tasks"],
                "done_habits_count": len(d["done_habits"]),
                "done_habits": d["done_habits"],
                "spheres": d["spheres"],
                "reflections": d["reflections"]
            }
            for d in diaries
        ],
        "plans": plans,
        "user": user
    }

    return json.dumps(data, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    period = "week"
    now_arg = None
    for i, a in enumerate(sys.argv[1:]):
        if a == "--period" and i + 1 < len(sys.argv) - 1:
            period = sys.argv[i + 2]
        elif a == "--now" and i + 1 < len(sys.argv) - 1:
            now_arg = sys.argv[i + 2]
        elif a in ("week", "month", "quarter", "year", "5y", "10y"):
            period = a
    print(generate(period, now_arg))
