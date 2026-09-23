---
name: mytasks
category: productivity
description: Показывает список задач из personal-task-tracker по команде /mytasks
---

# Tasks Summary

Выводит активные задачи из personal-task-tracker (SQLite).

## Запуск

```bash
python3 ~/.hermes/skills/productivity/tasks-summary/scripts/tasks_summary.py
```

## Формат вывода

```
📋 Задачи:
1. Название задачи
2. Название задачи
...
```

Если задач нет — выводит "✅ Все задачи выполнены".