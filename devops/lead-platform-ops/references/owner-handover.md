# Передача бизнеса клиенту-владельцу (кейс Lima Braids, 27.09.2026)

Плейбук: готовый тенант лид-платформы передается реальному владельцу (его Telegram-аккаунт + его боты).

## Состав тенанта (проверка живьём)
- Реестр (control-база `booking`): `SELECT id, slug, dsn, is_ephemeral, worker_bot_username, client_bot_username FROM tenant_endpoints;` — строка с `is_ephemeral=f` = боевая, поллер подхватывает rescan'ом ≤30с.
- База бизнеса: `psql -U booking -d <dsn из реестра>` (обычно `lp_demo_<slug с подчёркиваниями>`); `SELECT ... FROM tenants` — токены/`settings->>'owner_chat_id'`; `SELECT id, telegram_id, name, role FROM users`.
- Кейс: `lima-braids-6` / база `lp_demo_lima_braids_6` / @lima_braids_bot (клиентский) + @lima_braids_notify_bot (уведомления/владелец).

## Ручная смена владельца в БД (до #306 / когда нет доступа к UI)
Три места (проверено на Лиме, идемпотентно):
```sql
UPDATE users SET telegram_id=<НОВЫЙ_ID> WHERE id=<OWNER-строка>;   -- роль OWNER
UPDATE tenants SET settings=jsonb_set(settings,'{owner_chat_id}','<НОВЫЙ_ID>') WHERE id=1;
DELETE FROM chat_bot_bindings WHERE chat_id=<старый тестовый чат>;
```
Хвосты проверить: `leads/login_tokens/demo_visitors/blocked_persons.telegram_id` (в Lima-кейсе — пусто).

## BotFather-трансфер (внешний шаг, кодом НЕ делается)
Источник: core.telegram.org/bots/features (раздел Transfer ownership):
- `/mybots` → бот → **Transfer Ownership** → @username получателя → подтверждение (2FA-пароль; если 2FA включён недавно — ждёт 7 дней).
- **Получатель обязан заранее нажать /start в обоих ботах** — «you can only transfer a bot to users who have interacted with it at least once».
- **Токен при трансфере НЕ меняется** (подтверждено: github jlucus/tg-bot-disclosure) → поллинг на проде продолжает работать, в БД/реестре трогать нечего, пересборки не нужно.
- Трансфер необратим; новый владелец может Revoke Token — предупредить клиента явно (Revoke ломает поллер; лечение: новый токен в `tenants.worker/client_bot_token` + refresh в реестре, rescan ≤30с).

## #306 transfer-owner (коммит c0989d3, 27.09) — штатный путь
- `POST /api/admin/team/{member_id}/transfer-owner`, гейт `require_roles("owner")` (суперадмин проходит контракт).
- Прежний OWNER → ADMIN (staff-роли сохраняются), новый → OWNER + свои staff-роли; `settings.owner_chat_id/owner_name` переезжают; `sync_specialist_card` за обеими сторонами.
- Отказы 400: себе / неактивному / CLIENT вне команды / чужой тенант; 403 — вызывающий admin.
- Код: `src/application/admin/owner_transfer.py` (вынесен из team_service — лимит 150 строк); UI: Настройки → Команда → модалка сотрудника → «Передать владение» (ConfirmDialog, виден owner/super_admin), после — `refresh()` сессии (своя роль сменилась).
- Тесты: `tests/api/test_team_transfer_owner.py` (5), запуск `PYTHONPATH=. .venv/bin/python -m pytest tests/api/test_team_transfer_owner.py -q`.

## #305 поля в Настройки → Общие (тот же коммит)
- `name` (колонка tenants.name) + `bot_texts.greeting` (кастом бьёт каталог — `home_screen.custom_greeting`). PUT `/api/admin/settings` partial: greeting не затирает name и наоборот (тест `tests/api/test_settings_name_greeting.py`).

