# Vault Path Audit — полная процедура

> Когда vault-папки переименовываются или обнаруживается stale-путь.
> Цель: найти и исправить ВСЕ вхождения, а не только очевидные.

## Триггеры
- Файл не найден по ожидаемому пути (command not found / file not found)
- Пользователь сказал «смотри где ещё может быть» или «везде меняй»
- Обнаружен русский путь в английской системе
- Миграция папок (рус → англ или любая другая)
- Пользователь сообщил о stale-пути

---

## Фаза 0 — Определи полный набор stale-путей

**НЕДОСТАТОЧНО** проверять только известные пути из прошлой миграции.
ВСЕГДА выполняй полный рейд:

```bash
cd ~/hermes-vault

# 0a. Папки с русскими символами
find . -maxdepth 4 -type d -name "*[а-яА-Я]*" | grep -v ".obsidian" | grep -v "System/Gotham" | sort

# 0b. Файлы с русскими символами в имени
find . -maxdepth 4 -type f -name "*[а-яА-Я]*" | grep -v ".obsidian" | grep -v "System/Gotham/report-" | sort

# 0c. Wikilinks с русскими путями ([[папка/файл]])
grep -rn "\[\[[а-яА-Я].*/" --include="*.md" | grep -v ".obsidian/" | grep -v "System/Gotham/report-" | grep -v '\[\[Добро пожаловать'
```

Это найдёт ЛЮБЫЕ русские имена, включая те, что не в списке миграции.

---

## Фаза 1 — Найди ВСЕ вхождения в vault

```bash
# Для каждого найденного в Фазе 0 пути
for p in "${STALE_PATHS[@]}"; do
  echo "=== $p ==="
  grep -rln "$p" --include="*.md" | grep -v ".obsidian/" | grep -v "System/Gotham/report-" | sort
done
```

Категории находок:
1. **Wikilinks** `[[СтарыйПуть/файл]]` в Area файлах, профилях, Journal/
2. **System/Docs/** — документация (evening-brief-flow.md, system-map.md, vault-structure.md)
3. **System/audits/** — старые аудиты (добавить outdated notice)
4. **System/AgentsData/Worker/** — исторические agent memories (добавить outdated notice)
5. **Journal/YYYY-MM-DD.md** — старые дневники с битыми викилинками
6. **Areas/Profile/** — викилинки в index.md, experience/_index.md
7. **Areas/Contacts/_index.md** — викилинки на людей/группы
8. **Projects/README.md, Projects/Planning/** — пути проектов

---

## Фаза 2 — Найди вхождения в skills и scripts

```bash
cd ~/.hermes

# В активных SKILL.md (не .legacy/)
for p in "${STALE_PATHS[@]}"; do
  grep -rn "$p" skills/ --include="SKILL.md" | grep -v ".legacy/"
done

# В SKILL.md .legacy/ — может загрузиться вместо основного!
for p in "${STALE_PATHS[@]}"; do
  grep -rn "$p" skills/ --include="SKILL.md" | grep ".legacy/"
done

# В scripts/*.py
for p in "${STALE_PATHS[@]}"; do
  grep -rn "$p" scripts/ --include="*.py"
done
```

**Особо проверь:**
- Вкладка node_type → path в vault-frontmatter/SKILL.md (таблица `| Areas/Contacts/люди/ | person |`)
- Canonical path определения в vault-structure/SKILL.md (раздел Contacts)
- Примеры путей в contacts/SKILL.md (древо файлов)
- Примеры путей в universal-planner/SKILL.md (`План.md`)

---

## Фаза 3 — Исправь всё одним пакетом

### Если нужно переименовать ПАПКИ:
```bash
cd ~/hermes-vault
mv Areas/Contacts/группы Areas/Contacts/groups  # пример
```

### Если нужно исправить ТЕКСТ внутри файлов:
`patch` с replace_all=true для массовых замен.

### Если нужно отметить исторические файлы:
Добавь в начало (после frontmatter):
```
> **⚠️ УСТАРЕЛО (15.06.2026):** [описание]. Оставляю файл как исторический артефакт.
```

### Порядок исправления:
1. **Переименовать директории** (mv)
2. **Переименовать файлы** (mv) — внутри переименованных папок
3. **Wikilinks** → patch
4. **System/Docs/** → patch по одному
5. **Skills** → patch всех упоминаний (включая таблицы node_type, примеры древа, pitfall'ы, changelog)
6. **Agent memories** → добавить outdated notice поверх
7. **Audits** → добавить outdated notice поверх
8. **Memory** → memory(action='replace', target='memory')

---

## Фаза 4 — Перепроверь

```bash
# В vault — не должно остаться русских имён папок/файлов/викилинков
cd ~/hermes-vault
find . -maxdepth 4 -type d -name "*[а-яА-Я]*" | grep -v ".obsidian" | grep -v "System/Gotham"
find . -maxdepth 4 -type f -name "*[а-яА-Я]*" | grep -v ".obsidian" | grep -v "System/Gotham/report-"
grep -rn "\[\[[а-яА-Я].*/" --include="*.md" | grep -v ".obsidian/" | grep -v "System/Gotham/report-"

