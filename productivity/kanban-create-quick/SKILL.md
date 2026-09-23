---
name: kanban-create-quick
description: Шпаргалка по созданию Kanban-задач одной командой — без угадывания флагов.
tags: [kanban, hermes, productivity]
---

# Kanban Create Quick

**Перед созданием любой Kanban задачи — загрузи этот навык: `skill_view('kanban-create-quick')`.**

## Когда НЕ создавать Kanban задачу

**Bulk file/script operations → run directly via terminal, NOT via Kanban.**

Если задача сводится к запуску существующего Python/shell скрипта на массиве файлов (например, пройти по всем .md в vault и добавить frontmatter), не создавай Kanban задачу. Kanban спавнит LLM-агента, который будет обрабатывать каждый файл через LLM-цикл — это дорого и бессмысленно, когда ту же работу делает локальный скрипт за секунды.

**Признаки «не Kanban, а terminal»:**
- Задача = запустить один скрипт с флагами (уже написан)
- Обработка N файлов без LLM-логики (простое преобразование)
- Результат можно проверить одной командой (`gitmark.py lint --strict`)
- Нет потребности в рассуждениях/анализе — только выполнение

**Как делать вместо Kanban:**
```bash
cd /path/to/vault && python3 ~/.hermes/scripts/gotham-ensure-frontmatter.py --all --mode=add-missing
```

Или через `terminal()` напрямую. Проверить результат — отдельным вызовом. Закоммитить — ещё одним. Ноль токенов на LLM.

**Пример из реальной сессии (пользователь поправил):**
- ❌ Создал Kanban-задачу на worker для `gotham-ensure-frontmatter.py --all` (371 файл)
- ✅ Правильно: запустил скрипт напрямую через terminal() — 385 файлов, 0 токенов потрачено
- Реакция пользователя: *"нет я хочу по умному, щас все деньги мне сожрешь"*

**Kanban задачи нужны когда:**
- Нужен анализ, синтез, рассуждение
- Надо искать информацию в интернете
- Код пишется с нуля (не просто запуск готового скрипта)
- Нужно ревью, решение, архитектурное решение

Для «запустить скрипт и проверить результат» Kanban не нужен.

## Базовая команда (одна строка)

```bash
hermes kanban create "Название задачи" \
  --body "Описание задачи" \
  --assignee coder \
  --initial-status blocked \
  --priority 1
```

## Параметры (ключевые)

- **title** — позиционный аргумент, НЕ `--title`. Просто строка в кавычках.
- **`--assignee`** — профиль: `coder`, `researcher`, `self-improver`, `worker`, `architect`, `reviewer`, `debugger`, `skill-improver`
- **`--initial-status blocked`** — всегда blocked (потом unblock + dispatch). Никогда не создавать сразу ready.
- **`--priority`** — **integer**, не string. `1` = высший, `5` = низший. Никаких `critical`/`high`.
- **`--body`** — описание задачи. Если длинное — пиши в файл (см. ниже).
- **`--goal`** — для открытых/исследовательских задач (self-improver, researcher). Включает цикл judge-проверки.
- **`--goal-max-turns N`** — бюджет повторов для --goal (default 20). Для сложных задач увеличивай до 40-50.
- **`--max-runtime`** — ограничение по времени. `30m`, `2h`, `1d`.
- **`--json`** — вывод в JSON (удобно для скриптов).
- **`--skill SKILL`** — форсировать загрузку **навыка** (skill) у воркера. Принимает только имена навыков из `skills_list` (например, `kanban-worker`, `systematic-debugging`). ⚠️ **НЕ путай с `--assignee`!** `coder`, `self-improver`, `researcher` и т.п. — это профили/assignee, а не навыки. Передача имени профиля в `--skill` вызывает краш диспетчера с `Error: Unknown skill(s): profile-name`.

## Передача body (важно!)

Стандартный closing для any задачи — см. `references/standard-closing.md`.

Если body короткий (1-2 строки без кавычек/спецсимволов):
```
--body "Короткое описание"
```

Если body длинный или содержит кавычки/`$`/`` ` `` — пиши в файл:
```bash
cat > /tmp/task-body.md << 'EOF'
## Проблема
...
EOF
hermes kanban create "Title" --body "$(cat /tmp/task-body.md)" --assignee X --initial-status blocked --priority 1
```

**Никогда не вставляй многострочный body с кавычками прямо в командную строку** — shell ломается, получаешь 10 лишних вызовов.

## Полный lifecycle

```bash
# 1. Создать
hermes kanban create "Title" --body "..." --assignee X --initial-status blocked --priority 1

# 2. Подписать на уведомления
hermes kanban notify-subscribe T_ID --platform telegram --chat-id 350262645

