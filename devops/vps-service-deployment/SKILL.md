---
name: vps-service-deployment
category: devops
description: "Deploy and run long-lived services on a VPS: Telegram bots, tunnels, scrapers. Clone → configure → background → monitor."
---

# VPS Service Deployment

Deploying services (Telegram bots, web scrapers, API servers) on a Linux VPS. Covers the full lifecycle: repo discovery → clone → setup → configure → background → monitor.

## 1. Repo Discovery — check user's own repos FIRST

**GitHub install-script rot (proxy/VPN panels):** `bash <(curl -Ls https://raw.githubusercontent.com/...)`
URLs die often — GitHub periodically bans proxy repos (2024 wave), authors abandon
originals and users fork them under new names. BEFORE running any such installer,
verify the repo is alive:

```bash
curl -s -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com/OWNER/REPO/master/install.sh
# 404 → repo gone. Find the ACTIVE fork (check latest release via GitHub API)
# instead of debugging the old URL.
```

For x-ui/3x-ui specifically (which fork, install, update, GitHub-drop resilience,
local backup): see `references/x-ui-3x-ui-panel.md`.

When user asks about a repo by name (e.g. "скачай insta_flat_parser"), **do NOT start with public web search**.

```bash
# 1) Check user's own GitHub repos first
gh repo list --limit 30 --json name,owner,isPrivate 2>/dev/null || \
  curl -s -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/user/repos?per_page=30&sort=updated" \
    | python3 -c "import sys,json; [print(f'  {r[\"full_name\"]}  {\"private\" if r[\"private\"] else \"public\"}') for r in json.load(sys.stdin)]"

# 2) Check if it's already cloned locally
find ~/Projects -maxdepth 4 -type d -name "$REPO_NAME" 2>/dev/null

# 3) Only then fall back to public search
```

**Pitfall:** User may have the repo under a different account (`ogoclients` → `ogodevonline`) or pushed it during the conversation. Always check `gh repo list` before searching publicly.

## 2. GitHub Auth Check

```bash
# Check auth status
gh auth status 2>&1

# If fine-grained token without read:org — gh auth login --with-token fails.
# Workaround: use curl with token for API, git for clone (only need repo scope).
# Extract token from .env or git-credentials:
source ~/.hermes/.env 2>/dev/null
GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\\([^@]*\\)@.*|\\1|')
```

## 3. Python Project Setup

```bash
cd ~/Projects/Personal/GitHub/
gh repo clone owner/repo-name
cd repo-name

# Use uv (not pip — PEP 668 enforced)
uv sync

# Install Playwright browsers if needed
uv run playwright install chromium

# Create .env from user-provided variables
# ⚠️ Watch for special chars in values (quotes, $, etc.) — dotenv may misparse
```

## 4. Telegram Bot — First-Run Pitfalls

**"Chat not found" error:** When bot starts, it tries to send startup notification to `ADMIN_CHAT_ID` / `ADMIN_IDS`. If the admin hasn't started a chat with the bot yet, this fails with `TelegramBadRequest: chat not found`.

**Fix:** User must first write `/start` to the bot in Telegram. Only after that can the bot send messages to that chat_id.

**Multiple ADMIN_IDS:** If `ADMIN_IDS` has multiple users (e.g. `350262645,5400073449`), the bot tries to notify ALL of them at startup. Each user who hasn't messaged the bot yet gets "chat not found" — the error is non-fatal but noisy. Keep only `ADMIN_IDS=<your-id>` or ensure all listed admins `/start` the bot first.

**Restart gotcha:** After bot restart, previously sent `/start` commands may be consumed (update_id already acked). Tell the user to send `/start` again — the new instance will receive it fresh.