## Сообщение клиенту (пересылаемый шаблон)
1) открой оба бота и нажми /start (нужно для передачи), 2) придёт уведомление от @BotFather о трансфере, 3) НЕ жать Revoke Token в настройках бота, 4) ссылка админки `https://24ghost.online/web/` (вход через Telegram, роль OWNER подтянется).

⚠️ Василий, давая tg id/username получателя, ожидает немедленного выполнения правок (не переспрашивать: «Ну И» = требование действовать). Правки в прод-БД — approval-ход: предупредить и отправить сразу.

## 27.09 вечер: фикс #305-UI + уроки (коммит 3f7adf6)
- Жалоба «в „Общих“ нельзя сохранить»: кнопка Сохранить в GeneralTab шла ПОСЛЕ блока
  «Опасная зона» и на мобилке уезжала за экран — выглядела мёртвой. Фикс: sticky-строка
  (`position:sticky; bottom:10`) со статусами «Сохранение… / ✓ Сохранено / красный текст
  ошибки»; markDirty() при правке любого поля. **Правило новых вкладок CRM-админки:
  save-кнопка залипающая, ошибки НЕ глотать** — молчаливый 401 (рестарт app чистит
  cookie-сессии: GET ещё из кэша 200, PUT уже 401) ощущается как «кнопка не нажимается».
- Примеры подсказок в i18n-каталогах НЕ должны содержать имена реальных тенантов —
  «Lima Braids» попало в примеры name/greeting и раздражает; писать нейтральные
  («Ромашка», generic-приветствие).
- Диагностика «не сохраняется» — ОДНА команда, не расследование:
  `dk.sh docker logs lead-platform-app-1 --since 30m | grep -E 'PUT /api/admin'` — видно
  200/401/403 и таймлайн. Проверки initData (gen_initdata.py) требуют НАСТОЯЩИЙ токен из
  базы тенанта (`psql -tAc "SELECT worker_bot_token FROM tenants"` в lp_demo_*); токен из
  config/tenants/*.toml или наугад даёт ложный 401 и сажает в петлю.
- ⚠️ Порядок работы (Василий оборвал форензику матерщиной): когда пользователь КОНКРЕТНО
  указал дефект UI и просит починить — чинить СРАЗУ; углублённое воспроизведение curl'ом и
 чтение логов ДО фикса запрещено. Копать — только если сам фикс не объясняет симптом.

 ## 27.09: регрессия онбординга «пропала кнопка ?» (коммит 5f24a74)
 - Симптом: «после твоих правок перестало работать обучение» — кнопки «?» в шапке и
 «Пройти обучение ещё раз» в профиле пропали, по кнопке тур не открывался.
 - **Виноват НЕ мой деплой**: `git log --oneline e776233..HEAD -- <путь фичи>` пустой.
 Корень — коммит `59901c0` (24.09, чужой): удалили Demo-тур, а осиротевшие гейты
 `isDemo` остались (`OnboardingProvider(enabled=!isDemo)`, `{!isDemo && <OnboardingHelpButton/>}`)
 и гасили обучение во всех демо/эфемер-стендах. **Питфолл: при удалении фичи грепать
 её флаги/гейты — осиротевший гейт = невидимый регресс, всплывающий через дни на
 соседнем деплое.** Урок роутинга обвинений: перед ответом «это не я» — git log по
 файлам фичи между деплоями (проверяется одной командой).
 - Фикс: гейты `isDemo` сняты (SetupChecklist самодостаточен); `OnboardingRepeatButton`
 рендерится и на мобилке (раньше скрывался по #281 — Васе нужнее) и стоит САМЫМ
 ВЕРХОМ профиля с отступом (явная просьба — не прятать и не опускать). Проверка:
 tsc -b + vitest onboarding/profile/settings (33/33).
 - ⚠️ SKILL.md lead-platform-ops УПЁРСЯ в лимит 100k символов — новые записи только
 в references/*, либо сначала сокращать SKILL.md.
