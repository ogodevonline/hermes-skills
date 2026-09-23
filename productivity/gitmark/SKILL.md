---
name: gitmark
description: >-
  Search and manage markdown knowledge bases using GitMark Memory Bank.
  FTS5 search (bm25 + trigram) + Gotham ontology linter + ForceAtlas
  canvas graph with expandable nodes. map command generates self-contained
  HTML with sidebar tree + interactive force-directed graph.
  УСТАНОВЛЕНО: upstream в /home/hermes/gitmark-memory-bank/,
  CLI через ~/.local/bin/gms (скрипт, не алиас).
  Obsidian vault (hermes-vault) проиндексирован ~250 файлов.
---

# GitMark — markdown knowledge base search

**0 external dependencies.** Single stdlib Python file. FTS5 search, Gotham ontology, ForceAtlas graph.

## Architecture (two files — don't confuse)

| File | What | Edit via |
|------|------|----------|
| `/home/hermes/gitmark-memory-bank/skills/kb-search/gitmark.py` | **Upstream** — git pull, active development. `cmd_map`, `_MAP_HTML`, `parse_frontmatter` | `patch` by absolute path |
| `~/.local/bin/gms` | **CLI wrapper** — calls upstream with `--root ~/hermes-vault` | `patch` or `nano` |
| `~/.hermes/scripts/gitmark.py` | Local copy (may be stale) | `skill_manage` (part of this skill) |

**`gms` is NOT an alias.** It's an executable script in `~/.local/bin/gms`. It calls the upstream version. If search returns empty results, check `--root` flag in this script.

## Quick commands

```bash
# Search vault
gms "аэрофлот"

# Reindex vault (always use --root!)
python3 /home/hermes/gitmark-memory-bank/skills/kb-search/gitmark.py --root ~/hermes-vault index --force

# Generate interactive graph
python3 /home/hermes/gitmark-memory-bank/skills/kb-search/gitmark.py --root ~/hermes-vault map -o /tmp/gotham.html

# Search Hermes system
hms "таймаут gateway"
```

## Search routing (MANDATORY)

1. **hms** — searching in `~/.hermes/` (skills, configs, scripts)
2. **gms** — searching in Obsidian vault (notes, journals, planning)
3. **search_files/grep** — only if both returned empty

## Commands

| Command | Description |
|---------|-------------|
| `index [--root .] [--force]` | Build/rebuild FTS5 index (bm25 + trigram) |
| `search "<q>" [-k N] [--json]` | Ranked chunk search with file:line and snippet |
| `stat` | Index statistics |
| `map [-o file.html]` | **Self-contained HTML**: sidebar tree + ForceAtlas graph + document viewer |
| `lint [paths] [--strict]` | Gotham ontology check (I1–I6 invariants) |
| `serve [-p 8799]` | Local HTTP server for the map |
| `version` | Version |

## map command — ForceAtlas graph with fold/unfold

The `map` output has two tabs:

### Дерево (sidebar tree)
- Files listed by area (folder)
- Colored by `node_type` from frontmatter
- Search/filter input
- Click → opens document in right panel

### Граф (ForceAtlas canvas)
- **Canvas 2D ForceAtlas** — n-body repulsion + spring edges
- **Fold/unfold by click** — папки раскрываются/сворачиваются по клику
- **Start state**: only root + top-level folders (~10 nodes)
- **Click folder** → reveals children, ForceAtlas disperses them
- **Click file** (leaf node) → opens document (via right panel, switches to browse tab)
- **Shift+drag** a node → manual repositioning
- **Drag on empty space** → pan
- **Mouse wheel** → zoom (centered on cursor)
- **"F" button** — fit all visible nodes to viewport
- **Text always visible** — rendered per frame on canvas, not zoom-dependent
- Hover highlight on mouseover

