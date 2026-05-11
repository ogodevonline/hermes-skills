"""Задачи — из SQLite через task_display.py формат"""
import subprocess
import os

HERMES_HOME = os.path.expanduser("~/.hermes")
T_BIN = os.path.expanduser("~/.local/bin/t")
DISPLAY = os.path.expanduser("~/.hermes/scripts/task_display.py")


def _run_t(*args: str) -> str:
    cmd = [T_BIN, *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def get_one_big_thing() -> str:
    """Вернуть самую приоритетную задачу на сегодня"""
    raw = _run_t("list")
    if not raw:
        return "Нет активных задач"
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    lines = [l for l in lines if not l.startswith("✅")]
    if not lines:
        return "✅ Всё сделано!"
    for icon in ["🔴", "🟡", "🟢"]:
        for line in lines:
            if icon in line:
                parts = line.split("] ", 1)
                if len(parts) == 2:
                    return parts[1]
    parts = lines[0].split("] ", 1)
    return parts[1] if len(parts) == 2 else lines[0]


def get_all_today_tasks() -> str:
    """Вернуть все задачи на сегодня в едином формате task_display.py"""
    try:
        r = subprocess.run(
            ["python3", DISPLAY],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip() or "Нет задач"
    except Exception:
        return "Нет задач"


if __name__ == "__main__":
    print("Главная задача:", get_one_big_thing())
    print()
    print(get_all_today_tasks())