---
name: anthropic-claude-auth
category: devops
version: 1.0.0
author: Hermes Agent
license: MIT
description: Use when Claude по подписке (Claude Code) в Hermes.
metadata:
  hermes:
    tags: [anthropic, claude-code, oauth, profiles]
    related_skills: [hermes-ops]
---

# Anthropic / Claude по подписке (Claude Code) в Hermes

Общий setup провайдеров (KiloCode/DeepSeek/OpenRouter, `config set`, cron-модели) — в навыке `hermes-ops`.
Этот навык — про Anthropic-специфику: подписка вместо API-ключа и отдельный профиль под Claude.

## When to Use — когда браться за этот навык

- «Хочу общаться с моделями Claude через свою подписку» (Pro/Max), платить за API-токены не хочется
- Нужен отдельный профиль под Claude (свой агент рядом с остальными)
- Re-auth протухшего OAuth-токена, 401 при вызове Anthropic

## Шаг 0 — сначала выясни, что у пользователя УЖЕ есть

Один короткий вопрос до всего остального: аккаунт Claude уже есть? план Free/Pro/Max? чем входишь — Google, Apple или почта?

- Есть аккаунт с подпиской → не расписывай соглашения о регионах, номерах и картах. Это лишний текст, который читается как «ты не понял задачу». Сразу к авторизации.
- Пользователь просит именно Claude → не предлагай «более простой путь» через другие шлюзы (Kilo/OpenRouter). Это воспринимается как подмена задачи. Альтернативы озвучивай, только если он сам спросил, и только после проверки их работоспособности живым запросом.
- Способ входа (Google / Apple / почта) определяет, куда открывать ссылку и чем логиниться, — без него ссылку не выдавай.

## Гео: Россия не в списке Anthropic

РФ нет в `anthropic.com/supported-countries` (сверяйся с этим списком, не с блогами). Практические следствия:

- **Ссылка авторизации не открывается с российского IP** — ни с домашнего, ни с мобильного: страница Claude отдаёт ошибку. Это НЕ «протухшая ссылка», перевыпуск URL не поможет — сначала выясни, откуда пользователь её открывает.
- Номер телефона обязателен для всех новых аккаунтов; VoIP, Google Voice, номера из приложений и стационарные Anthropic отклоняет; один номер подтверждает максимум 3 аккаунта и потом не меняется.
- Подписка Pro/Max оплачивается картой поддерживаемой страны; IP, номер и карта должны сходиться в одну страну.
- Список поддерживаемых стран и правила телефона: `references/anthropic-regions-and-phone-verification.md`.

**Рабочий приём: авторизацию проводит сервер, а не телефон пользователя.** Сервер в поддерживаемой стране (у Василия — Нидерланды) открывает ссылку в headless Chrome, и страница логина Claude грузится нормально (виден выбор «Продолжить через Google / Apple / почту / SSO»). Пароль пользователь вводит сам через защищённое masked-окно (в чат не просить и не принимать), после чего код можно снять со страницы — копировать вручную не требуется.

```bash
# Chrome с CDP — нужен browser_exec, когда он ругается на недоступный BU_CDP_URL
/home/hermes/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome \
  --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-data-dir=/home/hermes/.hermes/cache/chrome-cdp about:blank
```

Запускать через `terminal(background=true)` — обёртки `nohup &`/`setsid` инструмент отклоняет; после старта проверить `curl -s http://127.0.0.1:9222/json/version`.

Ограничение приёма: он работает, когда вход — по почте/паролю. Если аккаунт на Google или Apple, masked-окно не поможет (чужой OAuth-провайдер и антибот) — тогда пользователь логинится сам из браузера с VPN на поддерживаемую страну.

## Шаг 1 — профиль

```bash
hermes profile create <name> --clone-from default
```

- Источник задаётся флагом `--clone-from <profile>`; просто `--clone` = клонировать активный профиль. Написать `--clone default` нельзя — argparse упадёт с `unrecognized arguments: default`.
- Клон **не** переносит мессенджер-каналы (bot tokens, allowlists) — это специально: копия токена заставит два gateway драться за один бот. Алиас-обёртка появляется в `~/.local/bin/<name>`.
- Профили не наследуют `.env` корня: если нужны ключи (поиск, инструменты), проверь `~/.hermes/profiles/<name>/.env`.

