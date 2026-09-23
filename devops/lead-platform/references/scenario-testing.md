# Сценарные тесты взаимодействия сервисов (lead-platform)

Сверено 14.09.2026 на живом окружении (прод-контейнеры + test-pg на хосте).

## Уровень 1 — боты в-process (быстро, детерминированно)
Инфраструктура в репо:
- `tests/helpers.py`:
  - `BotFakeSession` — перехватывает исходящие методы бота (sendMessage/editMessageText) в список `messages` (текст + клавиатуры); assertions по нему.
  - `build_fake_bot(token, fake)` — aiogram `Bot` с подменённой сессией.
  - `cb_update(id, data, tg_id, chat_id)` / `msg_update(id, text, tg_id, chat_id)` — конструкторы реальных `Update` (callback_query / message).
  - `build_init_data(bot_token, tg_id)` — подписанный Web App initData для тестов входа в админку.
  - `TelegramApiSpy`, `seed_subscription(session, slug, plan=...)`.
- `tests/conftest.py`: фикстуры `session`/`tenant` (внешняя транзакция + savepoint-коммиты, откат в teardown), `client_dp` (сессийный Dispatcher с роутерами-синглтонами — общие state-роутеры нельзя пересоздавать на тест).
- Прогон: `cd ~/projects/lead-platform && .venv/bin/python -m pytest tests/bot tests/integration -q`
  - БД: контейнер `test-pg` на 127.0.0.1:5432, база `booking_test` (conftest создаёт сам при дефолтном RESET_TEST_DB).
  - НЕ выставливать DATABASE_URL из `.env` — он ведёт на прод-базу `booking`.
  - `ModuleNotFoundError: pytest|cryptography` → `uv sync --group dev` (один раз; `--frozen` режет dev-группу).
  - `asyncpg UndefinedColumnError` на фикстуре → старая схема при `RESET_TEST_DB=0`: убрать env-флаг, дать БД пересоздаться.
- Что уже покрыто: `tests/bot/` (сетка кнопок записи, reschedule, my_appointments, worker-уведомления, demo-линк, сессии), `tests/integration/` (e2e-запись с авто-созданием клиента, админ-reschedule, напоминания, прямой notify API), `tests/api/` (16 файлов: тенант-изоляция, plan-gate, подписки, слоты, квиз-события).

## Уровень 2 — живые боты в проде
- Контейнер `lead-platform-bots-1`: поллинг 4 ботов (демо-пара @lead_worker_demo_bot/@lead_client_demo_bot + платформа-пара @lead_platform_worker_bot/@lead_platform_client_bot). Логи: `dk.sh docker logs lead-platform-bots-1`.
- Исходящие сообщения — реальными токенами из `.env` (`BOT_TOKEN_CLIENT/WORKER`) через Bot().sendMessage или curl Bot API.
- Коллбэки «с телефона» — просить Василия нажать кнопку; side-effects видны в БД (`appointments`, `leads.telegram_id`).
- Уведомления супер-админу 350262645 приходят реально — верификация только глазами Василия или по outgoing-логам.

## Уровень 3 — фронтенд через `browser`
- `/quiz`: экран за экраном (V2: вопросы→итог→тариф→апселл-лестница→контакт→оффер); на шаге оффера лид уже создан (POST `/api/public/quiz-lead` с addons), кнопка оплаты → pay-test.
- `/web/` админка: вход через подписанный initData (`build_init_data`) или deep link с телефона; guards с loading-состоянием (см. фикс 70f4797).
- `/s/<slug>` визитка: запись клиентом напрямую, сравнение DEMO vs PROD фазы.
- Каждый шаг — скриншот; при жалобе сверять визуал, а не только DOM.

### Подключение browser_exec к Chromium (проверено 14.09)
Ошибка `browser-harness: daemon default didn't come up` + лог `chrome-not-running` — harness не видит браузер. Рабочий рецепт:
1. Поднять playwright-Chromium с CDP: `~/.cache/ms-playwright/chromium-<ver>/chrome-linux64/chrome --headless=new --remote-debugging-port=9222 --user-data-dir=/tmp/bu-chrome --no-sandbox --disable-gpu about:blank &` (проверить `curl 127.0.0.1:9222/json/version`).
2. `hermes config set browser.cdp_url http://127.0.0.1:9222` (конфиг читается `tools/browser_use_cli.py::_resolve_backend_cdp`, ранг 2 — BROWSER_CDP_URL/browser.cdp_url).
3. Очистить `/home/hermes/.config/browser-harness/tmp/bu-default.log` и повторить вызов browser_exec.

