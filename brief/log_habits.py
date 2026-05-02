#!/usr/bin/env python3
"""Парсит `t habits` и сохраняет форматированный лог в Привычки/YYYY-MM-DD.md."""

import datetime, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes" / "skills" / "brief"))
from obsidian_utils import write_note, commit_all


def parse_habits():
    """Запускает t habits и возвращает (done_list, pending_list, total, done_count)."""
    result = subprocess.run(["t", "habits"], capture_output=True, text=True, timeout=15)
    output = result.stdout.strip()

    done_list = []
    pending_list = []
    total = 0
    done_count = 0

    for line in output.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Итого:"):
            # Парсим "Итого: 2/9"
            parts = stripped.split()
            if len(parts) >= 2 and "/" in parts[1]:
                counts = parts[1].split("/")
                done_count = int(counts[0])
                total = int(counts[1])
            continue

        if not stripped:
            continue

        # Определяем статус по первому символу
        if stripped.startswith("✅"):
            status = "done"
        elif stripped.startswith("⏳"):
            status = "pending"
        elif stripped.startswith("❌"):
            status = "cancelled"
        else:
            continue

        # Извлекаем название после "] "
        # Формат: "✅ [ 3] Вакуум 08:00"
        if "] " in stripped:
            name = stripped.split("] ", 1)[1].strip()
        else:
            name = stripped[2:].strip()

        if status == "done":
            done_list.append(name)
        else:
            pending_list.append(name)

    return done_list, pending_list, total, done_count


def format_habits_md(done_list, pending_list, total, done_count):
    """Форматирует лог привычек в markdown."""
    today = datetime.date.today().isoformat()
    pending_count = total - done_count

    lines = [f"# 🔁 Привычки — {today}", ""]

    # Выполненные
    lines.append(f"## ✅ Выполнено ({done_count}/{total})")
    if done_list:
        for name in done_list:
            lines.append(f"- [x] {name}")
    else:
        lines.append("- _нет_")
    lines.append("")

    # Не выполненные
    lines.append(f"## ⏳ Не выполнено ({pending_count}/{total})")
    if pending_list:
        for name in pending_list:
            lines.append(f"- [ ] {name}")
    else:
        lines.append("- _нет_")

    return "\n".join(lines)


def main():
    done_list, pending_list, total, done_count = parse_habits()
    today = datetime.date.today().isoformat()
    content = format_habits_md(done_list, pending_list, total, done_count)

    write_note(f"Привычки/{today}.md", content)
    commit_all(f"habits {today}")

    # Печатаем краткий итог
    print(f"🔁 Привычки: {done_count}/{total} выполнено")
    return 0


if __name__ == "__main__":
    sys.exit(main())
