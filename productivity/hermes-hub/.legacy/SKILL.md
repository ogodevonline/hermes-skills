---
name: hermes-hub
category: productivity
description: Единая сводка задач, целей, сфер и проблем. Запуск — `hermes-hub` в CLI, `/hub` в чате.
---

# Hermes Hub

Единый пульт управления системой Василия.

**CLI:** `hermes-hub`
**Чат:** команда `/hub`

## Архитектура

Скрипт: `~/.local/bin/hermes-hub` (Python 3, исполняемый).

Собирает данные из 3 источников через функции-блоки:

```
hermes-hub
├── get_tasks_block()   → вызывает ~/.hermes/scripts/task_display.py (subprocess)
├── get_stats()         → читает напрямую ~/.hermes/tasks/tasks.db (SQLite)
├── get_goals()         → читает ~/.hermes/life/goals.yaml (PyYAML)
│                         + cross-check с tasks.db (goal_id column)
├── get_spheres()       → вызывает ~/.hermes/skills/productivity/life-planning/scripts/planning.py --json (subprocess)
└── get_eternal()       → читает tasks.db (carry_over >= 5)
```

### Пути зависимостей (жёстко зашиты в скрипте)

| Переменная | Путь |
|---|---|
| DB | `~/.hermes/tasks/tasks.db` |
| GOALS | `~/.hermes/life/goals.yaml` |
| PLANNING | `~/.hermes/skills/productivity/life-planning/scripts/planning.py` |
| TASK_DISPLAY | `~/.hermes/scripts/task_display.py` |

## Источники данных

### tasks.db (SQLite)

Таблица `tasks`. Используемые колонки:
- `id`, `name`, `priority` (H/M/L), `category`, `due_date`, `status`
- `carry_over` — счётчик переносов (вечные хвосты >= 5)
- `goal_id` — привязка к цели из goals.yaml
- `project` — проект (иконки: 30bit=💼, english=📚, health=💪, finance=💰, lima=❤️)
- `duration` — длительность (показывается как ⏱)

Запросы:
- Сегодняшние pending — `due_date = today AND status = 'pending'`
- Просрочки — `due_date < today AND status = 'pending'`
- Все pending по проектам — GROUP BY project

### goals.yaml

Формат:
```yaml
goals:
  - id: "goal-id"
    title: "Название цели"
    status: active  # или archived
```
Цели без связанных pending-задач помечаются как ⚠️.

### planning.py --json

Читает дневники Obsidian (`~/hermes-vault/Дневник/`) за неделю.
Возвращает JSON с ключом `sphere_summary` — dict вида:
```json
{
  "Здоровье": {"scores": [7, 6], "avg": 6.5, "comments": [...]},
  "Спорт": {"scores": [5], "avg": 5.0, "comments": []}
}
```

**Известное расхождение:** hermes-hub ожидает ключ `sphere_trends` (список с полями name/emoji/avg/direction), но planning.py выдаёт `sphere_summary` (dict). Из-за этого блок сфер всегда показывает "📈  0 сфер" — данные не разбираются. Задача: согласовать формат (либо planning.py добавить sphere_trends, либо hermes-hub переключить на sphere_summary).

При отсутствии дневниковых записей за неделю sphere_summary будет пустым — это нормально, не ошибка.

### task_display.py

Форматирует задачи на сегодня и просрочки в единый вид. Показывает задачи с `due_date <= today AND status = 'pending'`, группирует по приоритету (H/M/L).

## Вывод

```
📊  HERMES HUB  ·  2026-05-27

📋  6 задач  ([H] 4 · [M] 2)
    💰finance:2  📁без проекта:14

**H**
- `93` 💰 Название задачи *(📁 finance · ⚠️ 18 переносов)*
- `115` 🔧 Другая задача *(📁 ремонт · 🔄 2)*

**M**
- `98` Купить кардхолдер *(⚠️ 18 переносов)*
    ⚠️ +2 просроченных (не сегодня)

🎯  6 целей (1 с задачами)
    ⚠️ Цель без задач
📈  0 сфер

⚠️  ВЕЧНЫЕ ХВОСТЫ (>=5 переносов):
    [93] 💰 Название  (перенос #18)

💡 Слишком много [H] задач (4) | 3 задач переносятся 5+ раз — отменить или переформулировать?
```

Логика рекомендаций (`💡`):
- H > 3 → пересмотри приоритеты
- overdue > 2 → пора ревью
- declining spheres >= 2 → запланируй действия
- eternal tasks > 0 → отменить или переформулировать
- иначе → "Всё ровно 👍"

## Зависимости

Python stdlib: `sqlite3`, `os`, `sys`, `json`, `datetime`, `subprocess`, `pathlib`, `zoneinfo`, `collections`

Сторонние: `PyYAML` (pip: `pyyaml`) — только для блока целей

Часовой пояс: `Europe/Moscow` (жёстко зашит, через `zoneinfo`)

## Troubleshooting

### /hub молчит в чате

Команда `/hub` вызывает hermes-hub. Если молчит:
1. Проверь что скрипт исполняемый: `ls -la ~/.local/bin/hermes-hub`
2. Запусти вручную: `hermes-hub` или `python3 ~/.local/bin/hermes-hub`
3. Смотри stderr: `python3 ~/.local/bin/hermes-hub 2>&1`

### "📈  0 сфер" всегда

planning.py читает дневники Obsidian `~/hermes-vault/Дневник/`. Причины:
- Нет дневников за текущую неделю → sphere_summary пустой → 0 сфер (норма)
- Дневник есть, но нет секции Сферы с оценками → то же самое
- Расхождение форматов: hermes-hub ожидает sphere_trends (список), planning.py отдаёт sphere_summary (dict) — сферы не будут показаны пока форматы не синхронизированы

Проверка: `python3 ~/.hermes/skills/productivity/life-planning/scripts/planning.py --json`

### "цели: No module named 'yaml'"

Установить PyYAML: `pip install pyyaml`

### "цели: [Errno 2] No such file or directory"

Создать файл `~/.hermes/life/goals.yaml` с минимальным содержимым:
```yaml
goals: []
```

### "Ошибка задач: ..."

Проверить что task_display.py существует: `ls ~/.hermes/scripts/task_display.py`
Запустить отдельно: `python3 ~/.hermes/scripts/task_display.py`

### Нет задач / пустая БД

БД должна быть по пути `~/.hermes/tasks/tasks.db`. Проверить: `ls ~/.hermes/tasks/`

## Интеграция

- Скрипт: `~/.local/bin/hermes-hub`
- Можно встроить в `morning-brief-pipeline` как блок
- Можно вызвать по расписанию (cron)
- Чат-команда `/hub` запускает hermes-hub автоматически

## История

- v1.0 (08.05.2026): Первая версия — задачи + цели + сферы + вечные хвосты
- v1.1 (27.05.2026): Добавлены архитектура, пути зависимостей, источники данных, зависимости, troubleshooting, реальный формат JSON из planning.py, расхождение sphere_trends vs sphere_summary
