---
name: crawl4ai
category: search
description: "Глубокий анализ сайтов: вытаскивает весь контент страницы в markdown через crawl4ai + Playwright. Для динамических сайтов (JS, SPA), которые httpx не берёт."
---

# Crawl4AI — Deep Site Scraper

Для сайтов с JS-рендерингом, бесконечной прокруткой, SPA.  
Заходит в браузер (Playwright), ждёт загрузки, вытаскивает всё в markdown.

**Скрипт:** `~/.hermes/skills/search/crawl4ai/scripts/crawl.py`

## Когда использовать

- **Классифайды**: OLX, Avito, CIAN — вытащить все объявления
- **Маркетплейсы**: Ozon, Wildberries — цены, описания, отзывы
- **SPA-сайты**: React/Vue/Angular — где httpx ловит пустую обёртку
- **Планирование**: booking.com, отели, билеты — реальный контент

Не использовать для: простых статей/новостей (там `web-search-scraper` быстрее).

## Установка

```bash
cd ~/.hermes/skills/search/crawl4ai/scripts
uv sync
playwright install chromium  # если не установлен ранее
```

## Использование

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

## Параметры

| Параметр | По умолч. | Описание |
|---|---|---|
| `--url` | **обяз.** | Стартовый URL |
| `--max-pages` | 3 | Сколько страниц пройти (пагинация) |
| `--timeout` | 30000 | Таймаут страницы в ms |
| `--max-chars` | 30000 | Макс символов на страницу |
| `--output` | — | Сохранить в markdown-файл |
| `--links-only` | — | Только {title, price, url} без full-content |
| `--quiet` | — | Без лишнего вывода в stderr |

## Формат результата

Без `--links-only`: JSON с `{pages[], listings[], total_pages, total_listings, total_chars}`.
- `pages[]` — полный контент каждой страницы
- `listings[]` — извлечённые объявления `{title, price, url}`

С `--links-only`: только `{listings[], total_listings, total_pages}` — для быстрого просмотра.

## Анализ классифайдов (OLX, Avito и др.)

При работе с узбекскими/казахскими классифайдами описания часто на местных языках (узбекский, каракалпакский). Порядок действий:

1. Скрапинг: `crawl.py --url "..." --max-pages N --links-only` — получить все ссылки и цены
2. Фильтр по бюджету: выбрать подходящие по цене
3. Детальный обход: для каждого отобранного объявления запустить параллельный скрапинг (через единый AsyncWebCrawler + Semaphore, макс 3 конкурентных, таймаут 25с)
4. Извлечь блок `### Описание` из markdown
5. Перевести описание на русский язык (узбекский/каракалпакский→русский)

При выводе длинных результатов (5+ объявлений с описаниями) — **использовать `send_message` в Telegram**, а не писать inline в чат. Пользователь предпочитает ссылки с заголовками, чтобы можно было кликнуть.

### Пример параллельного обхода listing-ов

```python
# Один crawler на все URL, Semaphore(3) для контроля
async with AsyncWebCrawler(verbose=False) as crawler:
    sem = asyncio.Semaphore(3)
    async def crawl_one(url):
        async with sem:
            result = await crawler.arun(url=url, config=config)
            # extract ### Описание block from result.markdown
    tasks = [crawl_one(u) for u in urls]
    results = await asyncio.gather(*tasks)
```

### Известные паттерны URL объявлений

Скрипт автоматически распознаёт:
- `/d/obyavlenie/` — OLX (рус)
- `/obyavlenie/` — OLX alt
- `/announce/` — OLX eng
- `/item/` — Avito
- `/a/` — Kufar и др.
- `/product/` — маркетплейсы
- `/ad/` — общий
