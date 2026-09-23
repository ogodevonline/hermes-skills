---
name: classifieds-scraper
title: Classifieds Scraper
description: >-
  Scrape listing sites (OLX.uz, etc.) — SSR HTML approach with httpx+BS4,
  price extraction, deduplication. Avoids Playwright/crawl4ai for speed
  and fewer blocks.
triggers:
  - user asks to scrape OLX / classifieds / listing sites
  - task involves extracting structured data from search page cards
  - site returns SSR HTML (not JS-rendered)
  - user wants a multi-source listing monitor (OLX + Telegram + report + cron delivery)
  - task involves setting up scheduled report generation for scraped listings
  - user needs to find Telegram channels for a specific location/niche
  - user asks to fix/update a scraper (rental filter, new fields, stale selectors)
  - user has existing DB entries that need backfill with new fields (phone, rooms, area, district)
  - user asks to improve report data quality (add fields, fix dates, clean phones)
---

# Classifieds / Listing Sites — Scraping Guide

## General Approach

1. **NO Playwright/crawl4ai** unless the site is JS-only. SSR HTML is faster,
   lighter, and avoids CloudFront/CDN blocks. Use httpx (async) + BS4 (lxml).

2. **Strategy order:**
   - First: JSON-LD (`script[type="application/ld+json"]` — check for
     `@type: ItemList` on search pages, `@type: Product` on detail pages).
   - Fallback: HTML card selectors (specific CSS classes).
   - NEVER rely on JSON-LD being present — sites change.

3. **Card structure varies by site.** Always inspect the raw HTML first
   with a quick test script before writing the collector.

4. **Price extraction:**
   - Look for `<p>` / `<span>` / `<strong>` containing "сум" or "$".
   - Strip suffixes like "Договорная" appended without space.
   - Normalise: "200 000 000 сум" → 200000000; "300 млн" → 300000000.
   - Watch for first-number traps: "6 соток.620 000 000 сум" — the first
     number (6) is area, not price. Extract from the PRICE element only.

5. **Detail pages:** JSON-LD Product is the most reliable source for price,
   title, and description on platforms that embed it (OLX, BirBir).

   **Two strategies for extracting extra fields (rooms, area, floor, phone):**

   **A) LLM-based extraction (preferred for frequently-changing HTML):**
   Collect the visible page text (description + characteristics list + breadcrumbs)
   and send it to a LLM (DeepSeek, GPT-4o-mini) with a structured extraction prompt.
   The LLM handles non-uniform data — some listings have params in tables,
   others only in free-text descriptions. Phone numbers embedded in descriptions
   are found reliably this way.

   Use when: the site changes HTML structure frequently, data is spread across
   structured + unstructured fields, or when phone numbers are JS-masked in the
   UI but present in description text.

   **B) BS4 + selectors (for stable/SSR HTML):**
   Find specific CSS classes or data-attributes for feature rows.
   Test against live HTML before writing — sites change often.
   Fall back to regex on the full description text for gas/water/wall material.

6. **Rental filtering:** Always detect and skip rental listings at scrape time:
   - Scan title for keywords: ижара, аренда, сдам, rent, суточн, посуточн
   - Price < 10 million сум/month is almost certainly a rental, not a sale
   - Apply filter before writing to DB so rentals never pollute the dataset
   - Consult the user early — they may want rentals tracked separately

7. **Phone numbers:** Many classified sites (OLX, etc.) mask phone numbers
   behind JS reveal buttons. Don't waste time trying to scrape them —
   the HTML contains only masked digits like +998****3335. Note this
   limitation to the user early and move on.

## Directory / Catalog Sites (32top.uz pattern)

Business-directory/catalog sites (32top.uz clinic listings, similar catalogs)
mask phones in the LISTING page behind a JS "Показать телефон" popup, but the
entity DETAIL pages are SSR and only *inconsistently* protected — some phones
are fully present in the HTML. Enumerate detail pages instead of fighting the
listing popup:

