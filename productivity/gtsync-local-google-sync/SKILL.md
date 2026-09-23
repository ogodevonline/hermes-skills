---
name: gtsync-local-google-sync
description: Двусторонний sync трекера t с Google Tasks/Calendar.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    category: productivity
    tags: [google, tasks, calendar, sync, sqlite, cron]
---

# Local ↔ Google Tasks Sync (gtsync)

## Что это
Двусторонняя синхронизация между SQLite-трекером `t` (задачи/привычки) и
Google Tasks + Google Calendar. Принцип: **Google = UI телефона** (там
пользователь вводит/отмечает), **локальная БД = мозг** (брифы, habit_log,
статистика, LLM-код). Построен и E2E-проверен 21.09.2026 после обсуждения
«Гугл вместо трекера?» — гибрид победил: у Google Tasks нет recurrence,
привычек по времени, множественных подходов и carry_over, а API не виден
брифам/статистике.

## Когда использовать
- Расхождение трекера `t` с Google Tasks/Календарем пользователя
- Починить/расширить sync, гонять вручную, добавить направление
- Дубли/зависшие карточки в TODAY/HABITS или state `gtsync.json`
- Любая двусторонняя синхронизация «локальная SQLite <-> облачный сервис»
  этого профиля (паттерны переносимы)

## Артефакты
| Файл | Роль |
|------|------|
| `~/.hermes/scripts/gtsync.py` | sync-цикл (pull/push задач, карточек привычек, календаря) |
| `~/.hermes/scripts/gtsync.sh` | обёртка крона (google-библиотеки видны и без PYTHONPATH) |
| cron `gtsync-5min` (job id 16dda29a4852) | no_agent, каждые 5 мин, deliver=local, тихий (пустой stdout = чисто) |
| `~/.hermes/tasks/gtsync.json` | state: `tasks{local_id→{gt,sig}}`, `habit_cards{"hid:date"→gt}`, `cal{hid→event_id}`, `cal_hash` |
| `~/.hermes/logs/gtsync.log` | журнал прогонов (только при непустых действиях) |
| хуки в `t` (`gt_cli/gt_push/gt_touch/habit_card_done`) | мгновенный push на `add/done/cancel/postpone/habit-done`; живой файл: `~/.hermes/skills/productivity/personal-task-tracker/scripts/t` (симлинк `~/.local/bin/t`) |
| `~/.hermes/scripts/gtsync_phone_{add,complete,uncheck}.py` | симуляторы телефона для E2E-регрессии — не удалять |

Google list id (захардкожены в `t` и gtsync.py):
⛅ TODAY `VDhuNDh2enVHY1I3TlBtUQ`, 📥 BACKLOG `MDM0ODI5NzY3OTIxMTU4MDMzOTQ6MDow`,
🌱 HABITS `Y0c3NGFIRThRTnlWNFRpMg`; аккаунт `svaaugust`, токен
`~/.hermes/google_token_svaaugust.json` (scope tasks).

## Протокол соответствия
- notes карточки задачи: `local:#<task_id>`; карточки привычки: `habit:#<habit_id> date=<YYYY-MM-DD>`
- карточка БЕЗ маркера в TODAY/BACKLOG = создана с телефона → pull: `t add`
  с `category=google` (с `GT_SYNC_OFF=1`), затем патчем вешается маркер НА
  СУЩЕСТВУЮЩУЮ карточку — новую не создавать!
- колонка `tasks.google_id` — дубль маппинга для хуков `t` (state gtsync.json —
  источник истины для sync-цикла)
- префикс `❗ ` в Google = приоритет H; единый sig = `"{title}|{YYYY-MM-DD}"`
  (due всегда усекать до 10 символов — иначе вечные ре-патчи)
- привычки с `time` → recurring-события календаря `🔁 имя (HH:MM)`, RRULE из
  `habits.days` (Mon→MO…), popup за 10 мин; пересборка только при смене
  hash-дайджеста таблицы habits (`cal_hash`)

## Directions (шаги sync_tasks)
1. карточка исчезла из Google → `t cancel`
2. карточка completed + локально pending/backlog → `t done`
3. локально done → complete карточки; cancelled → delete карточки
4. push/patch pending+backlog с изменённым sig или без маппинга
5. pull карточек без маркера (см. протокол выше)
Привычки: карточка сегодня completed + habit_log пуст → `t habit-done`;
наоборот — хук `habit-done` закрывает карточку. Карточки старше вчерашнего
дня чистятся.

