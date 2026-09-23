# Multi-Source Listing Monitor Pipeline

A concrete end-to-end example: the **nukus-houses** project at `/home/hermes/nukus-houses/`.

## Architecture

```
config.json ─┬─ OLX collector (httpx + BS4 cards → LLM for detail pages)
             ├─ Telegram collector (DISABLED — low quality for small cities)
             ├─ report.py (generates HTML → saves to file, OLX only)
             └─ cron job (Hermes cron → MEDIA: delivery to Telegram)
```

## Source Strategy

| Source | Technique | Status | 
|--------|-----------|--------|
| OLX.uz (cards) | httpx + BS4, 5 pages | ✅ Primary — ~7 sec |
| OLX.uz (detail) | LLM (DeepSeek) extracts phone/rooms/area/floor/gas/water from page text | ✅ Primary for new listings |
| Telegram channels | t.me/s/<channel> + LLM batch | ❌ **Disabled** — stale/low-quality for small cities |
| BirBir.uz | Candidate (SSR HTML) | 📝 Not implemented |

**Key decision:** Telegram is disabled because for non-capital cities like Nukus,
channels repost from OLX, are stale, or post over-budget properties. The LLM
cost and ~3 min runtime weren't worth the 0-2 useful listings per day.

## OLX Card Parsing (Search Page)

BS4 handles search-page cards reliably. Extract only the essentials from each card:

| Field | Selector / Method | Notes |
|-------|------------------|-------|
| Title | `h4` inside `div[data-cy="l-card"]` | |
| Price text | `p` with class containing `css-blr5zl` | Clean suffix "сумДоговорная" |
| URL | `a[href*="/d/"]` inside card | Prepend `https://www.olx.uz` |
| External ID | Regex `-ID([A-Za-z0-9]+)\\.html` on URL | |
| Area (card) | `div.css-1kfqt7f` inside card | **Ambiguous units** — may be сотки not м² |

See `references/olx-uz.md` for full selector reference.

## OLX Detail Page Parsing (LLM-based)

**Strategy:** Don't write BS4 selectors for detail page characteristics — OLX
changes their CSS-in-JS class names every deploy. Instead:

**Preferred: web_extract + regex + LLM hybrid (best quality):**
1. Use `web_extract(url)` to get clean markdown text of the detail page
2. Extract phone from raw text via regex: `re.search(r'998\d{9}', text.replace(' ', ''))`
3. Remove all phone patterns from the text
4. Send clean text to DeepSeek individually with detailed prompt for:
   - Structure extraction (rooms, area, floor, wall material, gas, water, etc.)
   - Translation of description from karakalpak/uzbek → Russian
5. Merge phone (from step 2) with structure (from step 4)

**Why hybrid over pure LLM:**
- LLMs return masked phones (`+998****6070`) even when full numbers are in the text
- OLX description text contains both masked and full phone variants
- Regex reliably finds the full number; LLM reliably translates and structures

**Older/cheaper approach (BS4 → LLM):**
1. Fetch the detail page HTML (same httpx call as cards)
2. Collect visible text from: description, characteristics list
   (`<p class="css-13x8d99">`), breadcrumbs, post date
3. Send to LLM (DeepSeek via `llm_parser.py`) — one API call per new listing
4. LLM extracts: phone, rooms, area_sqm, floor, wall_material, gas, water,
   district, is_apartment

**This is called only for NEW listings** — existing listings update price/status
from the card alone. New listings appear infrequently (1-2/day), so LLM cost
is negligible (~$0.001 per call).

**Why LLM over BS4:**
- OLX params HTML structure changes frequently
- Some listings have data only in description, not in structured params
- Phone is in the description text, not in a structured field — LLM finds it
- Address/landmark is always free-text, never structured

**Fallback for phone (if LLM unavailable):**
```python
re.search(r"(?<!\d)(\d{2})\s*(\d{3})\s*(\d{2})\s*(\d{2})(?!\d)", page_text)
# → prepend +998, skip if "****" in match
```

**Note on phone availability:** OLX UI masks phone as `+998****3335`
(JS-only reveal), but many sellers write their number in the description
text. The LLM catches these from description reliably.

## Rental Filtering

**Always** filter rentals at scrape time — never let them into the DB:

1. **Title keywords regex** (match whole word):
   `ижара|аренда|сдам|сниму|rent|суточн|посуточн|хостел`
2. **Price heuristic**: `0 < price < 10_000_000` → skip (monthly rent)
3. Apply **before** upserting — prevents DB pollution entirely

## Backfilling Existing Listings

When adding the LLM-based detail parser, existing DB entries won't have the
new fields (phone, rooms, area, etc.). Run a one-time backfill:

1. Query all active OLX listings missing phone/rooms/area
2. Fetch each detail page — **prefer web_extract(url)** over httpx+BS4 for
   cleaner text without fragile CSS selectors
3. Send to LLM in **batches of 10** (faster) or **individually** (more accurate)
4. Update DB with extracted data

**Batch vs Individual trade-off:**
- Batch (10/call): ~30% of entries get wrong data (cross-contamination)
- Individual: each listing gets full LLM attention, more accurate
- Individual+hybrid: phone via regex (always correct), LLM only for structure+translation
- For user-facing reports, individual calls are worth the extra cost

**If using web_extract for backfill:** each call takes ~5-10 seconds, so
57 listings would take ~5-10 minutes total for the web_extract step alone.
This is faster and more accurate than httpx+BS4+LLM pipeline.
**Post-LLM sanity fixes to apply:**

