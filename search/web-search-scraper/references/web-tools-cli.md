# web-tools CLI — быстрый поиск и экстракт

**Бинарник:** `~/.cargo/bin/web-tools` (Rust, установлен из релизов `ogodevonline/web-tools`)
**Credentials:** `XMLSTOCK_USER` + `XMLSTOCK_KEY` (env, тянутся из `~/.hermes/.env`)
**Fallback без credentials:** DuckDuckGo

## Установка / обновление

```bash
# SSH host key (если gh clone падает с Host key verification failed)
ssh-keyscan github.com >> ~/.ssh/known_hosts

# Скачать последний релиз
gh release download v0.1.0 -R ogodevonline/web-tools \
  --pattern 'web-tools-linux-amd64' \
  --output ~/.cargo/bin/web-tools
chmod +x ~/.cargo/bin/web-tools
```

## Поиск

```bash
# Яндекс — РФ (lr=213 Москва)
~/.cargo/bin/web-tools search "iPhone 17 цена" --source yandex --count 30 --lr 213

# Google — мир
~/.cargo/bin/web-tools search "iPhone 17 price" --source google --count 30 --domain com

# JSON output (для программной обработки)
~/.cargo/bin/web-tools search "запрос" --count 50 --json

# Новости — сортировка по времени
~/.cargo/bin/web-tools search "события москва" --sortby tm --domain ru

# Узбекистан
~/.cargo/bin/web-tools search "дом в нукусе" --source yandex --domain uz --lr 11117

# Мир — без региона
~/.cargo/bin/web-tools search "python asyncio" --source google --no-region
```

### Параметры search

| Флаг | Дефолт | Описание |
|------|--------|----------|
| `--source yandex` | yandex | Яндекс XML (РФ, регионы через `--lr`) |
| `--source google` | — | Google XML (мир, домен через `--domain`) |
| `--source duckduckgo` | — | Fallback без API ключа |
| `--count N` | 5 | Количество результатов (до 100) |
| `--page N` | 0 | Страница (0-based) |
| `--lr N` | — | Регион (213=Москва, 2=СПб) |
| `--domain zone` | — | Домен (ru, com, by, kz) |
| `--sortby rlv\|tm` | rlv | Релевантность / время |
| `--no-region` | — | Глобальный поиск |
| `--json` | — | JSON output |

## Экстракт страниц

```bash
# Одна страница
~/.cargo/bin/web-tools extract "https://example.com"

# Много страниц параллельно
~/.cargo/bin/web-tools extract --parallel 20 --timeout 30 url1 url2 url3

# Из поиска → в экстракт (pipe)
~/.cargo/bin/web-tools search "запрос" --count 30 --json | \
  jq -r '.[].url' | \
  tr '\n' ' ' | \
  xargs ~/.cargo/bin/web-tools extract --parallel 20 --timeout 20
```

### Параметры extract

| Флаг | Дефолт | Описание |
|------|--------|----------|
| `--parallel N` | 10 | Одновременных запросов (можно 50) |
| `--timeout N` | 15 | Таймаут на URL в секундах |
| `--retry N` | 2 | Повторных попыток |
| `--json` | — | JSON output |

## Когда что использовать

| Ситуация | Инструмент |
|----------|------------|
| Поиск + контент | `web-tools search` + `web-tools extract` |
| Только сниппеты (быстро) | `web-tools search --count 30` (без --json) |
| JS-сайты / Cloudflare / 403 | browser-tools (browser-extract) |
| 1-5 конкретных URL | `web-tools extract --parallel 5` |
| Массовый сбор (10+ URL) | `web-tools extract --parallel 20` |

## Приоритет вызова

1. `web-tools search` / `web-tools extract` — Rust бинарник, быстрее всего
2. `search.py` (Python, uv) — fallback если бинарника нет
3. `web_extract.py` — fallback для контента конкретных URL
4. Встроенный `web_search`/`web_extract` — только для быстрых фактов

## Ограничения

| Сайт | Код/результат | Причина |
|------|-------------|---------|
| **market.yandex.ru** | Капча («Вы не робот?» + captcha) | Даже через curl. Короткие ссылки `cc/` не резолвятся |
| **ozon.ru** | Пустая страница / 0 контента | JS-рендеринг |
| **wildberries.ru** | HTTP 498 | Кастомный блок, не bypass |
| **dns-shop.ru** | HTTP 401 | Unauthorized на карточки товаров |
| **mvideo.ru** | Пустая страница | JS-рендеринг |
| **citilink.ru** | HTTP 429 | Too Many Requests |
| **eldorado.ru** | HTTP 503 | Service Unavailable |
| **onlinetrade.ru** | HTTP 403 | Forbidden |
