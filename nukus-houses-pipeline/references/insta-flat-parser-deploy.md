# insta_flat_parser — Ввод в эксплуатацию

## О проекте

`ogodevonline/insta_flat_parser` — Telegram бот + CLI для парсинга Instagram объявлений о недвижимости.
Стек: Python 3.12+, aiogram 3.x, Playwright, SQLite.

Путь на сервере: `~/Projects/Personal/GitHub/insta_flat_parser/`

## Первичный деплой

### 1. Клонирование

```bash
gh repo clone ogodevonline/insta_flat_parser
mkdir -p ~/Projects/Personal/GitHub/
cd ~/Projects/Personal/GitHub/ && gh repo clone ogodevonline/insta_flat_parser
```

### 2. Установка зависимостей

```bash
cd ~/Projects/Personal/GitHub/insta_flat_parser
uv sync
uv run playwright install chromium
```

### 3. .env конфиг

```env
BOT_TOKEN=<telegram_bot_token>
ADMIN_CHAT_ID=<telegram_user_id>
ADMIN_IDS=<telegram_user_id>[,<second_admin_id>]
INSTAGRAM_USERNAME=<instagram_login>
INSTAGRAM_PASSWORD=<instagram_password>
ACCOUNTS_FILE=accounts_nukus.txt
CHECK_INTERVAL=3
POSTS_PER_CHECK=5
MAX_POST_AGE_HOURS=0.2
WEBAPP_PORT=8080
WEBAPP_HOST=0.0.0.0
WEBAPP_URL=https://<cloudflared-url>.trycloudflare.com
```

### 4. Cloudflared туннель (для Mini App)

```bash
# Установка
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
chmod +x /tmp/cloudflared

# Запуск
/tmp/cloudflared tunnel --url http://localhost:8080
# URL появится в логе: https://<hash>.trycloudflare.com
```

После запуска — обновить `WEBAPP_URL` в `.env` и перезапустить бота.

### 5. Instagram сессия (главная проблема)

⚠️ **На headless VPS login команда не работает** — Playwright требует X Server:

```bash
uv run python -m insta_flat_parser login
# ❌ BrowserType.launch: Missing X server or $DISPLAY
```

**Решение:** залогиниться на локальной машине (с GUI) и скинуть готовый session файл на сервер.

Файл сессии: `~/.insta_flat_parser/session-<instagram_username>.json`

Пользователь скидывает файл → кладёшь в `~/.insta_flat_parser/` → бот подхватывает при старте.

### 6. Чистый старт

```bash
rm -f ~/.insta_flat_parser/state.db  # сброс БД
```

### 7. Запуск бота

```bash
cd ~/Projects/Personal/GitHub/insta_flat_parser
uv run python -m insta_flat_parser bot
```

Запускать в `background=true` (демон).

## ⚠️ КРИТИЧЕСКИЙ БАГ: путь к сессии

**Файл сессии НЕ кладётся в `~/.insta_flat_parser/`!**

Код читает сессию из:
```python
_SESSION_DIR = Path.home() / ".config" / "instaloader"
# → ~/.config/instaloader/session-<instagram_username>.json
```

Если положить session файл в `~/.insta_flat_parser/` — бот не увидит его.
Лог: `InstagramScraper started (headless=True)` — **без** строки `Loaded session from...`.

**Правильный путь:** `~/.config/instaloader/session-<username>.json`

### Instagram 404 / Timeout

Если после правильной сессии всё равно "No posts" — возможные причины:
- Аккаунт не существует (переименован/удалён)
- Instagram блокирует headless запросы
- Сессия протухла

## Известные проблемы

### "chat not found" при старте

Бот пытается отправить приветственное сообщение всем `admin_ids` + `admin_chat_id`.
Если пользователь ещё не написал боту `/start` — Telegram отвечает "chat not found".

**Фикс:** сначала написать `/start` боту, потом запускать/перезапускать бота.
Или сократить `ADMIN_IDS` до одного ID, который уже писал боту.

### "No posts for @" при активных аккаунтах

Причина: **нет валидной Instagram сессии**. Scraper работает, но не авторизован —
Instagram не отдаёт посты без cookies. Лог без `Loaded session from` — явный признак.

**Фикс:** проверить путь сессии (см. критический баг выше), скинуть сессию с компа.

### "Failed to refresh DNS local resolver error" (cloudflared)

Туннель может упасть с `ERR Failed to refresh DNS local resolver error="lookup region1.v2.argotunnel.com: i/o timeout"`.
Симптом: Mini App недоступен, ошибка 1033 Cloudflare.

**Фикс:** убить процесс cloudflared → запустить новый → обновить WEBAPP_URL в `.env`.

```bash
kill $(pgrep cloudflared)
/tmp/cloudflared tunnel --url http://localhost:8080
# URL из лога: https://<new-hash>.trycloudflare.com
```

### Cloudflared URL меняется при каждом перезапуске

Новый URL → обновить `WEBAPP_URL` в `.env` → перезапустить бота.
Сохранять URL не нужно — он одноразовый.

### Дубликаты в accounts файле

`accounts_nukus.txt` содержит `nukus_rieltor` дважды (строка 6 и 12).
Monitor показывает 15 аккаунтов вместо 17 — дубликат игнорируется уникальным констрейнтом.

**Фикс:** убрать дубликат из файла (не критично, просто сбивает счётчик).

## Модификации кода (July 2026)

### 1. Отправлять ВСЕ посты, не только с контактами

Файл: `src/insta_flat_parser/monitor.py` (строка ~210)

**До:** отправлял уведомление только если `result.contacts.has_any`
**После:** отправляет всегда (сами посты шлются, даже без контактов — в уведомлении будет "❌ Contacts not found")

```python
# Было:
if result.contacts.has_any:
    try:
        await notify(self.bot, post, result)
    ...

# Стало:
try:
    await notify(self.bot, post, result)
except Exception as exc:
    logger.error("Failed to notify for {}: {}", post.shortcode, exc)
```

### 2. Кнопка Mini App в каждом уведомлении

Файл: `src/insta_flat_parser/bot.py` — функция `_lead_detail_kb`

**До:** одна кнопка "➕ Добавить в объявления"
**После:** два ряда — "➕ Добавить в объявления" + "🌐 Mini App" (WebApp)

```python
def _lead_detail_kb(post_code: str) -> InlineKeyboardMarkup:
    url = settings.webapp_url
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить в объявления", callback_data=f"add:{post_code}")],
            [InlineKeyboardButton(text="🌐 Mini App", web_app=WebAppInfo(url=url))] if url else [],
        ]
    )
```

```
src/insta_flat_parser/
├── bot.py          # aiogram хендлеры, /start, /add, /list, /app
├── cli.py          # Click entry points: bot, login, check, extract
├── config.py       # Settings из .env (python-dotenv)
├── storage.py      # StateStorage — аккаунты, known_posts, form_states
├── leads.py        # LeadStorage — CRM лидов (SQLite)
├── scraper.py      # InstagramScraper — Playwright + API interception
├── extractor.py    # DataExtractor — regex + OCR + Whisper
├── monitor.py      # Monitor — асинхронный polling каждые N мин
├── reminder.py     # ReminderService — проверка remind_at
├── web_app.py      # aiohttp REST API для Mini App
└── web/static/
    └── index.html  # Mini App SPA (vanilla JS)
```
