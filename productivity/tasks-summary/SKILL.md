---
name: mytasks
category: productivity
description: Показывает список активных задач из Google Tasks по команде /mytasks
---

# Tasks Summary

Выводит активные (открытые) задачи из **Google Tasks** — списки `⛅ TODAY` и
`📥 BACKLOG`. Источник истины для задач с 06.10.2026 (локальная `tasks.db`
больше не используется).

Читает через `skills/productivity/google-workspace/scripts/tasks_api.py`
(`get_service()`, OAuth уже настроен — свой не пишем).

## Запуск

```bash
python3 ~/.hermes/skills/productivity/tasks-summary/scripts/tasks_summary.py
```

## Формат вывода

```
📋 Задачи:
1. 🔴 Срочная задача (❗ в заголовке Google = High)
2. Обычная задача дня
3. 📥 Задача из BACKLOG
...
```

- `🔴` — задача High (в Google заголовок начинается с `❗`);
- `📥` — задача из списка BACKLOG;
- без префикса — открытая задача из списка TODAY.

Если открытых задач нет — выводит `✅ Все задачи выполнены`.
