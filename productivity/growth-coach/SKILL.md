---
name: growth-coach
description: Методология Growth Coach — ежедневный и еженедельный анализ опыта, привычек, инструментов, слепых зон.
---
# Growth Coach

Запускается профилем `coach` (cron daily + weekly).

**Daily** (single-pass, без delegate_task):
1. `compress_sessions.py --summarize`
2. Анализ диалогов + 1 web_search
3. Отчёт в Telegram (через cron deliver)

**Weekly** (через Kanban):
T1: researcher (сессии недели) → T2: аудит навыков → T3: research → T4: слепые зоны → синтез → Obsidian + Telegram

## ⚠️ Pitfall: не делай фактических утверждений без верификации

В этом навыке легко сделать ложные заявления о состоянии системы (crontab, файлы на диске, запущенные процессы). **Перед тем как написать "X не работает" / "Y отсутствует" / "Z бито" — верифицируй факты:**
- `crontab -l` — проверить реальные записи в crontab
- `ls /path/to/file` — проверить что файл существует
- `hermes kanban show <id>` — проверить реальный статус задачи
- `grep` в файлах — проверить что конфиг/задача/скрипт реально существуют

Ложные утверждения в отчёте подрывают доверие пользователя. Лучше сообщить "не удалось проверить" чем "это сломано".

## ⚠️ Pitfall: не пиши, что «cron-задачи сломанные», если не проверил

Реальный случай (30.05.2026): Coach Check написал что в crontab 4 мёртвых скрипта (habits_reminder, dinner_reminder, tasks_reminder, study_reminder). На деле crontab был чист — скрипты никогда не существовали. Анализ прошлых сессий дал ложную картину. Коуч убил доверие и был удалён.

Если не можешь проверить — не пиши как факт. Пиши «возможно» / «предположительно».

Скрипты: scripts/compress_sessions.py
Справочник: references/coach-cron-setup.md, references/state-db-schema.md
Памятка: section-analysis в obsidian_utils (daily) / obsidian_utils.write_file (weekly)