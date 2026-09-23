# Multi-Agent Improvement Roadmap

> Source: Conversation with Василий (2026-06-03), inspired by KiloCode newsletter
> "How 7 Kilo Code Engineers Run Up to 20 Parallel Agents and Still Ship Clean Code"

## User constraints (Василий)

- Все профили на deepseek (KiloCode). Plan/Execute разделение по моделям НЕ нужно.
- Токены — ресурс. Любое улучшение должно минимизировать расход.
- Self-improvement — только напоминания. Решение о внедрении принимает пользователь.
- Verification loop — можно, если reviewer дёшевый (max_turns=12, deepseek).

## Phase 1 — Background fire-and-forget tasks

**Идея:** Некоторые задачи не требуют approval gate. Агент делает → комитит → результат падает в Telegram.

**Когда использовать background:**
- Рефакторинг (переименование, выделение функций)
- Обновление зависимостей
- Добавление/фикс тестов
- Мелкие фиксы (typos, renaming, formatting)
- Документация

**Когда НЕ background (foreground с gate):**
- Новая фича
- Смена архитектуры
- Критичный баг
- Любая задача, где пользователь хочет видеть промежуточные решения

**Реализация:**
1. Body задачи начинается с `[background]` маркера
2. Создаётся с `--initial-status ready` (не blocked)
3. Подписка notify-subscribe есть, но gate пропускается
4. Агент делает работу → `kanban_complete` → результат в Telegram
5. Оркестратор показывает итог без предварительного approval

## Phase 2 — Verification loop (auto-review)

**Идея:** После каждой foreground coder-задачи создаётся reviewer-задача с parent link. Результат — проверенный код, не нужно переделывать.

**Правила экономии токенов:**
- Reviewer на deepseek (та же модель, без overhead)
- `max_turns=12` (достаточно для чтения diff + вывода verdict)
- Тело reviewer: только «Проверь что код соответствует Done when из родительской задачи»
- Если всё ок → `kanban_complete(approved=True)`
- Если issues → `kanban_comment` с конкретикой + `kanban_block`

**Когда добавлять:**
- Foreground coder-задачи (проходят approval gate)
- НЕ добавлять для background задач (Phase 1) — они и так мелкие
- НЕ добавлять для researcher/debugger — у них другой пайплайн

## Phase 3 — File size discipline (from architect)

**Идея:** Architect разбивает модули на мелкие файлы (≤200 строк). Меньше контекста → меньше ошибок → легче ревьюить.

**Реализация:**
В тело любой architect-задачи добавлять правило:
> Constraints: Каждый файл — не больше 200 строк. Если модуль больше — разбивай на несколько файлов с чёткими границами ответственности.

Зашить в GCCD-шаблон для architect (см. gccd-framework.md).

## Phase 4 — Self-improvement reminders

**Идея:** Не автомат, а напоминание. Раз в неделю — сводка: сколько задач сделано, какие профили лидируют, есть ли повторяющиеся проблемы.

**Формат (коротко, без разжёвывания):**
```
На неделе завершено N задач.
— Coder: M задач, среднее время X мин
— Researcher: K задач, Y источников
— Reviewer: Z задач, одобрено P%, blocked Q%
Стоит что-то улучшить в профилях/навыках?
```

Пользователь сам решает, нужно ли что-то менять.

## Phase 5 — Metrics & observability (research)

**Идея:** Посмотреть Kanban SQLite — какие данные собираются, можно ли сделать дашборд/отчёт.

**Текущий статус:** исследовать. Без конкретных обязательств.
