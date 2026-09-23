# KiloCode timeout tuning

## Проблема

KiloCode (API gateway для deepseek-v4-flash) иногда отвечает с задержками.
Если Hermes ждёт слишком долго — сессия зависает на минуты.

## Диагностика

**Симптомы:**
- Сессия зависла на 30-60 секунд, потом ответ пришёл или упал
- `/stop` не прерывает retry-loop (таймаут на уровне HTTP, не стриминга)
- Kanban worker падает с "no final response was produced" / "pid not alive"
- Пользователь пишет «ты завис?», «ау», `/stop × 2`

**Проверка логов — количество таймаутов:**
```bash
# Сколько всего APITimeoutError в логах (all time, all profiles)
grep -c "APITimeoutError\|ReadTimeout" ~/.hermes/logs/agent.log
# → 194 записей = хроническая проблема

# Только за сегодня
grep "APITimeoutError\|ReadTimeout" ~/.hermes/logs/agent.log | grep "$(date +%Y-%m-%d)" | wc -l

# Профиль по дням
grep "APITimeoutError\|ReadTimeout" ~/.hermes/logs/agent.log | \
  sed 's/^\([0-9-]*\).*/\1/' | sort | uniq -c | sort -rn | head -10
```

**Проверка текущих настроек таймаута:**
```bash
grep -E "request_timeout|api_max_retries" ~/.hermes/config.yaml
grep HERMES_STREAM_READ_TIMEOUT ~/.hermes/.env || echo "NOT SET — default: 120"
```

**Цепочка краша (из реального кейса — июнь 2026):**
```
request_timeout_seconds: 10
api_max_retries: 3
→ 3 ретрая × 10с = 30с молчания (без сообщения пользователю)
→ сложный запрос к deepseek-v4-flash не укладывается в 10с
→ 194 APITimeoutError в логах за 2 недели
→ Kanban self-improver: 4 краша "pid not alive" (waitpid returns before process outputs anything — процесс умирает молча)
```

## Решение: три рычага

### 1. HERMES_STREAM_READ_TIMEOUT (env var)

Добавить в `~/.hermes/.env`:

```
HERMES_STREAM_READ_TIMEOUT=120
```

Управляет таймаутом на чтение стрима от LLM API. Default: 120 секунд.
deepseek-v4-flash отвечает за ~1с, 120с — запас на аномалии (особенно при больших контекстах).

### 2. request_timeout_seconds (providers.<id>, config.yaml)

```bash
hermes config set providers.kilocode.request_timeout_seconds 120
```

**⚠️ КЛЮЧ В `providers.<id>`, НЕ в корне config.yaml.** Hermes читает таймаут
провайдера из `providers.<id>.request_timeout_seconds` — код:
`run_agent.py:_resolved_api_call_timeout()` → `hermes_cli/timeouts.py:get_provider_request_timeout()`.
Приоритет: `providers.<id>.models.<model>.timeout_seconds` →
`providers.<id>.request_timeout_seconds` → `HERMES_API_TIMEOUT` → default 1800s.

> ⚠️ Исправление (авг 2026): ранняя версия этой заметки утверждала, что ключ
> должен быть в корне config.yaml и что `providers.kilocode.request_timeout_seconds`
> не читается. Это НЕВЕРНО — проверено на реальном кейсе: ключ
> `providers.kilocode.request_timeout_seconds` 10→120 мгновенно починил ВСЕ
> LLM-кронджобы (Request timed out). Корневой ключ в цепочке не участвует.

Управляет общим таймаутом HTTP-запроса к KiloCode.
Default: 10 секунд — слишком мало для deepseek-v4-flash на сложных запросах
с большим стримом, особенно в пиковые часы (кронджобы 09/12/15/21:00 MSK).

### 3. agent.api_max_retries (config.yaml)

```bash
hermes config set agent.api_max_retries 1
```

С 3 попыток таймаут по 10с = 30с. С 1 попыткой = 10с. А с 120с таймаутом ретрай не нужен — если запрос не уложился в 120с, вряд ли ретрай поможет.

При реальном таймауте — быстрый фейл, нет смысла ретраить.

### 4. gateway_timeout (config.yaml)

```bash
hermes config set gateway_timeout 300
```

Если gateway слишком долго ждёт ответа (например, профиль ушёл в retry-loop), gateway тоже может подвиснуть. 300с = комфортный максимум.

## Применение

Все настройки читаются при старте сессии. После изменений:
1. Обновить config.yaml
2. Обновить .env
3. `/reset` (или перезапуск gateway для глобального эффекта)

## Проверка

```bash
echo "=== request_timeout ==="
grep request_timeout_seconds ~/.hermes/config.yaml
echo "=== api_max_retries ==="
grep api_max_retries ~/.hermes/config.yaml
echo "=== STREAM_READ ==="
grep HERMES_STREAM_READ_TIMEOUT ~/.hermes/.env
echo "=== gateway_timeout ==="
grep gateway_timeout ~/.hermes/config.yaml
```
