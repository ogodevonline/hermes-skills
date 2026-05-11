---
name: web-search-scraper
category: search
description: "Быстрый поиск + скрапинг в markdown. XMLStock XML POST (30 результатов/стр, 3 пассажа). Preview ~4с, full ~8с."
---

# Web Search Scraper

Поиск в интернете через XMLStock (XML endpoint) + опциональный скрапинг в markdown.  
Один файл, без LangGraph, БД, scheduler.

**Скрипт:** `~/.hermes/skills/search/web-search-scraper/scripts/search.py`

**Два режима:**
| Режим | Флаг | Время | Результатов |
|---|---|---|---|
| Preview | `--preview` | **~4с** | 20-25 со сниппетами |
| Full | (по умолч.) | **~8с** | 20-25 с контентом |

## Когда использовать

- Вместо `web_search` когда нужен не список ссылок, а содержание
- Разведка мест, событий, ресторанов, музеев
- Глобальный поиск (`--no-region`)

Не использовать для: быстрых фактов (там `web_search` быстрее).

## Использование

### CLI

```bash
cd ~/.hermes/skills/search/web-search-scraper/scripts

# Preview — только сниппеты, ~4с
uv run python search.py --query "музеи москвы" --preview

# Full — со скрапом, ~8с
uv run python search.py --query "рестораны с живой музыкой"

# Новости — сортировка по времени
uv run python search.py --query "события москва" --sortby tm --preview

# Мир — без региона (библиотеки, код)
uv run python search.py --query "python asyncio" --no-region

# Узбекистан — домен + регион
uv run python search.py --query "дом в нукусе" --domain uz --lr 11117
```

### Python import

```python
from search import web_search

# Preview
results = await web_search("музеи москвы", scrape_content=False)
# Full
results = await web_search("музеи москвы", scrape_content=True)
```

## Формат результата

```json
[
  {
    "url": "https://kudago.com/...",
    "title": "Музеи Москвы",
    "snippet": "Музей Москвы 0+. Мощнейшая выставочная площадка...",
    "content": "Полный текст страницы..."
  }
]
```

- `snippet` — из `passage` XMLStock (сниппет Яндекса, до 3 пассажей)
- `content` — только в full режиме, от trafilatura (~2000 символов)
- `title` — из XMLStock, обрезан до 120 символов

## Как это работает

```
query → POST XMLStock XML (POST к yandex/xml/, 30 results, 3 passages)
         → парсинг XML (ElementTree, ns yandex.com/xmlsearch/2.0)
         → если ≥20 → preview-выход (cancel остальных)
         → если <20 → scrape конкурентно (httpx→curl_cffi, 10 concurrent)
         → trafilatura bare_extraction → JSON [{url,title,snippet,content}]
```

- **search**: POST к `xmlstock.com/yandex/xml/` с XML-телом (`<request><query>...`)
- **groups-on-page=30**: 30 результатов на страницу (вместо 10 у JSON)
- **maxpassages=3**: 3 пассажа на документ (богатые сниппеты)
- **adaptive**: `asyncio.create_task()` + `task.cancel()` — ранний выход
- **filter**: блокировка соцсетей/карт/классифайдов
- **scrape**: httpx (4s) → curl_cffi fallback, 10 concurrent

## Параметры CLI

| Флаг | По умолч. | Описание |
|------|-----------|----------|
| `--query` | — | Поисковый запрос |
| `--pages` | 1 | Страниц (1 = 30 результатов) |
| `--preview` | false | Только сниппеты, без скрапа |
| `--lr` | **213** (Москва) | Регион поиска |
| `--no-region` | false | Без региона (глобальный поиск) |
| `--sortby` | — | `rlv`/`tm` (релевантность/время) |
| `--domain` | **ru** | `ru`, `uz`, `kz`, `by`, `com` |

## Pitfalls

1. **XMLStock медленный** — ~5-7с на страницу. Это внешний сервис.
2. **`--preview` возвращает пустой content** — не пытаться парсить.
3. **`.env` в `scripts/`** — `load_dotenv()` ищет в CWD.
4. **curl_cffi** — для WAF-обхода. `uv add curl-cffi`.
