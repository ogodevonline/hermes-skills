---
name: telegram-user-automation
description: "Telegram от имени владельца: бот-секретарь и userbot."
version: 1.0.0
author: Василий (Hermes Agent)
platforms: [linux]
metadata:
  hermes:
    tags: [telegram, secretary, business-bot, userbot, mtproto, клиенты]
    category: messaging
    related_skills: [sales-chat, channel-post]
---

# Telegram User Automation Skill

Как действовать в Telegram **от имени аккаунта владельца**, а не от имени бота. Два независимых пути: Business/Secretary-бот (штатный Bot API, ничего не ломает) и userbot (MTProto, полный доступ к аккаунту). Навык про личку и работу со списком диалогов; постинг в каналы — это `channel-post`.

## When to Use

- Ответить человеку в личке от имени Василия
- Писать первым / видеть список чатов / разобрать и почистить диалоги
- Выгрузить историю конкретного чата для разбора переговоров
- Настройка или починка Secretary Mode, проверка выданных прав

## Prerequisites

- `~/.hermes/tg-userbot/business_bridge.py` + `config.json` (токен секретарь-бота, chmod 600) — личные чаты
- `~/.hermes/tg-userbot/tg_dialogs.py` + `api.json` (api_id/api_hash) — список и удаление диалогов
- systemd-юнит `tg-business-bridge.service` (шаблон: `templates/tg-business-bridge.service`)
- Секретарь-бот должен быть **отдельным** от бота Hermes

## How to Run

**Личка (Bot API, api_id не нужен):**

- `python3 business_bridge.py chats` — живое ли подключение и выдан ли `can_reply`
- `python3 business_bridge.py inbox --limit 20` — что писали (входящие и исходящие владельца)
- `python3 business_bridge.py send --to <chat_id> --text "..."` — отправить от имени владельца
- `python3 business_bridge.py delete-msg --id <message_id>` — удалить отправленное ботом

**Диалоги аккаунта (MTProto, нужен api_id):**

- `tg_dialogs.py login` → `report` → `backup --ids <файл>` → `delete --file <файл>`

## Procedure

### 1. Поднять Secretary Mode

1. @BotFather → `/newbot` → отдельный бот
2. @BotFather → `/mybots` → Bot Settings → **Secretary Mode** (в 2026 так называется Business Mode)
3. Проверка до и после: `getMe` → `can_connect_to_business` (`false` до включения, `true` после)
4. Аккаунт: Настройки → Telegram Business → Чат-боты → username бота → выдать «Отвечать на сообщения» и «Читать сообщения»
5. Проверка прав: `business_bridge.py chats` → `can_reply=True`. Пока `False` — отправка не работает, даже когда подключение активно

### 2. Работа с личкой

Демон ловит `business_message` (и входящие, и исходящие владельца), пишет в `inbox.sqlite3`. Отправка — всегда с `business_connection_id` текущего подключения.

### 3. Чистка диалогов

`report` → классификация → согласование с владельцем → `backup` (страховка) → `delete` пачками с паузами и пережиданием `FloodWait`. По умолчанию без `--revoke`.

## Pitfalls

- **Один токен — один поллер.** Поллинг `getUpdates` тем же токеном, что у gateway Hermes, отбирает апдейты друг у друга — бот «перестаёт отвечать». Секретарь-бот всегда отдельный.
- **`can_reply=False` — самая частая поломка.** Подключение есть (`is_enabled=true`), а право не выдано. Лечится в карточке бота в «Чат-ботах», не в BotFather.
- **Бот видит только новые сообщения.** Истории до подключения нет, списка чатов нет, групп и каналов нет. Не обещать владельцу «прочитаю ваш чат с X», если X не писал после подключения.
- **Окно 24 часа.** Отвечать можно только в личке, где было входящее за последние сутки — официальная формулировка `can_reply`.
- **Направление сообщений.** `business_message` приходит и на сообщения владельца: без проверки поля `out` исходящие запишутся как входящие и картина переписки станет мусорной.
- **Демон должен жить вне Hermes.** Background-процесс умирает при обновлении или перезапуске — ставить systemd-юнит с `Restart=always`.
- **Отправка реальным людям — только с подтверждения владельца.** Близкие (Лима) — отдельный режим: тёплый тон, никаких сухих отписок, продаж там нет вообще.
- **Сессия = полный доступ к аккаунту.** `*.session` и `config.json` — chmod 600; напоминать владельцу, что сессию можно отозвать в «Устройствах».
- **`--revoke` необратим** — стирает переписку и у собеседника. Только по отдельному согласию.
- **api_id привязан к номеру один к одному** — если номер уже использовался, приложение не создаётся; см. `references/my-telegram-org-error.md`.

## Verification

- `business_bridge.py chats` → подключение есть, `can_reply=True`
- тест отправки: сообщение уходит и ложится в `inbox.sqlite3` как `out`
- `getWebhookInfo` → `pending_update_count: 0` (очередь не копится)
- после правки кода демона — `systemctl --user restart tg-business-bridge` и проверка лога

## References

- `references/business-bridge.md` — API бизнес-бота: флаги, права, методы, чего не умеет
- `references/client-chat-via-bridge.md` — ведение клиентской переписки: согласование текста, окно 24ч, диагностика застрявшего диалога
- `references/my-telegram-org-error.md` — почему my.telegram.org отдаёт ERROR и что делать
- `references/mtproto-dialogs.md` — разбор и удаление диалогов через userbot
- `templates/tg-business-bridge.service` — systemd-юнит для демона
