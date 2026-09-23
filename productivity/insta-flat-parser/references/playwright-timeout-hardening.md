# Playwright Timeout Hardening Pattern

## Проблема

Playwright `page.goto()` с таймаутом 30-60s не гарантирует, что операция завершится за это время.
В редких случаях (сетевые глюки, Instagram rate-limiting, краш соединения) вызов может зависнуть навсегда:
- `page.goto()` не возвращает управление
- `page.close()` в `finally` тоже виснет
- Рендерер Chromium остаётся в памяти с 88-99% CPU
- Монитор блокируется навсегда, новые проверки не запускаются

## Паттерн: asyncio.wait_for + set_default_timeout + close timeout

Обёртка для любого Playwright метода, работающего со страницей:

```python
async def fetch_something(self, param: str) -> list[PostData]:
    assert self._context is not None

    page: Page = await self._context.new_page()
    page.set_default_timeout(45_000)          # ← страховка для всех Playwright вызовов на странице

    async def _do_fetch() -> list[PostData]:
        # Вся логика работы со страницей здесь
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_load_state("networkidle", timeout=10_000)
        # ... сбор данных ...
        return results

    try:
        return await asyncio.wait_for(_do_fetch(), timeout=60)  # ← жёсткий таймаут
    except asyncio.TimeoutError:
        # Логируем, возвращаем пустой результат
        logger.error("Timeout (>60s)")
        return []
    except Exception as exc:
        logger.error("Failed: {}", exc)
        return []
    finally:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(page.close(), timeout=5)     # ← close тоже с таймаутом
```

## Что защищает

| Уровень | Защита | Таймаут |
|---------|--------|---------|
| `page.set_default_timeout(45_000)` | Все Playwright вызовы на странице (click, fill, evaluate) | 45s |
| `page.goto(timeout=30_000)` | Навигация | 30s |
| `page.wait_for_load_state(timeout=10_000)` | Ожидание загрузки | 10s |
| **`asyncio.wait_for(_do_fetch(), 60)`** | **ВЕСЬ блок** — если что-то зависло между вызовами | 60s |
| **`asyncio.wait_for(page.close(), 5)`** | Закрытие страницы | 5s |

## Куда применять

В проектах с Playwright асинхронным скрапингом — в каждый метод, который создаёт `page`:

- `fetch_profile_posts()`
- `fetch_post_comments()`
- Любой другой метод с `await self._context.new_page()`

## Диагностика зависших рендереров

```bash
# Список рендереров хром
ps aux | grep 'type=renderer' | grep -v grep

# Если renderer живёт >5 мин → скорее всего страница зависла
# Если таких 3+ — монитор заблокирован

# Скрипт для автоматической проверки:
bash ~/.hermes/skills/productivity/insta-flat-parser/scripts/check-stuck-renderers.sh

# Убить все виснущие рендереры:
kill $(ps aux | grep 'type=renderer' | grep -v grep | awk '{print $2}') 2>/dev/null
```