1. Fetch the listing page with curl (browser UA); extract entity hrefs with
   numeric IDs: `re.findall(r'href="(/nukus/clinics/(\d+)/)', html)` → all
   entities at once (e.g. all 13 Nukus dental clinics).
2. Loop each detail URL with curl; regex full phones from SSR text:
   `re.findall(r'\+998[\s\-()]*\d{2}[\s\-()]*\d{3}[\s\-()]*\d{2}[\s\-()]*\d{2}', raw)`.
3. Coverage is PARTIAL by design — phones behind the JS popup are absent from
   SSR. Expect ~1/3 of entities to yield phones; the rest need the JS click.
4. Do NOT burn time on per-name web search for the missing ones — small local
   businesses (clinics, services) often have zero web presence and searches
   return nothing. That is a signal, not a query problem.
5. Hand the JS-masked remainder to a human on the MOBILE site: the reveal
   button works in a phone browser; on desktop/headless it needs JS (httpx
   cannot do it). This closes the gap in minutes.
6. goldenpages.uz masks phones as XX-XX even on detail pages — useless as a
   phone source; use it only for names/addresses/rubrics.

## Key Lesson: trafilatura + web_extract Beat Custom Scripts

**For any classified detail page, NEVER write a custom httpx+BS4 script from scratch.**
Always try these tools FIRST, in this order:

### 1. trafilatura (preferred — works offline, no API calls)

`trafilatura` is a Python library that extracts clean text from HTML pages.
It removes navigation, ads, scripts, and returns only the readable content.
Works perfectly for OLX detail pages with SSR HTML.

```python
import trafilatura, json

downloaded = trafilatura.fetch_url(url, timeout=15)  # NO timeout arg! Use httpx then trafilatura.extract()
# Better: httpx + trafilatura.extract
r = httpx.get(url, headers=headers, timeout=20)
parsed = trafilatura.extract(r.text, output_format='json', with_metadata=True)
data = json.loads(parsed)
text = data.get('text', '')  # Clean structured text
raw = data.get('raw_text', text)  # Original text with some formatting
```

Output format:
```json
{
  "title": "Ипадром елатинда Сатылади: 160 000 000 сум - Продажа Нукус на Olx",
  "text": "Частное лицо\nКоличество комнат: 2\nОбщая площадь: 6 м²\nЖилая площадь: 37 м²\n...",
  "raw_text": "Частное лицо Количество комнат: 2 Общая площадь: 6 м² ...",
  "date": "2025-02-13",  // NOTE: trafilatura's date is not the listing date!
  "excerpt": "...",
  "image": "https://...",
  "source": "https://..."
}
```

**Key insight:** trafilatura's `date` field is the page metadata date, NOT the listing
publication date. The real date is in the `text` field as "Опубликовано 30 апреля 2026 г."
Always parse the date from `text`, not from the metadata.

**Crawl4ai does NOT work for OLX** — CloudFront blocks headless Playwright browsers,
even with stealth settings (magic=True, simulate_user=True, override_navigator=True).

### 2. web_extract (internal tool — use when trafilatura unavailable)

Returns clean markdown text with all visible data. Produces output like:
```
Количество комнат: 4
Общая площадь: 6 м2
Жилая площадь: 37 м2
Площадь участка: 6
Этажность дома: 1
...
Описание: [text]
Цена: [price]
Опубликовано: [date]
```

This text is directly parsable — no CSS selectors needed.

### 3. NEVER write test scripts for detail pages

When the user says "проверь на одном", respond by calling `web_extract` or `trafilatura`
on the URL, not by writing a new Python script. Writing a test script introduces:
- API key path resolution bugs (`.env` not found)
- Heredoc encoding corruption with кириллица
- Timeout errors from httpx in sandboxed environments
- Confusing stderr/stdout interleaving
The user will get frustrated when you spend 5+ rounds debugging a test harness.
These tools already work. If they fail, THEN write targeted code for the specific gap.

## Detail Page: Hybrid Approach (web_extract + regex + LLM)

**Best quality (proven in production):**

