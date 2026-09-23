# obsidian_save.py — универсальное сохранение в Obsidian

## Команда

```bash
# Вариант A — аргументом (для короткого текста)
python3 ~/.hermes/scripts/obsidian_save.py <AgentName> "содержание отчёта"

# Вариант B — через stdin (рекомендуется, для длинного/многострочного)
echo "содержание отчёта" | python3 ~/.hermes/scripts/obsidian_save.py <AgentName> -

# Вариант C — из переменной (для subprocess.run в коде)
python3 ~/.hermes/scripts/obsidian_save.py <AgentName> -
```

Скрипт сам:
1. Создаёт файл `agents-data/<AgentName>/YYYY-MM-DD-topic.md` в `~/hermes-vault/`
2. git add + commit + push

## Агенты и их директории

| Профиль | AgentName | Директория |
|---------|-----------|------------|
| architect | Architect | `agents-data/Architect/` |
| coder | Coder | `agents-data/Coder/` |
| debugger | Debugger | `agents-data/Debugger/` |
| orchestrator | Orchestrator | `agents-data/Orchestrator/` |
| prompt-engineer | PromptEngineer | `agents-data/PromptEngineer/` |
| researcher | Researcher | `agents-data/Researcher/` |
| reviewer | Reviewer | `agents-data/Reviewer/` |
| self-improver | SelfImprover | `agents-data/SelfImprover/` |
| skill-improver | SkillImprover | `agents-data/SkillImprover/` |
| worker | Worker | `agents-data/Worker/` |

## Когда сохранять

Перед `kanban_complete` — как последний шаг. Не завершай задачу без сохранения.

## Кому нужно

Каждый Kanban-профиль (и delegate_task суб-агент) должен сохранять свои результаты в Obsidian перед завершением.
