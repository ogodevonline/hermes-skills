# Research: Best Patterns & Prompts for Hermes Agent — 2026-05-30

Исследование лучших практик для AI-агентов, применимых к Hermes Agent Василия.

## Топ репозиториев

| Ресурс | ⭐ | Применимость | Описание |
|--------|-------|-------------|----------|
| ComposioHQ/awesome-claude-skills | 62.5k | 10/10 | 880+ SKILL.md-совместимых навыков |
| VoltAgent/awesome-agent-skills | 23.6k | 10/10 | 1000+ кросс-платформенных скиллов |
| agentsmd/agents.md | 21.8k | 10/10 | Официальная спецификация AGENTS.md |
| PatrickJS/awesome-cursorrules | 39.8k | 9/10 | 500+ .cursorrules с YAML frontmatter |
| ciembor/agent-rules-books | 1.7k | 9/10 | Clean Code/DDD-правила |
| hesreallyhim/awesome-claude-code | 45.2k | 8/10 | hooks, commands, templates |
| steipete/agent-rules | 5.7k | 7/10 | unified .mdc формат |

## Топ-3 паттерна для Hermes

### 🔴 #1: Approval Loop (Plan→Show→Wait→Execute→Show→Wait→Next)
```
1. ANALYZE — понять запрос, определить шаги
2. PLAN — структурированный план с goal/files/outcome
3. WAIT — "Shall I proceed?" — stop
4. EXECUTE — шаг за шагом, промежуточные результаты
5. VERIFY — самопроверка результата
6. SHOW — показать результат
7. NEXT — "What's next?"
```

### 🟡 #2: Risk-Tiered Approval Gates
- Read-only (низкий) — без OK: чтение, поиск, SELECT
- Reversible (средний) — опционально: создание файлов, commit
- Irreversible (высокий) — обязательно: push, deploy, rm

### 🟢 #3: Multi-Agent Decomposition с Checkpoints
Каждая подзадача = 1 Kanban-тикет (1-2ч), чёткий pass/fail
⚠ Multi-agent деградирует sequential reasoning на 39-70%

## Checkpoint Placement Guide
| Тип | Когда | Пример |
|-----|-------|--------|
| Input Validation | После загрузки | Verify extracted fields |
| Mid-Workflow | Между фазами | Review analysis before action |
| Destructive Gate | Перед необратимым | Approve DELETE/merge/publish |
| Quality Gate | После генерации | Review report before sending |
| Scope Escalation | Новые права | Approve DB write access |

## Ключевые статьи
- Anthropic, "Building Effective Agents" — anthropic.com/research/building-effective-agents
- A/B test compressed agent instructions — dev.to/aws-builders (47% compression works, 55% breaks)
- HITL Patterns (Arun Baby) — 3 паттерна: Approval, Intervention, Clarification
- Mastra: Tool-Level Approval Gates — damiangalarza.com
- VMAO: Plan→Execute→Verify→Replan — arxiv 2603.11445
- OpenClaw System Prompts — gist.github.com/mberman84 — Draft→Show→Confirm→Execute

## Применимо к Василию
- approval-rules.md уже вшит через prefill_messages_file (покрывает #1)
- Risk-Tiered Gates (#2) — частично покрыт, можно усилить
- Multi-agent (#3) — уже работает через Kanban, но только для параллельных задач