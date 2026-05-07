---
name: news-digest
category: productivity
description: Обеденный дайджест новостей — blogwatcher DB + KiloCode API + GitHub Trending + Telegram
---

# News Digest Pipeline

Собирает новости из blogwatcher DB (28+ источников), фильтрует по ключевым словам,
переводит английские заголовки на русский через KiloCode AI, добавляет AI-аннотации
и GitHub Trending, отправляет в Telegram в HTML-формате.

> **⚠️ Git:** Скилы на GitHub: `ogodevonline/hermes-skills-productivity`. Для отката: `git log`, `git checkout`.

## Работа с контентом статей

Если нужно загружать полный текст статей для аннотаций — использовать blogwatcher-cli
(статьи уже загружены при сканировании), а не парсить URL через trafilatura/bs4.
blogwatcher — единственный источник данных для дайджеста, любые изменения через него.

**Скрипт:** `~/.hermes/skills/productivity/news-digest/scripts/news_digest.py`
**Расписание:** 13:30 МСК (10:30 UTC) через task_manager
**API:** KiloCode Gateway (`https://api.kilo.ai/api/gateway`)
**Модель:** `kilo-auto/small` (дёшево, для фоновых задач)
**Fallback:** `inclusionai/ling-2.6-flash:free` → `openrouter/free`
**Ключ:** `KILOCODE_API_KEY` из `.env`
**Режим:** Streaming (`stream: true`) — free модели нестабильны без streaming

## Структура данных

### Категории и фильтрация

| Категория | Иконка | Примеры ключевых слов |
|-----------|--------|----------------------|
| Security  | 🔐 | CVE, vulnerability, exploit, malware, ransomware, breach, stalkerware |
| OSINT     | 🕵️ | osint, forensics, reconnaissance |
| Python/AI | 🐍 | python, django, fastapi, llm, gpt, openai, pytorch, granite, trainium, copilot |
| Policy    | 🏛️ | policy, regulation, gdpr, sanction, export-control |
| Russia    | 🇷🇺 | russia, россия, moscow, москва, kremlin, ukraine |
| Tools     | 🔧 | release, tool, library, framework, update, monad, mozilla |
| GitHub    | 🐙 | Trending (отдельная секция) |

### ⚠️ Важно: word boundaries для коротких ключей
Ключи `ai`, `ml`, `ru`, `us`, `eu` (≤3 символов) проверяются через `\bai\b` — иначе "ai" матчится в "said", "available", "trainium". Это критично для фильтрации BBC World статей.

### Blacklist (фильтрация мусора)

- `BLACKLIST_WORDS` — русские и английские мусорные слова (промокоды, зоотовары, батарейки, купоны)
- `BLACKLIST_DOMAINS` — мусорные домены (маркетплейсы)
- Проверка `is_blacklisted()` перед фильтрацией по ключевым словам

## Pipeline

```
blogwatcher-cli scan -> blogwatcher DB -> get_recent_articles(24h→48h→72h, 30)
    -> is_blacklisted() отсев мусора
    -> matches_keywords() фильтрация (с \b word boundaries для коротких ключей)
    -> categorize() группировка по категориям
    -> translate_articles() батчевый перевод через KiloCode (батчи по 10)
    -> summarize_articles() AI-аннотации (батчи по 10, макс 20 статей по приоритету категорий)
    -> get_github_trending_merged() парсинг github.com/trending (daily+weekly+monthly), мерж, топ-7 по звёздам
    -> github_summarize() AI-аннотации для репозиториев (чем полезен, для кого)
    -> format_digest() HTML-форматирование (макс 4 статьи на категорию)
    -> split_chunks(max_len=3800) -> send_telegram_chunks(parse_mode=HTML)
```

## Ключевые особенности

### API и модели

- **Основная:** `kilo-auto/small` — дёшево, стабильно в streaming режиме
- **Fallback 1:** `inclusionai/ling-2.6-flash:free` — бесплатно, нестабильно без streaming
- **Fallback 2:** `openrouter/free` — последняя надежда
- **Streaming обязателен** для KiloCode free/small моделей — в non-streaming возвращают `content: null`
- `deepseek/deepseek-v4-flash` и `deepseek/deepseek-v3.2` НЕ работают через KiloCode Gateway

### Перевод заголовков

- Батчевый по 10 заголовков (KiloCode замедляется при >10: 5→7с, 10→22с, 26+→таймаут)
- Fallback: поштучный перевод при ошибке батча
- Определение английского: латиница > кириллица И > 5 латинских символов
- Оригинал сохраняется в `title_original`, выводится в скобках
- Ответ KiloCode очищается от markdown-кода (```json ... ```) перед парсингом

### AI-суммаризация

- Каждая статья получает краткую аннотацию (2-3 предложения на русском)
- Батчи по 10 статей — модель нестабильна при >10
- Формат ответа: JSON-массив строк (очищается от markdown-кода)
- Поле `summary` добавляется к статье
- **Лимит:** максимум 20 статей для суммаризации (по приоритету категорий: security > osint > python_ai > policy > russia > tools > general)
- **Промпт** просит указать практическую значимость для Python-разработчика, отметить санкционные/российские аспекты, новые возможности/угрозы

### GitHub Trending

- **Источник:** парсинг `github.com/trending?since=daily|weekly|monthly` — три периода
- **Объединение:** репозитории со всех трёх периодов мержатся, дубликаты удаляются, сортировка по звёздам
- **Лимит:** все уникальные репозитории (сейчас ~16), сортировка по звёздам
- **Формат вывода:**
  ```
  • <a href="url">repo</a> [Lang] ⭐N 🍴N — Краткое описание (80 символов) 🏷️topic1
    💡 AI-аннотация (для кого, чем полезен)
  ```