**Polling conflict — «Conflict: terminated by other getUpdates request» (урок 21.08.2026, lead-platform).** Если серверный бот в логах пишет `Failed to fetch updates - TelegramConflictError: ... make sure that only one bot instance is running`, а ручной `curl .../getUpdates?limit=1` при этом возвращает `{"ok":true,"result":[]}` (а НЕ 409) — кто-то ВТОРОЙ держит long-polling на этом токене. Частая причина: зависший тестовый/диагностический скрипт `dp.start_polling`, запущенный вручную (или второй инстанс бота), перехватил getUpdates — реальный бот не может получать апдейты. Диагностика: `ps aux | grep -E "polling|python.*(start_polling|build_.*_bot)"` — найти и убить лишний процесс; после этого перезапустить сервис бота. Признак НОРМЫ: с активным polling СВОЙ же `getUpdates` через API возвращает 409 Conflict (токен занят единственным инстансом). ⚠️ НО `getUpdates?limit=1&timeout=0` → `ok:[]` — НЕ доказательство «бот не слушает»: между long-poll запросами aiogram есть пауза, и мгновенный getUpdates проходит без 409 даже у РАБОТАЮЩЕГО бота (проверено 21.08.2026: клиентский бот отвечал пользователю полным флоу записи, а getUpdates давал ok:[] — ложный вывод «боты не стартуют» увёл диагностику не туда). Надёжный сигнал живости: `getWebhookInfo.pending_update_count` — растёт = бот НЕ забирает апдейты; 0 = работает (или 409 на свой getUpdates).\n\n**Диагностика «кто держит polling» при docker compose (урок 21.08.2026, lead-platform).** Если конфликт есть, а `ps aux` на хосте чист:\n1. Прерванные диагностические `docker compose exec`-скрипты (вручную запущенный `dp.start_polling` через exec, прерванный orphan recovery/Ctrl+C) ОСТАЮТСЯ ЖИТЬ В КОНТЕЙНЕРЕ и держат getUpdates → основной uvicorn в логах пишет `TelegramConflictError` для ОБОИХ ботов, хотя в коде старт ровно один раз. Проверка: `docker top <container>` — должен быть только основной процесс.\n2. Эксперимент stop-app (разделяет «локальный источник» vs «внешний»): `docker compose stop app` → подождать 3с → `curl getUpdates?limit=1&timeout=5`: `ok:[]` = источник ЛОКАЛЬНЫЙ (контейнер/хост); `409` = источник ВНЕШНИЙ (другой сервер/инстанс, перевыпуск токена в @BotFather).\n3. Minimal alpine-образы не имеют ps/ss/netstat — диагностика через /proc:\n   ```bash\n   docker exec <c> sh -c 'for p in $(ls /proc | grep -E "^[0-9]+$"); do echo \"$p: $(cat /proc/$p/cmdline 2>/dev/null | tr \"\\0\" \" \" | head -c 90)\"; done'\n   docker exec <c> sh -c 'awk \"NR>1 && index(\\$3,\":01BB\")>0\" /proc/net/tcp'   # :01BB = 443 (Telegram)\n   ```\n4. Правило: НЕ запускать тестовые polling параллельно с живым ботом; если прервал exec-процесс — сразу проверить `docker top`, что он умер. После чистки — `docker compose restart app` (или `up -d --force-recreate`, если менялся код/env).

**Служебный бот молчит на /start (урок 21.08.2026, worker-бот lead-platform).** Уведомительный/рабочий бот часто НЕ имеет `Command("start")`-хэндлера — он только шлёт уведомления и отвечает на callback'и. Пользователь жмёт /start → «бот не работает», хотя бот жив. Диагностика: токен валиден (`getMe` ok), `getWebhookInfo.url` пуст, а в коде нет хэндлера — проверь регистрацию роутеров в `build_*_bot` (`grep -n "Command(" src/.../worker_bot.py` → пусто). Неконфликтная проверка живости бота: `getWebhookInfo.pending_update_count` — растёт = бот НЕ забирает апдейты; 0 = работает. Фикс: добавить `/start` с приветствием («✅ Рабочий бот активен…»).

**DB cleanup for fresh start:**
```bash
rm -f ~/.insta_flat_parser/state.db  # or wherever state.db lives
```

**Tip:** Find the bot's username via API:
```bash
curl -s "https://api.telegram.org/bot$BOT_TOKEN/getMe" | python3 -c "import sys,json; print('@'+json.load(sys.stdin)['result']['username'])"
```

## 5. Cloudflared Tunnel Setup

