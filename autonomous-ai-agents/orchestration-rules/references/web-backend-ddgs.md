# Web Backend: DuckDuckGo (ddgs)

## История
05.06.2026 — переключён с Firecrawl (кредиты кончились) на DuckDuckGo (ddgs).

## Текущее состояние
- `web.backend: ddgs` — бесплатно, без ключей, быстро
- `web.extract_backend: ''` — пусто, падает на `web.backend` (ddgs search-only)

## Что работает
- `web_search` — ✅ DuckDuckGo, ~1-2 сек
- `web_extract.py` (скрипт) — ❌ не встроенный, через терминал: `python3 ~/.hermes/scripts/web_extract.py <url>`
- `web-search-scraper` — ✅ Yandex XML, ~5-8 сек (глубокий поиск)

## Что НЕ работает
- `web_extract` (встроенный) — ❌ ddgs search-only, нужен другой бэкенд

## Free backends available
- ddgs — установлен (бесплатно)
- searxng — нужен SEARXNG_URL (самостоятельный хостинг)
- brave-free — нужен BRAVE_SEARCH_API_KEY (бесплатный тир)
- exa/tavily/firecrawl/parallel — платные

## Тест
```bash
# Проверка что бэкенд активен
python3 -c "from ddgs import DDGS; g = DDGS(); r = list(g.text('test', max_results=2)); print(len(r), 'results')"
```
