# Проверочные SQL-запросы и схема БД (прод vdska, lead-platform)

Проверки выполняются через:
`~/.hermes/scripts/dk.sh docker compose exec -T db psql -U booking -d booking -c "..."`

## Таблицы (public)
- `tenants`, `users`, `leads`, `knowledge_base`, `services`, `specialists`, `appointments`, `payments`, `lead_events`, `retarget_sent`
- `client_invites` (с 09.09, создаётся create_all): id, client_user_id→users, token_hash (UNIQUE), token_raw, created_at, expires_at, used_at, tenant_id — проверка активной ссылки: `SELECT * FROM client_invites WHERE used_at IS NULL AND expires_at > now();`
- ⚠️ Enum `appointment_status` хранит ЗНАЧЕНИЯ (они русские): `новая/подтверждена/отменена/перенесена/не_пришёл/выполнена`. Строка `'new'` → InvalidTextRepresentation (в тестах и SQL). В Python — `AppointmentStatus.NEW` из src.domain.booking.status_machine.
- **База знаний = `knowledge_base`** (колонки question, answer, embedding, tenant_id) — НЕ `ai_knowledge_items`, НЕ `knowledge_base_items` (ошибка 01.09).
- Связь KB ↔ тенант: `JOIN tenants t ON t.id = k.tenant_id`

## Enum user_role: в psql сравнивать по ИМЕНАМ членов, не по значениям
SQLAlchemy `Enum` хранит имена членов (`SUPER_ADMIN`), а не значения (`"super_admin"`):
- `WHERE u.role='super_admin'` → `ERROR: invalid input value for enum user_role`
- `WHERE u.role='SUPER_ADMIN'` → работает

Ранги ролей (ensure_super_admin): CLIENT(0) < SPECIALIST(1) < ADMIN(2) < OWNER(3) < SUPER_ADMIN(4).

## Частые проверки

Супер-админ создан и привязан к первому тенанту (US-01):
```sql
SELECT u.id, u.telegram_id, u.name, u.role, u.tenant_id, t.slug
FROM users u LEFT JOIN tenants t ON t.id=u.tenant_id
WHERE u.telegram_id=<SUPER_ADMIN_TELEGRAM_ID>;
```

Уникальность токенов ботов (дубликат → MultipleResultsFound, см. питфолл):
```sql
SELECT id, slug, client_bot_token IS NOT NULL AS client,
       worker_bot_token IS NOT NULL AS worker
FROM tenants ORDER BY id;
```

KB тенанта (адресный пункт после фикса 01.09):
```sql
SELECT k.id, k.question, k.answer
FROM knowledge_base k JOIN tenants t ON t.id=k.tenant_id
WHERE t.slug='city-dental' ORDER BY k.id;
```

Контент тенанта (пустой platform-тенант = демо-бот без услуг):
```sql
SELECT t.slug,
       (SELECT count(*) FROM services s WHERE s.tenant_id=t.id) AS services,
       (SELECT count(*) FROM specialists sp WHERE sp.tenant_id=t.id) AS specialists,
       t.ai_template IS NOT NULL AS has_ai_template
FROM tenants t ORDER BY t.id;
```

Адрес визитки (site JSONB → contacts.address; null = адреса нет):
```sql
SELECT t.slug, jsonb_path_query_array(t.site, '$.contacts') AS contacts
FROM tenants t ORDER BY t.id;
```

