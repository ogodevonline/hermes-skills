# Деплой lead-platform на vdska — команды и нюансы (31.08.2026)

Хост: vdska. Docker из Hermes-сессии только через `~/.hermes/scripts/dk.sh docker ...` (обёртка newgrp docker).

## Полный порядок подъёма (после git pull / пересборки)
```bash
cd ~/projects/lead-platform

# 1. Собрать образы (background + notify; терминал блокирует build/up в foreground)
dk.sh docker compose build            # app + bots, web собирается внутри (npm ci + build)

# 2. Только БД
dk.sh docker compose up -d db

# 3. Сид платформы ДО первого старта app (тенант platform должен быть id=1!)
dk.sh docker compose run --rm --no-deps app python scripts/seed_platform.py
# если в БД уже есть чужой первый тенант:
dk.sh docker compose exec db psql -U booking -d booking -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 4. app + боты
dk.sh docker compose up -d app bots

# 5. Туннель (если URL сменился):
~/.local/bin/cloudflared tunnel --url http://localhost:8000 --no-autoupdate   # background, silent
# URL из логов: «Your quick Tunnel has been created! https://<rand>.trycloudflare.com»
# → обновить в .env: WEBAPP_URL=https://<rand>.trycloudflare.com/web/ и SITE_BASE_URL=https://<rand>.trycloudflare.com
# → dk.sh docker compose up -d app
```

## Полезные команды
- `dk.sh docker compose ps` — статусы (формат `{{.Name}}\t{{.Status}}`)
- `dk.sh docker logs lead-platform-app-1 --tail 25` / `lead-platform-bots-1` — логи
- `dk.sh docker compose exec db psql -U booking -d booking -c "SELECT ..."` — SQL (БЕЗ -T)
- `dk.sh docker compose run --rm --no-deps app python scripts/seed_pilot.py` — сид пилота rashid-dental (услуги, специалист, KB)
- Смоук: `curl -s localhost:8000/health`, `/`, `/quiz`, `/web/`, `/api/public/platform-bot`, `/api/site/<slug>`

## .env — что важно
- `SUPER_ADMIN_TELEGRAM_ID=350262645` (Василий)
- `WEBAPP_URL` = туннель + `/web/` (Mini App HTTPS); `SITE_BASE_URL` = туннель (визитки /s/:slug, share_url)
- Ключей Payme/Click нет — реальная оплата недоступна (используется pay-test заглушка)
- .env в .gitignore; правки напрямую (это проект, не Hermes system)

## Специфика vdska vs машина Василия
- cloudflared на vdska РАБОТАЕТ; на машине Василия порт 7844 (QUIC/HTTP2) заблокирован → pinggy/serveo через 443
- Локальные pytest на vdska невозможны: DATABASE_URL в .env → localhost:5432/booking, а booking-platform-postgres-1 удалён (31.08 по просьбе Василия). Тесты гонять у Василия/CI; на vdska — живые curl-проверки.
- `dk.sh` может писать «unexpected EOF while looking for matching quote» при сложных кавычках — команда всё равно исполняется (проверять результат по выводу).
