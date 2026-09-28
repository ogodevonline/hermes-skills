# Передача бизнеса (боты + тенант) новому владельцу

Случай Lima Braids, 27.09.2026. Покрывает: где лежит правда о владельце, ручной
переезд через psql, BotFather-трансфер, и штатную реализацию #305/#306.

## Где что лежит
- Control-БД `booking` (контейнер `lead-platform-db-1`, юзер `booking`):
  `tenant_endpoints` — реестр slug → dsn, worker/client_bot_username,
  is_ephemeral/is_demo. Источник истины «чей бот поллится».
- База бизнеса `lp_demo_<slug>` (single-tenant): `tenants`
  (`worker/client_bot_token`, `settings` JSONB: `owner_chat_id`, `owner_name`,
  `bot_texts.greeting`, `lang`, `hours`), `users` (OWNER),
  `chat_bot_bindings` (chat_id → tenant_id).
- Фактический поллинг: `dk.sh docker logs lead-platform-bots-1 | grep -E 'Run polling|поднят бот'`
  → «registry_<slug>_worker/_client».
- ⚠️ `psql -c "\dt"` / `"\d table"` через `dk.sh docker exec` НЕ проходят —
  мета-команда ломается в синтаксис SQL. Схлопывай в
  `information_schema.columns` / `pg_database` через `-c`/`-tAc`.
- `owner_chat_id` хранится ЧИСЛОМ: проверить
  `jsonb_typeof(settings->'owner_chat_id')`; `jsonb_set(...,'{owner_chat_id}','<id>')`
  — без кавычек вокруг значения.

## Ручная смена владельца (быстрый путь, пока нет UI)
```sql
-- база lp_demo_<slug>:
UPDATE users SET telegram_id=<NEW_ID> WHERE id=1;                        -- OWNER-юзер
UPDATE tenants SET settings=jsonb_set(settings,'{owner_chat_id}','<NEW_ID>') WHERE id=1;
DELETE FROM chat_bot_bindings WHERE chat_id=<OLD_TEST_CHAT>;             -- отвязать чат Василия
```
Хвосты старого id искать в: `users`, `leads`, `login_tokens`, `demo_visitors`,
`blocked_persons`, `chat_bot_bindings` (одним SELECT count по каждой).

## BotFather-трансфер самих ботов
1. Получатель ОБЯЗАНА сначала нажать /start обоим ботам — BotFather требует
   предыдущее взаимодействие; после /start чат сам привяжется (owner_chat_id).
2. @BotFather: `/mybots` → бот → **Transfer Ownership** → Choose recipient →
   @username → «Yes, I'm sure» → 2FA-пароль. Для обоих ботов.
3. **Токен при трансфере НЕ меняется** (подтверждено докой+кейсом) — поллинг
   продолжает работать, БД/деплой трогать не нужно.
4. Предупредить нового владельца: НЕ жать Revoke Token — это убивает Bot API.
   Если ревокнул — новый токен → `UPDATE tenants SET worker_bot_token/client_bot_token=...`
   в базе бизнеса + реестр, rescan подхватит ≤30с.
5. Неотвратимо назад: ответный трансфер — только от нового владельца.

## Штатная реализация (27.09, issues #305/#306 → GitHub, main)
- **#306 transfer-owner**: `POST /api/admin/team/{member_id}/transfer-owner`
  → `src/application/admin/owner_transfer.py` (отдельный модуль: team_service.py
  уже 161 строк — правило ≤150, не плодить). Прежний OWNER → ADMIN (staff-роли
  сохраняются, assign_roles через ROLE_RANK-зеркало), новый → OWNER+staff,
  settings `owner_chat_id/owner_name` переезжают, sync_specialist_card на обе
  стороны. `require_roles("owner")` ПУСКАЕТ super_admin — контракт deps.py.
  Отказы ValueError→400: себе / неактивному / клиенту вне команды / нет owner-строки.
  UI: кнопка «Передать владение» в TeamMemberEditDialog (пропсы canTransfer/onTransfer)
  + ConfirmDialog; строки каталога team.ts (`transferOwner/transferConfirmTitle/transferConfirmText`, RU+UZ).
- **#305 «Общие» редактируемы**: приветствие клиента =
  `tenants.settings.bot_texts.greeting` (`home_screen.custom_greeting` бьёт
  каталог); backend PUT /api/admin/settings принимал его ВСЕГДА — не хватало
  поля в GeneralTab. Имя бизнеса: `TenantSettingsIn.name` (min_length=1) +
  "name" в COLUMN_FIELDS → колонка `tenants.name`.
- Тесты на vdska (хостовый `test-pg`, booking_test): `cd ~/projects/lead-platform &&
  PYTHONPATH=. .venv/bin/python -m pytest tests/api/test_team_transfer_owner.py
  tests/api/test_settings_name_greeting.py -q` — 8 passed.
