# Прогон тест-кейсов 03 «анкета → оплата → онбординг» живьём (рецепт 14.09)

Стандарт Василия: «процесс должен быть настолько чистым, что вопросов не
возникает» — каждый шаг, требующий от пользователя знать внутреннее состояние
или тайминг («нажми /start ЕЩЁ РАЗ», «повтори тест»), — это баг, заводить issue.

## Браузер для анкеты (browser_exec / browser-harness)
Если демон даёт `chrome-not-running`: поднять playwright-chromium headless и
указать harness'у CDP:
```bash
CHROME=$(ls ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome | head -1)
$CHROME --headless=new --remote-debugging-port=9222 --user-data-dir=/tmp/bu-chrome \
  --no-sandbox --disable-gpu about:blank &   # background
hermes config set browser.cdp_url http://127.0.0.1:9222   # ранг 1 резолва BU_CDP в browser_use_cli
```
(после смены browser.cdp_url демон пересоздаётся и подключается к этому CDP)
- React-плитки (сфера/тариф): синтетический `dispatchEvent(MouseEvent)` часто НЕ
  засчитывается — кликать `click_at_xy` по координатам центра элемента.
- Headless-вьюпорт 780×437: кнопка под фолдом → сначала `scrollIntoView({block:'center'})`,
  потом читать `getBoundingClientRect` и кликать.
- Поля React-форм: нативный setter + `dispatchEvent(new Event('input',{bubbles:true}))`.
- Helper-функции (click_text/set_input/state) писать в `$BH_AGENT_WORKSPACE/quiz_helpers.py`
  (workspace persist между вызовами) и `exec(open(...).read())` в начале каждого шага.
- Ссылку deep link финала читать из DOM (`a[href*='t.me/...start=lead_']`) — это
  единственный шаг, который нельзя симулировать (чужой Telegram-аккаунт).

## Прод-compose vs доки тест-кейсов
`docs/test-cases/*` написаны под локальный tmux-стек (`postgres_db`, :5173/5174).
На проде vdska: веб тот же https://24ghost.online (caddy), но БД — через
`dk.sh docker compose exec -T db psql -U booking -d booking`. Очистка стенда:
`POSTGRES_HOST=lead-platform-db-1 bash scripts/db_wipe_demo.sh --yes` (скрипт
берёт имя контейнера из env; запускать через tmp-скрипт, не инлайн).
⚠️ SQL с кавычками/JSONB через dk.sh ЛОМАЕТСЯ (`$` и `"` съедаются —
`invalid input syntax for type json`): писать запрос в `.sql`-файл, `docker cp`
в контейнер db, `psql -f /tmp/x.sql`.

## Гонка owner_chat_id — главная засада честного теста (шаг 4 из 6)
Тест шлёт sendMessage в `owner_chat_id` из ЕГО базы (`lp_demo_<компания>_<id>`);
id пишет только /start в рабочем боте ПОСЛЕ того, как поллер этого токена
поднялся (поллеры стартуют ≤30с после сохранения токенов — видно в
`compose logs bots` → `Run polling for bot @...`). /start, нажатый РАНЬШЕ,
съедается СТАРЫМ поллером (прошлый прогон на тех же токенах) — тест показывает
❌ у обоих, хотя «в телеге всё давно нажато». Диагностика:
`psql -d lp_demo_... -tAc "SELECT settings->>'owner_chat_id' FROM tenants"` (пусто)
+ таймстемпы поллеров. Обход для прогона (легитимный — id известен из
`chat_bot_bindings` главной БД):
```sql
UPDATE tenants SET settings = COALESCE(settings,'{}'::jsonb)
  || '{"owner_chat_id": <tg_id>, "owner_name": "..."}'::jsonb WHERE slug='<slug>';
```
после этого «🔁 Повторить тест» → оба ✅ без участия пользователя.
Корректный фикс UX — issue #146 (диплинк bind_ + авто-детект при первом
входящем апдейте). Статусы: `GET /api/public/quiz-lead/<id>/status` —
`registered` = `lead.telegram_id is not None` (привязка ТОЛЬКО живым /start по
`?start=lead_<id>`, не симулируется).

## Находки прогона 14.09 → GitHub issues #145–#150
- #145(P1) скидка −30% витринная: экран $27, в payments полные 490k UZS
  (`PLAN_AMOUNTS` quiz.py:39 + `quiz_discount` не входят в amount).
- #146(P1) гонка /start честного теста (выше).
- #147(P2) валидация токена только по длине ≥12 — фейк проходит шаги 2–3,
  всплывает только на проверке доставки.
- #148(P2) лейбл «E-mail» залип в шапке на всех финальных экранах (stepLabel QuizPage.tsx).
- #149(P2) «клиентский бот» назван «рабочим» в тексте теста + двойная нумерация
  (внутри «Шаг 5→18 из 22», финал «1 из 6»).
- #150(P2) `quiz_step_events` без `lead_id` (колонки: id, session_id, step, created_at).
Quick-ветка «Оплатить сейчас» прыгает шаг 5→18 (тариф); оплата — provider TEST.

## Локальные pytest (если гонять на vdska)
`.venv` без dev-зависимостей → `uv sync --extra dev` (cryptography, pytest).
Тестовая `booking_test` на host (контейнер test-pg :5432) может отставать от
схемы (`UndefinedColumnError`) — сбросить RESET_TEST_DB=0 (conftest
пересоздаёт схему).
