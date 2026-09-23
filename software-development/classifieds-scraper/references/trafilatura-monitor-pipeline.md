# trafilatura + Google Sheets + HTML Monitor Pipeline

Complete daily monitoring system for OLX house listings in Nukus.

## Architecture

```
cron (14:30 MSK) → cron_report.py → HTML report (file) → Telegram
                                  → Google Sheets → user reviews + marks status
                                  → next run preserves statuses
```

## Components

### 1. Data Collection (`parse_one()`)

```python
import httpx, trafilatura, json, re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

def parse_one(url, price):
    r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True, verify=False)
    if r.status_code != 200:
        return None
    
    parsed = trafilatura.extract(r.text, output_format='json', with_metadata=True)
    if not parsed:
        return None
    
    data = json.loads(parsed)
    text = data.get('text', '')
    raw = data.get('raw_text', text)
    
    # Parse all params from text
    params = {}
    for line in text.split('\n'):
        line = line.strip()
        if ':' in line and line.index(':') < 40:
            k, v = line.split(':', 1)
            params[k.strip()] = v.strip()
    
    # Phone extraction (from raw, not from text which may lose formatting)
    cleaned = raw.replace(' ', '').replace('\n', '')
    m = re.search(r'998(\d{9})', cleaned)
    phone = f"+998{m.group(1)}" if m else None  # Telegram will mask in display
    
    # Area normalization (сотки → m²)
    area_raw = params.get('Общая площадь', '0')
    am = re.search(r'([\d.]+)', area_raw)
    area_num = float(am.group(1)) if am else 0
    rooms = int(params.get('Количество комнат', 0))
    area_sqm = int(area_num * 100) if area_num < 50 and rooms >= 2 else int(area_num)
    
    # Date from text (NOT from trafilatura metadata — it returns page date, not listing date)
    date_str = ''
    dtm = re.search(r'Опубликовано\s*(.+)$', raw, re.MULTILINE)
    if dtm:
        date_str = dtm.group(1).strip()
    
    # Title cleanup
    title = re.sub(r':\s*\d[\d\s]*сум.*', '', data.get('title', '')).strip()
    
    return {
        'url': url, 'title': title, 'price_sum': price, 'phone': phone, 'date': date_str,
        'rooms': rooms, 'area_sqm': area_sqm,
        'has_gas': 'Газ' in text or 'Магистральный' in params.get('Газ',''),
        'has_water': 'Вода' in text,
        'has_phone': bool(phone and '****' not in phone),
        'wall': params.get('Тип строения', '—'),
        'cond': params.get('Состояние дома', '—'),
        'pos': params.get('Расположение', '—'),
        'floor': params.get('Этажность дома', ''),
        'heating': params.get('Отопление', ''),
        'furnished': 'Да' if params.get('Меблирован') == 'Да' else 'Нет' if 'Меблирован' in params else '',
        'year': params.get('Год постройки/сдачи', ''),
        'toilet': params.get('Санузел', ''),
        'nearby': params.get('Рядом есть', ''),
        'amenities': params.get('В доме / на участке есть', ''),
        'district': detect_district(title, text),
        'freshness': detect_freshness(date_str),
    }
```

### 2. HTML Report Generator

Generate a self-contained HTML file with:
- Statistics panel (count, avg price, avg area, price distribution, freshness counts)
- Filter dropdowns (price range, rooms, material, condition, location, district, phone, gas, freshness)
- Table with color-coded prices and freshness borders
- JS filter function that reads `data-*` attributes

Key CSS classes:
```css
tr.today td { border-left: 3px solid #f1c40f; }
tr.yesterday td { border-left: 3px solid #f97316; }
```

### 3. Google Sheets Update

See `classifieds-scraper/SKILL.md` → "Interactive Report: Google Sheets for Data Review"

### 4. Cron Job Setup

```bash
hermes cron create \
  --name "nukus-houses-daily" \
  --schedule "30 14 * * *" \
  --workdir "/home/hermes/nukus-houses" \
  --script "cron_report.py" \
  --deliver "telegram" \
  --prompt "Send the report file from REPORT_PATH to Telegram with summary."
```

### 5. Diff Tracking + Stale Detection

Added after the scrape loop in `main()`. Three additions to the baseline pipeline:

#### 5a. DB writeback (`update_db()`)

After each successful parse, update `last_seen` and record price changes:

```python
def update_db(url, price):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('SELECT id, price_sum FROM listings WHERE url = ?', (url,))
    row = cur.fetchone()
    if not row: return
    lid, old_price = row
    cur.execute('UPDATE listings SET last_seen = ? WHERE id = ?', (now, lid))
    if old_price and old_price != price:
        cur.execute('INSERT INTO price_history (listing_id, price_sum, recorded_at) VALUES (?, ?, ?)',
                    (lid, price, now))
    conn.commit(); conn.close()
```

#### 5b. Daily snapshot + diff (`get_diffs()`)

Save today's URL→price mapping as JSON, compare with yesterday's:

```python
def get_diffs(results):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today_urls = [r['url'] for r in results]
    today_prices = {r['url']: r['price_sum'] for r in results}
    
    snapshot = {'urls': today_urls, 'prices': today_prices}
    snap_path = os.path.join(OUT_DIR, f'nukus_snapshot_{today}.json')
    with open(snap_path, 'w') as f: json.dump(snapshot, f)
    
    yest_path = os.path.join(OUT_DIR, f'nukus_snapshot_{yesterday}.json')
    yest_urls = set(); yest_prices = {}
    if os.path.exists(yest_path):
        with open(yest_path) as f:
            yest_data = json.load(f)
            yest_urls = set(yest_data.get('urls', []))
            yest_prices = yest_data.get('prices', {})
    
    today_set = set(today_urls)
    new_urls = today_set - yest_urls
    removed_urls = yest_urls - today_set
    
    # Price changes
    price_changes = []
    for url in today_set & yest_urls:
        if yest_prices.get(url) != today_prices.get(url):
            price_changes.append({
                'url': url, 'old_price': yest_prices[url],
                'new_price': today_prices[url],
                'diff': today_prices[url] - yest_prices[url],
            })
    
    # Stale: 14+ days online (SQLite julianday)
    stale = []
    if today_urls:
        ph = ','.join('?' for _ in today_urls)
        cur.execute(f'''SELECT url, title, price_sum, first_seen,
            CAST(julianday('now') - julianday(first_seen) AS INTEGER) as days_online
            FROM listings WHERE status='active' AND url IN ({ph}) AND days_online >= 14
            ORDER BY days_online DESC''', today_urls)
        stale = [dict(r) for r in cur.fetchall()]
    
    return {
        'new_count': len(new_urls),
        'new_items': [r for r in results if r['url'] in new_urls],
        'removed_count': len(removed_urls),
        'removed_items': [],  # query DB for details
        'price_changes': price_changes,
        'stale': stale,
    }
```

#### 5c. HTML additions

Above the filter bar in the HTML report:

```html
<!-- Diff banner -->
<div style="margin:8px 0">
  <span style="color:#4ade80">+{new_c}</span> новых |
  <span style="color:#f87171">-{rem_c}</span> пропало |
  <span style="color:#f1c40f">~{len(price_changes)}</span> цен изменилось
  <!-- List first 5 changes inline -->
</div>

<!-- Stale warning -->
<div style="background:#1a2340;border-left:3px solid #f87171;padding:6px 10px">
  ⏳ {len(stale)} залёжных — {title1} ({N} дн.), {title2} ({N} дн.)...
</div>
```

New columns in the table:
- **🌡 Отопление** — `{r['heating'][:10]}` 
- **Дней** — `{r.get('days_online', '')}` (looked up from DB in gen_html)

Data attributes for JS filters (`data-h` for heating, `data-st` for days):

```python
html += f'''<tr ... data-h=\\"{r['heating'].lower()}\\" data-st=\\"{r.get('days_online', 0)}\\" ...>'''
```

JS filter support:
```javascript
const h=document.getElementById('fh').value, dn=document.getElementById('fdn').value;
if(h) s=s&&(t.dataset.h||'').includes(h);
if(dn){const dnv=+t.dataset.st||0; s=s&&dnv>=+dn;}
```

Style for stale rows (optional):
```css
tr.stale td { border-left: 3px solid #f87171; }
```

#### 5d. Cron stdout hints

```python
print(f"DIFF:+{new_c} -{rem_c} ~{chg_c} цен, ⏳{stl_c} залёжных")
```

### 6. Full Script Template

The complete `cron_report.py` should be saved at `/home/hermes/nukus-houses/cron_report.py`.
It must:
1. Read URLs from SQLite (`nukus.db`)
2. Fetch each via trafilatura (0.3s delay between)
3. Parse all parameters + phone + date
4. Detect district from title/text
5. Detect freshness (today/yesterday/old)
6. Generate HTML with filters + statistics
7. Update Google Sheets (preserve old statuses)
8. Print `REPORT_PATH:...` for cron agent to pick up