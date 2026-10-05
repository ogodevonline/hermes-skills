# Лимиты Business-бота и получение api_id

Конспект проверенного по первоисточникам, а не по пересказам форумов.

## Что Business-бот может и не может

Источник: <https://core.telegram.org/bots/api> (объект `BusinessBotRights`, метод `deleteBusinessMessages`) и <https://core.telegram.org/bots/features#business-bots>.

Права, которые видит бот в `BusinessConnection.rights`:

- `can_reply` — «the bot can send and edit messages in the private chats that had incoming messages in the last 24 hours»
- `can_read_messages` — «the bot can mark incoming private messages as read»
- `can_delete_sent_messages` / `can_delete_all_messages` — удаление своих / любых сообщений
- `can_edit_name`, `can_edit_bio`, `can_edit_username`, `can_edit_profile_photo` — правка профиля владельца
- `can_view_gifts_and_stars`, `can_manage_stories` — «the bot can post, edit and delete stories on behalf of the business account»

Чего в списке нет вообще: каналов, групп, списка диалогов, истории переписки. Из документации: действия «limited to eligible private chats with recent incoming messages» и требуют `business_connection_id`.

Порядок подключения (из того же источника): включить Secretary Mode бота в @BotFather → обработать `BusinessConnection` → слушать `business_message` → проверять `can_reply` в `rights` → отправлять с `business_connection_id`.

## Список диалогов и удаление чатов = только MTProto

Оба метода помечены в документации «Only users can use this method»:

- `messages.getDialogs` — «Returns the current user dialog list» (<https://core.telegram.org/method/messages.getDialogs>)
- `messages.deleteHistory` — «Deletes communication history», флаг `revoke` удаляет и у собеседника (<https://core.telegram.org/method/messages.deleteHistory>)

Следствие: бот никогда не покажет владельцу, из чего состоит его список чатов. Для разбора и чистки диалогов нужен userbot.

## my.telegram.org: разбор ошибки «ERROR» при создании приложения

Симптом: форма «Create new application» на <https://my.telegram.org/apps> отвечает просто `ERROR`, без деталей.

Проверенный чек-лист (разбор: <https://habr.com/ru/articles/923168/>):

1. **App title и Short name** — только латиница и цифры. Подчёркивания, пробелы, тире роняют форму. `HermesApp`, не `hermes_app`.
2. **Description** — развёрнутый текст, не одна строка.
3. **VPN выключить.** Telegram сверяет IP со страной номера: российский номер + российский IP работает, с VPN — молчаливый ERROR.
4. **URL** — работающий простой сайт вроде `https://example.com`; не `localhost` и не набор символов.
5. **Браузер** — Chrome в инкогнито или другой браузер, расширения (AdBlock) отключены.

Официальные ограничения (<https://core.telegram.org/api/obtaining_api_id>):

- «each number can only have one api_id connected to it» — повторно создать то же приложение нельзя, параметры смотрят на <https://my.telegram.org/apps>
- все аккаунты, входящие через неофициальные клиенты, автоматически попадают «under observation»; за флуд и спам — вечный бан
- тестовый api_id из исходников клиентов серверное ограничен и для реального использования не годится

Обходной путь, если номер не проходит: api_id — идентификатор приложения, а не аккаунта. По документации Telethon (<https://docs.telethon.dev/en/stable/basic/signing-in.html>): «This API ID and hash is the one used by your application, not your phone number. You can use this API ID and hash with any phone number». То есть приложение заводят на другой номер, а вход потом выполняют нужным.

## Альтернатива без api_id

Если вход по номеру недоступен, остаётся веб-клиент: `https://web.telegram.org/k/` открывается браузером, есть вход по QR и по номеру телефона. Управление через UI медленнее и хрупче, но на живых сессиях работает.
