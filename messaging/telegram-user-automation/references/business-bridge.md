# Business-бот (Secretary Mode): проверенные факты API

Живая проверка на подключении Василия, 04.10.2026.

## Включение и проверка

- BotFather → `/mybots` → Bot Settings → **Secretary Mode** (Telegram переименовал Business Mode в Secretary Mode).
- `getMe` → `can_connect_to_business`: `false` до включения, `true` после. Это самый быстрый способ проверить режим — UI сканировать не нужно.
- Подключение в аккаунте: Настройки → Telegram Business → **Чат-боты** → username бота (раздел виден только с Premium).
- `getBusinessConnection(business_connection_id)` → `is_enabled`, `user`, `rights`.

## Права (BusinessBotRights)

Пример полной выдачи (владелец может выдать всё сразу):
`can_reply`, `can_read_messages`, `can_delete_sent_messages`, `can_delete_all_messages`, `can_edit_name`, `can_edit_bio`, `can_edit_profile_photo`, `can_edit_username`, `can_view_gifts_and_stars`, `can_manage_stories`.

Официальные формулировки:

- `can_reply` — «send and edit messages in the private chats that had incoming messages in the last 24 hours»
- `can_read_messages` — помечать входящие прочитанными
- `can_manage_stories` — «post, edit and delete stories on behalf of the business account»

Каналов нет ни в одном праве: Business-связка работает только с личкой плюс истории. Пост в канал от имени аккаунта этим путём невозможен.

## Методы

- `sendMessage` с `business_connection_id`, `sendChatAction`, `deleteBusinessMessages(business_connection_id, message_ids)`, `getBusinessConnection`.
- `messages.getDialogs` и `messages.deleteHistory` — «Only users can use this method»: боту недоступны в принципе.

## Обновления

- `allowed_updates`: `business_connection`, `business_message`, `edited_business_message`, `deleted_business_messages`.
- `business_message` приходит и на исходящие владельца → направление определяется полем `out`.
- Медиа без текста отдаёт пустой `text` (в базе помечается `[не текст]`).

## Чего бот не умеет

- видеть историю до момента подключения
- получать список диалогов аккаунта
- группы и каналы
- писать в чат, где не было входящего за 24 часа

## Поллинг

`getUpdates` с `offset`, подтверждение — следующим вызовом с новым offset. Один токен = один поллер. `getWebhookInfo` → `pending_update_count` показывает, копится ли очередь.

## Локальный стек (этот сервер)

- `~/.hermes/tg-userbot/business_bridge.py`, база `inbox.sqlite3`, конфиг `config.json` (600)
- systemd: `systemctl --user restart tg-business-bridge`
