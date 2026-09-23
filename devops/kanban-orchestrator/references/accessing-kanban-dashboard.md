# Accessing the Kanban Web Dashboard

Hermes Kanban has a **web UI dashboard** served through Hermes' built-in
dashboard server. It lives at `plugins/kanban/dashboard/` — a React SPA
(compiled to `dist/index.js` + `dist/style.css`) with a FastAPI Python
backend (`plugin_api.py`). The dashboard supports drag-drop card columns,
comment threads, live WebSocket updates, and a Recovery drawer for stuck
workers.

## How to Open

```bash
hermes dashboard
```

This starts a web server on **port 9119**. Open the printed URL in
your browser. The Kanban tab appears as `/kanban` in the navigation.

## Key Flags

| Flag | Purpose |
|------|---------|
| `--port PORT` | Custom port (default 9119) |
| `--host HOST` | Bind address (default 127.0.0.1) |
| `--insecure` | **Required** with `--host 0.0.0.0`. Dashboard refuses LAN bind without it |
| `--skip-build` | Skip Web UI build (use prebuilt dist). **Saves 30-60s** and avoids hangs when npm isn't responsive |
| `--no-open` | Don't auto-open browser |
| `--status` | List running dashboard processes |
| `--stop` | Kill all running dashboard processes |

## Common Usage

```bash
# Local — just works
hermes dashboard

# LAN access (phone/tablet on same network)
hermes dashboard --host 0.0.0.0 --insecure --skip-build

# Custom port behind a reverse proxy
hermes dashboard --port 9090
```

## Pitfalls

**Build hangs on "Building web UI...".** The npm build step can stall or
take very long (60s+). Always use `--skip-build` — the prebuilt dist
exists at `$HERMES_HOME/hermes-agent/hermes_cli/web_dist/` and works
fine for the dashboard. Only omit `--skip-build` if you changed the web
source and need a fresh build.

**Port 8080 vs 9119.** Older docs/references may say port 8080. The
actual default is **9119** as of v2.x. Verify with `--help` if unsure.

**`--host 0.0.0.0` without `--insecure` fails.** The dashboard has a
safety check that refuses to bind to a non-local address without the
`--insecure` flag. The error message says: "Refusing to bind to
0.0.0.0 — the dashboard exposes API keys and config without robust
authentication." Add `--insecure` to override. Only use on trusted LANs.

**The session token is the only auth.** A random `_SESSION_TOKEN` is
printed at startup. Dashboard pages auto-inject it via
`window.__HERMES_SESSION_TOKEN__`. Anyone who can read the printed
URL+token gets full access — the dashboard is single-user. Do not expose
to the open internet.

## Checking Running Instances

```bash
hermes dashboard --status
```

## Stopping

```bash
hermes dashboard --stop
```

## Behind the Scenes

The dashboard plugin is loaded from:
```
plugins/kanban/dashboard/
├── manifest.json      # Plugin metadata, tab at /kanban
├── plugin_api.py      # FastAPI routes (thin wrappers around kanban_db)
├── dist/
│   ├── index.js       # Compiled React app
│   └── style.css      # Styling
```

The `plugin_api.py` wraps `hermes_cli.kanban_db` so all three surfaces
(CLI, gateway `/kanban`, web dashboard) share the same code paths.
Live updates arrive via `/events` WebSocket which tails the append-only
`task_events` table (WAL mode lets reads run alongside the dispatcher's
IMMEDIATE write transactions).