## Шаг 2 — авторизация (два пути)

### A. Hermes-native OAuth по подписке (Claude Code CLI не нужен)

```bash
hermes -p <name> auth add anthropic --type oauth
```

- Печатает ссылку `https://claude.ai/oauth/authorize?...` (PKCE, redirect `console.anthropic.com/oauth/code/callback`) и ждёт строку `Authorization code:`.
- Поток требует TTY — из gateway-сессии гоняй его в tmux:

```bash
tmux new-session -d -s cc-auth "hermes -p <name> auth add anthropic --type oauth"
sleep 10
tmux capture-pane -t cc-auth -p -S -120      # без -S URL уже проскроллен и не виден
tmux send-keys -t cc-auth '<code>' Enter     # код от пользователя
```

- Пользователь копирует код целиком, форма `<code>#<state>`: вторая часть проверяется как CSRF-guard, обрезанный код не примут.
- Ссылку отдавай дословно — она привязана к живой сессии.

### ⚠️ Ждать код в живом процессе нельзя — verifier сохраняй в файл

Интерактивный `auth add` живёт ровно столько, сколько живёт его процесс: PKCE-`code_verifier` держится в памяти. Как только сессия завершилась (таймаут, `/stop`, перезапуск, или пользователь ответил через час), полученный им код обменять уже нечем — он мусор, и человеку приходится проходить ссылку заново. Это читается как «ты гоняешь меня по кругу».

Правильный порядок, когда код добывает пользователь (а он почти всегда отвечает не мгновенно):

1. Сгенерировать PKCE и **сохранить `verifier` + `state` + сам URL в файл** — отдельным запуском, а не внутри интерактивного потока.
2. Отдать ссылку и спокойно ждать код: состоянию на диске ничего не угрожает.
3. Когда код пришёл — обменять его вторым запуском.

Модуль `agent/anthropic_credentials.py` даёт все нужные куски: `_generate_pkce()` → `(verifier, challenge)`, константы `_OAUTH_CLIENT_ID`, `_OAUTH_REDIRECT_URI`, `_OAUTH_SCOPES`; обмен — `_post_oauth_token(payload, content_type="application/json", timeout=25, what="exchange")`, где payload это JSON с `grant_type=authorization_code`, `code`, `state`, `redirect_uri`, `code_verifier`; запись — `_write_hermes_oauth_credentials(access_token, refresh_token, expires_at_ms)`.

Запускать такие скрипты интерпретатором Hermes и с home профиля:

```bash
HERMES_HOME=/home/hermes/.hermes/profiles/<name> \
  ~/.hermes/hermes-agent/.venv/bin/python3 /path/script.py
```

- venv — именно `~/.hermes/hermes-agent/.venv` (каталога `venv/` рядом нет), плюс `sys.path.insert(0, "/home/hermes/.hermes/hermes-agent")` в самом скрипте.
- Скрипт писать файлом через `write_file` и запускать `python3 <file>` — см. питфоллы 8–9 ниже.
- Успех проверяй по факту сохранённого токена (файл/ответ `_write_hermes_oauth_credentials`), а не по «процесс не ругнулся».

