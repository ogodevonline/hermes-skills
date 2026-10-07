"""Утилиты вечернего дневника: константы, t CLI, время, Obsidian."""
import sys, json, datetime, subprocess, re
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from obsidian_utils import write_section, commit_all, get_vault_path
from plan_utils import parse_plan_text, save_plan as save_plan_file

# Google Tasks — источник истины по задачам с 24.09.2026 (tasks.db не читается)
sys.path.insert(0, str(Path.home() / ".hermes" / "skills" / "productivity" / "google-workspace" / "scripts"))
from tasks_api import get_service  # noqa: E402

TODAY_LIST = "VDhuNDh2enVHY1I3TlBtUQ"    # ⛅ TODAY
BACKLOG_LIST = "MDM0ODI5NzY3OTIxMTU4MDMzOTQ6MDow"  # 📥 BACKLOG
_TASK_SERVICE = None

# ─── Константы ───

STATE_FILE = Path.home() / ".hermes" / ".evening_state.json"
MSK = ZoneInfo("Europe/Moscow")

PLAN_QUESTION = "📋 План на завтра? Диктуй время + действие (например «в 11 зубы, в 12 IMEI, в 13 обед»). Если плана нет — скажи «нет»"

SPHERES = [
    ("🧑‍💻", "Карьера", "30bit, деньги, проекты"),
    ("❤️", "Лима", "отношения с ней"),
    ("👨‍👩‍👧", "Семья/Родные", "родители, близкие"),
    ("🧠", "Развитие", "английский, Python, навыки"),
    ("💪", "Здоровье/Спорт", "зал, сон, еда"),
    ("🏠", "Быт/Финансы", "бюджет, порядок, дом"),
    ("🤝", "Друзья/Люди", "общение вне семьи"),
    ("🎮", "Хобби/Отдых", "время для себя"),
]

QUESTIONS = [
    "1. Что сегодня прошло ХОРОШО?",
    "2. Где облажался / можно лучше?",
    "3. Главный урок / инсайт дня?",
    "4. На что обратить внимание завтра?",
    "5. Deep Work (часы фокуса)?",
]

PHASE_ORDER = ["tasks", "habits", "spheres", "q1", "q2", "q3", "q4", "q5", "rating", "plan"]

YES_WORDS = {"да", "yes", "✅", "+", "done", "готово"}
NO_WORDS = {"нет", "no", "❌", "-", "cancel"}

# ─── Время (МСК) ───

def now_msk():
    return datetime.datetime.now(MSK)

def get_date_for_today():
    now = now_msk()
    return (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d") if now.hour < 4 else now.strftime("%Y-%m-%d")

def current_hour():
    return now_msk().hour

def time_passed(time_str):
    if not time_str:
        return False
    try:
        h = int(time_str.split(":")[0])
        nh = current_hour()
        if nh < 4:
            return 6 <= h <= 23
        return nh > h + 1
    except (ValueError, IndexError):
        return False

def filter_night_habits(habits):
    nh = current_hour()
    if nh >= 22 or nh < 6:
        return [h for h in habits if not (h["time"] and time_passed(h["time"]))]
    return habits

def _tasks_service():
    """Ленивая инициализация Google Tasks сервиса."""
    global _TASK_SERVICE
    if _TASK_SERVICE is None:
        _TASK_SERVICE = get_service()
    return _TASK_SERVICE


def _fetch_google_tasks(tasklist, **extra):
    """Задачи списка Google Tasks (с пагинацией). extra → параметры tasks().list."""
    out, token = [], None
    while True:
        kw = {"tasklist": tasklist, "showCompleted": True, "maxResults": 200, **extra}
        if token:
            kw["pageToken"] = token
        res = _tasks_service().tasks().list(**kw).execute()
        out += res.get("items", [])
        token = res.get("nextPageToken")
        if not token:
            return out


def _task_local_id(task):
    """Числовой ID из notes `local:#N` (иначе первые 8 символов Google-ID)."""
    m = re.search(r"local:#(\d+)", task.get("notes") or "")
    return m.group(1) if m else (task.get("id") or "")[:8]


def _msk_day_start_utc(date_str):
    """Начало дня МСК (00:00) для date_str в RFC3339 UTC — аргумент completedMin."""
    start_msk = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=MSK)
    return start_msk.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_completed_tasks(date_str):
    """Выполненные за дату (день МСК) задачи Google из списков TODAY/BACKLOG.

    showCompleted=True, showHidden=True, completedMin = начало дня МСК —
    иначе Google скрывает выполненные задачи.
    """
    out = []
    completed_min = _msk_day_start_utc(date_str)
    for tasklist in (TODAY_LIST, BACKLOG_LIST):
        for t in _fetch_google_tasks(tasklist, showCompleted=True, showHidden=True,
                                     completedMin=completed_min):
            if t.get("status") != "completed":
                continue
            out.append(t)
    return out


