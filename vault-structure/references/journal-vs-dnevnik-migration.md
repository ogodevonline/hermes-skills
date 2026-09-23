# Migration: Дневник → Journal (завершена 13.06.2026)

**Было:** В vault две директории дневников:
- `Дневник/` — активная (morning ritual, evening diary)
- `Journal/` — 46 старых файлов (предыдущая конвенция)

**Сделано:** Полная миграция Дневник/ → Journal/
1. Файлы из `Дневник/` перенесены в `Journal/`:
   - `2026-06-11.md` — смержен (утро из Journal/ + вечер из Дневник/)
   - `2026-06-12.md` — скопирован
   - `2026-06-13.md` — скопирован
   - `README.md` — перезаписан
2. `Дневник/` удалён
3. Все навыки и скрипты обновлены (`Дневник/` → `Journal/`):
   - vault-structure, morning-ritual, evening-diary-brief
   - vault-frontmatter, universal-planner, hermes-agent-skill-authoring
   - planning.py, health_check.py, life-planning/scripts/planning.py
4. Git commit: `migrate: Дневник/ → Journal/, merge files, update all skills refs`

**Итог:** `Journal/` — каноничная директория, 48 файлов.
