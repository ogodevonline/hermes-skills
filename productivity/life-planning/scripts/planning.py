#!/usr/bin/env python3
"""Персональный планировщик — стратегия, тактика, оперативка.

Запуск:
  python3 planning.py                           # план на неделю
  python3 planning.py --period month            # план на месяц
  python3 planning.py --period quarter          # план на квартал
  python3 planning.py --now "2026-06-01"        # от指定 даты
"""

import json, subprocess, sys, datetime
from pathlib import Path
from dataclasses import dataclass

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

@dataclass
class Task:
    id: int
    name: str
    priority: str
    status: str  # ⏳ ✅ ❌

def run_t(*args):
    r = subprocess.run(["t", *args], capture_output=True, text=True, timeout=10)
    return r.stdout.strip()

def parse_tasks(output):
    """Парсит t list — возвращает список Task."""
    import re
    tasks = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("📭") or "───" in line or line.startswith("ID"):
            continue
        # ⏳ 🟡 [23] 22:00 🍲 Название
        # ⏳ 🟡 [23] Название
        m = re.match(r'[✅⏳❌]\s+[🔴🟡🟢]\s+\[(\d+)\]\s*(?:\d+:\d+\s+)?(.*)', line)
        if m:
            tasks.append(Task(id=int(m.group(1)), name=m.group(2).strip(), priority="M", status="⏳"))
    return tasks

def parse_habits(output):
    """Парсит t habits — возвращает список привычек."""
    habits = []
    for line in output.splitlines():
        line = line.strip()
        if not line or "───" in line:
            continue
        # ⏳ [ 1] Omega + D3 08:00
        import re
        m = re.match(r'[✅⏳]\s+\[\s*(\d+)\]\s*(.*)', line)
        if m:
            habits.append({"id": int(m.group(1)), "name": m.group(2).strip()})
    return habits

def generate(period="week", now=None):
    if now is None:
        now = datetime.date.today()
    else:
        now = datetime.date.fromisoformat(now)

    # Параметры периода
    if period == "week":
        days = 7
        title = "НЕДЕЛЯ"
        focus = "ближайшие 7 дней"
    elif period == "month":
        days = 30
        title = "МЕСЯЦ"
        focus = "ближайшие 30 дней"
    elif period == "quarter":
        days = 90
        title = "КВАРТАЛ"
        focus = "ближайшие 3 месяца"
    else:
        days = 7
        title = "НЕДЕЛЯ"
        focus = "ближайшие 7 дней"

    # Собираем данные
    tasks_out = run_t("list")
    habits_out = run_t("habits")
    tasks = parse_tasks(tasks_out)
    habits = parse_habits(habits_out)

    pending = [t for t in tasks if t.status == "⏳"]
    done = [t for t in tasks if t.status == "✅"]

    output = []
    output.append("=" * 60)
    output.append(f"📊 ПЛАНИРОВАНИЕ: {title}")
    output.append(f"Дата: {now.strftime('%d.%m.%Y (%A)')}")
    output.append(f"Период: {focus}")
    output.append("=" * 60)
    output.append("")

    # ----- СТРАТЕГИЯ -----
    output.append("🎯 СТРАТЕГИЯ")
    output.append("-" * 40)

    # Считаем статистику
    total_tasks = len(pending) + len(done)
    done_today = len(done)
    progress = f"{done_today}/{total_tasks} задач" if total_tasks > 0 else "нет задач"

    output.append(f"📌 Текущий прогресс: {progress}")
    output.append(f"🏋️ Привычек в графике: {len(habits)}")
    output.append("")

    # Приоритеты на период
    if pending:
        output.append("🔴 Приоритеты (открытые задачи):")
        for t in pending[:8]:  # топ-8
            output.append(f"  • [{t.id}] {t.name}")
    output.append("")

    output.append("⚡ Фокусы периода:")
    output.append("  • Deep Work — 2-3 часа утром, без уведомлений")
    output.append("  • Спорт — 3-4 тренировки в неделю (записать в календарь)")
    output.append("  • Отношения — зафиксировать вечер с Лимой")
    output.append("  • Сон — 7-8 часов, неприкосновенно")
    output.append("")

    # ----- ТАКТИКА (по дням) -----
    output.append("📅 ТАКТИКА: ПО ДНЯМ")
    output.append("-" * 40)
    output.append("")

    for i in range(days):
        d = now + datetime.timedelta(days=i)
        day_name = WEEKDAYS_RU[d.weekday()]
        is_weekend = d.weekday() >= 5
        marker = "⬜" if is_weekend else "📍"
        day_type = "Выходной" if is_weekend else "Рабочий"
        output.append(f"{marker} День {i+1:2d} | {d.strftime('%d.%m')} ({day_name}) | {day_type}")

        if i == 0:
            output.append(f"     🎯 Главное на сегодня + вечерний дневник")
        elif i == days - 1:
            output.append(f"     🎯 Ревью периода + план на следующий")
        elif i == days // 2:
            output.append(f"     🔄 Чек-пойнт: середина, корректировка")
        elif not is_weekend:
            output.append(f"     Deep Work → задачи → тренировка → Лима")
        else:
            output.append(f"     ☕ Отдых, прогулка, пинг-понг, перезагрузка")
        output.append("")

    # ----- ОПЕРАТИВКА -----
    output.append("⚡ ОПЕРАТИВКА (ежедневный ритуал)")
    output.append("-" * 40)
    output.append("")
    output.append("🌅 Утро (06:00 — morning brief):")
    output.append("  • Прочитать бриф, выбрать 1-3 MUST-задачи")
    output.append("  • Заблокировать Deep Work в календаре")
    output.append("")
    output.append("☀️ День:")
    output.append("  • Deep Work (2-3 часа) — без телефона/уведомлений")
    output.append("  • Правило 1-3-5: 1 главная, 3 средних, 5 мелких")
    output.append("  • Если не закрыл — перенести, не ругать себя")
    output.append("")
    output.append("🌙 Вечер (21:00 — evening brief):")
    output.append("  • Выполнить вечерний дневник (5 вопросов)")
    output.append("  • ✅/⏳/❌ по задачам")
    output.append("  • Настроить задачи на завтра")
    output.append("")

    # ----- РИТУАЛЫ -----
    output.append(f"🔄 РИТУАЛЫ НА {title}:")
    output.append("-" * 40)
    output.append("  🔹 Воскресенье 20:00 — ревью недели")
    output.append("  🔹 Последний день периода — план на следующий")
    output.append("  🔹 Чек-пойнт в середине периода")
    output.append("")

    output.append("=" * 60)
    output.append("💪 Помни:")
    output.append("  • Баланс дисциплины и здоровья")
    output.append("  • Не расстраивать Лиму — планировать заранее")
    output.append("  • Если не успел вечерний бриф — можно за любой день")
    output.append("=" * 60)

    return "\n".join(output)


if __name__ == "__main__":
    period = "week"
    now_arg = None
    args = sys.argv[1:]

    for i, a in enumerate(args):
        if a == "--period" and i + 1 < len(args):
            period = args[i + 1]
        elif a == "--now" and i + 1 < len(args):
            now_arg = args[i + 1]
        elif a in ("week", "month", "quarter"):
            period = a

    print(generate(period, now_arg))
