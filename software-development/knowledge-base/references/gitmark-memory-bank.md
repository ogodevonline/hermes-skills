# GitMark Memory Bank — reference

**Repo:** https://github.com/vakovalskii/gitmark-memory-bank
**Author:** vakovalskii (Valera Kovalskii)
**License:** MIT
**Plugin for Claude Code:** `/plugin marketplace add vakovalskii/gitmark-memory-bank`

## Concept

"Самое простое и самое рабочее" — md + README(index) + git. Никаких сервисов, эмбеддингов, вендоров. Всё производное (индекс, HTML-граф) регенерится из md.

## CLI (один файл, 760 строк, чистый stdlib)

```bash
python3 scripts/gitmark.py index              # построить .gitmark/index.db (FTS5: bm25 + trigram)
python3 scripts/gitmark.py search "запрос"    # bm25 + trigram(substring) + fuzzy(typos)
python3 scripts/gitmark.py map -o map.html    # self-contained HTML: дерево + рендер md + радиальный граф
python3 scripts/gitmark.py stat               # статистика индекса
python3 scripts/gitmark.py lint               # инварианты онтологии I1–I6
python3 scripts/gitmark.py serve -p 8799      # локальный HTTP
```

## 3 стратегии поиска (в одном SQLite FTS5)

1. **bm25** — точные термины, ранжировка
2. **trigram** (`tokenize='trigram'`) — подстроки, кириллица, не-Latin
3. **fuzzy** — 4-символьные окна запроса OR'd, порог ≥20% покрытия → опечатки и морфология

## Онтология (Palantir-inspired)

- 9 типов: service, reference, runbook, gotcha, decision, plan, guide, report, index
- YAML frontmatter: node_type, title, service, status, updated, tags, links
- 6 typed link keys: documents, depends_on, supersedes, relates_to, implemented_by, part_of
- 6 инвариантов linter'a (см. SKILL.md или docs/ontology.md)

## Структура папок

```
CLAUDE.md / AGENTS.md       ← точка входа
/docs
  README.md                 ← мастер-индекс
  /services/<svc>/
    README.md               ← индекс папки-сервиса
  /reference/
  /ops/
  /decisions/
  /plans/
```

## Hermes port

- `gitmark.py` скопирован в `~/.hermes/scripts/gitmark.py`
- Skill `knowledge-base` создан (этот навык)
- Obsidian vault (`~/hermes-vault/`) заиндексирован
- Команды: `gms "<query>"` (поиск), `gmi` (переиндексация), `gmstat` (статистика)

## Routing rule (для Hermes)

Когда нужно найти информацию:
1. **Сначала** `gms "запрос"` — структурированный поиск с ранжированием
2. **Потом** `search_files` / `grep` — если индекс устарел или запрос по коду, а не по docs
