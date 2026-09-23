# Kanban Create — актуальный синтаксис

**Важно:** флаги `--profile`, `--goal`, `--notify` НЕ СУЩЕСТВУЮТ. Они были в ранних версиях CLI, но заменены.

## Правильная команда

```bash
hermes kanban create \
  --assignee <profile_name> \
  "Заголовок задачи" \
  --body "Подробное описание задачи" \
  [--skill <skill_name>] \
  [--workspace dir:/home/hermes/projects/<repo>]
```

## Флаги

| Флаг | Назначение | Пример |
|------|-----------|--------|
| `--assignee` | Какой профиль выполняет | `--assignee skill-improver` |
| `title` (позиционный) | Заголовок задачи | `"Доработать навык X"` |
| `--body` | Подробное описание | `"--body 'Проблема: ...'"` |
| `--skill` | Загрузить навык воркеру (повторяемый) | `--skill memory-auto-manager` |
| `--workspace` | Тип рабочего пространства | `--workspace dir:/home/hermes/projects/<repo>` (для кода; worktree под ВЕТО 21.09.2026) |
| `--priority` | Приоритет | `--priority high` |
| `--parent` | Родительская задача | `--parent t_abc123` |

## Примеры

```bash
# Исследование
hermes kanban create --assignee researcher "Исследовать: цены на билеты Мск-Нукус" --body "Даты 10-17 июля. Найди мин. цену на каждую дату."

# Доработка навыка (с загрузкой навыка воркеру)
hermes kanban create --assignee skill-improver --skill memory-auto-manager "Доработать навык" --body "Проблема: ..."

# Код в общем репо (worktree запрещён — только dir: + последовательно)
hermes kanban create --assignee coder "Fix: баг" --body "Описание" --workspace dir:/home/hermes/projects/<repo>

# Ревью
hermes kanban create --assignee reviewer "Review PR #42" --body "Проверить: ..."
```

## Редактирование тела задачи — НЕ существует

`hermes kanban update` — команда НЕ СУЩЕСТВУЕТ. `hermes kanban edit` — только меняет result/summary/metadata у **completed** задач, не тело.

Чтобы изменить тело/заголовок/assignee задачи:
1. Архивируй старую: `hermes kanban archive <task_id>`
2. Создай новую с правильным телом

## ⚠️ `--skill` crash pitfall

Флаг `--skill <name>` загружает навык в worker. **НО worker видит только то, что есть в его профиле** (`~/.hermes/profiles/<name>/skills/`). Если навык глобально существует, но в профиль не симлинкнут — worker падает с `Error: Unknown skill(s): <name>` и уходит в бесконечный цикл крашей.

**Проверка перед `--skill`:**
```bash
# Найди категорию глобального навыка
ls ~/.hermes/skills/*/<skill-name>/ 2>/dev/null
# Проверь что он есть в профиле
ls ~/.hermes/profiles/<profile>/skills/*/<skill-name>/ 2>/dev/null
```

**Если нет — создай симлинк:**
```bash
ln -sf ~/.hermes/skills/<category>/<skill-name> ~/.hermes/profiles/<profile>/skills/<category>/<skill-name>
```

**Безопасная альтернатива:** не указывай `--skill` — worker использует skills из toolsets. `--skill` нужен только для специфических навыков (вроде `memory-auto-manager` для coach).

## Уведомления

Отдельная команда (обязательно после создания задачи, иначе результат уйдёт в никуда):

```bash
hermes kanban notify-subscribe <task_id> --platform telegram --chat-id 350262645
```