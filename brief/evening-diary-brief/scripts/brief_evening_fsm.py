#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вечерний дневник с FSM (чтобы можно было отвечать в любой момент).
Состояние хранится в ~/.hermes/.evening_state.json
"""
import sys, os, json, datetime, subprocess, re
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "skills" / "brief"))
from obsidian_utils import write_note, write_section, commit_all, get_vault_path

STATE_FILE = Path.home() / ".hermes" / ".evening_state.json"
TODAY = None  # будет установлен из --date YYYY-MM-DD

def run_t(*args):
    r = subprocess.run(["t", *args], capture_output=True, text=True, timeout=10)
    return r.stdout.strip()

def parse_tasks_list(output):
    """Парсит вывод `t list --date YYYY-MM-DD` в список {name, priority, id}."""
    tasks = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("📭") or line.startswith("ID") or "───" in line:
            continue
        # Формат: "⏳ 🟡 [23] 22:00 🍲 Приготовить на ужин суп"
        # или:     "⏳ 🟡 [23] Название задачи"
        m = re.match(r'.+\[\s*(\d+)\]\s*(.*)', line)
        if m:
            tasks.append({"name": m.group(2).strip(), "priority": "M", "id": m.group(1)})
    return tasks

def load_data_for_date(date_str):
    output = run_t("list", "--date", date_str)
    return {"today": parse_tasks_list(output)}

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))

def clear_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()

def build_diary(tasks, answers):
    dt = datetime.datetime.strptime(TODAY, "%Y-%m-%d")
    today_str = dt.strftime("%d %B %Y (%A)")
    lines = []
    lines.append("# 📖 Вечерний дневник")
    lines.append(f"**{today_str}**")
    lines.append("")
    lines.append("## 📋 Статусы задач")
    done = 0
    for t in tasks:
        name = t.get("name","?")
        st = answers.get(name, "⏳")
        if st == "✅": done += 1
        lines.append(f"- {st} **{name}**")
    lines.append("")
    lines.append(f"**Итого:** {done}/{len(tasks)} выполнено")
    lines.append("")
    qs = [
        "1. Что сегодня прошло ХОРОШО?",
        "2. Где я облажался / можно лучше?",
        "3. Главный урок / инсайт дня:",
        "4. На что обратить внимание завтра?",
        "5. Deep Work (часы фокуса):",
    ]
    lines.append("## 💭 Ответы")
    for q in qs:
        a = answers.get(q, "_ _")
        lines.append("")
        lines.append(f"**{q}**")
        lines.append(f"  {a}")
    # ── Цели (goals-checkin) ──
    try:
        goals_checkin = subprocess.run(
            ["python3", str(Path.home() / ".hermes" / "skills" / "productivity" / "life-planning" / "scripts" / "planning.py"), "--goals-checkin"],
            capture_output=True, text=True, timeout=10
        )
        if goals_checkin.stdout.strip():
            lines.append("")
            lines.append(f"## 🎯 ПРОВЕРКА ЦЕЛЕЙ")
            lines.append(goals_checkin.stdout.strip())
    except Exception:
        pass
    lines.append("")
    lines.append(f"_Написано: {datetime.datetime.now().strftime('%H:%M МСК')}_")
    return "\n".join(lines)

def start_new():
    data = load_data_for_date(TODAY)
    tasks = data.get("today", [])
    state = {
        "phase": "tasks",
        "task_idx": 0,
        "answers": {},
        "tasks": [t.get("name","?") for t in tasks]
    }
    save_state(state)
    if not state["tasks"]:
        # задач нет — сразу к вопросам
        state["phase"] = "q1"
        save_state(state)
        q = "1. Что сегодня прошло ХОРОШО?"
        print(q)
        return q
    # Первая задача
    tname = state["tasks"][0]
    prio = [t.get("priority","?") for t in tasks if t.get("name")==tname][0]
    q = f'Задача [{prio}] {tname} — статус? (✅ / ⏳ / ❌)'
    print(q)
    return q

def handle_reply(text):
    state = load_state()
    if not state:
        start_new()
        state = load_state()

    text = text.strip()
    if state["phase"] == "tasks":
        cur = state["tasks"][state["task_idx"]]
        state["answers"][cur] = text
        state["task_idx"] += 1
        if state["task_idx"] >= len(state["tasks"]):
            state["phase"] = "q1"
            q = "1. Что сегодня прошло ХОРОШО?"
        else:
            tname = state["tasks"][state["task_idx"]]
            tasks_raw = load_data_for_date(TODAY).get("today", [])
            prio = [t.get("priority","?") for t in tasks_raw if t.get("name")==tname][0]
            q = f'Задача [{prio}] {tname} — статус? (✅ / ⏳ / ❌)'
        save_state(state)
        return q

    elif state["phase"].startswith("q"):
        idx = int(state["phase"][1])
        qs = [
            "1. Что сегодня прошло ХОРОШО?",
            "2. Где я облажался / можно лучше?",
            "3. Главный урок / инсайт дня:",
            "4. На что обратить внимание завтра?",
            "5. Deep Work (часы фокуса):",
        ]
        state["answers"][qs[idx-1]] = text
        if idx >= 5:
            tasks = load_data_for_date(TODAY).get("today", [])
            diary = build_diary(tasks, state["answers"])
            write_section(f"Дневник/{TODAY}.md", "# 📖 Вечерний дневник", diary)
            commit_all(f"diary {TODAY}")
            out = get_vault_path() / "Дневник" / f"{TODAY}.md"
            clear_state()
            result = f"\n{'='*60}\n{diary}\n{'='*60}\n\n✅ Дневник сохранён: {out}"
            return result
        else:
            state["phase"] = f"q{idx+1}"
            save_state(state)
            return qs[idx]

    return "Продолжаем..."

# CLI interface
if __name__ == "__main__":
    # Парсим --date YYYY-MM-DD (если есть)
    date_arg = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--date" and i+1 < len(args):
            date_arg = args[i+1]
            # убираем --date и значение из списка
            args = args[:i] + args[i+2:]
            break
    if date_arg:
        TODAY = date_arg
    else:
        TODAY = datetime.date.today().isoformat()

    if len(args) > 0 and args[0] == "--start":
        start_new()
    elif len(args) > 0 and args[0] == "--answer":
        reply = " ".join(args[1:])
        print(handle_reply(reply))
    else:
        if load_state():
            s = load_state()
            if s["phase"] == "tasks":
                t = s["tasks"][s["task_idx"]]
                tasks = load_data_for_date(TODAY).get("today", [])
                prio = [x.get("priority","?") for x in tasks if x.get("name")==t][0]
                print(f'Жду ответ на: [{prio}] {t} (✅/⏳/❌)')
            else:
                idx = int(s["phase"][1])
                qs = ["1. Что сегодня прошло ХОРОШО?", "2. Где я облажался / можно лучше?",
                      "3. Главный урок / инсайт дня:", "4. На что обратить внимание завтра?",
                      "5. Deep Work (часы фокуса):"]
                print(f'Жду ответ на: {qs[idx-1]}')
        else:
            start_new()
