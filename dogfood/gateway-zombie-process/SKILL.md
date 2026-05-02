---
name: gateway-zombie-process
description: Diagnose and fix hermes-gateway when systemd says it's active but Telegram polling is dead (main loop exited, process still alive)
---

# Gateway Zombie Process Diagnosis & Recovery

## Trigger

User says hermes-gateway doesn't respond in Telegram, but:
- `systemctl --user status hermes-gateway` shows `active (running)`
- `ps aux | grep gateway` shows a Python process

## Detection

### Step 1 — Check if gateway is actually processing Telegram

```bash
journalctl --user -u hermes-gateway -n 10 --no-pager
```

**Healthy**: shows recent entries (within seconds/minutes) like:
- `[Telegram] Connected to Telegram (polling mode)`
- `[Telegram] Flushing text batch`
- `response ready: platform=telegram`

**Zombie**: only old logs (hours ago), no Telegram activity. The **process is alive but the main loop exited**.

### Step 2 — Confirm main loop is dead

Check the agent.log for:
```bash
tail -20 ~/.hermes/logs/agent.log | grep -E "(Gateway stopped|Cron ticker stopped|Disconnected from Telegram)"
```

If you see `"Gateway stopped"` + `"Cron ticker stopped"` + `"Disconnected from Telegram"` consecutively, 
the gateway did a graceful shutdown and its event loop exited, but the Python process didn't terminate.

### Step 3 — Check network I/O (optional)

The zombie process still has open sockets (from epoll wait), but no active Telegram polling:

```bash
ls /proc/<PID>/fd/ | wc -l
```

### Step 4 — Check if SIGTERM works

```bash
systemctl --user restart hermes-gateway
```

If it hangs (timeout after 30+ seconds), the process ignores SIGTERM.

## Fix

Force kill the process, systemd will restart it:

```bash
systemctl --user kill hermes-gateway -s SIGKILL
```

Wait 2-3 seconds, then verify:

```bash
sleep 3 && journalctl --user -u hermes-gateway --since "30 seconds ago" --no-pager
```

**Expected healthy startup:**
```
18:17:07 — Started hermes-gateway.service
18:17:09 — Starting Hermes Gateway...
18:17:09 — Connecting to telegram...
18:17:12 — DoH discovery / fallback IPs loaded
18:17:15 — Application started
18:17:15 — ✓ Connected to Telegram (polling mode)
18:17:15 — Gateway running with 1 platform(s)
```

## Root Cause

The gateway can enter a "zombie" state where:
1. A `STOP` or restart command kills the internal event loop
2. Telegram `Application.stop()` completes and disconnects
3. The main Python process doesn't actually exit (stays in epoll wait)
4. Systemd sees PID alive → thinks service is healthy → doesn't restart

This differs from a normal crash where the process exits and systemd restarts it automatically.

## Pitfalls

- `systemctl --user restart` will hang/timeout if the process ignores SIGTERM — need SIGKILL
- Don't use `kill -9 <PID>` directly — use `systemctl kill` to keep systemd informed
- After SIGKILL, systemd clears `Main PID` and auto-restarts via `Restart=on-failure`

### Cron PATH issue

**Gateway healthcheck script (`scripts/gateway_healthcheck.sh`) must use full paths** for `systemctl`, `logger`, `journalctl`, `tail`, and `cut`.

Reason: cron and scheduled jobs (`cronjob` tool, `task-manager` skill) run with a **minimal PATH** that typically doesn't contain `/usr/bin/`. When the script calls `systemctl` by name, the command silently fails (exit 127 → `!` inverts it to 0 → the if-block executes a phantom restart that also silently fails). Result: the script always exits 0 regardless of whether systemd commands actually ran.

**Fix confirmed working** — `/usr/bin/systemctl`, `/usr/bin/logger`, `/usr/bin/journalctl` all exist. The script in this skill's `scripts/` directory now uses full paths (verified clean output with no errors when run via cron's PATH).

To test:
```bash
# Should run without any "command not found" errors
/usr/bin/bash /home/hermes/gateway_healthcheck.sh
echo $?  # 0 = healthy or restarted successfully
```
