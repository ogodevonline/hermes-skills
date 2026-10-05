# ERROR при создании приложения на my.telegram.org

Симптом: форма *API development tools* сохраняется и отдаёт просто `ERROR` без деталей.

## Причины, которые реально чинят (по порядку проверки)

1. **Short name / App title содержат подчёркивание, тире или пробел.** Только латиница и цифры, формат UpperCamelCase: `HermesApp`, `MonitorMyChannelUsers`. Подсказка в форме («5–32 символа») требования не описывает.
2. **Пустой или однострочный Description.** Нужно развёрнутое описание, ориентир 40+ символов, по смыслу совпадающее с title.
3. **VPN.** Telegram сверяет IP и страну номерa. Российский номер + российский IP работает; с VPN из другой страны форма молча падает.
4. **Кэш/куки/расширения.** Рабочее: Chrome в режиме инкогнито или другой браузер, AdBlock выключен.
5. **URL.** Нужен реально открывающийся сайт; `https://example.com` подходит, `localhost` и случайный набор символов — нет.

Источник по пунктам 1–5: разбор https://habr.com/ru/articles/923168/ (собран из практики, не официальная документация).

## Ограничения платформы, о которых стоит помнить

- **Один номер — один api_id.** Официально: «For the moment each number can only have one api_id connected to it» (https://core.telegram.org/api/obtaining_api_id). Если приложение уже создавалось, второе не создать — существующие `api_id`/`api_hash` просто показываются на https://my.telegram.org/apps.
- **api_id — идентификатор приложения, а не аккаунта.** Документация Telethon: «This API ID and hash is the one used by your application, not your phone number. You can use this API ID and hash with any phone number or even for bot accounts» (https://docs.telethon.dev/en/stable/basic/signing-in.html). Практический обход, когда номер не пускает в форму: завести приложение на другом номере, а вход выполнить нужным.
- Аккаунт, вошедший через сторонний API-клиент, попадает под наблюдение; флуд и накрутка = вечный бан (https://core.telegram.org/api/obtaining_api_id).

## Альтернатива: обойтись без api_id

Telegram Business / Secretary Mode — штатный Bot API, ключи не нужны. Владельцу нужен Premium, бот — отдельный от Hermes-бота.

- Официальное описание и права (`can_reply`, `can_read_messages`): https://core.telegram.org/bots/features#business-bots
- `can_reply` действует только в личных чатах с входящим сообщением за последние 24 часа — проактивно написать первым нельзя.
- Business-боты отвечают от имени владельца: `sendMessage` + `business_connection_id`.
- Проверка готовности бота: `getMe` → `can_connect_to_business` (false = Secretary Mode в @BotFather не включён).
