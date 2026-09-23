# Failure Pattern: Duplicate Fan-Out (28 May 2026)

## What happened

User asked for a self-improver analysis of researcher behaviour. Orchestrator created:

1. `t_e5c0347e` — self-improver (correct first attempt)
2. `t_78592b1a` — self-improver (duplicate, when user asked about model)
3. `t_bf307eb2` — researcher (wrong profile, when user questioned sonnet → deepseek)

All three ran concurrently, flooding Kanban. User rage: "ну не дибил ли", "все задачи падают в блок".

## Root cause

Orchestrator did NOT:
- Block the old task before creating a new one when user asked to change profile
- Check `hermes kanban list` to see if a task on the same topic was already running
- Verify after dispatch that only one task was running

## Correct sequence

1. User questions profile choice
2. If they want a different profile: BLOCK the running task first: `hermes kanban block <id> "reassigned to <new-profile>"`
3. THEN create new task on correct profile
4. Verify with `hermes kanban list` that only one task per topic runs

## Prevention

See "CRITICAL — Never create duplicate tasks on the same topic" and "Profile swap protocol" in the kanban-orchestrator SKILL.md.