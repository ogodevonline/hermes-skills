# Запись + предоплата — срез 10.09 (вынесено из SKILL.md 14.09)

Исторический срез: флоу «кнопка Записаться → услуга/время → предоплата →
уведомление+напоминание» и мини-апп веб-записи.

## Продуктовые решения (10.09, чат с Василием)
- **Картинка = ОДНА, привязана к услуге.** Колонка `services.photo_url` в модели ЕСТЬ, API отдаёт её
  (`site_card_service`, `interface/api/site.py`), но `web/src/site/sections/Services.tsx` не рендерит с 06.09
  (вердикт «визитка, не надо дохуя картинок»). Для показа достаточно вернуть фото в карточку услуги.
- **Предоплата в MVP фейковая**: «переведи на карту <номер>» + кнопка «Я оплатил», запись со статусом
  «ждёт предоплату», админ подтверждает руками. Платёжный шлюз (Payme/Click) — позже; абстракция
  `src/domain/payments/provider.py` + провайдеры уже есть, для клиентов БИЗНЕСА платежей нет вообще
  (есть только pay-test для подписки платформы).
- **Викторина из 3 вопросов для КЛИЕНТОВ — отвергнута**: «долго и сложно». Флоу = услуга + время, стандартно.

## Реализованный мини-апп веб-записи (10.09, НЕ бот-флоу)
Поправка направления от Василия: «мини апп это такая же ui страница... react роутер ведь отдаст».
⚠️ На 10.09 правки были НЕ закоммичены (срез в рабочем дереве main; актуальность — сверять в git).
Что сделано (tsc -b зелёный, tests/bot/test_handlers_session.py 3 passed):
- БЭК: `src/interface/api/public/booking.py` + `booking_schemas.py` — `/api/public/booking/<slug>/{config,slots,appointments,appointments/{id}/deposit}`;
  initData валидится токенами тенанта из URL + фолбэк `settings.bot_token_client` (общий демо-бот),
  тенант — ЯВНО из slug (deps.get_current_tenant тут неверен), карточка CLIENT создаётся по образцу ensure_client;
  путь `/api/public/*` CSRF-middleware пропускает. Колонки `appointments.deposit_percent/amount/paid_at/method`
  + идемпотентные ALTER в init_db; настройка `tenant.settings.deposit_percent` (0–100) через SCALAR_JSON_FIELDS
  SettingsService; `deposit_config()` в `src/domain/booking/settings.py`. Фото услуги —
  `POST /api/admin/services/{id}/photo` → uploads/services/ → /media (mount /media существует).
- ФРОНТ: `web/src/booking/{api.ts,BookPage.tsx}` — React-роут `/book/:slug` в App.tsx (рядом с /s/:slug,
  вне AuthProvider/shell), запросы НАПРЯМУЮ fetch с заголовком X-Telegram-Init-Data (мимо api.ts —
  тот cookie-центричен); wall-clock слоты показывать СТРОКОЙ (slice ISO), не `new Date()` — TZ-сдвиг.
- БОТ: `main_menu_kb` клиентского меню — «Услуги», «Записаться ещё раз», «Мои планы» УБРАНЫ;
  «📅 Записаться» = aiogram `WebAppInfo(url=f"{SITE_BASE_URL}/book/{slug}")`.

## Чек-лист продолжения (актуальный на 10.09)
① кнопка загрузки фото в `web/src/components/settings/ServiceDialog.tsx`
(`useServices().uploadPhoto` уже готов); ② коммит+push в main; ③ деплой (туннель-чек → compose build →
up -d --force-recreate app bots); ④ на демо-тенанте выставить `deposit_percent` (PUT /api/admin/settings)
и прокликать флоу на телефоне; ⑤ `kosy-9` без `client_bot_username` — для демо на Косах проставить или
смотреть через city-dental (4 услуги, специалист, бот на месте).

## Прочие заметки того же среза
- ⚠️ **Проверка маршрутов FastAPI в новом рантайме: `app.routes` отдаёт `_IncludedRouter`-обёртки** без
  `.path` — include-роуты там не видны (ложное «роутер не зарегистрирован»). Проверять
  `app.openapi()['paths']` или `router.routes` самого роутера.
- ⚠️ **«Хочу увидеть как это работает, не хочу долго сидеть» = предлагать минимальную достройку**
  уже работающего пути, а не новую поверхность. Формат ответа: что уже есть (1 блок) → чего не хватает
  (2 буллета) → оценка времени → ОДИН вопрос «начинаю?».
- ⚠️ **10.09: явная команда «worktree не делай»** — работу по lead-platform в чатовом режиме вести прямо
  в `~/projects/lead-platform` (main), без worktree и без Kanban-воркеров. Worktree — только для Kanban.
- ⚠️ **10.09: «мини-апп» у Василия = Telegram WebApp (веб-страница с initData), а НЕ бот-UI** — когда он
  говорит про мини-апп/запись, НЕ предлагать «быстрее доделаю в боте». Реальная цена веб-поверхности
  оказалась меньше дня — не пугать оценкой «день вёрстки» и не уводить в бот.
- Живой тенант «Косы» = `kosy-9` (id=10) — кандидат для ручной проверки флоу на телефоне.
