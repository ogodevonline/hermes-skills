---
name: insta-flat-parser
category: productivity
description: "Telegram-бот @insta_flat_parser_bot — мониторинг Instagram-аккаунтов недвижимости Нукуса, извлечение контактов, leads."
---

# Insta Flat Parser Bot

Telegram-бот для парсинга Instagram-аккаунтов недвижимости в Нукусе (Каракалпакстан).

**Бот:** @insta_flat_parser_bot
**Проект:** `~/Projects/Personal/GitHub/insta_flat_parser/`
**БД:** `~/.insta_flat_parser/state.db`
**Instagram-сессия:** `~/.config/instaloader/session-svaaugust@gmail.com.json`

---

## Когда загружать

- Пользователь спрашивает про insta_flat_parser бота
- Нужно проверить статус, перезапустить, залогиниться
- Нужно добавить/удалить аккаунты для мониторинга
- Проблемы с мониторингом Instagram
- Жалоба «не приходят уведомления» — см. раздел Диагностика

---

## Основные команды Telegram бота

| Команда | Что делает |
|---------|-----------|
| `/start` | Приветствие + список команд |
| `/add <username>` | Добавить аккаунт в мониторинг |
| `/remove <username>` | Удалить аккаунт из мониторинга |
| `/list` | Список всех аккаунтов со статусом |
| `/status` | Статистика: активные/неактивные, leads |
| `/addlead` | Добавить объявление вручную (форма) |
| `/leads` | Список всех объявлений |
| `/search <текст>` | Поиск по leads |
| `/lead <id>` | Детали объявления |
| `/comment <id> <текст>` | Добавить комментарий к lead |
| `/done <id>` | Отметить lead как выполненный |
| `/archive <id>` | Архивировать lead |
| `/app` | Web App (Mini App) |

---

## 🧠 Ключевые уроки этой сессии

### Три статуса — никакого is_favorite для навигации

Вкладки Mini App должны фильтроваться строго по `status`:
- **Добавленное** → `status === 'new'`
- **Избранное** → `status === 'in_progress'`
- **Архив** → `status === 'archived'`

Не использовать `is_favorite` для навигации! `is_favorite` существует в БД, но привязан к старой логике. Новая логика: ⭐ просто переключает статус на `in_progress`.

### При жалобах на UI — спросить ожидаемое поведение ДО правок

Худший сценарий: сделать 5 итераций с гаданием. Пользователь злится с каждой итерации.
Лучший сценарий: «Опиши словами — что должно происходить при нажатии каждой кнопки?» — и сделать за 1 раз.

### После изменения статуса — оставаться на карточке

При нажатии на кнопку (В избранное / В архив / Вернуть) — не возвращать в список (`loadList()`), а остаться на карточке (`showDetail(id)`), чтобы пользователь видел обновлённые кнопки и мог дальше взаимодействовать.

Кнопка «← Назад» должна грузить свежие данные с сервера (`goBack()` = `allLeads = await api(...)` + `render()`), а не просто рисовать старый `allLeads`.

---

## Мониторинг Instagram

### Архитектура

```
Monitor (async)
  ├── Scraper Pool (round-robin, ротация через 50 запросов)
  │     └── InstagramScraper (Playwright headless, GraphQL API interception)
  ├── DataExtractor (regex + OCR tesseract)
  └── StateStorage (SQLite)
```

### Параметры (.env)

| Параметр | Значение (рекомендуемое) | Описание |
|----------|-------------------------|----------|
| `CHECK_INTERVAL` | **15** (не 3!) | Минут между циклами. 3 — слишком часто, дёргает Instagram и жжёт сессию |
| `MAX_CONCURRENT` | 3 | Параллельных проверок |
| `POSTS_PER_CHECK` | 5 | Постов за проверку |
| `OCR_ENABLED` | true | Tesseract OCR на превью |
| `WHISPER_ENABLED` | **false** | Отключён (жрёт CPU, модель small на CPU — минуты на одно видео). Для извлечения контактов хватает caption + комментариев |

### Auto-recovery (добавлено июль 2026)

При падении Playwright контекста (сессия протухла/краш браузера):
- Scraper убивается, удаляется из пула, создаётся новый
- Запрос повторяется 1 раз
- Аккаунт **не помечается** неактивным