**⚠️ Когда пользователь просит Telegram Mini App — cloudflared это ДЕЛИВЕРАБЛ, а не отложенная опция (урок 21.08.2026, lead-platform).** Пользователь жёстко отчитал: «стоп что за хуйня мне mini app нужен, нужно было настроить через cloudflare дибил» — после того как агент отдал вместо рабочей кнопки текст-ссылочный фолбэк («🔗 Админка: ...»). HTTPS-гейт кнопки (см. ниже) — это ЗАЩИТНЫЙ код (чтобы /start не падал на http://), но НЕ ответ пользователю. Если пользователю нужен Mini App: СРАЗУ ставь cloudflared (§5) и вшивай https-URL в `WEBAPP_URL` → rebuild → кнопка Web App появится сама (ветвление `startswith("https://")`). Порядок действий: 1) `curl .../cloudflared-linux-amd64 -o ~/.local/bin/cloudflared && chmod +x`; 2) `cloudflared tunnel --url http://localhost:8000` в background; 3) вытащить URL из логов (`trycloudflare.com`); 4) проверить `curl -s https://<url>/health`; 5) `WEBAPP_URL=https://<url>/web/` в .env → rebuild → конфликтов 0. Фолбэк-текст — только как временная страховка, пока туннель не поднят, не как финальное решение.

```bash
# Download binary (no sudo needed)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /tmp/cloudflared
chmod +x /tmp/cloudflared

# Start tunnel to local web app
/tmp/cloudflared tunnel --url http://localhost:8080
```

The tunnel URL appears in logs as `https://xxxx-xxx.trycloudflare.com`. Pass it to the service via `WEBAPP_URL` env var.

## 5b. Home Server Instead of a VPS (cost-saving)

When the user asks «хватит ли ресурсов / запустим здесь, чтобы не тратить деньги» — оцени честно (проверено 21.08.2026: lead-platform пилот, FastAPI + 2 aiogram-бота + APScheduler + Postgres 16):

- **Боты через polling работают без публичного IP**: aiogram/telegram-боты сами инициируют исходящие соединения к api.telegram.org — NAT/домашний сервер не мешает самим ботам. Публичный IP нужен только для того, что СЕРВЕР должен отдавать наружу.
- **Что НЕ работает без публичного HTTPS**: Telegram Mini App / WebApp (админка, открываемая из бота) — Telegram требует HTTPS-URL для WebApp. Решение: cloudflared туннель (см. §5), бесплатно, ~2 минуты. Для пилота «боты + REST для внутренних проверок» VPS не нужен вообще.
- **Оценка ресурсов**: рантайм FastAPI + 2 бота (polling) + Postgres 16 ≈ **500MB RAM, 1 vCPU достаточно**; сборка docker-образа (node build stage) — пик до +1GB временно; диск 10GB с запасом. На машине 4GB RAM / ~2.5GB available — влезает с запасом. Минимум для VPS: 1 vCPU / 1GB RAM / 10GB; комфортно 1-2 vCPU / 2GB.
- **Перед запуском проверь занятые порты**: `ss -tlnp | grep -E ":8000|:5432"`. Dev-uvicorn может висеть на 8000, системный postgres — на 5432 (частая ситуация на домашнем сервере). Останови старый dev-процесс (`kill PID`), иначе порт занят. Если локальный postgres уже на 5432, а ты поднимаешь docker compose со своим postgres — конфликт портов; либо меняй порт контейнера, либо используй существующий postgres без docker.
- **docker compose плагин может отсутствовать** (Ubuntu): `docker compose version` → «docker: unknown command: docker compose» — это НЕ дефект кода, падает `docker compose config -q` и тесты вида `test_docker_compose_up`. Фикс окружения: сначала `sudo apt update`, затем ВАЖНО — у Ubuntu-пакета `docker.io` плагин называется **`docker-compose-v2`**, а НЕ `docker-compose-plugin` (последний только в официальном Docker repo, на Ubuntu apt выдаёт «E: Невозможно найти пакет docker-compose-plugin», проверено 21.08.2026): `sudo apt install docker-compose-v2`. Проверка: `docker compose version`.
- **Доступ к docker.sock: группа применяется только в новой сессии** — после `sudo usermod -aG docker $USER` текущая SSH-сессия всё ещё даёт `permission denied` (`groups` не показывает docker). Нужен `newgrp docker` (или выход/вход). Проверка: `docker ps` без sudo.
- **Доступ к docker из долгоживущей сессии Hermes (урок 21.08.2026):** сессия Hermes запущена ДО `usermod -aG docker` — группа не применится, перелогина нет. `newgrp docker -c "docker ps"` возвращает ПУСТО (не работает), а heredoc-форма работает:
  ```bash
  newgrp docker <<'EOF'
  docker ps
  EOF
  ```
  Готовая обёртка: `~/.hermes/scripts/dk.sh` (принимает команду, выполняет через newgrp-heredoc); эталонный экземпляр лежит в навыке: `scripts/dk.sh` (скопируй при необходимости). ⚠️ **Квотинг**: `$*` в обёртке снимает кавычки → команды с вложенными кавычками (`exec -T app sh -c '...'`) ломаются и тихо выполняются НА ХОСТЕ (traceback показывает хост-пути `/home/hermes/...` вместо `/app/...`). Надёжный паттерн: писать команду в скрипт-файл (`write_file /tmp/x.sh`) и вызывать `dk.sh bash /tmp/x.sh` — кавычки не теряются.
- **Свежая контейнерная БД пуста → «Бот не привязан к тенанту» (урок 21.08.2026, lead-platform).** После `docker compose up` у app СВОЯ БД (db-контейнер), сида там нет. Сид, запущенный на хосте, пишет в системный postgres, а НЕ в контейнерный → бот работает (отвечает), но tenant по токену не находит. Сид нужно запускать ВНУТРИ контейнера: `docker compose exec -T app python scripts/seed_pilot.py`; проверка: `docker compose exec -T db psql -U booking -d booking -c "SELECT slug, client_bot_token IS NOT NULL FROM tenants;"`.
- **Dockerfile должен копировать scripts/ (урок 21.08.2026).** Если образ собирается только с `COPY src` + web, `exec app python scripts/seed_pilot.py` → `can't open file '/app/scripts/seed_pilot.py'`. Фикс: `COPY scripts ./scripts` в Dockerfile → `docker compose build app && docker compose up -d --force-recreate app`. ⚠️ `docker compose restart` НЕ перечитывает env_file и НЕ пересобирает образ — для свежего env/кода нужен `build` + `--force-recreate`.
- **Боты — отдельный контейнер от API (архитектурное требование, урок 21.08.2026, lead-platform).** НЕ держать aiogram-ботов в lifespan uvicorn-приложения: рестарт/падение API роняет ботов, а пользователь требует независимости. Правильная структура compose: сервис `app` (FastAPI/uvicorn) + сервис `bots` (тот же образ, `command: python scripts/run_bots.py`, `depends_on: db`, без портов). Standalone-скрипт: event_bus + sessionmaker + init_db + start_bots + `await asyncio.Event().wait()`, по SIGTERM — stop_bots + bus.stop (НЕ вызывать uvicorn.run). Из app-lifespan start_bots/stop_bots УБРАТЬ (иначе двойной polling → TelegramConflictError). Критичный нюанс: уведомления НЕ могут слаться через Bot-объект из app-контейнера (его там нет) — переводить notifier'ы на прямой Telegram Bot API (`POST https://api.telegram.org/bot<token>/sendMessage`, reply_markup = inline_keyboard JSON для кнопок, которые обрабатывает bots-контейнер). Проверка: `docker compose ps` — оба Up; боты отвечают; уведомления доходят.
- **Темп пилота с нетерпеливым заказчиком (урок 21.08.2026): пересборка сразу после каждого готового фикса.** Как только смержен фикс, влияющий на поведение ботов/сервера — сразу `docker compose up -d --build` + сид + проверка конфликтов (`docker compose logs app --since 1m | grep -c Conflict` → 0) и отдавай на тест. НЕ копить Kanban-цепочку и не ждать «всех задач» — пользователь раздражается («чего ждешь», «ну и, чего ждешь пиздец времени прошло»). Статусы — короткие, с тем, что уже РАБОТАЕТ.\n- **terminal-эвристика «long-lived server» блокирует `docker compose up -d --build` в foreground (21.08.2026).** Hermes terminal отклоняет вызов («This foreground command appears to start a long-lived server/watch process»), хотя `up -d` завершаемая. Это НЕ ошибка кода: запускай с `background=true` + `notify_on_complete=true` → `process wait` → проверка health + `grep -c Conflict`. Аналогично сломанный `write_file` (internal import error `resolve_task_overrides`) — fallback через terminal heredoc (`cat > /tmp/x.sh <<'SCRIPT'`), не застревать.\n- **Проверь docker-compose.yml перед запуском — конфликт портов может быть только у app.** Если у сервиса `db` НЕТ секции `ports:` (postgres живёт во внутренней сети compose, app ходит на `db:5432`), системный postgres на :5432 не мешает контейнеру. Конфликтует только проброшенный порт app (напр. 8000) с нативным uvicorn — останови dev-процесс перед `docker compose up` (`ss -tlnp | grep 8000`, `kill PID`).
- **pydantic-settings читает .env сам, а скрипты с os.getenv — НЕТ (урок 21.08.2026, lead-platform seed).** App (config.py, `env_file=".env"`) видит токены, а `scripts/seed_pilot.py` с `os.getenv("BOT_TOKEN_CLIENT")` при прямом запуске получает None → сид не пишет токены в tenant (`SELECT client_bot_token ... → NULL`). Фикс: перед запуском таких скриптов `set -a; source .env; set +a` (или экспорт переменных вручную).
- **Скрипты из корня репозитория** (`python scripts/foo.py`) могут падать с `ModuleNotFoundError: No module named 'scripts'`, если код делает `from scripts.x import y` — запускай с `PYTHONPATH=. python scripts/foo.py`.
- **pydantic int-поле + compose `env: ${VAR:-}` = краш на пустой строке (урок 21.08.2026, lead-platform).** Если в compose `environment: SUPER_ADMIN_TELEGRAM_ID: ${SUPER_ADMIN_TELEGRAM_ID:-}` (дефолт пустой), а env-переменная не задана — контейнер получает ПУСТУЮ строку, и `super_admin_telegram_id: int | None = None` в pydantic-settings падает `ValidationError: Input should be a valid integer ... input_value=''` → app не стартует (uvicorn крашится на импорте `Settings()`). Симптом: `docker compose up -d --build` ок, но контейнер в `Exited`, `docker compose logs app` показывает ValidationError на `src/config.py settings = Settings()`. Фикс (в коде, не в compose — устойчиво к любому источнику): `@field_validator("super_admin_telegram_id", mode="before")` → пустая строка → `None`. Проверка перед деплоем: `SUPER_ADMIN_TELEGRAM_ID= PYTHONPATH=. .venv/bin/python -c "from src.config import settings; print(settings.super_admin_telegram_id)"` → None.\n- **PG-енум хранит ИМЕНА членов, а не значения (урок 21.08.2026, lead-platform).** SQLAlchemy `SqlEnum(UserRole)` (или `Enum(..., name=...)`) пишет в postgres ИМЯ члена: `UserRole.SUPER_ADMIN = \"super_admin\"` → в БД `'SUPER_ADMIN'`, а НЕ `'super_admin'`. Ручной `psql ... WHERE role='super_admin'` падает `ERROR: invalid input value for enum user_role: \"super_admin\"` — это НЕ баг кода, а неправильный регистр в запросе; ищи `role='SUPER_ADMIN'`. Дополнительно: **`Base.metadata.create_all` НЕ расширяет существующие PG-енумы** (новое значение роли не появится в enum у живой БД) — нужен явный идемпотентный `ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'SUPER_ADMIN'` в `init_db()` (или alembic-миграция). Симптом «миграция сделана, а приложение не может создать юзера новой роли / SQL на роль падает» — проверь оба места: регистр в запросе и ALTER TYPE в init_db.\n- **`Base.metadata.create_all` НЕ добавляет новые КОЛОНКИ в существующие таблицы (урок 21.08.2026, lead-platform users.is_active).** Воркер добавил в модель `User.is_active` (и ALTER TYPE для новой роли) — а app при старте упал `ProgrammingError: column users.is_active does not exist` → uvicorn `Application startup failed. Exiting.`, контейнер перезапускается, `/health` пусто, туннель отдаёт 502. Причина: `create_all` создаёт только НОВЫЕ таблицы; существующую таблицу users не расширяет. Для КАЖДОЙ новой колонки нужен явный идемпотентный SQL в init_db() рядом с ALTER TYPE: `ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE`. Симптом-подсказка: `docker compose logs app | grep -iE "UndefinedColumn|does not exist"`. После фикса — `docker compose up -d --build app` → `/health` ok + `psql -c '\\d users'`.

### Web App кнопка с http:// URL — крашит хэндлер, бот «молчит» (урок 21.08.2026, worker-бот lead-platform)

**Симптом:** пользователь жмёт /start, бот НЕ отвечает (бот жив: токен валиден, `pending_update_count=0`). В логах контейнера: `aiogram.exceptions.TelegramBadRequest: Bad Request: inline keyboard button Web App URL 'http://localhost:8000/web/' is invalid: Only HTTPS links are allowed`.

**Причина:** Telegram принимает Web App (`WebAppInfo`) кнопки ТОЛЬКО с `https://`. Если код безусловно добавляет `InlineKeyboardButton(text="Открыть админку", web_app=WebAppInfo(url=settings.webapp_url))`, а `webapp_url` = `http://localhost:8000/web/` (дефолт/локальный пилот) — исключение из `message.answer(...)` валится в обработчике /start, ответ не уходит → «нажал start, не работает».

**Фикс (в коде, не в конфиге — устойчив к любому источнику URL):** HTTPS-гейт на кнопке + ссылка текстом, когда HTTPS ещё нет:
```python
def admin_kb():
    kb = []
    if settings.webapp_url.startswith("https://"):
        kb.append([InlineKeyboardButton(text="Открыть админку",
                                        web_app=WebAppInfo(url=settings.webapp_url))])
    kb.append([InlineKeyboardButton(text="⚙️ Настройки", callback_data="wo:settings")])
    return InlineKeyboardMarkup(inline_keyboard=kb)
# и в текст сообщения при не-HTTPS добавить: f"{msg}\n🔗 Админка: {settings.webapp_url}"
```
После включения HTTPS (cloudflared, §5) кнопка Web App появится автоматически — ветвление по `startswith("https://")`.

**Тест-грабля (aiogram model_dump):** фейковые Bot-сессии часто хранят `method.model_dump(warnings=False)` → у обычной кнопки БЕЗ web_app всё равно присутствует ключ `"web_app": None`. Проверка `assert not any("web_app" in btn for btn in buttons)` даёт ЛОЖНЫЙ провал (ключ есть). Проверять по ЗНАЧЕНИЮ: `assert not any(btn.get("web_app") is not None for btn in buttons)`.

## 5c. Mini App / WebApp admin — вход вне Telegram

**⚠️ ОТВЕРГНУТО ПОЛЬЗОВАТЕЛЕМ (21.08.2026): dev-вход в ПРОДЕ — дыра, НЕ включать.** После реализации dev-входа за флагом пользователь жёстко развернул его: «любой желающий блядь в админку может зайти что за тупость мудак». Правильная пользовательская история (требование пользователя):
- **Супер-админ с полными правами; его telegram_id задаётся ПРИ СТАРТЕ приложения** (env `SUPER_ADMIN_TELEGRAM_ID` → при старте upsert User role=SUPER_ADMIN, идемпотентно). НЕ «первый написавший» и НЕ dev-кнопки.
- При первом `/start` в worker-боте супер-админу предлагается **онбординг компании** (название и т.п.) → кнопка «Открыть админку» (Web App).
- Вход в админку — ТОЛЬКО через Telegram Mini App: initData валидируется токеном бота + User по реальному telegram_id.
- `VITE_DEV_LOGIN` / `DEV_LOGIN_ALLOWED` в проде — выключены (дефолт 0/false); dev-вход — только dev-сборка.

Ниже — технические причины «кнопок входа нет» и механизмы за флагом (полезно для dev-сборки и диагностики), но продуктовое решение — суперадмин по env + онбординг + Mini App, а не dev-вход.

**Дизайн-предпочтения пользователя для админки/Mini App (урок 21.08.2026, lead-platform).** Пользователь жёстко раскритиковал монохромный интерфейс: «дизайн ужасный, не красиво, не ярко пиздец». Для бизнес-админок, которые открываются в Telegram Mini App, Василий хочет: ЯРКУЮ насыщенную палитру (не серо-белую shadcn-дефолтную oklch с насыщенностью 0) — градиенты на primary/шапке/карточках статистики, цветные статусы записей (new=янтарный, confirmed=зелёный, done=синий, cancelled/no_show=красный), активная навигация с цветной подложкой. Дефолтный акцент — индиго→фиолетовый градиент (если не оговорён другой цвет). Также: в меню worker-бота НЕ должно быть лишних кнопок — только «Открыть админку» (Web App); кнопка «⚙️ Настройки» признана лишней и убрана. Правило: сначала спросить/предложить цветовую гамму, если заказчик упомянул дизайн.

**⚠️ Роль есть в бэкенде, но НЕ во фронт-навигации = «пустая админка» (урок 21.08.2026, lead-platform).** После добавления роли SUPER_ADMIN (env `SUPER_ADMIN_TELEGRAM_ID` → upsert User role=SUPER_ADMIN) пользователь вошёл в админку и НЕ увидел ни клиентов, ни чатов, ни расписания — «будто задача была поставлена и вообще ноль выполнено», «из настроек нельзя вернуться в главный экран». Причина: бэкенд-gaurd `require_roles(*STAFF)` пропускает SUPER_ADMIN ВСЕГДА («полные права на всех админ-эндпоинтах»), но фронт-навигация фильтрует пункты по списку ролей (`AppShell.tsx` NAV_ITEMS: `roles: ['owner','admin','specialist','support']`) — super_admin в эти списки НЕ добавлен → пользователь видел ТОЛЬКО «Настройки» (единственный пункт с super_admin), и «назад» идти было некуда. Правило при добавлении новой роли: 1) бэкенд-guards (require_roles), 2) **фронт-навигация/UI-списки ролей ВО ВСЕХ экранах** (`roles:` в AppShell/NAV_ITEMS и т.п.) — grep по `roles: \[` в web/src; 3) E2E-проверка: войти под новой ролью и убедиться, что видны все положенные разделы. Фронт-роли дублируются вручную в каждом NAV_ITEMS — легко забыть. Проверочная команда после мержа: `grep -rn "roles:" web/src/components/layout/ | grep -v super_admin` — если пункт должен быть виден super_admin, а его там нет — баг.

