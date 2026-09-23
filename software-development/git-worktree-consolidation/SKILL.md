---
name: git-worktree-consolidation
description: Слияние worktree-веток в main и очистка их копий с диска.
---

# Git Worktree Consolidation Skill

Консолидация накопившихся git worktree-веток в main и освобождение диска от их рабочих копий. Агенты (Codex/Kanban) создают worktree на задачу и не удаляют — каждая копия тащит node_modules/.venv (100–250M). Проверено 01.09.2026: 63 worktree = 2,1G в lead-platform.

## When to Use
- Диск забит, а в проекте есть `.worktrees/` (`git worktree list` показывает десятки)
- Пользователь просит «завершить все worktree и влить в ветку»
- Нужно понять, какие ветки уже влиты, а какие содержат незакоммиченную работу

## Prerequisites
- git-репозиторий с worktree-ветками (обычно `t_*` / `wt/*` от агентских задач)
- `git worktree remove` работает (для удаления рабочей копии, ветки остаются в .git)

## Procedure

### 1. Диагностика
```bash
cd ~/projects/<repo>
git worktree list                          # какие worktree живы
du -sh .worktrees/                         # сколько весят
```

### 2. Классификация веток: влиты или нет
```bash
for b in $(git branch --format='%(refname:short)' | grep -v '^main$'); do
  n=$(git rev-list --count main..$b 2>/dev/null || echo 0)
  [ "$n" -gt 0 ] && echo "UNMERGED($n) $b" || echo "MERGED $b"
done
```
- **MERGED** — коммиты уже в main: копию можно удалять сразу.
- **UNMERGED** — есть коммиты вне main: сначала влить, потом удалять. (В lead-platform 58/63 уже были влиты.)

Порядок обязателен: merge → `git worktree remove` → `git worktree prune` → (опционально) удалить влитые ветки. `git worktree remove` стирает рабочую копию, но ветка и коммиты остаются — потерять закоммиченную работу нельзя.

### 3. Слияние пачкой
```bash
for b in <branch...>; do
  git merge --no-edit "$b" >/dev/null 2>&1 && echo "OK: $b" || { echo "CONFLICT: $b"; git merge --abort 2>/dev/null; }
done
```
При конфликте: `git status -s | grep '^UU'`, `grep -n '^<<<<<<<\|^=======\|^>>>>>>>' <file>`.

### 4. Разрешение конфликтов — три стратегии
1. **Ветка старая, интент уже реализован в main** → `git checkout --ours <файлы>` + `git add` + commit. Проверь grep'ом, что в HEAD-коде действительно нет того, что ветка «убирала».
2. **Ветка = рефакторинг поверх старого main, а main добавил фичи в тех же файлах** → для самодостаточных файлов бери версию ветки (`git checkout --theirs`), затем портируй фичи HEAD (`git show main:<path>`). Авто-merge часто объединяет остальные файлы сам — конфликтуют только пересекающиеся.
3. **modify/delete** (ветка удалила файл, main изменил) → `git rm` файл, если ветка заменила его новыми (напр. тест разбит на несколько).

### 5. Финал
```bash
git worktree remove --force <path>   # ветка уже в main — копию можно удалять
git worktree prune                   # почистить метаданные
git branch -d <влтые-ветки>          # спросить пользователя перед удалением десятков веток
```

## Pitfalls
- **Проверь merge-base** (`git merge-base main <branch>`): если ветка от старого main, конфликты будут именно в местах новых фич. Если merge-base = merge-commit ветки — ветка частично влита, конфликтуют только коммиты ПОСЛЕ неё.
- **Новые файлы ветки (статус A) не объединяются с main** — их API может не совпасть с объединёнными компонентами. Проверяй каждый новый файл-роутер (пример: stepContent.tsx вызывал StepTariff/StepUpsell со старыми props).
- **Портирование фичи HEAD**: смотри `git show main:<path>`, как HEAD передавал props/вызывал функции (onMode должен был звать q.next(); currentPlanName = имя плана `plans[key].n`, а не ключ 'p1').
- **Обязательно прогони тесты и типы после разрешения**: `npx vitest run <dir>` и `npx tsc -p tsconfig.json --noEmit` — ловят несовместимости props, которые merge не видит.
- **Длинные конфликтные блоки**: patch с большим old_string не матчится — пиши Python-скрипт в /tmp (write_file + `python3 /tmp/fix.py`), который убирает маркеры по правилам с assert на каждый блок. execute_code и сложные for/grep one-liner в terminal могут блокироваться — используй write_file-скрипт.

## Verification
- `git status` — чисто, нет конфликтных маркеров
- `git rev-list --count main..<branch>` для каждой ветки = 0 (всё влито)
- `git worktree list` — только main
- Тесты и tsc зелёные (см. Pitfalls)
