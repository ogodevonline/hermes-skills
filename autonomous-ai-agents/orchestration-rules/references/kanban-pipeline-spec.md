# Kanban Pipeline Spec: Plan → Approval → Code → Review

Spec написан prompt-engineer'ом 29.05.2026, сохранён в vault: `~/hermes-vault/agents-data/PromptEngineer/kanban-orchestration-spec.md`

## Pipeline

```
prompt-engineer (plan)
    → [blocked — approval gate: user reads spec, kanban unblock]
coder (implementation)
    → [blocked — review gate: user or reviewer checks]
reviewer (review)
    → done
```

## Как работает

1. **Создаётся задача на prompt-engineer** с телом: описание проблемы, чёткие критерии
2. **prompt-engineer**: пишет spec → создаёт coder-задачу с `initial_status='blocked'` → `kanban_complete`
3. **Пользователь**: читает spec → `hermes kanban unblock t_coder`
4. **coder**: реализует → создаёт reviewer-задачу с `initial_status='blocked'` → `kanban_complete`
5. **Пользователь/reviewer**: проверяет → unblock → reviewer завершает

## Контекст передаётся через
- **body** дочерней задачи: `spec_path`, ключевые требования
- **metadata** родителя: `spec_path`, `coder_task_id`, `reviewer_task_id`
- **comment** на задаче: полный spec текстом (дубль)

## Ключевые правила
- `initial_status='blocked'` на дочерних задачах — пользователь сам unblock
- `idempotency_key` для защиты от дублей при retry
- prompt-engineer НЕ пишет код — только spec
- coder строго по spec — если неполный, kanban_block
- reviewer только проверяет — не чинит