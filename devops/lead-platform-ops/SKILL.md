---
name: lead-platform-ops
description: Деплой/проверка lead-platform на vdska — compose, сид, туннель, US-00a.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [lead-platform, vdska, docker, deploy, us00a, воронка]
    category: devops
---

# Lead Platform Ops

⚠️ **12.09 репо перестроен (f622a41 и новее):** `web/` → **`admin-panel/`**, `web-public/` → **`landing/`**
(ветки были устаревшими — `web/dist`, `web/src/...` больше НЕ существуют; git status показывает `web/`,
`web-public/` как мусор от старого pull — игнорировать, НЕ трекать). Прод — **фикс-домен
`https://24ghost.online` через контейнер caddy** (не cloudflared-туннель): `WEBAPP_URL=https://24ghost.online/web/`,
`SITE_BASE_URL=https://24ghost.online` в .env. Ботов в поллинге 6 (с 19.09): 3 client + 3 worker — демо-пара
(@lead_worker_demo_bot/@lead_client_demo_bot) + платформа-пара (@lead_platform_worker_bot/@lead_platform_client_bot)
+ Mamin-пара (@mamin_worker_bot/@main_client_bot — имя клиента именно `main`, не `mamin`); проверять по `docker logs lead-platform-bots-1 | grep 'Run polling'`.
Миграции — **alembic** (issue #108): `src/core/db_migrate.py` — CLEAN→`upgrade head`, UNTRACKED→create_all+ad-hoc+stamp,
TRACKED→`upgrade head`; пред-чек сборки: `cd admin-panel && npx tsc -b` И `cd landing && npx tsc -b` (node на хосте есть,
`npm ci` в обеих директориях один раз;vitest 4 ловит TS6133/TS2493 так же, как Dockerfile-сборка).
⚠️ **12.09 питфолл (уронил старт app на проде):** alembic-ревизии на TRACKED-базах ОБЯЗАНЫ быть
идемпотентными: ad-hoc ALTER в init (`src/core/db_adhoc_*.py`)/add_column без `if_not_exists=True` →
`DuplicateColumnError` при старте (случай d2f6a9c4b1e7 refund_deadline; починено op.execute IF NOT EXISTS).
Симптом: app-контейнер в crash-loop с «Application startup failed», а `docker compose up` выглядит успешным.
⚠️ **12.09 демо-стенд (#115, модель Z):** гейт «оставь контакт → живое демо» = `POST /api/auth/demo`;
503 «демо-тенант не настроен (is_demo)» = нет маршрута с is_demo. Резолв: `tenant_endpoints.is_demo`
→ фолбэк `tenants.is_demo`. Ставится ФЛАГОМ `demo = true` в `config/tenants/<slug>.toml` + пересид
`dk.sh docker compose run --rm --no-deps app python scripts/seed_demo.py` (создаёт базу `lp_demo_<slug>`,
single-tenant, свои 2 бота). `config/` примонтирован в app-ro → правка тома БЕЗ пересборки образа;
`config/tenants/*.toml` на проде в .gitignore — стендовый конфиг только на диске vdska. Боты подхватывают
реестр rescan'ом 30с (пересид ботов не трогает, конфликтов нет). Визитка стенда: /s/<slug>.

Операционный workflow для проекта **lead-platform** (мультитенантная лид-платформа
онлайн-записи). Проект живёт в `~/projects/lead-platform`, прод-деплой — docker compose
на vdska. Карта шагов проверки воронки — в репо `docs/us00a-platform-funnel/`.

## Когда использовать
- «поднять проект», «проверить lead-platform», «продолжить по шагам проверки user stories»
- пересобрать/пересидить тенант, перезапустить ботов, сменить туннель
- проверить воронку US-00a или user stories по критериям приёмки

⚠️ **12.09 питфолл (Василий матом):** «ОПУСТИ лид-платформу» = ТОЛЬКО `docker compose down`
(стопить прод). НЕ pull, НЕ build, НЕ деплой, НЕ чистить диск «перед сборкой» — это не
подъём. Поднимать только отдельной командой «подними/деплой». Не расширять буквальную команду.

## Актуальный статус (03.09.2026): платформа НЕ готова к показу
- Василий остановился на US-04: «по факту записаться нельзя, админка кривая, доступы
  тенантов не продуманы» — продажи (касание Sorriso) **ОТЛОЖЕНЫ до «всё работает»**.
- Решение 03.09: **админка → ВЕБ (URL с любого устройства), НЕ Telegram Mini App**.
  Это влияет на аудит: вход/initData, WEBAPP_URL, дизайн под десктоп+мобайл.
- **Запущен полный аудит: Kanban **t_3894dc97** (architect, prio 90) — карта проблем
  P0/P1/P2: доступы/изоляция, US-04 запись, админка UX, функции US-05..US-20, безопасность.
  В задаче комментарий про эволюцию видения.
- **Аудит ЗАВЕРШЁН (03.09, t_3894dc97 done).** Итог: `AUDIT_PROBLEM_MAP.md` в worktree
  ветки t_3894dc97; отчёты: `us04_audit_report.md`, `UX_AUDIT_admin_web_ready.md`,
  `AUDIT_t_3894dc97_report.json`. Вердикт: **продукт НЕ готов к показу** — блокеры в
  базовой механике. P0-1..P0-8: вход владельца в веб-админку (нет вообще), супер-админ
  не видит компании, запись рвётся на 2-м шаге (service_specialist), подтверждение
  сломано токен-разрывом, confirm_mode не работает, оплата=заглушка + pay-test IDOR,
  dev-бэкдор, роль в localStorage без сверки. Оценка P0 целиком ~7-11 человеко-дней
  (бэк+фронт). Отдельные архитектурные задачи: веб-админка (V-04), V-01 single-tenant,
  V-03 визитка, реальная оплата Payme/Click.
- Порядок работы: аудит → чинить P0 по юзер-стори → только потом продажи. Не тянуть
  продажи раньше рабочего продукта (прямая просьба Василия).
- Живая проверка 03.09: app /health 200, /quiz 200, оба бота поллят (bots контейнер Up) —
  «жив» ≠ «рабочая»; флоу записи рвётся несмотря на здоровые контейнеры.
- **Модель суперадмина (уточнение Василия 03.09):** суперадмин — ЭТО владелец тенанта
  самой платформы, НЕ роль поверх всех тенантов; его «клиенты» = покупатели платформы
  (бизнес-тенанты). Это упрощает изоляцию: нет глобальной роли, обходящей тенанты;
  переход «владелец платформы → компания клиента» — сущность «клиент платформы».
- **Ключевая причина «записаться нельзя» (аудит t_3894dc97, B-13):** `company_factory`
  создаёт Service и Specialist, но НЕ заполняет `service_specialist` → у quiz-тенантов
  клиент получает «Услуга пока недоступна — нет активных специалистов». Фикс: автолинк
  в company_factory/create_service + бэкфилл прод-связок.
  **Полностью закрыто 09.09 (main ff65fbf, случай «Косы»):** фабрика делала специалиста
  только при team_choice=«я сам», а веб-викторина это поле НЕ отправляет вовсе → теперь
  ЛЮБОЙ owner бот-лида становится активным Specialist с привязкой всех услуг (гейт
  is_self_choice удалён); `week_schedule_from_hours` понимает компактный формат викторины
  "10-20-7" (часы + число рабочих дней от Пн; "byappt"/кривое → пустой график, старый
  "09:00-19:00" не сломан). Существующие quiz-тенанты чинятся `scripts/backfill_owner_specialist.py [slug...]`
  (в репо, идемпотентен). Регресс-тесты: tests/unit/test_quiz_company_specialist.py.
- **Источник истины по багам/доработкам: GitHub Issues** (с 09.09; backlog.md удалён, см. «Как
  фиксировать находки» ниже), commit+push в main. Не хранить находки только в
  Kanban-комментариях — Василий требует их в репо.

## Запись + предоплата (срез 10.09) и прогон сценария 03 (14.09)
- Исторический срез «запись+предоплата, мини-апп /book/:slug, чек-лист продолжения»:
  `references/booking-prepay-10-09.md`.
- **Прогон тест-кейсов 03 живьём (анкета→оплата→онбординг): браузер через CDP,
  обход dk.sh-кавычек для JSONB-SQL, гонка owner_chat_id честного теста, находки
  #145–#150 — `references/testcase-03-live-run.md`. Стандарт Василия: шаг,
  требующий от пользователя тайминга или повторного действия «вслепую», — баг.**

## ⚠️ 13.09 деплой-побочка: alembic-ревизия в pull роняет ботов на ДЕМО-базах (lp_demo_*)
Симптом после `git pull` + build + `up -d`: app жив (/health 200, все / 200), но `docker logs lead-platform-bots-1` → шквал `asyncpg.exceptions.UndefinedColumnError: column tenants.<новая_колонка> does not exist` (случай: `cancel_cutoff_hours`, коммит cdd814c #132) при `SELECT ... FROM tenants WHERE client_bot_token=...` — поллинг ботов крашится на резолве тенанта. КОРЕНЬ: lifespan app мигрирует ТОЛЬКО control-базу (`booking`); ДЕМО-подбазы `lp_demo_*` (модель Z, у каждой свой `tenants`) догоняются alembic только внутри `seed_demo`/`reseed` (`migrate_url(dsn)` в `_seed_one`). Простой деплой БЕЗ пересида оставляет демо-базы на старой ревизии → боты сыпятся, хотя прод-сайты 200 (обманчивое «всё ок»). Фикс бота = перезапуск после миграции (aiogram жрёт ошибку в middleware, но sessionmaker уже держит битый кэш маршрутов — точечно не проверял; `up -d --force-recreate bots` надёжно).
ЛЕЧЕНИЕ (не пересид — пересид = wipe+fill демо-CRM и перезапишет график): ⚠️ **14.09 — в репо ЕСТЬ штатный `scripts/migrate.py` (в образе), docker cp-одноразовка больше НЕ нужна.** Порядок: список демо-бД `dk.sh docker exec lead-platform-db-1 psql -U booking -d booking -tAc "SELECT datname FROM pg_database WHERE datname LIKE 'lp\_%'"` → для каждой: `dk.sh docker exec lead-platform-app-1 python scripts/migrate.py "postgresql+asyncpg://booking:booking@db:5432/<name>"` (идемпотентно, пишет `OK <dsn>`). Control-бД мигрирует lifespan app при старте — поднимать app ПЕРВЫМ, до ботов. ВЕРИФИКАЦИЯ релаунда: `psql -d lp_demo_demo -tAc "SELECT version_num FROM alembic_version;"` = head репо + констрейнт/колонка из ревизии фактически поменялись. После — колонка в `information_schema` есть, `grep -c UndefinedColumn` за 2м = 0. ПРОВЕРКА при любом pull: `git diff --stat <задеплоенный-sha>..HEAD -- alembic/versions/` (задеплоенный sha = HEAD ДО pull, а не фиксированный коммит) — если ревизии прилетели, мигрировать и control, и lp_demo_*.

## ⚠️ 14.09 «❌ нет контакта» на bots/test: централизованный поллинг реестра и TTL-эфемеры
- **Централизованный поллинг (#113):** контейнер `bots` поллит env-ботов платформы + КАЖДУЮ строку `tenant_endpoints` (control-БД `booking`) с непустым worker/client-токеном — `src/interface/bots/polling.py::_collect_registry_bots`, rescan ~30с (токен==платформенный env-токен пропускается, hard-off слаги пропускаются). **Источник истины «поллится ли бот» — СТРОКА РЕЕСТРА, а НЕ tenants в базе бизнеса.**
- **Симптом:** финал викторины `POST /api/public/quiz-lead/<id>/bots/test` → оба бота «нет контакта — нажмите /start» навсегда. Два корня: 1) честный — владелец не нажал /start, `chat=None` (`quiz_bots._owner_chat` читает `tenants.settings.owner_chat_id` из ЕГО базы, пишется `worker_start._remember_owner_chat` при /start); 2) **призрак-эфемер (#120/#146)** — стенд лида создан `is_ephemeral=true + expires_at`, TTL истёк → `provisioning/purge.py::delete_endpoint` снёс строку реестра → поллер молча отпустил ботов, а токены остались в tenants его базы (сирота). /start не доходит НИКУДА — тест не пройдёт никогда, каким бы правильным он ни был.
- **Диагностика (порядок):** `psql -d booking -c "SELECT id, slug, tenant_id, is_ephemeral, expires_at, worker_bot_username, client_bot_username FROM tenant_endpoints;"` (строки нет/истекла = призрак) → `docker logs lead-platform-bots-1 | grep 'Run polling for'` (фактический состав поллинга; на старте бот мог поллиться и исчезнуть после рескана = подтверждение) → `psql -d lp_demo_<x> -tAc "SELECT settings->>'owner_chat_id' FROM tenants;"` (пусто при живом реестре = честный случай 1).
- **Лечение:** перепройти финал викторины заново (стенд пересоздастся со свежей строкой реестра) ИЛИ db_reset --demo. Перед ЛЮБЫМ вайпом — выписать токены из сирота-баз (`SELECT worker_bot_token, client_bot_token FROM tenants` в lp_demo_*): после DROP DATABASE не восстановить.
- ⚠️ **db_reset.sh сносит только базы из реестра + `lp_demo_%` по маске pg_database**, но ОРФАНЫ без строк реестра переживают сброс (14.09: lp_demo_fit_1, lp_demo_spa_2 остались). После reset проверять `SELECT datname FROM pg_database WHERE datname LIKE 'lp\_%';`; чистить отдельным DROP DATABASE (approval-ход, в BLOCKED не долбить).

## Рутинный деплой «подтяни изменения и обнови прод» (эталон 19.09, ~5 tool-вызовов)
1. `git fetch && git status -sb` → behind N → `git pull --ff-only origin main` (обычно ff, конфликтов нет).
2. **Триаж по диффу** — `git diff --name-only HEAD~N..HEAD` решает, какие пред-чеки нужны:
   - нет `admin-panel/`/`landing/` → пропустить `npx tsc -b`;
   - нет `alembic/versions/` → схему не трогать, alembic отработает сам при старте app (в логах — `alembic.runtime.migration`, это норма, не ред-флаг);
   - **backend-only правки всё равно требуют `compose build`** — код в образе, volumes нет, `up -d` без пересборки старьё не подхватит.
3. Диск перед build: `df -h /` (19.09: 58% → prune не нужен; порог ~78–80%, иначе `docker builder prune -f`, жрать будет ~1–2.5 ГБ).
4. Туннель НЕ трогать — прод на caddy + фикс-домене (шаг «Туннель ПЕРВЫМ» ниже — только для dev/демо-стендов).
5. `dk.sh docker compose build` (background, успех = `Built` в хвосте; dk.sh может дать exit 2 после успеха).
6. `dk.sh docker compose up -d --force-recreate app bots` — db и caddy НЕ перезапускать.
7. Верификация: `curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/health` → 200; `/`, `/quiz`, `/web/`, `/s/city-dental` через `https://24ghost.online` → 200; логи app на ошибки; `Run polling` в логах ботов.

## Быстрый старт (деплой на vdska)
⚠️ 07.09: машина Hermes = vdska (hostname vdska); `scripts/remote*.sh` (ssh-обёртки) НЕ работают — хост `hermes` не резолвится. Все команды локально напрямую.
⚠️ Пилот переименован: `rashid-dental` → **`city-dental`**; демо-вертикали (demo-barber/salon/massage/fitness) — `scripts/seed_verticals.py`.
⚠️ Сброс БД одной командой: `~/.hermes/scripts/dk.sh bash -c "cd ~/projects/lead-platform && bash scripts/db_reset.sh --yes"` (DROP SCHEMA → seed_platform → seed_pilot → up -d app bots). Флаг **`--demo` = канон-состояние 24ghost** (platform + витрина «Косы» slug=demo, своя база lp_demo_demo, боты из config/tenants/demo.toml). Затем заполнение CRM: см. «Демо-CRM» ниже.
⚠️ **14.09 поправка Василия («А что ты делаешь, боюсь спросить? Нужно было сбросить и перезапустить все»):** по явной команде «снести всё / переставить» — запускать штатный скрипт СРАЗУ. Единственное предварение: если в текущих базах есть уникальные секреты (токены ботов клиента в сирота-базе `tenants`), выписать их в файл ОДНИМ быстрым запросом — и сразу вайп. Не разворачивать чтение кода/реестра ДО команды: диагностику — параллельно или после. При длинной диагностике по свежей жалобе — вердикт каждые 2–3 tool-вызова (усиление правила 09.09).
⚠️ Новые скрипты НЕ видны в работающем контейнере (код в образе, volumes нет): `dk.sh docker cp scripts/<x>.py lead-platform-app-1:/app/scripts/` + `dk.sh docker exec lead-platform-app-1 python scripts/<x>.py`, либо пересборка образа.
⚠️ Kanban-гигиена: после мержа задачи удалять её worktree и влитые ветки (`git branch --merged main | grep lead-platform/ | xargs git branch -d`); 07.09 накопилось 33 — Василий недоволен.
0. **Проверка диска ПЕРЕД build (07.09, привычка Василия «сначала место почистить»):**
   `df -h /` + `dk.sh docker system df` — если >80%: `docker builder prune -f`, удалить
   осиротевшие kanban-образы `t_*-*`/`t_*-app`/`t_*-bots` и мёртвые контейнеры
   (`docker ps -a`), ненужные образы сторонних сервисов. До сборки было 87% → после 63%.
   ⚠️ **Не ждать чуда от prune (уточнение 09.09 вечер):** `docker system df` показал
   Build Cache 16.33GB / RECLAIMABLE 1.073GB — и `builder prune -f` вернул ровно ~1ГБ,
   поле «RECLAIMABLE» честное, «TOTAL» вводить в заблуждение. Если после prune df всё ещё
   >78% — это не недоработка чистки, а реальный размер рабочих образов; сборка всё равно
   пройдёт, не уходить в расширенную очистку. (09.09: 80% → prune 1.07GB → 78% → build → 81%.)
1.5. **Пред-чек сборки за секунды (вместо «npm run build», если node_modules уже есть):**
   `cd admin-panel && npx tsc -b` И `cd landing && npx tsc -b` (пути после перестройки 12.09,
   `web/` больше нет) — это ровно та проверка, которая валит
   Dockerfile-сборку на чужих коммитах (см. питфолл 09.09 про 34671fb); exit 0 → можно
   гонять `compose build` не глядя. `npm run build` нужен только когда надо и vite собрать.
1. `cd ~/projects/lead-platform && git pull --ff-only origin main`
2. **Туннель ПЕРВЫМ (урок 08.09; для прода на caddy 24ghost.online шаг ПРОПУСТИТЬ — актуален только для cloudflared-стендов):** проверить, жив ли URL в `.env` —
   `curl https://<sub>.trycloudflare.com/quiz`; NXDOMAIN/000 = мёртв (туннель рестартовался).
   Если мёртв: поднять новый туннель (`~/.local/bin/cloudflared tunnel --url http://localhost:8000
   --no-autoupdate`, background+tee → URL из логов) и обновить `WEBAPP_URL`/`SITE_BASE_URL` в `.env`.
   ТОЛЬКО потом сборка/подъём — иначе сервисы стартуют со старым URL и шлют мёртвые ссылки
   (реальный случай 08.09: `up -d` после pull прошёл, а боты/WebApp ссылались на NXDOMAIN-домен).
3. Сборка образов: `~/.hermes/scripts/dk.sh docker compose build` — **background=true БЕЗ
   notify**, дальше самому `process(action='wait', timeout≤180)` (клампится, повторять),
   успех = `Built` в хвосте вывода. ⚠️ `notify=[…]` (список паттернов) в текущем рантайме
   отвергается валидатором терминала («notify must be true/false … or a list of strings»
   — на список тоже; 09.09) — не тратить ход на эксперименты с форматом.
   ⚠️ **14.09: exit_code=2 при успешной сборке — НЕ ред-флаг.** dk.sh — shell-обёртка,
   её собственный хвост может валиться на кавычках («/tmp/dk_cmd.sh: unexpected EOF while
   looking for matching») ПОСЛЕ того, как compose вывел `app Built` / `bots Built`.
   Критерий успеха — `Built` в выводе + `docker ps` со свежими контейнерами, НЕ exit code.
   ⚠️ **14.09: `scripts/stack.sh` в репо — ЛОКАЛЬНЫЙ tmux-стек (dev), НЕ прод.** Прод —
   docker compose (db/app/bots/caddy). Прод-контейнеры могут лежать (`docker ps -a`
   показывает только caddy+test-pg), а site при этом отдаёт 502 через caddy — это повод
   поднимать, а не диагностировать код.
4. `dk.sh docker compose up -d db` (background; Hermes блокирует как server-процесс)
5. **Сид платформы ДО первого старта app** (только для свежей БД; тенант platform должен быть id=1):
   `dk.sh docker compose run --rm --no-deps app python scripts/seed_platform.py`
6. `dk.sh docker compose up -d --force-recreate app bots` (**--force-recreate** при смене
   `.env`/URL: обычный `up -d` НЕ перечитывает env у running-контейнеров)
7. Проверка: `curl localhost:8000/health`, **curl ЧЕРЕЗ ТУННЕЛЬ** `/quiz` → 200,
   `dk.sh docker logs lead-platform-bots-1 --tail`, `printenv SITE_BASE_URL` в bots.
   **Фронт-правки: верификация, что новый бандл реально в проде (14.09, хэш-сверка —
   пути после перестройки репо):** сравнить хэш в образе с хэшем наружу, обе пачки бандлов:
   `dk.sh docker exec lead-platform-app-1 grep -oE "assets/index-[A-Za-z0-9_-]+\.js" admin-panel/dist/index.html`
   vs `curl -s https://24ghost.online/web/ | grep -oE 'assets/index-[A-Za-z0-9_-]+\.js'` (админка)
   и `... landing/dist/index.html` (`assets-p/index-*.js`) vs `curl -s https://24ghost.online/quiz`
   (лендинг). Равенство обеих пар + все 4 URL (`/`, `/quiz`, `/web/`, `/s/city-dental`) → 200
   = деплой применён. «build прошёл» ≠ «отдаётся новый бандл»; старые пути `web/dist`,
   `web-public/dist` — НЕ существует.

## Сброс БД («снести все данные» для ручной проверки, актуально 08.09)
Одна команда + два дозаполнения. Ручные `UPDATE ..._bot_username` из старого рецепта 01.09
больше НЕ нужны: seed_platform читает `BOT_WORKER_USERNAME`/`BOT_CLIENT_USERNAME` из .env
и ставит platform worker+client сам; seed_pilot (дефолтный slug **city-dental**) ставит
пилоту client_bot_username сам.
```bash
# 0) туннель ПЕРВЫМ: curl https://<URL из .env>/quiz — мёртв → новый туннель ДО сброса (см. секцию Туннель)
~/.hermes/scripts/dk.sh bash -c "cd ~/projects/lead-platform && bash scripts/db_reset.sh --yes"
#   (background; ~1-2 мин: stop app+bots → DROP SCHEMA → seed_platform → seed_pilot → up -d app bots)
# 1) демо-вертикали и CRM — docker exec по УЖЕ запущенному app (db_reset сам поднимает app;
#    скрипты в образе с 07.09 — проверять НЕ через docker cp, а: dk.sh docker exec lead-platform-app-1 ls scripts/)
dk.sh docker exec lead-platform-app-1 python scripts/seed_verticals.py
dk.sh docker exec lead-platform-app-1 python scripts/seed_demo_crm.py
```
Проверка после сброса (обязательный чек-лист): username'ы в БД
(`SELECT id, slug, worker_bot_username, client_bot_username FROM tenants ORDER BY id;`),
`curl /api/public/platform-bot` (оба username'а), curl **через туннель** `/quiz` + `/s/city-dental` +
`/web/` → 200, `docker logs lead-platform-bots-1` → «Run polling for bot @lead_worker_demo_bot».
Две учётки для ручной проверки после сидов на месте: Василий tg 350262645 → SUPER_ADMIN
platform; Андрей tg 7519756578 → OWNER city-dental.
⚠️ Предупредить пользователя после вайпа: сессии инвалидированы — закрыть и переоткрыть
Mini App / разлогиниться (старый `tg_init_data` в localStorage и cookie `lp_session`
не соответствуют новым сидам).
Для повторного прогона демо-CRM на живом тенанте — сначала сброс его записей/чатов:
`scripts/reset_tenant_demo_history.sql` (в скилле; id тенанта заменить, approval-ход).
⚠️ Актуальные username — через `curl https://api.telegram.org/bot<TOKEN>/getMe` из .env;
01.09 вечером боты переименованы БЕЗ «рашида»: @rashid_worker_bot → **@lead_worker_demo_bot**,
@rashid_clinic_bot → **@lead_client_demo_bot** (новые токены в .env и БД). Старые имена больше не использовать.
`ensure_super_admin` выполняется в lifespan при **СТАРТЕ** app — после сброса обязателен
рестарт: `up -d` НЕ пересоздаёт уже running-контейнер. `docker compose restart app` может
потребовать подтверждения пользователя (approval Hermes) — предупредить и ждать OK, не
пытаться обойти. Супер-админ привязывается к **ПЕРВОМУ** тенанту — поэтому сид раньше старта.
Сид пилота восстанавливает демо-тенант (услуги, специалист, KB, графы) — без него ломаются
кнопка «🎯 Попробовать запись» и визитка /s/city-dental.
После чистки проверить: `curl /api/public/platform-bot` → `{"username":"lead_worker_demo_bot",...}`;
реальные username ботов — через `curl https://api.telegram.org/bot<TOKEN>/getMe` (из .env).

## Сиды
- `scripts/seed_platform.py` — тенант **Lead Platform** (slug=platform), токены ботов из .env.
  Модель: сид платформы, а НЕ чужой бизнес-тенант; бизнес-тенанты — через викторину/запрос владельца.
- `scripts/seed_pilot.py` — пилот «Городская стоматология» (дефолтный slug=**city-dental**,
  переопределяется `--slug`): услуги, специалист, график, KB, конфиг визитки, `client_bot_username`
  из env. Username ботов вручную после сида НЕ проставлять (обsolete-рецепт 01.09, проверено 08.09).
- Запуск скриптов в контейнере: `dk.sh docker compose run --rm --no-deps app python scripts/<name>.py`
  (env берётся из compose env_file — вне контейнера скрипты через `os.getenv` .env не видят).

## Туннель cloudflared (HTTPS для Mini App)
- **На vdska cloudflared РАБОТАЕТ** (на локальной машине пользователя порт 7844/QUIC заблокирован — там pinggy/serveo по 443).
- Запуск: `~/.local/bin/cloudflared tunnel --url http://localhost:8000 --no-autoupdate` (background, silent — это демон).
- URL из логов: `Your quick Tunnel has been created! Visit it at https://<sub>.trycloudflare.com`.
- **«Не открывается» → диагностика (01.09):** 1) локально `curl localhost:8000/quiz` — если 200,
  а туннель 530/502 — процесс cloudflared умер (`ps -ef | grep cloudflared` пусто); 2) перезапустить
  туннель (background), взять НОВЫЙ URL из логов, обновить `WEBAPP_URL`/`SITE_BASE_URL` в `.env`;
  3) `up -d app`; 4) сразу после рестарта app туннель может отдавать 502 — это НОРМАЛЬНО
  (uvicorn поднимается), подождать ~10с и ретрай. Туннель — демон без автозапуска: после
  ребута vdska/смерти процесса URL меняется, старые ссылки у Василия перестают работать.
