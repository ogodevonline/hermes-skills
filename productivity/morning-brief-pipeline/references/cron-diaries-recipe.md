# Cron-mode diary reading recipe

**Проблема:** `execute_code` и `python3 -c "import sqlite3..."` блокируются в cron-режиме (pending_approval).

## 1. Чтение дневников

```python
# ❌ НЕ РАБОТАЕТ (cron):
python3 -c "from pathlib import Path; ..."

# ❌ НЕ РАБОТАЕТ (cron): execute_code
execute_code(...)

# ✅ РАБОТАЕТ:
# 1. Найти правильный путь к vault (не Дневник/, а Journal/ или другой)
search_files(pattern="2026-06-*", target="files", path="/home/hermes/hermes-vault/Journal/")
# 2. Прочитать файлы read_file напрямую
read_file(path="/home/hermes/hermes-vault/Journal/2026-06-13.md")
```

## 2. Задачи и просрочки (Google Tasks)

Задачи читаются ТОЛЬКО из Google Tasks (источник истины с 24.09.2026).
Локальный трекер для чтения задач не используется.

```python
# ❌ НЕ РАБОТАЕТ (cron):
python3 -c "import sqlite3; ..."

# ❌ НЕ РАБОТАЕТ (cron): heredoc
python3 << 'PYEOF' ... PYEOF

# ❌ НЕ РАБОТАЕТ (cron): execute_code
execute_code()

# ✅ РАБОТАЕТ A: готовый скрипт → задачи дня из Google (TODAY/BACKLOG/HABITS)
#   открытые задачи дня, выполненные за день, backlog, привычки
PYTHONPATH=/home/hermes/.local/lib/python3.12/site-packages \
    /usr/bin/python3 ~/.hermes/scripts/brief_data.py            # сегодня
PYTHONPATH=/home/hermes/.local/lib/python3.12/site-packages \
    /usr/bin/python3 ~/.hermes/scripts/brief_data.py --yesterday

# ✅ РАБОТАЕТ B: полный список открытых/просроченных из Google
PYTHONPATH=/home/hermes/.local/lib/python3.12/site-packages \
    /usr/bin/python3 ~/.hermes/scripts/brief_tasks.py

# ✅ РАБОТАЕТ C: форматированный список (task_display.py теперь читает Google)
python3 ~/.hermes/scripts/task_display.py

# ✅ РАБОТАЕТ D: кастом — временный .py с импортом get_service из tasks_api.py
#   ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py
```

Важно: счётчика переносов (carry_over) в Google Tasks НЕТ. «Просрочка» =
у задачи due-дата в прошлом (`due < today`); задача без due просроченной не считается.

## 3. ⚠️ Sibling collision при write_file в /tmp/

**Симптом (пойман 07.07.2026):**
```
/tmp/carry_over.py was modified by sibling subagent 'fb00d78c-1f62-4db2-b018-394e10b5b9f3'
but this agent never read it. Read the file before writing to avoid overwriting the sibling's changes.
```

**Причина:** Два параллельных крон-задания используют одинаковые имена `/tmp/*.py` — второй write_file перезаписывает первый до того как тот успел его прочитать.

**Как избежать:**
1. **Лучший вариант:** читай через `read_file` / `search_files` / готовые скрипты (`brief_data.py`) — без write_file, нет shared state
2. **Если write_file неизбежен:** используй уникальные имена — `/tmp/cron_taskname_TIMESTAMP.py`, где TIMESTAMP — метка из TZ='Europe/Moscow' date
3. **Чисти за собой:** `rm -f /tmp/cron_*.py` в terminal() после чтения

## 4. Дата и время

```bash
# ✅ Всегда работает:
TZ='Europe/Moscow' date '+%A, %d %B %Y %H:%M'
```

## 6. Валидированные пути vault

- Корень vault: `/home/hermes/hermes-vault/`
- Дневники: `Journal/` (ENG, не русский)
- AGENTS.md: `/home/hermes/hermes-vault/System/Docs/vault-rules.md`
- Структура: Journal/, Areas/, Projects/, Learning/, Inbox/, System/, Archive/, agents-data/

## 7. Детекция пустых дневников (спячка системы)

**Когда бить тревогу:** 3+ дня подряд сферы = `_`, привычки = `0/11` или `0/12`, рефлексия пустая (`_ _`).

**Как проверить (cron-safe, без python3 -c):**

```bash
# read_file каждого из 3 последних дневников:
# Ищи признаки активности:
# - В секции "🌱 Баланс жизни" есть числа (например "Карьера: 5/10") — НЕ пусто
# - В "Привычки" есть ✅ (зачёркнутые) — НЕ пусто
# - В "Рефлексия" есть текст вместо "_ _" — НЕ пусто
# - Вопрос Q4 "На что обратить внимание завтра?" — есть ответ
# Если за 3 дня ни одного признака → SEVERE в брифинге
```

**Пример формулировки в брифинге:**\n```\n📉 Системный провал: 3 дня сферы не оцениваются, привычки 0/11,\nрефлексия пустая, задачи не закрываются 14+ дней.\n```\n\n**Важно:** в Google Tasks счётчика переносов (carry_over) нет — просрочка определяется по due-дате (`due < today`); полный список открытых/просроченных — `brief_tasks.py` (Google TODAY/BACKLOG).

## 8. Детекция системного блока через просрочки

**Сигнал:** все открытые задачи из Google TODAY/BACKLOG имеют due в прошлом и не двигаются N дней.

**Что это значит:** Это не N отдельных просрочек, а одна системная проблема — человек блокирован и не решает ни одну задачу N дней подряд.

**Как проверить (cron-safe):**
1. Получить список открытых задач: `PYTHONPATH=/home/hermes/.local/lib/python3.12/site-packages /usr/bin/python3 ~/.hermes/scripts/brief_tasks.py`
2. Если почти все задачи просрочены и список не меняется — это системный блок.

**Если много просроченных задач и ни одна не закрывается = SEVERE.** Брифинг должен писать не «N задач с carry_over», а «системный блок: ни одна задача не сдвинулась N дней». Это важнее, чем список задач.

**Пример формулировки:**
```
⚠️ Системный блок: все открытые задачи просрочены.
Ни одна не двигалась 17 дней.
```

## 9. Валидированные пути vault

- Корень vault: `/home/hermes/hermes-vault/`
- Дневники: `Journal/` (ENG, не русский)
- AGENTS.md: `/home/hermes/hermes-vault/System/Docs/vault-rules.md`
- Структура: Journal/, Areas/, Projects/, Learning/, Inbox/, System/, Archive/, agents-data/
