# Instagram Scraper Debugging (Playwright)

## Session Storage

Instagram scraper sessions are stored at:
```
~/.config/instaloader/session-{instagram_username}.json
```

### Check existing sessions

```bash
ls -la ~/.config/instaloader/
```

### Relogin

```bash
cd /path/to/project
uv run python -m <module> login
```

This runs Playwright in non-headless mode, opens Instagram login page, fills credentials from `.env`, and saves the session.

### Session validation — cookie check (quick, may be stale)

The session file is valid if it contains a `ds_user_id` cookie:

```python
storage = json.loads(path.read_text())
cookies = {c["name"]: c["value"] for c in storage.get("cookies", [])}
is_valid = "ds_user_id" in cookies
```

**⚠️ Warning:** A `ds_user_id` cookie can **exist but be expired**. Instagram still has the cookie but
redirects to the login page on any real page load. Cookie presence is NOT the same as session validity.

### Session validation — LIVE check (authoritative)

To **really** verify a session works, open Instagram and check you're not redirected to login:

```python
import asyncio
from playwright.async_api import async_playwright

async def check_session(session_path: str) -> bool:
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = await browser.new_context(storage_state=session_path)

    # Check cookie existence first
    cookies = await ctx.cookies()
    has_ds = any(c.get("name") == "ds_user_id" for c in cookies)
    if not has_ds:
        await ctx.close(); await browser.close(); await p.stop()
        return False  # Definitely dead

    # LIVE check — try loading Instagram
    page = await ctx.new_page()
    await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)
    content = await page.content()
    await page.close(); await ctx.close(); await browser.close(); await p.stop()

    # If we see login form, session is expired
    return "login" not in content.lower()[:5000]

# Usage:
# asyncio.run(check_session("/path/to/session-user.json"))
```

## Diagnosing "Context has been closed" Errors

### Step 1: Check state DB

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/path/to/state.db')
for r in conn.execute('SELECT username, last_error FROM accounts WHERE is_active=0'):
    print(f'🔴 @{r[0]:25s} {r[1][:120]}')
"
```

### Step 2: Check if all failed accounts have the SAME error

Same error = shared cause (session died, browser crashed).
Different errors = per-account issues.

### Step 3: Restart

If session expired:
1. Relogin (creates fresh `session-{username}.json`)
2. Reactivate accounts in state DB
3. Bot should restart automatically (if running as daemon/cron)

## Code Patterns Specific to Instagram Scraping

### Context lifecycle

```python
class InstagramScraper:
    def __init__(self):
        self._context = None  # Single shared context = fragility point

    async def start(self):
        self._context = await self._browser.new_context(
            storage_state=storage_state,  # Load saved cookies
            ...
        )

    async def fetch_profile_posts(self, username):
        page = await self._context.new_page()  # ← Crash here if context dead
```

### Race condition in pool

If the scraper pool shares one `InstagramScraper` instance, and one task triggers
context rotation (e.g. after N uses), the rotation closes the context while other
concurrent tasks try to use it.

**Signs:** Accounts fail in batches equal to `max_concurrent` — e.g. 3 at a time
if max_concurrent=3.

### Detection code

```python
# In monitor loop, after gather:
if results_have_errors:
    error_counts = Counter(str(e)[:100] for e in results if isinstance(e, Exception))
    top_error, count = error_counts.most_common(1)[0]
    if count >= 3 and "context or browser has been closed" in top_error:
        # Session likely dead — notify admin
```

## Recovery Steps

1. **Relogin**: `uv run python -m insta_flat_parser login`
2. **Reactivate accounts**: either via bot `/status` + manual, or SQL:
   ```sql
   UPDATE accounts SET is_active = 1, last_error = NULL WHERE is_active = 0;
   ```
3. **Verify**: Check that green accounts > 0 after next monitor cycle
