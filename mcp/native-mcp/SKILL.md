---
name: native-mcp
description: "MCP client: connect servers, register tools (stdio/HTTP)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [MCP, Tools, Integrations]
    related_skills: [mcporter]
---

# Native MCP Client

Hermes Agent has a built-in MCP client that connects to MCP servers at startup, discovers their tools, and makes them available as first-class tools the agent can call directly. No bridge CLI needed -- tools from MCP servers appear alongside built-in tools like `terminal`, `read_file`, etc.

## When to Use

Use this whenever you want to:
- Connect to MCP servers and use their tools from within Hermes Agent
- Add external capabilities (filesystem access, GitHub, databases, APIs) via MCP
- Run local stdio-based MCP servers (npx, uvx, or any command)
- Connect to remote HTTP/StreamableHTTP MCP servers
- Have MCP tools auto-discovered and available in every conversation

For ad-hoc, one-off MCP tool calls from the terminal without configuring anything, see the `mcporter` skill instead.

## Prerequisites

- **mcp Python package** -- optional dependency; install with `pip install mcp`. If not installed, MCP support is silently disabled.
- **Node.js** -- required for `npx`-based MCP servers (most community servers)
- **uv** -- required for `uvx`-based MCP servers (Python-based servers)

Install the MCP SDK:

```bash
pip install mcp
# or, if using uv:
uv pip install mcp
```

## Quick Start

Add MCP servers to `~/.hermes/config.yaml` under the `mcp_servers` key:

```yaml
mcp_servers:
  time:
    command: "uvx"
    args: ["mcp-server-time"]
```

Restart Hermes Agent. On startup it will:
1. Connect to the server
2. Discover available tools
3. Register them with the prefix `mcp_time_*`
4. Inject them into all platform toolsets

You can then use the tools naturally -- just ask the agent to get the current time.

## Configuration Reference

Each entry under `mcp_servers` is a server name mapped to its config. There are two transport types: **stdio** (command-based) and **HTTP** (url-based).

### Stdio Transport (command + args)

```yaml
mcp_servers:
  server_name:
    command: "npx"             # (required) executable to run
    args: ["-y", "pkg-name"]   # (optional) command arguments, default: []
    env:                       # (optional) environment variables for the subprocess
      SOME_API_KEY: "value"
    timeout: 120               # (optional) per-tool-call timeout in seconds, default: 120
    connect_timeout: 60        # (optional) initial connection timeout in seconds, default: 60
```

### HTTP Transport (url)

```yaml
mcp_servers:
  server_name:
    url: "https://my-server.example.com/mcp"   # (required) server URL
    headers:                                     # (optional) HTTP headers
      Authorization: "Bearer sk-..."
    timeout: 180               # (optional) per-tool-call timeout in seconds, default: 120
    connect_timeout: 60        # (optional) initial connection timeout in seconds, default: 60
```

### All Config Options

| Option            | Type   | Default | Description                                       |
|-------------------|--------|---------|---------------------------------------------------|
| `command`         | string | --      | Executable to run (stdio transport, required)     |
| `args`            | list   | `[]`    | Arguments passed to the command                   |
| `env`             | dict   | `{}`    | Extra environment variables for the subprocess    |
| `url`             | string | --      | Server URL (HTTP transport, required)             |
| `headers`         | dict   | `{}`    | HTTP headers sent with every request              |
| `timeout`         | int    | `120`   | Per-tool-call timeout in seconds                  |
| `connect_timeout` | int    | `60`    | Timeout for initial connection and discovery      |

Note: A server config must have either `command` (stdio) or `url` (HTTP), not both.

## How It Works

### Startup Discovery

When Hermes Agent starts, `discover_mcp_tools()` is called during tool initialization:

1. Reads `mcp_servers` from `~/.hermes/config.yaml`
2. For each server, spawns a connection in a dedicated background event loop
3. Initializes the MCP session and calls `list_tools()` to discover available tools
4. Registers each tool in the Hermes tool registry

### Tool Naming Convention

MCP tools are registered with the naming pattern:

```
mcp_{server_name}_{tool_name}
```

Hyphens and dots in names are replaced with underscores for LLM API compatibility.

Examples:
- Server `filesystem`, tool `read_file` → `mcp_filesystem_read_file`
- Server `github`, tool `list-issues` → `mcp_github_list_issues`
- Server `my-api`, tool `fetch.data` → `mcp_my_api_fetch_data`

