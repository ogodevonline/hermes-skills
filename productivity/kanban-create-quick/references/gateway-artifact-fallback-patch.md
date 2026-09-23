# Gateway Artifact Fallback Patch

## Что это

Патч в `gateway/run.py` — функция `_deliver_kanban_artifacts`. Если Kanban-завершение пришло с `summary` но без `artifacts`, gateway сам сохраняет summary во временный `.md` файл и отправляет его как вложение.

## Где патч

**Файл:** `/home/hermes/.hermes/hermes-agent/gateway/run.py`
**Строки:** 5662-5674 (вставлены в `_deliver_kanban_artifacts`)

```python
# 4. Fallback: if no file paths found but there's a summary,
#    save it as a temp .md file and deliver that instead.
if not candidates and isinstance(summary, str) and summary:
    task_id = getattr(task, "id", None) if task is not None else None
    fallback_path = f"/tmp/kanban-{task_id or 'unknown'}-result.md"
    try:
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(summary)
        _add(fallback_path)
    except (OSError, IOError) as exc:
        logger.warning(
            "kanban notifier: fallback summary-to-md write failed: %s", exc,
        )
```

## Postinstall auto-apply

**Скрипт:** `~/.hermes/scripts/postinstall-apply-artifact-fallback.py`
**Триггер:** post-merge git hook в `/home/hermes/.hermes/hermes-agent/.git/hooks/post-merge`

Проверяет, есть ли уже патч (поиск комментария "Fallback: if no file paths"), если нет — вставляет.

## История

- **10.06.2026:** Создан. Run 349 timed out (50 max_turns), run 350 completed (после увеличения до 100). Патч установлен, скрипт проверки создан.
- **10.06.2026 (фикс):** Обнаружено, что notify-subscribe обязателен — без него notifier не обрабатывает задачу, fallback не срабатывает. После рестарта gateway и теста с подпиской — всё работает. Файл приходит как нативный аттач.

## Важные условия работы

1. **Нужен notify-subscribe.** Патч срабатывает только для задач, подписанных на уведомления (`hermes kanban notify-subscribe T_ID --platform telegram --chat-id 350262645`). Без подписки notifier не обрабатывает события задачи — fallback не вызывается.
2. **Нужен рестарт gateway.** Изменения `gateway/run.py` не вступают в силу до перезапуска gateway (`systemctl --user restart hermes-gateway`). Патч на диске ≠ патч в памяти процесса.
3. **Срабатывает только для completed.** `_deliver_kanban_artifacts` вызывается только для события `completed`. При `crashed`, `gave_up`, `timed_out` — файл не шлётся.
