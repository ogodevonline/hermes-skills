---
name: telegram-account-bridge
description: "Писать в Telegram от имени владельца: бот или userbot."
version: 1.0.0
author: Hermes Agent
platforms: [linux, macos]
metadata:
  hermes:
    tags: [telegram, business, secretary-mode, mtproto, userbot, личные-сообщения]
    category: social-media
    related_skills: [channel-post, telegram-file-delivery, vps-service-deployment]
---

# Telegram Account Bridge Skill

Как действовать от имени личного аккаунта Telegram: читать личные чаты, отвечать за владельца, править и удалять отправленное. Разбирает три уровня доступа и что каждый реально умеет. Не про посты в каналы (это channel-post) и не про рассылки.

## When to Use

- «Пиши от моего имени», «ответь этому человеку», «посмотри, что мне написали»
- Нужно видеть новые сообщения в личке и отвечать на них
- Нужно выгрузить список диалогов или почистить чаты (только userbot)
- Бот подключён, но не может что-то сделать — понять, это лимит платформы или настройка

## Prerequisites

- Отдельный бот в @BotFather. Не тот, через которого работает Hermes: Telegram отдаёт апдейты только одному поллеру, два процесса на одном токене передерутся
- Telegram Premium у владельца аккаунта (Business-режим без него не включается)
- Для userbot — api_id/api_hash с my.telegram.org, см. references/business-bot-limits.md

## How to Run

Всё живёт в `~/.hermes/tg-userbot/`:

- `business_bridge.py poll` — слушает новые сообщения личных чатов в базу
- `business_bridge.py inbox --limit 20` — кто что написал
- `business_bridge.py send --to <chat_id> --text "..."` — отправить от имени владельца
- `business_bridge.py delete-msg --id <msg_id>` — удалить своё отправленное
- `business_bridge.py chats` — проверка подключения и права can_reply
- `business_bridge.py media --chat <id> --limit 5` — выгрузить картинки из чата

Слушает демон `tg-business-bridge` (systemd --user), логи в `poll.log`.

## Quick Reference: три уровня доступа

**Обычный бот** — пишет только тем, кто нажал /start. Первым в личку написать нельзя. Для «пиши от моего имени» не подходит.

**Business-бот (Secretary Mode)** — то, что обычно называют «подключить бота в аккаунт». Без api_id. Верифицированные границы (Bot API, `BusinessBotRights`):

- `can_reply` — «send and edit messages in the private chats that had incoming messages in the last 24 hours». Только личка и только внутри суточного окна от входящего
- `can_read_messages` — пометка входящих прочитанными
- `can_manage_stories` — посты, правка и удаление **историй** от имени владельца
- Каналов нет вообще, списка диалогов нет, истории до момента подключения нет

**MTProto userbot** — единственный путь к `messages.getDialogs` (список) и `messages.deleteHistory` (удаление), оба помечены «Only users can use this method». Файл сессии равнозначен полному доступу к аккаунту без пароля.

## Procedure

### 1. Подключение Business-бота (проверено рабочим)

1. @BotFather → `/newbot` → отдельный бот, получить токен.
2. `/mybots` → Bot Settings → **Secretary Mode** → включить.
3. Проверить флаг: `getMe` → `can_connect_to_business` должен стать `true`. Пока `false` — аккаунт к боту не подключится.
4. В аккаунте: Настройки → **Telegram Business** → **Чат-боты** → добавить username бота. Права живут в карточке самого бота, а не в списке: открыть бота → «Управление сообщениями» → **Отвечать на сообщения** (обязательно) + **Читать сообщения**.
5. Проверить права: `getBusinessConnection` → `rights.can_reply` должен быть `true`. Без него подключение есть, а отправка не работает.
6. Запустить поллер сервисом: см. `templates/tg-business-bridge.service`.

### 2. Отправка и правка

Отправка `sendMessage` с `business_connection_id`; удаление — `deleteBusinessMessages` с `business_message_id`. Удалять и править можно только своё отправленное (при выданных правах).

### 3. Userbot (когда нужен список чатов или удаление диалогов)

`tg_dialogs.py` в той же папке: `login` / `report` / `backup` / `delete`. Скрипт написан и проверен по CLI, но **полный вход на живом аккаунте ещё не проходился** — считать непроверенным до первого реального запуска. Порядок безопасной работы: `report` (ничего не меняет) → разбор → `backup` в JSON → `delete` без `--revoke`.

## Pitfalls

- **Один токен — один поллер.** Второй процесс на том же токене забирает апдейты у первого, и Hermes перестаёт отвечать.
- **Свои сообщения тоже приходят.** `business_message` включает исходящие владельца; без проверки флага `out` своя же переписка ложится в базу как входящая. Если это уже случилось — починить через `UPDATE messages SET direction='out' WHERE sender='<владелец>'`.
- **Историю до подключения не видно.** Telegram отдаёт только новые сообщения; чат, где человек писал до подключения бота, для моста не существует, пока он не напишет снова.
- **Медиа надо ловить в моменте.** `file_id` сохраняется из апдейта; задним числом фото не скачать — придётся просить прислать заново.
- **Лишние права.** Владелец часто выдаёт всё сразу: `can_delete_all_messages`, `can_edit_username`, `can_edit_profile_photo`, `can_edit_name`, `can_edit_bio`. Для работы достаточно `can_reply` + `can_read_messages` (+`can_manage_stories` при нужде). Остальные снять.
- **Текст не отправлять молча.** Показывать формулировку владельцу до отправки, особенно близким людям.
- **Хрупкие клики в Telegram Web.** Клик через JS `element.click()` там не срабатывает: кнопка бывает `span` внутри `label`, а координаты — за пределами viewport. Работает только настоящий клик по координатам после `scrollIntoView`.

## Verification

Подключение живое, если выполнены все три:

- `getMe` → `can_connect_to_business: true`
- `getBusinessConnection` → `rights.can_reply: true`
- `business_bridge.py chats` → строка подключения с `can_reply=True`

Отправка подтверждена, если в `inbox.sqlite3` появилась строка с `direction='out'` и тем же `msg_id`, что вернул API.
