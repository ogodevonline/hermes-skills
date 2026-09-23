# Gotham Map — онтологическая визуализация vault

**Команда:** `gitmark --root ~/hermes-vault map -o /tmp/gotham-map.html`
**Версия:** gitmark v0.2.0 (июнь 2026)

## Что изменилось

Раньше `gitmark map` рисовал граф "кто на кого сослался" — ноды
раскрашивались по папкам (area_of()), все рёбра были `kind: "ref"`.
Бесполезная каша.

Теперь граф использует Palantir Gotham-онтологию:

### Ноды — цвет по node_type

| node_type | Цвет | Статус | Визуализация |
|-----------|------|--------|-------------|
| journal   | #4ec9ff синий | draft | пунктирная обводка |
| plan      | #00ff88 зелёный | active | сплошная |
| person    | #ffb454 оранжевый | done | зелёное свечение (glow) |
| project   | #c586ff фиолетовый | archived/cancelled | полупрозрачные (α=0.3) |
| book      | #ff6ec7 розовый | — | — |
| note      | #9ece6a зелёный | — | — |
| system-note | #7c9cff голубой | — | — |
| agent-memory | #bb9af7 лавандовый | — | — |
| index     | #9aa0a6 серый | — | — |
| reflection | #f7768e красный | — | — |
| task      | #e0af68 жёлтый | — | — |
| log       | #73daca бирюзовый | — | — |

### Рёбра — цвет/стиль по типу связи (links.*)

| Ключ | Цвет | Стиль | Семантика |
|------|------|-------|-----------|
| parent | синий 0.5 | пунктир 6,4 | родительская папка |
| depends_on | красный 0.6 | пунктир 2,4 | блокирующая зависимость |
| documents | синий 0.5 | сплошная | документирует |
| created_by | зелёный 0.5 | пунктир 4,4 | кем создан |
| part_of | фиолетовый 0.5 | сплошная | часть чего-то |
| related | серый 0.3 | пунктир 4,6 | связанная заметка |
| supersedes | оранжевый 0.5 | пунктир 2,6 | заменяет устаревшее |
| ref | зелёный 0.13 | сплошная | простая markdown-ссылка |
| own | серый 0.07 | сплошная | папка→файл |

### Легенда

Показывает типы нод (по популярности) + typed link счётчики + статус-подсказку.

### Тултип при наведении

`имя файла [node_type] · путь · N шагов · status: draft/active`

## Архитектура изменений

### Python (cmd_map, строка ~493)

1. Парсит frontmatter каждого .md через `parse_frontmatter()`
2. Извлекает `node_type` (fallback `"note"`), `status` (fallback `"draft"`)
3. Собирает typed links из `links:` словаря: для каждого ключа (parent, depends_on, etc.)
   резолвит ссылку через `resolve_link()` и добавляет edge с `kind: <link_kind>`
4. В data.stats добавляет `typed: {kind: count}` для отображения в шапке

### JavaScript (_MAP_HTML, строка ~695+)

1. `NC` — словарь цветов нод по node_type (19 типов + default)
2. `EC` — словарь цветов рёбер по kind (8 типов + ref/own)
3. `NT_LABEL` — русские названия типов для легенды
4. `startG()` — маппит node_type → col, status → dim/dashed/glow
5. `startG()` — маппит kind → col/sty (dash pattern)
6. `draw()` — рёбра: `setLineDash(e.sty)` + `strokeStyle = e.col`
7. `draw()` — ноды: dim (α=0.3), dashed (ctx.setLineDash), glow (зелёная обводка)
8. `legend()` — группировка по node_type, показ typed links, подсказка статусов
9. `statStr()` — отображает typed link счётчики в шапке
10. Тултип — node_type цвет + label + статус

## Связанные файлы

- `gitmark.py` — cmd_map (строка ~493), _MAP_HTML (строка ~695)
- `SKILL.md` — основная документация навыка

### Физика и навигация (v0.2.0 upgrade, 16.06.2026)

После жалобы "README в центре, остальное по кругу нечитабельно" — переработана
визуализация:

1. **Physics (ForceAtlas) включён по умолчанию** — галочка `свободный режим`
   стоит checked с первого открытия графа. Ноды не на кольцах, а в свободном плавании.
2. **Repulsion 2200→4000** — ноды не слипаются при 247+ файлах.
3. **Текст подписей виден всегда** — убрано условие `v.k > 1.7`.
   Каждая нода имеет подпись при любом зуме.
4. **Клик по ноде = refocus** — клик на doc-ноде перестраивает BFS от неё.
   Новая функция `refocus(rel)` на чистом JS пересчитывает level/angle/gap
   по существующим данным (без перегенерации HTML). Работает и в physics, и
   в радиальном режиме.
5. **Кнопка `◎ центр: README`** — сброс refocus на корень.
6. **Начальный зум 1.2x** — чуть ближе, чем было.
7. **Hint обновлён** — "клик по точке → новый центр".

### JS-изменения для refocus

```js
function refocus(rel){
  // BFS от rel по G.edges
  const adj = {};  G.edges.forEach(e => {
    (adj[e.s]=adj[e.s]||[]).push(e.t);
    (adj[e.t]=adj[e.t]||[]).push(e.s);
  });
  // level, parent, children, leaf, ang — полный пересчёт
  // как в Python-версии BFS, только на JS
  // layout() перезапускает позиции
}
```

### Изменения gms (скрипт)

`~/.local/bin/gms` — исправлен: добавлен `--root ~/hermes-vault`.
Раньше искал по cwd, возвращал пустые результаты.
Теперь:
```bash
exec python3 /home/hermes/gitmark-memory-bank/skills/kb-search/gitmark.py \
  --root "$HOME/hermes-vault" search "$@"
```

## Известные проблемы

- `parse_frontmatter()` не умеет inline `links: {parent: [val]}` — только многострочный
- Если файл не имеет frontmatter, node_type=`"note"`, status=`"draft"` — все такие файлы выглядят одинаково зелёными
- Для vault с 247+ файлами HTML получается ~1.5MB — не проблема для локального просмотра
- refocus() не обновляет legend (показывает типы всего vault, а не поддерева) — не критично
- При 500+ файлах physics может тормозить (requestAnimationFrame + O(n²) repulsion)
