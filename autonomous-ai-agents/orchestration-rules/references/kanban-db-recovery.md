# Kanban DB Corruption Recovery

## Симптом
`hermes kanban list` выдаёт:
```
kanban: could not initialize database: Refusing to open corrupt kanban DB
at ~/.hermes/kanban.db: integrity_check returned 'wrong # of entries in
index idx_notify_task'.
```
Hermes автоматически создаёт backup: `~/.hermes/kanban.db.corrupt.<timestamp>.bak`.

## Восстановление (чистая БД)

Python `sqlite3.backup()` **НЕ помогает** — сохраняет коррупцию индекса.

Рабочий способ — удалить БД и дать Hermes создать новую (чистая, без задач):

```bash
rm -f ~/.hermes/kanban.db
hermes kanban list
```

## Восстановление с сохранением задач

Если задачи важны и их нужно восстановить, нужно извлечь данные из corrupt DB через Python:

```python
import sqlite3
# Попытка восстановить данные из corrupt DB
conn = sqlite3.connect('~/.hermes/kanban.db')
# Если integrity_check падает, но SELECT работает — можно выгрузить данные
tasks = conn.execute("SELECT * FROM tasks").fetchall()
```

После этого создать новую БД и вставить записи обратно, либо просто создать задачи заново через `hermes kanban create`.

## Профилактика

- База в `~/.hermes/kanban.db` (SQLite, один файл)
- Бэкап не предусмотрен штатно — при повреждении теряются активные задачи
- Для важных долгих задач — дублируй во внешнюю систему (Obsidian, трекер)