1. **web_extract** → get clean page text (one API call per URL)
2. **Regex** → extract phone from the raw text (998XXXXXXXX pattern)
3. **Remove all phone numbers from the text** → send to LLM for:
   - Structure extraction (rooms, area, floor, material, gas, water, etc.)
   - Translation of description from local language → Russian
4. **Merge** phone (from regex) with structure (from LLM)

**Why separate phone from LLM:**
- OLX embeds masked numbers (`+998****3335`) in the description text
- LLMs **always** return the masked version even when:
  - The full number (`998979416070`) is present in the input text
  - The prompt explicitly says "use the full number, not the masked one"
  - The system prompt says "never use asterisks in phone numbers"
  - You remove the masked version and keep only the full one
  This is a hard behaviour in training — don't fight it, work around it.
- Regex reliably finds the full number if it exists (pattern: `998\d{9}` after
  stripping spaces and newlines from the raw text).
- Telegram then masks the full number in its display, which creates confusion
  during debugging — the code is correct, the display lies. Hex-dump to confirm.

**Phone workflow (exact steps):**
1. Get raw text from page (web_extract or httpx+BS4)
2. Strip all spaces and newlines: `text.replace(' ', '').replace('\n', '')`
3. Apply regex: `re.search(r'998(\d{9})', cleaned)`
4. Full number: `'+998' + m.group(1)` or display-safe: `f"998 {d[:2]} {d[2:5]} {d[5:7]} {d[7:9]}"`
5. Remove ALL phone-like substrings from the text sent to LLM:
   `re.sub(r'Телефон\s*998[\s\d]*\d{2}', '', text)`
6. LLM gets clean text (no phones), returns structure + translation
7. Merge: add extracted phone to LLM result after parsing

**When to use this vs pure LLM:**
- Use hybrid for user-facing reports where data accuracy matters
- Use pure LLM (batch) for backfill of existing DB entries — but expect
  masked phones in output and plan a post-LLM regex pass
- Use pure BS4 only if web_extract is unavailable or takes too long

## OLX.uz (2026)

See `references/olx-uz.md` for current selectors and structure.

## Pitfalls

- **Цикл по страницам — проверять отступ `_fetch()`.** Python async-код с циклами страдает багом индентации: `for page in range(1, max_pages + 1):` с логированием *внутри*, а `html = await self._fetch(url)` — на том же отступе, что и `for` (снаружи цикла). Симптом: в логах все "page N/5" в одну миллисекунду, HTTP-запрос только один (последний). Фикс: переместить `await self._fetch(url)` и весь блок обработки *внутрь* цикла `for page`.

- **Rental filter может убить категорию аренды.** Если парсер отфильтровывает аренду по ключевым словам (`_is_rental`: ижара, аренда, сдам, суточн) ИЛИ по цене (< 10 млн сум), то dedicated категория "rent" с ценами 1-5 млн будет полностью вырезана. Фикс: применять фильтры только для категорий продажи (`"houses"`, `"apartments"`), а для `"rent"` — пропускать.

- **LLM-based parsing is SLOW for batches:** Each detail page requires a separate LLM API call (~3-5s each through KiloCode). For 44 listings × 5 pages = 220 calls, expect 11-18 minutes of runtime. Set `timeout` >= 600s in cron config or run in background. Consider batching calls where the LLM API supports it (send N descriptions in one prompt) instead of one-at-a-time extraction.
- **Stale selectors:** OLX changes CSS classes on every UI update. Test
  periodically and update the reference file.
- **JSON-LD absent on search:** OLX search pages have NO ItemList anymore
  (only WebPage + Product + BreadcrumbList). Only HTML cards work.
- **Price suffix bleeding:** "200 000 000 сумДоговорная" has no space
  between "сум" and "Договорная". Pre-clean with regex before normalising.
- **Area vs price:** The card's outer div contains BOTH title+price data.
  Extracting from the outer div picks up the first number (e.g. "6" from
  "6 соток") as the price. Always target the SPECIFIC price element.
- **Budget filtering:** Apply AFTER parsing (some listings above budget
  might need to be updated). Filter new listings only.
- **CloudFront blocks:** Plain httpx works where Playwright/crawl4ai gets
  blocked (OLX serves SSR HTML but blocks headless browsers).