### B. Через Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
claude setup-token        # браузерная авторизация
```

- Креды падают в `~/.claude/.credentials.json`; Hermes подхватывает их сам — в `hermes model` → Anthropic покажет «Claude Code credentials: ✓ (auto-detected)». Копировать токен в `.env` не нужно.
- Альтернатива: тот же setup-token можно положить в `.env` как `CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_TOKEN`.

## Срок жизни токена — без него авто-обновления не будет

Токен-эндпоинт возвращает **`expires_in` (секунды), а не абсолютную дату**: сохраняй `expiresAt = int((time.time() + expires_in) * 1000)` в оба файла (`~/.hermes/profiles/<name>/.anthropic_oauth.json` и `~/.claude/.credentials.json`).

Механизм: при falsy `expiresAt` валидатор считает токен живым, пока есть `accessToken`, — значит до первого 401 Hermes его не обновляет, а к моменту 401 refresh-токен может быть уже мёртв (`invalid_grant: Refresh token not found or invalid`), и тогда лечится только новым логином. Один пропущенный `expires_in` стоит пользователю ещё одной ссылки и ещё одного кода — а он этого не прощает.

Диагностика (живой `GET /v1/models`) — `scripts/anthropic_live_models.py`. Нужны заголовки `Authorization: Bearer <access>`, `anthropic-version: 2023-06-01`, **`anthropic-beta: oauth-2025-04-20`**, `User-Agent: claude-code/2.0.0`; без beta-заголовка запрос не проходит. Тот же скрипт печатает реальный список моделей аккаунта.

## Шаг 3 — модель и проверка

```bash
hermes -p <name> model                      # интерактивно → Anthropic
# либо явно:
hermes -p <name> config set model.provider anthropic
hermes -p <name> config set model.default <claude-model-id>
hermes -p <name> chat -q "OK"               # проверка живым запросом
```

Список моделей: живой `GET https://api.anthropic.com/v1/models` + курируемый список в `hermes_cli/models.py` (`_PROVIDER_MODELS["anthropic"]`); `hermes model` показывает объединение.

## Шаг 4 — открыть Claude во ВСЕХ профилях (в том числе в чате Telegram)

Профили — изолированные острова: креды, полученные через `hermes -p <name> auth add anthropic`, видит ТОЛЬКО этот профиль. В чате gateway (профиль `default`) список `/model` останется из DeepSeek/Kilo/Copilot, и Anthropic там не появится — сколько раз ни перезапускай поток авторизации.

Рабочий способ (проверено живым запросом): положить токены в «родной» стор Claude Code — Hermes подхватывает его как borrowed login во всех профилях (`auth.adopt_external_logins` по умолчанию `true`):

```json
// ~/.claude/.credentials.json
{"claudeAiOauth": {"accessToken": "…", "refreshToken": "…", "expiresAt": null,
                   "scopes": ["user:inference", "user:profile", "org:create_api_key"]}}
```

- Писать через temp-файл + `os.replace`, права `600`.
- `expiresAt` заполнять обязательно: при falsy-значении Hermes считает токен живым до первого 401 и **не обновляет** его (механизм — в разделе «Срок жизни токена»).
- Копия профильного `~/.hermes/profiles/<name>/.anthropic_oauth.json` в корневой `~/.hermes/.anthropic_oauth.json` сама по себе кредов не даёт: `hermes chat -q … --provider anthropic` отвечает `No Anthropic credentials found`. Не трать на это итерацию — сразу пиши файл Claude Code.
- Проверка на default-профиле: `hermes chat -q "ты кто и какая модель?" -m claude-sonnet-4-5-20250929 --provider anthropic`.

Готовые скрипты двухшагового PKCE: `scripts/anthropic_oauth_step1.py` (печатает ссылку и сохраняет `verifier`+`state` в файл) и `scripts/anthropic_oauth_step2.py '<code>#<state>'` (обмен кода на токены + запись в home профиля). Раскладка кредов по всем профилям — `scripts/claude_code_credentials.py <путь к .anthropic_oauth.json профиля>`.

## Порядок разрешения токена (диагностика 401)

`ANTHROPIC_TOKEN` / `CLAUDE_CODE_OAUTH_TOKEN` → `ANTHROPIC_API_KEY` → OAuth-гранты Hermes (`~/.hermes/.anthropic_oauth.json`, пул `auth.json`) → `~/.claude/.credentials.json` (или macOS Keychain «Claude Code-credentials»).

- OAuth-токены: `sk-ant-oat…`, `eyJ…`, `cc-…`; API-ключи: `sk-ant-api…` — Hermes различает их по префиксу.
- OAuth-идентичность работает только на нативном антроповском роуте (provider `anthropic` / host `api.anthropic.com`): сторонние Anthropic-совместимые эндпоинты на Claude Code-заголовках отдают 401/403.
- Протухший OAuth без валидных Claude Code кредов → `hermes model` считает, что кредов нет, и предлагает re-auth. Это ожидаемо, не баг.