- **Жалоба «запустил и не работает» → СПЕРВА проверять доступность, потом код (01.09).**
  Продукт был жив (health 200, викторина 200 на localhost), а Василий жаловался «не
  взлетело» — потому что открывал СТАРЫЙ trycloudflare URL, который умер после перезапуска
  туннеля. 10-секундная проверка до любых правок в коде:
  1) `curl -m 6 localhost:8000/health` → если 200 — app жив;
  2) `curl -m 15 https://<старый-домен>/quiz` → `000`/таймаут;
  3) `nslookup <старый-домен>.trycloudflare.com` → **NXDOMAIN** = туннель перезапускался,
  URL сменился. Это НЕ баг кода — чинится новой ссылкой, а не правками.
- **Поднять новый туннель (рецепт, Hermes):** НЕ использовать `nohup`/`disown` — терминал
  Hermes блокирует („Foreground command uses shell-level background wrappers“). Правильно:
  `terminal(command="~/.local/bin/cloudflared tunnel --url http://localhost:8000 --no-autoupdate 2>&1 | tee /tmp/cf_tunnel_new.log", background=true)`
  → через ~6с `grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /tmp/cf_tunnel_new.log`.
  Проверить `curl https://<новый>/quiz` → 200, отдать Василию новую ссылку. Если URL
  используется в продукте (CTA/боты/QR) — обновить `WEBAPP_URL`/`SITE_BASE_URL` в `.env`
  и рестартнуть app; для разовой ручной проверки можно просто отдать URL.
  Старый процесс cloudflared НЕ убивать (чужой, из gateway-сессии): новый quick-туннель
  не конфликтует (каждый держит свой edge-URL, локально порт не занимает).