- **OLX card area is in ambiguous units:** OLX displays area as a bare
  number with "м²" appended regardless of unit. "16 м²" on a card can
  mean 16 соток (= 1600 м²) or 16 м² — the title is the only clue.
  Don't treat it as authoritative square metres.
- **OLX breadcrumbs changed (May 2026):** No longer `<a data-cy="breadcrumb-link">`
  elements. Now a single `div[data-cy="categories-breadcrumbs"]` with all
  categories concatenated. Update parsing accordingly.
- **OLX phone is JS-masked:** The HTML shows only masked numbers like
  +998****3335. Do not attempt to scrape phone from OLX — it requires
  a JS click on "Показать телефон" which httpx cannot do.
- **Telegram channels for small cities (e.g. Nukus):** Useless. The channels
  are stale, private, repost from OLX, or have fewer than 5 relevant listings
  after weeks of monitoring. Don't add Telegram as a source — it wastes LLM
  calls, cron runtime, and DB space. The user will eventually tell you to
  delete it. Focus on OLX as the primary source.
  If Telegram is already in the codebase: set `"enabled": false` in config,
  then DELETE the collector file entirely and remove it from `source_names`
  in the orchestrator. Also clean the Telegram entries from the DB.
- **TGStat/analytics search requires auth:** Free channel search on tgstat.ru
  requires registration + JS rendering. Web search is more productive
  for finding channels in small markets.
- **Telegram auto-masks phone numbers in output:** When you send a message
  containing a phone number like +998979416070, Telegram replaces digits with
  `****` in the display. This does NOT affect the underlying data — hex dumps
  prove the correct digits are there. When debugging phone extraction, write
  the number to a file or format it with spaces (`998 97 941 60 70`) to
  confirm the actual value.
- **DO NOT write test scripts for detail pages — use web_extract:** When the user
  says "проверь на одном", respond by calling `web_extract` on the URL, not by
  writing a new Python script. Writing a test script introduces: API key path bugs
  (`.env` not found when running from `test_parser.py`), heredoc encoding corruption
  with кириллица, timeout errors from httpx in sandboxed environments, and confusing
  stderr/stdout interleaving. The user will get frustrated when you spend 5+ rounds
  debugging a test harness instead of showing results. web_extract already works.
  If web_extract fails, THEN write targeted code for the specific gap.
- **Always translate descriptions for user-facing reports:** Classified listings
  in Uzbekistan are often in karakalpak or uzbek. Users want Russian
  translations. Include `description_ru` in the LLM prompt as a required field.
## HTML Report Delivery via Telegram (MEDIA Limitation)

**MEDIA: directive does NOT support .html files.** The `extract_media()` regex in
Hermes Gateway (`gateway/platforms/base.py`) only allows these extensions:
`.png|jpe?g|gif|webp|mp4|mov|avi|mkv|webm|ogg|opus|mp3|wav|m4a|flac|epub|pdf|zip|rar|7z|docx?|xlsx?|pptx?|txt|csv|apk|ipa`

`.html` and `.htm` are NOT in the list. If you include `MEDIA:/path/to/report.html`
in a `send_message` call, the text is sent as-is and the file is NOT attached —
the user sees the raw MEDIA: string. The tool returns `success: True` regardless,
giving no error signal.

**Workaround:** Send the HTML file via python-telegram-bot directly:

```python
import asyncio
from telegram import Bot

# Read token from .env
token = None
with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        line = line.strip()
        if line.startswith("TELEGRAM_BOT_TOKEN=*** and not line.startswith("#"):
            token = line.split("=", 1)[1].strip()
            break

async def send():
    b = Bot(token=token)
    with open("/path/to/report.html", "rb") as f:
        msg = await b.send_document(chat_id="350262645", document=f, filename="report.html")
    print(f"OK msg_id={msg.message_id}")

asyncio.run(send())
```

Save this as a temp script, run with `python3 /tmp/send_html.py`.

**Fix (if you can modify Hermes):** Add `.html` and `.htm` to the regex in
`gateway/platforms/base.py` line ~2416.

