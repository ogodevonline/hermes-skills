## curl exit codes for Telegram file delivery

- **Exit 0** + `"ok":true` — успех
- **Exit 26** — CURLE_READ_ERROR: файл не существует по указанному пути. Проверь `ls -la`
- **Exit 3** — URL malformat: токен битой. Use `grep -oP`, не `source`
- **Exit 7** — Failed to connect: нет сети

## Проверка токена (shell-safe, без маскировки)

```
grep -oP 'TELEGRAM_BOT_TOKEN=\K.*' ~/.hermes/.env | head -1
```

## Успешная отправка JSON-файла (рабочий шаблон)

```
TOKEN=$(grep -oP 'TELEGRAM_BOT_TOKEN=\K.*' ~/.hermes/.env | head -1)
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendDocument" \
  -F "chat_id=350262645" \
  -F "document=@/path/to/file.json" \
  -F "filename=file.json" \
  -F "caption=Описание"
```

## Проверка результата

Успех: `"ok": true` + `"document": {"file_name": "..."}`.
Фейл: `"ok": false` + `"description": "..."`.