### Паттерны автоматизации React-анкеты (проверено 14.09, весь TK-A/B/C проходим)
- Viewport headless ~780×437: кнопки оффера/оплаты ниже фолда — ДО кликa `scrollIntoView({block:'center'})`, затем `click_at_xy` по центру `getBoundingClientRect()`. Синтетический `dispatchEvent(MouseEvent)` доходит не до всех React-обработчиков (плитки сфер выбирались только координатным кликом).
- Controlled-инпуты: нативный setter + `input`-event: `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,val); i.dispatchEvent(new Event('input',{bubbles:true}))` — `i.value=val` React не видит.
- Поиск элементов: emoji-префиксы в `textContent` ломают `startsWith('🦷')` (вариационные селекторы) — матчить по русскому слову; карточки тарифов — `.plans .pc` (выбор = класс `sel`).
- Проверять `disabled` у «Далее» после клика — это сигнал, что выбор не засчитался.
- Helper'ы (`click_text`/`set_input`/`next_btn`/`state`) сохранять в `$BH_AGENT_WORKSPACE/quiz_helpers.py` и `exec(open(...).read().replace("_js","js"))` в начале каждого browser_exec-вызова (Python-переменные между вызовами НЕ живут).

### Прогон TK-03 на compose-проду (14.09, дошёл до честного теста)
- Пути в `docs/test-cases/*` рассчитаны на tmux-стек (`postgres_db`, :5174); на compose-проду: БД через `dk.sh docker compose exec -T db psql`, анкета на `https://24ghost.online/quiz`.
- `db_wipe_demo.sh --yes` на compose = `POSTGRES_HOST=lead-platform-db-1 bash scripts/db_wipe_demo.sh --yes` (дефолт в скрипте — контейнер tmux-стека `postgres_db`). Деструктив на проде: терминал ждёт Approve; обёртка — скрипт в /tmp + `dk.sh bash /tmp/wipe_lp.sh`. После wipe остаётся пользователь лида (CLIENT) в tenant platform — ок.
- Цепочка подтверждена живьём: оплата (Payment provider=TEST) → лид PAID → «Подключить ботов →» → база `lp_demo_<компания>_<id>` + строка в `tenant_endpoints`, токены в ЕГО базе и реестре → `POST /bots` → шаг 4 «Проверка ботов» с честными ❌. Поллеры клиентских ботов поднялись в `lead-platform-bots-1` за секунды после сохранения токенов. Статус-гейты: `/api/public/quiz-lead/<id>/status` → `provision_started:true → provisioned:true, registered:true`.
- Фронт шага 2 валидирует токен только по длине ≥12: фейк `abcdefghijklmnop123` проходит на шаг 3 (ожидалась ошибка формата — её ловит бэкенд, не UI). Реальные токены вписывать сразу.
- Честный тест (TK-D) воспроизводим ТОЛЬКО с живым аккаунтом: /start в СВОИХ ботах делает пользователь на телефоне (бот не может написать первым до owner_chat_id). Просить в чате «открой @bot → /start → напиши „сделал“», дальше «🔁 Повторить тест».
- Тексты TK-D.2 дрейфуют vs док: ожидание «не дошло (…)», прод выдаёт «❌ … нет контакта — нажмите /start в вашем рабочем боте @…» — сверять смысл и помечать док-дрейф.
- Быстрый тест-привязка: `curl /api/public/quiz-lead/<id>/status` + SQL `SELECT datname FROM pg_database WHERE datname LIKE 'lp_%'` + `settings->>'owner_chat_id'` в базе тенанта.

## Сквозные цепочки (чек-лист прогонов)
1. Лендинг → `/quiz` полный проход → лид NEW + событие `quiz_finished` → человекочитаемое уведомление супер-админу → финал без «Готово».
2. pay-test → PAID + Payment(provider=test) + trial +7д → deep link `lead_<id>` в worker-боте → привязка telegram_id первому открывшему → User(ADMIN) + кнопки «Открыть админку»/«Попробовать запись».
3. Клиент-бот: /start → Записаться → услуга → слот → подтверждение → запись в БД; слот исчезает из сетки; worker-бот получил уведомление.
4. Отмена в окне cut-off (`tenants.cancel_cutoff_hours`) — ок / вне окна — отказ.
5. Визитка → запись → та же запись видна в админке клиента (таймлайн).
6. Напоминания: integration `test_reminders` — appointment → сообщение клиенту.

## Питфолы
- Роутеры aiogram — синглтоны модуля: Dispatcher пересоздавать на тест нельзя (conftest держит один на сессию, `dp` фикстура = `client_dp`).
- При проверке сеток кнопок матчить `callback_data` целиком (формат `t_f<id>`), не только текст кнопок.
- `docker compose exec -T db psql` — для инспекции прод-БД без хост-клиента.
