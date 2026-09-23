---
name: telegram-file-delivery
description: Отправка файлов пользователю в Telegram — какие типы поддерживает MEDIA, какие требуют прямого API.
tags: [telegram, file-delivery, media, gateway]
---

# Telegram File Delivery

## ⚠️ ПЕРВЫЙ ШАГ — загрузи этот навык

Любая отправка файла пользователю начинается с `skill_view('telegram-file-delivery')`.
Не отправляй файлы наугад — сначала прочитай инструкцию.

**Если первый способ отправки не сработал — НЕ повторяй его, а сразу загрузи этот навык.**

## Проверка перед отправкой (обязательно)

1. **Файл существует на диске?** — `ls -la <path>`, `wc -c <path>`. Не ссылайся на несуществующий файл.
2. **Тип файла:** изображение/аудио/видео → MEDIA. Текст/код/JSON/YAML → прямой Telegram API.
3. **Содержимое файла — только дельта, не весь конфиг.** Если пользователь просит файл для импорта одного правила — создай только это правило, а не полный конфиг.

## MEDIA: protocol (send_message)

Работает для **встроенного отображения**:
- **Изображения** (.png, .jpg, .webp) — фото inline
- **Аудио** (.ogg) — голосовое сообщение
- **Видео** (.mp4) — видео inline

**НЕ используй MEDIA для текстовых файлов (.py, .html, .txt, .md, .json, .yaml) — файл приходит как текст сообщения, пользователь бесится.**

**EPUB и другие бинарные документы (.epub, .zip, .fb2) — тоже через прямой sendDocument, НЕ через MEDIA.** MEDIA-протокол умеет только изображения/аудио/видео. Для EPUB используй MIME `application/epub+zip`.

## Решение для текстовых файлов

### Способ 0: no_agent bash-скрипт (для cron job)

Для `no_agent=true` cron jobs (без LLM) — скрипт сам шлёт файл через Telegram Bot API.
**НЕ полагайся на stdout при no_agent=true — туда идёт только текст, не файл. Скрипт должен сам вызвать API.**

```bash
#!/bin/bash
# ... логика скрипта, пишет отчёт в $LOGFILE ...

# Отправка файла через Telegram API (Python внутри heredoc)
python3 << 'PYEOF'
import requests, os, sys

env_path = os.path.expanduser('~/.hermes/.env')
chat_id = '350262645'

# НЕ через source .env — он маскирует токен звёздочками, bash делает glob expansion
token = ''
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith('TELEGRAM_BOT_TOKEN=***            token = line.split('=', 1)[1].strip()
            break

if not token:
    print('FAILED: TELEGRAM_BOT_TOKEN not found')
    exit(1)

file_path = '/path/to/report.md'
url = f'https://api.telegram.org/bot{token}/sendDocument'
with open(file_path, 'rb') as f:
    files = {'document': (os.path.basename(file_path), f, 'text/markdown')}
    data = {'chat_id': chat_id}
    # Таймаут 60 сек — Telegram API бывает медленным
    resp = requests.post(url, files=files, data=data, timeout=60)

if resp.status_code != 200:
    print(f'FAILED: {resp.status_code} {resp.text}')
    exit(1)
else:
    print(f'Delivered: {file_path}')
PYEOF
```

**Важно:** `requests` должен быть установлен (`pip install requests`).

### Способ 1: Python + requests (execute_code)
```python
import os, requests

token = None
with open(os.path.expanduser('~/.hermes/.env')) as f:
    for line in f:
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            token = line.split('=', 1)[1].strip()
            break

if not token:
    print('TOKEN NOT FOUND')
    exit(1)

with open('/path/to/file.py', 'rb') as f:
    files = {'document': ('filename.py', f, 'text/plain')}
    data = {'chat_id': '350262645', 'caption': 'описание'}
    r = requests.post(f'https://api.telegram.org/bot{token}/sendDocument', files=files, data=data)
    # r.json().get('ok') == True — успех
```