## Pitfalls

1. **`claude setup-token` требует подписку Claude Pro/Max.** Для API-ключевого аккаунта выбирай в `hermes model` вариант «Anthropic API key» — иначе поток упадёт в браузере.
2. **OAuth-поток без TTY бесполезен** — запускай в tmux/PTY и забирай URL из `capture-pane -S`.
3. **Смена модели профиля — три поля.** `model.default`, `agent.model`, `delegation.model`; оставленные старыми поля утащат агента или субагентов на прежний провайдер.
4. **Не дублируй креды.** Если Hermes уже видит `~/.claude/.credentials.json`, лишний `CLAUDE_CODE_OAUTH_TOKEN` в `.env` перекроет авто-подхват и протухнет первым.
5. **Ссылку не отдавай как «нажми в Telegram».** Встроенный браузер Telegram не имеет сессии claude.ai, а с российского IP страница вообще не открывается. Либо отдавай ссылку вместе с инструкцией «открывать с VPN на поддерживаемую страну», либо проводи вход на сервере.
6. **Подписка ≠ API-ключ.** Для Pro/Max путь один — `--type oauth`; совет «добавь API-ключ» звучит как «заплати дважды» и только путает.
7. **Проверяй баланс шлюза, прежде чем предлагать его как рабочий путь.** Новый профиль может ответить 402 (`Low Credit Warning`) — это внешний баланс провайдера, а не поломка профиля. Пробный `POST /chat/completions` с моделью провайдера показывает это за один вызов, до того как ты пообещаешь пользователю рабочий вариант.
8. **Скрипты запускай файлом, а не heredoc.** `python3 - <<'PY' … PY` и подстановки `$(...)` внутри одной команды распознаются сканером как исполнение сгенерированного кода: команда ждёт подтверждения пользователя и без ответа за минуту возвращает `BLOCKED: … do NOT retry, do NOT rephrase`. Обходить это нельзя — пиши скрипт через `write_file` в `~/.hermes/cache/scratch/` и запускай `python3 <путь>`.
9. **Интерпретатор — `.venv` Hermes, иначе падает на импортах.** Системный `python3` не видит зависимости Hermes (`No module named 'ruamel'`). Рабочий запуск: `HERMES_HOME=/home/hermes/.hermes/profiles/<name> ~/.hermes/hermes-agent/.venv/bin/python3 <script>`.
10. **Креды профиля не видны другим профилям.** Новый профиль с Claude ≠ Claude в чате Telegram: у gateway свой профиль (`default`), и его `/model` читает только его креды. Решение — файл Claude Code из Шага 4, а не повторная авторизация.
11. **Список провайдеров в `/model` внутри gateway может остаться старым.** Процесс держит каталог с момента запуска — после добавления кредов предложи `/restart` (или перезапусти gateway), прежде чем делать вывод «не подхватилось».
12. **Список моделей провайдера в `/model` — это кэш, и он бывает fallback-ом.** Каталог читается из `$HERMES_HOME/provider_models_cache.json`; запись с `"fallback": true` — курируемый список Hermes, а не модели аккаунта (живой фетч идёт по API-ключу и с OAuth-кредой возвращает пусто). Признак: в списке нет свежих моделей и висят устаревшие. Что делать: снять реальные id через `scripts/anthropic_live_models.py` и либо вписать их в кэш (сохранив `fp`, выставив `fallback: false`), либо просто дать пользователю id и попросить ввести его руками — пикер принимает произвольное имя. `/model --refresh` кэш сбрасывает, но пустой живой фетч вернёт тот же fallback.
13. **Мёртвую tmux-сессию видно по панели.** Если `tmux list-panes -t <sess> -F "#{pane_current_command}"` показывает `sleep` (или панель пустая), дочерний `hermes auth add` уже завершился и PKCE-verifier потерян. Код пользователя обменять нечем — не трать его, перезапусти шаг 1 и выдай новую ссылку.
