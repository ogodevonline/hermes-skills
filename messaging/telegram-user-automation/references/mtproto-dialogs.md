# Разбор и чистка диалогов через userbot (MTProto)

## Почему только userbot

`messages.getDialogs` («Returns the current user dialog list») и `messages.deleteHistory` («Deletes communication history») помечены **«Only users can use this method»**. Бот список чатов не видит и диалоги не удаляет — ни Business-бот, ни обычный.

## Порядок работы

1. `login` — авторизация (номер → код → 2FA), создаёт `owner.session`
2. `report` — CSV: `id, kind (user/bot/group/channel/supergroup/deleted_account), name, username, archived, pinned, unread, last_date, last_msg`. Ничего не меняет.
3. Классификация и согласование списка с владельцем (без его «да» не удалять)
4. `backup --ids <файл> --dir <папка>` — JSON-выгрузка истории: страховка перед необратимым шагом
5. `delete --file <файл>` — пауза 1.5 с между удалениями, `FloodWaitError` пережидается автоматически

## Семантика удаления

- по умолчанию история удаляется **только у владельца**
- `--revoke` стирает и у собеседника, необратимо — только по отдельному согласию

## Ограничения и риски

- `owner.session` = полный доступ к аккаунту без пароля: хранить с правами 600, напоминать про «Устройства → завершить сессию»
- официальная дока: аккаунты, входящие через неофициальные клиенты, ставятся «под наблюдение»; флуд и спам — «will be banned forever» (https://core.telegram.org/api/obtaining_api_id)
- массовые операции — маленькими пачками с паузами, иначе `FLOOD_WAIT`