### Auto-Injection

After discovery, MCP tools are automatically injected into all `hermes-*` platform toolsets (CLI, Discord, Telegram, etc.). This means MCP tools are available in every conversation without any additional configuration.

### Connection Lifecycle

- Each server runs as a long-lived asyncio Task in a background daemon thread
- Connections persist for the lifetime of the agent process
- If a connection drops, automatic reconnection with exponential backoff kicks in (up to 5 retries, max 60s backoff)
- On agent shutdown, the MCP connection (asyncio task) is closed, but **the child OS process is NOT terminated** — it becomes an orphan under PID 1 and continues consuming memory
- Each Hermes session (CLI, gateway, Kanban worker) spawns its OWN independent MCP subprocess. N sessions = N codegraph instances

### Idempotency

`discover_mcp_tools()` is idempotent -- calling it multiple times only connects to servers that aren't already connected. Failed servers are retried on subsequent calls.

## Transport Types

### Stdio Transport

The most common transport. Hermes launches the MCP server as a subprocess and communicates over stdin/stdout.

```yaml
mcp_servers:
  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
```

The subprocess inherits a **filtered** environment (see Security section below) plus any variables you specify in `env`.

### HTTP / StreamableHTTP Transport

For remote or shared MCP servers. Requires the `mcp` package to include HTTP client support (`mcp.client.streamable_http`).

```yaml
mcp_servers:
  remote_api:
    url: "https://mcp.example.com/mcp"
    headers:
      Authorization: "Bearer sk-..."
```

If HTTP support is not available in your installed `mcp` version, the server will fail with an ImportError and other servers will continue normally.

## Security

### Environment Variable Filtering

For stdio servers, Hermes does NOT pass your full shell environment to MCP subprocesses. Only safe baseline variables are inherited:

- `PATH`, `HOME`, `USER`, `LANG`, `LC_ALL`, `TERM`, `SHELL`, `TMPDIR`
- Any `XDG_*` variables

All other environment variables (API keys, tokens, secrets) are excluded unless you explicitly add them via the `env` config key. This prevents accidental credential leakage to untrusted MCP servers.

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      # Only this token is passed to the subprocess
      GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_..."
```

### Credential Stripping in Error Messages

If an MCP tool call fails, any credential-like patterns in the error message are automatically redacted before being shown to the LLM. This covers:

- GitHub PATs (`ghp_...`)
- OpenAI-style keys (`sk-...`)
- Bearer tokens
- Generic `token=`, `key=`, `API_KEY=`, `password=`, `secret=` patterns

## Troubleshooting

### "MCP SDK not available -- skipping MCP tool discovery"

The `mcp` Python package is not installed. Install it:

```bash
pip install mcp
```

### "No MCP servers configured"

No `mcp_servers` key in `~/.hermes/config.yaml`, or it's empty. Add at least one server.

### "Failed to connect to MCP server 'X'"

Common causes:
- **Command not found**: The `command` binary isn't on PATH. Ensure `npx`, `uvx`, or the relevant command is installed.
- **Package not found**: For npx servers, the npm package may not exist or may need `-y` in args to auto-install.
- **Timeout**: The server took too long to start. Increase `connect_timeout`.
- **Port conflict**: For HTTP servers, the URL may be unreachable.

### "MCP server 'X' requires HTTP transport but mcp.client.streamable_http is not available"

Your `mcp` package version doesn't include HTTP client support. Upgrade:

```bash
pip install --upgrade mcp
```

### Tools not appearing

- Check that the server is listed under `mcp_servers` (not `mcp` or `servers`)
- Ensure the YAML indentation is correct
- Look at Hermes Agent startup logs for connection messages
- Tool names are prefixed with `mcp_{server}_{tool}` -- look for that pattern
- **Tools discovered (`hermes mcp test` succeeds) but not in the agent's tool list:** the session started before MCP connected. Tools are only registered at agent startup. Run `/reset` (Telegram) or restart Hermes CLI to see them. Until then, use the MCP tool via CLI or direct JSON-RPC over stdin (see `references/codegraph-cli-fallback.md`). For full diagnostic workflow (checking mcp-stderr.log timestamps, agent.log registration lines, session vs server start ordering), see `references/mcp-timing-diagnostics.md`.
  - **Use the `codegraph-cli` skill** (autonomous-ai-agents category) — it teaches subagents to use CodeGraph CLI commands directly via terminal (`codegraph context`, `codegraph query`, `codegraph callers/callees`, etc.)
  - Or use direct JSON-RPC over stdin (see `references/codegraph-cli-fallback.md` in this skill)

### Multiple orphaned MCP processes found (memory leak)

If you see multiple instances of the same MCP server (e.g. 3-4 `codegraph serve` processes), each one was spawned by a different Hermes session that exited without cleaning up. Detect with:

```bash
ps aux | grep -E 'codegraph.*serve.*mcp' | grep -v grep | wc -l
ps -eo pid,ppid,lstart,cmd --sort=-%mem | grep -E 'codegraph|mcp.*serve'
```

Cleanup: kill all orphaned instances except the one owned by the active gateway or your current CLI session.

```bash
# Find gateway's pid
GW_PID=$(systemctl --user show hermes-gateway.service -p MainPID --value 2>/dev/null)
# Kill codegraph instances NOT owned by gateway or your current session
ps -eo pid,ppid,args --no-headers | grep -E 'codegraph.*serve.*mcp' | while read pid ppid rest; do
  if [ "$ppid" != "$GW_PID" ] && [ "$ppid" != "$$" ]; then
    echo "killing orphan $pid (parent $ppid)"
    kill "$pid" 2>/dev/null
  fi
