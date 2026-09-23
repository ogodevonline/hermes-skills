# Kanban — создание задачи со сложным телом

## Проблема

`hermes kanban create --body "..."` — тело в кавычках. Если в теле есть кавычки, 
доллары, обратные кавычки, shell-метасимволы — команда ломается.

`--body-file <path>` — НЕ СУЩЕСТВУЕТ в этой версии.

## Решение: Python subprocess скрипт

1. Напиши тело задачи в файл: `/tmp/body-<topic>.md`
2. Напиши Python скрипт, который читает файл и вызывает `hermes kanban create`
3. Запусти скрипт через `terminal`

### Шаблон Python скрипта

```python
#!/usr/bin/env python3
# /tmp/create_task.py
import subprocess

with open("/tmp/body-<topic>.md") as f:
    body = f.read()

cmd = [
    "hermes", "kanban", "create",
    "--initial-status", "blocked",
    "--assignee", "<profile>",
    "Заголовок задачи",
    "--body", body
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
if r.returncode == 0:
    print(f"OK: {r.stdout.strip()}")
else:
    print(f"FAIL: {r.stderr.strip()[:300]}")
```

### Особенности

- `--initial-status blocked` — задача не запустится пока не разблокировать
- После создания нужно: `notify-subscribe` → `unblock` → `dispatch`
- Тело читается из файла как есть — никакие shell-символы не опасны
- timeout=15с — достаточно для создания задачи
- `hermes kanban create` должен быть первой командой в `cmd` — работает без shell

## Alias hkc не работает в terminal tool

Bash alias `hkc="hermes kanban create --initial-status blocked"` работает 
только в интерактивном shell. В terminal tool (неинтерактивный) alias не подхватывается.
Используй полную команду или Python script.
