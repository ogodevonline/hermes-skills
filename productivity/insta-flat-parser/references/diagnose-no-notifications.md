# Диагностика: почему не приходят уведомления от бота

Полный чеклист, когда пользователь жалуется «не приходят уведомления».

## Фаза 1: Базовые проверки

```bash
# 1. Бот запущен?
ps aux | grep insta_flat_parser | grep -v grep
# Если пусто — перезапустить

# 2. Аккаунты зелёные?
python3 ~/.hermes/skills/productivity/insta-flat-parser/scripts/list-accounts.py

# 3. Сессия жива?
cd ~/Projects/Personal/GitHub/insta_flat_parser && uv run python3 \
  ~/.hermes/skills/productivity/insta-flat-parser/scripts/check-session.py
```

## Фаза 2: Есть ли новые посты?

Самая частая причина «не приходят уведомления» — риелторы просто не постят.

```bash
cd ~/Projects/Personal/GitHub/insta_flat_parser && uv run python -c "
import asyncio
from insta_flat_parser.scraper import InstagramScraper
from insta_flat_parser.storage import StateStorage

async def check():
    scraper = InstagramScraper(headless=True)
    await scraper.start()
    storage = StateStorage()
    new_count = 0
    for username in storage.get_all_active():
        last_id = storage.get_last_post_id(username)
        posts = await scraper.fetch_profile_posts(username, limit=2)
        if posts:
            newest = posts[0]
            is_new = newest.post_id != last_id if last_id else True
            icon = '🆕' if is_new else '  '
            if is_new: new_count += 1
            print(f'{icon} @{username:25s} {newest.post_id[:15]}')
        else:
            print(f'  @{username:25s} no posts')
    print(f'\nАккаунтов с новыми постами: {new_count}')
    await scraper.stop()

asyncio.run(check())
"
```

- Если `Аккаунтов с новыми постами: 0` — **бот исправен, постов нет**. Ничего не чинить.
- Если `🆕` есть — бот найдёт и отправит уведомление в следующем цикле (ждём до 15 мин).

## Фаза 3: Работает ли отправка?

```bash
cd ~/Projects/Personal/GitHub/insta_flat_parser && uv run python -c "
import asyncio
from aiogram import Bot
from insta_flat_parser.config import settings
async def test():
    bot = Bot(token=settings.bot_token)
    await bot.send_message(settings.admin_chat_id, '🧪 Тест от бота — проверка связи')
    print('✅ Сообщение отправлено')
    await bot.session.close()
asyncio.run(test())
"
```

Если ошибка — проблема с токеном бота или Telegram API.

## Фаза 4: Проблема в scraper'е

Если сессия жива, бот работает, но скрипт выше показывает ошибки:
- `BrowserContext.new_page` — контекст упал, но должен восстановиться автоматически
- Другие ошибки — смотреть в stderr бота (логируемые через loguru)

## Что сказать пользователю

> «Проверил: бот работает, Instagram-сессия жива, все аккаунты зелёные. За последние X часов новых постов у риелторов не было. Как только появится — пришлёт.»
