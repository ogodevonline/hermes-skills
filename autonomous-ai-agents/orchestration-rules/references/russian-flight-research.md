# Russian Flight / Transport Research

> Domain-specific knowledge for researching Russian domestic/international flights via Kanban → researcher.

## Key principle: JS-heavy sites don't parse

Russian travel aggregators (Aviasales, Skyscanner, Яндекс.Путешествия) are SPAs — prices render in the browser. **httpx/BeautifulSoup, web_extract, and generic web_search all fail on these sites.** The researcher gets empty or partial results and blocks/wastes iterations.

## Working sources (exact prices via web_extract)

These sites are server-rendered — **web_extract returns actual prices, not ranges**.

| Source | URL pattern | What it gives | Price example |
|--------|-------------|---------------|---------------|
| **Yandex Raspisaniya** | `rasp.yandex.ru/plane/moscow--nukus` | Точные цены по рейсам и дням недели | Победа DP-731 от **6 171 ₽**, HY-9626 от **10 500 ₽** |
| **UniTicket** | `uniticket.ru/aviabilety/moscow/nukus/` | Цены по конкретным датам в таблице | от **6 067 ₽** на июнь |
| **biletdv.ru** | `biletdv.ru/raspisanie/avia/Moscow-Nukus` | Расписание рейсов по неделям | — |
| **flaut.travel** | `flaut.travel/ru/tickets/moscow/nukus` | Маршруты и цены | — |
| **lansh.ru** | `lansh.ru/city/nukus/` | Календарь цен по месяцам | — |

## ⚠️ CRITICAL: researcher returns PRICE RANGES, not exact prices

Это ключевой баг researcher с web_search: он находит общие сведения («от 7 000 до 12 000 ₽») вместо точных цен на конкретные даты. **Пользователь бесится когда видит вилку вместо конкретной цифры.**

**Причина:** web_search возвращает snippets из поисковой выдачи — «цены от X», «Y–Z ₽». Это мета-информация, не точные цены.

**Протокол для оркестратора после kanban_complete:**
1. Прочитай summary через `hermes kanban show <task_id>`
2. Если цены в диапазонах («от X», «X–Y») — результат НЕПРИЕМЛЕМ
3. Сделай сам через web_extract на Yandex Raspisaniya или UniTicket — они серверные, отдают точные цифры
4. Только после получения точных цен — показывай пользователю

**Пример конверсии диапазона → точная цена:**
- Researcher: «Победа 7–12к, HY 10–15к» → бесполезно
- web_extract rasp.yandex.ru: «Победа 6 171 ₽, HY 10 500 ₽» → ✅

## Sources that should NOT be attempted via web_search/extract

| Source | Why not | What to do instead |
|--------|---------|-------------------|
| **Aviasales** | SPA, React-rendered | ❌ Не пытаться |
| **Skyscanner** | SPA | ❌ Не пытаться |
| **Яндекс.Путешествия** (travel.yandex.ru) | SPA, JS-heavy | ❌ Не пытаться. Использовать rasp.yandex.ru вместо него |
| **T-Bank Travel** | SPA | ❌ Не пытаться |

## Searchable via web_search (text results)

| Source | Search query pattern | Notes |
|--------|---------------------|-------|
| **Победа (pobeda.aero)** | `"Победа" "Москва" "Нукус" "10 июля 2026" цена` | Primary for Uzbekistan routes. Budget airline. |
| **Utair** | `"Utair" "Москва" "Нукус" билеты` | Also flies Uzbekistan routes |
| **Uzbekistan Airways** | `"Uzbekistan Airways" "Москва" "Нукус"` | National carrier |
| **Аэрофлот** | `"Аэрофлот" "Москва" "Нукус" расписание` | May not fly direct to Nukus |
| **S7** | `"S7" "Москва" "Нукус"` | May have connections via Novosibirsk |
| **Yandex Travel** | `site:travel.yandex.ru "Москва" "Нукус"` | Sometimes indexed in web_search |
| **Google Flights** | `"Moscow" "Nukus" flights July 2026 price` | Search snippets may show prices |

## Body template for a flight research task

```markdown
Найти авиабилеты [Москва→Город] на даты [список дат], 1 пассажир, без багажа.

АЛГОРИТМ ПОИСКА:
1. Через web_search искать рейсы авиакомпании Победа (Pobeda) — приоритет
2. Также проверить [другие а/к: Utair, Uzbekistan Airways, S7, Аэрофлот]
3. Искать через web_search запросы вида "Москва [Город] авиабилеты [дата] цена"
4. Для каждой даты — свой запрос (не смешивать все даты в один)
5. После сбора данных — попробовать web_extract на rasp.yandex.ru/plane/moscow--city для точных цен

ВАЖНО: 
- ❌ НЕ пытаться парсить JS-сайты (Aviasales, Skyscanner, Яндекс.Путешествия)
- ❌ НЕ использовать web_extract для агрегаторов — они SPA, httpx бесполезен
- ❌ НЕ использовать httpx/BeautifulSoup/ScreenScraper
- ✅ Только web_search (XMLStock) + web_extract на серверных источниках (Yandex Raspisaniya, UniTicket)

⚠️ НЕ возвращай цены в диапазонах ("от 7 000 до 12 000 ₽"). Точная цена обязательна для каждой даты.

Формат вывода — для каждой даты:
- Авиакомпания, номер рейса
- Вылет→прилёт, длительность
- ТОЧНАЯ цена RUB (не диапазон)
```

## Research flow

1. **web_search** (XMLStock) — первый шаг, найти доступные рейсы
2. **web_extract** на rasp.yandex.ru или uniticket.ru — для точных цен (серверный рендеринг, работает)
3. **crawl4ai** — только если источник — статичная страница (не SPA). Для Победы/Utair — можно попробовать
4. ❌ НЕ web_extract на SPA-агрегаторах (Aviasales, Skyscanner)

## Known pitfalls

- **Researcher defaults to httpx+BS4** — even on SPA sites. Always explicitly forbid in body.
- **One date only** — researcher tends to check only the first date and stop. Explicitly say "перебери ВСЕ даты, не останавливайся на первой".
- **Single source** — researcher may check one airline and declare done. Say "проверь как минимум 3 источника".
- **Цены в $/сум** — researcher may return prices in non-RUB currencies. Explicitly require RUB.
- **Недельные тарифы** — Победа меняет цены по дням недели + сезон. Результат действителен на момент поиска.
- **⚠️ Price RANGES instead of exact prices** — researcher with web_search returns "от 7к до 12к" instead of "6 171 ₽". See critical note above. Always validate and re-do via web_extract on working sources if ranges appear.