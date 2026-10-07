---
name: hermes-hub
category: productivity
description: "Единая сводка задач, целей, сфер и проблем. Команды: hermes-hub (CLI), /hub (чат)."
---
# Hermes Hub

**Команды:** `hermes-hub` (CLI), `/hub` (чат)
**Скрипт:** `~/.local/bin/hermes-hub`

**Источники:** ⚠️ С 24.09.2026 задачи/привычки — ТОЛЬКО Google Tasks: читать через
`get_service()` из `~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py`
(списки `⛅ TODAY` / `📥 BACKLOG` / `🌱 HABITS`); для готового текстового брифа —
`/usr/bin/python3 ~/.hermes/scripts/brief_data.py`
(PYTHONPATH=/home/hermes/.local/lib/python3.12/site-packages). task_display/tasks.db/`t` мёртвы.
→ `~/hermes-vault/Goals.md` (цели; парсер `~/.hermes/scripts/goals_md.py`, формат — секции
`### <goal_id> · Название` + строки `- Область: … · Срок: … · Статус: …` и `- Метрики: k: v`) → planning.py (сферы)

**Известные проблемы:**
1. planning.py отдаёт `sphere_summary` (dict), hub ожидает `sphere_trends` (list) → блок сфер всегда 0. Согласование в шаге 9.
2. Локальный `~/.local/bin/hermes-hub` всё ещё напрямую открывает `tasks.db` в `get_stats()` (устаревший путь) — файл вне этого переноса, требует отдельной правки владельцем.