- **После смены URL** обновить в `~/projects/lead-platform/.env`:
  `WEBAPP_URL=https://<sub>.trycloudflare.com/web/` и `SITE_BASE_URL=https://<sub>.trycloudflare.com`,
  затем **`dk.sh docker compose up -d --force-recreate app bots`** (07.09): обычный
  `up -d` НЕ пересоздаёт running-контейнеры и НЕ перечитывает env — app/боты остаются
  на СТАРОМ домене и шлют магические ссылки/WebApp-кнопки на мёртвый URL
  (реальный случай «🔑 Вход в админку … не открылось»: sed по .env не применился из-за
  блокировки команды + `up -d` без --force-recreate). Проверка после рестарта ОБЯЗАТЕЛЬНА:
  `dk.sh docker exec lead-platform-bots-1 printenv SITE_BASE_URL` + curl туннеля.
  Правка .env и рестарт — РАЗНЫЕ команды: если первая утонула в approval/BLOCKED,
  вторую не считать сделанной (перепроверить grep'ом .env).
- **Cloudflare 1033 при живом localhost (07.09):** `/health` на :8000 = 200, а через
  туннель HTML-ошибка «configured as a Cloudflare Tunnel… unable to resolve» — edge
  quick-туннеля отвалился сам, процесс cloudflared может даже висеть с «Registered
  tunnel connection» в логе. Лечится только новый туннель + новый URL (выше), это НЕ
  баг кода. После каждого деплоя проверять curl'ом ЧЕРЕЗ ТУННЕЛЬ, а не только :8000.
  URL меняется при каждом рестарте туннеля.
- Проверка: `GET /api/admin/site` с initData супер-админа → `share_url` должен содержать SITE_BASE_URL, не localhost.

## Викторина v2 — воронка продаж (01.09.2026, согласовано с Василием)
План: `~/hermes-vault/Projects/Planning/2026-09-01/lead-platform-quiz/` (README + 01-plan-quiz + 02-tech).
Реализовано и смержено (бэкенд `d36c01d`, фронт `fee4009`), деплой сделан, финальная проверка на телефоне pending.

**Продуктовые решения (по требованиям Василия — переделывали 4 раза, пока не поняли):**
- Викторина = **воронка продаж**, не анкета/конфигуратор. Каждый вопрос должен ПОКАЗЫВАТЬ ценность продукта (семя: «это поможет тебе»).
- Ценность — **реакцией ПОСЛЕ ответа** (реплика на экране), не блок до ответа.
- **Минимум 15 шагов** (итого 19 экранов, шаг 0 = старт-оффер «Соберём систему за 2 минуты»). 8 шагов — «тупая херня».
- **Крючок-боль («сколько клиентов теряете») НЕ нужен** — не пугать в начале, вовлекать позитивом.
- **Тариф — в конце** (шаг 15); **до тарифа НИ ОДНОГО апселла**; апселлы — только после выбора тарифа (up-sell к выбранному).
- Тарифы — лестницей под апселлы; **ИИ внутри тарифов p2/p3** — отдельный ИИ-апселл убран («клиент два раза платит за ИИ»). Остаётся апселл «Настройка под ключ» (разово, не дублирует).
- **Контакт — ОДИН селектор** tg/instagram/phone/email (шаг 17), не отдельные экраны; привязка лида всё равно через бота (telegram_id) + IP.
- **Формулировка шага контакта (жалоба 01.09):** контакт нужен, чтобы СВЯЗАТЬСЯ / предложить доп. услуги, НЕ «прислать доступ». «Куда прислать доступ? Пришлём доступ и план запуска» — ЗАПРЕЩЕНО (Василий: «мы блядь ничего не пришлём»). Правильно: «Как с вами связаться?» + «Оставьте один удобный контакт — свяжемся, если понадобится что-то уточнить или предложить». Тексты викторины живут в `web/src/quiz/config/quizConfig.json` И дублируются в `QuizPage.test.tsx` — при правке текста обновлять ВСЕ вхождения в тестах (grep по старому тексту), replace_all по одному шаблону может пропустить вхождения с другим контекстом.
- **QR НЕ в викторине** — будет в боте.
- Скидка «−30% первый месяц при оплате сейчас» + **фиксация IP**, дедуп оффера один раз на IP/контакт.
- Превью-визитка собирается по ходу (название/сфера/услуги/часы), перед тарифом — персональный итог («вот ваша система»).

**Архитектура кода (урок: QuizPage был 894 строки — «так ни один нормальный программист не пишет»):**
- Data-driven: `web/src/quiz/config/quizConfig.json` (все 19 шагов: id/type/title/options/reaction/validate/next) + `useQuiz.ts` (оркестратор) + `steps/` (12 компонентов: Start/Choice/Text/Services/Hours/Summary/Tariff/Upsell/Contact/Offer/Final/Shell) + тонкий `QuizPage.tsx` (~100 строк). Тексты/цены правятся в JSON, не в коде.

**Бэкенд v2:**
- Контакт `{type, value}` + `normalize_contact` (`src/domain/leads/contact.py`; tg/insta — strip '@' lower, email — lower, phone — цифры).
- Новые колонки `leads`: `ip_address`, `contact_type`, `contact_value`, `discount_offered_at` — идемпотентные ALTER в `init_db` (`src/core/db.py`), `create_all` их НЕ добавит.
- Дедуп скидки: `src/application/leads/quiz_discount.py` (`discount_already_used` по IP или контакту, exclude_lead_id для update-ветки).
- `src/interface/api/public/quiz_schemas.py`: `ContactIn`, `QuizLeadIn` (contact + legacy tg_username/phone), `DiscountOut`/`QuizLeadOut` (discount {available, percent}).
- Ответ `POST /api/public/quiz-lead` несёт `discount` для фронта.

**Воркеры упёрлись в лимит итераций (100/100) с незакоммиченной работой — спасение оркестратором:** проверка фронт-воркера = `cd web && npx tsc --noEmit` + `npx vitest run` (весь web suite); проверка бэк-воркера pytest на vdska падает `ConnectionRefusedError 5432` (нет postgres) — e2e через curl. Ветки мержить по фактическому имени (`git branch -a | grep wt/`), не по id задачи.

## web-public — публичная воронка вынесена из web/ (09.09, коммит e47ca02)
Лендинг + викторина вырезаны в отдельный SPA `web-public/` (cda8500..437b53b), но **деплой-проводка в тех коммитах не была сделана** — `build app` как есть ломал `/` и `/quiz` (web/dist содержит только админку с `/` → Navigate на /login). Проводка (задепложено, проверено через туннель):
- `src/main.py::create_app(..., public_dir=...)`: если `web-public/dist` есть — роуты `/` и `/quiz` отдают его index.html (регистрируются ДО spa_fallback админки; в самом web-роутере `/` остаётся redirect в /login — это путь админки внутри /web).
- `web-public/vite.config.ts`: `build.assetsDir: 'assets-p'` — ассеты публичного бандла изолированы от админских `/assets`.
- `spa_fallback`: путь с префиксом `assets-p/` ищется в web-public/dist, остальное — в web/dist.
- `Dockerfile`: stage `webpublic` (node:20-alpine → npm ci → npm run build) + `COPY --from=webpublic /app/web-public/dist web-public/dist`.
- Предсборка локально: `cd web-public && npm ci && npm run build` (tsc -b && vite build; в выводе должны быть `dist/assets-p/...`).
- Проверка после деплоя: `curl / | grep assets-p` (≥1), `curl /quiz | grep assets-p`, `assets-p/index-*.js` → 200, `/assets/index-*.js` (админ) → 200, `/s/city-dental` → 200 (визитки остались в админ-бандле), `/web/` → 200.
- Урок (усиление правила 21.08 «заготовка ≠ deliverable»): при появлении НОВОГО фронтенд-модуля/поддиректории перед деплоем grep'ом проверить его путь в образ и наружу: `grep -rn "<модуль>" Dockerfile docker-compose.yml src/main.py`. «Смержено в main» ≠ «попадёт в прод».

## Проверка US-00a (10 шагов воронки платформы)
Критерии приёмки — в `docs/us00a-platform-funnel/steps/*.md` (репо). Что проверяется программно:
- 01 Лендинг `GET /` → 200 (с 09.09 — index.html бандла web-public, критерий: grep `assets-p` в HTML; не редирект в админку)
- 02 Викторина `GET /quiz` → 200; **10 шагов** (`TOTAL_STEPS=10`): 7 вопросов →
  шаг 8 апселл «Настройка под ключ» → шаг 9 апселл «ИИ-консультант» → шаг 10
  «Оплата» (НЕ «Готово», НЕ «готовим платформу»); лид создаётся на шаге 10
  (после апселлов, `addons` попадают в quiz_data); после pay-test —
  «Доступ открыт» + кнопка «🚀 Открыть админку» = `t.me/<worker>?start=lead_<id>`
  (username из `GET /api/public/platform-bot` — тенант platform; id из ответа
  POST /api/public/quiz-lead; нет username → кнопки нет)
- 03 Лид `POST /api/public/quiz-lead` (без auth) → 201 + лид в БД + `LeadEvent quiz_finished`;
  невалидный payload → 422; анти-дубль по username (повтор → тот же id)
- 04 Уведомление супер-админу — прямой Telegram API из app; no-op при отсутствии токена; живое подтверждение у пользователя в TG
- 07 Админка «Лиды»: `GET /api/admin/leads` с initData супер-админа → лид виден
- 08 Оплата: провайдеры регистрируются ТОЛЬКО при наличии `PAYME_*`/`CLICK_*` ключей в .env; без ключей — «Оплата скоро»
- 09 Триал/cron: scheduler стартует в lifespan; джобы `trial_expiry_daily`+`retarget_daily` (cron hour=9), `auto_status`/`reminders`/`escalation_check` (interval 5m); `company_factory` ставит `trial_ends_at = +7 дней`
- 10 Анти-фрод: unique-индексы `ix_leads_telegram_id_unique` + `ix_leads_username_web`; rate-limit/IP-фрод НЕ реализованы (решение — после пилота)
- 05 (бот-викторина) — УПРАЗДНЕНА (см. продуктовое решение ниже): deep link `?start=quiz` ведёт в приветствие/меню, как /start
- 06 (автозаполнение компании из викторины) — живой проход в Telegram
- Live (Telegram, воронка): `/start` у незнакомца → «Пройти викторину» (БЕЗ «Войти
  в админку»); пройти `/quiz` → кнопка «Написать боту» (`?start=lead_<id>`) → бот
  отвечает «Заявка получена» → в БД у лида появился `telegram_id`:
  `SELECT id, username, telegram_id FROM leads WHERE id=<id>;`

## initData супер-админа (для curl-проверки админских API)
Готовый e2E-контракт «новый клиент + приглашение» одним прогоном: `scripts/check_invite_contract.py`
(подписывает initData в процессе, проверяет 422/201+link/regenerate/400; после — вычистить
«e2e …»-карточки, enum роли ВЕРХНИМ регистром).
Готовый скрипт: `scripts/gen_initdata.py` (HMAC-SHA256, подпись WebAppData;
токен берёт из `BOT_TOKEN_WORKER` в `~/projects/lead-platform/.env`).
```bash
INITDATA=$(python3 ~/.hermes/skills/devops/lead-platform-ops/scripts/gen_initdata.py)
curl -s http://localhost:8000/api/admin/leads -H "X-Telegram-Init-Data: $INITDATA"
# любой юзер (проверка прав роли): TG_ID=<id> TG_USERNAME=<uname> python3 .../gen_initdata.py
```

## Демо-CRM (07.09)
`scripts/seed_demo_crm.py` (в репо) заполняет все 5 бизнес-тенантов: этапы воронки (BOOKING_DEFAULT_STAGES), по 11 клиентов (role=CLIENT: этап/источник/сумма/ответственный), ~20 записей за 40 дней (DONE/CONFIRMED/CANCELLED/NO_SHOW + AppointmentEvent + StaffNotification в колокольчик), 3 чата с сообщениями (open/needs_response), 6 лидов платформы для «Лидов» суперадмина. Идемпотентен: непустая таблица leads пропускается. С 17dfbe0 слаги принимаются аргументами CLI (`seed_demo_crm.py kosy-9`) — провизим на ЛЮБОЙ живой тенант; `_ensure_clients` ДОЛИВАЕТ существующих CLIENT до плана STAGE_PLAN (не скипает, если карточки уже есть), но ⚠️ сид ПЕРЕЗАПИСЫВАЕТ week_schedule специалиста на демо-WEEK_SCHEDULE — после прогона на живом тенанте вернуть реальный график; history (записи/чаты) генерится только при пустых таблицах — для повторного прогона сначала вычистить записи/чаты/уведомления тенанта. Reminder-строки НЕ создаёт — иначе cron шлёт Telegram на вымышленные telegram_id. Запускать ПОСЛЕ db_reset + seed_verticals, `docker exec lead-platform-app-1 python scripts/seed_demo_crm.py` (в актуальном образе скрипты уже есть — docker cp нужен только если образ старее сида).

## ⚠️ Worktree «воскресает» после complete/kill — проверяй на новые коммиты (07.09, t_9502e93a)
Timed-out (`max_runtime=0s; will retry`) или убитый воркер => диспетчер retry спавнит НОВЫЙ процесс в ТОМ ЖЕ worktree: незакоммиченные правки не теряются, и retry может дописать ценную работу (так появились POST /clients/{id}/appointments + /unread-count, смержено bf596e5) уже ПОСЛЕ того, как оркестратор закрыл задачу и удалил worktree — `git worktree list` показал его заново. Порядок уборки после kill/complete: 1) `git worktree list` + `git log main..<ветка>` — нет ли свежих коммитов retry-процесса; 2) если есть — прогоны целевых pytest, свой коммит недостающего, merge; 3) только потом `git worktree remove --force` + `git branch -d`. Никогда не удалять worktree «механически» сразу после timed_out.

## Быстрый скан «старого кода админки» (07.09, вопрос «где ещё остались инкременты?»)
Однострочник по web-дереву — файлы, которые никто не импортирует (сироты) за секунды:
```bash
cd web && for f in $(find src/pages src/components src/hooks -name "*.tsx" -o -name "*.ts" | grep -v test); do b=$(basename "$f" | sed 's/\.tsx$//;s/\.ts$//'); [ "$b" = "index" ] && continue; n=$(grep -rl "$b" src/ --include="*.tsx" --include="*.ts" | grep -v test | grep -v "^$f$" | wc -l); [ "$n" -eq 0 ] && echo "ORPHAN: $f"; done
```
Далее обязательно сверить РОУТЫ (grep "Route path" App.tsx + импорты): сирота = удаление, а «старая страница за роутом за ролью» = долг редизайна (найдено 07.09: /clients/:id все еще вел на старый ClientCardPage; /plans /ai оставлены осознанно без V-10 макета). Не путать: старые components/chat|settings живы — их ест НОВАЯ SettingsPage/очередь, это не мусор.

