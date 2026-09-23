---
name: nukus-houses-pipeline
category: productivity
description: "Pipeline для парсинга недвижимости Нукуса: OLX + Excel/HTML. Баги и фиксы парсера."
---

# Nukus Houses Pipeline

## Quick start

```python3 ~/.hermes/skills/productivity/nukus-new/scripts/nukus_new.py``` — shows new listings from last 7 days.

## Full pipeline

### Step 1: OLX parse

```bash
cd ~/nukus-houses
rm -f nukus.db-wal nukus.db-shm
PYTHONPATH="/home/hermes/nukus-houses:$PYTHONPATH" /home/hermes/.hermes/hermes-agent/.venv/bin/python3 src/main.py config.json
```

Sources in config.json: `houses` (sale), `apartments` (sale), `rent` (rental).

### Step 2: Excel

```bash
cd /home/hermes/nukus-houses && /home/hermes/.hermes/hermes-agent/.venv/bin/python3 gen_xlsx.py
```
* Two sheets: "All" (color-coded) + "Rent"
* Column "Notes" — empty for user annotations

### Step 3: HTML (optional, PC only)

```bash
cd ~/.hermes/skills/productivity/nukus-new/scripts && python3 gen_report_interactive.py
```

### Deliver to user

* **NEVER send .html to phone** — opens as Excel garbage.
* **.xlsx** via `MEDIA:/home/hermes/nukus-houses/nukus_report.xlsx` in response body
* **Text** — top-5 listings with prices + OLX link

## Known bugs & fixes (July 2026)

1. **Loop indent bug.** `_fetch()` was outside `for page` — only last page loaded. Fix: move inside loop.
2. **`_is_rental()` kills "rent" category.** Rental keyword filter skipped everything. Fix: skip only for sale categories.
3. **`< 10M sum` filter kills rentals.** Skipped all cheap listings as "probable rental". Fix: apply only to sale categories.
4. **Price slider min=50.** Rentals (1-5M) invisible. Fix: min=0.
5. **NULL price_sum crash** in HTML builder. Fix: `{(r['price_sum'] or 0)/1e6}`.
6. **Google Sheets batchUpdate** requires `"fields": "userEnteredFormat"`. sheetId is random, not 0/1.

## Budget planning (3-currency)

User wants ALL amounts in RUB / USD / UZS. Always show all three.

* Kurs: 1 USD = 77.96 RUB, 1M UZS = 6,515 RUB, 1 USD = 11,970 UZS (July 2026)
* Rent in Nukus: 1.2-5M UZS/month (~7,800-32,600 RUB)
* Sale 1-room apt: 50-250M UZS (~326K-1.6M RUB)

**User's typical budget calc (July 2026):**
- Своих средств: карта РФ + кеш USD + ЗП (1-6 авг) + остаток за отпуск
- Кредитка: считать как заёмные, не как свои (идеал — не трогать)
- Комиссии: Сбер (снятие кредитки 3%, мин 390 ₽) + Золотая Корона (~1%)

**Google Sheets integration:**
- Создаётся через `update_sheets.py` в `/home/hermes/nukus-houses/`
- API v4: `"fields": "userEnteredFormat"` обязателен в `repeatCell`
- `sheetId` — случайный (не 0/1), получать через `spreadsheet.get()`
- Цветовое кодирование: зелёный ✅ сценарии, красный ❌ сценарии

## Instagram as source — insta_flat_parser (active)

Приватный репозиторий `ogodevonline/insta_flat_parser` — Telegram бот для парсинга Instagram.
**Полный гайд по деплою:** `skill_view('nukus-houses-pipeline', 'references/insta-flat-parser-deploy.md')`

Проблема: на headless VPS Instagram login не работает. Нужна готовая сессия с компа.

⚠️ **ВАЖНО:** session-файл кладётся в `~/.config/instaloader/session-<email>.json`,
НЕ в `~/.insta_flat_parser/`. См. `references/insta-flat-parser-deploy.md` (раздел «КРИТИЧЕСКИЙ БАГ»).

**Кодовая база:** `~/Projects/Personal/GitHub/insta_flat_parser/src/insta_flat_parser/`
- Зависимости: `uv sync` + `uv run playwright install chromium`
- Запуск демона: `uv run python -m insta_flat_parser bot`
- Сброс БД перед первым запуском: `rm -f ~/.insta_flat_parser/state.db`
- Cloudflared туннель: `/tmp/cloudflared tunnel --url http://localhost:8080`
- Сессия: `~/.config/instaloader/session-<email>.json` (с компании, через zip)

Старая схема (instaloader, неактивна):
1. Add IG account sessionid + realtor accounts to config.json
2. instaloader fetches posts + comments + video metadata
3. Video→text: ffmpeg extract audio → Whisper/Яндекс SpeechKit transcribe

**API options (2026):**
- Free: `instaloader` (open-source, уже стоит) — посты + комменты, сессия от твоего IG
- Paid RUB: **instaloader (бесплатно)** — парсинг постов; транскрибация через **Яндекс SpeechKit** (~0.28 ₽/мин, рубли)
- Paid USD: HikerAPI ($0.0006/req), RocketAPI (€49/мес), EnsembleData ($100+/мес)

**Транскрибация — Яндекс SpeechKit (рубли):**
- Асинхронное распознавание: ~0.28 ₽/мин
- 1000 Reels (~30 сек): ~140 ₽
- Оплата рублями через Яндекс.Облако
- Python SDK есть

**Локальный Whisper (бесплатно, ресурсы):**
- tiny/base (~1-1.5 GB RAM) — влезает на 4.8 GB VPS
- medium/large — не влезают

## References

* `references/instagram-parsing.md` — deep research on Instagram parsing APIs
* `references/insta-flat-parser-deploy.md` — полный гайд по деплою и модификациям бота
