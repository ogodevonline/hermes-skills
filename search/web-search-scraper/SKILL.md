---
name: web-search-scraper
category: search
description: "ТОЛЬКО через web-tools CLI. Встроенные web_search/web_extract ЗАПРЕЩЕНЫ. Бинарник: ~/.cargo/bin/web-tools. Python search.py — fallback."
---

# Web Search Scraper

## ⚠️ MANDATORY RULES — прочитай ДО работы

Этот навык — замена `web_search`/`web_extract`. Действует для ВСЕХ агентов (не только Kanban worker, но и в обычной сессии Hermes).

**Firecrawl НЕ РАБОТАЕТ** — кредиты исчерпаны (Payment Required). В конфиге Hermes: `web.backend=ddgs` (бесплатный DuckDuckGo, только поиск). `web_extract` не настроен. Не пытайся переключить на Firecrawl.

**В обычной сессии Hermes (не Kanban):** используй `terminal("~/.cargo/bin/web-tools search ...")` и `terminal("~/.cargo/bin/web-tools extract ...")` вместо встроенных `web_search`/`web_extract`. Встроенный `web_search` (ddgs) — **только если web-tools бинарник отсутствует**. Дополнительная защита: `skill_view('web-search-scraper')` теперь встроен во ВСЕ 19 SOUL.md (корневой + 18 профилей). Каждый агент автоматически загружает этот навык при старте. Если агент всё равно использует `web_search` — проблема в его SOUL.md, не в навыке.

**В Kanban-задаче (через `--skill web-search-scraper`):**

1. **Для поиска — `web-tools` CLI (приоритет).** Бинарник: `~/.cargo/bin/web-tools`. Быстрее Python-скриптов, тот же XMLStock API, не требует uv/venv. Команда: `~/.cargo/bin/web-tools search "запрос" --count 30 --source yandex`. Если бинарник не найден — попробуй установить: проверить `~/.cargo/bin/` или релизы `ogodevonline/web-tools`.

2. **Для извлечения контента — `web-tools extract`.** Команда: `~/.cargo/bin/web-tools extract <url1> [url2...] --parallel 10 --timeout 15`. Параллельный экстракт, быстрее Python.

3. **Если `web-tools` недоступен — fallback на `search.py`.** Команда: `cd /home/hermes/.hermes/skills/search/web-search-scraper/scripts && uv run python search.py --query "..." --preview`. Generic встроенный `web_search`/`web_extract` не используй — они слабее, медленнее и не для русскоязычного поиска.

4. **Для извлечения контента из найденных URL (fallback) — `web_extract.py`.** После search.py, когда есть конкретные URL, используй `python3 ~/.hermes/scripts/web_extract.py <url1> <url2> [--chars N]` — параллельно, с ретраями. Не лезь в crawl4ai для 2-3 страниц.

5. **Не игнорируй body задачи.** Если в body сказано «используй search.py» — так и делай. Не заменяй на то, что тебе удобнее.

6. **Не уходи в blocked без попытки.** Сначала попробуй указанный подход. Если не сработало — попробуй альтернативу. Если всё равно не вышло — закомментируй частичный результат и только потом block с объяснением почему. Ничего > что-то.

7. **Загрузи этот навык.** Вызови `skill_view('web-search-scraper')` — это покажет точные пути к скриптам и параметры. Без этого ты не увидишь команды.

8. **Для параллельных запросов — запускай web-tools search несколько раз подряд.** Не пытайся сделать один сложный запрос на всё сразу.

## 🎯 Trigger — загружать этот скилл когда

⚠️ Загружать ВСЕГДА перед любым поиском в интернете. Исключений нет.

Пользователь просит:
- **Любой поиск в интернете** — быстрый факт, обзор сервисов, исследование, новости, цены
- **Русскоязычные/региональные запросы** (RU, UZ, KZ, BY — XMLStock через Yandex лучше покрывает СНГ)
- **Разведку мест/событий/ресторанов/музеев** с контентом
- **Анализ рынка/ценообразование** с реальными страницами
- **Содержание страниц**, а не просто список ссылок

**⚠️ Health / medical / safety / financial / legal — ВСЕГДА проверяй из интернета. НЕ отвечай из знаний модели.**
Пользователь категорически требует верификации через web-tools для вопросов с последствиями. Ответ из training data = 😡. Даже если «знаешь» ответ — проверь. До ответа: `web-tools search` + 2-3 источника, потом цитируй источники. Цена ошибки высока.