done
```

After cleanup, verify with `free -h` — expect significant memory recovery (each codegraph instance uses ~78MB RSS).

**Root cause:** Hermes MCP client spawns the server as a stdio subprocess. On agent exit, the asyncio MCP session closes, but `process.terminate()` is NOT called on the child. The orphan survives under PID 1. This applies to ALL stdio-based MCP servers, not just codegraph.

**Long-term fix (upstream):** patch `discover_mcp_tools()` / the MCP client to call `process.terminate()` or use `Popen` with `close_fds=True` + track child PIDs for cleanup on exit.

**Workaround: use HTTP transport** — configure MCP servers via `url:` instead of `command:` so they run independently (systemd service, Docker, etc.) and Hermes just connects as a client. No orphan processes.

### `hermes mcp add`

**Root cause:** `hermes mcp add --args` uses argparse after the `mcp` subcommand. Any `--args` value that starts with `--` (e.g. `--mcp`, `--path`) is intercepted by the parent parser as a global flag before it reaches `mcp add`.

**Fix:** Do NOT use `hermes mcp add` when the command's own arguments include double-dash flags. Instead, edit `~/.hermes/config.yaml` directly, adding `args` as a YAML list with each element on a separate line:

```yaml
mcp_servers:
  my_server:
    command: "codegraph"
    args:
    - serve
    - --mcp
    - --path
    - /path/to/project
    enabled: true
```

Then verify with `hermes mcp test my_server`.

For commands without leading-dash args (e.g. `npx -y mcp-server-time`), `hermes mcp add` works fine.

## Examples

### Time Server (uvx)

```yaml
mcp_servers:
  time:
    command: "uvx"
    args: ["mcp-server-time"]
```

Registers tools like `mcp_time_get_current_time`.

### Filesystem Server (npx)

```yaml
mcp_servers:
  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/documents"]
    timeout: 30
```

Registers tools like `mcp_filesystem_read_file`, `mcp_filesystem_write_file`, `mcp_filesystem_list_directory`.

### GitHub Server with Authentication

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_xxxxxxxxxxxxxxxxxxxx"
    timeout: 60
```

Registers tools like `mcp_github_list_issues`, `mcp_github_create_pull_request`, etc.

### Remote HTTP Server

```yaml
mcp_servers:
  company_api:
    url: "https://mcp.mycompany.com/v1/mcp"
    headers:
      Authorization: "Bearer sk-xxxxxxxxxxxxxxxxxxxx"
      X-Team-Id: "engineering"
    timeout: 180
    connect_timeout: 30
```

### CodeGraph — Code Knowledge Graph

