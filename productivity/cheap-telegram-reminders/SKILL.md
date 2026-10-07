---
name: cheap-telegram-reminders
description: Создание дешевых напоминаний в Telegram без LLM — Python скрипт + cron + Google Tasks/SQLite
---

# Cheap Telegram Reminders

Единый Python-скрипт `reminders.py` для всех напоминаний. **Задачи** читаются из
Google Tasks, **привычки** и **периодика** — из SQLite (`tasks.db`). Запускается
cron'ом каждый час.

## Архитектура

```
task-manager (systemd) → cronjobs.yml → reminders.py
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
                 Google Tasks ⛅TODAY    SQLite: habits       SQLite: periodic
              (tasks_api.py, OAuth)   (ведёт другой агент)  (ведёт другой агент)
                        │
                        ▼
                 Telegram Bot API → Пользователь
```

Источник задач мигрирован с локальной `tasks.db` на Google Tasks 06.10.2026.
OAuth не пишется свой — импортируется `get_service()` из
`skills/productivity/google-workspace/scripts/tasks_api.py`.

## Скрипт

**Путь:** `~/.hermes/skills/productivity/cheap-telegram-reminders/scripts/reminders.py`

Три источника напоминаний:

### 1️⃣ Задачи (Google Tasks, список «⛅ TODAY»)
- Открытые задачи (`status = needsAction`) из списка `⛅ TODAY`
  (id `VDhuNDh2enVHY1I3TlBtUQ`).
- Время напоминания задаётся **в notes** задачи строкой `reminder:HH:MM`.
- Срабатывает если `due` пустой или = сегодня и `reminder` = текущее `ЧЧ:ММ`.
- Приоритет: `❗` в начале заголовка = High (`[приоритет: H]` в сообщении).
- Пример notes: `reminder:18:00` / `local:#229 reminder:18:00`.
- Задача без `reminder:HH:MM` в notes time-напоминание НЕ даёт (не спамит).

### 2️⃣ Привычки (`habits` table, SQLite — не трогаем, ведёт другой агент)
- Колонки: `time` (ЧЧ:ММ), `weekdays` (дни через запятую, или пусто — каждый день)
- Срабатывает если `time = сейчас` и день подходит
- Управляются через `t habit-add / t habits / t habit-done`

### 3️⃣ Периодика (`periodic` table, SQLite — не трогаем, ведёт другой агент)
- Колонки: `every` (1h), `start_time` (08:00), `end_time` (22:00), `last_sent_hour`
- **Защита от дублей:** `last_sent_hour` записывается при отправке. Если скрипт запустится второй раз в тот же час — пропускает.
- Пример: `t periodic-add "Приседания 10 раз" --every 1h`
- Управляются через `t periodic` / `t periodic-add` / `t periodic-rm`

## Режим без отправки

```bash
python3 ~/.hermes/skills/productivity/cheap-telegram-reminders/scripts/reminders.py --dry-run
```

Печатает открытые задачи из Google (⛅ TODAY) и то, что было бы отправлено.
Telegram не трогает, `periodic.last_sent_hour` не пишет — база остаётся нетронутой.

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
| ... | ... | ... |
| 00:00 | 21:00 | последний |

## Google Tasks: что важно для reminders.py

| Поле | Описание |
|------|----------|
| title | Название задачи; `❗` в начале = High |
| due | Дата `ГГГГ-ММ-ДДT00:00:00.000Z` (время не поддерживается Google Tasks) |
| notes | Заметка; здесь хранится `reminder:HH:MM` и маркер `local:#<id>` |
| status | `needsAction` (открыта) / `completed` |

Списки Google Tasks: `⛅ TODAY` (`VDhuNDh2enVHY1I3TlBtUQ`),
`📥 BACKLOG` (`MDM0ODI5NzY3OTIxMTU4MDMzOTQ6MDow`),
`🌱 HABITS` (`Y0c3NGFIRThRTnlWNFRpMg`).

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

1. **Timezone!** — скрипт форсирует `Europe/Moscow` через `os.environ['TZ'] + time.tzset()`. Все времена (reminder в notes, habits time) должны быть в МСК.
2. **Дубли при повторном запуске за минуту** — `check_periodic()` использует `last_sent_hour`. Если скрипт упал после отправки но до `UPDATE` — `last_sent_hour` не запишется, и в следующий раз (новый час) отработает нормально.
3. **systemd не видит `~/.local/bin/`** — если reminders.py вызывает внешний CLI через subprocess (например `task_migrate.py` → `t migrate`), используй полный путь `~/.local/bin/t` или через `os.path.expanduser()`.
4. **Привычки: один источник истины** — если привычки есть и в SQLite, и в YAML — каждое срабатывание даст дубль. Решение: хранить только в SQLite, `check_habits()` никогда не читает YAML.
5. **Telegram без parse_mode** — используется plain text (без `parse_mode`), чтобы не было ошибок с кириллицей и спецсимволами.
6. **delta_interval для periodic не используется** — интервал `every` (1h) служит для отображения, реальная частота определяется cron'ом. Защита от дублей — только через `last_sent_hour`.
7. **Задача-напоминалка срабатывает ТОЛЬКО в :00 минуту и только с `reminder:HH:MM` в notes.** `check_tasks()` матчит время из notes по точному `ЧЧ:ММ`, а cron гоняет скрипт раз в час на :00. Значит `reminder:17:45` НИКОГДА не сработает (запуски 17:00 и 18:00 не совпадут с 17:45). Для напоминания в не-:00 время — одноразовый `cronjob` no_agent со `schedule` = ISO-таймстамп в МСК на нужную минуту (проверено 25.08.2026).
8. **Google Tasks не хранит время напоминания.** Поле `due` — только дата. Поэтому время живёт в notes-конвенции `reminder:HH:MM`, и его перезаписывает не gtsync, а ручная правка задачи.
9. **Напоминалка НЕ чинит контекстный сбой памяти.** Если пользователь забыл задачу в момент контекста («вышел из метро и прошёл мимо аптеки»), time-напоминалка бесполезна — момент не привязан ко времени. Предлагать поведенческое решение (задача ПЕРВОЙ задачей утра, привычка-якорь по дню недели) или гео-напоминалку (Google Keep, Android), а НЕ плодить крон-напоминалки. Пользователь явно отклонил time-напоминалку в таком кейсе (25.08.2026).

## t CLI команды для периодики

```bash
t periodic                    # список
t periodic-add "Присесть 20 раз" --every 2h --start 10:00 --end 20:00
t periodic-rm 1               # удалить
```
