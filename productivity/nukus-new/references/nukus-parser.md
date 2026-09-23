# Nukus Parser Infrastructure

## Project location
`~/nukus-houses/`

## Entry point (LLM-based parsing)
```bash
cd ~/nukus-houses
rm -f nukus.db-wal nukus.db-shm  # clean stale locks after kill

# ⚠️ Использовать Hermes venv (3.11), НЕ system python3 (3.12 — нет bs4!)
PYTHONPATH="/home/hermes/nukus-houses:${PYTHONPATH:-}" /home/hermes/.hermes/hermes-agent/.venv/bin/python3 src/main.py config.json
```
⚠️ PYTHONPATH обязателен — иначе `from src.xxx` ломается.

## What it does
1. Parses OLX houses in Nukus — multi-page (up to 5 pages), ~44 listings per page
2. Each listing parsed via LLM (KiloCode) — SLOW, 5-10 min full run
3. Saves to `nukus.db`
4. Marks disappeared as sold
5. Generates HTML report (REPORT_PATH in stdout)

## Sources
- **olx** — `src/collectors/collector_olx.py`, enabled. Categories: houses, apartments, rent.
- **telegram** — REMOVED. Deleted from codebase, `"enabled": false` in config.json

## Quick report (no HTTP, from DB)
Script: `~/.hermes/skills/productivity/nukus-new/scripts/gen_report_interactive.py`
Reads DB directly, builds interactive HTML with JS filters (price, rooms, district, gas, phone, freshness).
Fast (~1s), no network calls.

## Excel (для заметок пользователя)
Script: `~/nukus-houses/gen_xlsx.py`
```bash
cd ~/nukus-houses && /home/hermes/.hermes/hermes-agent/.venv/bin/python3 gen_xlsx.py
```
Создаёт `~/nukus-houses/nukus_report.xlsx` с двумя листами (все объявления + только аренда),
цветовой маркировкой по цене, колонкой «Заметки», гиперссылками на OLX.

## Sending reports to Telegram
- **.xlsx** → `MEDIA:/home/hermes/nukus-houses/nukus_report.xlsx` в тело ответа (нормально)
- **.html** → НЕ слать на телефон (открывается как Excel). Только локально для ПК: `file:///home/hermes/.hermes/cache/documents/nukus_report.html`

## Database
- `nukus.db` — SQLite, tables: listings, sources, price_history, exchange_rates
- WAL files (`nukus.db-wal`, `nukus.db-shm`) — remove after abrupt process kill
- `database is locked` — happens in `cron_report.py` due to dual connections. Use `gen_report_interactive.py` instead (read-only).

## Cron
DISABLED per user request. Manual-only.

## Known bugs (починены 16.07.2026)

- **for loop indentation** — `_fetch()` и весь блок ниже были на том же отступе, что и `for page`. Цикл только логировал, загружалась только последняя страница. Фикс: переместить внутрь цикла.
- **filter `_is_rental`** — пропускал все объявления с "аренд/сдам/ижара". Для rent-категории убивал 100%. Фикс: `if cat_name in ("houses", "apartments")`.
- **filter `< 10 млн`** — пропускал все объявления дешевле 10 млн как "аренду". Для rent вырезал 1-5 млн. Фикс: `if cat_name in ("houses", "apartments")`.
- **Timeout** — LLM parsing takes 5-10 min. Run `background=true, timeout=600`.
- **Background pipe = silence** — don't pipe through `tail`, it buffers. Run without pipe.
- **ModuleNotFoundError: No module named 'src'** — forgot PYTHONPATH.
- **No new listings** — may be normal (all in DB). Check by first_seen date.
- **bs4/lxml missing** — system python3 (3.12) doesn't have them. Use Hermes venv python3 (3.11). Install: `uv pip install beautifulsoup4 requests lxml`.
- **Price slider min=50** — скрывал аренду (1-5 млн). Фикс: `min=0` в nukus_html_builder.py.
- **`r['price_sum']` is None** — TypeError в f-строке. Фикс: `{(r['price_sum'] or 0)/1e6:.0f}`.
- **Send HTML → user sees Excel** — .html на телефоне открывается в Excel. НЕ слать.