[CodeGraph](https://github.com/colbymchenry/codegraph) builds a local SQLite knowledge graph of your project (function calls, imports, inheritance) via tree-sitter. 21k+ stars, 19+ languages, framework-aware.

Install: `curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh`

Index a project: `cd /path/to/project && codegraph init -i`

Add to Hermes via config.yaml (use direct edit, not `hermes mcp add`, because of the `--mcp` flag):

```yaml
mcp_servers:
  codegraph:
    command: "codegraph"
    args:
    - serve
    - --mcp
    - --path
    - /path/to/project
    enabled: true
```

Verify: `hermes mcp test codegraph`

Add `--no-watch` to `args` to disable the file watcher on slow filesystems (WSL2 /mnt drives).

Available tools after connection: `mcp_codegraph_search`, `mcp_codegraph_context`, `mcp_codegraph_trace`, `mcp_codegraph_impact`, `mcp_codegraph_explore`, and 5 more.

**Pitfalls:**
- **No markdown support:** CodeGraph uses tree-sitter and does NOT parse `.md` files. Indexing an Obsidian vault or docs-only repo produces minimal results (only JS/YAML/Python files get parsed). Stick to source-code projects.
- **`codegraph uninit` requires confirmation:** pipe `echo "y" | codegraph uninit` or pass nothing to skip the prompt.
- **Auto-sync via cron:** `codegraph sync` is incremental (seconds). Create a no_agent cron job (`cronjob(action='create', no_agent=true, script='cd /home/hermes/.hermes/skills && codegraph sync 2>&1')`) — when nothing changed, stdout is empty and no message is sent (silent watchdog pattern).
- **Multiple instances pile up:** Each Hermes session (CLI, gateway, Kanban worker) spawns its own codegraph subprocess (~78MB RSS each). After several CLI sessions + gateway, 3-4 orphaned codegraph instances accumulate. See the "Multiple orphaned MCP processes found (memory leak)" troubleshooting section for detection and cleanup.
- **Reuse design (limitation):** The ideal architecture is one codegraph per machine (run as systemd service), with all Hermes sessions connecting via HTTP transport or UNIX socket sharing. Currently each session spawns its own — fix is in `discover_mcp_tools()`: either (a) add `process.terminate()` on exit, or (b) use a singleton/connection-pool so only one codegraph runs.

> **Fallback when MCP tools aren't visible in the agent's tool list** (session started before MCP connected): use CodeGraph's CLI commands directly, or direct JSON-RPC over stdin for MCP-only tools (`node`, `trace`, `explore`). See `references/codegraph-cli-fallback.md`.

### Multiple Servers

```yaml
mcp_servers:
  time:
    command: "uvx"
    args: ["mcp-server-time"]

  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]

  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_xxxxxxxxxxxxxxxxxxxx"

  company_api:
    url: "https://mcp.internal.company.com/mcp"
    headers:
      Authorization: "Bearer sk-xxxxxxxxxxxxxxxxxxxx"
    timeout: 300
```

All tools from all servers are registered and available simultaneously. Each server's tools are prefixed with its name to avoid collisions.

## Sampling (Server-Initiated LLM Requests)

Hermes supports MCP's `sampling/createMessage` capability — MCP servers can request LLM completions through the agent during tool execution. This enables agent-in-the-loop workflows (data analysis, content generation, decision-making).

Sampling is **enabled by default**. Configure per server:

```yaml
mcp_servers:
  my_server:
    command: "npx"
    args: ["-y", "my-mcp-server"]
    sampling:
      enabled: true           # default: true
      model: "gemini-3-flash" # model override (optional)
      max_tokens_cap: 4096    # max tokens per request
      timeout: 30             # LLM call timeout (seconds)
      max_rpm: 10             # max requests per minute
      allowed_models: []      # model whitelist (empty = all)
      max_tool_rounds: 5      # tool loop limit (0 = disable)
      log_level: "info"       # audit verbosity
```

Servers can also include `tools` in sampling requests for multi-turn tool-augmented workflows. The `max_tool_rounds` config prevents infinite tool loops. Per-server audit metrics (requests, errors, tokens, tool use count) are tracked via `get_mcp_status()`.

Disable sampling for untrusted servers with `sampling: { enabled: false }`.

## Notes

- MCP tools are called synchronously from the agent's perspective but run asynchronously on a dedicated background event loop
- Tool results are returned as JSON with either `{"result": "..."}` or `{"error": "..."}`
- The native MCP client is independent of `mcporter` -- you can use both simultaneously
- Server connections are persistent and shared across all conversations in the same agent process
- Adding or removing servers requires restarting the agent (no hot-reload currently)