## Медленный coder на механических фиксах — спасение оркестратором (07.09)
Когда воркер на готовый чек-лист фиксов жжёт 40+ мин (находки аудита уже известны: файл/строка/суть), Василий останавливает: «то, что можно было сделать быстро, выполняется очень долго». Порядок: kill процесса воркера (`ps -ef | grep kanban.*T_ID` → kill -9) → прочитать `git diff` и новые файлы в worktree (половина кода обычно валидна и пригодна) → доделать недостающее + целевые тесты самому (`PYTHONPATH=. ~/projects/lead-platform/.venv/bin/python -m pytest tests/<файлы> -q`, нужен .env-симлинк, см. питфолл выше) → логические conventional-коммиты → merge в main + push → `hermes kanban complete T_ID --result ...` → `git worktree remove --force .worktrees/T_ID` + `git branch -D` (явная просьба Василия: удалять worktree за собой) → диспатчить следующую задачу цепочки. Мелкие правки по готовому аудиту вообще лучше делать самому, не роутить на coder'а.

## Заходы в админку из уведомлений бота (07.09, ЗАФИКСИровано в main 1c5718d)
Жалоба: чат-пуш («💬 Новое сообщение», кнопка «Открыть чат») вёл на неавторизованный /chat/{id} — войти нельзя. Рабочий паттерн (применять ко ВСЕМ новым пушам бота в веб):
- `GET /api/auth/token?token=&next=` принимает `next` — whitelist `/chat/…` и `/clients`, всё остальное (внешний URL) игнорируется → посадка по роли (open-redirect закрыт);
- `worker_chat_notifier._magic_chat_link(user_id, conv_id)` — одноразовый login-токен (`create_login_token`, TTL 5 мин, привязан к членству) → `{SITE_BASE_URL}/login?token=<raw>&next=%2Fchat%2F<id>`; кнопка «Открыть чат» = эта ссылка, fallback (фабрика None / ошибка) — обычный URL;
- `LoginPage.tsx` прокидывает `next` в API-редирект (иначе теряется);
- Тесты: `tests/integration/test_notify_direct_api.py::test_notify_new_message_magic_link_when_factory_set`, `tests/api/test_auth_token_next.py`.
Правило: пуш вне браузерной сессии без магической ссылки = мёртвая кнопка; голые web-URL в бот-пушах не давать.