**Симптом (урок 21.08.2026, lead-platform):** пользователь открывает админку Mini App в браузере (`http://host:8000/web/`), видит экран «Вход в админку» и ВООБЩЕ нет кнопок входа — «нихуя не понятно». Три независимые причины, проверять все:

1. **Кнопки dev-входа скрыты в прод-сборке.** `import.meta.env.DEV` (Vite) истинно только в dev-сборке; в Docker-образе (web/dist) кнопки «Войти как owner/admin/specialist» не рендерятся. Фикс: build-arg `VITE_DEV_LOGIN=1` → условие показа `import.meta.env.DEV || import.meta.env.VITE_DEV_LOGIN === '1'`.
2. **Тестовые telegram_id не совпадают с сид-юзерами.** Фронт хардкодит `DEV_TG_IDS` (owner=801, admin=802, specialist=803), а сид создаёт юзеров с `PILOT_*_TELEGRAM_ID` (напр. 1001/1002/2001) → «Войти как owner» ищет User с tg_id=801 → 404 «user not found». Фикс: build-arg `VITE_DEV_TG_IDS='{"owner":"1002","admin":"1001","specialist":"2001"}'` → `buildTestInitData` берёт ID из env (дефолт — старые константы).
3. **Подпись initData требует токен — НЕ вшивай его в бандл.** `buildTestInitData` подписывает initData токеном `VITE_BOT_TOKEN`; в проде он пуст → бэкенд `validate_init_data` → 401. Правильное решение: бэкенд-флаг `security.allow_dev_login` (env `DEV_LOGIN_ALLOWED=1`, дефолт False): при включённом флаге `get_current_user` принимает initData БЕЗ валидной подписи (парсит `user` payload, ищет User по tenant_id+telegram_id; не найден → 404 как обычно). Токен бота НЕ попадает в JS-бандл. Для прода флаг выключен.

