# GitHub Search через curl (fallback когда gh не работает)

## Когда использовать

Когда нужно найти репозиторий/проверить существование проекта на GitHub,
а `gh search repos` не работает (токен протух, нет `read:org` scope).

## Команды

### Поиск репозиториев по названию

```bash
source ~/.hermes/.env
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/search/repositories?q=insta_flat_parser" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{r['full_name']} — {r.get('description','')[:80]}\") for r in d['items']]"
```

Если `total_count: 0` — репозитория **не существует публично с данным токеном**. Это точный ответ, не нужно лезть в web-search.

### Получить информацию о конкретном репозитории

```bash
source ~/.hermes/.env
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/owner/repo" | python3 -m json.tool
```

### Поиск по разным keywords

```bash
# Разные варианты названия
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/search/repositories?q=insta+flat+parser&per_page=5"
```

## Private репозитории: 404 или 0 результатов ≠ не существует

GitHub API и `gh` ищут **только в доступных токену репозиториях**. Если пользователь утверждает, что репозиторий есть, а API возвращает 404/пусто:

**Возможные причины:**
- Репозиторий приватный, и у токена нет к нему доступа
- Репозиторий на **другом аккаунте** (не том, на который выдан токен)
- Репозиторий существует **только локально** у пользователя, на GitHub его нет
- Репозиторий на другом хостинге (GitLab, Bitbucket, собственный сервер)

**Что делать:**
1. Спроси пользователя: `git remote -v` — URL покажет настоящего владельца
2. Если remote указывает на GitHub — проверь, какой аккаунт в URL
3. Если remote на GitLab/Bitbucket/свой сервер — GitHub API не поможет, нужны другие инструменты

## Важно

- Токен в `~/.hermes/.env` под именем `GH_TOKEN` — это **классический PAT**, без `read:org` scope
- `gh auth login --with-token` **упадёт** с `missing required scope 'read:org'` — это нормально
- API GitHub через curl **работает без `read:org`** для поиска и чтения репозиториев
- Если `GH_TOKEN` замаскирован security scan (показывает `***`) — используй `source ~/.hermes/.env` в terminal
