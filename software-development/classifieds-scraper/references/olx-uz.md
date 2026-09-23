# OLX.uz — Current Structure (May 2026)

## Search Page Cards

```html
div[data-cy="l-card"]           (class css-1sw7q4x)
  └─ h4.css-hzlye5              → title text
  └─ a[href*="/d/"]             → listing URL (relative, add https://www.olx.uz)
  └─ p.css-blr5zl               → price text, e.g. "200 000 000 сумДоговорная"
  └─ div.css-acsxuw             → location / date / area combined
       ├─ p.css-1b24pxk         → "Нукус - 11 мая 2026 г."
       ├─ div.css-1kfqt7f       → area, e.g. "600 м²"
       │    └─ span.css-h59g4b  → same area text
```

### Selectors (working as of May 2026)
- Card: `div[data-cy="l-card"]` — 40-45 cards per page
- Title: `h4` inside the card
- Price: `<p>` with class containing `css-blr5zl`
- URL: `<a>` with `href` containing `/d/`
- External ID: regex `-ID([A-Za-z0-9]+)\\.html` on the URL
- Area (card): `div.css-1kfqt7f` — but see "Card area units" below
- Card title block: `div[data-cy="ad-card-title"]` or `div[data-testid="ad-card-title"]`

### Price format
- `"200 000 000 сумДоговорная"` — no space before "Договорная"
- `"300 000 000 сум"` — clean price
- `"Договорная"` — price not specified
- Parse: regex-extract digits, strip Cyrillic suffix after "сум"

### Card area units
OLX displays area as a bare number with "м²" appended, but the unit is
ambiguous. "16 м²" on a card could mean 16 соток (= 1600 м²) for a
house, or actually 16 м² for a room. The title is the only clue
(e.g. "Продаётся дом 16 соток" → card shows "16 м²").

Always extract the raw number and let the user interpret.
Do NOT treat card area as authoritative square metres.

## Detail Page

### Strategy (May 2026+)

**Primary: web_extract** (preferred — gives clean markdown text without CSS selectors)

OLX renders listing characteristics as **client-side JavaScript** — they are NOT
in `<tr>` elements anymore. Instead of fighting CSS-in-JS class names:

1. Get the raw page text via `web_extract(url)` — returns clean markdown
2. The result contains everything: parameters list, description, price, date, phone
3. Extract phone via regex (`998\d{9}`) from the raw text
4. Feed the text (with phone removed) to DeepSeek for structure + translation

Example output from web_extract:
```
Количество комнат: 2
Общая площадь: 6 м2
Жилая площадь: 37 м2
Расположение: В городе, В пригороде
Этажность дома: 1
Высота потолков: 2
Меблирован: Да
Площадь участка: 6
Состояние дома: Не достроен
Тип дома: Дом
Тип строения: Монолитный
Вода: В доме
Электричество: Есть
Отопление: Центральное
Газ: Магистральный
...

Описание:
[original karakalpak/uzbek text, may contain phone]

Цена: 160 000 000 сум
Опубликовано: 30 апреля 2026 г.
```

**LLM prompt template (for individual calls, one per listing):**

```text
Извлеки данные из объявления. Верни ТОЛЬКО JSON:

{"title": "str", "price_sum": int, "rooms": int, "area_sqm": int,
 "area_land_sqm": int, "district": "str", "floor": "str",
 "wall_material": "str", "gas": true, "water": true, "heating": "str",
 "condition": "str", "year_built": int, "furnished": true,
 "description_ru": "str"}

Правила:
- Если Общая площадь < 50, а комнат >= 2 -> это сотки, *100
- Определи район из текста/названия
- Переведи описание с каракалпакского/узбекского на русский
```

**Fallback: JSON-LD** (always present)
```json
{
  "@type": "Product",
  "name": "listing title",
  "description": "full description",
  "offers": {
    "price": 200000000,
    "priceCurrency": "UZS"
  }
}
```

**Fallback: BS4** (when web_extract is unavailable)
Use the same selectors approach described below.

### Detail HTML (raw elements)
- Description: `div[data-cy="ad_description"]`
- Post date: `span[data-cy="ad-posted-at"]` — strip "Опубликовано" prefix
- Offer title: `span[data-cy="offer_title"]`
- Breadcrumbs: `div[data-cy="categories-breadcrumbs"]` — single element,
  format: `ГлавнаяНедвижимостьДомаПродажаПродажа - КаракалпакстанПродажа - Нукус`
  Split on "Продажа - " to extract district name after Нукус.
- Seller card: `div[data-cy="seller_card"]` — username, join date, last online
- Characteristics: `<p class="css-13x8d99">` — one per parameter,
  format `Ключ: Значение`. NOT in `<tr>` elements anymore.
  Keys: Количество комнат, Общая площадь, Жилая площадь, Площадь участка,
  Этажность дома, Состояние дома, Тип дома, Меблирован, Расположение, Комиссионные

### Phone on OLX — the full story

**OLX UI masks the phone** — the visible element shows `+998****3335`.
The real number requires clicking "Показать телефон" (JS-only).

**BUT** many sellers write their phone number directly in the **description text**:
- `"Усы ном хабарласын: 88 508 8100"` (local format, 9 digits)
- `"+998 97 240 30 85"` (full format)

**Recommended extraction order (hybrid approach):**

