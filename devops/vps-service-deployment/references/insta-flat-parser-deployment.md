# Session 2: insta_flat_parser — monitor fixes, OCR/Whisper, WebApp button (2026-07-19/20)

## Parts from Session 1 still relevant
- GitHub auth, clone, uv sync, .env setup — all done in Session 1
- Final state of Session 1: bot running, cloudflared tunnel, 17 accounts monitoring

## Session 2 changes

### 1. Monitor sends ALL posts (not just with contacts)

**Problem:** Bot found posts (log: `Checked @user (5 posts)`) but sent no notifications.
**Root cause:** `monitor.py` line 210: `if result.contacts.has_any:` — only sends notifications when contacts (phone/email) are found in the post.

**Fix:** Removed the condition — unconditionally calls `notify()`:
```python
# Before:
if result.contacts.has_any:
    await notify(self.bot, post, result)

# After:
try:
    await notify(self.bot, post, result)
except Exception as exc:
    logger.error("Failed to notify: {}", exc)
```

### 2. Increased Playwright timeouts

Instagram was timing out on headless Chrome from VPS:

| Context | Before | After |
|---------|--------|-------|
| `fetch_profile_posts` | 15s | 30s |
| `fetch_post_comments` | 30s | 60s |

Changed in `scraper.py` lines 389 and 425.

### 3. Debug logging added to notify()

Added logger calls in `bot.py` `notify()` to confirm delivery:
```python
logger.info("Notifying about post {}", post.shortcode)
logger.debug("Sent notification for {} to chat_id={}", post.shortcode, chat_id)
```

### 4. WebApp button in every notification

Added second row to inline keyboard in `_lead_detail_kb()`:
```python
InlineKeyboardButton(text="🌐 Mini App", web_app=WebAppInfo(url=settings.webapp_url))
```

### 5. OCR and Whisper enabled

**System deps installed:** `tesseract-ocr`, `tesseract-ocr-rus`, `ffmpeg`
**Python deps:** `uv sync --extra all` (adds pytesseract, faster-whisper, pillow, ctranslate2)
**.env changes:**
```env
OCR_ENABLED=true
OCR_LANG=rus+eng
WHISPER_ENABLED=true
WHISPER_MODEL_SIZE=tiny  # → later changed to small
```

**Whisper test results (small model):**
- First video: "Президентский кущенок Боя, динсоулахла Сахлав Министерлинг, Алдинда Жайласхан, 2 этажа Лодовнын, 2 этажа Дага, Майдана, 60 квадрат метра..." — accented but intelligible
- Second video: failed due to SSL handshake timeout (network issue, not model)

### 6. Cloudflared tunnel instability

Tunnel URL changed 3 times during session:
1. `begins-extension-hire-bean.trycloudflare.com` — original, died
2. `plastic-counseling-casting-diamond.trycloudflare.com` — ran ~6h
3. `iso-measuring-russia-judge.trycloudflare.com` — ran ~? 
4. `ignored-temperatures-interpretation-participating.trycloudflare.com` — current

Each time: kill old cloudflared → start new → grep new URL → update .env → restart bot.

### 7. Single admin kept

Reduced from `ADMIN_IDS=350262645,5400073449` to `ADMIN_IDS=350262645` only to avoid "chat not found" noise on startup.

## Current state (end of Session 2)
- Bot running with all fixes (unconditional notify, increased timeouts, WebApp button)
- OCR enabled, Whisper enabled (small model)
- Cloudflared tunnel active
- Single admin (350262645)
- MAX_POST_AGE_HOURS accidentally removed from .env (defaults to 24h now)
