---
name: hermes-hub
category: productivity
description: "Единая сводка задач, целей, сфер и проблем. Команды: hermes-hub (CLI), /hub (чат)."
---
# Hermes Hub

**Команды:** `hermes-hub` (CLI), `/hub` (чат)
**Скрипт:** `~/.local/bin/hermes-hub`

**Источники:** ⚠️ С 24.09.2026 задачи/привычки — ТОЛЬКО Google Tasks: читать `/usr/bin/python3 ~/.hermes/scripts/brief_data.py` (PYTHONPATH=/home/hermes/.local/lib/python3.12/site-packages); task_display/tasks.db/`t` мёртвы. → goals.yaml (цели) → planning.py (сферы)

**Известная проблема:** planning.py отдаёт `sphere_summary` (dict), hub ожидает `sphere_trends` (list) → блок сфер всегда 0. Согласование в шаге 9.