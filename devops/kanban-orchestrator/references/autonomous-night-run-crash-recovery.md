# Автономный ночной прогон TDD-пайплайна — worktree merge + crash recovery (20-21.08.2026)

Реальный прогон: этапы 5 → 6 → 7 платформы lead-platform, ~8 часов автономной работы оркестратора.
Пользователь снял approval gate: «меня дальше не спрашивай, надеюсь до утра все сделаешь».

## Последовательность на каждый этап (проверено 8+ раз подряд)

1. Создать граф: тесты (`blocked`, p=30) → реализации (`todo`, `--parent`) → ревью (`blocked`, p=10, `--parent` последней реализации)
2. Подписать ВСЕ задачи: `hermes kanban notify-subscribe <id> --platform telegram --chat-id <chat_id>`; проверить `notify-list | grep <id>`
3. unblock тесты → `hermes kanban dispatch --max 1`
4. Ждать: `python3 ~/.hermes/scripts/kanban_wait.py <id> --timeout 570 --interval 30` (повторять циклы)
5. После done: **ОБЯЗАТЕЛЬНО смержить worktree-ветку в main** (воркер не мержит сам):
```bash
cd ~/projects/<repo>
git branch -a | grep wt/          # найти ветку воркера
git merge wt/<branch> --no-ff -m "merge: <описание> (t_<id>)"
git push
git log --oneline -2              # свежий merge-коммит виден?
```
6. dispatch следующей задачи. Реализации строго последовательно (одно репо) — parent-связи сами держат порядок.

## Краш-паттерны и их разбор (реальные логи ночи)

### 1. «worker exited cleanly (rc=0) without calling kanban_complete or kanban_block — protocol violation»
Причина: deepseek thinking-loop — воркер генерирует объяснения вместо tool calls («the only winning move is to stop generating explanatory words»), исчерпывает итерации, CLI выходит rc=0 без вызова kanban_*.
- Диспетчер сам перезапускает (run N+1); 2-я/3-я попытка часто успешна
- Диагностика: `tail -30 ~/.hermes/kanban/logs/<id>.log` + `cd ~/projects/<repo>/.worktrees/<id> && git status --short`
- Если файлы уже написаны — перезапуск добьёт; если файлов нет после 15-20 мин — резать задачу

### 2. «Iteration budget exhausted (100/100)» дважды (этап 7A, 8 модулей 7.1-7.8)
Воркер пишет файлы в самом конце и не успевает прогнать тесты. Лечение:
- unblock + dispatch — новый воркер продолжает с незакоммиченных файлов в том же worktree (run #3 = done)
- Оценить остаток самому ДО перезапуска:
```bash
cd ~/projects/<repo>/.worktrees/<task_id> && ~/projects/<repo>/.venv/bin/python -m pytest <files> -q
```
⚠️ У worktree НЕТ своего `.venv` — использовать `.venv` главного чекаута.
- На будущее: реализации резать на 2-3 подзадачи плана, не 5-8

### 3. blocked review + дочерняя fix-задача застряла в todo
Fix-задача с `--parent <blocked-review>` не промоутится (dependency engine ждёт `done`).
```bash
hermes kanban complete <review_id> --summary "Вердикт: BLOCKED — findings в отчёте, переданы в доработку <fix_id>"
hermes kanban unblock <fix_id>
hermes kanban dispatch --max 1
```

## Результаты ночи (цифры для ориентира по времени)

| Этап | Тесты → Реализации → Ревью | Прогоны | Итог |
|---|---|---|---|
| 5 (чат/тикеты) | 6 задач | 170 pytest / 54 vitest | APPROVED после 1 цикла доработки |
| 6 (рабочие планы) | 5 задач | 185 pytest / 68 vitest | APPROVED после 1 цикла доработки (Enum) |
| 7A (инфраструктура ИИ) | тесты+реализация | 2× iteration budget → run #3 done | файлы 8 модулей + миграция f4a3c2b1e001 |

Среднее время задачи: тесты 10-25 мин, реализация 15-60 мин, ревью 10-20 мин (при ночной латентности deepseek 20-50с за вызов).