### Session health check при старте

При запуске монитора:
- Проверяется cookie `ds_user_id`
- Если сессия протухла → Telegram alert + блокировка старта

### Mass-failure alert

Если ≥50% аккаунтов упали с одинаковой ошибкой за цикл → Telegram уведомление.

---

## Mini App (Web App)

**Файл:** `src/insta_flat_parser/web/static/index.html`

SPA на чистом JS, без фреймворков. Весь код в одном HTML-файле.

### 🎯 Логика вкладок — ТРИ СТАТУСА (никакого is_favorite для навигации)

**ВАЖНО:** вкладки привязаны к полю `status` в таблице `leads`. Никакого `is_favorite` для переключения между вкладками — это баг, который уже допускался.

| Вкладка | Фильтр (`status`) | Что показывает |
|---------|-------------------|----------------|
| 📋 Добавленное | `=== 'new'` | Новые объявления |
| ⭐ Избранное | `=== 'in_progress'` | Избранные (те, куда нажал звезду) |
| 📦 Архив | `=== 'archived'` | Архивированные |

```javascript
// ПРАВИЛЬНО — фильтр по статусу
let filtered = [];
if (currentTab === 'archived') filtered = allLeads.filter(l => l.status === 'archived');
else if (currentTab === 'fav') filtered = allLeads.filter(l => l.status === 'in_progress');
else filtered = allLeads.filter(l => l.status === 'new');
```

НЕПРАВИЛЬНО — смешивать `is_favorite` и `status` для навигации по вкладкам:
```javascript
// ❌ НЕ ДЕЛАЙ ТАК — приводит к дублям
if (currentTab === 'fav') filtered = allLeads.filter(l => l.is_favorite);
```

### ⚠️ Pitfall: спрашивай ожидаемое поведение ДО правок (критично!)

Пользователь **не объясняет словами** как должно работать. Он говорит «не работает», «неправильно», «всё сломал» — и ждёт что ты сам догадаешься. Каждая неверная догадка = потеря доверия.

**Плохой сценарий (как было в этой сессии — 5 итераций по 10-15 мин каждая):**
1. Пользователь: «в избранном и добавленном одинаковые элементы»
2. → Догадка: убрать дубли через `!is_favorite` ❌
3. Пользователь: «нихуя не так, кнопки нет чтобы вернуть»
4. → Догадка: добавить кнопку «Вернуть» из архива ❌
5. Пользователь: «нету кнопки в добавленное»
6. → Догадка: три статуса `new`/`in_progress`/`archived` ❌
7. Пользователь: «ничего не работает, нету кнопки в добавленное»
8. → Догадка: проблема в кнопках ❌
9. Пользователь: «логика блядь не работает»
10. → Оказалось: после нажатия кнопки loadList() возвращал в список, а не showDetail(id) ❌

**Итого:** час времени, пользователь в ярости.

**Хороший сценарий (как НАДО было):**
Сразу после первой жалобы спросить:
> «Опиши словами: какие должны быть вкладки и что в каждой показывать? Что происходит при нажатии каждой кнопки — объявление остаётся на карточке или уходит в список? Может ли объявление быть в нескольких вкладках одновременно?»

После ответа — **одна реализация**. Без итераций.

**Главное правило:** если пользователь пожаловался на UI — **СТОП**. Не править, пока не спросишь детали. Вопрос занимает 30 секунд. Догадка — 15 минут итераций.

### Кнопки в детальной карточке

| Статус объявления | Показать кнопки | Действие |
|-------------------|-----------------|----------|
| `new` | ⭐ В избранное + 📦 Архив | → `in_progress` / → `archived` |
| `in_progress` | ↩️ В добавленное + 📦 Архив | → `new` / → `archived` |
| `archived` | ↩️ Вернуть | → `new` |

**Критично:** после нажатия на кнопку — **оставаться на карточке** (`showDetail(id)`), а не уходить в список. Кнопка «← Назад» должна загружать свежие данные с сервера:

```javascript
async function setStatus(id, st) {
  await api('/api/leads/' + id + '/status', { method: 'POST', body: JSON.stringify({status: st}) });
  showDetail(id);  // ← остаться на карточке с новыми кнопками
}

async function goBack() {
  allLeads = await api('/api/leads?limit=200');  // ← свежие данные с сервера
  render();
}
```

