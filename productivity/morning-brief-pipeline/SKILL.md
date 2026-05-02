---
name: morning-brief-pipeline
description: Утренний бриф — разбивка на чанки, умное сокращение ссылок, fallback на plain text. Отправка в Telegram по расписанию.
---

# Morning Brief Pipeline (обновлён 23.04.2026 + перевод новостей)

Создаёт утренний бриф и отправляет его в Telegram по расписанию. **Ключевое:** сообщения разбиваются на чанки ≤2500 символов, чтобы не превысить лимит Telegram. Ссылки сокращаются только если они очень длинные (>100 символов). **Все английские новости переводится на русский.**

## Структура

```
~/.hermes/
├── skills/productivity/morning-brief-pipeline/
│   └── scripts/
│       └── brief/               # Пакет-модуль
│           ├── __init__.py       # generate_brief(), chunking, simplify_links()
│           ├── weather.py        # get_weather()
│           ├── infra.py          # get_infra_status()
│           ├── tasks.py          # get_one_big_thing()
│           ├── news.py           # get_all_signals()
│           ├── gmail.py          # get_gmail_inbox()
│           ├── calendar.py       # get_calendar()
│           └── habits.py         # get_workspace_tasks(), get_personal_and_habits()
│           └── morning_brief.py  # Альтернативная точка входа
├── cron/
│   └── output/
│       └── morning_brief.md  # Полная версия (сохраняется)
└── tasks/                    # YAML-конфиги задач/привычек
```

## Architecture: Поток данных

```
┌─────────────────────────────────────────────────────────────┐
│  generate_brief()                                          │
│    ├─► weather.py → infra.py → tasks.py                    │
│    ├─► news.py ───┐                                         │
│    │              │                                          │
│    │              ▼                                          │
│    │      [translate_english_news()] ← .env TRANSLATOR_API │
│    │              │                                          │
│    │              ▼                                          │
│    └─► gmail.py → calendar.py → habits.py                  │
└─► gmail.py → calendar.py → habits.py                  │
│                                                              │
│    └─► format_brief_as_chunks() → send_brief_chunks() ──► Telegram
└─────────────────────────────────────────────────────────────┘

**Важно:** Новости УБРАНЫ из утреннего брифа (27.04.2026). Теперь они
отдельным дайджестом в 13:30 МСК — см. навык `news-digest`.

## Быстрый запуск

```bash
cd ~/.hermes/skills/productivity/morning-brief-pipeline/scripts && python3 -c "from brief import generate_brief; generate_brief()"
```

## Архитектура отправки

Бриф собирается как единый текст, затем разбивается на **чанки** и отправляется отдельными сообщениями:

1. **Заголовок** — `🌅 Утренний бриф — {день}, {дата}`
2. **Статус системы + Погода + Главная задача** (1–2 чанка)
3. **Почта** — заголовок уже вшит в `get_gmail_inbox()` (не дублируем)
4. **Календарь** — заголовок уже вшит в `get_calendar()` (не дублируем)
5. **Задачи + Личное + Привычки** (разбиваются при необходимости)
6. **Футер** — время генерации

> **Новости убраны** из утреннего брифа (27.04.2026). Отдельный дайджест в 13:30 МСК — `news_digest.py`.

### Лимиты и обработка

| Параметр | Значение |
|----------|---------|
| Макс. длина чанка | **2500 символов** (безопасный лимит Telegram с Markdown) |
| Упрощение ссылок | Только если URL **>100 символов** (остальные — как есть) |
| Fallback parse_mode | При любой ошибке Markdown → повтор с `parse_mode=None` (plain text) |
| Группировка новостей | По эмодзи-заголовкам, чтобы не разрывать контекст |
| Перевод новостей | Максимум 5 статей за запуск, только `lang='en'` |

### Ключевые функции (`brief/__init__.py`)

- `generate_brief()` — точка входа, собирает все модули, форматирует, сохраняет в файл, отправляет чанками
- `format_brief_as_chunks()` — возвращает `list[str]` чанков
- `split_to_chunks(text, max_len=2500)` — разбивает текст по строкам, не обрывая слов
- `split_by_sections(text)` — делит новости на блоки по эмодзи-заголовкам (`📱 **...**`, `🌍 **...**` и т.д.)
- `simplify_links(text)` — сокращает **только очень длинные** URL (>100 символов) до домена
- `send_brief_chunks(chunks)` — циклит отправку, возвращает `True` если все чанки отправлены
- `send_telegram_message(text)` — отправляет один чанк, пробует Markdown → plain text
- `translate_english_news(news_list)` — переводит английские новости на русский (≤5 статей)

## Упрощение ссылок

Правило: **оставляем как есть, если URL ≤100 символов** (даже с `?` и `#`). Сокращаем только супер-длинные.

