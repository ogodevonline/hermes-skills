---
name: cheap-telegram-reminders
description: Создание дешевых напоминаний в Telegram без LLM — Python скрипт + cron + SQLite
---

# Cheap Telegram Reminders

Единый Python-скрипт `reminders.py` для всех напоминаний (задачи, привычки, периодика). Читает данные из SQLite (`tasks.db`), запускается cron'ом каждый час.

## Архитектура

```
task-manager (systemd) → cronjobs.yml → reminders.py
                                              │
                                              ▼
                                         SQLite (tasks.db)
                                              │
                                              ▼
                                         Telegram Bot API → Пользователь
```

## Скрипт

**Путь:** `~/.hermes/skills/productivity/cheap-telegram-reminders/scripts/reminders.py`

Три источника напоминаний:

### 1️⃣ Задачи (`tasks` table)
- Колонки: `reminder` (ЧЧ:ММ), `duration` (напр. 1.5ч), `due_date`, `status`, `priority`
- Срабатывает если `due_date = сегодня ∧ status = 'pending' ∧ reminder = сейчас`
- Пример: `t add "Сходить в зал" --reminder 18:00 --duration 1.5ч`

### 2️⃣ Привычки (`habits` table)
- Колонки: `time` (ЧЧ:ММ), `weekdays` (дни через запятую, или пусто — каждый день)
- Срабатывает если `time = сейчас` и день подходит
- Управляются через `t habit-add / t habits / t habit-done`

### 3️⃣ Периодика (`periodic` table)
- Колонки: `every` (1h), `start_time` (08:00), `end_time` (22:00), `last_sent_hour`
- **Защита от дублей:** `last_sent_hour` записывается при отправке. Если скрипт запустится второй раз в тот же час — пропускает.
- Пример: `t periodic-add "Приседания 10 раз" --every 1h`
- Управляются через `t periodic` / `t periodic-add` / `t periodic-rm`

## Cron

```yaml
- name: Универсальный reminder
  script: reminders
  schedule: 0 5-19 * * *    # 08:00-00:00 МСК каждый час
  enabled: true
```

| МСК | UTC | Запуск |
|-----|-----|--------|
| 08:00 | 05:00 | 1й |
| 09:00 | 06:00 | 2й |
| 10:00 | 07:00 | 3й |
| ... | ... | ... |
| 00:00 | 21:00 | последний |

## SQLite схема (ключевые колонки для reminders.py)

### tasks
| Колонка | Тип | Описание |
|---------|-----|----------|
| name | TEXT | Название задачи |
| due_date | TEXT | Дата "ГГГГ-ММ-ДД" |
| status | TEXT | pending / done / cancelled |
| reminder | TEXT | ЧЧ:ММ (опционально) |
| duration | TEXT | длительность (опционально) |
| priority | TEXT | H/M/L |

### habits
| Колонка | Тип | Описание |
|---------|-----|----------|
| name | TEXT | Название привычки |
| time | TEXT | ЧЧ:ММ |
| weekdays | TEXT | дни недели (напр. "Пн,Ср,Пт") |

### periodic
| Колонка | Тип | Описание |
|---------|-----|----------|
| name | TEXT | Название |
| every | TEXT | интервал (напр. "1h") |
| start_time | TEXT | начало окна |
| end_time | TEXT | конец окна |
| last_sent_hour | INTEGER | час последней отправки (-1 = никогда) |

## ⚠️ Правило выбора: no_agent для статики — ПЕРВЫЙ выбор

Когда создаёшь cronjob, который шлёт **фиксированный текст** (напоминалка, пинок, предложение действий) — **сразу делай `no_agent=true`**. Не начинай с LLM-driven. LLM-driven — только когда нужна генерация (дайджест, сводка, анализ).

> Урок: пользователь поправил, когда я сначала починил LLM-driven версию вместо того чтобы сразу перевести на no_agent. Это потеря токенов и лишний шаг.

## Самый дешёвый паттерн: no_agent=true cronjob

```bash
# ⚠️ `hermes cronjob` — НЕ существует (CLI: invalid choice: 'cronjob'). CLI-глагол — `hermes cron` (list/add/...).
# Крон-джобы с no_agent создаёт АГЕНТ инструментом `cronjob` (а не через CLI):
cronjob(action="create", name="lunch-reminder", schedule="30 13 * * *",
        no_agent=true,
        script="echo -e '🍽 Обед!\n📰 /news\n📋 /tasks\n🔥 /trends\n🏠 /houses\n💰 /rates'",
        deliver="origin")
```

**Почему это дешевле:**
- `no_agent=true` → **ноль токенов LLM**, ноль вызовов модели
- Скрипт выполняется раз в день, stdout сразу идёт в Telegram
- Идеально для меню, напоминалок, предложений выбора

**Когда использовать no_agent=true:**
- Статический текст (меню на день, предложение действий)
- `script` = однострочник с echo / printf
- Не нужно никакой логики, фильтрации, AI
- Противоположность: если нужно сгенерировать что-то (дайджест, сводку) — используй LLM-driven cronjob или on-demand навык

## Pitfalls

1. **Timezone!** — скрипт форсирует `Europe/Moscow` через `os.environ['TZ'] + time.tzset()`. Все времена в БД (reminder, habits time) должны быть в МСК.
2. **Дубли при повторном запуске за минуту** — `check_periodic()` использует `last_sent_hour`. Если скрипт упал после отправки но до `UPDATE` — `last_sent_hour` не запишется, и в следующий раз (новый час) отработает нормально.
3. **systemd не видит `~/.local/bin/`** — если reminders.py вызывает внешний CLI через subprocess (например `task_migrate.py` → `t migrate`), используй полный путь `~/.local/bin/t` или через `os.path.expanduser()`.
3. **Привычки: один источник истины** — если привычки есть и в SQLite, и в YAML — каждое срабатывание даст дубль. Решение: хранить только в SQLite, `check_habits()` никогда не читает YAML.
4. **Telegram без parse_mode** — используется plain text (без `parse_mode`), чтобы не было ошибок с кириллицей и спецсимволами.
5. **delta_interval для periodic не используется** — интервал `every` (1h) служит для отображения, реальная частота определяется cron'ом. Защита от дублей — только через `last_sent_hour`.
6. **Задача-напоминалка срабатывает ТОЛЬКО в :00 минуту.** `check_tasks()` матчит `reminder = current_time` по точному `ЧЧ:ММ`, а cron гоняет скрипт раз в час на :00. Значит `--reminder 17:45` НИКОГДА не сработает (запуски 17:00 и 18:00 не совпадут с 17:45). Для напоминания в не-:00 время — одноразовый `cronjob` no_agent со `schedule` = ISO-таймстамп в МСК на нужную минуту (проверено 25.08.2026).
7. **Напоминалка НЕ чинит контекстный сбой памяти.** Если пользователь забыл задачу в момент контекста («вышел из метро и прошёл мимо аптеки»), time-напоминалка бесполезна — момент не привязан ко времени. Предлагать поведенческое решение (задача ПЕРВОЙ задачей утра, привычка-якорь по дню недели) или гео-напоминалку (Google Keep, Android), а НЕ плодить крон-напоминалки. Пользователь явно отклонил time-напоминалку в таком кейсе (25.08.2026).

## t CLI команды для периодики

```bash
t periodic                    # список
t periodic-add "Присесть 20 раз" --every 2h --start 10:00 --end 20:00
t periodic-rm 1               # удалить
```