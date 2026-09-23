# Gateway CLI-Only Commands Fix — 2026-05-26 Session

## Problem

Gateway crashed with AttributeError when user invoked `/tools`, `/skills`, `/cron` from Telegram. The user reported "сессия отрубилась" — the bot replied with "OGO BOT: Sorry, I encountered an error".

## Log Evidence

```
2026-05-26 16:07:49,069 ERROR gateway.platforms.base: [Telegram] Error handling message: 'GatewayRunner' object has no attribute '_handle_tools_command'
2026-05-26 16:07:58,708 ERROR gateway.platforms.base: [Telegram] Error handling message: 'GatewayRunner' object has no attribute '_handle_skills_command'
2026-05-26 16:08:05,001 ERROR gateway.platforms.base: [Telegram] Error handling message: 'GatewayRunner' object has no attribute '_handle_cron_command'
```

The gateway log also showed these commands were registered as `cli_only=True` in `commands.py`:

```python
# hermes_cli/commands.py lines 161-172
CommandDef("tools", "Manage tools: /tools [list|disable|enable] [name...]", "Tools & Skills",
           args_hint="[list|disable|enable] [name...]", cli_only=True),
CommandDef("skills", "Search, install, inspect, or manage skills",
           "Tools & Skills", cli_only=True,
           subcommands=("search", "browse", "inspect", "install", "audit")),
CommandDef("cron", "Manage scheduled tasks", "Tools & Skills",
           cli_only=True, args_hint="[subcommand]",
           subcommands=("list", "add", "create", "edit", "pause", "resume", "run", "remove")),
```

## Root Cause

The `_handle_message` method in `gateway/run.py` had `if canonical == "tools"/"skills"/"cron"` dispatch blocks (added in a previous session) that called `self._handle_tools_command(event)` etc., but the actual methods `_handle_tools_command`, `_handle_skills_command`, `_handle_cron_command` were never implemented on the GatewayRunner class.

## Fix Applied

**1. Dispatch blocks** (added after `voice` block, around line 7598):
```python
if canonical == "tools":
    return "🔧 `/tools` — управление инструментами. Доступна только в CLI."

if canonical == "skills":
    return "📦 `/skills` — управление навыками. Доступна только в CLI."

if canonical == "cron":
    return "⏰ `/cron` — управление расписанием. Доступна только в CLI."
```

**2. Handler methods** (added after `_handle_voice_channel_leave`, around line 11200):
```python
async def _handle_tools_command(self, event: MessageEvent) -> str:
    """Handle /tools — CLI-only command."""
    return "🔧 `/tools` — управление инструментами. Доступна только в CLI."

async def _handle_skills_command(self, event: MessageEvent) -> str:
    """Handle /skills — CLI-only command."""
    return "📦 `/skills` — управление навыками. Доступна только в CLI."

async def _handle_cron_command(self, event: MessageEvent) -> str:
    """Handle /cron — CLI-only command."""
    return "⏰ `/cron` — управление расписанием. Доступна только в CLI."
```

**3. Gateway restarted:**
```bash
hermes gateway restart
```

## Verification

After restart:
- `hermes gateway status` confirmed running (PID rotated)
- No new AttributeError in logs
- Memory dropped from 247MB to 201MB (fresh process)

## Other Issues Found During Investigation

- **Telegram DNS**: `api.telegram.org` periodically unreachable. Gateway falls back to IP `149.154.166.110`. Consider adding static `/etc/hosts` entry.
- **Memory full**: Agent memory at 2,169/2,200 chars. Cleaned by removing stale book context.
- **Discord**: No bot token configured. Gateway auto-paused after 10 reconnect failures.

## Commands Used

```bash
# Check gateway status
hermes gateway status

# Read gateway logs
grep -i "error\|fail\|attribute" ~/.hermes/logs/gateway.log | tail -30

# Find CLI-only commands
grep -B2 "cli_only=True" hermes_cli/commands.py | grep "CommandDef"

# Find existing gateway handlers
grep -n "async def _handle_.*_command" gateway/run.py

# Find command dispatch blocks
grep -n "if canonical == " gateway/run.py | head -40

# Restart
hermes gateway restart
```