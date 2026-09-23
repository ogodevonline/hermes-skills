# Architecture / System Design Spec Format

Use this format when designing a multi-module system (not a single code change). It answers "what and why" before implementation begins. Implementation plans (per the main SKILL.md) come after this spec is approved.

## Where to Save

Spec-файлы сохраняй в Obsidian vault: `~/hermes-vault/<тема>/README.md` (оглавление) + `01-...md`, `02-...md` и т.д. с Obsidian-ссылками `[[file]]`.

**Плохо:** один файл на тысячи строк
**Хорошо:** README.md (TOC + ссылки) + отдельные файлы по темам с перекрёстными ссылками

## Hard Rules (Пользовательские требования)

### 1. Максимум 200 строк на файл

Ни один spec-файл не должен превышать 200 строк. Если содержимое не влезает — режь на тему/модуль/компонент, а не расширяй файл.

Признаки что пора резать:
- Раздел описывает независимую сущность (коллектор, БД, отчёты) → отдельный файл
- Описание одной сущности заняло >100 строк → значит внутри есть подсущности → выноси
- Секция Edge Cases / Error Handling выросла >30 строк → в отдельный файл `errors.md`

### 2. README.md — оглавление + cross-links

Каждый файл начинает spec-набор:
```
тема/
├── README.md       # Оглавление + сводная таблица решений + data flow
├── 01-database.md
├── 02-collector.md
└── 03-alerter.md
```

**README.md содержит:**
- Ссылки (`[[01-database]]`, `[[02-collector]]`) на каждый файл
- 1-2 предложения что в каждом файле
- Таблицу ключевых архитектурных решений (как в примере ниже)

### 3. Cross-links внутри файлов

Каждый spec-файл заканчивается блоком ссылок на смежные:
```markdown
## Связанные spec'ы
- [[01-database]] — схема хранения данных
- [[03-alerter]] — нотификации об ошибках
```

### 4. Пример структуры (≤200 строк каждый файл)

```markdown
# 02-collector.md

## Purpose
Собирает объявления с OLX.uz.

## Источник
- URL: https://olx.uz/d/etc
- Частота: каждый час

## Парсинг
[... ~80 строк логики ...]

## Edge cases
[... ~30 строк ...]

## Связанные spec'ы
- [[01-database]] — куда сохраняем результат
- [[03-alerter]] — если сборщик упал
```

## Spec Sections

### Section: Purpose
One paragraph: what the module does, why it exists, who uses it.

### Section: Files
| File | Responsibility |
|------|---------------|
| `src/module.py` | Does X |
| `src/utils.py` | Provides Y |

### Section: Interfaces
List every public function/class with:
- Signature (parameters + return type)
- Description of behavior
- Side effects (DB writes, network calls, file I/O)

```python
# Example
def upsert_listing(conn, listing: dict) -> int:
    """Insert a new listing or update existing (matched by url_hash).
    Returns listing id.
    Adds a row to price_history if price changed.
    """
```

### Section: Dependencies
- External libs (requests, beautifulsoup4, etc.)
- Internal modules (src.db, src.currency_converter)
- Stdlib modules (re, hashlib, json)

### Section: Edge Cases / Error Handling
List concrete edge cases by scenario, not generic "handle errors":

| Scenario | Behavior |
|----------|----------|
| Network timeout | Retry 3x with backoff, then log and skip |
| No price in listing | Store NULL, continue |
| All sources fail | Don't mark listings as sold |
| First run (empty DB) | Nothing to compare, skip |
| Duplicate URL | Upsert (update last_seen + add price_history row) |

### Section: Testing Strategy
Don't write tests yet. List what to test and how:
1. Parse real HTML fixture with BeautifulSoup
2. Verify all price formats: "300 000 000 сум", "300млн", "$80,000"
3. Verify date parsing: "Сегодня", "Вчера", "1 май"
4. Verify error fallback: 404 page, empty response

## Spec Organization (Multi-Module System)

```
specs/
├── ARCHITECTURE.md      # Overview: components, data flow, design decisions, error strategy
├── database.md          # Schema: all tables with CREATE TABLE, indices
├── collector_olx.md     # Per-source: URL, parse logic, edge cases
├── collector_insta.md   # Instagram: instaloader session, comment parsing, price extraction
├── currency_converter.md
├── report.md            # Report: sections, format, Telegram vs email
├── alerter.md           # Alerts: error categories, notification channels
├── cron_and_config.md   # Orchestrator, cron, config schema
└── requirements_spec.md # Python dependencies
```

Each spec covers one module. ARCHITECTURE.md is the index — it names all specs, shows data flow, and documents cross-cutting decisions (why SQLite, why requests+BS, why instaloader).

## Example: ARCHITECTURE.md table of decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| DB | SQLite | No server, single file, ~100 listings/day |
| HTTP | requests | Lightweight, no browser overhead |
| Instagram | instaloader (cookies) | Only free way without GraphQL API |
| Currency | CBU API | Free, no auth, official Central Bank |
| Scheduling | cron | Built-in, no infra |
| Report delivery | SMTP | Email to multiple recipients |
| Price extraction | regex + LLM | Regex covers 80%, LLM catches rest |

## When to Use This vs. writing-plans SKILL.md

| Situation | Use |
|-----------|-----|
| New multi-module system | Architecture spec (this file) |
| Single feature in existing codebase | Implementation plan (main SKILL.md) |
| Need both (design then build) | Architecture spec first → Approved → Implementation plan per module |