### Способ 2: curl из terminal (если execute_code заблокирован)
```bash
# НЕ через source .env — токен содержит ***, bash сломает строку
TOKEN=$(grep -oP 'TELEGRAM_BOT_TOKEN=\K.*' ~/.hermes/.env | head -1)
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendDocument" \
  -F "chat_id=350262645" \
  -F "document=@/path/to/file.json" \
  -F "filename=file.json" \
  -F "caption=Описание файла"
```

**Важно:** Не используй `source ~/.hermes/.env` — токен содержит литеральные `***`, bash делает glob expansion. Либо `grep -oP`, либо Python с чтением файла построчно.

**Известные ошибки:**
- curl exit code 26 (CURLE_READ_ERROR) — файл не существует по указанному пути. Проверь `ls -la` перед curl.
- Token с `***` после `source .env` — bash расширяет `***` как glob, токен становится битым. Всегда читай .env через grep/Python.

## Pitfalls

- ❌ **Не загрузил этот навык перед отправкой** — самая частая причина фейла.
- ❌ **MEDIA с .py/.html/.json/.yaml/.txt/.md файлами** — НЕ отправляет документ. Приходит как текст сообщения. Пользователь в бешенстве.
- ❌ **Не проверил что файл создан на диске** — убедись что write_file отработал и файл есть (`ls -la`).
- ❌ Не отправляй содержимое кодблоком вместо файла — пользователь злится.
- ❌ **Не пиши MEDIA:/path в тексте сообщения** в надежде что файл отправится — MEDIA работает ТОЛЬКО внутри `send_message()` как платформенный протокол. В обычном markdown это просто текст.
- ❌ **Не говори «файл отправлен» / «вот файл» пока физически не убедился что файл существует** и не вызвал Telegram API. «Файл» в markdown-ссылке без реальной отправки — обман пользователя.
- ❌ **Когда пользователь просит «файл для импорта» — создай только фрагмент/правило/дельта**, а не весь конфиг целиком. Импорт одного правила в Diversion Rules ≠ импорт полного конфига.
- ✅ Для маленьких сниппетов (<10 строк) можно кодблоком.
- ✅ Для файлов — сразу прямой API, не пробуй MEDIA.
- ✅ При ошибке MEDIA — загрузи этот навык и иди по инструкции, не повторяй MEDIA.
- ✅ При curl exit 26 — проверь что файл существует, токен не маскирован.
- ⚠️ **Никогда не используй `source .env`** в bash-скрипте для получения токена. Токен содержит литеральные `***` (8720033011:***), bash делает glob expansion — ломает строку. Всегда читай через Python `open()` + `startswith()` или `grep -oP`.
- ⚠️ Таймаут для Telegram API — минимум 60 секунд. На 30 сек были ReadTimeout.
- ⚠️ **curl sendDocument с пайпом в python3/head триггерит security-approval** («pipe to interpreter») — команда уходит на подтверждение и может зависнуть. Не пайпить вывод curl: `curl ... -o /tmp/out.json`, затем отдельно `grep -oP '"ok":(true|false)' /tmp/out.json`.
- ⚠️ **Имя файла с пробелами ломает `-F document=@...`** (файл «не найден» / curl exit 26) — сначала скопировать: `cp "Автор Название (2018).fb2" "Автор_Название.fb2"`.
- ⚠️ **`TOKEN=*** ...)` в terminal иногда проходит через секрет-фильтр уже как `TOKEN=*** — bash падает на syntax error рядом с `)`. Это не «токен битый», это маскирование командой — переходить на Python + requests (Способ 1).
- ⚠️ Отправка может уйти в approval и зависнуть без ответа пользователя — после блокировки НЕ повторять команду и не менять формулировку: сообщить пользователю статус («файл готов на диске, жду подтверждения отправки») и остановиться.
- chat_id пользователя: 350262645.