## Interactive Report: Google Sheets for Data Review

After scraping, **always offer a Google Sheets table** for interactive review.
The user wants to mark listings as "мусор"/"проверен"/"снято" and add comments,
then have persistence across daily updates. HTML alone is read-only — Sheets is
read-write and the user can filter/sort directly.

**Implementation (add to your report script):**

1. Store the Sheet ID in `~/.hermes/nukus_sheet_id.txt` for persistence
2. On each run:
   - Read existing statuses and comments from the sheet (columns T and U)
   - Update data rows with fresh listings
   - Write back, preserving old statuses/comments
   - The cron agent sends the Sheet URL alongside the HTML report

**User workflow:**
1. User opens the Sheet link
2. Enables filters: Data → Create filter (or the funnel icon)
3. Sets status in column "Статус": types "мусор", "проверен", "снято"
4. Writes notes in column "Комментарий"
5. Next cron run preserves these values while updating listing data

**Google Sheets setup (token must have sheets scope):**
```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_PATH = os.path.expanduser("~/.hermes/google_token_svaaugust.json")
with open(TOKEN_PATH) as f:
    creds = Credentials.from_authorized_user_info(json.load(f))
service = build('sheets', 'v4', credentials=creds)

# Read old statuses
old = service.spreadsheets().values().get(
    spreadsheetId=sheet_id, range='Объявления!T1:U'
).execute()

# Write new data
body = {'values': rows}
service.spreadsheets().values().update(
    spreadsheetId=sheet_id, range=f'Объявления!A1:V{len(rows)}',
    valueInputOption='RAW', body=body
).execute()
```

**Recommended sheet columns:**
`# · Дата · Название · Цена · Комнат · Площадь · Материал · Состояние · Район · Газ · Вода · Телефон · Этаж · Отопление · Свежесть · **Статус** · **Комментарий** · URL`

Keep the "Статус" and "Комментарий" columns at positions 20 and 21 (T and U)
so they persist across updates regardless of column reordering.

## Report Format: Table > Cards

**The user strongly prefers table format over card format for listing reports.**
Table = rows with columns, sortable by clicking headers. Card = individual
blocks with styled content.

When generating HTML reports:
- ALWAYS use a `<table>` with `<th>` headers
- Add JS filters as `<select>` dropdowns above the table (NOT as side panels)
- Include a statistics bar above the filters (counts, averages, distributions)
- Color-code prices: green <200M, yellow 200-250M, red 250-300M
- Highlight new listings: yellow left border for "сегодня", orange for "вчера"
- Filters should include: price range, rooms, wall material, condition,
  location, district, phone (has/not), gas, freshness
- Show a live count of visible/filtered rows

**HTML report outline:**
```html
<div class="stats"> [average price, count, distribution bars] </div>
<div class="filters"> [dropdowns for each dimension] </div>
<div class="wrap"><table>
  <thead><tr><th>#</th><th>Цена</th><th>Название</th>...</tr></thead>
  <tbody> [data rows with data-* attributes for JS filtering] </tbody>
</table></div>
<script> [JS filter function reading data-* attrs] </script>
```

**Freshness detection:**
```python
freshness = 'old'
if 'сегодня' in date_str.lower():
    freshness = 'today'  # yellow border
elif 'вчера' in date_str.lower():
    freshness = 'yesterday'  # orange border
```

**Color the table rows:**
```css
tr.today td { border-left: 3px solid #f1c40f; }
tr.yesterday td { border-left: 3px solid #f97316; }
```

## District Detection

User wants district/area extracted from listing titles. OLX listings
often contain neighborhood names in the title but no structured district field.