```
✅ Оставляем:
  [mail](https://mail.google.com/mail/u/0/?view=pt&message_id=ID)  # ~80 chars
  [gh](https://github.com/affaan-m/everything-claude-code)       # ~55 chars
  [news](https://techcrunch.com/2026/04/22/short-slug/)          # ~70 chars

🔧 Сокращаем (→ domain):
  [long](https://techcrunch.com/2026/04/22/instagram-tests-a-new-instants-app-for-sharing-disappearing-photos/)
     → [long](techcrunch.com)
  [cal](https://www.google.com/calendar/event?eid=very-long-eid-string...)
     → [cal](google.com)
```

## Формат вывода (пример)

```
🌅 **Утренний бриф — Четверг, 23 April 2026**

⚡️ **Статус системы**
⚠️ Docker: нет работающих контейнеров
💾 Диск: 61% занято, свободно 7,4G
...

🌦️ **Погода — Москва**
🌡️ **Сейчас:** ⛅ 2°C (ощущается -3°C), Partly cloudy
...

🎯 **Главное на сегодня:** Сходить в зал

📧 **Почта** — 7 непрочитанных:
  • **Pydantic Team** — [Integrate Logfire](...)

📅 **Календарь:**
  • 🕐 08:00 — [✍ Focus time](...)

💻 **Задачи — 1 шт.:**
  🟡 Позвонить маме

🏠 **Личное — 2 дела:**
  🔴 Сходить в зал

✅ **Привычки:**

_🕐 Сгенерировано: 09:45 МСК_
```

## Google Workspace

- **Аккаунт по умолчанию:** `svaaugust` (`svaaugust@gmail.com`)
- **Токены:** `~/.hermes/google_token_svaaugust.json`
- `gmail.py` и `calendar.py` явно передают `--account svaaugust` в `google_api.py`

## .env Variables

```bash
# Ключ для перевода английских новостей на русский
TRANSLATOR_API_KEY=sk-...
# (можно использовать OpenAI, DeepL, Yandex, любой переводчик)
```

## Cron

- **Время:** 6:00 МСК (3:00 UTC)
- **Расписание:** `0 3 * * *` (через `cronjob` или crontab)
- **Команда:** (через task-manager демон, `cronjobs.yml → script: brief`)
- Полный лог: `~/.hermes/cron/output/morning_brief.md`

> **Обеденный дайджест новостей** — 13:30 МСК (10:30 UTC) — настроен через cronjob 'news-digest'

## Pitfalls

1. **Telegram лимит 4096 символов** — даже с Markdown может не пройти. Решение: чанки ≤2500 + fallback plain text.
2. **Markdown parse errors** — кириллица и спецсимволы в `parse_mode=Markdown`. Решение: при любой ошибке парсинга — повтор без parse_mode.
3. **Длинные URL** — garbage-ссылки с долгими путями/фрагментами. Решение: `simplify_links()` оставляет только домен для URL >100 символов.
4. **Дубли заголовков** — `get_gmail_inbox()` и `get_calendar()` уже содержат свои заголовки (`📧 **Почта**`, `📅 **Календарь:**`). При сборке чанков не добавлять их повторно.
5. **Аномальная погода** — WeatherAPI иногда возвращает снег при плюсовых температурах. TODO: фильтр или альтернативный источник.

## Что ещё можно улучшить

- [x] **Новости вынесены в отдельный дайджест** (27.04.2026 → `news_digest.py` в 13:30 МСК)
- [x] **Перевод английских новостей на русский** (API ключ из .env, max 5 статей)
- [x] **Задачи переведены на SQLite** (29.04.2026 — `tasks.py` и `habits.py` теперь читают через `t list`/`t status`/`t habits` вместо YAML)
- [x] **Периодические задачи в брифе** (30.04.2026 — `habits.py` вызывает `t periodic`, отображает 🔄 напоминания после привычек)
- [ ] Фильтр аномалий погоды (снег при >0°C → замена на \"сложные условия\")
- [ ] Retry-логика для Telegram при сетевых ошибках (backoff)
- [ ] Настройка порога сокращения ссылок через конфиг (по умолчанию 100)