# 3. Показать пользователю → получить OK
# 4. Разблокировать и запустить
hermes kanban unblock T_ID && hermes kanban dispatch

# 5. Через 30-60с проверить статус
hermes kanban show T_ID

# 6. Если задача упала/crashed — НЕ ретраить вслепую.
#    Сначала проверь логи: `hermes kanban log T_ID`. Там сразу видна причина
#    (например, `Unknown skill(s): ...`). Исправь причину, потом ретрай.

# 7. Если задача timed_out (Iteration budget exhausted) — увеличь max_turns
#    на профиле (coder до 100, researcher до 100) и dispatch снова.
#    Пример: hermes --profile coder config set agent.max_turns 100
#    Задача retry-нется автоматически при unblock+dispatch.

# 8. После завершения — gateway шлёт файл с результатом автоматически.
#    Если задача завершилась без artifacts, gateway сам создаст .md из summary
#    (см. references/gateway-artifact-fallback-patch.md).

# 9. Результат — сразу в чат пользователю, не ждать пока спросит

# 10. Для последовательных задач (B зависит от A) — используй parent link
#     Создай все задачи как blocked, потом свяжи:
#     hermes kanban link t_parent_id t_child_id
#     Parent link работает автоматически: дочерняя задача разблокируется
#     когда родительская завершена. Не нужно unblock вручную.
```

## Что писать в body задачи (про доставку результата)

**С 10.06.2026:** gateway сам создаёт .md файл из summary если worker не передал `artifacts`
(патч `_deliver_kanban_artifacts` fallback). Но **рекомендуется** по-прежнему требовать
`artifacts` в body — worker может отформатировать результат лучше, чем сырой summary.

**Рекомендуемая строчка в конце body:**
```
После завершения сохрани результат в /tmp/{TASK_ID}-result.md
и вызови kanban_complete(summary=кратко, artifacts=['/tmp/{TASK_ID}-result.md']).
НЕ используй clarify — в Kanban нет пользователя.
```

**Критично:** без `notify-subscribe` notifier не срабатывает вообще — ни текст, ни файл
не доставляются. Подписка обязательна.

## Правила структурирования Research-задач

При создании Kanban-задач для исследовательского профиля (`--assignee researcher`):

- **Каждая независимая тема — отдельная задача.** Не объединяй несколько исследовательских вопросов в одну задачу, даже если они тематически близки.
- Признаки «одна тема»: вопрос можно сформулировать одним предложением, ответ не требует cross-reference нескольких разных источников/методологий.
- Пример ✅: три задачи — «Анализ районов Нукуса» / «Рынок цен на 1-к квартиры» / «Проверка физ лиц онлайн»
- Пример ❌: одна задача — «Всё про квартиры в Нукусе» (районы + цены + юр. проверка)
- Почему: каждая тема требует разного типа источников и методологии. В одной задаче researcher переключается между контекстами, теряет фокус, результат поверхностный.
- **Запускать параллельно** — они независимы, нет последовательной зависимости.

**Исключение:** если пользователь явно сказал «сделай одну задачу на всё» — тогда объединяй.

## Типовые ошибки (из реальных сессий)

1. ❌ `--title "..."` → ✅ title — позиционный, без флага
2. ❌ `--priority critical` → ✅ `--priority 1`
3. ❌ Длинный body с кавычками в inline-строке → ✅ файл + `--body "$(cat ...)"`
4. ❌ `kanban edit` для добавления body к существующей задаче → ✅ `kanban comment T_ID "текст"`
5. ❌ Создал без `--initial-status blocked` → задача сразу уходит в работу без подтверждения пользователя
6. ❌ Забыл `notify-subscribe` → пользователь не получает уведомления о завершении
7. ❌ Не проверил статус через 30-60с → пользователь ждёт результат
8. ❌ Передал имя профиля (`self-improver`, `coder`, `researcher`) в `--skill` → диспетчер падает с `Unknown skill(s): X`. `--skill` только для реальных навыков из `skills_list`, профили — только в `--assignee`
9. ❌ `kanban_complete(summary=текст)` без `artifacts` → summary обрезается в Telegram (лимит 4096 символов). Всегда передавай `artifacts=['/tmp/{TASK_ID}-result.md']` с файлом результата.
10. ❌ **CLI-завершение из main-сессии: `hermes kanban complete T_ID --artifacts путь` — такого флага НЕТ.** У CLI-команды `complete` флаги только: `--result` (итог), `--summary` (структурированный handoff для downstream-задач), `--metadata` (JSON-словарь фактов, напр. `'{"changed_files": [...], "tests_run": 12}'`). Артефакты/ссылки на файлы передавать в тексте `--result` или в `--metadata`. Проверять: `hermes kanban complete --help`. (ВНИМАНИЕ: `artifacts=` существует у инструмента `kanban_complete` внутри воркера — это НЕ то же самое, что CLI!)
10. ❌ Создал тестовую Kanban-задачу без `notify-subscribe` → notifier не срабатывает, fallback artifacts не доставляются. Тестировать Kanban notifier можно только на подписанных задачах.
11. ❌ После изменения `gateway/run.py` (кода Hermes) не перезапустил gateway → патч на диске, но не в памяти. `systemctl --user restart hermes-gateway` обязателен.
12. ❌ Показал пользователю код изменений вместо того, чтобы протестировать живьём. После внесения изменений (особенно в код Hermes) — сразу создай тестовую задачу и проверь, что оно работает. "Покажи diff" ≠ "докажи что работает".
13. ❌ Удалил навык (`english-lesson`), не проверив cron jobs → `study-reminder` и `study-reminder-1830` ссылались на него и упали с error. **Перед удалением навыка — проверь `hermes cron list`, не ссылается ли какой-то cron job на него (`skills` поле).**
14. ❌ `enabled_toolsets: ["web"]` для крона `evening-reminder` → воркер не мог отправить сообщение. `enabled_toolsets` ограничивает инструменты крона. **Не используй без крайней необходимости. Лучше оставить пустым (все инструменты по умолчанию), чем получить неожиданный сбой.**
15. ❌ **`..` в названии задачи, привязанной к репо** («Этап 8: доработка (M-1..M-2)`) → title транслитерируется в git-ветку (`lead-platform/t_*-8-m-1..m-2`) → git: `'...' is not a valid branch name` → `spawn_failed` ×2 → auto-block. **НЕ использовать `..` (и `?*[~^:\`) в title** задач с `--project`. Если читаемость нужна — «M-1..M-2» только в body, в title пиши «M-1 M-2». Обработка: `hermes kanban archive T_ID` → пересоздать с корректным title (parent/body те же) → notify-subscribe → unblock → dispatch.
17. ❌ **[LEGACY — worktree под ВЕТО с 21.09.2026] Мержишь ветку worktree-задачи по «угаданному» имени** → `git merge lead-platform/t_5f9e7def-ai-template` → `merge: ... not something we can merge`. Реальная ветка генерится из title со slug-нормализацией и НЕ совпадает с ожидаемой (`t_5f9e7def-9-ai-template-tdd` — там есть этап и суффикс). Проверено 3 раза за сессию 21.08.2026. **Фикс: точное имя ветки смотри в `git branch -a | grep t_<id>` (или `git worktree list | grep t_<id>` — показывает ветку ворктри).** Или `hermes kanban show T_ID` → Events → `branch_name: lead-platform/t_<id>-<slug>`. Только потом merge + push.
18. ❌ **Достаёшь task_id из `hermes kanban list --format json | python3 ...`** → падает `JSONDecodeError` (флаг формата не отдаёт JSON как ожидается). Надёжно: ID задачи берётся прямо из вывода `create` (`Created t_xxxx`) — сохрани его в переменную/заметку и используй для `notify-subscribe`/`unblock`/`dispatch`. Не пытайся парсить список.
19. ❌ **Все Kanban-задачи крашатся с `SyntaxError` при старте** — проверить `~/.hermes/hermes-agent/tools/terminal_tool.py` на наличие незакрытых git-merge маркеров (`<<<<<<< HEAD`, `=======`, `>>>>>>>`). Один такой конфликт в любом core-файле (особенно `terminal_tool.py`, `cli.py`) ломает импорт tools, и все Kanban-воркеры падают на `_install_tool_callbacks()` ещё до старта задачи. **Симптом:** `hermes kanban log T_ID` показывает `SyntaxError: invalid syntax in terminal_tool.py:1154`. **Фикс:** найти и удалить все маркеры конфликта, корректно объединить код. Проверить: `python3 -c "compile(open('tools/terminal_tool.py').read(), 'terminal_tool.py', 'exec')"`.

| Профиль | Когда |
|---|---|
| `coder` | Написание кода, фиксы, баги |
| `researcher` | Поиск, цены, факты, исследование |
| `debugger` | Root cause analysis |
| `architect` | Spec, архитектура, требования |
| `reviewer` | Ревью кода |
| `worker` | Рутина, скрипты, Obsidian, t-команды |
| `self-improver` | Анализ неудач, план исправлений |
| `skill-improver` | Анализ навыков, обновление |

**Важно:** self-improver и skill-improver — только для плана/анализа. Исполнение плана — отдельная задача на coder/worker.
