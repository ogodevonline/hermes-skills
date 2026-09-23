# Kanban list status mismatch — completed tasks shown as running

**Date observed:** 2026-05-29
**Bug task:** `t_995ff2b6`
**Assignee:** debugger

## Symptom

`hermes kanban list` shows a task with `● running` indicator, but `hermes kanban show <id>` reveals `status: done` with a `completed:` timestamp.

## Affected tasks (29 May 2026)

| Task | Real status | List display | Completed at |
|------|-------------|--------------|-------------|
| t_f50c2852 | done | running (●) | 2026-05-29 19:43 |
| t_24b75516 | done | running (●) | 2026-05-29 19:43 |

## Impact

- Orchestrator thinks tasks are actively working and waits
- User thinks tasks haven't started and re-requests
- Risk of duplicate task creation if user assumes the task never dispatched

## Workaround

Always verify ambiguous running tasks with `hermes kanban show <id>` before acting. If confirmed done, archive immediately.

## Root cause

Under investigation — see `t_995ff2b6` for debugger analysis.