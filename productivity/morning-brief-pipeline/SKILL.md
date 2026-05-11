---
name: morning-brief-pipeline
category: productivity
description: Утренний бриф — разбивка на чанки, умное сокращение ссылок, fallback на plain text. Отправка в Telegram по расписанию.
requires: [personal-task-tracker, task_display]
---

# Morning Brief Pipeline (обновлён 08.05.2026)

Создаёт утренний бриф и отправляет его в Telegram по расписанию. Сообщения разбиваются на чанки ≤2500 символов. Ссылки сокращаются только >100 символов. Английские новости переводятся на русский.

## Структура

```
~/.hermes/
└── skills/productivity/morning-brief-pipeline/
    └── scripts/
        └── brief/
            ├── __init__.py       # generate_brief(), chunking, simplify_links()
            ├── weather.py        # get_weather()
            ├── infra.py          # get_infra_status()
            ├── tasks.py          # get_one_big_thing() — использует task_display.py
            ├── news.py           # get_all_signals()
            ├── gmail.py          # get_gmail_inbox()
            ├── calendar.py       # get_calendar()
            └── habits.py         # get_workspace_tasks(), get_personal_and_habits(), get_backlog() — фильтрует ✅ строки
```

**Выполненные задачи скрыты** (08.05.2026): `tasks.py` и `habits.py` фильтруют строки с ✅ через условие `not l.startswith("✅")`.

**Формат задач:** единый, через `~/.hermes/scripts/task_display.py`. Не сырой `t list`.

## Быстрый запуск

```bash
cd ~/.hermes/skills/productivity/morning-brief-pipeline/scripts && python3 -c "from brief import generate_brief; generate_brief()"
```

## Архитектура отправки

Бриф собирается, разбивается на чанки и отправляется:

1. Заголовок — дата
2. Статус системы + Погода + Главная задача
3. Почта
4. Календарь
5. **Задачи + Личное + Привычки** (✅ отфильтрованы, единый формат)
6. Бэклог
7. Футер

## Pitfalls

1. **Telegram лимит** — чанки ≤2500 + fallback plain text.
2. **Markdown errors** — кириллица. При ошибке — повтор без parse_mode.
3. **Длинные URL** — `simplify_links()` оставляет домен для URL >100 символов.
4. **Дубли заголовков** — gmail и calendar уже содержат свои заголовки.
5. **Аномальная погода** — снег при плюсе. TODO.
6. **✅ фильтр хрупкий** — `not l.startswith("✅")` в tasks.py/habits.py. Если формат `t list` изменится — сломается.

## Что сделано

- [x] Новости в отдельный дайджест (27.04)
- [x] Перевод новостей на русский
- [x] Задачи на SQLite (29.04)
- [x] Периодические задачи в брифе (30.04)
- [x] **Скрытие ✅ задач** (08.05 — фильтр в habits.py/tasks.py)
- [ ] Фильтр погодных аномалий
- [ ] Retry-логика Telegram
