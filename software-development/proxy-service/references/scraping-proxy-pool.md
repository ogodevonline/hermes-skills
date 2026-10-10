# Scraping Proxy Pool — варианты автоматизации

## Когда это нужно

Парсер (Playwright, Scrapy, aiohttp) требует ротации IP, чтобы не быть забаненным. Threads/Instagram и другие не-HTTP протоколы — SOCKS5 обязателен.

## SOCKS5 vs HTTP прокси

| | HTTP прокси (CONNECT) | SOCKS5 |
|---|---|---|
| Работает с HTTP/HTTPS | ✅ | ✅ |
| Работает с любым TCP (Threads, FTP, SSH, кастомные протоколы) | ❌ | ✅ |
| Уровень | Прикладной (L7) | Транспортный (L5) |
| Поддержка в Playwright | встроенная | через `--proxy-server=socks5://` |
| Поддержка в curl | `-x http://` | `-x socks5://` |

**Правило:** если протокол не HTTP — только SOCKS5.

## Архитектура DIY-пула

```
Парсер → HAProxy (TCP mode, round-robin) → 20-30 VPS с SOCKS5
```

### Компоненты

- **Балансер**: HAProxy в mode tcp (проксирует любой TCP, SOCKS5 рукопожатие проходит насквозь)
- **Бэкенды**: 3proxy или Dante на каждом VPS, SOCKS5 на порту 1080
- **Деплой**: Ansible (один плейбук на все VPS)

### HAProxy конфиг (TCP mode для SOCKS5)

```haproxy
frontend socks5-in
    bind *:1080
    mode tcp
    default_backend socks5

backend socks5
    mode tcp
    balance roundrobin
    server vps01 1.2.3.4:1080 check
    server vps02 5.6.7.8:1080 check
```

## Открытые решения (self-hosted)

| Решение | Описание | Звёзды | Язык |
|---------|----------|--------|------|
| **PoolX** | Конвертирует Clash/Mihomo VPN-ноды в HTTP прокси пул. Веб-интерфейс, workspace-ы, авто-выбор по задержке | ~280 | Go+TS |
| **Rota** | Полноценная платформа: пулы с GeoIP, per-user routing, health checks, webhook алерты, TimescaleDB | ~377 | Go+TS |
| **slrp** | Самостоятельно собирает open прокси, валидирует, HTTPS MITM, веб-дашборд, история запросов | ~198 | Go |
| **proxy-in-a-box** | YAML-driven, Lua-скрипты для источников, Lightpanda headless browser для JS-страниц, TLS fingerprint spoofing | ~38 | Go |
| **socks5-proxy** | Лёгкий SOCKS5 пул с ротацией каждые 3-6 мин, auto-failover, веб-дашборд | ~190 | Go |

## Коммерческие провайдеры (если не хочется VPS)

| Провайдер | Цена от | Особенность |
|-----------|---------|------------|
| Bright Data | $4/GB | Крупнейшая сеть, гео до города |
| Oxylabs | $30/мес (5GB) | Стабильные residential |
| SOAX | $90/мес (25GB) | SOCKS5+QUIC, sticky sessions |
| IPRoyal | $7/GB | Sticky до 7 дней |
| ScrapingBee | $49/мес | Managed API (прокси+рендеринг) |

## No-root SOCKS5 сервер (тест на любом сервере)

Когда нет sudo, но Python есть:

```python
# Минимальный SOCKS5 на Python asyncio/socketserver
# Установка: 0 зависимостей, только stdlib
# Запуск: python3 socks5.py (порт 1080)
```

Реализация: рукопожатие → CONNECT → relay через select.
Не для продакшна — для быстрого теста.

Готовый шаблон: `templates/socks5-minimal.py` (запуск: `python3 socks5-minimal.py`).

## VPS для прокси-пула

| Провайдер | Цена/мес | Комментарий |
|-----------|----------|-------------|
| Hetzner CX22 | €3.79 | Топ по цене/качество, EU |
| RackNerd | $1.5-2.5 | США, частые скидки |
| BuyVM | $3.50 | США/Люксембург, /64 IPv6 |
| Netcup | €2.50 | Германия |
| AlphaVPS | $3 | Болгария/США/Германия |

**Правило:** 20 VPS × $3-5 = $60-100/мес. Не класть все в один ДЦ — размазывать по разным AS.

## Софт на VPS

### 3proxy (рекомендую — легче Squid)
```bash
apt install 3proxy
# socks -p1080 в конфиге
```

### Dante (только SOCKS5)
```bash
apt install dante-server
```

### gost (один бинарник, 0 зависимостей)
```bash
./gost -L socks5://user:pass@:1080
```

## Проверка прокси

### Threads (реальный тест)
```bash
# Проверка доступности
curl -x socks5://host:1080 -s --max-time 10 -o /dev/null -w "%{http_code} %{time_total}s %{size_download}bytes\n" https://www.threads.net/

# Полная загрузка страницы
curl -x socks5://host:1080 -sL --max-time 10 https://www.threads.net/ | head -100

# Проверка IP через прокси
curl -x socks5://host:1080 -s https://eth0.me/
curl -x socks5://host:1080 -s http://ip-api.com/json/
```