## Pitfalls (все — реальные кейсы первого боевого прогона 21.09.2026)
1. **Двойной пул:** pull звал `t add`, а у `t` хук push → дубль карточки в
   Google. Лечится env `GT_SYNC_OFF=1` при subprocess-вызове `t` из gtsync
   (`gt_cli` делает no-op, если он стоит).
2. **Stale-снапшот ре-пушится:** `local_tasks()` читается ДО шагов 1–2, которые
   меняют статусы; шаг 4 толкал «удалённую» задачу обратно. Лечится множеством
   `handled` (id из шагов 1–2 пропускаются в шаге 4).
3. **Фильтр по created_at** (`>= '2026-09-01'`) молча не пускал в Google
   вчерашние живые задачи. Отбор — только `status IN (pending,backlog)` + id из
   state (для done/cancel-детекта).
4. **Heredoc `python3 - <<'PY'` блопится хардлайном терминала** — одноразовые
   Google-операции писать файлом (`/tmp/x.py`) и звать `python3 x.py`.
5. **patch tool + argparse:** врезка между `add_parser(...)` и его
   `set_defaults(cmd=...)` привязывает команду НЕ туда. После правки парсеров —
   перечитать блок main().
6. **`move()` googleapiclient Tasks не работает** (неизвестный kwarg) — смена
   списка = delete в старом + insert в новом.
7. **`delete`/`complete` привязаны к списку:** карточка из TODAY не удаляется
   id из BACKLOG (404).
8. **dry-run не должен трогать `cal_hash`/писать state** — иначе реальный прогон
   пропустит создание событий (digest совпадёт, events пустые).
9. **Идемпотентность = приёмка:** два прогона подряд → второй печатает 0
   действий. Проверять после любой правки gtsync.
10. **Не сносить свои файлы shell-цепочкой с rm** (случайно удалил gtsync.py
    посреди правки) — rm отдельной командой с явным списком.

## How to Run / Debug
```bash
python3 ~/.hermes/scripts/gtsync.py --dry-run      # план без записи
python3 ~/.hermes/scripts/gtsync.py --no-calendar  # без пересборки календаря
python3 ~/.hermes/scripts/gtsync.py                # полный цикл (он же в кроне)
tail ~/.hermes/logs/gtsync.log                     # история действий
# регрессия «телефон → локально»:
python3 ~/.hermes/scripts/gtsync_phone_add.py add   # карточка «с телефона»
python3 ~/.hermes/scripts/gtsync.py --no-calendar   # → появится в t list (одна!)
python3 ~/.hermes/scripts/gtsync_phone_complete.py E2E
python3 ~/.hermes/scripts/gtsync.py --no-calendar   # → t cancel / t done дома
```
Рассинхрон state/Google: сверить `gtsync.json` с
`SELECT id,google_id,status FROM tasks`; разовые фиксеры — `gtsync_*_once.py`
в `~/.hermes/scripts/` (пример: `gtsync_dedup_once.py` — claim карточек +
удаление дублей из BACKLOG).

## Установка заново (другая машина)
1. OAuth аккаунт со scope tasks (skill `google-workspace`, при нехватки scope —
   `google-workspace-reauth-expand-scopes`)
2. Создать tasklist'ы ⛅ TODAY / 📥 BACKLOG / 🌱 HABITS, вписать id в `t` и gtsync.py
3. Колонка `google_id` — миграцией `add_days_column()` в `t` (уже есть)
4. Крон: `cronjob create no_agent=true script=gtsync.sh schedule="every 5m" deliver=local`

## Verification
Приёмка 21.09.2026 пройдена живыми прогонами: push; pull-add (id 227);
pull-delete → `t cancel`; phone-complete → `t done`; `t habit-done` → карточка
completed в Google; phone-check привычки → habit_log +1 (затем откат тестовых
отметок + reopen карточек `gtsync_phone_uncheck.py`); двойной прогон = 0
действий. Неизвестное состояние — `--dry-run` + лог, БД руками не править
(только через `t`).