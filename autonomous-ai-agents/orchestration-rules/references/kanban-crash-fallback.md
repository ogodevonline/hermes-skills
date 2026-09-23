# Kanban Crash Fallback: Dispatch Failed, What Now

## Симптомы

- `hermes kanban dispatch --max 1` возвращает: `Crashed: 1, t_<id>`
- В логе задачи (`cat ~/.hermes/kanban/logs/<task_id>.log`): `Error: Unknown skill(s): <skill-name>`
- Задача перезапускается бесконечно (dispatcher → crash → promote → spawn → crash)

## Root Cause (90% случаев)

**Скилл `kanban-worker` (или другой) отсутствует в профиле воркера.**

`_default_spawn()` (kanban_db.py:5766) добавляет `--skills kanban-worker` в команду запуска worker'а. Если скилл физически не существует в `~/.hermes/skills/` — Hermes падает с `exit code 1` при старте.

## Процедура

1. **Проверь лог:**
   ```bash
   cat ~/.hermes/kanban/logs/<task_id>.log
   ```

2. **Если `Error: Unknown skill(s): kanban-worker`:**
   - Найди bundled-версию скилла в репозитории: `ls ~/.hermes/hermes-agent/skills/devops/kanban-worker/SKILL.md`
   - Скопируй в глобальный skills:
     ```
     mkdir -p ~/.hermes/skills/devops/kanban-worker/
     cp ~/.hermes/hermes-agent/skills/devops/kanban-worker/SKILL.md ~/.hermes/skills/devops/kanban-worker/SKILL.md
     ```
   - Категория `devops` обязательна — `_kanban_worker_skill_available()` ищет именно `skills/devops/kanban-worker/SKILL.md`
   - Если скилла нет нигде — создай минимальный SKILL.md с frontmatter (name, description, version)
   - **НЕ создавай дубликат в `~/.hermes/skills/kanban-worker/` (без категории) — это вызовет collision: skill_view найдёт 2 кандидата и вернёт «Ambiguous skill name»**
   - Проверь что заработало: `hermes --skills kanban-worker chat -q "hello"` (должен стартовать без ошибки)
   - Проверь для каждого профиля: `hermes -p <profile> --skills kanban-worker chat -q "hello"`
   - Архивируй старые крашнутые задачи: `hermes kanban archive <task_id>`

3. **Если ошибка другая (import error, profile not found):**
   - Проверь `~/.hermes/profiles/<assignee>/config.yaml`
   - Проверь `~/.hermes/profiles/<assignee>/skills/` — есть ли симлинки

4. **Fallback: пока Kanban не починен, используй delegate_task:**
   ```python
   delegate_task(
       goal="…",
       toolsets=["terminal", "file"],
   )
   ```

5. **Создай задачу на починку Kanban** (если ещё не создана): debugger с планом фикса.

## Профилактика

Прежде чем создавать Kanban-задачу с `--skill <name>` — проверь, что навык есть в профиле воркера:
```bash
ls ~/.hermes/profiles/<assignee>/skills/<category>/<skill-name>/
```
Если нет — не используй `--skill`. Без флага `--skill` Kanban worker работает из коробки.