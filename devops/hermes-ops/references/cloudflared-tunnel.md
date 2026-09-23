# Cloudflared Quick Tunnel Management

## Когда использовать

Нужно временно открыть localhost-порт наружу через Cloudflare (без регистрации/домена):
- Telegram Mini App / Web App на VPS
- Тестовый эндпоинт для вебхуков
- Любой HTTP-сервис на VPS, который нужно показать через HTTPS

## Поднятие туннеля

```bash
# Простейший запуск
/tmp/cloudflared tunnel --url http://localhost:8080
```

## Получение URL туннеля

Hermes может не захватить первые строки вывода cloudflared (URL печатается до precheck). Используй `tee`:

```bash
/tmp/cloudflared tunnel --url http://localhost:8080 2>&1 | tee /tmp/cloudflared.log
```

Затем прочитать URL:
```bash
grep "trycloudflare.com" /tmp/cloudflared.log | grep "Visit it at"
# → https://xxxx-xxx.trycloudflare.com
```

## Известные проблемы

### 1. DNS Timeout (~каждые 6 часов)

Туннель падает с ошибкой:
```
ERR Failed to refresh DNS local resolver error="lookup region1.v2.argotunnel.com: i/o timeout"
```

**Причина:** нестабильный DNS на VPS провайдере. Не лечится — только перезапуск.

**Фикс:**
```bash
# Найти PID
ps aux | grep cloudflared | grep -v grep
kill <pid>
# Запустить заново
/tmp/cloudflared tunnel --url http://localhost:8080 2>&1 | tee /tmp/cloudflared.log
```

### 2. URL меняется при каждом перезапуске

Quick туннели без аккаунта создают новый URL каждый раз. После перезапуска нужно обновить:
- `WEBAPP_URL` в `.env` проекта
- Перезапустить бота (или сервис, который использует этот URL)

### 3. Нет гарантии аптайма

Quick tunnels без Cloudflare аккаунта — без гарантии. Для продакшена нужен named tunnel с доменом.

### 4. QUIC может не работать (UDP блокирован)

На некоторых VPS порт 7844 (QUIC) блокирован. Cloudflared автоматически падает на HTTP/2:
```
UDP Connectivity  FAIL  QUIC connection failed
SUMMARY: Environment ready with degraded transport. cloudflared will proceed using 'http2'.
```

Это нормально — HTTP/2 работает стабильно.

## Установка cloudflared на VPS

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
chmod +x /tmp/cloudflared
```
