"""Задачи — из SQLite через t status / t list"""
import subprocess
import os

HERMES_HOME = os.path.expanduser("~/.hermes")
T_BIN = os.path.expanduser("~/.local/bin/t")


def _run_t(*args: str) -> str:
    """Запустить t и вернуть stdout"""
    cmd = [T_BIN, *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception as e:
        return f""


def get_one_big_thing() -> str:
    """Вернуть самую приоритетную задачу на сегодня из SQLite"""
    raw = _run_t("list")
    if not raw:
        return "Нет активных задач"
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    if not lines:
        return "Нет активных задач"
    # Приоритет: 🔴 (H) > 🟡 (M) > 🟢 (L)
    for icon in ["🔴", "🟡", "🟢"]:
        for line in lines:
            if icon in line:
                # Вытаскиваем название: ⏳ 🔴 [ 1] Название задачи
                parts = line.split("] ", 1)
                if len(parts) == 2:
                    return parts[1]
    # Если нет иконок — первая строка
    parts = lines[0].split("] ", 1)
    return parts[1] if len(parts) == 2 else lines[0]


def get_all_today_tasks() -> str:
    """Вернуть все задачи на сегодня как строку"""
    raw = _run_t("list")
    return raw or "Нет задач"


if __name__ == "__main__":
    print("Главная задача:", get_one_big_thing())
