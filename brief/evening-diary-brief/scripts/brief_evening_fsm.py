#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вечерний дневник с FSM (чтобы можно было отвечать в любой момент).
Состояние хранится в ~/.hermes/.evening_state.json
"""
import sys, os, json, yaml, datetime
from pathlib import Path

sys.path.insert(0, '/home/hermes/.hermes/scripts')
sys.path.insert(0, str(Path.home() / ".hermes" / "skills" / "brief"))
import importlib.util
spec = importlib.util.spec_from_file_location("brief_mod", "/home/hermes/.hermes/scripts/brief/__init__.py")
brief_mod = importlib.util.module_from_spec(spec)
sys.modules["brief_mod"] = brief_mod
spec.loader.exec_module(brief_mod)

STATE_FILE = Path.home() / ".hermes" / ".evening_state.json"
DATA_FILE  = Path.home() / ".hermes" / "tasks" / "tasks.yml"

def load_data():
    with open(DATA_FILE) as f:
        return yaml.safe_load(f) or {}

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
    today = datetime.date.today().strftime("%d %B %Y (%A)")
    lines = []
    lines.append("# 📖 Вечерний дневник")
    lines.append(f"**{today}**\n")
    lines.append("## 📋 Статусы задач")
    done = 0
    for t in tasks:
        name = t.get("name","?")
        st = answers.get(name, "⏳")
        if st == "✅": done += 1
        lines.append(f"- {st} **{name}**")
    lines.append(f"\n**Итого:** {done}/{len(tasks)} выполнено\n")
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
        lines.append(f"\n**{q}**  \n  {a}")
    tom = load_data().get("tomorrow", [])
    if tom:
        lines.append("\n## 📅 Завтра")
        for t in tom:
            lines.append(f"- {t.get('name','')}")
    lines.append(f"\n_Написано: {datetime.datetime.now().strftime('%H:%M МСК')}_")
    return "\n".join(lines)

def start_new():
    data = load_data()
    tasks = data.get("today", [])
    state = {
        "phase": "tasks",
        "task_idx": 0,
        "answers": {},
        "tasks": [t.get("name","?") for t in tasks]
    }
    save_state(state)
    # Первый вопрос
    tname = state["tasks"][0]
    prio = [t.get("priority","?") for t in tasks if t.get("name")==tname][0]
    q = f'Задача [{prio}] {tname} — статус? (✅ / ⏳ / ❌)'
    print(q)
    return q

def handle_reply(text):
    state = load_state()
    if not state:
        # Никого не ждём — запускаем сначала автоматом
        start_new()
        state = load_state()

    text = text.strip()
    if state["phase"] == "tasks":
        # сохраняем ответ на текущую задачу
        cur = state["tasks"][state["task_idx"]]
        state["answers"][cur] = text
        state["task_idx"] += 1
        if state["task_idx"] >= len(state["tasks"]):
            # задачи кончились → переходим к вопросам
            state["phase"] = "q1"
            q = "1. Что сегодня прошло ХОРОШО?"
        else:
            # следующая задача
            tname = state["tasks"][state["task_idx"]]
            tasks_raw = load_data().get("today", [])
            prio = [t.get("priority","?") for t in tasks_raw if t.get("name")==tname][0]
            q = f'Задача [{prio}] {tname} — статус? (✅ / ⏳ / ❌)'
        save_state(state)
        return q

    elif state["phase"].startswith("q"):
        # вопрос
        idx = int(state["phase"][1])
        state["answers"][f"{idx}. ..."] = text  # просто сохраняем номер
        # правильный ключ — длинный вопрос
        qs = [
            "1. Что сегодня прошло ХОРОШО?",
            "2. Где я облажался / можно лучше?",
            "3. Главный урок / инсайт дня:",
            "4. На что обратить внимание завтра?",
            "5. Deep Work (часы фокуса):",
        ]
        state["answers"][qs[idx-1]] = text
        if idx >= 5:
            # всё, строим дневник
            tasks = load_data().get("today", [])
            diary = build_diary(tasks, state["answers"])
            from obsidian_utils import save_note, get_vault_path
            today = datetime.date.today().isoformat()
            save_note(f"Дневник/{today}.md", diary)
            out = get_vault_path() / "Дневник" / f"{today}.md"
            clear_state()
            result = f"\n{'='*60}\n{diary}\n{'='*60}\n\n✅ Дневник сохранён: {out}"
            return result
        else:
            state["phase"] = f"q{idx+1}"
            save_state(state)
            return qs[idx]  # следующий вопрос

    return "Продолжаем..."

# CLI interface
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--start":
        start_new()
    elif len(sys.argv) > 1 and sys.argv[1] == "--answer":
        reply = " ".join(sys.argv[2:])
        print(handle_reply(reply))
    else:
        # Без аргументов — если стейт есть, показываем что ждём, если нет — запускаем
        if load_state():
            s = load_state()
            if s["phase"] == "tasks":
                t = s["tasks"][s["task_idx"]]
                tasks = load_data().get("today", [])
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