Build a mapping dictionary optimized for Nukus:
```python
DISTRICTS = {
    'ипадром': 'Ипподром', 'иподром': 'Ипподром',
    'гербиш': 'Кирпичный завод', 'кирпичный': 'Кирпичный завод',
    'кошколь': 'Кошколь', 'кош-коль': 'Кошколь',
    'хожан': 'Хожан ауыл', 'хожа': 'Хожан ауыл',
    'кум ауыл': 'Кум ауыл', 'телецентр': 'Телецентр',
    'шымбай': 'Шымбай-гузары', 'бестөбе': 'Бестөбе',
    'саранча': 'Саранча', 'развилка': 'Развилка',
    'водник': 'Водник', 'хожели': 'Хожели', 'ходжейли': 'Хожели',
}
def detect_district(title, text):
    t = (title + ' ' + text).lower()
    for key, val in DISTRICTS.items():
        if key in t:
            return val
    return ''
```

Search `(title + ' ' + text).lower()` for best coverage.

## Translate Descriptions in Batch

Descriptions in karakalpak/uzbek need translation to Russian.
Use DeepSeek batch prompt (not individual requests — too slow):

```python
numbered = "\n\n---\n\n".join(f"[{j+1}] {d[:1000]}" for j, d in enumerate(descriptions))
prompt = f"""Переведи {len(descriptions)} объявлений с каракалпакского/узбекского на русский.
Про дома в Нукусе. Верни JSON-массив переводов в том же порядке: ["перевод1", "перевод2", ...]
Тексты: {numbered}"""
```

**Known issue:** DeepSeek via kilocode sometimes returns `content = None` (empty response)
on batch requests with long prompts. If this happens:
1. Reduce batch size to 10-15 descriptions
2. Increase timeout to 90-120 seconds
3. Add retry with 3-second backoff
4. If still failing, fall back to single-request translation (one per listing, ~10 sec each)
5. As last resort, use rule-based translation from the crawl4ai skill's
   `references/uzbek-classifieds-translation.md` dictionary
  **Sanity check for area:** After normalizing, check that area_per_room ≈ 50-200 m².
  If area/rooms < 30, it's still in сотки and needs another x100.
  Example: "Общая площадь: 6 м²" + rooms=2 → 6 < 50 → 6*100 = 600 m². Correct.
  But "Общая площадь: 165 м²" + rooms=4 → 165 > 50 → keep 165 m². Correct.
  The heuristic is: area < 50 AND rooms >= 2 → сотки.
- **Area from trafilatura text:** Parse "Общая площадь: N м²" with `re.search(r'([\d.]+)', area_raw)`.
  Apply the сотки rule BEFORE storing. Store BOTH the raw value and the normalized value.
- **Verify report before sending:** When delivering a scraped listing report
  as a file, ALWAYS verify its contents first. Check that dates are clean
  (no "Опубликовано" prefix), phone numbers are valid (+998XXXXXXXXX, no
  garbage), and area values are plausible. Sending unchecked data erodes
  trust fast — the user will notice immediately.
- **Backfill new fields:** When adding new extraction fields (phone, rooms,
  area, district), existing DB entries won't have them. Run a one-time
  backfill: fetch detail pages → LLM extract → update DB. After backfill,
  apply post-LLM sanity fixes (phone normalisation, area сотки→м², date cleanup).

## Price Limit vs Parser — Diagnostic First

When a user says "parser плохо парсит" or "хреново парсит", **do NOT jump to debugging selectors**. The most common cause is a too-strict `budget_max_sum` filter in config, not a parser bug.

**Diagnostic protocol (run this first):**

1. Run `scripts/diagnose_parser.py` on page 1 of the search URL:
   ```
   cd /path/to/project
   python3 SCRIPT_DIR/diagnose_parser.py <SEARCH_URL> --price-filter <CURRENT_LIMIT>
   ```
   (Find SCRIPT_DIR via `skill_view("classifieds-scraper")` → linked_files.scripts)

2. The output shows:
   - Total cards found (should be ~40-44 for OLX page 1)
   - Every listing with parsed price
   - ⚠️ marker on items above the filter limit
   - Summary: "X/Y объявлений отсекаются фильтром!"

3. **Interpretation:**
   - If all prices parse correctly and many are above the limit → **parser is fine, raise budget_max_sum in config**
   - If prices are 0, 4, 6, 16 (area numbers parsed as price) → **selectors are stale, update CSS classes**
   - If no cards found → **CARD_SELECTOR is stale, inspect current HTML**