### Data flow
```
Python cmd_map()
  ├── parse frontmatter → node_type, status, links.parent
  ├── build tree: parent links from frontmatter, else by folder (area)
  ├── orphan grouping: >10 files without parent → group by area node
  └── JSON → mindmap_tree {"content", "type", "children"}

JavaScript initFA()
  ├── flatten tree → all nodes + edges, mark depth
  ├── initial visibility: depth <= 1 (root + folders)
  ├── ForceAtlas: 30 iterations, rep=5000, ks=0.04, damp=0.85
  ├── auto-fit after layout
  └── requestAnimationFrame render loop
```

### Key implementation details
- **No CDN, no libraries** — vanilla Canvas 2D API
- `FA.nodeMap` — lookup by id for O(1) access
- `FA.childMap` — parent→children for fold/unfold
- `syncFA()` — rebuilds visible nodes/edges from visibility flags
- `_posSet` flag — new nodes spawn near parent on first sync
- `fitFA()` — computes bounding box, centers with scale ≤ 0.8
- `hitTestFA(mx, my)` — distance-based click detection with (n.r+8)² threshold

## Gotham ontology

GitMark uses typed **objects** (documents) with **properties** (YAML frontmatter) and typed **links** (parent, depends_on, documents…). 19 node types defined in AGENTS.md. `gitmark lint` checks 6 invariants (I1–I6).

## hms — search over ~/.hermes (all file types)

Separate FTS5 indexer for Hermes system files. Covers .md, .yaml, .py, .toml, .json, .sh, .txt, .env. ~6700 files indexed.

## Pitfalls & lessons

### map command
- **ForceAtlas > static mindmap.** User explicitly wants force-directed graph with fold/unfold, not tree layout. Started with radial canvas → markmap CDN → vanilla SVG mindmap → finally ForceAtlas. The first canvas approach was closest to what user wanted; the problem was too many nodes at once, which fold/unfold solves.
- **Always use canvas for force-directed graphs.** SVG with hundreds of elements is slow. Canvas 2D + requestAnimationFrame handles 250+ nodes at 60fps.
- **Fold/unfold is essential for >20 nodes.** Without it, force graph is unreadable. Start with root + 1 level, unfold on demand.
- **Coordinate transforms: apply once.** When using `ctx.translate/scale`, draw in world coordinates. Don't manually multiply by view.k in individual draw calls — causes double-transform bug where edges/positions drift during zoom.
- **JS constants must be global scope.** `const NODE_H=20` inside one function is invisible to another. If `layoutMM()` and `renderMM()` both use it — define at top of script. ReferenceError crashes the entire graph.
- **setTimeout(50-100ms) before init.** Canvas/element dimensions are 0 if the container was just unhidden. Wait one frame for layout.
- **Canvas events: transform mouse coords to world.** `hitTest` must invert the view transform: `(mx - view.x) / view.k`, not raw mouse coords.
- **Patch large JS carefully.** Replacing `function foo(){...}` by matching only the first line leaves the function body dangling as dead code. After patch, verify syntax opens in browser.
- **No CDN.** User opens HTML via file:// protocol with no internet. Every `<script src="cdn...">` guarantees blank screen. Zero external dependencies mandatory.

### Search
- **`gms` is a script, not an alias.** Lives at `~/.local/bin/gms`. To add `--root`, edit that file, not .bashrc.
- **Two gitmark.py files.** Upstream at `gitmark-memory-bank/` (git repo) and local copy at `~/.hermes/scripts/`. `gms` calls upstream. Patch both if changing core logic.
- **Without `--root`, index is built from cwd.** Running `gmi` from `/home/hermes` indexes 1359 system files instead of 247 vault files → search returns empty. Always use `--root ~/hermes-vault` or cd into vault.
- **YAML frontmatter parser is stdlib-only.** Inline `links: {parent: [val]}` not supported. Use multiline format. Test after patching `parse_frontmatter`.

### Telegram file delivery
- **`source .env` breaks tokens with `*`.** Bash glob expands `***`. Read via Python `startswith()` + `split('=',1)`.
- **Write a reusable `send_gotham.py` script** instead of crafting curl commands each time. Saves iterations.