### Формат статьи (HTML)

```
  • <a href="url">Переведённый заголовок</a> <i>(ориг: Original Title)</i>
    <i>(Источник)</i>
    💬 Аннотация (1-2 предложения)
```

- Telegram отправка с `parse_mode: HTML`
- `html_escape()` экранирует `<`, `>`, `&` во всех текстах

### Разбивка на чанки

- max_len: 3800 символов (безопасный лимит для Telegram)
- Разбивка по границам строк — не рвёт строки
- Каждый чанк отправляется отдельным сообщением

## Ручной запуск

```bash
cd ~/.hermes/skills/productivity/news-digest/scripts && python3 news_digest.py
```

Логи: `~/.hermes/cron/output/news_digest_YYYYMMDD.md`

## Настройка расписания

Запись в таблице `cron_jobs` в `~/.hermes/tasks/tasks.db`:
```sql
INSERT INTO cron_jobs (name, script, schedule, description)
VALUES ('News Digest', 'news_digest', '30 10 * * *', 'Дайджест новостей в 13:30 МСК');
```
Расписание в UTC: 10:30 UTC = 13:30 МСК.

Зарегистрировать в SCRIPT_COMMANDS в main.py (task_manager/main.py):
```python
SCRIPT_COMMANDS = {
    ...
    "news_digest": ["python3", "news_digest.py"],
    ...
}
```

## Pitfalls

1. **400/401 ошибка при вызове OpenAI endpoint** — скрипт больше не использует `api.openai.com`. Весь AI — через KiloCode Gateway. Если видишь 400/401 — проверь что `KILOCODE_API_KEY` в `.env` актуален.
2. **KiloCode free модели возвращают null в non-streaming** — все API вызовы обязательно с `stream: true`. Non-streaming даёт `content: null` на большинстве free моделей.
3. **DeepSeek модели не работают через KiloCode** — не трать время на `deepseek/deepseek-v4-flash` или `deepseek/deepseek-v3.2`. Используй `kilo-auto/small`.
4. **Суммаризация >10 статей в одном батче** — KiloCode возвращает меньше результатов чем запрошено. Разбивай на батчи по 10. То же касается перевода — батчи >10 заголовков могут зависнуть, так как KiloCode пропорционально замедляется (5 заголовков ~7с, 10 ~22с, 26+ таймаут).
5. **Blogwatcher scan и пустой дайджест** — если scan не нашёл новых статей (битые фиды, старые данные), скрипт пробует расширить окно: 24ч → 48ч → 72ч. Лимит статей увеличен до 30. Если и это пусто — проверь фиды через `blogwatcher-cli scan | grep -i error`. Многие RSS-фиды со временем ломаются (301, 403, 404) — нужна периодическая чистка.
6. **GitHub API rate limit** — без токена ~60 req/h, для одного запуска в день — ок.
7. **Ошибка перевода** — заголовки остаются английскими, не падаем. Скрипт пробует батч, затем поштучно, затем пропускает.
8. **Мусорные статьи** — blacklist расширяемый. Если видишь промокоды/спам в дайджесте — добавь слово/домен в `BLACKLIST_WORDS` или `BLACKLIST_DOMAINS`.
9. **Лимит статей 30 — не 60 и не 20** — лимит увеличен с 20 до 30. При большом количестве статей приоритет по категориям: security, osint, python_ai, policy, russia, tools, general.
10. **Word boundaries для коротких ключей** — "ai", "ml", "ru", "us", "eu" матчатся как подстроки (в "said", "available", "группа"). Всегда используй `\bai\b` (с re.search) в `matches_keywords()` и `categorize()` для ключей ≤3 символов. Аналогично для "ai" в заголовках новостей — иначе BBC World статьи про китов и нефть попадают в Python/AI категорию.
11. **Markdown-код в ответе KiloCode** — API может возвращать `` ```json ... ``` `` вместо чистого JSON. Все парсеры (перевод, суммаризация, GitHub) сначала очищают ответ: `cleaned = result.strip()` + удаление markdown-блоков перед JSON-парсингом.
12. **Жадный vs нежадный regex для JSON-массивов** — `re.search(r'\[.*?\]', text, re.DOTALL)` находит первое вхождение `]`, обрезая массив. Используй `re.search(r'\[.*\]', text, re.DOTALL)` (жадный) для корректного захвата всех элементов.
13. **Streaming обязателен** для KiloCode — free/small модели возвращают `content: null` в non-streaming режиме. Параметр `stream: True` и итерация `resp.iter_lines()`.
14. **Blogwatcher scan требует таймаут 120с** — вызов `blogwatcher-cli scan` в начале `main()` использует `timeout=120`, а не стандартные 15с из `_run_command()`. При редактировании кода убедись, что таймаут остаётся большим — некоторые источники (BBC, блоги) загружаются медленно.
15. **GitHub Trending stale data** — старый запрос `created:>=7дней` через Search API возвращал одни и те же репозитории несколько дней (топ за неделю почти не меняется). Реальный github.com/trending показывает репозитории по относительному приросту звёзд. Решение: парсить `github.com/trending?since=daily|weekly|monthly` HTML, извлекать owner/repo через regex `href="/owner/repo"`, дёргать `/repos/{owner}/{name}` для деталей. `get_github_trending_merged()` объединяет все три периода, убирает дубликаты, сортирует по звёздам. GitHub API rate limit без токена ~60 req/h — для одного запуска (макс 21 запрос) ок.
