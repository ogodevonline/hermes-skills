#!/usr/bin/env python3
"""Сборщик данных для Life Planning.

Читает:
  1. Obsidian дневники за период (задачи ✅, привычки ✅, 8 сфер, рефлексия)
  2. MEMORY.md — все факты
  3. USER.md — профиль
  4. Планы из Projects/Planning/ — 4 предыдущих + текущий

Не вызывает t list / t habits — дневники содержат всё.
Выдаёт JSON.
"""

import json, sys, datetime, re
from pathlib import Path

HOME = Path.home()
DIARY = HOME / "hermes-vault" / "Journal"
PLANS = HOME / "hermes-vault" / "Projects" / "Planning"
PROJECTS = HOME / "hermes-vault" / "Projects"
MEMORY_FILE = HOME / ".hermes" / "memories" / "MEMORY.md"
USER_FILE = HOME / ".hermes" / "memories" / "USER.md"
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
SPHERE_EMOJIS = r'[💼❤️👨‍👩‍👧📚💪🏠🤝🎮🎯]'


def parse_diary(path):
    """Парсит дневник: задачи ✅, привычки ✅, 8 сфер, рефлексия.
    Возвращает None если файла нет, иначе dict с is_empty."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    result = {
        "date": path.stem,
        "done_tasks": [],
        "done_habits": [],
        "spheres": {},
        "reflections": {},
        "is_empty": True
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
            m = re.search(r'\|[\s\uFE0F\u200D]*' + SPHERE_EMOJIS + r'[\s\uFE0F\u200D]*(.+?)\s*\|\s*(\d+)\s*\|', line)
            if m:
                result["spheres"][m.group(1).strip()] = {"score": int(m.group(2))}
                continue
            m = re.search(r'\|[\s\uFE0F\u200D]*' + SPHERE_EMOJIS + r'[\s\uFE0F\u200D]*(.+?)\s*\|\s*(.+?)\s*\|', line)
            if m:
                result["spheres"][m.group(1).strip()] = {"comment": m.group(2).strip()}

    # Рефлексия (5 вопросов)
    for q in range(1, 6):
        m = re.search(
            r'\*\*' + str(q) + r'\.\s*(.+?)\?\*\*\s*\n(.+?)(?:\n\n|\Z)',
            text, re.DOTALL
        )
        if m:
            result["reflections"][f"q{q}"] = m.group(2).strip()

    # Детект пустого шаблона
    all_reflections_empty = all(
        v.strip(" _") == "" for v in result["reflections"].values()
    ) if result["reflections"] else True
    no_content = (
        len(result["done_tasks"]) == 0
        and len(result["done_habits"]) == 0
        and len(result["spheres"]) == 0
        and all_reflections_empty
    )
    result["is_empty"] = no_content

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
    """Читает ВСЕ файлы планов из Projects/Planning/ + проекты из Projects/."""
    result = {}

    # Читаем всё из Projects/Planning/
    if PLANS.exists():
        for f in sorted(PLANS.glob("*.md"), reverse=True):
            result[f.stem] = f.read_text(encoding="utf-8", errors="replace")

    # Добавляем проекты из Projects/
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

    diaries = [d for d in get_diaries(period, now) if not d.get("is_empty", True)]
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

    # Конвертация sphere_summary → sphere_trends для совместимости с hermes-hub
    SPHERE_EMOJI = {
        "Карьера": "💼", "Лима": "❤️", "Семья": "👨‍👩‍👧", "Развитие": "📚",
        "Здоровье": "💪", "Быт": "🏠", "Друзья": "🤝", "Отдых": "🎮",
    }
    sphere_trends = []
    for name, data in sphere_summary.items():
        entry = {"name": name, "emoji": SPHERE_EMOJI.get(name, "📌"), "avg": data.get("avg", 0)}
        if isinstance(entry["avg"], (int, float)) and entry["avg"] < 5:
            entry["direction"] = "🔻"
        sphere_trends.append(entry)

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
        "sphere_trends": sphere_trends,
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


def goals_checkin():
    """Краткая текстовая сводка целей на сегодня (для вечернего брифа).
    Считает с начала текущей недели (понедельник) по сегодня."""
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())  # понедельник
    week_diaries = [d for d in get_diaries("week", today) if not d.get("is_empty", True)]
    # Оставляем только с начала недели
    week_diaries = [d for d in week_diaries if d["date"] >= week_start.isoformat()]

    streak = 0
    for d in sorted(week_diaries, key=lambda x: x["date"], reverse=True):
        if d["done_tasks"] or d["done_habits"]:
            streak += 1
        else:
            break

    total_tasks = sum(len(d["done_tasks"]) for d in week_diaries)
    total_habits = sum(len(d["done_habits"]) for d in week_diaries)

    # Последний дневник
    last = week_diaries[0] if week_diaries else None
    spheres_text = ""
    if last and last["spheres"]:
        low = [s for s, v in last["spheres"].items() if isinstance(v, dict) and v.get("score", 10) < 6]
        if low:
            spheres_text = f"⚠️ Просадки: {', '.join(low)}"

    lines = [f"📊 {week_start.isoformat()}–{today.isoformat()}: ✅ {total_tasks} задач · привычки ✅ {total_habits} раз(а)"]
    if streak > 1:
        lines.append(f"🔥 Streak: {streak} дней подряд")
    if spheres_text:
        lines.append(spheres_text)
    return "\n".join(lines)


if __name__ == "__main__":
    if "--goals-checkin" in sys.argv:
        print(goals_checkin())
        sys.exit(0)

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