Проверка после деплоя: открыть `/web/` → три кнопки → «Войти как owner» → `/schedule` с данными. Безопасность: флаг — пилот-костыль, не включать на публичных деплоях.

## 5d. «Кнопка не работает» в веб-админке — диагностика (урок 22.08.2026, lead-platform)

**Симптом:** пользователь: «нельзя отменить запись в админке» — жмёт ❌ Отменить, диалог закрывается, «ничего не происходит».

**Диагностический порядок (read-only, не гадать):**
1. Бэкенд-эндпоинт существует? `grep -rn "cancel" src/interface/api/admin/` → есть `POST /appointments/{id}/cancel`.
2. Фронт-кнопка существует? `grep -rn "cancel" web/src/` → есть, в `AppointmentActions.tsx`.
3. **Что РЕАЛЬНО отвечает прод:** `docker compose logs app --since 24h | grep -E "appointments/.*/cancel"` → `POST /api/admin/appointments/1/cancel HTTP/1.1" 409 Conflict` (повторяется N раз = пользователь пробовал несколько раз).
4. **Состояние записи в БД:** `docker exec <db> psql -U <user> -d <db> -c "SELECT id, status, start_at, created_at FROM appointments ORDER BY id;"` → запись №1 уже `CANCELLED`, №2 `DONE`.
5. Вывод: запись в ТЕРМИНАЛЬНОМ статусе — статусная машина (`src/domain/booking/status_machine.py`) правильно отдаёт 409 «Недопустимый переход». Бэкенд НЕ сломан — сломан UX.