4. Only dig into selector debugging AFTER confirming the filter is not the cause.

## Batch Scraping Resilience: Handling Individual URL Failures

When scraping a batch of listing detail pages (50–200+ URLs per run), **individual HTTP/SSL failures are inevitable** and must not crash the entire run.

### The Problem

```
httpx.ConnectTimeout: _ssl.c:999: The handshake operation timed out
```

Some OLX listing URLs intermittently fail with SSL handshake timeouts. A naive loop raises the exception on the first failure and the entire batch is lost — no report generated, no sheets updated.

### The Fix: try/except Around Each `parse_one()`

```python
results = []
errors = 0
for i, row in enumerate(rows):
    try:
        r = parse_one(row['url'], row['price_sum'])
    except Exception:
        r = None
    if r:
        results.append(r)
    else:
        errors += 1
    if (i+1) % 15 == 0:
        print(f"  {i+1}/{len(rows)}... (errors: {errors})")
    time.sleep(0.3)
print(f"  Собрано: {len(results)}/{len(rows)}, ошибок: {errors}")
```

**Key points:**
- Wrap `parse_one()` in a broad `try/except Exception` — individual HTTPS or trafilatura failures should be silently skipped
- Count errors and report them in progress output
- Log total at end: `{success}/{total}, errors: {N}`
- If **all** URLs fail (errors == total), only then abort — otherwise proceed with partial data
- The cron agent receives this count in the script output and can include it in the delivery message

### Reporting to the User

When the cron agent sees `errors: N` in the script output, include it in the summary:
```
112 объявлений собрано (из 114 в БД, 2 ошибки — SSL timeout на некоторых OLX)
```

This sets expectations and avoids "why are there 112 listings when yesterday there were 113?" questions.

### Retrying Slow URLs

For particularly slow OLX pages, add a retry with shorter timeout:
```python
def parse_one_with_retry(url, price, retries=2):
    for attempt in range(retries):
        try:
            return parse_one(url, price)
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            if attempt == retries - 1:
                return None
            time.sleep(1)
    return None
```

But typically a single try/except is sufficient — the failing URLs are consistently failing (server-side SSL issues) and won't succeed on retry.

## Verification

After any fix, run a test against a live page and check:
- All ~44 cards on page 1 are parsed (or close to it)
- Prices are realistic (not 0, 4, 6, 16)
- Titles are clean (no location/price noise)

## Full Monitor Pipeline

For multi-source monitor setups (OLX + Telegram + HTML report + cron delivery to Telegram),
see `references/multi-source-monitor-pipeline.md`. Covers:
- Telegram channel discovery via analytics platforms
- Report generation and file-based delivery (no email)
- Hermes cron job setup with MEDIA: delivery
- Running src/ modules from cron (PYTHONPATH pitfalls)

## Cron Pipeline: Script Structure & Delivery

When the scraped data powers a daily cron report, structure the script to produce
machine-readable output that the cron agent can parse for the delivery message:

### Output Convention

The script MUST print these markers to stdout for the cron agent to consume:
```
REPORT_PATH:/home/hermes/.hermes/cron/output/nukus_report_2026-05-27.html
SHEET_URL:https://docs.google.com/spreadsheets/d/1ERYiLb8s9...Jcw
SHEETS_ERROR:{exception}         # if sheets update fails (do NOT crash)
```

The cron agent reads these to attach the HTML file and include the sheets link.

### Timeout Requirement

For batch scraping (100+ URLs with HTTP + trafilatura):
- Each URL takes ~2-3s (HTTP fetch + trafilatura.extract)
- With 0.3s sleep between calls: ~2.5-3.5s per URL
- 100 URLs ≈ 250-350s
- 110-120 URLs ≈ 280-420s
- **Set cron timeout >= 300s.** The default 120s WILL timeout for 80+ URLs.

In the Hermes cron config:
```yaml
# ~/.hermes/cronjobs.yml
- name: nukus-report
  schedule: "0 14 * * *"
  command: "python3 ~/.hermes/scripts/cron_report.py"
  timeout: 360
```