## Дубликат токенов → MultipleResultsFound (симптом)
`get_by_bot_token` (tenant_repo.py) ищет `WHERE client_bot_token = :t OR worker_bot_token = :t` БЕЗ ORDER BY; два тенанта с одним токеном → `scalar_one_or_none()` бросает `MultipleResultsFound` на ЛЮБОМ сообщении бота (супер-админ /start, клиентский бот, callback'и). Deep link `lead_<id>` тенант НЕ резолвит — работает даже при дубликате (поэтому воронка «Написать боту» могла жить, а админка — падать).

Разделение (фикс 01.09): `platform` = worker-токен, `rashid-dental` = client-токен. Закреплено в сидах: seed_platform ставит только worker, seed_pilot — только client.

## Сиды лежат в образе app
`scripts/seed_platform.py`, `scripts/seed_pilot.py` копируются в образ app при сборке. После правки сидов:
1. `dk.sh docker compose build app` (background + notify_on_complete)
2. `dk.sh docker compose up -d app`
3. `dk.sh docker compose run --rm --no-deps app python scripts/seed_platform.py`
4. `dk.sh docker compose run --rm --no-deps app python scripts/seed_pilot.py`
Оба сида идемпотентны (upsert по slug); повторный seed_pilot обновляет KB-ответы (в т.ч. адресный пункт из site.contacts.address).

## Колонки таблицы `users` (проверено 08.09)
`users`: id, telegram_id, name, phone, roles, role, opened_bot, is_active,
client_stage_id, client_owner_id, amount, source, tenant_id, created_at, updated_at.
⚠️ Колонки `username`/`tg_username` у users **нет** (username есть у `leads`) —
`SELECT username FROM users` → `column "username" does not exist`. Сортировка проверки юзеров:
`SELECT id, tenant_id, telegram_id, name, role FROM users ORDER BY id;`
После db_reset + сидов (08.09): id=1 Андрей OWNER city-dental (tg 7519756578), id=2
SUPER_ADMIN platform (tg 350262645), владельцы демо-вертикалей — telegram_id 9000000xx,
демо-клиенты от seed_demo_crm — 910000xxx (вымышленные, напоминаний на них нет).

## Удаление сущностей (09.09, верифицированный рецепт — случай «Momin Ahmed»)

### FK на users (pg_constraint, confdeltype)
- `a` NO ACTION — блокируют DELETE, чистить руками: `appointments.client_user_id`, `conversations.client_user_id`, `client_events.client_user_id`, `retarget_sent.client_user_id`, `messages.sender_user_id`, `internal_notes.staff_user_id`, `ai_conversations.client_id`, `work_plans.client_id`
- `c` CASCADE — уходят сами: `sessions.user_id`, `staff_notifications.user_id`, `specialists.user_id`, `client_invites.client_user_id`
- `n` SET NULL — обнуляются сами: `leads.client_user_id`, `users.client_owner_id`
Проверить свои: `SELECT conrelid::regclass AS tbl, confdeltype FROM pg_constraint WHERE confrelid='users'::regclass AND contype='f';`

### Поиск всех строк человека
```sql
SELECT id, tenant_id, name, role, telegram_id, is_archived
FROM users WHERE name ILIKE '%<подстрока>%' OR telegram_id=<tg_id> ORDER BY id;
```
Один tg-аккаунт = несколько строк: CLIENT в каждом тенанте, где его создали,
+ OWNER тенанта, собранного через викторину (company_factory). Роли в SQL — ВЕРХНИМ регистром.

### Удаление CLIENT c историей (каскад = зеркало ClientsTableService.delete_client)
```sql
BEGIN;
DELETE FROM appointment_events WHERE appointment_id IN (SELECT id FROM appointments WHERE client_user_id IN (:ids));
DELETE FROM reminders           WHERE appointment_id IN (SELECT id FROM appointments WHERE client_user_id IN (:ids));
DELETE FROM specialist_notifications WHERE appointment_id IN (SELECT id FROM appointments WHERE client_user_id IN (:ids));
DELETE FROM appointments  WHERE client_user_id IN (:ids);
DELETE FROM client_events WHERE client_user_id IN (:ids);
DELETE FROM retarget_sent WHERE client_user_id IN (:ids);
DELETE FROM users WHERE id IN (:ids);
COMMIT;
```

### Удаление БИЗНЕСА ЦЕЛИКОМ (тенанта; UI для этого не существует — см. SKILL.md)
```sql
BEGIN;
-- порядок важен: сначала убрать NO ACTION / SET NULL-держателей, ПОТОМ tenants
UPDATE leads SET client_user_id = NULL WHERE tenant_id = :t;   -- НЕ DELETE leads (падает, катит всю транзакцию)
DELETE FROM chat_bot_bindings WHERE tenant_id = :t;            -- единственный NO ACTION на tenants
DELETE FROM tenants WHERE id = :t;                             -- 23 остальных FK — ON DELETE CASCADE
COMMIT;
```
⚠️ `psql -c "BEGIN; ... COMMIT;"` = одна транзакция: ЛЮБАЯ ошибка откатывает всё, повторять надо весь блок с начала (проверено 09.09 — первый прогон с `DELETE FROM leads` откатился целиком).

### Проверка после удаления
```sql
SELECT count(*) FROM appointments a LEFT JOIN users u ON u.id=a.client_user_id WHERE u.id IS NULL; -- орфаны записей = 0
SELECT id, slug FROM tenants ORDER BY id;
```
Не трогать при зачистке одного человека: лид-строки platform-тенанта с похожими именами тестов (`Mamin` и т.п.) и учётки сидов (9000000xx/910000xxx).
