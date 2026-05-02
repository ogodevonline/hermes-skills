---
name: evening-diary-fsm
description: Конечный автомат для интерактивного вечернего дневника (без блокирующего input())
category: productivity
---

# Конечный автомат вечернего дневника

## Зачем создан
Обычные скрипты с `input()` блокируют выполнение в cron и не работают при запуске из Telegram-бота. Нужна была система сбора статусов задач и рефлексии через асинхронные сообщения (чат → ответ → следующий вопрос).

## Как работает
- **Состояние** хранится в `~/.hermes/.evening_state.json`
- **Команды:**
  - `--start` — инициализация, задать первый вопрос
  - `--answer "<text>"` — сохранить ответ, получить следующий вопрос или финальный дневник
- Интеграция с ботом: сообщение пользователя передаётся как `--answer`, ответ ботом — текст из stdout

## Структура состояния
```json
{
  "phase": "tasks|q1..q5",
  "task_idx": 0,
  "answers": {"Задача": "✅", "Вопрос": "Ответ"},
  "tasks": ["Задача 1", "Задача 2"]
}
```

## Вопросы дневника
1. Что сегодня прошло ХОРОШО?
2. Где я облажался / можно лучше?
3. Главный урок / инсайт дня:
4. На что обратить внимание завтра?
5. Deep Work (часы фокуса):

## Вывод
- Статусы задач (✅⏳❌) собираются из tasks.yml
- Ответы сохраняются по мере поступления
- По завершении генерируется Markdown (`~/.hermes/diary/YYYY-MM-DD.md`)
- Состояние сбрасывается

## Пример использования (CLI)
```bash
~/.hermes/scripts/brief_evening_fsm.py --start
~/.hermes/scripts/brief_evening_fsm.py --answer "⏳"
~/.hermes/scripts/brief_evening_fsm.py --answer "Ничего не вышло"
```

## Пример интеграции с Telegram ботом
```python
result = subprocess.run(
    [sys.executable, 'brief_evening_fsm.py', '--start'],
    capture_output=True, text=True
)
bot.send_message(chat_id, result.stdout.strip())

# На следующее сообщение от пользователя:
result = subprocess.run(
    [sys.executable, 'brief_evening_fsm.py', '--answer', msg.text],
    capture_output=True, text=True
)
bot.send_message(chat_id, result.stdout.strip())
```

## Итог
Скрипт позволяет вести дневник через чат без блокирующих вызовов, с сохранением прогресса между сообщениями и автоматической генерацией итогового отчета.