**⚠️ Ассиметричные предположения — проверяй, не додумывай.**
Когда ситуация пользователя может отличаться от типовой (напр. «жевать здоровой стороной» при тотальной операции всей челюсти) — спроси или проверь. Не навязывай шаблонное решение.

**Никогда не используй встроенный `web_search`/`web_extract`.** Даже для быстрых фактов. Только `terminal("~/.cargo/bin/web-tools search ...")`. Если не загрузил навык — не узнаешь точных команд и сорвёшься на дефолт.

## Когда использовать

- Всегда, когда нужен любой доступ в интернет
- Вместо `web_search`/`web_extract` в любом сценарии

## Использование

### CLI — web-tools (приоритет)

```bash
# Яндекс — РФ (lr=213 Москва)
~/.cargo/bin/web-tools search "музеи москвы" --source yandex --count 30 --lr 213

# Google — мир
~/.cargo/bin/web-tools search "python asyncio" --source google --count 30 --no-region

# Новости — сортировка по времени
~/.cargo/bin/web-tools search "события москва" --source yandex --sortby tm --count 30

# Узбекистан — домен + регион
~/.cargo/bin/web-tools search "дом в нукусе" --source yandex --domain uz --lr 11117

# DuckDuckGo fallback (без XMLStock credentials)
~/.cargo/bin/web-tools search "музеи москвы" --source duckduckgo --count 10

# Экстракт страниц
~/.cargo/bin/web-tools extract "https://example.com" --parallel 5 --timeout 15

# JSON output (для программной обработки)
~/.cargo/bin/web-tools search "запрос" --count 30 --json
```

### Fallback — search.py (Python, если web-tools недоступен)

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

### Python import (только для search.py)

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
5. **Sub-agent provider inheritance (HTTP 500).** Если запускаешь search.py через `delegate_task`, sub-agent наследует provider от родительского агента, НЕ из профиля. Если родитель использует fallback/custom provider (не kilocode напрямую), sub-agent получит HTTP 500 при попытке инициализации. Лечение: в goal явно указать `use the web-search-scraper scripts directly via terminal()` вместо delegate_task — или переопределить provider в запросе.
6. **Fallback после отказа sub-agents.** Если `delegate_task` для параллельного поиска упал (timeout/HTTP 500) — НЕ переключайся на `web_extract` для каждого URL. Используй `~/.cargo/bin/web-tools search --source duckduckgo` напрямую (быстро, ~2с). Если бинарника нет — `search.py --preview` (~4с). Ограничь количество прямых вызовов: максимум 5-7 за всю сессию. После исчерпания — `kanban_block`, не продолжай сырыми инструментами.
7. **`web_extract.py` — рабочая утилита для 1-5 конкретных URL, НЕ для массового сбора.** Скрипт `~/.hermes/scripts/web_extract.py` — параллельный асинхронный сбор контента с ретраями и таймаутами. Используй его когда у тебя уже есть конкретные URL (после поиска). Не используй для каталогов/списков — там `search.py --preview` + crawl4ai. Систематический сбор 10+ URL через `web_extract.py` — красный флаг, остановись.
8. **Прикреплён через --skill — используй web-tools CLI, не search.py / generic fallback.** Когда этот навык прицеплен к Kanban-задаче через `--skill web-search-scraper`, а в body сказано «используй web-tools» — не игнорируй это. Запускай `~/.cargo/bin/web-tools search "запрос" --count 30 --source yandex`. Если бинарника нет — fallback на `uv run search.py --query "..." --preview` с абсолютным путём.

9. **`web_extract.py` зависает при запуске через terminal() если stdin не tty.** Когда `sys.stdin.isatty()` возвращает False (Hermes terminal без tty), скрипт пытается читать stdin и вечно ждёт. Фикс: скрипт проверяет `select.select()` с 0.5с таймаутом. Если всё равно зависает — передай URL как аргументы командной строки, а не через пайп.

10. **`web_extract.py` — передавай --chars=N или --chars N.** Скрипт поддерживает оба варианта. Без --chars дефолт 3000 символов.

11. **SSH Host key verification failed при gh clone.** Перед клонированием репозиториев через gh — выполни `ssh-keyscan github.com >> ~/.ssh/known_hosts`. Без этого git падает с "Host key verification failed".

12. **`web-tools` бинарник — проверить `~/.cargo/bin/`.** Если `web-tools` не в PATH, используй полный путь. Скачать: `gh release download -R ogodevonline/web-tools --pattern 'web-tools-linux-amd64' --output ~/.cargo/bin/web-tools && chmod +x ~/.cargo/bin/web-tools`.

