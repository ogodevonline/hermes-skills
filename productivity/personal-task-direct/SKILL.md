---
name: Personal Task Direct
description: Управление задачами напрямую (без LLM)
---

# Personal Task Direct

Команды для управления задачами без использования LLM.

## ⚠️ deprecated: personal-task-manager
**`personal-task-manager` (LLM-based) — удалён.** Не используйте. Для системных cronjobs см. skill `task_manager`.

## Команды

### добавить сегодня [задача]
Добавить задачу в секцию `today` в tasks.yml:
```python
from hermes_tools import read_file, patch, terminal

# 1. Прочитать tasks.yml
# 2. Добавить задачу в today:[]
# 3. Сохранить
# 4. Запустить tasks_reminder.py если нужно
```

### добавить привычку [название] время [время]
Добавить привычку в секцию `habits`:
```python
# Добавить в habits:[]
```

### выполнено [номер]
Удалить задачу из today по номеру и добавить в архив.

## Скрипты

- `tasks_reminder.py` — отправляет задачи в Telegram (18:00)
- `habits_reminder.py` — отправляет привычки (08:00, 22:00)
- `dinner_reminder.py` — напоминание про ужин (17:30)
- `study_reminder.py` — английский/python (09:00, 14:00, 18:00)

## Редактирование tasks.yml

Использовать patch() для edits:
```python
# Добавить задачу
old_string = "today:\n  -"
new_string = "today:\n  - name: \"Новая задача\"\n    priority: M\n  -\n  -"
```

## CRITICAL

НЕ использовать LLM для этих операций! Прямое редактирование YAML файла + запуск скриптов.