---
name: brief-calendar
category: brief
description: Календарь на сегодня — через google_api.py
---

# Календарь на сегодня

Вызывает `~/.hermes/scripts/brief/calendar.py` → `get_calendar()`

## Использование
```python
from hermes_tools import terminal
result = terminal(
    command="cd ~/.hermes/scripts/brief && python3 calendar.py",
    timeout=30
)
```

## Вывод
Список событий со временем и ссылками.

## Пример
```
📅 **Календарь:**
  • 🕒 10:00 — [Встреча по проекту](...)
```