13. **⚠️ ЗАГРУЖАЙ ЭТОТ НАВЫК ДО ЛЮБОГО ПОИСКА/ИССЛЕДОВАНИЯ.** Даже если в памяти сказано "web-tools приоритетнее", без загрузки навыка ты не увидишь точных команд и используешь встроенный `web_search` — это гарантированно вызывает 😡 пользователя. Если запрос — исследование, обзор сервисов, анализ рынка, разведка — сперва `skill_view('web-search-scraper')`, потом `terminal('web-tools search ...')`. Не делай наоборот. Trigger-секция выше — это не рекомендация, это правило.

14. **⚠️ SOUL.md enforcement chain (урок 12.06.2026).** Навык установлен, содержит правила, но агенты его игнорируют — потому что `skill_view('web-search-scraper')` НЕТ в их SOUL.md. Наличие навыка на диске — ПАССИВНО. Агенты загружают навык ТОЛЬКО если их SOUL.md вызывает `skill_view('имя-навыка')`. Фикс: добавь `skill_view('web-search-scraper')` в корневой `~/.hermes/SOUL.md` и во все профильные `~/.hermes/profiles/*/SOUL.md`. Сейчас там уже есть во всех 19 — поддерживай это состояние.

15. **🔍 Source hierarchy для юридических/регуляторных запросов.** Когда пользователь спрашивает о законах, правилах, сроках или требованиях (регистрация, визы, налоги, штрафы в другой стране) — СНАЧАЛА проверь официальные первоисточники (lex.uz, pravo.gov.ru, официальные тексты договоров, mid.ru), а не форумы и блоги. Порядок приоритета: (1) текст закона/договора — конкретная статья, (2) официальные разъяснения госорганов, (3) проверенные юридические публикации, (4) форумы/блоги — ТОЛЬКО если первичные источники недоступны. Пользователь проверяет достоверность — всегда указывай конкретный документ и статью. Исключение: запрос на «реальный опыт» / «отзывы» — там форумы уместны как источник практики.
    **Для РФ: «подписан» ≠ «вступил в силу».** Миграционные реформы вводятся поэтапно (ФЗ № 241-ФЗ от 26.07.2026 подписан, но основные нормы с 01.01.2027, обмен ФНС→МВД с 01.10.2026). Всегда проверяй постатейные сроки вступления. Рабочие источники: publication.pravo.gov.ru, consultant.ru/law/hotdocs, lexpat.ru (постатейный разбор); НЕ работают через extract: rg.ru (401), glavbukh.ru (cookie-sync редирект). См. `references/russian-migration-law-2026.md`.

16. **⚠️ GitHub-специфичные запросы — НЕ через web-search.** Если пользователь просит найти/скачать репозиторий, библиотеку, или проверить существование проекта на GitHub — НЕ используй web-search. Сначала `gh search repos` (если `gh` авторизован), или `curl -H "Authorization: token \$GH_TOKEN" "https://api.github.com/search/repositories?q=..."`. GitHub API даёт точный ответ. Web-search по GitHub даёт мусор и пропускает точное название. Только если GitHub API недоступен (нет токена) — web-search как крайний fallback.
    - **404/пустой результат ≠ репозитория не существует.** Причина может быть в отсутствии доступа к приватному репозиторию, другом аккаунте пользователя, или репозитории только локально. Если пользователь утверждает что репозиторий есть — спроси `git remote -v`.

17. **🔐 Google Docs — не читается без аутентификации.** Если пользователь даёт ссылку на Google Docs (`docs.google.com/document/d/{ID}`):
    1. Сначала `curl -sL "https://docs.google.com/document/d/{ID}/export?format=txt"` — если ответ содержит HTML страницы входа или переадресацию на accounts.google.com, документ требует логина
    2. Затем `curl -sL "https://docs.google.com/document/d/{ID}/pub"` — проверь, опубликован ли документ (ответ «Файл не обнаружен» = не опубликован)
    3. Если оба не сработали — сообщи пользователю, что документ требует Google-логина. Предложи варианты:
       - Изменить доступ: «Все, у кого есть ссылка» (без входа)
       - Опубликовать в веб (Файл → Опубликовать → получить /pub ссылку)
       - Скачать и прислать текстом / файлом
    4. После изменения доступа — перепроверь `/export?format=txt`. Документ откроется как plain text.

