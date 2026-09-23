#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вечерний дневник с FSM — шаг за шагом, строгий порядок.
Фазы: tasks → habits → spheres → q1..q5 → rating → save

CLI:
  --start [--date YYYY-MM-DD]  — начать новую сессию
  --answer "текст"              — передать ответ, получить следующий вопрос
  (без аргументов)               — показать текущий вопрос
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "skills" / "brief" / "evening-diary-brief" / "scripts"))
from brief_evening_lib import (
    SPHERES, QUESTIONS, PHASE_ORDER, YES_WORDS, NO_WORDS,
    get_date_for_today, filter_night_habits,
    parse_pending_tasks, parse_pending_habits,
    load_state, save_state, save_diary, run_t, PLAN_QUESTION,
)


# ═══════════════════════════════════════════════
# ВОПРОСЫ
# ═══════════════════════════════════════════════

def q_task(s):
    t = s["tasks"][s["step"]]
    return f'Задача [{t["id"]}] {t["name"]} — сделано? (да/нет/пропуск)'

def q_habit(s):
    h = s["habits"][s["step"]]
    return f'Привычка [{h["id"]}] {h["name"]} — делал? (да/нет)'

def q_sphere(s):
    e, n, d = SPHERES[s["step"]]
    return f'{e} {n} — что было? ({d})'

def q_reflect(s):
    return QUESTIONS[int(s["phase"][1]) - 1]

Q_RATING = "Оценка дня /10? (1-10)"

def q_plan(s):
    return PLAN_QUESTION

PHASE_Q = {
    "tasks": q_task, "habits": q_habit, "spheres": q_sphere,
    "q1": q_reflect, "q2": q_reflect, "q3": q_reflect,
    "q4": q_reflect, "q5": q_reflect, "rating": lambda s: Q_RATING,
    "plan": q_plan,
}

def current_q(s):
    fn = PHASE_Q.get(s["phase"])
    return fn(s) if fn else "Сохраняю..."


# ═══════════════════════════════════════════════
# ПЕРЕХОДЫ
# ═══════════════════════════════════════════════

def advance(s, target=None):
    if target:
        s["phase"] = target
    else:
        try:
            s["phase"] = PHASE_ORDER[PHASE_ORDER.index(s["phase"]) + 1]
        except (ValueError, IndexError):
            s["phase"] = "save"
    s["step"] = 0
    save_state(s)
    return current_q(s)


# ═══════════════════════════════════════════════
# СТАРТ
# ═══════════════════════════════════════════════

def start_new(date_str=None):
    today = date_str or get_date_for_today()
    tasks = parse_pending_tasks(today)
    habits = filter_night_habits(parse_pending_habits())

    s = {"date": today, "phase": "tasks", "step": 0, "answers": {},
         "tasks": tasks, "habits": habits}
    save_state(s)

    if not tasks:
        return advance(s, "habits" if habits else "spheres")
    return q_task(s)


# ═══════════════════════════════════════════════
# ОБРАБОТКА ОТВЕТА
# ═══════════════════════════════════════════════

def handle_reply(text):
    s = load_state()
    if not s:
        return "❌ Нет активной сессии. Запусти через --start"
    text = text.strip().lower()

    # ── TASKS ──
    if s["phase"] == "tasks":
        t = s["tasks"][s["step"]]
        if text in YES_WORDS:
            run_t("done", t["id"]); s["answers"][f"task_{t['id']}"] = "✅"
        elif text in NO_WORDS:
            run_t("cancel", t["id"]); s["answers"][f"task_{t['id']}"] = "❌"
        else:
            s["answers"][f"task_{t['id']}"] = "⏳"
        s["step"] += 1
        if s["step"] < len(s["tasks"]):
            save_state(s); return q_task(s)
        return advance(s, "habits" if s["habits"] else "spheres")

    # ── HABITS ──
    if s["phase"] == "habits":
        h = s["habits"][s["step"]]
        if text in YES_WORDS:
            run_t("habit-done", h["id"]); s["answers"][f"habit_{h['id']}"] = "✅"
        else:
            s["answers"][f"habit_{h['id']}"] = "❌"
        s["step"] += 1
        if s["step"] < len(s["habits"]):
            save_state(s); return q_habit(s)
        return advance(s, "spheres")

    # ── SPHERES ──
    if s["phase"] == "spheres":
        _, n, _ = SPHERES[s["step"]]
        s["answers"][f"sphere_{n}"] = text if text.strip() else "—"
        s["step"] += 1
        if s["step"] < len(SPHERES):
            save_state(s); return q_sphere(s)
        return advance(s, "q1")

    # ── REFLECTION ──
    if s["phase"].startswith("q"):
        idx = int(s["phase"][1])
        s["answers"][f"q_{idx}"] = text if text.strip() else "_ _"
        return advance(s, f"q{idx + 1}") if idx < 5 else advance(s, "rating")

    # ── RATING ──
    if s["phase"] == "rating":
        try:
            s["answers"]["rating"] = str(max(1, min(10, int(text.strip()))))
        except ValueError:
            s["answers"]["rating"] = "5"
        save_state(s)
        # После оценки — спросить про план на завтра
        return advance(s, "plan")

    # ── PLAN ──
    if s["phase"] == "plan":
        s["plan_text"] = text
        save_state(s)
        return save_diary(s)

    return "Продолжаем..."


# ═══════════════════════════════════════════════
# СТАТУС
# ═══════════════════════════════════════════════

def show_current():
    s = load_state()
    return current_q(s) if s else "❌ Нет активной сессии. Запусти через --start"


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    date_arg = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--date" and i + 1 < len(args):
            date_arg = args[i + 1]
            args = args[:i] + args[i + 2:]
            break
    if args and args[0] == "--start":
        print(start_new(date_arg))
    elif args and args[0] == "--answer":
        reply = " ".join(args[1:]) if len(args) > 1 else ""
        print(handle_reply(reply))
    else:
        print(show_current())
