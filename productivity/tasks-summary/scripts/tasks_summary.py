#!/usr/bin/env python3
"""Вывод активных задач из personal-task-tracker (SQLite)."""
import sqlite3, os
from datetime import datetime, date

DB = os.path.expanduser("~/.hermes/tasks/tasks.db")

def main():
    if not os.path.exists(DB):
        print("❌ База задач не найдена")
        return

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Активные: pending или те, что на сегодня
    today = date.today().isoformat()
    cur.execute("""
        SELECT id, name, priority, status, due_date
        FROM tasks
        WHERE status IN ('pending')
        ORDER BY
            CASE priority WHEN 'H' THEN 0 WHEN 'M' THEN 1 WHEN 'L' THEN 2 ELSE 3 END,
            due_date NULLS LAST,
            id
    """)
    tasks = cur.fetchall()
    conn.close()

    if not tasks:
        print("✅ Все задачи выполнены")
        return

    print("📋 **Задачи:**")
    for i, (tid, name, priority, status, due_date) in enumerate(tasks, 1):
        pfx = {'H':'🔴','M':'🟡','L':'🟢'}.get(priority, '')
        line = name.strip()
        # убираем префикс [H][M][L] если есть
        if line.startswith('[H]') or line.startswith('[M]') or line.startswith('[L]'):
            line = line[3:].strip()
        print(f"{i}. {pfx} {line}")

if __name__ == '__main__':
    main()