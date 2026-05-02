---
name: interactive-evening-diary
category: productivity
description: Interactive evening diary — task statuses + 5 reflection questions, saves to Markdown.
setup_needed: false
---

# Interactive Evening Diary

## Context
Created per request: evening brief without weather/news, focusing on task statuses and daily reflection.

## Features
- Reads `tasks.yml` (today + tomorrow)
- Interactive mode (TTY): asks for ✅/⏳/❌ per task + 5 reflection questions
- Cron/background mode: forms template with `_ _` answers, tries Telegram, saves locally
- Output: Markdown saved to `~/.hermes/diary/YYYY-MM-DD.md`
- Schedule: cron `0 18 * * *` → 21:00 MSK

## Usage

### Interactive (manual)
```bash
~/.hermes/scripts/brief_evening.py
```

### Cron (auto)
In `~/.hermes/tasks/cronjobs.yml`:
```yaml
- name: Evening Brief
  script: brief_evening
  schedule: "0 18 * * *"
  description: Evening diary at 21:00 MSK
  enabled: true
```

## Output Format
```markdown
# 📖 Evening Diary
**26 April 2026**

## 📋 Task Statuses
- ⏳ Call mom
- ✅ Gym

## 💭 Answers
1. What went well?
   > ...
2. What to improve?
   > ...
3. Main lesson?
   > ...
4. Focus for tomorrow?
   > ...
5. Deep Work time?
   > 2h

## 📅 Tomorrow
- New task
```

## Pitfalls & Fixes

### 1. Calendar module shadowing
Running from `brief/` shadows Python `calendar` → `ImportError: timegm`.
**Fix:** Run from outside `brief/` or clean `sys.path`.

### 2. No TTY in cron
`input()` fails → EOFError.
**Fix:** Detect `isatty()`. Non-TTY → template mode, try send to TG, save locally.

### 3. Telegram availability
No token/chat configured → send fails.
**Fix:** Graceful fallback — always save local file.

## Files
- `~/.hermes/scripts/brief_evening.py` — main script
- `~/.hermes/diary/` — saved diaries
- `~/.hermes/tasks/cronjobs.yml` — schedule