```python
# Remove masked phones
if "****" in phone: phone = None

# Normalise phone format
digits = re.sub(r"\D", "", phone)
if len(digits) == 9: phone = f"+998{digits}"
elif len(digits) == 12 and digits.startswith("998"): phone = f"+{digits}"
else: phone = None

# Fix area: <50m² with rooms ≥2 is сотки
if area_sqm and area_sqm < 50 and (rooms or 0) >= 2:
    area_sqm = int(area_sqm * 100)

# Clean date prefix
if "Опубликовано" in created_at_source:
    created_at_source = created_at_source.replace("Опубликовано", "").strip()

# Require translation: if description is in karakalpak/uzbek, the LLM should
# always produce a `description_ru` field. Check that it exists in the result.
```

## Report Generation

### Before (removed):
- `report.py` → `alerter.py` → Gmail API → email with HTML body

### After:
- `report.py` generates HTML report with styled table → saves to
  `~/.hermes/cron/output/nukus_report_YYYY-MM-DD.html`
- `main.py` prints `REPORT_PATH:/path/to/file` to stdout
- **Report includes OLX listings only** — Telegram data excluded entirely
- Report shows: Price, Title (linked), Rooms, Area, District, Phone,
  Features (газ/вода/стены), Date
- Cheap/below-budget section shows potential rentals/land-only listings
- No email, no Gmail API dependency

### ⚠️ CRITICAL: Verify Before Sending

**Never** send a report file without verifying its contents first. The user
will notice missing/invalid data immediately. Always:

1. Check that dates are clean (no "Опубликовано" prefix)
2. Check that phone numbers are valid (+998XXXXXXXXX, no asterisks/garbage)
3. Check that area values are reasonable (>10m² for houses with rooms)
4. Scan a few random rows for plausibility
5. **Then** send the file via `MEDIA:/path/to/file`

**Debugging note — Telegram masks phones in output:**
When you print a phone like +998979416070 in a debug message, Telegram
will display it as +998****6070. This does NOT mean the code is wrong.
To verify the actual value: write to a file, use spaced format
(`998 97 941 60 70`), or check hex (`phone.encode('utf-8').hex()`).
The same masking applies to LLM responses displayed through Telegram.

## Cron Job (Hermes)

```yaml
name: nukus-houses-daily
schedule: "30 14 * * *"       # 14:30 MSK
script: nukus-run.sh           # Copied to ~/.hermes/scripts/ (NOT symlinked)
workdir: /home/hermes/nukus-houses
deliver: origin                # Sends report file to user's Telegram
prompt: |
  Find REPORT_PATH: in stdout. If path exists and file exists →
  send the HTML file via MEDIA:/path + short summary.
  If REPORT_PATH:None → message "Report not generated".
```

### Script requirements:
- **Must be in `~/.hermes/scripts/`** — Hermes cron rejects absolute paths
- Copied file (symlinks are rejected too)
- Must export `PYTHONPATH=/home/hermes/nukus-houses` because `python src/main.py`
  doesn't add project root to sys.path

### Wrapper script (`run-and-report.sh`):
```bash
#!/bin/bash
set -euo pipefail
cd /home/hermes/nukus-houses
export PYTHONPATH="/home/hermes/nukus-houses:${PYTHONPATH:-}"
python src/main.py config.json
```

## Running Manually

**Do NOT use `python src/main.py`** — PYTHONPATH won't include project root.
Correct approaches:

```bash
# A) With PYTHONPATH (for scripts/cron)
cd /home/hermes/nukus-houses && PYTHONPATH=. python src/main.py config.json

# B) -c pattern (interactive, recommended)
cd /home/hermes/nukus-houses && python3 -c "
import sys; sys.path.insert(0, '.')
from src.main import main; main('config.json')
"
```

## Config Tips

- `config.json` is the single source of truth for sources, budget, channels
- Telegram channels in config list: **without** `@` prefix
- Budget filter: 150–300 млн сум (hardcoded in collector too)
- To speed up: disable Telegram: `"telegram": {"enabled": false}`
- Price filter: only applies when price IS available; no-price listings pass through
- Set `"telegram": {"max_posts": 50}` — higher values slow the LLM batch

## Known Channels (Nukus, May 2026)

| Channel | Type | Result |
|---------|------|--------|
| @Nukus | Channel | ✅ 7+ listings |
| @uy_satiladi | Channel | ✅ Active |
| @uy_jay_nukus | Channel | ✅ Active |
| @Bazar_nks | Channel | ⚠️ Partial |
| @Nokis_uy_jay | Channel | ❌ Empty |
| @uyjaysatiladi007 | Channel | ❌ Private |
| @Nukus_uyler | Channel | ❌ Empty |
| @imarat_nukus | **Chat** (not channel) | ❌ t.me/s/ won't work |
| @kvartira_nukus | **Chat** | ❌ t.me/s/ won't work |
| @shaharuzchannel | Channel | ❌ Nation-wide, not Nukus-specific |

## Finding New Channels

- **Web search** more productive than TGStat for small markets:
  `Нукус телеграм канал дом сатылады 2026`
- **tgram.uz** shows channel descriptions and usernames
- **TGStat** requires registration + JS — only worth it for large markets
- **Instagram** sometimes cross-posts house listings with phone numbers
- Verify at `t.me/s/<username>` before adding to config

## Git & Deployment

- Project: standalone at `/home/hermes/nukus-houses/` (not in hermes repos)
- `run.sh` uses `flock` to prevent concurrent runs
- Config backup via `ogodevonline/hermes-setup` (private repo)
- Environment: `.env` in project root (loaded by `llm_parser.py` via `load_dotenv`)