18. **🛒 CIS/Uzbek e-commerce — алгоритм по типам сайтов.**
    
    **A) Texnomart.uz, Mediapark.uz** — SPA на JS, `web-tools extract` пустой. Используй browser.
    - Алгоритм: `web-tools search` → `browser_navigate` → модалка региона (нажать "Да") → `browser_console` с JS-селекторами.
    
    **B) Uzum.uz** — **Yandex SmartCaptcha, browser тоже блокируется.** Uzum.uz имеет агрессивную антибот-защиту (Yandex SmartCaptcha), которая не пропускает ни curl, ни browser_navigate (редирект на `tmgrdfrend/showcaptcha`).
    - **Рабочий подход — поисковые сниппеты:**
      1. `~/.cargo/bin/web-tools search "товар site:uzum.uz"` — поиск через Яндекс/Google
      2. Изучи **заголовки и сниппеты** результатов — Uzum часто выводит цену прямо в title (например: «Отборные зерна кукурузы для попкорна, 0.5 кг, 1 кг, 2 кг за 74500 сум»)
      3. Для нескольких товаров — запускай параллельные `web-tools search` (разные терминалы), не последовательные
      4. Если в сниппете есть несколько SKU с разными ценами → извлеки минимальную и максимальную
      5. **Важно:** цена в сниппете может быть за самый дешёвый вариант (0.5 кг), а не за 2 кг. Пиши «от X сум» или указывай неопределённость.
    - **Когда browser не работает — не пытайся повторно.** Если browser_navigate на Uzum.uz показывает капчу — сразу переходи к поисковым сниппетам.
    - **Ozon.uz** — не показывает цены без JS, browser может работать (капчи нет), пробуй browser как fallback.
    
    **C) Общие правила:**\n    - Всегда начинай с `web-tools search` для предварительной разведки\n    - Цены в сум → перевести в USD (проверить курс на сегодня: `~/.cargo/bin/web-tools search`)\n    - См. `references/ecommerce-price-research.md` с реальными ценами\n\n    **D) Wildberries.uz (узбекский сегмент WB)** — browser работает, JS SPA.\n    - `browser_navigate` → вводи запрос в поисковую строку (ref из snapshot)\n    - Цены скрыты в ноде: ищи `insertion`/`deletion` (старая/новая цена) или текст с `сум`\n    - Чтобы открыть товар — `browser_click` по article → жди загрузки → `browser_snapshot(full=true)`\n    - Если не открылся (клик не сработал) — доставай URL ссылки из article через browser_console\n    - **Питфолл:** WB.uz не показывает цену в accessibility snapshot для товаров из списка. Нужно либо кликнуть в карточку, либо использовать browser_console с селектором цен\n\n    **E) OLX.uz** — объявления живут недолго.\n    - Через browser любое объявление **старше нескольких дней** показывает "Объявление больше не доступно"\n    - Рабочий подход: `web-tools search \"site:olx.uz товар\"` → берём заголовки и цены из сниппетов поиска\n    - OLX — SPA, curl не даёт контент\n    - Для актуальных предложений — ищи свежие объявления (сниппет содержит дату), старые игнорируй

19. **🏦 Узбекские банковские сайты — web-tools extract не раскрывает курсы.** Kapitalbank.uz → HTTP 403 (WAF). Anorbank.uz → показывает базовый курс, но региональные ставки спрятаны за expand-ссылкой. Алгоритм:
    1. `web-tools search` — найти страницу курсов банка
    2. `web-tools extract` — попробовать (если 403 → browser)
    3. `browser_navigate` — открыть страницу курсов
    4. Искать expand-элементы: ссылки "отличается в зависимости от региона", выпадающие списки городов
    5. `browser_click` по expand → таблица раскроется
    6. `browser_snapshot` — найти строку своего города
    - Пример: Anorbank — после клика на "Курс доллара США, USD отличается в зависимости от региона" раскрывается таблица со всеми городами.
    - L-образный подход: `web-tools search` для перечня источников, browser для конкретных страниц банков.

20. **💱 Курсы валют в Узбекистане — агрегаторы с JS-рендером.** `pulbek.uz/currencies/{city}` — JS-сайт, `web-tools extract` не работает. Используй browser + browser_console для извлечения таблицы курсов:
    1. `browser_navigate("https://pulbek.uz/currencies/nukus")`
    2. `browser_console` с JS: `document.querySelectorAll('[class*="bank"], [class*="currency"], [class*="rate"]')` → `textContent` — собирает все строки банков с курсами.
    3. Формат данных: Название банка → Купить USD → Сдать USD → Купить EUR → Сдать EUR → Купить RUB → Сдать RUB.
    4. **Пользователь говорит «купить сумы за доллары»** = ему нужен курс **«Сдать»** (банк покупает его доллары). Чем выше — тем выгоднее.
    5. `bankchart.uz/spravochniki/kursy_valyut_city/{id}` — `web-tools extract` работает, показывает средние курсы по городу и список банков. ID Нукуса: 117198.
    6. `bank.uz/currency` — только топ-3 курса по стране, без фильтра по городам.
    7. Не гнаться за идеалом: разница между банками в одном городе 20-50 сум (~$0.15-0.40 на $100).
    8. См. `references/uzbekistan-currency-rates.md` для полного алгоритма и таблицы источников.

