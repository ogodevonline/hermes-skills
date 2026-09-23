# Usage: compress_sessions.py

Скрипт: `~/.hermes/scripts/compress_sessions.py` (заглушка → `compress/cli.py`)
Модули: `~/.hermes/scripts/compress/{__init__,cli,db,compress,summarize}.py`

## Режимы

### --compact (быстрый, без LLM)
```bash
python3 ~/.hermes/scripts/compress_sessions.py --compact
python3 ~/.hermes/scripts/compress_sessions.py --compact --date 2026-05-26
python3 ~/.hermes/scripts/compress_sessions.py --compact --days 7
```
Вывод: JSON с session_id, source, title, message_count, tool_call_count + сводка (total_sessions, total_messages, total_tool_calls, tokens). Без саммари и key_messages. Время: 0.1-0.3 сек.

### --summarize (LLM-саммари, параллельно)
```bash
python3 ~/.hermes/scripts/compress_sessions.py --summarize
python3 ~/.hermes/scripts/compress_sessions.py --summarize --date 2026-05-26
```
Вывод: JSON с осмысленными саммари каждой сессии (1-2 предложения: тема, решение, проблемы). Чанки по 5 сессий, параллельно 5 воркеров через ThreadPoolExecutor. Время: ~15-30 сек на 37 сессий. Требует DEEPSEEK_API_KEY.

### Без флагов (саммари + key_messages)
```bash
python3 ~/.hermes/scripts/compress_sessions.py
```
Вывод: саммари + ключевые сообщения (первые 3, каждое N-ное, последние 3 из каждой сессии).

## Формат вывода
```json
{
  "period": {"start": "2026-05-26", "end": "2026-05-26", "days": 1},
  "sessions": [
    {
      "session_id": "...",
      "source": "telegram",
      "title": "...",
      "message_count": 278,
      "tool_call_count": 134,
      "summary": "тема: ...; решение: ...; проблемы: ..."
    }
  ],
  "summary": {
    "total_sessions": 37,
    "total_messages": 1579,
    "total_tool_calls": 657
  }
}
```

## LLM internals
- Модель: `deepseek-chat` (температура 0.3, max_tokens 500)
- Ограничение: 2000 символов на сессию (обрезка длинных сообщений до 500 символов)
- Чанки: 5 сессий на один LLM-колл
- Параллелизм: 5 воркеров через ThreadPoolExecutor
- Таймаут: 60 секунд на колл
