---
name: osint-planning
category: productivity
description: Персональный планировщик — стратегия (квартал) → тактика (по дням) → оперативка (ежедневные ритуалы). Тянет задачи из t list и привычки.
---

# Personal Planning

Персональный планировщик жизни Василия. Строит план на неделю/месяц/квартал,
подтягивая реальные задачи из `t list` и привычки из `t habits`.

## Запуск

```bash
cd ~/.hermes/skills/productivity/osint-planning/scripts

# Неделя (по умолчанию)
python3 planning.py

# Месяц
python3 planning.py --period month

# Квартал
python3 planning.py --period quarter

# От指定 даты
python3 planning.py --period week --now "2026-06-01"
```

## Что делает

1. **Стратегия** — статистика задач, приоритеты на период, фокусы
2. **Тактика** — разбивка по дням с чек-пойнтами
3. **Оперативка** — ритуалы: утро (brief) → день (Deep Work) → вечер (diary)
4. **Ритуалы** — воскресное ревью, план на следующий период

## Интеграция с task-manager

Уже в cron (воскресенье 20:00 МСК): `0 18 * * 0` → `planning.py`

## Зависимости
- CLI `t` (personal-task-tracker)
- Python 3
