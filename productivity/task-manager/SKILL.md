---
name: task-manager
description: Демон-планировщик для cronjobs.yml. Запускает скрипты по расписанию из ~/.hermes/tasks/cronjobs.yml. Работает как systemd-сервис.
---

# Task Manager Daemon

Системный демон, который читает расписание из SQLite (`tasks.db`, таблица `cron_jobs`) и запускает скрипты по cron-расписанию.

## Архитектура

```
task_manager/main.py
      │
      ▼
SQLite (~/.hermes/tasks/tasks.db)
  ├── cron_jobs    — расписание скриптов
  ├── tasks        — задачи пользователя
  ├── habits       — привычки
  └── periodic     — периодические напоминания
      │
      ▼
  subprocess → скрипты в навыках
```

## Как это работает

1. Демон запущен через systemd (бесконечный цикл, проверка каждые 60 сек)
2. Читает таблицу `cron_jobs` из SQLite, вычисляет `_next_run` для каждой задачи через `croniter`
3. Grace period 120 сек — если перезапуск демона был в течение 2 минут после запланированного времени, задача всё равно выполнится
4. При запуске скрипта: `subprocess.run()` с PYTHONPATH, включающим директорию скрипта
5. Авто-перезагрузка: проверяет `COUNT(*)` в таблице `cron_jobs` каждую минуту (если изменилось — перезагружает)

## Маппинг script → skill (с категорией)

Скрипты живут в навыках, main.py использует два словаря:

```python
SCRIPT_TO_SKILL = {
    "brief": "morning-brief-pipeline",
    "reminders": "cheap-telegram-reminders",
    "news_digest": "news-digest",
    "brief_evening": "evening-diary-brief",
    "task_migrate": "personal-task-tracker",
}

SCRIPT_CATEGORY = {
    "brief": "productivity",
    "reminders": "productivity",
    "news_digest": "productivity",
    "brief_evening": "brief",
    "task_migrate": "productivity",
}
```

**ВАЖНО:** Категория обязательна! Реальный путь:
`~/.hermes/skills/{category}/{skill}/scripts/`

Без категории (только по имени скилла) путь не найдётся, т.к. навыки лежат в поддиректориях категорий.

| script name | category | skill | путь скрипта |
|---|---|---|---|
| brief | productivity | morning-brief-pipeline | skills/productivity/morning-brief-pipeline/scripts/brief/ |
| brief_evening | brief | evening-diary-brief | skills/brief/evening-diary-brief/scripts/ |
| reminders | productivity | cheap-telegram-reminders | skills/productivity/cheap-telegram-reminders/scripts/ |
| news_digest | productivity | news-digest | skills/productivity/news-digest/scripts/ |
| task_migrate | productivity | personal-task-tracker | skills/productivity/personal-task-tracker/scripts/ |

## Добавление нового скрипта

1. Положить скрипт в `~/.hermes/skills/{category}/{skill}/scripts/`
2. Добавить запись в таблицу `cron_jobs` в `tasks.db`: `INSERT INTO cron_jobs (name, script, schedule, description) VALUES (...)`
3. Добавить команду в `SCRIPT_COMMANDS` в `main.py`
4. Добавить маппинг в `SCRIPT_TO_SKILL` и `SCRIPT_CATEGORY`
5. Перезапустить демон: `sudo systemctl restart task-manager`
6. Проверить: `sudo journalctl -u task-manager --since "1 min ago" --no-pager | grep -E "✅|❌"`

## Systemd Service

```ini
[Unit]
Description=Task Manager Scheduler
After=network.target

[Service]
Type=simple
User=hermes
Group=hermes
WorkingDirectory=/home/hermes/.hermes/skills/productivity/task-manager/scripts
Environment=PYTHONPATH=/home/hermes/.local/lib/python3.12/site-packages
ExecStart=/usr/bin/python3 task_manager/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Миграция скриптов из ~/.hermes/scripts/ в навыки

Если нужно перенести скрипт из `~/.hermes/scripts/` в навык:

1. Создать `scripts/` в скилле (если нет): `mkdir -p skills/{category}/{skill}/scripts`
2. Скопировать файл: `cp scripts/имя.py skills/{category}/{skill}/scripts/`
3. Добавить маппинг в `SCRIPT_TO_SKILL` + `SCRIPT_CATEGORY` в `main.py`
4. Добавить команду в `SCRIPT_COMMANDS` если её там нет
5. Перезапустить демон: `sudo systemctl restart task-manager`
6. Проверить: `sudo journalctl -u task-manager --since "1 min ago" --no-pager | grep -E "✅|❌"`
7. После проверки удалить оригинал из `~/.hermes/scripts/`

## Pitfalls

1. **⚠️ ВСЕГДА проверяй task-manager перед созданием Hermes cronjob!** 
   Расписание в SQLite (`~/.hermes/tasks/tasks.db`, таблица `cron_jobs`):
   - Evening Brief → script `brief_evening`, `0 18 * * *`
   - Morning Brief → script `brief`, `0 3 * * *`
   - News Digest → script `news_digest`, `30 10 * * *`
   - Task Migrate → script `task_migrate`, `1 21 * * *`
   - Reminders → script `reminders`, `0 5-19 * * *`
   
   Если пользователь просит настроить периодическую задачу — сначала: `sqlite3 ~/.hermes/tasks/tasks.db "SELECT * FROM cron_jobs"`. Если уже есть — не плоди дубликат.

2. **Не запускать вручную!** — systemd управляет единственным экземпляром.
3. **При миграции скриптов теряются патчи** — после переноса проверь diff.
4. **Категория в пути!** — `get_script_dir()` строит путь как `SKILLS_DIR / category / skill / "scripts"`. Забыть категорию = путь не найдётся.
5. **Авто-перезагрузка** — только при изменении `COUNT(*)` в `cron_jobs`.
6. **Скрипты должны быть исполняемыми** — `chmod +x` для *.py
7. **Демон не останавливается при ошибке скрипта** — только логирует
8. **/usr/bin/python3 → python3.12** — не путать с python3 из venv (3.11).
