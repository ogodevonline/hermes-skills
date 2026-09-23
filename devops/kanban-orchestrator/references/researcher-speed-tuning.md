# Researcher Speed Tuning

## Problem
Researcher на deepseek-v4-flash через KiloCode выполняет простой поиск (температура в Москве) за **3+ минуты**. Это дорого и медленно.

## Root Causes

### 1. `reasoning_effort: high`
В `~/.hermes/profiles/researcher/config.yaml` стоит `reasoning_effort: high`. Для поискового агента это избыточно — он не анализирует архитектуру, а просто ищет и возвращает.

**Фикс:** поставить `reasoning_effort: medium` или `auto`.

### 2. `max_turns: 30`
Researcher может сделать 30 итераций tool calls. Если на каждой итерации вызывает `web_search` (~5-10с) или `web_extract` (~60с+) — время улетает.

**Фикс:** уменьшить до 15. Для простого поиска (1-2 запроса) хватит 5-8.

### 3. `web_extract` — убийца скорости
Один вызов `web_extract` занимает 1+ минуту. Если researcher на каждый результат поиска делает extract — время улетает.

**Фикс:** в body задачи жёстко запрещать `web_extract`. Использовать `web_search` с `--preview` (4с через Yandex XML search.py).

### 4. Не использует search.py
Researcher не загружает skill_view('web-search-scraper') автоматически, даже если прицеплен `--skill`. Использует generic `web_search` (медленнее).

**Фикс:** в body задачи явно указывать команду: `cd /home/hermes/.hermes/skills/search/web-search-scraper/scripts && uv run python search.py --query "..." --preview`

## Recommended config (~/.hermes/profiles/researcher/config.yaml)

```yaml
agent:
  max_turns: 15
  reasoning_effort: medium
  api_max_retries: 2
```

## Expected improvement
- Простой поиск (погода, факт): ~30-60с вместо 3+ минут
- Поиск со search.py (Yandex XML --preview): ~4с на запрос
- Кратное снижение токенов на reasoning