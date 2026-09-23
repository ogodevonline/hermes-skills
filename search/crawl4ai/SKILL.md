---
name: crawl4ai
category: search
description: "Глубокий анализ сайтов. Сначала httpx + BeautifulSoup (быстрее). Crawl4ai (Playwright) — запасной вариант для SPA/JS, когда httpx не берёт."
---

# Crawl4AI — Deep Site Scraper

## 🔑 Приоритет: httpx + BeautifulSoup FIRST

**Прежде чем лезть в crawl4ai — попробуй httpx + BeautifulSoup.** Многие сайты (OLX, Avito, Telegram t.me/s/) отлично парсятся обычными HTTP запросами:

- **Быстрее** — 1-2 сек вместо 5-15 сек на Playwright
- **Нет блокировок** — CloudFront/Cloudflare часто блокируют именно headless браузеры
- **Меньше зависимостей** — не нужен Playwright/Chromium
- **SSR данные** — многие классифайды (OLX) вставляют данные в JSON-LD (schema.org)

```python
import httpx
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
soup = BeautifulSoup(resp.text, "lxml")
```

**Откат на crawl4ai только если:**
- Сайт SPA (React/Vue/Angular) и JSON в HTML нет
- Браузерное поведение (прокрутка, hover, клики)
- httpx возвращает пустую обёртку или 403/CloudFront

## Когда что использовать

| Тип сайта | Пробуй сначала | Если не работает |
|-----------|----------------|----------------|
| **Классифайды** (OLX, Avito) | `httpx + BS4` — ищи JSON-LD schema.org ItemList | crawl4ai |
| **Telegram каналы** (t.me/s/) | `httpx + BS4` — парсинг tgme_widget_message | crawl4ai с stealth |
| **Маркетплейсы** | `httpx + BS4` | crawl4ai |
| **SPA-сайты** (React/Vue) | crawl4ai | web-extract |
| **Travel aggregators** (Aviasales, Skyscanner, Яндекс.Путешествия) | crawl4ai — SPA, динамические цены | web-extract |
| **Статьи/новости** | web-search-scraper | httpx |

## Установка

```bash
cd ~/.hermes/skills/search/crawl4ai/scripts
uv sync
playwright install chromium  # если не установлен ранее
```

## Использование crawl4ai (для SPA/JS)

```bash
cd ~/.hermes/skills/search/crawl4ai/scripts

# Просто вытащить весь контент страницы
uv run python crawl.py --url "https://www.olx.uz/nedvizhimost/doma/prodazha/nukus/"

# С пагинацией — 3 страницы объявлений
uv run python crawl.py --url "https://www.olx.uz/nedvizhimost/doma/prodazha/nukus/" --max-pages 3

# 5 страниц, сохранить в файл
uv run python crawl.py --url "https://..." --max-pages 5 --timeout 60000 --output results.md

# Только первую страницу, без лишнего вывода
uv run python crawl.py --url "https://..." --quiet
```

## Параметры crawl.py

| Параметр | По умолч. | Описание |
|---|---|---|
| `--url` | **обяз.** | Стартовый URL |
| `--max-pages` | 3 | Сколько страниц пройти (пагинация) |
| `--timeout` | 30000 | Таймаут страницы в ms |
| `--max-chars` | 30000 | Макс символов на страницу |
| `--output` | — | Сохранить в markdown-файл |
| `--links-only` | — | Только {title, price, url} без full-content |
| `--quiet` | — | Без лишнего вывода в stderr |

## 🚨 CloudFront / Cloudflare bypass (crawl4ai)

Некоторые классифайды защищены CloudFront и блокируют headless Playwright.

**Симптомы:**
- `"ERROR: The request could not be satisfied"` (403)
- Title пустой или `ERROR`
- `total_listings: 0`

**Stealth-конфигурация:**
```python
config = CrawlerRunConfig(
    word_count_threshold=3,
    cache_mode=CacheMode.BYPASS,
    page_timeout=60000,
    wait_until="networkidle2",
    delay_before_return_html=1.0,
    magic=True,
    simulate_user=True,
    override_navigator=True,
    scan_full_page=True,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    remove_consent_popups=True,
)

async with AsyncWebCrawler(
    verbose=verbose,
    user_agent="...",
    headers={"Accept": "text/html,...", "Accept-Language": "ru-RU,...",
             "DNT": "1", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate"},
) as crawler:
    ...
```

**Если не помогает:** сделать паузу 30+ сек (CloudFront запомнил IP), попробовать httpx или **trafilatura** (`pip install trafilatura` — чистит HTML без браузера).

## 📐 Референс-файлы

- **`references/olx-jsonld-parsing.md`** — парсинг OLX через JSON-LD (SSR), httpx+BS4
- **`references/telegram-tme-parsing.md`** — парсинг Telegram каналов через t.me/s/
- **`references/llm-listing-enrichment.md`** — батчевое LLM-обогащение: извлечение структуры + фильтр спама через DeepSeek
- **`references/uzbek-classifieds-translation.md`** — перевод узбекских/каракалпакских объявлений
- **`scripts/crawl.py`** — скрипт crawl4ai (для SPA-сайтов)

## Интеграция с SQLite-мониторингом (upsert-паттерн)

Стандартный пайплайн:

1. **Скрапинг списка** → получаем [{title, price, url}]
2. **Фильтр по бюджету в КОДЕ** — не через URL (параметры OLX ненадёжны)
3. **LLM батч** — все новые тексты → структурированные данные + фильтр релевантности
4. **Upsert в БД** — url_hash (SHA-256 URL) ⇒ INSERT OR UPDATE
5. **Поиск исчезнувших** — active → sold

**Workflow для OLX (httpx):**
```python
# 1 страница: ~40 объявлений, 2-3 сек
# Детальный обход новых: ~1-2 сек на объявление
```

**Workflow для Telegram (httpx + LLM):**
```python
# t.me/s/<channel> → 5-50 постов → LLM батч → is_house? → структура → DB
# 1 канал: ~20 сек (запрос + LLM)
```

## Известные паттерны URL объявлений

- `/d/obyavlenie/` — OLX (рус)
- `/obyavlenie/` — OLX alt
- `/announce/` — OLX eng
- `/item/` — Avito
- `/a/` — Kufar и др.
