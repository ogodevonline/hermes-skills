---
name: personal-task-tracker
category: productivity
description: SQLite-based CLI трекер задач и привычек. Одна БД, простые команды, короткий статус для Hermes.
setup_needed: true
---

# Personal Task Tracker

## Что это
SQLite-трекер задач и привычек. Всё в одной БД `~/.hermes/tasks/tasks.db`.

## Структура БД

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    priority TEXT DEFAULT 'M',   -- H, M, L
    category TEXT DEFAULT 'general',
    status TEXT DEFAULT 'pending',  -- pending, done, cancelled, backlog
    due_date TEXT,   -- YYYY-MM-DD or YYYY-MM-DD HH:MM
    created_at TEXT DEFAULT (datetime('now','localtime')),
    done_at TEXT,
    carry_over INTEGER DEFAULT 0  -- сколько раз переносилась (макс 3 → backlog)
);

CREATE TABLE habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    time TEXT,         -- HH:MM
    sort_order INTEGER DEFAULT 0,
    days TEXT DEFAULT '*'  -- дни недели: '*'=ежедневно, 'Sat,Sun'=выходные, 'Mon,Wed,Fri' и т.д.
);

CREATE TABLE IF NOT EXISTS habit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    done INTEGER DEFAULT 0,
    done_at TEXT,
    FOREIGN KEY (habit_id) REFERENCES habits(id)
);
```

Колонка `days` добавлена через ALTER TABLE (функция `add_days_column()` вызывается при каждом запуске `t`).

## CLI-команды

Скрипт `t` в `~/.local/bin/t` (424+ строк, Python).

```bash
# Задачи
t add "Название" [-p M] [-c general] [-d YYYY-MM-DD] [-r HH:MM] [--duration "1.5ч"]
t done <id>                                             # ✅
t cancel <id>                                           # ❌
t postpone <id> [-d YYYY-MM-DD]                         # ➡️ перенести на завтра/указ. дату
t list [--all|--date YYYY-MM-DD|--backlog]              # список (сегодня по умолч.)
t migrate                                               # все просрочки → завтра
t status                                                # краткий статус для Hermes

# Привычки
t habits                              # список на сегодня с количеством подходов (✅xN)
t habit-add "Название" --time HH:MM [--days "Sat,Sun"]
t habit-done <id>                     # ✅ множественный трекинг — можно несколько раз в день
t habit-rm <id>

# Периодические задачи
t periodic
t periodic-add "Название" -e "1h" [--start 09:00] [--end 22:00]
t periodic-rm <id>
```

### t postpone (добавлена)

Перенос pending-задачи без cancel+add:
```
t postpone 8          # → завтра (перенос #1)
t postpone 8 -d 2026-05-01  # → на 1 мая
```
Увеличивает `carry_over` на 1. При >=3 — предупреждение, после `migrate` уйдёт в backlog.

### t habit-add --days (добавлена)

Расписание привычек по дням недели:
```
t habit-add "Постричь ногти" --time 20:00 --days "Sat,Sun"
t habit-add "Работа" --days "Mon,Tue,Wed,Thu,Fri"
```
Формат: трёхбуквенные английские дни через запятую. `*` = ежедневно (по умолчанию).

`t habits` показывает только привычки, подходящие под сегодняшний день недели.
Скрытые привычки: `(+N не по расписанию)` в итоге.

## Особенности

- **Нет sqlite3 CLI** — только через `t` или Python `import sqlite3`
- **Лимит переносов** — 3 переноса, потом задача в backlog
- **Привычки по расписанию** — колонка `days` (Mon,Tue,Wed,Thu,Fri,Sat,Sun или *)
- **Вывод с ID** — `[ 1]`, `[ 9]` — все команды показывают числовые ID для быстрых действий

## Интеграция с Hermes

При запросе «задачи»/«статус»/«что сегодня» — запускать `t status` (сырой stdout).
При запросе «отметь задачу X сделанной» — `t done <id>`.
При переносе задачи — `t postpone <id>` (а не cancel+add).

## Cron

Скрипт `task_migrate.py` вызывает `t migrate` в 00:01 МСК.
Лимит переносов: 3 раза, после задача уходит в backlog.

## Pitfalls

1. **systemd PATH** — systemd-сервисы не видят `~/.local/bin`. Решение: полный путь `~/.local/bin/t` или `shutil.which("t")`.
2. **python3.12 vs venv** — демон task-manager использует `/usr/bin/python3` (3.12), не venv-ный python3.11.
3. **Привычки с днями** — при добавлении колонки `days` через ALTER TABLE, существующие привычки получают `days='*'` (ежедневно). Надо вручную обновить: `UPDATE habits SET days='Sat,Sun' WHERE id=N`.
4. **patch tool** — при редактировании `t` (многострочный Python) patch иногда ломает кавычки (`\"` → `\\\"`). Проверять после каждого patch.
5. **Привычки без UNIQUE** — `habit_log` не имеет `UNIQUE(habit_id, date)`, поэтому `t habit-done <id>` можно вызывать **много раз в день**. Каждый вызов создаёт новую запись. В выводе `t habits` показывается количество подходов: ✅x3.

## Связь привычек и периодических задач

Привычки и периодические задачи — **разные системы, но для одного действия**:

- **Периодическая задача** (таблица `periodic`) — **напоминания**. Task_manager шлёт уведомления по расписанию (каждый час и т.п.). Не трекает выполнение.
- **Привычка** (таблица `habits`) — **трекинг**. Ручное отмечание через `t habit-done <id>`. Множественные чеки в день.

Пример: "Приседания"
- Периодика: `[1] Приседания 10 раз (каждые 1h)` → напоминает каждый час
- Привычка: `[12] Приседания` (без времени) → чекаешь `t habit-done 12` после каждого подхода

Вывод `t habits` покажет: `✅x4 [12] Приседания` — сделано 4 подхода сегодня.

## Установка
```bash
chmod +x scripts/t
ln -sf $(pwd)/scripts/t ~/.local/bin/t
```
