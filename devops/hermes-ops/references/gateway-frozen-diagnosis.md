# Gateway Frozen / Provider Unresponsive — Full Diagnostic Protocol

Диагностика и восстановление, когда gateway не отвечает (Telegram бот молчит, типинг индикатор завис, сообщения не обрабатываются).

## Эталонный случай (июнь 2026)

Пользователь: «глянь что не так у меня gateway завис». Симптомы:
- Telegram бот не отвечал
- `hermes gateway restart` сам зависал
- Gateway process был жив (`Ssl`), systemd показывал `active (running)`

## Step 1: Проверить процесс и service

```bash
ps aux | grep -i gateway | grep -v grep
# → hermes ... python -m hermes_cli.main gateway run --replace  (жив)
# → hermes ... python3 hermes gateway restart  (завис в статусе T)

systemctl --user status hermes-gateway
# → Active: active (running) since ...
# → Main PID: 82487 (python)
```

### Что смотреть в ps aux:
- `Ssl` — нормально, gateway работает
- `T` или `Tl` — stopped (кто-то отправил SIGSTOP)
- `Z` — zombie
- Если процесса нет — gateway dead, systemd должен перезапустить

## Step 2: Проверить логи на ReadTimeout

```bash
journalctl --user -u hermes-gateway --since "30 minutes ago" --no-pager | grep -E "ReadTimeout|API call failed|Stream drop|Stream exhausted" | tail -20
```

### Характерный паттерн (когда провайдер лагает):

```
WARNING agent.stream_diag: Stream drop on attempt 2/3 — retrying. 
  provider=kilocode 
  error_type=ReadTimeout 
  http_status=200 
  bytes=375 chunks=1 
  elapsed=10.86s 
  ttfb=0.85s 
  upstream=[x-vercel-id=fra1::... server=Vercel]

WARNING agent.conversation_loop: API call failed (attempt 3/3)
  provider=kilocode 
  model=deepseek/deepseek-v4-flash:discounted 
  summary=The read operation timed out
```

### Ключевые маркеры:\n| Поле | Значение | Диагноз |\n|------|----------|---------|\n| `http_status=200` | Сервер ответил 200 OK | Соединение установлено |\n| `ttfb=0.85s` | Time to first byte быстрый | Проблема не в сети |\n| `bytes=375 chunks=1` | Всего 375 байт за 10с | Стрим прервался в начале |\n| `upstream=server=Vercel` | KiloCode через Vercel | Vercel может убивать долгие стримы |\n| `Stream exhausted on attempt 3/3` | 3 попытки закончились | Провайдер стабильно не отвечает |\n\n**Диагноз:** Провайдер (KiloCode) начинает отвечать, но зависает mid-stream. Gateway не виноват — он корректно ретраит. Health endpoint (`/health`) возвращает `405` — это нормально для KiloCode API, не признак проблемы.\n\n**`hermes gateway restart` как отдельный процесс:** Когда пользователь запускает `hermes gateway restart` в терминале, он создаёт отдельный Python-процесс, который пытается graceful restart. Если gateway не отвечает на SIGTERM (потому что ждёт ответа от провайдера), этот процесс зависает в состоянии `T` (stopped by SIGSTOP) или `S` (sleeping). Его можно безопасно убить: `kill <pid>` или `kill -9 <pid>` — это просто CLI-команда, не gateway.

## Step 3: Проверить API провайдера напрямую

```bash
# Health check
curl -s -o /dev/null -w "%{http_code} %{time_total}s" --max-time 15 https://api.kilo.ai/api/gateway/health

# Chat test (осторожно — может сжечь токены)
curl -s --max-time 20 -X POST https://api.kilo.ai/api/gateway/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $KILOCODE_API_KEY" \
  -d '{"model":"deepseek/deepseek-v4-flash:discounted","messages":[{"role":"user","content":"hi"}],"stream":true}' 2>&1 | head -5
```

Если API отвечает мгновенно (121ms как в нашем случае) — провайдер жив, но стриминг конкретной модели может быть нестабилен.

## Step 4: Emergency restart

### Проблема: `hermes gateway restart` и `systemctl --user restart` зависают

Обе команды посылают SIGTERM (graceful shutdown). Gateway начинает drain активных агентов (180s таймаут) и может пытаться финализировать API-запросы. Если провайдер не отвечает — shutdown зависает.

**Решение — kill -9:**

```bash
# 1. Найти PID
PID=$(ps aux | grep "gateway run" | grep -v grep | awk '{print $2}')

# 2. Жёстко убить (SIGKILL)
kill -9 $PID

# 3. Подождать перезапуска от systemd
sleep 3
systemctl --user is-active hermes-gateway
# → active
```

### Что происходит:
1. SIGKILL убивает gateway мгновенно (без graceful drain)
2. systemd видит exit code 9/KILL → Restart=always → запускает заново
3. Новый PID, свежее состояние
4. Gateway лог: `Started hermes-gateway.service`

### После рестарта — проверить:

```bash
# Показать PID нового процесса
ps aux | grep "gateway run" | grep -v grep

# Проверить логи — есть ли новые ReadTimeout
journalctl --user -u hermes-gateway --since "1 minute ago" --no-pager | grep -E "ReadTimeout|Started"

# Если ReadTimeout нет — gateway чист, проблема была в накопившемся состоянии
# Если ReadTimeout продолжаются — провайдер реально лежит
```

## Step 5: Если провайдер реально лежит

ReadTimeout продолжаются сразу после рестарта — значит проблема на стороне KiloCode/Vercel, не в gateway. Варианты:

1. **Подождать** — обычно проходит само за несколько часов
2. **Сменить провайдера** — временно переключиться на OpenRouter или DeepSeek напрямую
3. **Уменьшить таймауты** — `HERMES_STREAM_READ_TIMEOUT=10`, `api_max_retries=1` (см. `references/kilocode-timeout-tuning.md`)

## Бонус: зависший `hermes gateway restart` процесс

Если `hermes gateway restart` был запущен и завис, он висит как отдельный процесс:

```
hermes    117028  ... python3 /home/hermes/.local/bin/hermes gateway restart
```

Состояние `T` (stopped) или `S` (sleeping). Его можно:
- Разбудить: `kill -CONT <pid>` (переведёт в S, но она всё равно зависнет)
- Убить: `kill <pid>` или `kill -9 <pid>` — это безопасно, он всего лишь CLI-команда

## Превентивные меры

1. **Настроить таймауты** (см. `kilocode-timeout-tuning.md`)
2. **Регулярно проверять** `journalctl --user -u hermes-gateway --since "1 hour ago" --no-pager | grep -c "ReadTimeout"` — если >0 за час, провайдер нестабилен
3. **Держать альтернативного провайдера** в конфиге для быстрого переключения
