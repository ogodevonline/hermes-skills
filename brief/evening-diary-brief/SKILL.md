---
name: evening-diary-brief
category: brief
description: Вечерний бриф — подведение итогов дня с ID-шниками, рефлексией и сохранением в Obsidian.
---

# Вечерний дневник (Evening Diary Brief)

## Что это
Система вечернего подведения итогов: задачи → привычки → рефлексия → Obsidian.
Работает в двух режимах: интерактивный (чат с Hermes) и автоматический (скрипт --send).

## Как работает

### База
- SQLite + CLI `t` (personal-task-tracker). База: `~/.hermes/tasks/tasks.db`.
- `sqlite3` CLI не установлен — только через Python `sqlite3` модуль или `t`.
- Перенос задачи: `t postpone <id>` (на завтра) или `t postpone <id> -d ДАТА`.
- Команда `t habit-add --days "Sat,Sun"` — привычки по дням недели.

### Два режима

**1. Чат с ассистентом (Telegram/CLI — основной)**
Hermes делает полный цикл интерактива:
1. Запускает `t list` — сырой stdout с ID, НЕ переписывать
2. Спрашивает по каждой ⏳ задаче (✅/❌/⏳). Если ❌ — уточнить отменить или перенести.
3. `t done <id>` / `t cancel <id>` / `t postpone <id>` (перенос на завтра)
4. Запускает `t habits` — сырой stdout с ID, НЕ переписывать
5. Спрашивает, что сделано → `t habit-done <id>`
   > ⚠️ **ID могут быть НЕ последовательны** — в выводе могут быть пропуски (напр. `[1]-[8]`, потом `[10]` без `[9]`). Всегда бери ID из сырого stdout, не нумеруй сам.
6. **5 вопросов рефлексии** (обязательно!)
7. Сохраняет в Obsidian: `~/hermes-vault/Дневник/YYYY-MM-DD.md`
8. Сохранить + закоммитить: используй `write_note()` для записи, затем `commit_all("diary YYYY-MM-DD")` для одного коммита.
   > ⚠️ Post-commit hook делает `git push` автоматически после каждого коммита.

> ⚠️ **Никогда не пропускать 6-8.** Это accountability partner, а не просто логгер.

**2. Скрипт (--send)**
```bash
python3 ~/.hermes/skills/brief/evening-diary-brief/scripts/brief_evening.py --send
```
Что делает:
- `t status` + `t list` + `t habits` → сырые stdout
- `build_brief_msg()` → форматирует
- Сохраняет шаблон в Obsidian (с `_ _` вместо ответов)
- Отправляет в Telegram через `send_telegram()` (Bot API, `urllib.request`)
- Выводит статус в stdout

**Отправка в Telegram:**
- Читает `.env` через `dotenv_get()` — пропускает строки с `#`
- Нужные переменные: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_HOME_CHANNEL`
- Использует `urllib.request`, не curl/xitter

### Пять вопросов рефлексии (обязательные)
1. **Что сегодня прошло ХОРОШО?** — победы, достижения, приятные моменты
2. **Где облажался / можно лучше?** — проколы, что не сделал, зоны роста
3. **Главный урок / инсайт дня** — что понял за день
4. **На что обратить внимание завтра?** — приоритеты на завтра
5. **Deep Work (фокус-время)** — сколько часов было в фокусе

### Автоматический перенос
В 00:01 МСК `task_migrate.py` → `t migrate` — переносит просрочку на завтра (макс 3 переноса, потом backlog).

## Структура вывода (чат)

Вывод `t list` и `t habits` — **только сырой stdout с ID-шниками**.

```
⏳ 🟡 [ 8] Позвонить маме ⏰14:00
✅ 🔴 [ 9] Сходить в зал ⏰18:00
⏳ 🟡 [11] Постирать кроссовки ⏰22:00

🔁 Привычки:
⏳ [ 1] Omega + D3 08:00
✅ [ 3] Вакуум 08:00
✅ [10] Приседания 08:00

Итого: 2/10
```

## Архитектура

- **Общая утилита:** `~/.hermes/skills/brief/obsidian_utils.py`
  - `write_note(subpath, content)` — записать файл в vault, БЕЗ git-коммита
  - `commit_all(msg)` — один `git add -A && git commit -m "msg"` (push через post-commit hook)
  - `save_note(subpath, content)` — устаревшая, только для обратной совместимости
- Скрипт: `~/.hermes/skills/brief/evening-diary-brief/scripts/brief_evening.py`
  - `dotenv_get(key)` — читает .env, пропуская `#` строки
  - `run_t(*args)` — обёртка над `t`
  - `build_brief_msg()` — форматирует сырые выводы в сообщение
  - `send_telegram(text)` — отправка через urllib.request + Bot API
  - `cron_mode()` — сбор + отправка + Obsidian
  - `interactive_mode()` — TTY: интерактивный опрос через input()
  - `main()` — --send → cron_mode; isatty → interactive_mode; иначе cron_mode
