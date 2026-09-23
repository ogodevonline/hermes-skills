# Playwright-based Instagram Scraping — Deployment Notes

Собрано после настройки `insta_flat_parser` (Telegram Bot + Playwright для Instagram).

## Session Management

- **Путь к сессии** Playwright scraper читает из `~/.config/instaloader/session-{username}.json`
  (определён в `_SESSION_DIR = Path.home() / ".config" / "instaloader"`)
- **НЕ путать** с `~/.insta_flat_parser/` — там БД state.db, а не сессия.
- Файл сессии — это Playwright `storage_state` (cookies + localStorage).
- Если файла нет — scraper работает без авторизации, Instagram не отдаёт посты.
- Если сессия протухла — нужно перелогиниться через `uv run python -m insta_flat_parser login`.

## Headless Mode on VPS

- На VPS без XServer Playwright требует `headless=True` (по умолчанию так и есть).
- `chromium.launch(headless=True)` работает; `headless=False` упадёт с ошибкой:
  `Missing X server or $DISPLAY`.
- **Установка браузера:** `uv run playwright install chromium` — скачивает в `~/.cache/ms-playwright/`.
- Chrome for Testing ~177 MiB + Chrome Headless Shell ~114 MiB.

## Логин на VPS

- `login_interactive()` открывает headless страницу логина, заполняет credentials.
- Если 2FA не нужен — после заполнения пароля нажимает Enter и ждёт `click.prompt`.
- Если 2FA нужен — браузер показывает QR/код, нужно передать управление.
- На headless VPS login проблематичен из-за `click.prompt()` — проще скинуть session JSON с локальной машины, где был выполнен логин в GUI.

## Первая проверка (first_check)

- При первом запуске scraper отправляет **только 3 самых новых поста** (код `if i >= 3: mark_post_seen`).
- **Уведомление отправляется только если в посте найдены контакты** (телефон, email, Telegram).
- Если контакты в тексте на фото — нужен OCR (`OCR_ENABLED=true`).

## Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `Page.goto: Timeout 15000ms exceeded` | Instagram не отвечает / блокирует headless | Проверить сессию, перезапустить, увеличить таймаут |
| `ERR_ABORTED` | Фрейм отвалился при ротации scraper | Игнорировать — штатное поведение при SIGTERM |
| `chat not found` | Бот пытается написать админу до первого `/start` | Админ должен написать `/start` боту первым |
| `Missing X server` | `headless=False` на VPS | Переключить `headless=True` |
| `No posts for @...` | Сессия не загружена или аккаунт пуст | Проверить `Loaded session from` в логах |