## Мини-апп веб-записи (10.09, коммит b24cbe6, ЗАДЕПЛОЕН)
Кнопка «📅 Записаться» в клиентском боте → WebApp (web_app button, URL {SITE_BASE_URL}/book/<slug>) → React-роут /book/:slug (вне админ-шелла, spa_fallback его отдаёт). Поток: услуга (с фото photo_url) → день → время → создание → если tenant.settings.deposit_percent (1-100) — экран фейковой предоплаты (POST deposit → deposit_paid_at, шлюз позже) → «Вы записаны, адрес из site.contacts».
- API: `/api/public/booking/{slug}/config|slots|appointments|appointments/{id}/deposit` — авторизация ТОЛЬКО по initData (X-Telegram-Init-Data, подпись токенами тенанта из URL + фолбэк bot_token_client для демо); тенант ЯВНО из slug (демо-бот общий — resolve по токену неверен). CSRF/ TenantMiddleware не мешают (/api/public/*).
- Клиент = ensure по telegram_id (создаёт User CLIENT). Запись идёт через CreateAppointment (шина → уведомление владельцу + напоминания работают бесплатно). source="web".
- Колонки deposits: deposit_percent/amount/paid_at/method — ALTER в init_db.
- Меню клиента: «Услуги/Записаться ещё раз/Мои планы» УБРАНЫ по решению Василия (handler'ы callbacks живы — deep link/текст «📋 Услуги» всё ещё ведёт в бот-флоу).
- E2E-проба: scripts в /tmp одноразовые; подмах initData = тот же WebAppData-HMAC (навык gen_initdata).

## Проверки БД (psql)
Имена таблиц, enum-значения, проверки супер-админа/KB/токенов/адреса — `references/db-schema-queries.md`.
Ключевое: KB = таблица `knowledge_base`; enum `user_role` сравнивается по ИМЕНАМ членов (`SUPER_ADMIN`, не `super_admin`).
⚠️ Метакоманды `\d`/`\dt` через `docker exec ... psql -c` НЕ работают (это не SQL — «syntax error at or near "d"»). Существование таблицы проверять SQL: `psql -c "SELECT to_regclass('public.chat_bot_bindings');"` (NULL = нет).

## Как фиксировать находки аудита/прожарки (03.09)
Василий: «надо записать все найденные баги и закинуть в репо в бэклог, там файл есть».
- ⚠️ 09.09: файла `docs/us-audit/backlog.md` в репо БОЛЬШЕ НЕТ — удалён коммитом 3253200 «миграция задач/планов на GitHub-центричный флоу». Находки — в GitHub Issues (`gh issue create`); исторический список B-XX/V-XX доступен через `git show 3253200^:docs/us-audit/backlog.md`. Любой grep/чтение по пути backlog.md — ошибка.
- Формат: общий шаблон записи с полями Дата/Источник/Тип/Описание/Влияет на/Приоритет/Статус/Решение владельца.
  Префиксы: **B-XX** = баги (найдено в живом прогоне/прожарке), **V-XX** = изменения видения/доработки.
- Типы в таблице шапки: баг (новый, добавлен 03.09), видение, доработка, логика, идея.
- Решения владельца фиксировать сразу в записи (например: админка → веб = V-04;
  суперадмин = владелец тенанта платформы).
- Крупные отчёты аудита (отчёты архитектора) — в worktree ветке задачи, но находки в
  backlog заносить в main сразу.

## Мобильный адаптив админки (08.09, коммит eb011f7)
Жалоба Василия: «на десктопе ок, на телефоне не удобно смотреть админку»; требования:
**минимальными усилиями, без лишних тестов; «а по css ты не можешь определить?»** — начинать
с обзора раскладок (grep `gridTemplateColumns` / фикс. ширин по `crm/`), а не с браузерного аудита.

Что уже адаптивно из коробки: CrmShell прячет сайдбар в drawer < lg (1024px), бургер в TopBar;
таблицы в `overflow-auto` (скролл внутри таблицы — приемлемо); RecordPanel `maxWidth: '100%'`.
Адаптив лендинга/викторины/визитки есть, у crm/ НЕ было ни одного media-запроса — это и есть
источник жалобы.

Сделано (минимальные правки, без новых тестов):
- Календарь: `.cal-wrap` (месяц+день бок о бок) → media (max-width:1023px) `flex-direction: column`;
  `.cal-month` без правой рамки; `.cal-day` (width:400px!) → `width:100%`; `.cal-ev .n` скрыт
  (в чипе только время); ячейки `minmax(86px,1fr)` → `minmax(56px,1fr)`. Медиа-блоки — в конец
  `web/src/crm/tokens.css` (импортируется через index.css).
- Инлайн-grid в tsx НЕ перебить media-правилом без !important → правильный паттерн: жёсткую
  колонку заменить на auto-fit: `'1fr 1fr'` → `'repeat(auto-fit, minmax(300px, 1fr))`;
  `'repeat(4, minmax(0,1fr))'` → `'repeat(auto-fit, minmax(150px, 1fr))`
  (FieldGrid, HoursSection, SiteFields, ProfileSection, SiteThemes, StatsPage KPI/CARDS).
  ⚠️ **НО goлый `minmax(420px, 1fr)` вылезает за экран на телефоне 390px** (реальный баг
  08.09: статистика «Записи по дням/Воронка этапов» за границу). Единственно правильная
  форма для колонок шире ~350px: **`minmax(min(100%, 420px), 1fr)`** — min() не даёт
  колонке быть шире контейнера. Таблицы внутри карточек дополнительно оборачивать
  `<div style={{overflowX:'auto'}}>` (SpecialistsTable).
- Настройки (финал 08.09, коммит 9f7ef4c): панель секций SettingsNav на мобильном
  ЗАМЕНЕНА на компактный `<select>` через `window.matchMedia('(max-width: 767px)')`
  внутри SettingsNav.tsx (options = SECTIONS, onChange → onSelect) — Василий отверг
  и табы сверху («второе меню», «панель двигает влево»). Плюс в SettingsPage корню
  добавлен класс `settings-layout`, media (max-width:767px): `flex-direction: column` —
  без этого select-блок в flex-row сжимает контент слева до нечитаемого.
  ⚠️ Урок про flex: панель в flex-row с align-items stretch растягивается на всю
  высоту соседа (симптом «второе меню» высотой 1454px — nav h=1454 при контенте
  настроек); любой мобильный переключатель секций требует column-раскладку родителя.
- Точки перелома: <1023px календарь, <767px настройки. Сетки-формы сами складываются через auto-fit.

**08.09 вечер (коммиты 7ee9484, 2420a73) — карточка клиента на мобиле:**
- Quick-actions («Записать/Написать/Заметка/Позвонить») вылезали за экран («кнопка позвонить
  выпадает») → `flexWrap: 'wrap'` на строку в QuickActions.tsx; «Позвонить» с marginLeft:auto
  переносится на вторую строку.
- Блок полей FieldGrid (этап/ответственный/ближайшая запись/сумма) по требованию Василия
  «пол-экрана занимают, сделай стрелку, по нажатию скрывать, только для мобильных»:
  collapsed-состояние через `useState(isMobile)` — на мобиле старт свёрнутым (лента сразу
  видна), свёрнуто = строка-кнопка «› Поля клиента» + название этапа справа, развёрнуто =
  внизу «⌄ Свернуть» на `gridColumn: '1 / -1'`; стрелка рендерится ТОЛЬКО при matchMedia
  <768px (та же точка, что у настроек), на десктопе nothing changed.
- ⚠️ jsdom НЕ имеет `window.matchMedia`: любой компонент с matchMedia обязанguarded
  (`typeof window !== 'undefined' && !!window.matchMedia`) и в init-state, и в useEffect —
  fieldGrid.test.tsx упал 10 тестами «matchMedia is not a function». Тот же паттерн, что
  guard IntersectionObserver в TimelineList.
- ⚠️ `Icon` (crm/ui) не принимает prop `style` (TS ошибка) — не крутить chevron через
  transform, а брать нужный (chevronDown/chevronRight) из реестра.

**08.09 поздний вечер — мобильная навигация и доводки карточки/статистики:**
- Quick-actions: одного `flexWrap` мало — «Позвонить» переносилась одна на вторую строку,
  Василий: «не эстетично, особенно что рядом три кнопки». Финал (315344b): контейнеру
  убрать инлайн-стили вовсе → класс `.quick-actions` в tokens.css (flex+wrap на desktop),
  media <768px: `display:grid; grid-template-columns:1fr 1fr` (сетка 2×2 равной ширины),
  `> a { margin-left: 0 !important }` (перебить инлайн прижатие вправо). Урок: если
  media-правило должно ПЕРЕБИТЬ инлайн-стиль контейнера — инлайн надо удалить, а не
  воевать !important по всем свойствам.
- **Мобильная навигация — нижняя, бургера/drawer больше нет** (0efdbe5→ad5f5e0, финал):
  `web/src/crm/BottomNav.tsx` — sticky bottom, рендерится при matchMedia <1023px (в jsdom
  matchMedia нет → guard → null, desktop-тесты не видят дублей). Пункты — те же SIDE_GROUPS
  с ролевой фильтрацией, **`slice(0, MAX_TABS=4)`** рабочих табов + короткие подписи из
  карты SHORT (Записи/Чаты/Отчёты). ФИНАЛ (b3813ac): «Настройки» (sliders, роль
  owner/admin/super_admin) и «Профиль» (user) — extras того же BottomNav, ВНИЗУ: Василий
  отверг перенос иконок в топбар («кнопку профиля с настройками зря наверх перенес,
  это неудобно»). TopBar на мобиле = ТОЛЬКО колокольчик. Кнопка «Выйти из аккаунта» —
  внизу ProfileSection. «Выйти» в SideNav остался (desktop-тест CrmShell.test проходит —
  на мобиле сайдбар display:none). Правило Василия: все доступы к разделам — в нижнем
  баре одним рядом; верх — только уведомления.
  ⚠️ Две поправки Василия по ходу: «бургер убрал а меню внизу не добавил» — menu был,
  но УШЁЛ ПОД СГИБ: каркас CrmShell сидел на `h-screen`=100vh, а в мобильном WebView
  100vh больше видимой области (URL-бар). Фикс: класс `.crm-shell { height:100vh;
  height:100dvh }` (двойное объявление = фолбэк старым движкам) + sticky bottom +
  `padding-bottom: env(safe-area-inset-bottom)`. Затем «кнопок слишком много, меню
  должно всегда быть видимым» — 4 рабочих таба + настройки/профиль (см. выше).
  Уроки общие для любой мобильной WebView-админки: нижний бар + dvh, компактный набор
  табов, всё навигационное — вниз (второстепенное в топбар НЕ выносить — неудобно).
- Статистика (a255a5f): сетка карточек → класс `.stats-cards-grid` с
  `minmax(min(100%,420px),1fr)` (см. исправленный паттерн выше).
- Тулбар календаря: инлайн-стили → класс `.calendar-toolbar`; <767px `flex-wrap:wrap;
  height:auto` + `> span:last-child { margin-left:0 !important }` — фильтр «Специалист…»
  больше не лезет за 390px.
- **Уведомления на мобиле — полноэкранный оверлей (b3813ac).** Жалобы: «уведомления
  уезжают в сторону и не видно» + «кнопка Прочитать все не работает». Корень один:
  панель `w-[380px]` прижата `right:0` к колокольчику → на вьюпорте 390px её левый край
  = **−62px** (замерено playwright `getBoundingClientRect()` панели). read-all при этом
  работал (24 unread → 0 в БД и в /unread-count). Фикс: класс `.crm-notif-panel` вместо
  инлайн-ширины, media <768px — `position:fixed; inset:0`, список `flex:1` вместо
  max-h 420. ⚠️ ПОРЯДОК по жалобе «кнопка не работает» в выпадающей панели: СПЕРВА
  измерить геометрию контейнера, потом обработчик — «не видно» ≠ «не сработало».
  Общее правило: right-aligned fixed-width дропдаун на телефоне всегда залезает за
  левый край → <md делать полноэкранный оверлей.
- **08.09 финал (коммит 7b02f9d, задепложен): адаптив секций НАСТРОЕК** (часы/воронка/услуги/команда/приглашения/профиль/визитка на 390px): специалисты колонкой, перенос строк этапов воронки, nowrap-таблицы → скролл внутри `.table-scroll` (<768px), отступы секций 24→12px, ряд фото-плиток wrap. ⚠️ Неочевидный баг-паттерн: скрытый `input.rc-in` (чекбокс) без positioned-предка раздувал document до 542px даже при обрезанной таблице — фикс `.rc { position: relative }`; любой «появился х-скролл неизвестно откуда» — искать абсолютные/скрытые элементы без relative-предка. Headless-аудит: все 7 экранов docW=390 hScroll=False; `tsc -b` зелёный = критерий перед build образа.
- После этих коммитов mobile_audit.py в scripts/ скилла обновлён: навигация кликами по
  `[data-testid="crm-bottom-nav"] a:has-text(...)` — табы Клиенты/Записи/Чаты/Отчёты +
  Настройки/Профиль (с b3813ac они тоже внизу; aria-label-иконок в топбаре больше нет,
  старый клик по `[aria-label="Настройки"]` — мёртвый). Критерий зелёного аудита:
  `docW=390 hScroll=False` на всех разделах; единственный допустимый OUT — широкая
  таблица клиентов (скроллится внутри себя).

## «Записать» из админки (08.09, BookAppointmentDialog, коммит 9f7ef4c)
Жалоба Василия: «кнопка записать не работает, логика неудобная — сначала клиента добавить».
Корень: в веб-админке создания записи НЕ БЫЛО вообще — кнопка «Записать» (QuickActions book)
вела `navigate('/schedule?client=N')`, где открывалась та же карточка, а записать было нечем.
Фикс: `web/src/crm/panel/BookAppointmentDialog.tsx` — модалка записи для выбранного клиента:
- услуга/специалист/дата/время → `POST /api/admin/clients/{id}/appointments`
  (эндпоинт уже был, bf596e5; payload `{service_id, specialist_id, start_at}`,
  duration_minutes опционален). Слот валидируется бэкендом (график−блокировки−занятые−зазор),
  409 `detail` («слот недоступен…») показываем как есть — API свободных слотов в вебе НЕТ.
- `start_at` слать NAIVE ISO (`${date}T${time}:00`) — соглашение UTC-wall-clock: бэкенд
  naive-значение трактует как UTC и сравнивает со слотами без сдвига. Aware/Z сдвинет время.
- Роли: эндпоинт открыт owner/admin/specialist/support, но списки услуг/специалистов —
  STAFF (owner/admin); specialist/support получат 403 на загрузку селектов.
- Суперадмин platform в режиме `deal` — кнопки «Записать» у него НЕТ (только «Сделка»);
  проверять под владельцем бизнес-тенанта: city-dental OWNER telegram_id=7519756578.
- RecordPanel: `bookOpen` state, action 'book' → setBookOpen(true) (вместо navigate).

**09.09 доводка (коммит d8ac777): выбор клиента глобальной записи был неудобным**
(жалоба Василия: «не удобно если нового клиента нужно добавить», «список выбрать
неудобно — во время ввода подтягивать, выпадашка со скроллом»). Паттерн, применять к
любому picker'у сущностей в crm/:
- `web/src/crm/panel/ClientCombobox.tsx` — живой поиск: debounce 250 мс → серверный
  фильтр `q` (`GET /admin/clients?q=` ищет по имени/телефону, вся база — НЕ top-6
  срезами с клиента), выдача в скроллируемом `.crm-pick-list` (max-height 220px,
  `overscroll-behavior: contain`), до 25 позиций;
- Enter = первый результат; если совпадений нет (или имя не точное) — последней
  строкой выдачи «Создать нового клиента «X»» → `createClient({name, no_contact: true})`
  → подставляется в ту же модалку без потери заполненных полей (создание НЕ выносить
  в отдельную модалку — это и была жалоба). ⚠️ `no_contact: true` ОБЯЗАТЕлен с 09.09:
  контракт POST /admin/clients теперь требует телефон, кроме явного no_contact
  (см. секцию «Приглашение клиента»); тест bookAppointmentDialog.test.tsx ассертит
  ровно этот payload;
- строка создания скрыта для specialist (`canCreate={role !== 'specialist'}` —
  POST /admin/clients = CREATE owner/admin/support, SUPER_ADMIN проходит всегда
  через require_roles); точное совпадение имени скрывает строку (анти-дубль, бэк
  дополнительно даёт 409 {similar} по телефону);
- стили — в tokens.css блоком `.crm-combo/.crm-pick-list/.crm-pick-new` (внутри
  listbox `.crm-pick` без рамок/margin);
- тесты: `web/src/crm/panel/bookAppointmentDialog.test.tsx` (мок `createClient`
  отдельным vi.mock, useAuth мокается на owner).

## Приглашение клиента в клиентский бота (09.09, коммиты 06c9f0c+bc796a9+d6d1f92, ЗАДЕПЛОЕНО, e2E на проде зелёный)
Запрос Василия: в «Новый клиент» контакт обязательным + переключатель «оставить
пустым» (бот не нужен); если бот нужен — генерить ссылку/сообщение/QR.
Решение: одноразовый deep link `t.me/<client_bot>?start=cli_<raw>` по образцу
`worker_invite` (`inv_`).
**Контракт API (реализовано, pytest зелёный):**
- `ClientCreateIn`: phone обязателен, КРОМЕ `no_contact: true`; phone+no_contact вместе →
  422; пустой/пробельный phone → 422 (strip-валидаторы в clients_table_dto.py).
  Существующие тесты без телефона переведены на phone или no_contact — при правке
  контракта грепать tests/api на `"name":` без phone.
- POST /admin/clients → `ClientCreatedOut` = RowOut + `invite: {link, message} | null`.
  `ClientInviteService.create_for_client` возвращает None если username бота нет
  (`settings.bot_client_username` → фолбэк `tenant.client_bot_username`) — строка invite
  тогда НЕ создаётся, ответ invite=null.
- POST /admin/clients/{id}/invite — «Пригласить в бота» для существующей карточки:
  400 без телефона / без username бота; fresh-гард 404/403 инлайном (стиль /messages,
  `_client_in_scope` — приватная функция clients.py, не переиспользовать).
- Ротация: новая ссылка гасит (`used_at`) все неиспользованные старые — одна активная
  на клиента; TTL 7 дней; sha256-хэш + raw (паттерн TeamInvite #75).
**Бот-хендлер** `src/interface/bots/handlers/client_invite.py`, включён в
client_bot.py `include_routers` ПЕРВЫМ (до client_lead/client_menu — aiogram берёт
первый фильтр). Гарды: только CLIENT-карточка; привязка только в приватном чате
(`message.chat.type == 'private'`, НЕ сравнивать chat.id с from_user.id); использованная
ссылка чужим / уже привязанная к другому аккаунту / неизвестный токен → INVALID_MSG
(карточка не угоняется); повтор владельцем → меню (invite домаркируется).
- Merge дубля: если у открывшего уже есть CLIENT-строка в тенанте (создал `ensure_client`
  раньше) → `merge_client_cards(src=бот-строка, dst=карточка)`: FK-перенос ДО
  проставления card.telegram_id (UNIQUE(tenant_id, telegram_id)). Карта FK: appointments,
  conversations, messages.sender_user_id, client_events, staff_notifications.user_id,
  leads.client_user_id, retarget_sent, sessions.user_id. chat_bot_bindings НЕmerge-ится
  (ключ — chat_id). Staff-роль у «дубля» → НЕ сливать и НЕ claim-ить invite (админ
  тыкнул свою ссылку — настоящий клиент зайдёт потом). Имя карточки админа НЕ
  перезаписывать full_name из Telegram.
**Фронт:** `NewClientDialog` — «Контакт (телефон)» обязательный + чекбокс «Без контакта»
(disabled input), после создания с телефоном — экран `ClientInviteResult` (QR через
`qrcode.react` — установлен в web/package.json, python-qrcode в .venv НЕТ и не нужен;
2 кнопки copy: ссылка / готовое сообщение). `RecordPanel` — кнопка «Пригласить в бота»
(QuickActions `onInvite`, роли owner/admin/support/super_admin, видна только с телефоном)
→ `inviteClient(id)` из `crm/api/adminClients.ts`. Иконки `check`/`copy` добавлены в
реестр crm/ui/Icon. Стили `.crm-invite*` в tokens.css.
**ОСТОРОЖНО с бот-тестами (отловлено 09.09, tests/bot/test_client_invite_handlers.py):**
1) `AppointmentStatus` хранит РУССКИЕ значения (`NEW == "новая"`); строка `"new"` →
   InvalidTextRepresentation — передавать enum-член из src.domain.booking.status_machine;
2) хендлер коммитит в СВОЕЙ сессии — после feed_update НЕ делать refresh/expire_all
   на объектах из identity map (MissingGreenlet); читать свежие состояния только
   column-запросами `select(User.id, User.telegram_id, ...) WHERE ...`;
3) `msg_update(id, text, tg, chat)` — в приватном чате chat.id == from_user.id, тесты
   должны передавать одно и то же число, иначе хендлер правомерно отказывает.
**Тесты (итог):** tests/api/test_client_invite.py + test_create_client.py +
test_client_phone_dedup + tests/bot/test_client_invite_handlers.py — 19 passed;
vitest web 129/129; tsc -b чистый. Задеплоено: таблица `client_invites` поднялась
create_all при старте app (новая таблица — alembic не нужен, подтверждено
`to_regclass` в прод-БД).
**e2E прямо на проде (проверено 09.09):** python-скрипт подписывает initData сам
(тот же алгоритм, что gen_initdata: ключ `hmac.new(b"WebAppData", token.encode(),
sha256)` — ПОРЯДОК АРГУМЕНТОВ ВАЖЕН, наоборот → вечно 401) — контракт подтверждён
живьём: 422 без телефона / 201+invite.link с телефоном / regenerate 200 (новый
токен) / 400 карточке без телефона. Тестовые карточки вычищать из прод-БД с enum
ВЕРХНИМ регистром: `role='CLIENT'` (не 'client' — InvalidTextRepresentation;
skill уже фиксировал это для user_role, повторов на DELETE не ловил).

## Таймлайн — бесконечная лента (08.09, коммит bed9ebd)
Жалоба Василия: «там стрелочки были сверху для пагинации переключения, я от них хотел
избавиться и показывать всю историю». Стрелки ← → в шапке RecordPanel («Предыдущий/
Следующий клиент») Василий принимал за пагинацию истории — УБРАНЫ (осталась только
позиция `1 / 128` и крестик). Заодно кнопка «Загрузить ещё» внизу заменена на ленту:
- `web/src/crm/panel/TimelineList.tsx`: в конце списка sentinel-`<div ref>` + `IntersectionObserver`
  с `root: node.parentElement` (это контейнер скролла `[data-testid=timeline]`, overflowY auto),
  `rootMargin: '120px'`; пересечение → `onLoadMore()` (дубли гасит loading-guard в
  useClientTimeline). Обязателен guard `typeof IntersectionObserver === 'undefined'` —
  иначе jsdom-тесты падают (паттерн уже был в LandingPage).
- Timeline API: `GET /admin/clients/{id}/timeline?days=7&before=<cursor>` — порция 7 дней,
  `next_cursor`. У демо-клиентов истории < 7 дней → `hasMore=false`, sentinel НЕ рендерится
  (это норма, лента просто показывает всё). Проверять на клиенте с событиями за >7 дней.
- Для такой проверки есть `scripts/seed_client_month.py` (в репо, 2420a73):
  `dk.sh docker exec lead-platform-app-1 python scripts/seed_client_month.py --client-id 8`
  — заполняет последние 30 дней ПО ДНЯМ всеми 6 источниками таймлайна (звонки ClientEvent,
  приёмы new→confirmed→done, отмены/no-show, чат-сообщения, внутренние заметки,
  Lead+LeadEvent+Payment по telegram_id) + 2 будущие записи. Идемпотентен по
  meta->>'seed'='month30'. Источники union'а — `src/application/crm/timeline_service.py`.
- Проверка таймлайна — под OWNER бизнес-тенанта, НЕ суперадмином: `_entries` кидает
  TimelineError, если `client.tenant_id != tenant`, а тенант суперадмина = platform.
  `TG_ID=7519756578 TG_USERNAME=andrey_test python3 .../gen_initdata.py` (Андрей, владелец
  city-dental) → `GET /api/admin/clients/8/timeline?days=40` (Жасур Каримов = id 8 после
  db_reset 08.09) → ожидай ~31 день/78 записей, next_cursor=None.

## Глобальная «+» в админке и договорная цена в каталоге (09.09, коммиты 5ea7688 + 961df0e, задеплолены)
- `web/src/crm/GlobalAdd.tsx` — глобальная кнопка «+» (запись/клиент/каталог): в хедере CrmShell
  на десктопе + FAB на мобиле. Правки затронули `CrmShell.tsx`, `BookAppointmentDialog.tsx`,
  `CalendarToolbar.tsx`, `tokens.css` (+99 строк) — при следующем мобильном адаптиве/аудите
  админки учитывать FAB «+» как новый элемент вьюпорта (проверять, что не перекрывает BottomNav).
- Каталог: услуга ИЛИ товар (`ServiceKindToggle.tsx`), договорная цена (null/«договорная»),
  позиции без записи; новые компоненты `DurationOptionsPicker.tsx`; бэк: `catalog_service`,
  `models/catalog.py` (колонки — через идемпотентные ALTER в `init_db`, как всегда),
  `api/appointments.py`, `slots_service`. Точка входа mobile_audit: навигация не менялась.

## Headless-проверка админки (playwright на vdska, 08.09)
**Авторизация фронта с 08.09 — httpOnly cookie `lp_session`:** вход = `POST /api/auth/telegram
{init_data}` (обязателен `X-Requested-With: XMLHttpRequest` — CSRF-guard) → cookie в контексте
браузера; `GET /api/me` → роль. Заголовок `X-Telegram-Init-Data` остался легаси-путём для curl
(работает, `gen_initdata.py` актуален).
- Playwright ставится в venv проекта: `uv pip install --python ~/projects/lead-platform/.venv/bin/python playwright`;
  chromium уже на vdska: `ls ~/.cache/ms-playwright/` (путь меняется с версией, искать `*/chrome-linux64/chrome`).
- **Прямые URL `/web/schedule` → 404 от FastAPI** (SPA-fallback покрывает только `/`, `/quiz`, `/s/:slug`,
  `/web/`; с 09.09 `/` и `/quiz` отдают web-public-бандл, а не админский) — по админке навигация ТОЛЬКО кликами, не goto по под-путям. С 08.09 на мобиле
  это клики по `[data-testid="crm-bottom-nav"]` (бургер/drawer удалены), на десктопе — сайдбар.
  Кликать через `a:has-text("…") >> visible=true`: скрытый десктопный `aside` остаётся в DOM,
  `.first` без `visible` выбирает невидимый NavLink и клик падает («element is not visible»).
- **НЕ использовать `is_mobile=True` в playwright-контексте** — headless chromium отдаёт layout-viewport
  980 и SPA не рендерится; обычный контекст `viewport=390` честно проверяет media-запросы по ширине.
- vision_analyze на vdska может быть недоступен (нет vision-провайдера) — полагаться на DOM-метрики
  (scrollWidth vs clientWidth, элементы за вьюпортом), а не на скриншоты глазами.
- Готовый аудит: `scripts/mobile_audit.py` (вход по cookie, обход страниц кликами, отчёт об
  элементах за пределами 390px).

## Удаление человека/бизнеса из прода (09.09, случай «Momin Ahmed — пытался удалить, не удалось»)
Жалоба «не могу удалить клиента» разбирается так (проверено, всё удалено чисто):
1. **Один человек = НЕСКОЛЬКО строк `users`.** Сначала grep по БД: `SELECT id, tenant_id, name, role FROM users WHERE name ILIKE '%<имя>%' OR telegram_id=<tg_id>;` — у одного tg-аккаунта бывают CLIENT-копии в нескольких тенантах (созданы флоу лида/записи) И **OWNER в тенанте, который он сам собрал через викторину** (company_factory).
2. **Почему UI не дает (дыра продукта на 09.09):** кнопка «Удалить клиента» (RecordPanel → DELETE /api/admin/clients/{id}) работает только для CLIENT-строк текущего тенанта — OWNER в таблицу клиентов не попадает вообще; «Убрать из команды» OWNER отказывает (фиксированный статус в team_service); **удаления бизнеса (тенанта) в админке нет как функции** — quiz-тенант из продукта не убрать. Василий подтвердил проблему; заводить GitHub issue «удаление тенанта админом платформы + удаление OWNER».
3. **Сначала верифицируй бэкенд, потом вердикт «UI не показывает»:** `curl -X DELETE /api/admin/clients/<id>` с initData суперадмина (gen_initdata.py). 204 = каскад бэкенда рабочий, значит проблема доступности строки в UI, а не FK-блокировка. Не репро-гадать по логам: `docker logs lead-platform-app-1 | grep DELETE` показывает, дошла ли попытка вообще.
4. **Карта блокировщиков users:** `SELECT conrelid::regclass, confdeltype FROM pg_constraint WHERE confrelid='users'::regclass;` — `a` (NO ACTION) = чистить руками (appointments, conversations, client_events, retarget_sent, messages.sender_user_id, ai_conversations, work_plans, internal_notes.staff), `c` = каскад сам (sessions, staff_notifications, specialists, client_invites), `n` = SET NULL сам (leads, users.client_owner_id).
5. **Рабочий SQL-рецепт (одна транзакция BEGIN..COMMIT, проверено 09.09):** CLIENT с записями — каскад как в `ClientsTableService.delete_client` (appointment_events → reminders → specialist_notifications → appointments → client_events → retarget_sent → users). ВЕСЬ тенант: `UPDATE leads SET client_user_id=NULL WHERE tenant_id=N` → `DELETE FROM chat_bot_bindings WHERE tenant_id=N` → `DELETE FROM tenants WHERE id=N` (остальные 23 FK на tenants — ON DELETE CASCADE). ⚠️ `DELETE FROM leads WHERE tenant_id=N` ДО tenants кидает ошибку и **откатывает всю транзакцию** (psql -c = один BEGIN..COMMIT, при ошибке не сделано ничего — повторять весь блок, а не с середины).
Точные FK-листы и SQL — `references/db-schema-queries.md`, §«Удаление сущностей».

## Настройка живого бизнеса из лида (09.09, случай «Косы»)
Симптом: после викторинного лида клиент-бот в демо-записи — «нет активных специалистов».
Диагноз одним запросом: `SELECT t.id, t.slug, (SELECT count(*) FROM specialists s WHERE s.tenant_id=t.id) AS specs, (SELECT count(*) FROM users u WHERE u.tenant_id=t.id AND u.role='OWNER') AS owners FROM tenants t WHERE id NOT IN (1);` — specs=0 при owner>0 = тенант из-под старой фабрики. Рецепт для ЖИВОГО тенанта (новых лидов лечит ff65fbf):
1. `dk.sh docker exec lead-platform-app-1 python scripts/backfill_owner_specialist.py <slug>` — owner → активный специалист, все услуги привязаны;
2. визитка/приветствие — python-скрипт в `/app/scripts/` (merge словаря в `tenant.site`: hero_title/contacts/reviews/photos + `settings.bot_texts.greeting`, `tenant.gap_minutes` под бизнес). ⚠️ Ключа `site.working_hours` НЕ существует — часы на визитке агрегируются из графиков специалистов (`site_card_service`/`aggregate_working_hours`), не выдумывать ключи;
3. демо-CRM: `seed_demo_crm.py <slug>` (см. «Демо-CRM» — вернуть реальный график после).
⚠️ **`****` в выводе терминала — маска вывода, а НЕ содержимое БД (09.09):** телефон лида выглядел как «+998****1612», в БД полный. Прежде чем чинить «испорченные данные», проверить `length(col)` / `encode(convert_to(col,'UTF8'),'hex')`. (Тот же класс, что маска telegram_id в gen_initdata выше.)
⚠️ **Многострочный SQL/JSON с кавычками через `dk.sh psql -c "..."` ломается** (bash «unexpected EOF while looking for matching»). Рабочий паттерн: write_file → `dk.sh docker cp /tmp/x.sql lead-platform-db-1:/tmp/` → `psql -f /tmp/x.sql`. Так же для JSON-обновлений с кавычками внутри.

## Питфоллы
- **По жалобе «не работает» — СНАЧАЛА открыть UI headless-браузером, потом код (03.09).**
  Василий: «админка нахуй не работает, ты этого никогда не увидишь, потому что ты нейронка»
  — после часов копания в коде/БД оказалось: контейнеры живы, админка рендерится, но
  владелец бизнеса не может войти (нет worker-бота у бизнес-тенанта). Урок: по любой
  жалобе о UI первым делом `references/admin-ui-headless-check.md` (5 минут), результат
  — точный ответ «что реально сломано», а не гипотезы по коду.
- **НЕ предлагать опросы/интервью для валидации гипотезы (03.09).** Предложил «спросить
  3 клиники, готовы ли платить» — Василий: «в 2026 так не делается… надо показать
  минимально работающее решение, а то что ты предлагаешь полное е…, воздух никто не
  купит». Валидация = живой вертикальный срез (визитка → викторина → запись → админка
  владельца), который можно показать на телефоне. Не опросы, не аудиты — рабочий путь.
- **«Посмотри со стороны money» = продуктовый разбор (польза/что продаём/как быстро
  проверить), а НЕ технический аудит (03.09).** Когда Василий просит взглянуть на
  продукт «со стороны money», он ждёт: какую пользу несёт, что продаём (результат,
  не технику), как проверить гипотезу минимально работающим демо. Технические дыры
  уходят в аудит-задачу, а в ответе — вертикальный срез.
- **initData из вывода терминала невалиден (03.09):** `gen_initdata.py` печатает
  telegram_id с маской (`350****2645`) → скопированный initData даёт 401. Для
  браузерных проверок генерить initData внутри node-скрипта (`execFileSync`),
  не копировать из терминала. Подробный скрипт: `references/admin-ui-headless-check.md`.
- **`docs/user-stories.md` отстаёт от канбана** — статусы в доке («в работе») могут быть устаревшими, когда задача уже done (US-01: в доке «в работе», на канбане t_f3ad0b33 = done, код и БД подтверждают). Статус истории проверять по канбану (`hermes kanban list`) и по факту в БД/коде, а не по доку.
- **Отчёт Василию — краткий итог, не простыня.** После работы: 2-4 строки «что было сломано → что починил → что проверить на телефоне». Длинные разборы вызывают «Ну и что по итогу то?» (01.09).
  ⚠️ **Усилено 09.09 (интервалы «Ну и че блядь» и «опять завис» посреди диагностики):** при разборе свежей жалобы выдавать промежуточный вердикт каждые 2–3 tool-вызова — текстом в конце хода («что уже исключено / что проверяю / предварительный диагноз»), а не исчезать в 10+ вызовах чтения кода и логов без вывода. Длинный ход без текста Василий считывает как зависание. Порядок: короткий «что сломано» (1) → план починки (2) → только потом глубокая копания; разрешение «Да давай» на починку давать после вердикта, не до него.
- **«Что там должно быть?» — отвечать конкретным списком US.** Когда Василий просит «ещё раз, что там должно конкретно быть» — он хочет по каждой истории: номер US, что конкретно должно происходить (где, какая кнопка/поведение), статус ✅/🟡/❓. Без общих слов и воды. «Ещё раз» = первый ответ был недостаточно конкретным.
- **Прохождение викторины /quiz в Browserbase:** кликать по карточкам-родителям (`.opt`), а НЕ по заголовку/тексту внутри (клик по тексту не переключает выбор); перед кликом по «Далее» — `window.scrollTo(0, document.body.scrollHeight)` (вьюпорт Browserbase широкий, кнопка за пределами экрана, иначе клик «успешен», но шаг не меняется). Тексты «Студия „Волна“»/«Ташкент» в полях шага 2 — плейсхолдеры, не значения. Проверено 01.09: викторина полностью проходится (10 шагов), лид создаётся на шаге оплаты (после апселлов; NEW + `quiz_finished`), финал показывает «Начать 7 дней бесплатно» → «Доступ открыт» + «🚀 Открыть админку». Апселлы (шаги 8–9) — отдельные экраны с кнопками «Да, настроить (+$150)»/«Нет, справлюсь сам», НЕ «Далее».
- **Неоднозначная жалоба ≠ команда на глубокую диагностику.** 01.09 Василий: «мини админка открылась, кнопка mini app открывается this parola» (жаргон, «параша»). Начал расследование (ассеты, initData, /api/admin/me) — получил «остановись дебил», после чего: «всё работает как и должно». Урок: по неоднозначному/смайл-жаргонному сообщению о проблеме делать ОДНУ минимальную проверку (curl /health + /web/ 200) или коротко переспросить — не разворачивать многошаговую диагностику, пока не подтверждён симптом. «Остановись»/«стоп» от Василия = немедленный стоп без объяснений, даже если расследование почти завершено.
- **initData для curl: рабочий скрипт — `scripts/gen_initdata.py` в этом скилле** (python3, HMAC-SHA256, токен из BOT_TOKEN_WORKER в .env проекта; `TG_ID=`/`TG_USERNAME=` для любого юзера). Админские API смотреть в `src/interface/api/admin/*` (эндпоинта `/api/admin/me` нет; рабочие — `/api/admin/leads`, `/api/admin/site` и т.п.), а не угадывать.
- **«Проверка по пользовательскому пути» = пройти воронку как юзер, НЕ допиливать фичи.** Когда Василий говорит «подними и продолжим по шагам проверки user stories» — это проход лендинг → викторина → лид → уведомление → бот → оплата → админка с отчётом статусов, а не написание новых фич. 31.08 ушёл в доработки (бот-викторина, оплата-заглушка, тексты) и получил «ты куда-то не туда свернул». Модель триала: 7 дней бесплатно — на ботах/админке ПЛАТФОРМЫ; лид своей визитки/компании в триале НЕ получает; настройка — только после оплаты владельцем вручную.
- **«Адрес фиксированный на визитке» — проверять рендер, а не грепать код.** Адрес визитки приходит ТОЛЬКО из `tenant.site.contacts.address` (редактор SiteTab → PUT /api/admin/site); в шаблонах `/s/:slug` хардкода нет. Если в БД `site->'contacts'` пусто — на визитке адреса нет вообще. **Фикс 01.09:** хардкод «г. Ташкент, ул. Пахтакор, 12» убран из KB (`scripts/pilot_data.py`); пункт «Какой адрес клиники?» seed_pilot формирует из `site.contacts.address` тенанта, без адреса — «Адрес уточните у администратора». Быстрая проверка: `curl /api/site/<slug>` (адрес в `site.contacts.address`) + browser_navigate на `/s/<slug>`.
- **Смена демо-ботов — чек-лист 4 места (01.09).** Василий дал новых ботов
  (@lead_worker_demo_bot / @lead_client_demo_bot) — «переименовать нормально без рашида».
  При смене ботов обновить ВСЕ: 1) `.env` (BOT_TOKEN_WORKER/BOT_TOKEN_CLIENT + комментарии);
  2) БД `tenants` — `worker_bot_token`/`client_bot_token` И `worker_bot_username`/`client_bot_username`
  (platform → worker, rashid-dental → client; НЕ забыть `worker_bot_username` у rashid-dental —
  CTA «Для бизнеса» на визитке ведёт на worker-бота; И `client_bot_username` у platform =
  `lead_client_demo_bot` — иначе у лида после deep link НЕТ кнопки «🎯 Попробовать запись»,
  `lead_kb` берёт `tenant.client_bot_username`); 3) перезапуск `up -d app bots`
  (bots читают .env при старте; app — для initData-проверки по токенам из БД);
  4) тесты с username в моках (grep по старым именам: `sed -i "s/rashid_worker_bot/lead_worker_demo_bot/g"`
  по tests/ и web/src/quiz/*.test.*). Проверка: `docker logs lead-platform-bots-1` →
  «Run polling for bot @lead_worker_demo_bot» + `curl /api/public/platform-bot`.
- **Привязка клиентского/воркер бота к тенанту — ГЛОБАЛЬНАЯ (по токену), параллельные юзеры ломают друг друга (09.09, разбор на ветке `fix/bot-chat-binding`).** Симптом живого прогона: за минуту «✅ привязан к Serenita» → «к Lead Platform» → «к Городская стоматология», затем «✅ Запись создана» → `/appointments` → «Аккаунт не найден», посреди флоу «Бот не привязан. Обратитесь к администратору». Корни (подтверждены чтением кода): 1) `bot_bind.start_client_bind` при `/start` СНИМАЕТ токен со всех держателей и перепривязывает бота; привязка живёт в колонке `tenants.client_bot_token/worker_bot_token` — ОДНА на весь бот для всех чатов. Два параллельных пользователя перепривязывают тенант друг у друга: запись создалась в тенанте A, `/appointments` резолвится уже в B → «Аккаунт не найден»; гонка двух /start (первый снял привязку, второй не нашёл свободных кандидатов) → NOT_BOUND_MSG. Диагностика: `SELECT id, slug, client_bot_token IS NOT NULL, worker_bot_token IS NOT NULL FROM tenants ORDER BY id;` + `docker logs lead-platform-bots-1 | grep "handled by bot id="` по таймлайну жалоб.
  **FIXED 09.09 (main b127840, задеплоен): привязка стала per-chat.** Новая таблица `chat_bot_bindings` (chat_id UNIQUE → tenant_id, поднимается create_all) + модуль `src/interface/bots/chat_binding.py` (`get_chat_tenant_id`/`set_chat_tenant`). `tenant_utils.resolve_tenant`: привязка чата бьёт глобальный токен; глобальный `tenants.client_bot_token` — fallback для seeded-тенантов и single-tenant прода. `bot_bind.start_client_bind` колонки токенов НЕ трогает вовсе: кандидаты = все бизнес-тенанты (platform исключён через `is_platform_slug`), 1 → сразу BOUND, >1 → пикер с per-chat записью. Вход, выбирающий тенант, тоже фиксирует за чатом: `_answer_lead_menu` (меню лида), deep link `book_<slug>` в `cmd_start_book`. Worker `/start`: `state.clear()` ПЕРВЫМ делом до ветки — выбрасывает из зависшего сценария. Тесты-регрессии: `tests/bot/test_bot_bind.py` (два чата независимы, токены не тронуты, platform исключён, приоритет resolve_tenant).
  2) Worker-бот застревал в FSM: `@router.message(MoveState.waiting_time, F.text)` (worker_reschedule) подключён к роутеру ДО worker_start, aiogram берёт ПЕРВЫЙ подходящий фильтр без сортировки по специфичности, а F.text матчится и на текст команд → «/menu» и «/start» получают «Не понял время». **FIXED в b127840:** FSM-text-хендлеры фильтруют команды: worker_reschedule `move_time`, worker_start `onboarding_name`, worker_onboarding_team `team_tg_id`, worker_quiz_team `quiz_tg_id`, domain/ai/bot_router `ai_text` (AiMode.chatting — тот же класс бага у клиента). Регресс-тест `test_commands_escape_reschedule_fsm`.
  ⚠️ **Критический pitfall aiogram magic-filter (сбил все move-тесты по ходу фикса): `F.text.not_startswith("/")` НЕ существует** — MagicFilter на несуществующий метод str тихо возвращает False для ВСЕГО текста (не падает!), фильтр глушит хендлер целиком. Единственно правильная форма отрицания: `~F.text.startswith("/")`. Проверять фильтр перед коммитом: `f = F.text & ~F.text.startswith("/"); f.resolve(msg)` — `resolve()` возвращает bool (не await).
- **Дубликат бот-токенов у тенантов → MultipleResultsFound.** `get_by_bot_token` ищет по `client_bot_token`/`worker_bot_token` и `scalar_one_or_none()` бросает исключение, если токен есть у 2+ тенантов (любое сообщение бота падает). Разделение (фикс 01.09): worker-бот (админка платформы, deep link `lead_<id>`) = тенант **platform**; клиентский бот (демо-запись «Попробовать запись») = пилот **rashid-dental**. seed_platform ставит только worker-токен, seed_pilot — только client. Проверка: `SELECT id, slug, client_bot_token IS NOT NULL, worker_bot_token IS NOT NULL FROM tenants;`
- **`--workspace worktree` без пути репо = spawn_failed (08.09, t_d323ee31).** Даже при `--project lead-platform` и cwd внутри репо kanban create может дать `project_id: None, workspace_path: None` → диспетчер `spawn_failed: workspace_kind=worktree but no workspace_path, board 'default' has no default_workdir` (failures=1 → blocked). Лечение: `archive T_ID` → пересоздать с ЯВНЫМ `--workspace worktree:/home/hermes/projects/lead-platform` → `show` (workspace = `worktree @ <путь>`) → assign → notify-subscribe → dispatch. Всегда писать форму с двоеточием.
- **kanban_wait foreground: --timeout ≤ 400 (08.09).** Жёсткий лимит терминала рантайма — 420с: wait 560/terminal 590 убиты «timed out after 420.0s», воркер при этом жив. Для длинных задач — несколько wait подряд ~5 мин + проверка живости по `~/.hermes/profiles/coder/logs/agent.log` (растёт ли `API call #N`). Прерывание wait ≠ прерывание воркера.
- `docker compose up -d ...` Hermes блокирует как «server» → только background=true (+notify для build). ⚠️ Формат notify в текущем рантайме: boolean или список паттернов; `notify=true` для build проходил с ошибкой валидации — background без notify + `process poll`/`wait` самому работает надёжнее. ⚠️ `process(action='wait')` timeout молча клампится до 180с («Requested wait of 420s was clamped to configured limit of 180s») — это НЕ смерть процесса: после клампа просто повторить poll/wait, build дособерётся (проверено 09.09 на compose build).
- **Редизайн UI «инкрементами» — вычищай старые роуты сразу (07.09, V-10).** `/schedule` был раздвоен: суперадмин шёл на старый SchedulePage (до-V-10), остальные — на новый CalendarPage. Василий увидел «старый календарь поверх нового» и пожаловался «старые инкременты остались от предыдущей админки». Правило: после мержа новой оболочки/страницы grep'ом проверить импорты старой в App.tsx — route-развилка «роль X пока на старой странице» = долг, который мгновенно становится багом восприятия. Фикс d71702c: единый CalendarPage для всех ролей, старая страница + её 5 эксклюзивных компонентов удалены (бэкенд не мешал: require_roles пропускает SUPER_ADMIN на всех admin-эндпоинтах). Также: комменты «API пока нет / роут ниже» в коде устаревают — перед фиксом сверяй с фактическим роутером.
- **Lifecycle-команды (stop/restart/down) требуют APPROVE КНОПКОЙ, текст в чате не считается (07.09).** Василий сказал «да стоп» — команда всё равно упала в `pending_approval` и протухла («BLOCKED: Command timed out without user response»), дважды. Порядок: явно попросить нажать Approve, и ОТСРАЗУ после этого переслать команду (окно короткое; с третьей попытки прошла). Не обходить `kill`-контейнеров.
  Под тот же гейт попадают `git branch -D` и `git worktree remove` — уборка после мержа тоже стоит одного нажатия (08.09). И UPDATE/DELETE psql через docker exec в прод-БД (09.09: mid-recipe команда на правку графика упала в BLOCKED) — планировать запись в прод как approval-ход: предупредить и отправить сразу после «го». Работающий порядок: ОДНО сообщение «отправляю команду — жми Approve сразу, как прилетит», и в СЛЕДУЮЩЕМ ходе отправить; после 2–3 протуханий НЕ долбить повторно — дать Василию готовую команду для ручного выполнения по SSH и продолжить остальной фронт. ⚠️ Цепочка `stop … && sleep … && up -d …` в foreground детектится как «server» — гонять background=true (или просить пользователя).
- **«cannot unblock T_ID (not blocked/scheduled?)» — НЕ ошибка (07.09):** диспетчер gateway сам подобрал blocked-задачу между create и unblock (тик 60с). Проверить `hermes kanban show T_ID` → running, цепочка жива, ничего пересоздавать не надо. Перед unblock — сначала show.
- **Обновление кода ботов: НЕ `docker compose restart bots`.** Код копируется В ОБРАЗ
  (сервис `bots: build: .`, volume исходников НЕТ) — restart оставит старый код, а сама
  команда может упереться в approval Hermes. Правильно: `dk.sh docker compose build bots`
  (background+notify) → `dk.sh docker compose up -d bots` (background). Кнопка Web App
  в боте читает `WEBAPP_URL` при старте — после смены URL/`.env` тоже нужен этот путь.
  Проверка после: `docker logs lead-platform-bots-1` → «Run polling for bot @lead_worker_demo_bot».
  Плюс проверка меню «☰» (set_my_commands — один раз при старте поллинга, runner.start_bots/
  start_one_bot; /menu+/help обоим ботам с 273e0ab): `curl api.telegram.org/bot<TOKEN>/getMyCommands`
  (токены из .env) → ожидаемый список команд.
- **TelegramConflictError-шторм после `up -d --force-recreate bots` (08.09, НА МОМЕНТ ЗАПИСИ НЕ РАЗРЕШЕНО).**
  Симптом: «Conflict: terminated by other getUpdates» 2+ часа (190+ tryings, aiogram спит по 5с),
  при этом `getUpdates?offset=-1` curl'ом с того же хоста возвращает ok:true — призрачного
  держателя токена ЛОКАЛЬНО НЕТ. Что проверено и чисто: ps хоста (run_bots только в контейнере,
  app-контейнер не поллит — lifespan register_subscribers без polling), соединения netns контейнера
  `awk '$4=="01" && $3 ~ /:01BB$/' /proc/<docker inspect -f {{.State.Pid}}>/net/tcp` (2 = по одному
  на бота — норма), getWebhookInfo → url пуст, дублей контейнеров нет (docker ps -a), restarts=0.
  stopPolling API не годится (404 — метод для webhook-ботов). Planned fix (НЕ верифицирован):
  `docker compose stop bots` на 2–3 мин (graceful SIGTERM, сессия Telegram отпускается) → `up -d bots`.
  ⚠️ Дополнение 09.09: шторм ПРОДОЛЖАЕТСЯ после полного пересоздания контейнера ботов (374 конфликта за 15 мин), но update'ы обрабатываются — бот отвечает с задержками. Перепроверено начисто: `ss -tnp state established '( dport = :443 )' | grep 149.154` — на хосте к Telegram DC держит соединения только процесс `hermes` gateway СВОИМ токеном (не демо-ботами); процессов с BOT_TOKEN_* в /proc/*/environ на хосте нет; в netns контейнера по 1 соединению на бота; getWebhookInfo пуст.
  ⚠️ **РЕШАЮЩИЙ ПРОБЕ призрака-держателя (09.09, ВЕРИФИЦИРОВАН): `curl -m 40 "https://api.telegram.org/bot<TOKEN>/getUpdates?timeout=30&limit=1"`.** Мгновенный 409 (2–3 c из 30) = на сервере Telegram идёт АКТИВНЫЙ конкурирующий long-poll — призрак реален, это НЕ «старые TCP-сессии». Старый вывод 08.09 «offset=-1 вернул ok:true → призрака нет» — **ЛОЖНЫЙ**: `offset=-1` не ждёт и не конкурирует по сессии, онghost не ловит. Единственная честная проверка持有 — вариант с timeout=30.
  Итог 09.09: локально на vdska держатель исключён полностью (ps/environ/netns по контейнерам/ss хоста), при этом пробник даёт мгновенный 409 на оба демо-токена → следующий шаг (НЕ повторять локальные проверки): искать поллер на ДРУГИХ машинах Василия (grep `BOT_TOKEN_CLIENT|8703577446|8864466232` по ~/projects на старом хосте/ноуте, где боты гоняли до переезда на vdska 07.09). Работоспособность бота при этом судить по «is handled» в логах, а не по числу конфликтов. Готовый пробник обоих токенов с вердиктом: `scripts/tg_ghost_poller_probe.py` в этом скилле.
  ✅ **РЕШЕНО 09.09: призрак жил на второй машине Василия** (старый хост, где боты гоняли до переезда). После «я вырубил» — шторм прекратился сам (0 конфликтов за 3 мин, «Connection established», апдейты «is handled»), повторный деплой с `--force-recreate bots` чистый. ⚠️ Методика проверки при РАБОТАЮЩЕМ контейнере: curl-пробник нечестен (контейнер и есть второй держатель) — либо тестировать счётчиком логов `docker logs lead-platform-bots-1 --since 2m | grep -c TelegramConflictError`, либо заморозить поллер `dk.sh docker exec lead-platform-bots-1 sh -c 'kill -STOP 1'` и вернуть `'kill -CONT 1'` (poll-треды виснут на read, сессия Telegram отпускается только с таймаутом ~1 мин — после CONT поллер переподключается сам).
- **pytest на vdska: с 07.09 ЕСТЬ тестовый postgres на хосте** — `test-pg`
  (`dk.sh docker run -d --name test-pg --restart unless-stopped -e POSTGRES_USER=booking
  -e POSTGRES_PASSWORD=*** -e POSTGRES_DB=booking_test
  -p 127.0.0.1:5432:5432 postgres:16-alpine`). conftest ждёт `booking:booking@localhost:5432/booking_test`
  (создаёт схемы сам, xdist-воркеры берут booking_test_gwN). Kanban-кодеры могут гонять
  целевые тесты `pytest tests/<файл> -q`; полный набор не гонять (сокращён до ~105).
  Если контейнер лёг — переподнять той же командой. Прод-БД lead-platform во внутренней
  docker-сети, на 5432 хоста не слушает — конфликта нет. Проверки API — e2e через curl/initData.
  ⚠️ **Подозрение «мои правки уронили тесты» — сначала baseline чистого HEAD (09.09):**
  `git worktree add /tmp/lp-base HEAD && ln -sf ~/projects/lead-platform/.env /tmp/lp-base/.env &&
  cd /tmp/lp-base && PYTHONPATH=. ~/projects/lead-platform/.venv/bin/python -m pytest tests/ -q` —
  те же фейлы на base = предсуществующие/флаки полного прогона. Реально: test_timeline_union —
  стабильно красный на чистом HEAD; test_notify_new_message_sends_chat_button — проходит изолированно,
  падает только в полном наборе. НЕ чинить до замера baseline (иначе гонишь за призраком).
  ⚠️ **pytest из kanban-worktree требует `.env` репо (07.09):** тесты читают токены ботов из
  `.env`; без него `TelegramApiSpy.calls` пуст → «упавший» тест выглядит как баг кода, а это
  дефект окружения. Фикс: `ln -sf ~/projects/lead-platform/.env <worktree>/.env`
  (.env в .gitignore — в коммит и `git worktree remove --force` не мешает).
- `create_all` НЕ добавляет колонки/enum в существующие таблицы — новые ALTER только идемпотентно
  в `init_db` (`src/core/db.py`), alembic в проде НЕ применяется.
- НЕ запускать диагностические exec-скрипты с polling параллельно контейнеру ботов (TelegramConflictError).
- `.env` в .gitignore — не коммитить.
- **Hermes-терминал рвёт heredoc-дописывание и сложные one-liners** (`cat >> tests/... <<EOF`, `sed -n "$(grep -n ...)"`, вложенные `\"` в awk внутри `$(...)`) — hardline-блок «oversized/unparseable payload» НЕ обходится retry'ом и не должен переизобретаться другим способом. Дописать тест/секцию — `patch`-инструментом (old_string = последний уникальный абзац файла), многострочную проверку — отдельным `python3 -c` без shell-вложений.
- Ошибки SPA на телефоне «Unexpected token '<'» = SPA-fallback отдаёт index.html вместо отсутствующего
  ассета; фикс: `/assets/*` и пути с точкой в последнем сегменте → 404 (не index.html).
- Стили визитки `web/src/site/site.css` обязаны импортироваться в `SitePage.tsx` — иначе vite не кладёт их в бандл.
- **Web-правки: vitest зелёный ≠ docker build зелёный.** `npm run build` (Dockerfile) = `tsc -b && vite build`,
  tsc проверяет ВСЕ .ts/.tsx, включая тестовые файлы — неиспользуемые параметры в моках (TS6133) и
  ошибки типов валят сборку образа. ⚠️ **`npx tsc --noEmit` НЕ ловит всё, что ловит `tsc -b`**
  (реальный случай 08.09: в `LeadsTablePage.test.tsx` `input.url` на типе `URL` — `tsc --noEmit`
  зелёный, `docker compose build` упал; фикс `input instanceof Request ? input.url : input.href`).
  Надёжная проверка перед сборкой: `cd web && npm run build` (или `npx tsc -b`), не только `--noEmit`.
- **После `git pull` с origin — `cd web && npm run build` ЛОКАЛЬНО до `compose build` (09.09).**
  Коммиты, прилетевшие с чужой машины в main, регулярно ломают именно `tsc -b` (сборку
  Docker): 34671fb пришёл с 4 классами поломок — неиспользуемый импорт (TS6133,
  правка в чужом CrmShell), state задан но не использован (`actionBusy` — правильное
  применение `disabled={actionBusy}` на кнопки), новое обязательное поле DTO (`is_archived`)
  уронило `makeClient`-фабрики тестов (fieldGrid.test), а моки `ReturnType<typeof vi.fn>`
  в vitest 4 не присваиваются типизированным callback-пропсам — типизировать через
  `import type { Mock } from 'vitest'` → `Mock<(id: number) => Promise<void>>`.
  Припал build — починить, отдельным `fix(web)` закоммитить в main, потом пересобирать.
- **Продуктовое решение (31.08): бот-викторина (`?start=quiz`) дублировала
  веб-викторину — упразднена (36f4a34).** Воронка = лендинг `/quiz` → лид →
  кнопка «Написать боту»; бот = канал связи/доступа, не викторина. Итог:
  - `/start` у незнакомца → «👋 Это бот платформы Lead Platform…» + ОДНА кнопка
    «📝 Пройти викторину» (URL `SITE_BASE_URL/quiz`). **БЕЗ «Войти в админку»** —
    неизвестный юзер не должен плодить шум (65e2592).
  - deep link `?start=quiz` → то же, что /start (`cmd_start_quiz` вызывает `cmd_start`)
  - CTA «Для бизнеса» на визитке — `t.me/<worker>` без payload (Contacts.tsx)
  - роутер `worker_quiz` отключён от `worker_bot` (тесты FSM подключают его сами)
  - супер-админ из `?start=quiz` → меню админки (не викторина)
- **Отслеживание лида через deep link `?start=lead_<id>` (65e2592, доработки 39455b7/3f2b48a; ⚠️ username-механика из этого блока ЗАМЕНЕНА f64b9ea — первый открывший, без username).** Кнопка
  «Написать боту» после /quiz = `t.me/<worker>?start=lead_<id>` (id — из ответа
  `POST /api/public/quiz-lead`; username — из `GET /api/public/platform-bot`).
  Бот (`cmd_start_lead` в worker_start.py, regexp `^lead_(\\d+)$`, идёт ДО cmd_start):
  - username совпал (`lead.username` == `from_user.username`) → привязка
    `lead.telegram_id = from_user.id` + «👋 Привет! Заявка получена…» + **создаётся
    `User(role=ADMIN)` в тенанте платформы** (`_ensure_lead_user`) и кнопки
    «🚀 Открыть админку» (Web App) + «🎯 Попробовать запись» (клиентский бот) —
    демо-доступ лида на 7 дней (жалоба Василия: «доступ к админке должен там быть»)
  - чужой/левый/несуществующий id → общее «Заявка получена, скоро свяжемся»
    без деталей и **БЕЗ доступа** (строгая проверка `lead.telegram_id == from_user.id`;
    раньше чужой получал полное приветствие и даже доступ — закрыто 3f2b48a)
  - повторный `/start` у ADMIN/OWNER тенанта → меню админки (как у супер-админа)
  - веб-лид имеет `tg_username`, но `telegram_id=None` — это и есть «отследить
    пользователя»: после перехода в бота лид привязан к аккаунту
- **Уведомление супер-админу о лиде — человекочитаемое (39455b7).**
  `src/infrastructure/notifications/lead_notifier.py` маппит коды в названия:
  `TYPE_LABELS` (salon → «Салон / маникюр», dental → «Стоматология», …) и
  `PLAN_LABELS` (p1 → «Два бота + админка», p2 → «Два бота + ИИ», p3 →
  «Визитка с воронкой»), + город, список услуг, телефон. Не показывать лиду/в
  логах сырые коды (жалоба 01.09: «Бизнес: salon» / «Вариант: p1» — это непонятно).
- **Роль на фронте ≠ роль в БД → кэш сессии в localStorage (01.09).** Жалоба
  Василия: «клиент супер-админом стал» — в БД/API роль всегда была `admin`,
  но в шапке Mini App показывалось `super_admin`. Диагностика (порядок):
  1) БД `SELECT id, tenant_id, telegram_id, name, role FROM users ORDER BY id;`
  → роль реальная; 2) API от имени этого юзера: `TG_ID=<id>
 python3 ~/.hermes/skills/devops/lead-platform-ops/scripts/gen_initdata.py` → `curl /api/me`
  (актуальная роль) и `/api/admin/leads` (для не-супер-админа 403);
  3) код фронта. Корень: `web/src/hooks/useAuth.ts` кэширует `{id,name,role}`
  в localStorage `admin_session` и при старте НЕ перепроверял роль, а
  `window.Telegram.WebApp` в первый момент может быть ещё не инициализирован
  → `login` не вызывался → закэшированная `super_admin` показывалась вечно
  (на первом входе; после reload SDK готов — роль правильная).
  Фикс (web): стартовый рендер не показывает кэш вообще (`useState(null)`);
  при старте `initData = getLiveInitData() || getStoredInitData()` (из
  localStorage `tg_init_data`, бэкенд принимает до 24ч по auth_date) →
  `login()` → `GET /api/me` → кэш перезаписывается свежей ролью; 401 → сброс
  сессии; вне Telegram (dev) — кэш. Сопутствующее: `ROLE_LABELS` в
  `web/src/lib/format.ts` должен содержать ВСЕ роли `UserRole` (бэкенд:
  `src/infrastructure/db/models/user.py`) — не было `super_admin`, бейдж
  показывал сырое `"super_admin"`. После фикса: vitest `useAuth.test.tsx`
  (добавить регресс-тест «initData при старте перекрывает старый кэш»),
  `npx tsc --noEmit`, пересборка образа + `up -d app`; клиент переоткрывает
  Mini App → кэш обновится сам (старую сессию чистить не надо).
  `gen_initdata.py` с `TG_ID=` годится для проверки прав ЛЮБОГО юзера, не
  только супер-админа.