- **Git post-commit hook:** `~/hermes-vault/.git/hooks/post-commit`
  - Автоматический `git push origin main` после каждого коммита
  - Страхует от забытого push'а
- **Периодические задачи:** `brief_evening.py` вызывает `t periodic` и отображает 🔄 секцию после привычек (во всех режимах: build_brief_msg, save_diary_template, interactive_mode)
- Заметки: `~/hermes-vault/Дневник/YYYY-MM-DD.md`
- Демон: `task-manager` (systemd, ~/.hermes/skills/productivity/task-manager/)

## Troubleshooting

**Отправка в Telegram не работает**
Проверь `.env`: TELEGRAM_BOT_TOKEN и TELEGRAM_HOME_CHANNEL (не закомментированы).
`dotenv_get()` игнорирует строки с `#`.
Запуск: `python3 brief_evening.py --send`.

**Вывод без ID-шников**
Самая частая ошибка. Правило: всегда сырой stdout `t list` и `t habits`.
Не переписывать, не фильтровать, не переставлять строки.
Итог (`Итого: X/Y`) можно добавить отдельной строкой после сырого вывода.

## Pitfalls

1. **НЕ переформатировать вывод `t list` / `t habits`** — теряются ID, счётчики, строки. Всегда сырой stdout.
2. **НЕ пропускать вопросы рефлексии** — пользователь хочет accountability partner, не просто логгер. Все 5 вопросов обязательны.
3. **Перенос задачи:** `t postpone <id>` — перенос на завтра. `t postpone <id> -d YYYY-MM-DD` — на конкретную дату. Не cancel + add.
4. **Нет `sqlite3` CLI** — только через Python `sqlite3` или `t`.
5. **Не создавать отдельные скрипты** — чинить существующий `brief_evening.py`, а не плодить файлы.
6. **Проверять patch на Python-скриптах** — patch tool иногда ломает кавычки (`"` → `\"`). После редактирования `t` или `brief_evening.py` всегда проверять синтаксис.
7. **ID привычек могут быть НЕ последовательны** — в выводе `t habits` могут быть пропуски (напр. `[1]...[8]`, `[10]` без `[9]`). Пропущенный ID — это привычка «не по расписанию» (выполнена вне графика или удалена). `t habit-done <id>` использует реальный DB-айдишник, а не порядковый номер. **Ошибка:** пользователь говорит «отметь 9», думая что это порядковый номер, а `[9]` в списке нет → `t habit-done 9` отметит скрытую привычку.

   **Решение:** не принимать ID на слух — всегда сверяться с сырым stdout. Если видишь разрыв в нумерации — не используй пропущенные номера. После массового `t habit-done` перепроверять `t habits`.
8. **Не делать микрокоммиты на каждый файл.** `obsidian_utils.py` предоставляет `write_note()` (только запись) и `commit_all()` (один коммит на все изменения). Если нужно сохранить несколько файлов (например, text.md + grammar.md + vocabulary.md + state.yaml):
   - Пиши всё через `write_note()`
   - Потом один `commit_all("осмысленное сообщение")`
   - Post-commit hook сделает push сам

   **Ошибка:** вызов `save_note()` для каждого файла → N микрокоммитов с бесполезными сообщениями и N push'ей.

9. **`t habit-done` НЕ принимает несколько ID одной командой.** `t habit-done 1 5 6` → `unrecognized arguments`. Нужно цепочкой: `t habit-done 1 && t habit-done 5 && t habit-done 6`, либо вызывать каждый ID отдельным `terminal()`.

   **Симптом:** первый вызов падает с `usage: t [-h] {add,done,cancel,list,...}` и `unrecognized arguments`.

10. **`obsidian_utils.py` не создан в системе** — описанные утилиты `write_note()` и `commit_all()` отсутствуют. 
    - `~/.hermes/skills/brief/obsidian_utils.py` не существует
    - `~/.hermes/skills/brief/` директория тоже отсутствует
    - **Решение:** сохранять заметку через `write_file()` напрямую, коммитить вручную:
      ```bash
      cd ~/hermes-vault && git add -A && git commit -m "diary YYYY-MM-DD"
      ```
    - Post-commit hook (если настроен) делает push автоматически.

## История изменений

- v1.2: Добавлен pitfall #7 — ID привычек не последовательны, риск отметить скрытую привычку «не по расписанию». Добавлено предупреждение в шаг 5 интерактивного режима.
- v1.1: Починен send_telegram (dotenv_get + urllib.request вместо curl/xitter),
  добавлен --send флаг, build_brief_msg(). Добавлен обязательный цикл рефлексии.
- v1.0: Первый релиз.