1. **Regex first** — search the raw page text for `998\d{9}` (998 + 9 digits).
   This catches numbers in any format (with/without spaces).
   - Clean: `re.sub(r'\s+', '', raw)` then `re.search(r'998(\d{9})', cleaned)`
   - Prefix: `'+998' + group(1)`

2. **LLM fallback** — if regex found nothing, let the LLM try from the
   description text (but strip masked versions from the prompt).

**⚠️ Critical: separate phone from LLM input**
If you pass the page text WITH phone numbers to the LLM, it often returns
the **masked** version (`+998****6070`) even when the full number is present.
The model has learned from training data that OLX numbers should be masked.
Always:
- Extract phone via regex FIRST
- Remove all phone patterns from the text sent to the LLM
- Merge results afterwards

**⚠️ Telegram display quirk**
Telegram automatically masks phone numbers in agent output. When you send
a message containing `+998979416070`, Telegram replaces digits with `****`
in the display. This does NOT mean your code is wrong — hex dumps prove
the correct digits. To confirm during debugging, write to a file or space-separate
the digits (`998 97 941 60 70`).

## Rental Detection

Filter out rental listings at scrape time using these rules:

1. **Title keywords** (compile once as reusable regex):
   `ижара|аренда|сдам|сниму|rent|суточн|посуточн|хостел`
2. **Price heuristic**: price < 10,000,000 сум is almost certainly monthly
   rent, not a sale price. Skip these.
3. Apply BEFORE writing to DB so the dataset stays clean.

## Budget Filtering (nukus-houses project)

- OLX max_price: 300,000,000 UZS (config: `budget_max_sum`)
- Applied in collector: new listings > budget are skipped
- Existing listings are always updated regardless of price
- Min price: 150,000,000 UZS (below this is considered rental/land-only)

## JSON-LD: What's NOT on the search page

- ❌ No `ItemList` — search page has only `WebPage`, `Product` (category-level),
  and `BreadcrumbList`
- ✅ Detail page HAS `Product` with offers.price

## Known Issues

- CSS class names (`css-hzlye5`, `css-blr5zl`, `css-1sw7q4x`, `css-13x8d99`) are
  auto-generated by OLX's CSS-in-JS and change on every deploy.
  When they break, inspect the actual page HTML and update the selectors.
  **Better yet: use `web_extract` instead of BS4 for detail pages.**
- Always verify against a live fetch before trusting parser output.
- Card area unit is ambiguous (м² vs сотки) — flag to user, don't convert.
- Breadcrumbs changed from `a[data-cy="breadcrumb-link"]` (per-item) to
  `div[data-cy="categories-breadcrumbs"]` (single concatenated string) in May 2026.
- **Telegram auto-masks phone numbers in output.** When you send a message
  with `+998979416070`, Telegram replaces digits with `****` in the display.
  This is purely a display layer — the actual data is correct. To debug,
  write the phone to a file or use spaced format (998 97 941 60 70).
- **LLMs return masked phones.** DeepSeek consistently returns `+998****6070`
  even when the full number `998979416070` is present in the input text.
  The model has learned from training data that OLX numbers should be masked.
  Always extract phone via regex first, then remove it from the LLM input.

## Area Normalisation (Post-LLM / Post-Extract)

### The Сотки Problem

OLX displays area in **ambiguous units**. Both "Общая площадь" and "Площадь
участка" are shown in сотках but labelled "м²". Example:
- `Общая площадь: 6 м²` → real meaning: 6 соток = 600 м²
- `Площадь участка: 6` → also 6 соток = 600 м²
- `Жилая площадь: 37 м²` → this IS actual м² (cross-check with rooms count)

### Normalization Rules

LLM-rendered `area_sqm` values below 10 m² for listings with rooms ≥ 2 are
almost certainly **сотки** mislabelled as м². Apply this sanity fix:

```python
if area_sqm < 50 and (rooms or 0) >= 2:
    area_sqm = area_sqm * 100  # сотки → м²
```

**Cross-check sources** (if available from web_extract output):
- `Площадь участка: N` — if N matches Общая площадь, both are сотки
- `Жилая площадь: N м²` — this is actual м², compare with Общая площадь
- If Общая площадь < Жилая площадь → Общая is in сотки
- If title contains "соток" / "sotok" with a number, that's the real сотки value

### Best Practice

Do NOT let the LLM guess area units from context alone — it gets them wrong
~30% of the time (DeepSeek tends to take the first "м²" value literally).
Apply explicit post-processing rules after LLM extraction.

## Batch vs Individual LLM Calls

**Batch** (10 listings/call): faster, cheaper, but cross-contamination between
listings can produce wrong data for ~30% of entries. Good for backfilling
existing DB where partial data is acceptable.

**Individual** (1 listing/call): slower, more expensive ($), but each listing
gets full LLM attention. Required when data accuracy matters for user-facing reports.

**Individual + hybrid (web_extract + regex for phone + LLM for rest):** best quality.
Use for all NEW listings that appear in daily runs. Phone extracted via regex
is always correct; LLM handles translation + structure without being confused
by masked phone numbers.

**Recommendation:** Use individual+hybrid for new listings as they appear
(1-2/day). Use batch only for backfill of existing data as a one-off — but
even then, consider individual calls if the user values data quality over speed.
