# Standard Kanban Task Closing

## Правило

В конец тела **каждой** Kanban-задачи ОБЯЗАТЕЛЬНО дописывать closing инструкцию. Без неё worker не знает, как завершить задачу.

## Шаблон

```
После завершения:
1) сохрани результат в /tmp/{TASK_ID}-result.md
2) вызови kanban_complete(summary=кратко, artifacts=['/tmp/{TASK_ID}-result.md']).
3) НЕ используй clarify — в Kanban нет пользователя.
```

## Почему так

- **`artifacts=[путь]`** — worker сам форматирует результат как файл (читаемый .md)
- **Gateway fallback** (с 10.06.2026): если worker не передал artifacts, gateway сам сохраняет summary в `/tmp/kanban-{task_id}-result.md` и шлёт как файл. Но это fallback — результат идёт как сырой текст summary, без структуры.
- **Файл** — gateway шлёт как нативный аттач (sendDocument), без обрезания
- **Нет `clarify`** — в Kanban нет пользователя, спрашивать некого
- **`summary`** — краткая строка, первая строка идёт в текстовое уведомление
- **`notify-subscribe` обязателен** — без подписки notifier не запускается вообще

## Пример

```markdown
После завершения:
1) сохрани результат в /tmp/t_xxx-result.md
2) вызови kanban_complete(
       summary="Готов отчёт по X: 5 источников, 3 рекомендации",
       artifacts=['/tmp/t_xxx-result.md']
   )
3) НЕ используй clarify — в Kanban нет пользователя.
```

## История

- **До 10.06.2026:** closing без artifacts — результат обрезался в Telegram
- **С 10.06.2026:** closing с artifacts + файл — полный результат доставляется как вложение
