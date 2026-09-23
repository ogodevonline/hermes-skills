# Kanban Artifact Fallback Patch

## What

Patch in `gateway/run.py` — `_deliver_kanban_artifacts`. When a Kanban task completes with `summary` but no `artifacts`, the gateway saves the summary to a temp `.md` file and sends it as a native attachment. This prevents Telegram truncation (~200 chars).

## Where

**File:** `~/.hermes/hermes-agent/gateway/run.py`
**Lines:** 5662-5674 (inside `_deliver_kanban_artifacts`)

```python
# 4. Fallback: if no file paths found but there's a summary,
#    save it as a temp .md file and deliver that instead.
if not candidates and isinstance(summary, str) and summary:
    task_id = getattr(task, "id", None) if task is not None else None
    fallback_path = f"/tmp/kanban-{task_id or 'unknown'}-result.md"
    try:
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(summary)
        _add(fallback_path)
    except (OSError, IOError) as exc:
        logger.warning("kanban notifier: fallback summary-to-md write failed: %s", exc)
```

## Postinstall auto-apply (survives `hermes update`)

**Script:** `~/.hermes/scripts/postinstall-apply-artifact-fallback.py`
**Trigger:** post-merge git hook in `~/.hermes/hermes-agent/.git/hooks/post-merge`

The script checks for the marker comment `"Fallback: if no file paths"` — if missing, re-applies the patch.

## Critical: conditions for the patch to work

1. **Notify-subscribe required.** The fallback only fires for subscribed tasks. `notify-subscribe` is per-task, not global.
2. **Gateway restart required after code change.** The patch is on disk; the running gateway has old code in memory. `systemctl --user restart hermes-gateway` is mandatory.
3. **Only fires on `completed` event.** `crashed`, `gave_up`, `timed_out` don't trigger artifact delivery.

## Before this patch

Kanban tasks without `artifacts=` sent only text — Telegram truncated to ~200 chars. The fix was either (a) always write `artifacts=['/tmp/{TASK_ID}-result.md']` in every task body, or (b) patch the gateway. We did (b) + (a) as belt-and-suspenders.
