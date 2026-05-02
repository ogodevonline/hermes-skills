---
name: task_manager
description: Управление задачами через модификацию YAML-файлов. Добавляет/удаляет задачи, привычки, напоминания и cronjobs.
setup_needed: true
---


## ⚠️ deprecated: personal-task-manager

**`personal-task-manager` (LLM-based) — удалён.** Не используйте. Вместо него:
- Прямое редактирование YAML (см. `personal-task-direct`)
- Или `task_manager/main.py` демон для системных cronjobs

# Task Manager Skill

**Требует установки зависимостей:**
```bash
pip install --break-system-packages schedule croniter pyyaml requests
```

# Task Manager Skill

Управление всеми типами задач через прямое редактирование YAML-файлов.

## ⚠️ ВАЖНО

**Skill работает с файлами, а не с Hermes cronjobs!** Hermes cronjobs вызывают LLM — это медленно и дорого.

Используй:
- Прямое чтение/запись YAML через Python (pyyaml)
- Systemd-демон `task_manager/main.py` для исполнения расписания

## Структура

```
~/.hermes/tasks/
├── tasks.yml       # задачи на сегодня/завтра/backlog
├── habits.yml      # привычки с фиксированным временем
├── reminders.yml   # периодические задачи (каждый N часов)
└── cronjobs.yml    # системные cron-задачи (мониторинг, брифы)

~/.hermes/scripts/task_manager/main.py  # демон-планировщик
```

## YAML схемы

### tasks.yml
```yaml
today:
  - name: "Сходить в зал"
    priority: H  # H/M/L
    duration: "1.5ч"
    reminder: "18:00"
tomorrow: []     # завтрашние задачи
backlog: []      # общий бэклог
```

### habits.yml
```yaml
habits:
  - name: "Omega + D3"
    time: "08:00"
```

### reminders.yml
```yaml
periodic:
  - name: "Приседания 10 раз"
    every: "1h"      # интервал: 5m, 1h, 2h
    start: "08:00"
    end: "22:00"
```

### cronjobs.yml
```yaml
cronjobs:
  - name: "Morning Brief"
    script: "brief"
    schedule: "0 3 * * *"    # cron UTC
    description: "Утренний бриф в 06:00 МСК"
    enabled: true
```

script: "brief" | "reminders" | "news_digest" | "brief_evening" | (другие Python-скрипты)

**ВАЖНО:** Каждый новый script name надо зарегистрировать в `SCRIPT_COMMANDS` словаре
в `~/.hermes/scripts/task_manager/main.py`! Иначе task_manager не будет знать,
какую команду запускать. Пример добавления:
```python
SCRIPT_COMMANDS = {
    "brief": ["python3", "-c", "from brief import generate_brief; generate_brief()"],
    "news_digest": ["python3", "news_digest.py"],
    "my_new_script": ["python3", "my_new_script.py"],
    ...
}
```

### ⚠️ Не создавай Hermes cronjob
Если пользователь просит добавить новую периодическую задачу — НЕ используй `cronjob()` инструмент.
У пользователя свой task_manager демон с `~/.hermes/tasks/cronjobs.yml`.
Вместо этого:
1. Добавь запись в `~/.hermes/tasks/cronjobs.yml`
2. Зарегистрируй команду в `SCRIPT_COMMANDS` в `~/.hermes/scripts/task_manager/main.py`
3. Демон сам подхватит изменения (авто-перезагрузка по mtime)

## API (python3)

```python
import yaml
from pathlib import Path

TASKS_DIR = Path.home() / ".hermes" / "tasks"

def read_yaml(filename: str):
    path = TASKS_DIR / filename
    with open(path) as f:
        return yaml.safe_load(f) or {}

def write_yaml(filename: str, data: dict):
    path = TASKS_DIR / filename
    with open(path, "w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
```

## Команды

### Добавить задачу на сегодня
```
добавить задачу [название] приоритет [H/M/L] длительность [Nч] напоминание [HH:MM]
```
Пример: `добавить задачу Сходить в зал приоритет H длительность 1.5ч напоминание 18:00`

### Добавить привычку
```
добавить привычку [название] время [HH:MM]
```
Пример: `добавить привычку Дыхание по Вим Хофу время 08:00`

### Добавить периодическое напоминание
```
добавить periodic [название] каждый [Nm/h] с [HH:MM] по [HH:MM]
```
Пример: `добавить periodic Приседания 10 раз каждый 1h с 08:00 по 22:00`

### Добавить cronjob
```
добавить cronjob [название] script [brief|reminders] schedule "[cron UTC]"
```
Пример: `добавить cronjob "Проверка API" script reminders schedule "*/30 * * * *"`

