---
name: playwright-scraper-reliability
category: software-development
description: "Reliability patterns for Playwright-based scrapers — session lifecycle, error recovery, context management, admin notifications for browser/context death."
triggers:
  - user has a Playwright-based scraper that intermittently fails
  - error message contains "BrowserContext.new_page: Target page, context or browser has been closed"
  - scraper stops working after a period of time (session expiry)
  - multiple accounts/targets fail with the same Playwright error
  - user asks about Playwright session persistence / storage_state
---

# Playwright Scraper Reliability

## Common Failure Modes

| Error | Likely Cause |
|-------|-------------|
| `BrowserContext.new_page: Target page, context or browser has been closed` | Browser/context died or was closed; or session expired |
| `Target closed` | Navigation interrupted by context death |
| `Timeout 30000ms exceeded` | Site blocks headless; or network issue |
| `net::ERR_NAME_NOT_RESOLVED` | DNS issue (proxy/VPN) |

## Session Lifecycle

### Storage State (Session Persistence)

```python
# Save session after successful login
storage = await context.storage_state()
session_path.write_text(json.dumps(storage))

# Load on startup
if session_path.exists():
    storage_state = json.loads(session_path.read_text())
    context = await browser.new_context(storage_state=storage_state, ...)
```

**Session expiry signals:**
- Login page redirect during `goto()` instead of profile/target page
- `context.new_page()` starts failing after working for hours
- Instagram/other sites return 401 or redirect to `/accounts/login/`

**Fix:** Re-run the login flow to get fresh cookies.

### Context Per-Request vs Shared Context

| Approach | Pros | Cons |
|----------|------|------|
| **Shared context** (`self._context`) | Faster (no new browser setup) | Race conditions; one failure kills all concurrent tasks |
| **Per-request context** | Isolated failures; clean state | Slower; more resource usage |
| **Pool with rotation** | Balance of speed + freshness | Complexity; need careful locking |

### Recovery from Dead Context

When a shared context dies mid-operation, ALL tasks using it fail. Add recovery:

```python
MAX_RETRIES = 1

async def _safe_fetch(self, username: str) -> list[PostData]:
    for attempt in range(MAX_RETRIES + 1):
        try:
            page = await self._context.new_page()
            # ... do work ...
            return result
        except Exception as exc:
            error_text = str(exc)
            if "context or browser has been closed" in error_text:
                logger.warning("Context dead, recreating (attempt %d)", attempt + 1)
                await self.stop()
                await self.start()
                continue
            raise
    return []
```

## Scraper Pool Anti-Patterns

**DO NOT** mutate the shared context in one task while another task uses it:

```python
# BAD: rotation kills context while another task uses it
async def rotate(self):
    await old_scraper.stop()  # closes self._context!
    new_scraper = await InstagramScraper().start()
    pool.append(new_scraper)
```

**DO** ensure each scraper in the pool is independent and its lifecycle is managed with a lock:

```python
async def get_scraper(self):
    async with self._pool_lock:
        # Check, rotate, create — all under lock
        scraper = self._scraper_pool[idx]
        # ... rotation logic ...
        return scraper
```

Even with a lock on `get_scraper()`, concurrent tasks using the SAME scraper instance can collide. Either:
1. Reserve a scraper exclusively per task (not just get+release)
2. Or use per-request contexts within a scraper

## Recovery Sequence (when many accounts fail simultaneously)

When `count >= threshold` of accounts fail with the SAME "context closed" error:

1. **Check session live** — use the LIVE check (see `references/instagram-scraper-debugging.md`)
2. **If session alive** — the browser just crashed or hit a transient. Reactivate accounts and let the monitor retry:
   ```sql
   UPDATE accounts SET is_active = 1, last_error = NULL WHERE is_active = 0;
   ```
3. **If session dead** — re-login (fresh cookies), then reactivate accounts
4. **Add auto-recovery to code** — see "Recovery from Dead Context" below

## Admin Notification

When many accounts fail simultaneously with the same error, notify the admin:

```python
if inactive_count > 3 and all_same_error:
    error_type = "BrowserContext closed"
    await bot.send_message(
        admin_chat_id,
        f"🔴 Сессия протухла — {inactive_count} таргетов упали с '{error_type}'.\\n"
        f"Нужен перелогин.",
    )
```

## Instagram-Specific

See `references/instagram-scraper-debugging.md` for Instagram-specific debugging.
