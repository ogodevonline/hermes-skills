# prefill_messages_file — Permanent Behavioral Rules in Hermes

## What

`prefill_messages_file` is a Hermes config option that injects a file into EVERY session as a prefill message. Unlike skills (optional to load) or memory (can be compressed/removed), this is **permanent** — it's part of the agent's base prompt, always present, cannot be forgotten.

## When to Use

- Behavioral rules that must apply **in every session, without exception**
- Rules that override or supplement the agent's built-in behavior
- Anything the user has called "soul" — non-negotiable core behavior

## How to Set

```bash
hermes config set prefill_messages_file /path/to/rules.md
```

Verify:
```bash
grep "prefill_messages_file" ~/.hermes/config.yaml
```

## What NOT to Put Here

- Task-specific instructions → skill
- Environment facts → memory
- One-time setup notes → memory or delete

Only permanent, session-independent behavioral rules.

## Current Rules (30.05.2026 — polished by prompt-engineer)

File: `~/.hermes/approval-rules.md`

Covers:
1. **Plan → Show → OK → Execute** — любые действия (кроме исключений §5) только с OK
2. **One step at a time** — задача → атомарные шаги → после каждого отчёт по §4 и OK
3. **No surprises** — навыки, кроны, файлы, процессы только с OK. Ошибка/таймаут — сразу сообщи
4. **Report format**: ✅ Шаг N/N, 📊 Токены, 📁 Файлы, ⏱ Время, ❓ Продолжить?
5. **Exceptions (без OK)**: чтение/поиск, время/дата, ответ фактом

Применяется через `prefill_messages_file` в config.yaml.

## Alternative Approaches (Rejected)

| Approach | Problem |
|----------|---------|
| Skill | Optional to load, can be forgotten |
| Memory | Compressed/removed when full, not permanent |
| System prompt patch | Overwritten on update, fragile |