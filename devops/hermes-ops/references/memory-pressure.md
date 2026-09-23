# Memory Pressure — Hermes VPS

Diagnose and fix low memory on a 2 GB Hermes VPS.

## When to Use

- `free -h` shows less than 300 MB available or swap over 80%
- User complains of slowness, timeouts, errors
- Prophylactic maintenance after 1+ week of gateway uptime

## Diagnostics

### 1. Overall picture
```bash
free -h
cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree|SReclaimable'
```

### 2. Gateway status
```bash
systemctl --user status hermes-gateway.service
```
Shows PID, Memory, CPU, Tasks, recent logs. Faster than `ps` for a baseline.

### 3. Top consumers
```bash
ps aux --sort=-%mem | head -20
```

### 4. Parent-child relationships (who owns what)
```bash
ps -eo pid,ppid,pgid,lstart,stat,cmd --sort=-%mem | head -30
```
Check PPID to see if codegraph is attached to gateway (PPID = gateway PID) or orphan (PPID=1).

### 5. Known leaks

**Old codegraph processes** — should be at most 1 per active session + 1 for gateway.
```bash
ps aux | grep codegraph | grep -v grep
```
- Each takes 18-80 MB RSS
- Accumulate from terminated Hermes sessions
- Cause: `~/.hermes/config.yaml` has `mcp_servers.codegraph`. Each Hermes run spawns a codegraph MCP process. On normal exit the `finally` block cleans it up, but SIGKILL/SIGSTOP/crash skips cleanup.
- Orphan detection: PPID = 1 (adopted by init) or PPID of a dead session.

**Stopped Hermes sessions** (state `Tl`):
```bash
ps aux | grep hermes | grep -v grep
```
- Each ~114 MB RSS
- Cause: Ctrl+C or `/stop` or SIGTERM didn't reach the process cleanly.

**Hanging Kanban workers** — task completed but process alive:
```bash
ps aux | grep 'hermes.*kanban task' | grep -v grep
```
- Each takes baseline RSS (50-80 MB)
- Cause: worker agent loop finishes, calls `kanban_complete`, but the CLI process doesn't exit
- Detection: `hermes kanban show <id>` shows `done`, but `ps` shows the process still running
- Distinction: NOT state `Tl` — these are `Ssl` (normal sleeping)
- Fix: `kill -9 <pid>` (SIGTERM usually ignored)
- Symptom: persistent Telegram typing indicator

**Stale Hermes CLI processes** with high accumulated CPU:
```bash
ps aux --sort=-%mem | grep 'hermes.*bin/hermes' | grep -v gateway | grep -v grep
```
- If alive > 1 day and > 50 min CPU, likely abandoned.
- State `D` (uninterruptible sleep) doesn't respond to signals — dies on I/O completion.

**Linux process states:**
- `Tl` — Stopped (traced). Dead weight, `kill -9` safe.
- `Zs` — Zombie. Will clean itself.
- `D` — Uninterruptible sleep. Can't be killed, wait or reboot.
- `Sl` — Sleeping, multi-threaded. Normal.
- `R` — Running.

## Cleanup

### Safe to kill

| Process | Signal | Note |
|---------|--------|------|
| Stopped Hermes sessions (state Tl) | `kill <PID>` | 100% safe |
| Old codegraph (not attached to gateway) | `kill <PID>` | Leave 1 for gateway |
| Hanging Kanban worker (done task, alive process) | `kill -9 <PID>` | SIGTERM rarely works; SIGKILL required |
| Stale Hermes CLI (not gateway) | `kill <PID>` | Only if not in use now |
| Dashboard | `kill <PID>` | If not needed now |

### DO NOT kill

- Gateway (`hermes ... gateway run`)
- codegraph belonging to gateway (same start time)
- Current user session

## Gateway Restart Sequence

### Critical: kill dashboard FIRST

Dashboard is a separate `hermes dashboard --host 0.0.0.0 --insecure` process.
It does NOT die with gateway.

```bash
# 1. Kill dashboard if running
kill <dashboard_pid>

# 2. Soft stop gateway
systemctl --user stop hermes-gateway.service

# 3. Fallback (if stop times out after 60s)
systemctl --user status hermes-gateway.service  # get PID
kill -TERM <gateway_pid>
sleep 5
ps -p <pid> -o pid,state,cmd --no-headers || echo "gone"

# 4. Verify stopped
ps aux | grep 'gateway run' | grep -v grep

# 5. Start
systemctl --user start hermes-gateway.service
sleep 3
systemctl --user status hermes-gateway.service

# 6. Check memory
free -h
```

## Expected Effect After Cleanup

- RAM: ~800-900 MB used (was 1.6-1.7 GB)
- Available: > 1 GB (was < 300 MB)
- Swap: partially clears (not instantly, may drop 511 Mi to 46 Mi)
- Gateway: ~135 MB instead of 1 GB+
- codegraph: 2 processes (yours + gateway) instead of 4-5

## Methodology — Iterative

1. Overall picture: free -h, systemctl status, ps aux
2. Restart gateway — usually removes 70% of load
3. Check again — what's still consuming?
4. Find specific culprits — codegraph orphans, Tl processes, stale sessions
5. Kill precisely — each process individually, verify
6. Final check — free -h, compare to baseline

## Pitfalls

- **Don't restart gateway without killing dashboard first.** Dashboard continues eating RAM independently.
- **`systemctl stop` may time out.** Gateway doesn't respond to graceful shutdown with stuck workers. Always have a `kill -TERM` fallback.
- **codegraph multiplies.** Each `hermes` launch spawns its own codegraph MCP subprocess. Kill excess, keep only gateway-attached ones.
- **Swap doesn't clear magically.** `swapoff -a && swapon -a` requires free RAM = swap size — risky on 2 GB.
- **State `D` processes** don't respond to kill signals. Wait for I/O to complete.
- **Dashboard survives gateway restart.** Verify it didn't restart: `ps aux | grep dashboard | grep -v grep`.
- **Hermes has orphan cleanup** (`_kill_orphaned_mcp_children()` in `tools/mcp_tool.py`) but only runs on `finally` block of `_run_stdio()`, which doesn't execute on SIGKILL/crash.