21. **🔢 Идентификатор от пользователя — ищи ДОСЛОВНО, а не generic-запросами.** Когда пользователь даёт конкретный номер/код (лицевой счёт, SOATO-код, артикул, «35401», «1503514») и спрашивает «что это / где это / как по нему платить» — НЕ начинай с общих запросов («как оплатить свет в Узбекистане»). Ищи сам идентификатор: `web-tools search "\"35401\" elektr energiya" --domain uz --lr 11117`. Пользователь прямо ругает: «по номеру просто поищешь?», «35401 надо искать было» (урок 09.08.2026). В сессии именно дословный поиск кода в узбекском домене вывел на официальную форму идентификации абонентов ГорЭСП Нукуса (nukis-connect.lovable.app), где код подтверждается. Generic-запросы по тем же номерам дали мусор (законы Калифорнии, светильники). Правило: есть идентификатор → ищи его в кавычках + контекст страны/домена → только потом обобщай.

22. **⚠️ «Найди работающий сайт/сервис» — проверяй ЖИВЬЁМ перед рекомендацией, не вываливай выдачу.** Поисковая выдача — список кандидатов, НЕ подтверждение: многие сайты мертвы или мусорны. Пользователь прямо ругается за непроверенное («ты выходил хоть проверил», урок 24.08.2026). Алгоритм:
    1. Все кандидаты разом: `curl -s -o /dev/null -w "%{http_code}" -L "https://домен"` (000 = не резолвится = мёртв).
    2. Живых — реальный тест через `browser_navigate` с настоящей ссылкой: вставь URL в форму, нажми кнопку, проверь, что появился файл/прямая ссылка, а НЕ редирект на рекламу.
    3. Рекомендуй только лично проверенное, помечай ✅ проверено / ⚠️ непроверено.
    - Кейс (Instagram-даунлоадеры, 24.08.2026): из 5 «топ-сайтов 2026» реально работал только `yt-dlp` (уже стоит на сервере: `~/.local/bin/yt-dlp`, качает IG reels/посты/stories без логина). snapinsta.io — мёртв (DNS 000), sssinstagram.com — редирект на AliExpress (мусор), savefrom.net — форма есть, результат не выдаёт (IG блокирует), snaptik.app — только TikTok. Сайты-даунлоадеры Instagram массово дохнут, т.к. IG требует авторизацию/капчу.
    - Рабочий вывод при отсутствии живого сайта: предложи скачать самому через yt-dlp (пользователь кидает ссылку → ты качаешь → присылаешь файл) — надёжнее любого сайта.

## Связанные файлы

- `references/uzbekistan-currency-rates.md` — поиск и сравнение курсов валют в городах Узбекистана (агрегаторы, JS-извлечение, таблица сравнения)
- `references/web-tools-cli.md` — полная справка по `web-tools` CLI (Rust бинарник, приоритетный инструмент)
- `references/research-strategy.md` — какой инструмент когда использовать (все инструменты поиска)
- `references/flight-search.md` — поиск авиабилетов: отдельные запросы по датам, XMLStock, агрегаторы через поиск
- `references/russian-ecommerce-research.md` — поиск товаров по точным габаритам/характеристикам в РФ (работающие и неработающие магазины, алгоритм, pitfalls)
- `references/github-search-fallback.md` — GitHub API через curl (fallback когда gh не работает)
- `references/uzbekistan-registration.md` — регистрация иностранцев в Узбекистане
- `references/playwright-instagram-scraping.md` — развёртывание Playwright Instagram scraper на headless VPS (сессии, логин, типичные ошибки): правила для россиян (15 дней), работающие сервисы (emehmon.uz), штрафы
- `references/ecommerce-price-research.md` — сбор цен с узбекских e-commerce (Texnomart, Uzum, OLX): browser console для JS-сайтов, перевод сум→USD, примеры реальных цен на технику/мебель
- `references/russian-migration-law-2026.md` — поиск изменений законодательства РФ (ВНЖ/РВП): алгоритм, поэтапные сроки вступления, рабочие/нерабочие источники, срез миграционной реформы 2026 (241-ФЗ, 162-ФЗ, 314-ФЗ)