**Два фронт-дефекта, превращающих корректный 409 в «нельзя отменить»:**
1. **Кнопки действий показываются для ВСЕХ статусов** (`AppointmentActions.tsx` рендерит ✅ Подтвердить / 📅 Перенести / ❌ Отменить всегда) — включая терминальные (отменена/выполнена/не_пришёл). Для терминальных статусов кнопки надо СКРЫВАТЬ; для `подтверждена` — убрать «Подтвердить».
2. **Ошибки API молча проглатываются**: в `run()` нет catch — `APIError` уходит в unhandled rejection, UI не показывает detail → «нажал, ничего не произошло». Каждое действие должно ловить ошибку и показывать её (красный текст/тост).

**Общий паттерн:** жалоба «кнопка/фича не работает» в задеплоенном веб-приложении = сначала проверь, что РЕАЛЬНО отвечает сервер (`docker logs` → HTTP status) и в каком состоянии данные (psql), потом код. 4xx на терминальном состоянии + молчаливый фронт = классическая пара «правильный бэкенд, сломанный UX».

## 6. Background Process Lifecycle

```bash
# Start service in background
cd ~/Projects/Personal/GitHub/repo-name
uv run python -m module.name bot &
# Or use Hermes terminal(background=true) with watch_patterns

# Check it's running
ps aux | grep "python -m module.name" | grep -v grep

# To kill
pkill -f "python -m module.name bot"

# View logs
tail -f nohup.out
```