Результат теста с VDSka (Нидерланды): threads.net → 200 OK, 516KB, полный HTML (все Meta/Instagram CSS+JS бутлоадеры). SOCKS5 работает с Threads без проблем.

### IP геолокация
`ip-api.com/json/` через прокси показал: Нидерланды, Flevoland, Dronten, AS50053 VDSka, ISP «Антон Левин».

Playwright `proxy=` параметр НЕ поддерживает SOCKS5 напрямую. Решение — передать `--proxy-server` как аргумент Chromium:

```python
import asyncio
from playwright.async_api import async_playwright

PROXY = "socks5://104.238.27.229:1080"
UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[f"--proxy-server={PROXY}"]
        )
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        await page.goto("https://www.threads.net/@zuck", wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        print(f"OK: {title}")  # → Mark Zuckerberg (@zuck) • Threads, Say more
        await browser.close()

asyncio.run(main())
```

Проверено: Chromium через SOCKS5 загрузил Threads (793KB HTML, 3.3s). Важно:
- Threads лучше грузить с мобильным UA (`Android ... Chrome/125 Mobile`)
- `wait_until="domcontentloaded"` — не ждать полной загрузки JS (дольше, не нужно)
- `--proxy-server=socks5://` — это Chromium флаг, работает в headless и headful режимах

Другие варианты (если `--proxy-server` не подходит по каким-то причинам):
1. **Privoxy**: локальный HTTP→SOCKS5 мост (`forward-socks5t / proxy:1080 .`) → Playwright использует `proxy={"server": "http://127.0.0.1:8118"}`
2. **3proxy локально**: `proxy -p3128` перенаправляет в SOCKS5 upstream

## Гео-блок по IP: диагностика и российские прокси

**Заблокированный сервис отдаёт не 403, а таймаут.** MAX (VK) с зарубежного IP: DNS резолвится, но TCP :443 не открывается вообще (`http_code=000`, `time=20s`). Диагностика в три команды:

```bash
curl -s -o /dev/null -w "target http=%{http_code} t=%{time_total}\n" --max-time 20 https://<target>/
curl -s -o /dev/null -w "control http=%{http_code}\n" --max-time 10 https://yandex.ru/   # контроль: чужие сайты живы?
timeout 8 bash -c '</dev/tcp/<host>/443' && echo OPEN || echo BLOCKED
```

Контрольные сайты (yandex.ru, mail.ru, api.telegram.org) с того же сервера отвечают 302 → блок на стороне цели, а не у нас. Решение — exit-IP нужной страны.

### Российские прокси: как брать и почём

Снимай цены с калькулятора самого провайдера (рендер JS-страницы через chrome-headless-shell — см. навык web-search-scraper), не из подборок. Ориентиры (₽ за 1 IP/мес): IPv4 SHARED ~33 ₽, IPv6 ~21 ₽, выделенный IPv4 ~120 ₽ у proxy6; серверные от ~23-31 ₽ у proxy-store. Зарубежные (Webshare/FineProxy/PapaProxy) дают $0.03-0.12/IP — это цена пакета 100+ IP, минимальный чек $3-7.

- Для HTTP(S)-запросов к API достаточно HTTP-прокси (CONNECT); SOCKS5 нужен только для не-HTTP протоколов.
- Часто дешевле выходит RU VPS + 3proxy/gost (~100-150 ₽/мес за сервер с безлимитом, а не за IP).
- Проверка купленного прокси: `curl -x http://user:pass@host:port https://api.ipify.org` (должен вернуть RU-адрес) + реальный запрос к целевому API.

### MAX Bot API (частый потребитель российского IP)

- база `https://platform-api2.max.ru` (с июля 2026 миграция с `platform-api.max.ru`)
- токен в заголовке `Authorization: <token>` **без** `Bearer` — с Bearer приходит 401 «No access token»
- поллинг `GET /updates` надёжнее вебхука: MAX отписывает подписку после 8 часов без успешного ответа endpoint'а
- проверка прокси под MAX: `curl -x http://u:p@h:port -o /dev/null -w "%{http_code}" https://platform-api2.max.ru/me` → ждём **401** (нет токена), а не 000/таймаут.

## Pitfalls

- **Cloudflare** банит дата-центры (Hetzner, OVH) — нужны residential для таких сайтов
- **Threads/Instagram** требуют SOCKS5 — HTTP прокси не работают
- **Не пиши Python SOCKS5 в продакшн** — это для теста. Для прода: 3proxy/Dante/gost
- **Health-check обязателен** — иначе мёртвые VPS тихо роняют коннекты
- **Auth обязателен на публичном IP** — иначе любой может юзать твой SOCKS5
- **Threads тест**: дата-центр VDSka (AS50053, Нидерланды) проходит. Если нужны российские IP — нужны VPS у Selectel/Timeweb/Beget
- **Гео-блок бывает на уровне TCP (000/таймаут), а не HTTP-кодом.** Не считай сервис «сломанным» и не ищи капчу — сначала проверь контрольный сайт с того же хоста.
- **$/IP на лендинге = цена пакета.** Перед рекомендацией смотри минимальный заказ и минимальный платёж, иначе совет окажется в разы дороже ожиданий пользователя.
