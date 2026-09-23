# Карта данных gtsync (обновлено 21.09.2026)

## State `~/.hermes/tasks/gtsync.json`

```json
{
 "tasks": {"216": {"gt": "dDNLMW80T2pqdXFHQ3l0cw", "sig": "Стирка спортивной формы|2026-09-21"}},
 "habit_cards": {"12:2026-09-21": "djdwVXdsZE94U1lyRDBUOQ"},
 "cal": {"1": "<google_event_id>"},
 "cal_hash": "<digest привычек с time>"
}
```

- `sig = f"{'❗ ' if prio=='H' else ''}{name}|{due[:10]}"` — ВСЕГДА оба конца пишут в одном формате, иначе вечный ре-патч.
- `tid` (ключ `tasks`) — строка; `id` в БД — int. Приведения через `str()`/`int()`.

## Порядок шагов sync_tasks (важен!)

1. google-удалённые (gt исчез из списков) → `t cancel`, pop из state, **handled.add**
2. google-completed + local pending/backlog → `t done`, pop, **handled.add**
3. local done/cancelled + gt still needsAction → patch completed / delete
4. push/patch локальных pending+backlog (скип `str(lid) in handled`)
5. pull google-карточек без маркера → `t add` c `GT_SYNC_OFF=1`, патч маркера на карточку, google_id в БД, state claim

## Google Tasks REST (проверено live)

- `insert(tasklist, body={title,notes,due})` — ok
- `patch(tasklist, task, body={title|notes|due|status})` — ok (status: needsAction/completed)
- `delete(tasklist, task)` — ok
- `list(tasklist, showCompleted=True, showHidden=True, maxResults=500)` — ok
- `updatedMin` — delta-листинг ok
- `move` — НЕ работает в python-клиенте (kwargs-ловушка); перенос между списками только delete+insert
- У ресурса `task` НЕТ полей: recurrence, множественные отметки, время (только дата due)

## Calendar (для привычек со временем)

```python
body = {
  "summary": f"🔁 {name} ({time})",
  "start": {"dateTime": iso_msk, "timeZone": "Europe/Moscow"},
  "end": {"dateTime": iso30m, "timeZone": "Europe/Moscow"},
  "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO,TU,..."]  # or FREQ=DAILY
  "reminders": {"useDefault": False, "overrides": [{"method":"popup","minutes":10}]},
}
```
Digest cal_hash меняет состав событий только при изменении списка привычек с time — пересоздаёт ВСЕ (удаление старых best-effort).

## Импорт хуков в `t`

`t` вызывает `/usr/bin/python3 tasks_api.py` субпроцессом (не импортирует — иначе тянет googleapiclient в каждый чих CLI). Костяк `gt_cli`:

```python
if os.environ.get("GT_SYNC_OFF"): return "", "sync off", 1
r = subprocess.run(["/usr/bin/python3", GT_TASKS_API, *gargs], capture_output=True, text=True, timeout=10)
return r.stdout.strip(), r.stderr.strip(), r.returncode
```

## Запуск/обвязка

```bash
~/.hermes/scripts/gtsync.sh [--dry-run] [--no-calendar]   # = PYTHONPATH=... python3 gtsync.py
# cron: gtsync-5min (16dda29a4852), no_agent, deliver=local
# лог действий (не-пустые прогоны): ~/.hermes/logs/gtsync.log
```
