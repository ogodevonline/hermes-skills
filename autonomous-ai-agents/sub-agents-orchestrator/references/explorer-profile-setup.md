# Explorer Profile Setup

Создан 05.06.2026. Read-only codebase analyst, аналог Kilo `explore` subagent.

## Конфиг (`~/.hermes/profiles/explorer/config.yaml`)

```yaml
model:
  default: deepseek/deepseek-v4-flash
  provider: kilocode
agent:
  max_turns: 10
  reasoning_effort: low
  disabled_toolsets: []
toolsets:
  - file
  - terminal
  - session_search
```

**Ключевые решения:**
- Только `file`, `terminal`, `session_search` — никакого `web`, `kanban`, `skills`, `memory`
- `max_turns: 10` — быстрые задачи, если нужно больше → Kanban → coder
- `reasoning_effort: low` — дешевле и быстрее

## SOUL.md

Содержит инструкции по: search_files (glob/ripgrep), read_file, terminal (только git).

**Запреты:**
- ❌ Не использовать rg/fd/fzf в терминале — их нет на сервере
- ❌ Не писать/редактировать файлы
- ❌ Не искать в интернете

## Использование

Запуск через `delegate_task` (не Kanban — быстрые задачи):

```python
delegate_task(
    goal="Найди где используется функция X",
    context="Проект в /home/hermes/Y.",
    toolsets=["file", "terminal"]
)
```
