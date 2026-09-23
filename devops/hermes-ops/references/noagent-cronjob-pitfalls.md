# no_agent Cronjob Pitfalls

Session: 2026-06-14 — weekly-self-improvement fix

## Problem

Cronjob `weekly-self-improvement` failed with:
```
RuntimeError: [Errno 32] Broken pipe
```

This was a pure LLM-driven job with a simple prompt:
```
Напиши пользователю короткое сообщение: «Неделя прошла. Может, пора что-то улучшить в профилях/навыках/воркфлоу? Решай сам.»
```

Broken pipe was a transient scheduler-level error — retry fixed it.

## Fix

User wanted no LLM at all for a static text reminder:

1. Created `~/.hermes/scripts/weekly_self_improvement.sh`:
   ```bash
   #!/usr/bin/env bash
   echo "Неделя прошла. Может, пора что-то улучшить в профилях/навыках/воркфлоу? Решай сам."
   ```

2. Converted job to `no_agent=true, script=weekly_self_improvement.sh`

## The Trap: `run` doesn't deliver for no_agent

**This wasted several rounds.** After setting `no_agent=true`, calling `cronjob(action='run', job_id=...)` showed:
- `last_status: ok`
- **No message delivered** to user

This is NOT a bug — it's by design: `run` is meant to test execution, not delivery. Only the scheduled cron tick actually delivers stdout.

## Deliver target confusion

Tried in sequence:
1. `deliver: origin` (default from update) — didn't deliver on `run`
2. `deliver: telegram` — didn't deliver on `run`  
3. `deliver: telegram:350262645` — didn't deliver on `run`
4. `send_message(action='send', target='telegram:350262645')` — ✅ WORKED (proves channel is fine)
5. Recreated job with `deliver: origin` — pending scheduled run on 21.06

Verdict: `origin` is the proven value. All other no_agent cronjobs (lunch-reminder, sync-profile-skills, gotham-nightly) use `origin` and deliver fine via scheduled execution.

## Lessons

1. `cronjob(action='run')` for no_agent jobs = execution test only, no delivery
2. Use `origin` for deliver target on Telegram-sourced jobs
3. Static text reminders should be no_agent — 0 tokens vs ~500-2000 per LLM run
4. Transient `Broken pipe` on cron can be ignored if retry succeeds
