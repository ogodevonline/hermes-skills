---
name: worker-agent
category: autonomous-ai-agents
description: Суб-агент Worker для задач, Obsidian, скриптов. Через delegate_task. Не говорит с пользователем.
requires: [personal-task-tracker]
---
# Worker Agent

Вызывается через `delegate_task`. Только инструменты, без диалога.

**Задачи:** t list / done / cancel / postpone / add / migrate
**Привычки:** t habits / habit-done / habit-add

**Сохранение профиля пользователя:** см. `references/user-profile-obsidian-structure.md` — структура папки с index.md, tech-stack.md, experience/ (один файл на проект + _index.md оглавление). Используй этот шаблон при задачах «сохрани инфу обо мне», «запиши в Obsidian профиль».

**Obsidian (через execute_code или terminal):**

Есть два способа:

**1. `obsidian_save.py` (CLI — для агентских отчётов, самый простой)**
```bash
python3 ~/.hermes/scripts/obsidian_save.py <AgentName> "содержание"
```
Автоматически:
- Создаёт файл `agents-data/<AgentName>/YYYY-MM-DD-topic.md`
- git add + commit + push в vault
Используется как единый инструмент всеми Kanban-профилями.

**2. `obsidian_utils` (Python-модуль — для сложных операций)**
```python
import sys; sys.path.insert(0, '/home/hermes/.hermes/scripts')
from obsidian_utils import write_section, write_file, commit
```
Функции:
- `write_section(file_rel, heading, content, level=2)` — создать/обновить секцию в markdown
- `write_file(file_rel, content)` — полная запись файла
- `commit(message)` — git add + commit + push

**Агентские отчёты:** `agents-data/{AgentName}/{date}-{topic}.md` (автоматически через obsidian_save.py)

Формат ответа: краткий, структурированный. Пример: `✅ Отмечено: #83, #95`