### Diff Computation (Previous Run Comparison)

After the script runs, the cron agent should compute a diff against the previous
HTML report (filename with yesterday's date):

```python
# Extract URLs from today's and yesterday's HTML
today_urls = set(re.findall(r'href="(https?://[^"]+)"', today_html))
yesterday_urls = set(re.findall(r'href="(https?://[^"]+)"', yesterday_html))

new_c = len(today_urls - yesterday_urls)
rem_c = len(yesterday_urls - today_urls)

# Price changes: compare data-p attributes on matching URLs
common = today_urls & yesterday_urls
for url in common:
    tp = today_prices.get(url)
    yp = yesterday_prices.get(url)
    if tp != yp:
        price_changes += 1
```

Report format in the delivery message:
```
- +N новых / -N пропало / ~N цен изменилось
- ⏳N залёжных (freshness=old)
- Если new_c == 0 и rem_c == 0 и price_changes пусто → «без изменений с прошлого раза»
```

### Cron Delivery Message Format

The message structure for the user:
1. Short text summary with key stats
2. HTML file attached via `MEDIA:/path/to/report.html`
3. Google Sheets link if SHEET_URL was produced

```markdown
📊 **Сводка:**
- **N** объявлений (собрано N/M, K ошибок)
- **X млн** — средняя цена
- +N новых / -N пропало / ~N цен изменилось
- ⏳N залёжных
- ✅ Таблица обновлена: https://...

MEDIA:/home/hermes/.hermes/cron/output/nukus_report_2026-05-27.html
```

### Retry on Timeout

If the script times out (hermes reports `Script timed out after Ns`):
1. Re-run the script directly with `terminal(timeout=360)` — the cron limit does not apply to agent-executed terminal calls
2. Save the timeout fact: this script needs longer cron timeout and adjust cronjobs.yml
3. Proceed with normal summary + delivery using the regenerated output

### Optimization: Fresh/Old Split for Recurring Scrapes

**Problem:** When scraping the same listings daily (100+ URLs), the script takes 250-420s because every URL gets a full `httpx.get()` + trafilatura parse. After the first few days, most listings are stale with no changes.

**Solution:** Split listings by age — full parse for fresh, lightweight HEAD check for old.

```python
FRESH_DAYS = 7       # listings younger than this get full parse
REFRESH_DAYS = 7     # old listings get a full re-parse every N days
```

**Logic in `main()`:**

```python
for row in rows:
    days_online = (now - row['first_seen']).days
    days_since_last = (now - row['last_seen']).days

    if days_online < FRESH_DAYS:
        data = parse_one(url, price)           # full parse
    elif days_since_last >= REFRESH_DAYS:
        data = parse_one(url, price)           # full re-parse (weekly)
    else:
        data = head_check(url, price, db_cursor)  # lightweight

def head_check(url, price, cur):
    \"\"\"HEAD request + DB update. Returns reconstructed result or None.\"\"\"
    try:
        r = httpx.head(url, timeout=10, follow_redirects=True)
    except Exception:
        return None
    if r.status_code != 200 or redirect_to_homepage(r):
        cur.execute(\"UPDATE listings SET status='removed' WHERE url=?\", (url,))
        return None
    cur.execute(\"UPDATE listings SET last_seen=? WHERE url=?\", (now, url))
    return reconstruct_from_db(cur, url, price)
```

**Reconstruction from DB:** For HEAD-only listings, query the cached data:
```sql
SELECT title, price_sum, ... FROM listings WHERE url = ?
```

**Results:**
- **Before:** 113 URLs × ~3s each = ~340s (timeout risk)
- **After:** ~3 fresh × 3s + ~110 old × 0.5s (HEAD) = ~64s (safe within 120s)

**When to apply:**
- Script revisits the SAME set of URLs on each run
- Most listings are >7 days old with no expected daily changes
- User reports "same data every day, no new listings"

**Schedule optimization:** If new listing volume is consistently zero, reduce cron frequency from daily to every-other-day (`30 14 */2 * *`). Less noise for the same signal.
