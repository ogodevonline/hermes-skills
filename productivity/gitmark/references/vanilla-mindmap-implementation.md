# Vanilla SVG Mindmap — implementation notes

## Status: UNSTABLE (v0.3.0)

The `gitmark map` command currently generates a vanilla SVG mindmap that
**does not work reliably**. User reports:
- Black screen on mindmap tab
- JS ReferenceErrors (NODE_H scope, switchTab logic)
- Tab switching broken

**Do not send this HTML to the user expecting it to work.** Debug in
browser console first.

## Planned direction: ForceAtlas with expandable nodes

The user explicitly requested a **ForceAtlas-style circular graph**:

1. **Равноудалённые расстояния** — nodes repel each other equally
2. **Раскрывашки (folding)** — click a folder node to expand/collapse its children
3. **Отталкивание** — force-directed layout, nodes push each other apart
4. **Рёбра вытягиваются, связь сохраняется** — edges act as springs
5. **Самое главное видно сразу** — start with collapsed view, click to reveal

This is a **return to the canvas ForceAtlas** approach from v0.1.0, but with
incremental node expansion instead of showing all 247 nodes at once.

### ForceAtlas implementation constraints
- Pure JS, no CDN (file:// restrictions)
- Canvas 2D or SVG
- Start with only root + 1 level visible
- Click expands only that node's direct children (not all levels)
- Text always visible (not hidden until zoom)
- Repulsion force: ~4000, edge spring: ~0.045 (tuned for ~50 visible nodes)

## Why not markmap / obsidian graph / canvas (all-at-once)

- markmap needs CDN (d3 + markmap-view) — doesn't work offline. Confirmed: user opened HTML locally, CDN didn't load, black screen.
- Canvas 2D (all 247 nodes at once) — text overlaps, edges unreadable. Confirmed: user reported "названия друг на друга налезают, связей не видно".
- Obsidian graph is proprietary and doesn't integrate with gitmark CLI.

## Folder grouping (critical)

When parent links are missing, group orphans by area (folder):

```python
area_nodes: dict[str, list] = {}
for rel in children_of.get("__root__", []):
    area = files[rel]["area"]
    area_nodes.setdefault(area, []).append(rel)
for area, rels in sorted(area_nodes.items()):
    if len(rels) > 1:  # folder node with children
    else:  # single file, direct child of root
```

247 orphans on one level = impossible to read. 9 folders x ~27 files = usable.
This is also how ForceAtlas should start — show only folders, expand on click.

## Layout algorithm (current, for SVG mindmap)

```
function layoutSub(id, x, top, bottom):
  n.y = (top + bottom) / 2
  children.forEach(child => {
    h = visibleChildren(child.id) * NODE_H
    layoutSub(child.id, x + LVL_W, cur, cur + h)
    cur += h + GAP
  })
```

## Auto-fit initial viewport

After layout, trees often extend far above/below the SVG viewport.
Without auto-fit, 247 nodes render at Y=-2000 and are invisible.

```js
maxY = max(nodes.map(n => n.y + NODE_H))
minY = min(nodes.map(n => n.y))
scaleX = fitW / (maxX + 40)
scaleY = fitH / (maxY - minY + 40)
view.k = min(1, min(scaleX, scaleY))
view.x = 40
view.y = (-minY + 20) * view.k + (H - (maxY - minY + 40) * view.k) / 2
```

## Known bugs (all fixed in v0.3.0 but graph still broken)

| Bug | Symptom | Fix |
|-----|---------|------|
| switchTab inverted | Mindmap tab shows doc pane | doc.hidden=m; mm.hidden=!m |
| Double transform in renderMM | Edges offset from nodes during zoom | Use world coords in SVG |
| main() KeyError after cmd_map refactor | gitmark map crashes | Sync print() with return dict keys |
| Dangling function body after patch | JS ReferenceError | Check old_string includes full body |
| initMM called while #mm hidden | Layout at Y=-2000 (invisible) | setTimeout(50) before init |
| No folder grouping | 247 nodes on one unreadable level | Group orphans by area |
| No auto-fit | Tree renders outside viewport | Calculate scale/offset after layout |
| Missing #search input in HTML | JS TypeError: Cannot set oninput of null | Keep `<input id='search'>` in markup |
| getContext('2d') returns null | measureText throws | try/catch with fallback width=120 |
| innerHTML='' on SVG element | Fails silently on some browsers | Use while(firstChild) removeChild |
| MM.svg null on init | Cannot read clientWidth of null | Check MM.svg before use |
| **NODE_H scope in layoutMM** | **ReferenceError in renderMM** | **Hoist NODE_H to global scope (before initMM)** |

### NODE_H scope: the hidden trap

`const NODE_H=20` was initially defined inside `layoutMM()` function. But
`renderMM()` also uses it for `bg.setAttribute('height', NODE_H+4)`.
Since `renderMM()` is called from outside `layoutMM()`, NODE_H was
undefined there → ReferenceError.

**Fix:** Move `const NODE_H=20` to global scope, right after the `let MM={}` block.

**Lesson:** When sharing constants between layout and render functions, define them
at the top of the script, not inside any function. Same applies to `LVL_W`, `GAP`.

## file:// protocol restrictions

When HTML is opened via `file://` protocol, browsers apply strict security:
- **No CDN loading** — d3, markmap-view, katex all fail silently
- **No web workers** — some SVG operations restricted
- Unique origin — cross-frame access blocked (harmless, just a console warning)

**This means:** every gitmark map HTML MUST be fully self-contained (0 external deps).
CDN links in `<script src>` will fail. All JS/CSS must be inline.
The warning `Unsafe attempt to load URL file:///...` is benign — ignore it.

## Node type colors

- journal: #4ec9ff (blue)
- plan: #00ff88 (green)
- person: #ffb454 (orange)
- project: #c586ff (purple)
- book: #ff6ec7 (pink)
- note: #9ece6a (green)
- system-note: #7c9cff (light blue)
- agent-memory: #bb9af7 (lavender)
- index: #9aa0a6 (grey)
- reflection: #f7768e (red)
- task: #e0af68 (yellow)
- log: #73daca (teal)
- root: #00ff88 (green, entry point)
- folder: #565f89 (dark grey)
- default: #7dcfff (light blue)