# В skills
grep -rn "люди/\|группы/\|Дневник/\|Планирование/\|Проекты/\|профиль\|Привычки/\|~/obsidian/\|План\.md\|архитектура-агентов" ~/.hermes/skills/ --include="SKILL.md" --include="*.md" | grep -v ".legacy/" | grep -v "УСТАРЕЛО\|migration\|cтарый\|бывш\|changelog\|История"
```

Допустимо:
- Migration reference таблицы (старый→новый по смыслу)
- User-facing сообщения (напр. «✅ Дневник сохранён!»)
- Файлы с пометкой УСТАРЕЛО
- История изменений (changelog), где упоминается «до: Х, после: Y»

---

## Фаза 5 — Commit + Memory

```bash
cd ~/hermes-vault && git add -A && git commit -m "fix: migrate stale paths ..."
```

Обновить memory:
`memory(action='replace', target='memory', old_text='<prev vault paths entry>', content='All vault paths are English: Journal/, Projects/Planning/, Areas/Profile/, Areas/Habits/, Areas/Contacts/groups/, Areas/Contacts/people/...')`

Записать в память ПОЛНЫЙ список английских путей, чтобы в следующей сессии не повторить.

---

## Что НЕ надо трогать

- **System/Gotham/report-*.md** — исторические отчёты linter'а. Трогать нельзя.
- **Имена файлов-контента** (семья.md, оля-мама.md, василий.md) — это имена людей/групп, не системные пути. Можно оставить на русском.
- **Заголовки в Journal/YYYY-MM-DD.md** — «# 📖 Дневник — 2026-06-13» это пользовательский контент, не путь.
- **Migration reference таблицы** — они специально показывают старый→новый.

---

## Уроки (почему в прошлый раз не получилось)

1. **Поправил только один файл** — пользователь сказал «исправляй память», я исправил только память. Нужно было сразу grep ВСЁ.
2. **Не проверил System/Docs/** — stale документация заражает последующие сессии.
3. **Не вычистил битые викилинки** — `[[профиль-пользователя/...]]` продолжали ссылаться в никуда.
4. **Не добавил outdated notice в agent memories** — исторические файлы с обратной миграцией сбивают с толку.
5. **Не обновил memory запись о путях** — в следующей сессии снова та же ошибка.
6. **Урок 15.06.2026:** Проверял только известный список stale-путей, а нужно было сделать полный рейд по русским символам. Нашёл `группы/`, `люди/`, `Узбекистан-2026/`, `План.md`, `архитектура-агентов`, `Анализ-работы-researcher` — только через `find` по кириллице.
7. **Урок 15.06.2026:** После переименования папок — обнови все навыки, которые определяют эти пути как canonical (vault-structure, vault-frontmatter, contacts). Иначе навык будет указывать на несуществующую папку.
