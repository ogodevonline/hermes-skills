---
name: brief-habits
category: brief
description: Работа с habits.yml — личные задачи и привычки
---

# Привычки и личные задачи

Вызывает `~/.hermes/scripts/brief/habits.py` → `get_personal_and_habits()`

## Использование
```python
from hermes_tools import terminal
result = terminal(
    command="cd ~/.hermes/scripts/brief && python3 habits.py",
    timeout=15
)
```

## Вывод
- Личные задачи с приоритетами (отфильтрованно по PERSONAL_KEYWORDS)
- Привычки из habits.yml группированные по времени

## Пример
```
🏠 **Личное — 2 дела:**
  🟢 Сойти в зал
  🟡 Купить лампочки

✅ **Привычки:**
  🕐 08:00
    ☐ Omega + D3
    ☐ Дыхание по Вим Хофу
    ☐ Вакуум
  🕐 09:00
    ☐ Английский или Python
```