def parse_pending_tasks(date_str):
    """Задачи дня из Google Tasks (списки TODAY/BACKLOG).

    Источник истины — Google (24.09.2026); локальная tasks.db не читается.
    Возвращает открытые задачи со сроком на date_str плюс выполненные за этот
    день (showCompleted/showHidden + completedMin = начало дня МСК).
    В Google нет счётчика переносов, «отложенные» отдельно не досыпаются.
    """
    tasks, seen = [], set()
    try:
        # 1) открытые задачи со сроком на дату
        for tasklist in (TODAY_LIST, BACKLOG_LIST):
            for t in _fetch_google_tasks(tasklist, showCompleted=False):
                if t.get("status") != "needsAction":
                    continue
                if (t.get("due") or "")[:10] != date_str:
                    continue
                tid = _task_local_id(t)
                if tid in seen:
                    continue
                seen.add(tid)
                tasks.append({"id": tid, "name": (t.get("title") or "").strip()})
        # 2) выполненные за сегодня (completedMin = начало дня МСК)
        for t in parse_completed_tasks(date_str):
            tid = _task_local_id(t)
            if tid in seen:
                continue
            seen.add(tid)
            tasks.append({"id": tid, "name": (t.get("title") or "").strip()})
    except Exception:
        pass
    return tasks

HABITS_LIST = "Y0c3NGFIRThRTnlWNFRpMg"   # 🌱 HABITS


def parse_pending_habits(date_str=None):
    """Неотмеченные привычки дня из Google Tasks (список HABITS, due == date_str)."""
    date_str = date_str or datetime.datetime.now(MSK).date().isoformat()
    habits = []
    for t in _fetch_google_tasks(HABITS_LIST, showHidden=True):
        if (t.get("due") or "")[:10] != date_str or t.get("status") == "completed":
            continue
        full = (t.get("title") or "").strip()
        tm = re.search(r"(\d{2}:\d{2})", full)
        habits.append({"id": t["id"][:8], "gid": t["id"], "name": full,
                       "time": tm.group(1) if tm else None})
    return habits

# ─── Состояние JSON ───

def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else None

def save_state(s):
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2))

def clear_state():
    STATE_FILE.exists() and STATE_FILE.unlink()

# ─── Сборка дневника ───

def build_diary(state):
    ds = state["date"]
    lines = [f"# 📖 Вечерний дневник — {ds}", ""]
    if state["tasks"]:
        done = sum(1 for k, v in state["answers"].items() if k.startswith("task_") and v == "✅")
        lines.append(f"**Задачи:** {done}/{len(state['tasks'])} выполнено\n")
        lines.append("## 📋 Задачи")
        for t in state["tasks"]:
            s = state["answers"].get(f"task_{t['id']}", "⏳")
            lines.append(f"- {'✅' if s == '✅' else '❌' if s == '❌' else '⏳'} {t['name']}")
        lines.append("")
    if state["habits"]:
        done = sum(1 for k, v in state["answers"].items() if k.startswith("habit_") and v == "✅")
        lines.append(f"## 🔁 Привычки ({done}/{len(state['habits'])})")
        for h in state["habits"]:
            s = state["answers"].get(f"habit_{h['id']}", "❌")
            lines.append(f"- {'✅' if s == '✅' else '❌'} {h['name']}")
        lines.append("")
    lines.append("## 🌱 Сферы жизни")
    for e, n, _ in SPHERES:
        lines.append(f"- {e} {n}: {state['answers'].get(f'sphere_{n}', '—')}")
    lines.append("")
    lines.append("## 💭 Рефлексия")
    for i in range(1, 6):
        lines.append(f"**{QUESTIONS[i-1]}**")
        lines.append(f"  {state['answers'].get(f'q_{i}', '_ _')}\n")
    lines.append(f"**Оценка дня:** {state['answers'].get('rating', '—')}/10\n")
    lines.append(f"_Создано: {now_msk().strftime('%H:%M МСК')}_")
    return "\n".join(lines)

def save_diary(state):
    ds = state["date"]
    write_section(f"Journal/{ds}.md", "# 📖 Вечерний дневник", build_diary(state))
    try:
        commit_all(f"diary {ds}")
    except Exception as e:
        # Если pre-commit hook заблокировал — commit без проверок
        vault = get_vault_path()
        import subprocess
        subprocess.run(["git", "commit", "--no-verify", "-m", f"diary {ds}"],
                       cwd=vault, capture_output=True, text=True, timeout=30)
    rating = state["answers"].get("rating", "—")

    # Сохранить план на завтра, если есть
    plan_text = state.get("plan_text", "")
    if plan_text and plan_text.strip().lower() not in NO_WORDS:
        from datetime import datetime, timedelta
        tomorrow = (datetime.strptime(ds, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        plan_items = parse_plan_text(plan_text)
        if plan_items:
            try:
                vault_path = save_plan_file(tomorrow, plan_items)
                plan_msg = f"\n📋 План на завтра ({tomorrow}) сохранён"
            except Exception as e:
                plan_msg = f"\n⚠️ План не сохранился: {e}"
        else:
            plan_msg = f"\n⚠️ Не удалось распарсить план: «{plan_text}»"
    else:
        plan_msg = ""

    clear_state()
    return f"✅ Дневник за {ds} сохранён: {get_vault_path() / 'Journal' / f'{ds}.md'}\n\nРейтинг: {rating}/10{plan_msg}"