### Поля даты и времени

Для напоминаний — два отдельных поля `date` и `time`, а не `datetime-local`:

```javascript
{label:'📅 Дата напоминания', key:'remind_date', type:'date'},
{label:'⏰ Время', key:'remind_time', type:'time'},
```

В `saveEdit` дата+время собираются в `remind_at` обратно:
```javascript
const d = document.getElementById('e_remind_date')?.value;
const t = document.getElementById('e_remind_time')?.value;
data.remind_at = (d && t) ? d + ' ' + t : null;
```

Телеграм WebView не поддерживает `datetime-local` (в некоторых версиях просто не отображается), поэтому — только раздельные поля.

### Cache-busting для Mini App

Telegram WebView кэширует index.html агрессивно. После изменений пользователь может видеть старую версию. Добавлять в `<head>`:

```html
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
```

Плюс после перезапуска бота — попросить пользователя закрыть Mini App и открыть заново.

### Проверка: тестовый сценарий

```
1. На вкладке «Добавленное» — есть объявление
2. Нажать на него → открылась карточка
3. Нажать «⭐ В избранное» → остался на карточке, кнопки сменились на «↩️ В добавленное» + «📦 Архив»
4. Нажать «← Назад» → список обновлён, объявления нет на «Добавленное»
5. Перейти на «Избранное» — объявление там
6. Нажать на него → кнопки «↩️ В добавленное» + «📦 Архив»
7. Нажать «📦 Архив» → кнопки «↩️ Вернуть»
8. Нажать «← Назад» → объявление на «Архив»
9. Нажать «↩️ Вернуть» → кнопки «⭐ В избранное» + «📦 Архив» (вернулось в «Добавленное»)
10. Ни в одной вкладке нет дублей
```

---

## CLI команды (из папки проекта)

```bash
cd ~/Projects/Personal/GitHub/insta_flat_parser

# Запустить бота
uv run python -m insta_flat_parser bot

# Запустить только монитор (без бота)
uv run python -m insta_flat_parser monitor

# Логин в Instagram (интерактивный, headless=false)
uv run python -m insta_flat_parser login

# Проверить один аккаунт
uv run python -m insta_flat_parser check <username>

# Извлечь контакты из поста
uv run python -m insta_flat_parser extract <url>

# Список аккаунтов в БД
uv run python -m insta_flat_parser list-accounts

# Импорт аккаунтов из файла
uv run python -m insta_flat_parser import-accounts <file.txt>

# Экспорт активных аккаунтов
uv run python -m insta_flat_parser export <file.txt>
```

---

## Управление аккаунтами мониторинга

### Список аккаунтов в БД

```bash
python3 ~/.hermes/skills/productivity/insta-flat-parser/scripts/list-accounts.py
```

### Реактивация упавших

```bash
python3 ~/.hermes/skills/productivity/insta-flat-parser/scripts/reactivate-accounts.py
```

### Bulk удаление

```python
import sqlite3
conn = sqlite3.connect('/home/hermes/.insta_flat_parser/state.db')
accounts = ['user1', 'user2']
for u in accounts:
    conn.execute('DELETE FROM accounts WHERE username = ?', (u,))
    conn.execute('DELETE FROM known_posts WHERE username = ?', (u,))
conn.commit()
```

---

## Перезапуск бота

```bash
# Убить старый процесс
kill -9 $(ps aux | grep 'insta_flat_parser bot' | grep -v grep | awk '{print $2}') 2>/dev/null
sleep 2

# Запустить в background
cd ~/Projects/Personal/GitHub/insta_flat_parser && uv run python -m insta_flat_parser bot
# Используй terminal(background=true, notify_on_complete=true)
```

---

## Перелогин в Instagram

```bash
cd ~/Projects/Personal/GitHub/insta_flat_parser
uv run python -m insta_flat_parser login
```

Откроется браузер (не headless), введи логин/пароль, если запросит код — введи. Сессия сохранится в `~/.config/instaloader/session-{username}.json`.

---

## Диагностика: монитор не проверяет аккаунты (зависшие страницы Playwright)

### Симптом

Последняя проверка (`last_checked_at`) была часы назад, хотя интервал 15 мин.
Аккаунты все зелёные, ошибок нет.

