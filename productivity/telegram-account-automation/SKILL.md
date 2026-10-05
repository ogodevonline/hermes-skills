---
name: telegram-account-automation
description: Telegram messages as the user's own account (bot/userbot).
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [telegram, userbot, business-bot, secretary-mode, mtproto, telethon]
    category: productivity
---

# Telegram Account Automation Skill

Как дать агенту писать в Telegram **от имени владельца аккаунта**, а не от бота-собеседника.
Два независимых пути: официальный Business-бот (Secretary Mode) и MTProto-userbot.
Скилл не про отправку файлов владельцу (`telegram-file-delivery`) и не про посты в его канал (`channel-post`).

## When to Use

- «Хочу, чтобы ты писал от моего имени в личку» / «бот, подключённый в аккаунт».
- Нужно отвечать людям в Telegram от лица владельца или писать первым.
- Проверка/диагностика уже подключённого Business-бота или userbot-сессии.

## Prerequisites

- **Ветка A (Business-бот):** Telegram Premium у владельца (без него раздела *Telegram Business* в настройках нет), отдельный бот в @BotFather, Python 3.11 (только stdlib).
- **Ветка B (userbot MTProto):** `api_id`/`api_hash` с https://my.telegram.org, отдельный venv с `telethon` (ставится через `uv pip install --python <venv>/bin/python "telethon>=1.36,<2"`).
- Согласие владельца на то, что содержимое его личной переписки попадает в контекст агента — сказать об этом прямо до подключения.

## How to Run

Выбор ветки — по вопросу владельца, не по удобству:

- **Отвечать входящим от его имени** → Business-бот. Официально, без `api_id`, но `can_reply` работает только в личных чатах, где было входящее за последние 24 часа.
- **Писать первым кому угодно** → только userbot MTProto (`api_id` обязателен).
- **«И то и другое»** → обе ветки: Business для диалогов, userbot для инициативных сообщений.

Мост для ветки A: `scripts/business_bridge.py` (stdlib, без зависимостей).

```bash
cd ~/.hermes/tg-userbot
python3 business_bridge.py poll              # слушать входящие (демон/фон)
python3 business_bridge.py inbox --limit 20  # кто написал и что
python3 business_bridge.py chats             # есть ли подключение и право can_reply
python3 business_bridge.py send --to <chat_id> --text "..."
```

Токен — в `config.json` рядом со скриптом, права файла `600`. Токен в чате/логе не печатать.

## Quick Reference

- Диагноз «Secretary Mode выключен»: `getMe` → поле `can_connect_to_business: false`. Другого способа со стороны бота нет.
- Подключение: @BotFather → `/mybots` → бот → **Bot Settings → Secretary Mode**; затем в аккаунте **Настройки → Telegram Business → Чат-боты** → username бота → выдать права (минимум: отвечать, читать сообщения).
- Отправка от имени владельца: `sendMessage` с параметром `business_connection_id`, полученным из апдейта `business_connection`.
- Ошибка формы на my.telegram.org — см. `references/my-telegram-org-error.md`.

## Procedure

1. Выясни у владельца: отвечать входящим или писать первым (это определяет ветку, а не наоборот).
2. Ветка A: создать **отдельного** бота → включить Secretary Mode → прислать токен → проверить `getMe` на `can_connect_to_business: true`.
3. Запустить `poll` **до** подключения бота в аккаунт — так поймается апдейт `business_connection` с фактическими правами (`can_reply`).
4. Владелец подключает бота в Telegram Business и выдаёт права; проверить `chats`, затем отправить тестовое сообщение себе.
5. Ветка B: получить `api_id`/`api_hash`, авторизовать Telethon (номер → код из Telegram → облачный пароль при 2FA), файл сессии — `600`.

## Pitfalls

- **Тот же токен, что у Hermes-бота, — нельзя.** `getUpdates` отдаёт апдейты только одному поллеру: демон и гейтвей начнут перехватывать друг у друга, и владелец перестанет получать ответы Hermes. Business-бот всегда создаётся отдельным.
- **Проактивно писать первым Business-бот не может** — платформенное ограничение (`can_reply` только в чатах с входящим за 24 часа). Не обещать обратное; для этого нужна ветка B.
- **Массовые рассылки через userbot = бан аккаунта.** Отправка по одному человеку по команде владельца — норма; веерная рассылка — нет.
- **Файл сессии Telethon равносилен полному доступу к аккаунту без пароля.** Хранить на сервере с правами `600`, не пересылать в чат.
- **Не гуглить причину ERROR на my.telegram.org вслепую** — разбор причин и источники лежат в `references/my-telegram-org-error.md`; самая частая — подчёркивание в Short name и пустой Description.
- Не у всех аккаунтов Business-раздел доступен: он привязан к подписке, наличие которой надо спросить до начала работ.

## Verification

- Ветка A жива: `getMe` → `can_connect_to_business: true`, затем `business_bridge.py chats` показывает `can_reply=True`, тестовое сообщение доходит.
- Ветка B жива: скрипт печатает своё имя (`get_me()`), тестовое сообщение отправляется и видно в клиенте владельца.
- Факт успеха подтверждать реальным ответом API (`ok: true` + id сообщения), а не отсутствием ошибки в логе.