**Pitfall:** Don't use `&` in Hermes `terminal()` — use `background=true` parameter instead. Foreground terminal with `&` is rejected.

## 7. Instagram/Playwright Scraper Gotchas

### Session placement

When a project uses Playwright to scrape Instagram, check where `_SESSION_DIR` is defined:

```bash
grep -rn "_SESSION_DIR\|_session_path" src/ --include="*.py"
# Typical: _SESSION_DIR = Path.home() / ".config" / "instaloader"
```

Session files MUST be placed at the path the code expects. For `insta-flat-parser`:
- **Code expects:** `~/.config/instaloader/session-{username}.json`
- **Obvious but WRONG:** `~/.insta_flat_parser/session-{username}.json`

Always check the actual `_SESSION_DIR` const before placing session files.

### Headless Chrome timeouts

Instagram is slow to serve headless Chrome from a VPS (European datacenters → US Instagram servers). Default 15s timeouts often fail. Increase to 30s+:

```python
# In fetch_profile_posts:
resp = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

# In fetch_post_comments:
await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
```

### Session validation

After loading a session, verify: `any(c.get("name") == "ds_user_id" for c in cookies)`. The cookie `ds_user_id` confirms Instagram accepted the session.

### Monitor always-notify patch

If the bot only sends notifications when contacts are found (common pattern), and you want ALL posts:

```python
# Before (monitor.py):
if result.contacts.has_any:
    await notify(self.bot, post, result)

# After:
try:
    await notify(self.bot, post, result)  # unconditionally
except Exception as exc:
    logger.error("Failed to notify: {}", exc)
```

### OCR/Whisper extras

For text extraction from images (OCR) and audio transcription (Whisper):

```bash
# System deps
sudo apt install tesseract-ocr tesseract-ocr-rus ffmpeg

# Python extras — check pyproject.toml for extras
grep -E "^\[project\.optional-dependencies\]" -A 10 pyproject.toml
uv sync --extra all   # or: uv sync --extra ocr --extra whisper
```

Enable in .env:
```env
OCR_ENABLED=true
OCR_LANG=rus+eng
WHISPER_ENABLED=true
WHISPER_MODEL_SIZE=tiny   # tiny/small/medium/large
```

**Whisper model selection (CPU, no GPU):**

| Model | Size | Speed (2-min video) | Quality |
|-------|------|---------------------|---------|
| `tiny` | ~40MB | 20-40s | Poor on accented speech, often misses phones |
| `base` | ~140MB | 30-60s | Fair |
| `small` | ~460MB | 1-2 min | **Good — recommended** for Central Asian accents |
| `medium` | ~1.5GB | 3-5 min | Better but heavy RAM (~2GB+ for model) |

- tiny is fine for clear Russian/English — struggles with Uzbek/Karakalpak accent
- small is the sweet spot for rieltor videos with accent
- Model downloads once on first run (~30-50s), cached in HF cache (~/.cache/huggingface/)
- First-load log: `Loaded Whisper model: small`

**Debugging silent notification failures**

If the bot finds posts (logs show `Checked @user (5 posts)`) but user gets no Telegram messages:

1. Add logging to `notify()`:
```python
async def notify(bot, post, result):
    logger.info("Notifying about post {}", post.shortcode)
    ...
    logger.debug("Sent notification to chat_id={}", chat_id)
```

2. Check `getUpdates` via API — but note: `getUpdates` only shows messages **to** the bot, **not** messages sent **by** the bot.

3. Look for `Task exception was never retrieved` in logs — this is an aiogram 3 pattern where `asyncio.create_task(bot.send_message(...))` fails but nobody awaits the task. The error is logged but doesn't crash the bot — it just silently drops the notification. Fix: replace `asyncio.create_task(bot.send_message(...))` with direct `await` inside a try/except.

## 8. Common Pitfalls

| Problem | Solution |
|---------|----------|
| `chat not found` on startup | User must `/start` the bot first. Non-fatal error, bot works after user initiates chat |
| `/start` молчит, в логах `Only HTTPS links are allowed` (Web App кнопка с http://) | `WebAppInfo` требует https:// — HTTPS-гейт кнопки (`webapp_url.startswith("https://")`), иначе ссылка текстом (см. «Web App кнопка с http:// URL» выше) |
| «Нельзя отменить/подтвердить запись» в админке, в логах `409 Conflict` | Запись в терминальном статусе (отменена/выполнена/не_пришёл) — статусная машина запрещает переход; фронт при этом показывает кнопки для всех статусов и молча глотает ошибки API. Фикс: скрывать действия по статусу + показывать detail ошибки (см. §5d) |
| Multiple ADMIN_IDS causes repeated "chat not found" | Reduce to single admin: `ADMIN_IDS=<your-id>` only, or ensure all admins `/start` the bot |
| Cloudflared tunnel 1033 error | Cloudflared process died — restart it. New URL changes — update `WEBAPP_URL` in .env and restart bot |
| Token in .env has special chars (`$`, `"`, `#`) | Python-dotenv may misparse. Wrap in single quotes or escape. Check with `uv run python3 -c "from dotenv import load_dotenv; load_dotenv(); import os; print(repr(os.environ['KEY']))"` |
| Playwright browser not installed | Run `uv run playwright install chromium` |
| `uv sync` fails on missing system deps | Install: `sudo apt install libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0` |
| Process died silently with no logs | Start with `2>&1` capture, or use Hermes `terminal(background=true)` with `notify_on_complete=true` for bounded tasks |
| Bot processed /start once, then ignores after restart | Update IDs were already consumed. User must `/start` again — the new instance receives it fresh |
| Bot sends no notifications even though logs show posts found | Check for `Task exception was never retrieved` — aiogram create_task may silently swallow errors. Add try/except around await (see §7 Debugging) |
| Instagram scraper returns 0 posts (timeout) | Page.goto timeout too short for headless Chrome. Increase from 15s to 30s+ (see §7) |
| Session file exists but "not loaded" in logs | Session is in wrong directory. Check `_SESSION_DIR` const in source code, move file there |
| Cloudflared tunnel died (1033) — new URL differs from old | Restart cloudflared, extract new URL from logs, update `WEBAPP_URL` in .env, restart bot |
