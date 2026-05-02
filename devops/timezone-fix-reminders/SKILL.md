---
name: timezone-fix-reminders
title: Timezone Fix for reminders.py
description: Hardcode Europe/Moscow timezone in reminders script to avoid UTC/local mismatches
category: devops
---

## Problem
Reminders script displayed times incorrectly when run under a system with UTC timezone (e.g., Docker container or remote server). Task manager daemon (`task_manager/main.py`) runs in UTC and launches `reminders.py` as a subprocess, causing mismatch between stored task times (Moscow time) and script's local time checks.

## Solution
Hardcode `Europe/Moscow` timezone at the top of `reminders.py`:

```python
import os
import time
os.environ['TZ'] = 'Europe/Moscow'
time.tzset()
```

## Files Modified
- `~/.hermes/skills/productivity/cheap-telegram-reminders/scripts/reminders.py` — added TZ setup before any datetime usage (2026-04-28: miгрирован из ~/.hermes/scripts/)
- `~/.hermes/scripts/reminders.py` — original fix, now deleted after migration

## Result
- Script now correctly compares task reminder times (stored as HH:MM in Moscow time) against current Moscow time
- Works regardless of host system timezone (UTC, local, etc.)
- No need to restart or reconfigure task_manager daemon
- Расписание task_manager в UTC, скрипт форсирует МСК — корректная работа

## ⚠️ Lost-patch trap (apply this checklist after ANY script relocation)

This fix has been **lost twice** during migrations (scripts/ → skills). Always re-check after:

1. Moving `reminders.py` to a new location
2. Renaming the script
3. Migrating between `~/.hermes/scripts/` and skills directories
4. Creating a fresh copy from a template

**Check:** `head -5 ~/.hermes/skills/productivity/cheap-telegram-reminders/scripts/reminders.py | grep TZ`
Should output `os.environ['TZ'] = 'Europe/Moscow'`. If not, re-apply the fix.
