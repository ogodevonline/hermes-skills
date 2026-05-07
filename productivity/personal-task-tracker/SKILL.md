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
    carry_over INTEGER DEFAULT 0  -- сколько раз переносилась
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
Увеличивает `carry_over` на 1. При >=3 — предупреждение.

### ⚠️ БАГ: `t migrate` переносил на завтра вместо сегодня (ИСПРАВЛЕНО 06.05.2026)

В `cmd_migrate()` в `~/.local/bin/t` использовался `tomorrow_msk()` вместо `today()`:
```python
# ❌ БЫЛО — задачи пропускали день
(   tomorrow_msk(), carries, r["id"])

# ✅ СТАЛО — задачи переносятся на сегодня
(   today(), carries, r["id"])
```
**Симптом:** migrate в 00:01 МСК переносил просрочку на `tomorrow()` (следующий день), а не на текущую дату. Пользователь терял день — задачи не показывались в `t list` сегодня.

**Фикс:** заменить `tomorrow_msk()` на `today()` в UPDATE-запросе `cmd_migrate()`.

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
- **Без лимита переносов** — `t migrate` переносит все просрочки на сегодня (не завтра!), никогда не отправляет в backlog
- **MSK timezone** — `today()` использует Europe/Moscow через `zoneinfo`, не UTC
- **Бэклог в утреннем брифе** — задачи со статусом `backlog` выводятся отдельной секцией 📦
- **Привычки по расписанию** — колонка `days` (Mon,Tue,Wed,Thu,Fri,Sat,Sun или *)
- **Вывод с ID** — `[ 1]`, `[ 9]` — все команды показывают числовые ID для быстрых действий

## Интеграция с Hermes

При запросе «задачи»/«статус»/«что сегодня» — запускать `t status` (сырой stdout).
При запросе «отметь задачу X сделанной» — `t done <id>`.
При переносе задачи — `t postpone <id>` (а не cancel+add).

## Cron

Скрипт `task_migrate.py` вызывает `t migrate` в 00:01 МСК.
Без лимита переносов — все просрочки переезжают на сегодня.

## Pitfalls

1. **⚡ `-d tomorrow` пишет строку \"tomorrow\" в БД (БАГ, ИСПРАВЛЕНО 08.05.2026)**
   `cmd_add`, `cmd_list`, `cmd_postpone` не парсили "tomorrow"/"today"/"завтра"/"сегодня" в ISO-дату.
   **Фикс:** добавлена функция `parse_date(s)` в ~/.local/bin/t, вызывается во всех трёх местах.

2. **systemd PATH** — systemd-сервисы не видят `~/.local/bin`. Решение: полный путь `~/.local/bin/t` или `shutil.which("t")`.

8. **⚠️ cmd_migrate переносил на завтра вместо сегодня (БАГ, ИСПРАВЛЕНО 06.05.2026)**
   В `cmd_migrate()` в `~/.local/bin/t` (строка ~183) использовался `tomorrow_msk()` вместо `today()`:
   ```python
   # ❌ БЫЛО — задачи пропускали день
   conn.execute("UPDATE tasks SET due_date=?, carry_over=? WHERE id=?",
                (tomorrow_msk(), carries, r["id"]))
   
   # ✅ СТАЛО — задачи переносятся на сегодня
   conn.execute("UPDATE tasks SET due_date=?, carry_over=? WHERE id=?",
                (today(), carries, r["id"]))
   ```
   **Симптом:** migrate в 00:01 МСК переносил просрочку на ЗАВТРА (следующий день), а не на СЕГОДНЯ. Пользователь терял день — задачи висели "в никуда" и не показывались в `t list` текущего дня.
   **Фикс:** заменить `tomorrow_msk()` на `today()` в `cmd_migrate()`.
2. **python3.12 vs venv** — демон task-manager использует `/usr/bin/python3` (3.12), не venv-ный python3.11.
3. **Привычки с днями** — при добавлении колонки `days` через ALTER TABLE, существующие привычки получают `days='*'` (ежедневно). Надо вручную обновить: `UPDATE habits SET days='Sat,Sun' WHERE id=N`.
4. **patch tool** — при редактировании `t` (многострочный Python) patch иногда ломает кавычки (`\\\"` → `\\\\\\\"`). Проверять после каждого patch.
5. **Привычки без UNIQUE** — `habit_log` не имеет `UNIQUE(habit_id, date)`, поэтому `t habit-done <id>` можно вызывать **много раз в день**. Каждый вызов создаёт новую запись. В выводе `t habits` показывается количество подходов: ✅x3.
6. **`t postpone` не меняет время задачи** — команда `t postpone <id> [-d DATE]` меняет только `due_date`, но **не время**. Время хранится в поле `name` как префикс (например, `"17:00 💪 Тренажёрный зал"`). Чтобы изменить время, нужно править `name` напрямую через SQLite:

   ```python
   import sqlite3
   conn = sqlite3.connect('/home/hermes/.hermes/tasks/tasks.db')
   # Для задачи с временем в имени — заменить префикс
   conn.execute("UPDATE tasks SET name = REPLACE(name, '17:00', '07:00') WHERE id = 60")
   # Для задачи без времени — переписать имя целиком
   conn.execute("UPDATE tasks SET name = '09:00 🧺 Постирать вещи' WHERE id = 25")
   conn.commit()
   conn.close()
   ```

   **Альтернатива** — пересоздать задачу: `t cancel <id>` + `t add "07:00 💪 Зал" -d YYYY-MM-DD`, но это теряет историю переносов (carry_over). SQLite-редактирование предпочтительнее.
7. **Проверка структуры БД** — перед SQLite-правкой всегда проверять схему:
   ```python
   conn.execute('PRAGMA table_info(tasks)').fetchall()
   ```
   Поле `due_date` хранит ТОЛЬКО дату (YYYY-MM-DD), время — только в `name`.

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