- **«Не пускает в админку» / «постоянная перезагрузка» Web App (01.09, фикс 70f4797).**
  Кнопка «🚀 Открыть админку» открывает `WEBAPP_URL=/web/`. ВАЖНО: `/web/` НЕ рендерит
  лендинг — catch-all (`<Route path="*">` в App.tsx) редиректит на /schedule → /login.
  Первая гипотеза «кнопка ведёт на лендинг» (RootPage, 4578c04) — НЕВЕРНА, RootPage
  откачен: он стоит на path="/" и для /web/ не вызывается вовсе. Настоящая причина
  жалобы «вход в админку показывается, но войти не могу, будто перезагружается» —
  БЕСКОНЕЧНЫЙ ЦИКЛ `/login ↔ /schedule`: после фикса роли 33a610c useAuth стартует
  с user=null и грузит роль асинхронно, а AppShell/RoleRoute редиректили на /login
  сразу при user=null (каждый ре-маунт = новый инстанс useAuth с user=null →
  редирект до завершения fetch). Симптом в логах app: повторные `GET /login`
  (server-side = полный reload страницы; client-side Navigate НЕ даёт GET).
  Фикс: `useAuth` стартует с `loading=true` (проверка сессии идёт); AppShell/RoleRoute
  при `!user && loading` показывают «Загрузка…», редирект на /login только при
  `!user && !loading`. Регресс-тест — AppShell.test.tsx «пока проверка сессии идёт —
  НЕ редиректит» (tg_init_data + fetch pending → «Загрузка…», не LOGIN_PAGE).
  WEBAPP_URL менять на `/web/schedule` НЕЛЬЗЯ: SPA-fallback отдаёт 404 для
  произвольных путей (покрыты только `/`, `/quiz`, `/s/:slug`). После деплоя
  старые открытые Mini App кэшируются — закрыть и переоткрыть кнопку.