### Диагностика

```bash
# 1. Есть ли виснущие рендереры Chromium?
bash ~/.hermes/skills/productivity/insta-flat-parser/scripts/check-stuck-renderers.sh

# 2. Если да — убить все виснущие рендереры
kill $(ps aux | grep 'type=renderer' | grep -v grep | awk '{print $2}') 2>/dev/null

# 3. Проверить, поехали ли проверки заново (подождать 1-2 мин)
sqlite3 ~/.insta_flat_parser/state.db "SELECT username, last_checked_at FROM accounts ORDER BY last_checked_at DESC LIMIT 5"
```

### Причина

`page.goto()` с таймаутом 30-60s не спасает, если Playwright page зависает на установке соединения
или `wait_for_load_state("networkidle")` не завершается. Страница не закрывается (`page.close()` тоже виснет),
рендерер остаётся в памяти, аккумулируется, монитор перестаёт работать.

### Решение

Применить паттерн **`asyncio.wait_for`** как жёсткий таймаут поверх всего блока работы со страницей:

```python
page.set_default_timeout(45_000)   # страховка
try:
    return await asyncio.wait_for(_do_fetch(), timeout=60)
except asyncio.TimeoutError:
    # log and return empty
finally:
    # page.close() тоже с таймаутом
    await asyncio.wait_for(page.close(), timeout=5)
```

**Где применять:** `fetch_profile_posts()` и `fetch_post_comments()` в `scraper.py`.

---

## Диагностика: почему не приходят уведомления

### Шаг 1: Бот запущен?

```bash
ps aux | grep insta_flat_parser | grep -v grep
```

### Шаг 2: Аккаунты зелёные?

`/list` в Telegram или `python3 scripts/list-accounts.py`

### Шаг 3: Сессия жива?

```bash
cd ~/Projects/Personal/GitHub/insta_flat_parser && uv run python3 \
  ~/.hermes/skills/productivity/insta-flat-parser/scripts/check-session.py
```

### Шаг 4: Есть ли новые посты?

Скрипт в `references/diagnose-no-notifications.md`

### Шаг 5: Работает ли Telegram API?

```bash
cd ~/Projects/Personal/GitHub/insta_flat_parser && uv run python -c "
import asyncio
from aiogram import Bot
from insta_flat_parser.config import settings
async def test():
    bot = Bot(token=settings.bot_token)
    await bot.send_message(settings.admin_chat_id, '🧪 Тест')
    await bot.session.close()
asyncio.run(test())
"
```

---

## Типовые проблемы

### "BrowserContext.new_page: Target page, context or browser has been closed"

**Причина:** Instagram разорвал соединение или краш Playwright.

**Решение:** проверь сессию (check-session.py). Если жива — реактивируй упавшие. Если протухла — перелогин.

### Аккаунт без постов (no posts в скрипте)

Причина: смена юзернейма, удаление, блокировка Instagram. Удалить из мониторинга (`/remove`).

### Кнопки Mini App не работают / дубли

См. раздел «Логика вкладок» выше. Основная причина — путаница между `is_favorite` и `status`.

---

## Скрипты навыка

- `scripts/check-session.py` — проверка Instagram сессии
- `scripts/list-accounts.py` — список аккаунтов из SQLite
- `scripts/reactivate-accounts.py` — реактивация упавших
- `scripts/check-stuck-renderers.sh` — поиск зависших Chromium рендереров (диагностика залипания монитора)

## Ссылки

- `references/diagnose-no-notifications.md` — полный гайд по диагностике уведомлений
- `references/playwright-timeout-hardening.md` — паттерн asyncio.wait_for для Playwright (таймауты, защита от зависания страниц)

---

## Структура проекта

```
src/insta_flat_parser/
├── __main__.py     # Точка входа
├── bot.py          # Telegram bot (aiogram)
├── cli.py          # CLI entry point (click)
├── config.py       # Settings из .env
├── extractor.py    # Извлечение контактов (regex, OCR, Whisper)
├── leads.py        # LeadStorage
├── monitor.py      # Оркестратор мониторинга
├── reminder.py     # Напоминания
├── scraper.py      # Playwright Instagram scraper
├── storage.py      # SQLite хранение
└── web_app.py      # Web App (Flask)
```
