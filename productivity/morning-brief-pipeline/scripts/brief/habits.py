"""Привычки и задачи — из SQLite через t list / t habits"""
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
        return ""


def _count_tasks(status_output: str) -> int:
    """Извлечь количество задач из t status"""
    import re
    m = re.search(r'(\d+)\s+задач', status_output)
    return int(m.group(1)) if m else 0


def get_workspace_tasks() -> str:
    """Задачи на сегодня из SQLite (все, без разделения на личные/рабочие)"""
    raw = _run_t("list")
    if not raw:
        return "💻 Задачи: пусто"

    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    status = _run_t("status")
    count = _count_tasks(status)

    if not lines:
        return "💻 Задачи: пусто"

    result = [f"💻 Задачи — {count} шт.:"]
    for line in lines:
        result.append(f"  {line}")
    return "\n".join(result)


def get_backlog() -> str:
    """Бэклог — отложенные/будущие задачи."""
    raw = _run_t("list", "--backlog")
    if not raw or "Нет" in raw:
        return ""
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    if not lines:
        return ""
    result = ["📦 **Бэклог:**"]
    for line in lines:
        result.append(f"  {line}")
    return "\n".join(result)


def get_periodic() -> str:
    """Периодические задачи (напоминания)."""
    raw = _run_t("periodic")
    if not raw or "Нет" in raw:
        return ""
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    if not lines:
        return ""
    result = ["🔄 Периодические напоминания:"]
    for line in lines:
        result.append(f"  {line}")
    return "\n".join(result)


def get_personal_and_habits() -> str:
    """Личные дела и привычки"""
    parts = []

    # Привычки
    habits_raw = _run_t("habits")
    if habits_raw and "Итого" in habits_raw:
        habits_lines = habits_raw.split("\n")
        # Отделяем заголовок от итога
        header_lines = [l.strip() for l in habits_lines if l.strip() and "Итого" not in l]
        total_line = [l.strip() for l in habits_lines if "Итого" in l]
        if header_lines:
            parts.append("✅ Привычки:")
            for line in header_lines:
                parts.append(f"  {line}")
            if total_line:
                parts.append(f"  *{total_line[0]}*")

    # Периодические напоминания
    periodic = get_periodic()
    if periodic:
        parts.append("")
        parts.append(periodic)

    return "\n".join(parts) if parts else "Нет задач и привычек"


def get_habits() -> str:
    """Только привычки"""
    raw = _run_t("habits")
    if not raw or "Итого" not in raw:
        return ""

    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    # Убираем строку итога, оставляем только привычки
    habit_lines = [l for l in lines if "Итого" not in l]
    if not habit_lines:
        return ""

    result = ["✅ Привычки:"]
    for line in habit_lines:
        result.append(f"  {line}")
    return "\n".join(result)


if __name__ == "__main__":
    print("=== Задачи ===")
    print(get_workspace_tasks())
    print()
    print("=== Личное и привычки ===")
    print(get_personal_and_habits())
