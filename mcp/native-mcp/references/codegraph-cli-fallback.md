# CodeGraph CLI — Fallback when MCP tools are not in session tool list

When the native MCP client connects but its tools (`mcp_codegraph_*`) don't appear in the agent's available tool list (common when session started before MCP was connected), use CodeGraph's CLI directly as a fallback.

## Prerequisite

CLI commands look for `.codegraph/` in the **current working directory**. Always `cd` to the project first:

```bash
cd /path/to/project/with/.codegraph
```

## CLI Commands (also available via MCP)

| CodeGraph CLI | MCP Tool | Purpose |
|---|---|---|
| `codegraph status [path]` | `codegraph_status` | Index statistics (files, nodes, edges) |
| `codegraph query <symbol>` | `codegraph_search` | Quick symbol search by name (locations only) |
| `codegraph context <task>` | `codegraph_context` | PRIMARY — composes search + node + callers + callees into one markdown output with code |
| `codegraph callers <symbol>` | `codegraph_callers` | Find all functions that call a symbol |
| `codegraph callees <symbol>` | `codegraph_callees` | Find all functions a symbol calls |
| `codegraph impact <symbol>` | `codegraph_impact` | Analyze impact radius of changing a symbol |
| `codegraph files` | `codegraph_files` | Project file tree from the index |

## MCP-Only Tools (no CLI equivalent)

These require MCP transport. When MCP tools aren't in the agent's tool list, fall back to direct JSON-RPC over stdin:

```bash
# codegraph_node — get one symbol's details (location, signature, docstring, edges)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"codegraph_node","arguments":{"symbol":"myFunction"}}}' | \
  codegraph serve --mcp --path /path/to/project --no-watch 2>/dev/null

# codegraph_trace — trace call path between two symbols
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"codegraph_trace","arguments":{"from":"funcA","to":"funcB"}}}' | \
  codegraph serve --mcp --path /path/to/project --no-watch 2>/dev/null

# codegraph_explore — returns source for several related symbols grouped by file
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"codegraph_explore","arguments":{"query":"symbol1 symbol2"}}}' | \
  codegraph serve --mcp --path /path/to/project --no-watch 2>/dev/null
```

**Important:** the `--no-watch` flag prevents the file watcher from starting (faster, avoids filesystem issues on WSL2 /mnt drives).

## Verifying the connection

```bash
hermes mcp test codegraph
```

Expected output:
```
Testing 'codegraph'...
  Transport: stdio → codegraph
  Auth: none
  ✓ Connected (355ms)
  ✓ Tools discovered: 10
```

## Known tools (full list)

1. `codegraph_search` — Quick symbol search (CLI: `query`)
2. `codegraph_context` — Primary comprehensive context (CLI: `context`)
3. `codegraph_callers` — Find callers (CLI: `callers`)
4. `codegraph_callees` — Find callees (CLI: `callees`)
5. `codegraph_impact` — Impact analysis (CLI: `impact`)
6. `codegraph_node` — **MCP-only**: single symbol details
7. `codegraph_explore` — **MCP-only**: several related symbols + source code
8. `codegraph_status` — Index status (CLI: `status`)
9. `codegraph_files` — File tree (CLI: `files`)
10. `codegraph_trace` — **MCP-only**: call path trace between two symbols

## Pitfalls

### 🚫 Markdown files are NOT indexed
CodeGraph uses tree-sitter parsers and does NOT support `.md` files. An Obsidian vault with 216 markdown files indexed only its `.obsidian/plugins/obsidian-git/main.js` (JS) and some YAML configs — all `.md` content was invisible. **Only index source-code projects.**

### ⚠️ `codegraph uninit` requires confirmation
The command prompts `Continue? (y/N)` and blocks on stdin. To skip:
```bash
echo "y" | codegraph uninit
```

### 🔄 Auto-sync via cron (silent watchdog pattern)
`codegraph sync` is incremental (takes seconds). Create a no_agent cron:
```yaml
# cronjob(action='create', no_agent=true, schedule='0 6 * * *', 
#         script='cd /path/to/project && codegraph sync 2>&1')
```
When nothing changed → empty stdout → no message sent. Silent, cheap, always fresh.