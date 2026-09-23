# MCP Timing Diagnostics — Tools discovered but not registered

## Symptom

- `hermes mcp test <server>` succeeds (connected, tools discovered)
- But the agent's tool list has no `mcp_<server>_*` tools
- `/reset` (Telegram) or CLI restart doesn't fix it

## Root Cause

MCP tools are registered **only at agent startup** during `discover_mcp_tools()`. If the MCP server process takes longer to start than the agent's initialization phase, the session starts with an empty MCP tool registry and no re-discovery happens.

## Diagnostic Steps

### 1. Check MCP server startup timing

```bash
cat ~/.hermes/logs/mcp-stderr.log
```

Look for the most recent `===== starting MCP server 'X' =====` line. The timestamp tells you when the server actually connected.

### 2. Check tool registration

```bash
grep -i "MCP.*registered" ~/.hermes/logs/agent.log ~/.hermes/logs/agent.log.1
```

If this line is missing for the current session's timeframe, registration didn't happen.

### 3. Compare session start vs server start

```bash
# Find the current session ID from agent.log
grep "conversation turn.*session=" ~/.hermes/logs/agent.log | tail -1

# Find MCP registration time
grep "MCP.*registered 10 tool" ~/.hermes/logs/agent.log

# Check mcp-stderr.log for the server start time
tail -3 ~/.hermes/logs/mcp-stderr.log
```

If the session timestamp is **before** the MCP server start timestamp, the session won the race and tools aren't registered.

## What Doesn't Help

- Running `/reset` again — same race condition
- `hermes mcp test` — it tests connectivity, not registration
- Restarting MCP servers manually — they reconnect but registration is one-shot at startup

## The Fix

The native MCP client should ideally re-discover tools periodically or after reconnection. Until that's implemented:

1. **Restart the entire gateway** (not just /reset):
   ```bash
   hermes gateway restart
   ```
   This kills and re-spawns the agent process, which re-runs `discover_mcp_tools()`.

2. **If gateway restart still fails** — wait 10-15 seconds between gateway start and first message. The MCP server needs time to start and register.

3. **Use CLI fallback** — CodeGraph and other MCP tools often have CLI equivalents. See `references/codegraph-cli-fallback.md`.

## Prevention

For speeding up MCP server startup:
- Pre-warm the server: start codegraph in the background before the gateway
- Reduce `connect_timeout` in config.yaml (makes connection attempts faster)
- Use `--no-watch` for codegraph to skip file watcher init