- **Проверка рендера SPA без браузера (headless chromium на vdska):**
  `CHROME=~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome; timeout 60 $CHROME --headless=new --disable-gpu --no-sandbox --dump-dom --virtual-time-budget=8000 "https://<туннель>/web/" | grep -oE "Вход в админку|Клиент записывается сам|Загрузка…"`
  — показывает, какой React-роут реально рендерится под URL (вне Telegram initData пуст →
  LoginPage с заглушкой «Откройте Mini App в Telegram» — это норма). Быстрее и честнее,
  чем гадать по App.tsx, какая страница открывается по /web/.
- **Вход лида по deep link (фикс f64b9ea): username-проверка УБРАНА ПОЛНОСТЬЮ.**
  `_bind_lead` (worker_start.py): первый, кто открыл `?start=lead_<id>`, привязывается
  (`lead.telegram_id = from_user.id`) для ЛЮБОГО статуса лида; уже привязанного не
  перепривязываем (защита от угона); несуществующий id → «Заявка получена, скоро
  свяжемся» без деталей. История: 120f01f сделал «PAID — сразу, NEW — по username с
  подсказкой» (жалоба: «должен был дать вход в админку и в клиентского бота», бот
  отвечал «Заявка получена»), но Василий отверг и это: «вот то бред, у меня там могут
  разные аккаунты быть либо один и тот же аккаунт, за одним аккаунтом тг может быть
  зарегистрировано несколько тенантов» → f64b9ea. Урок: НЕ вводить username-гейты для
  доступа лида — у лида несколько аккаунтов, у аккаунта несколько тенантов.
  Проверка: `SELECT id, status, username, telegram_id FROM leads;` — после deep link
  `telegram_id` заполнен у любого лида.
