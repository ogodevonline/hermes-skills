# KANBAN_GUIDANCE Block Trap — Root Cause Analysis & Fix

> Session: 28 May 2026. User reported Kanban agents stuck in `blocked` instead of completing with errors.
> Fix applied same session — three patches to `agent/prompt_builder.py`.

## The Problem

When a Kanban agent encounters an error (API failure, parse error, timeout, missing data), it calls `kanban_block()` instead of `kanban_complete(error_summary)`. This:
- Leaves the task stuck in `blocked` status
- Downstream tasks (with parent links) never start — they wait for parent to reach `done`
- The entire pipeline stalls until a human manually unblocks

## Root Cause: KANBAN_GUIDANCE in `agent/prompt_builder.py`

The lifecycle instructions in `KANBAN_GUIDANCE` (auto-injected system prompt for EVERY worker) contain three problematic instructions:

### 🔴 Instruction 1 — Line 238 (worst offender)

```python
"- Do not complete a task you didn't actually finish. Block it.\n"
```

**How agents interpret it:** "I got an error → I didn't finish → I must block."
**What they should do:** "I got an error → I should complete with a clear error summary in metadata."

**Why it's the worst:** It's a blanket rule with no exception for error cases. It explicitly tells agents to BLOCK on any incomplete outcome. There's no nuance about "partial success = still finish."

### 🔴 Instruction 2 — Lines 212-219 (review-required trap)

```python
"Exception: if your output is a code change that needs human review "
"before counting as merged/done (most coding tasks), drop the "
"structured metadata (changed_files / tests_run / diff_path) into a "
"`kanban_comment` first, then end with "
"`kanban_block(reason=\"review-required: <one-line summary>\")` so a "
"reviewer can approve+unblock or request changes."
```

**Problem:** This tells coders to block after writing code. This is incompatible with pipeline mode where a downstream reviewer task is parent-linked. The dependency engine only promotes children when parent reaches `done`, so a `blocked` parent never triggers the reviewer.

**The irony:** This instruction exists to ensure code gets reviewed. But in a pipeline setup, the downstream reviewer task IS the review mechanism — blocking only breaks the chain.

### 🟡 Instruction 3 — Lines 202-205 (ambiguous ambiguity)

```python
"4. **Block on genuine ambiguity.** If you need a human decision you cannot "
"infer (missing credentials, UX choice, paywalled source, peer output you "
"need first), call `kanban_block(reason=\"...\")` and stop. Don't guess. "
"The user will unblock with context and the dispatcher will respawn you.\n"
```

**Problem:** The intent is correct (human-decidable ambiguity), but combined with Instruction 1, agents interpret technical errors as "ambiguity" and block. The examples don't include technical failures, but the broad framing invites over-blocking.

## Why SOUL.md Fixes Are Not Enough

Previous analysis blamed this on coder/reviewer SOUL.md files saying "block when done." But:
- None of the user's SOUL.md files contained `kanban_block`
- The behavior was universal across ALL profiles
- The body instruction workaround (`"kanban_complete when done"`) sometimes works, sometimes doesn't — agents trust system prompt over task body

The real root cause is in `KANBAN_GUIDANCE` in the codebase, not in SOUL.md files.

## The Fix (applied 28 May 2026)

Three patches applied to `agent/prompt_builder.py`:

### Patch 1 — Line 238 (fix the blanket block rule)

**Was:**
```python
"- Do not complete a task you didn't actually finish. Block it.\n"
```

**Became:**
```python
"- If you hit an error, complete with error summary + metadata in "
"`kanban_complete`. Only block for human-decidable choices (missing "
"credentials, UX decisions), never for technical errors.\n"
```

### Patch 2 — Lines 212-219 (fix review-required block)

**Was:**
```python
"Exception: if your output is a code change that needs human review "
"before counting as merged/done (most coding tasks), drop the "
"structured metadata (changed_files / tests_run / diff_path) into a "
"`kanban_comment` first, then end with "
"`kanban_block(reason=\"review-required: <one-line summary>\")` so a "
"reviewer can approve+unblock or request changes. Reviewing-then-"
"completing is more honest than auto-completing work that still needs "
"eyes on it.\n"
```

**Became:**
```python
"For code changes: drop structured metadata (changed_files / tests_run / "
"diff_path) into a `kanban_comment` first, then `kanban_complete` with "
"summary. The review pipeline is managed via parent links, not via block. "
"Do NOT block — completing lets downstream tasks proceed.\n"
```

### Patch 3 — Lines 202-205 (clarify ambiguity)

**Was:**
```python
"4. **Block on genuine ambiguity.** If you need a human decision you cannot "
"infer (missing credentials, UX choice, paywalled source, peer output you "
"need first), call `kanban_block(reason=\"...\")` and stop. Don't guess. "
"The user will unblock with context and the dispatcher will respawn you.\n"
```

**Became:**
```python
"4. **Block only on genuine human-decidable ambiguity.** If you need a human "
"decision you cannot infer (missing credentials, UX choice, paywalled source, "
"peer output you need first), call `kanban_block(reason=\"...\")` and stop. "
"Don't guess. Technical errors (API failures, parse errors, timeouts, unexpected "
"responses) are NOT ambiguity — complete with error summary in metadata. "
"The user will unblock with context and the dispatcher will respawn you.\n"
```

### Verification

```python
# Import test — confirm KANBAN_GUIDANCE compiles and contains new semantics
from agent.prompt_builder import KANBAN_GUIDANCE
assert "Block only on genuine human-decidable ambiguity" in KANBAN_GUIDANCE
assert "Technical errors" in KANBAN_GUIDANCE
assert "hit an error, complete with error summary" in KANBAN_GUIDANCE
assert "Do NOT block" in KANBAN_GUIDANCE
assert "Do not complete a task you didn't actually finish" not in KANBAN_GUIDANCE
```

## Diagnosis Checklist

If workers still block on errors after this fix:
1. Verify the fix was deployed: `grep -n "Do not complete a task you didn't actually finish" /home/hermes/.hermes/hermes-agent/agent/prompt_builder.py` should return empty
2. Check if there's a stale `.pyc` cache: `find ~/.hermes/hermes-agent -name "*.pyc" -delete`
3. Verify the new pattern: `grep -n "hit an error, complete" /home/hermes/.hermes/hermes-agent/agent/prompt_builder.py` should find the replacement
4. If the old patterns still exist, reapply patches (see above)

## New Orchestrator Pattern: Direct Analysis on Kanban-blocking Problems

When the user reports Kanban tasks blocking, and the fix IS about Kanban behavior:
- **Do NOT create a Kanban task to investigate** — that task would also block, creating a meta-block loop
- **Do NOT use Claude Sonnet agents** (skill-improver, refactoring-guru) — they're expensive and not needed for a root-cause code read
- **Analyze directly yourself:** read `prompt_builder.py` KANBAN_GUIDANCE, check SOUL.md files, grep for `kanban_block`, compile a fix plan, show user → get approval → apply patches

**Why:** The task to fix the Kanban lifecycle will itself run inside that lifecycle. If the lifecycle tells agents to block on errors, the fixer agent will also block. Break the cycle by working directly.

## Related Files

- `agent/prompt_builder.py` — KANBAN_GUIDANCE definition (lines 175-242 as of fix)
- `agent/agent_init.py` — where KANBAN_GUIDANCE is resolved per agent (line 935)
- `agent/system_prompt.py` — where KANBAN_GUIDANCE is injected into system prompt (lines 34, 120)