### Удалить
```
удалить [тип] [название]
```
Типы: `задача`, `привычка`, `periodic`, `cronjob`

### Список
```
показать [тип]
```
Типы: `все`, `задачи`, `привычки`, `periodic`, `cronjobs`

### Обновить задачу
```
обновить задачу [старое название] новое название [новое] приоритет [H/M/L] ...
```

## Pitfalls

1. **Файлы `.yml`, не `.yaml`** — расширение важно
2. **Время в UTC для cronjobs.yml** — schedule в UTC, а остальные файлы используют МСК
3. **Задача = напоминание!** — всегда спрашивать время при добавлении задачи
4. **cronjobs.yml — для системных задач** (brief, reminders, мониторинг), не для личных задач
5. **Демон task_manager** должен быть запущен через systemd, а не через cron

## Systemd

```ini
# /etc/systemd/system/task-manager.service
[Unit]
Description=Task Manager Scheduler
After=network.target

[Service]
Type=simple
User=hermes
WorkingDirectory=/home/hermes/.hermes/scripts
ExecStart=/usr/bin/python3 task_manager/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Установка зависимостей (если ещё не установлены)
pip install --break-system-packages schedule croniter pyyaml requests

# Активация
sudo systemctl daemon-reload
sudo systemctl enable --now task-manager
sudo systemctl status task-manager
```

## Проверка

```bash
# Проверить синтаксис YAML
python3 -c "import yaml; yaml.safe_load(open('~/.hermes/tasks/cronjobs.yml'))"

# Запустить демон вручную (для тестов)
cd ~/.hermes/scripts && python3 task_manager/main.py

# Проверить логи
tail -f ~/.hermes/logs/task_manager.log
```

## Implementation Details (внутренности)

### Стек
- **Планировщик:** `schedule` + `croniter` (лёгкие, стабильные)
- **Демон:** `main.py` с бесконечным циклом, systemd service
- **Запуск скриптов:** через `subprocess.run()` с `capture_output=True`, `timeout=300`
- **Зависимости:** `pip install schedule croniter pyyaml requests`

### Логика запуска (в main.py)
1. **Инициализация:** при старте вычисляем `_next_run` через `croniter(schedule, now)`
2. **Grace period (120 сек):** если `get_prev()` был в последние 2 минуты, ставим `_next_run = prev_run`. Это избегает пропуска задач при перезапуске демона в промежутке `[scheduled_time, scheduled_time+grace)`.
3. **Цикл (каждые 60 сек):** `now_ts >= _next_run` → запуск → `get_next()` для следующего.
4. **Авто-перезагрузка:** проверяем `mtime` `cronjobs.yml` каждую итерацию; при изменении — перечитываем.

### PYTHONPATH для subprocess
```python
SCRIPTS_DIR = Path("/home/hermes/.hermes/scripts")
site_packages = Path.home() / ".local" / "lib" / "python3.12" / "site-packages"
env["PYTHONPATH"] = f"{SCRIPTS_DIR}:{site_packages}:" + env.get("PYTHONPATH", "")
```
`SCRIPTS_DIR` нужен для импорта `brief` как модуля (`from brief import generate_brief`).

### Timezone
- **cronjobs.yml:** расписание в **UTC**
- **tasks.yml/habits.yml/reminders.yml:** время в **МСК**
- Конвертация: МСК = UTC+3. Пример: 08:00 МСК → `schedule: "0 5 * * *"`

### Telegram integration
- `brief/__init__.py` и `reminders.py` читают `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` из `~/.hermes/.env`
- `TELEGRAM_CHAT_ID` берётся (в порядке приоритета):
  1. `TELEGRAM_ALLOWED_USERS` (первый ID, если несколько через запятую)
  2. `TELEGRAM_HOME_CHANNEL`
- `brief` использует `parse_mode=Markdown` с fallback на plain text
- `reminders.py` использует `parse_mode=None` (plain text)

### Дополнительные pitfalls
1. **Grace period:** без него задачи пропускаются при перезапуске в промежутке `[scheduled, scheduled+60s)`. С grace period: `_next_run = prev_run` → запуск через ≤60 сек.
2. **Auto-reload:** `mtime` проверяется раз в минуту; двойное редактирование быстрее — вторая перезагрузка задержится.
3. **TELEGRAM_ALLOWED_USERS** может содержать несколько ID через запятую — `reminders.py` использует первый.
4. **reminders.py** должен быть исполняемым (`chmod +x`) и в `~/.hermes/scripts/`.
5. Убедитесь, что `~/.hermes/logs/` существует и доступен пользователю `hermes`.