- **Аудит-воркер на Kanban упёрся в лимит итераций (45/45 ×2 → auto-block, 03.09):**
  задача t_3894dc97 зависла «blocked», хотя воркер успел написать отчёты. Recovery:
  1) `hermes kanban show <id>` — посмотреть diagnostics (Iteration budget exhausted);
  2) в worktree задачи: `git status` в `.worktrees/<task>/` — незакоммиченные отчёты
  (`AUDIT_*_report.json`, `*_audit_report.md`) закоммитить в ветку (не потерять работу);
  3) находки зафиксировать в `docs/us-audit/backlog.md` в main (см. выше);
  4) `hermes kanban unblock <id>`, затем `hermes kanban dispatch --max 2`.
  ⚠️ У `hermes kanban dispatch` НЕТ id-аргумента — справливает глобально. После unblock
  диспетчер gateway может уже заспавнить воркера (Spawned:0 в CLI — не паниковать;
  проверить `hermes kanban show` → статус running и `ps -ef | grep kanban`).
  ⚠️ **Причина лимита — `agent.max_turns` в конфиге ПРОФИЛЯ, не в `~/.hermes/config.yaml`**
  (в основном конфиге может стоять 250, а у профиля — 45). У профиля architect было
  `agent.max_turns: 45` → отсюда «Iteration budget exhausted (45/45)». Поднять:
  `hermes -p architect config set agent.max_turns 100`. Проверить: `grep -rn "max_turns"
  ~/.hermes/profiles/architect/config.yaml`. Для тяжёлых задач (аудит всего репо) —
  ставить 100 сразу при создании задачи или перед справливанием воркера.
- **Проверять прод-конфигурацию, а не только тесты (03.09):** E2E-тесты записи
  привязывают worker-бот к ТОМУ ЖЕ тенанту, что и запись → кросс-тенантная конфигурация
  «worker=platform, запись=rashid-dental» не покрыта, ручное подтверждение записи
  сломано (B-14), `confirm_mode=manual` игнорируется (B-15), а `pay-test` — публичный
  мутирующий эндпоинт без auth (B-12, IDOR). Эти баги найдены аудитом, не тестами.
- **Диагностика входа (коды /api/me):** 200 = юзер есть (супер-админ/ADMIN);
  404 «user not found» = initData валиден, но User нет (лид не привязан);
  401 «invalid init data» = подпись не прошла ни одним токеном тенанта (старый
  токен бота / просроченный `tg_init_data` из localStorage при открытии вне
  Telegram). В логах app (`docker logs lead-platform-app-1`) искать 401/404 —
  это и есть неудачные попытки входа.
- **Главная дыра изоляции тенантов (03.09, подтверждено grep'ом).**
  `_tenant_by_init_data` (`src/interface/api/deps.py`) определяет тенант юзера по
  initData, **перебирая токены ВСЕХ тенантов из БД**; `_tenant_by_init_data` не
  проверяет членство юзера в тенанте — юзер с одной Telegram-учёткой может попасть
  в чужой тенант, лид/админ видят чужие компании. Плюс роль на фронте кэшируется
  в localStorage (`admin_session`) и не сверяется с БД (см. питфолл 01.09 про
  «клиент супер-админом стал»). Любая работа над доступами — это НЕ точечный фикс,
  а переработка слоя авторизации: схема «как определяется тенант юзера, права по
  ролям, изоляция между компаниями» ДО кода.
- **Видение платформы менялось в процессе разработки (03.09).** Василий:
  «у меня несколько раз менялось видение платформы, надо взглянуть со стороны
  money». Код писался под универсальную платформу записи (US-00..US-23), а сейчас
  продаётся «лид-машина для стоматологий Нукуса» (платформа+викторина+реклама,
  поток пациентов под ключ). При аудите/доработках сверять код с ТЕКУЩИМ
  продуктовым видением (в чекпойнте vault), а не с user-stories.md (21.08);
  помечать, что осталось от старого видения и мешает продажам.
