# РФ-прокси: рынок цен, рендер JS-прайсов, тесты

Цифры ниже — снятые с живых страниц провайдеров, не из обзоров. **Цены и минимумы меняются**: перед выдачей рекомендации перепроверить рендером (рецепт ниже), иначе получится выдуманная цена — за это пользователь ругает сильнее всего.

## 1. Как снять прайс с JS-страницы

Симптом: страница отдаёт 200 и десятки КБ, но `web-tools extract` даёт текст без единой цифры — видны только заголовки колонок («Страна | Кол-во IP | Стоимость одного IP»). Так у proxy6.net, proxyline.net, proxymania.su и большинства калькуляторов тарифов.

Рабочий рецепт — headless-chromium из кэша playwright (ставится python-playwright не обязателен):

```bash
CHROME=$(ls -d ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | head -1)
[ -z "$CHROME" ] && CHROME=$(ls -d ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome | head -1)
"$CHROME" --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --user-agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36' \
  --dump-dom --virtual-time-budget=12000 --timeout=30000 '<URL>' > page.html
```

Далее снять теги и искать цены:

```python
import re
html = open('page.html', encoding='utf-8').read()
t = re.sub(r'<script[\s\S]*?</script>', ' ', html)
t = re.sub(r'<[^>]+>', ' ', t)
t = re.sub(r'&nbsp;', ' ', t)
t = re.sub(r'\s+', ' ', t)
for m in re.finditer(r'\d[\d\s]{0,6}[.,]?\d{0,2}\s*(?:₽|руб|\$|€)', t):
    print(t[max(0, m.start() - 120): m.end() + 40])
```

- `--virtual-time-budget` обязателен: без него DOM снимается до XHR-отрисовки и цифр нет.
- Признак успеха: видны сами строки тарифа, напр. `1 − 99 | 7.7 руб. | 33 руб. | 79.2 руб.`.
- Проверка живости кандидатов до рендера: `curl -s -o /dev/null -w "%{http_code}" -L <url>` (000 = мёртв). Значительная доля «топ-10 прокси 2026» ведёт на мёртвые или WAF-закрытые (403/503) сайты — не тратить на них время и не рекомендовать.

## 2. Раскладка цен (РФ-адреса, за 1 IP)

| Провайдер | Что даёт | Цена | Минимум |
|---|---|---|---|
| proxy6.net | IPv4 SHARED | ~33 ₽/мес (1–99 шт), 3 мес ~79 ₽ | 1 IP |
| proxy6.net | IPv6 | ~21 ₽/мес, от 500 шт — ~7 ₽ | 1 IP |
| proxy6.net | IPv4 выделенный | ~120 ₽/мес, от 100 шт — ~99 ₽ | 1 IP |
| proxy6.net | MTproto | ~90 ₽/мес | 1 IP |
| proxy-store.com | серверные IPv4 | от ~23 ₽; РФ-локация — от ~31 ₽ | 1 IP |
| proxyline.net | IPv4 shared | ~0,67 $/мес за IP | 1 IP |
| fineproxy.org (RU) | датацентр, свой ASN, без лимита трафика | от ~0,12 $/IP в пакете | пакет |
| papaproxy.net | RU datacenter IPv4 | от ~0,08 $/IP в пакете | пакет |
| webshare.io (RU) | датацентр | от ~0,029 $/IP, в крупных пакетах ~0,018 $ | пакет от нескольких $/мес |

Практический вывод для одного бота/сервиса: дешёвый «$ за IP» у зарубежных сетей существует только внутри пакетов; по минимальному чеку РФ-провайдеры (IPv4 SHARED ~33 ₽ или свой RU-VPS) выгоднее. Ниже ~20–30 ₽ за РФ-IP в месяц на рынке не встречалось.

## 3. Проверка цели до и после покупки

```bash
# страна/ASN выхода
curl -x http://LOGIN:PASS@HOST:PORT -s --max-time 15 "http://ip-api.com/json/?fields=query,country,isp,as"
# цель: ожидаем ответ приложения (401/200), а не таймаут
curl -x http://LOGIN:PASS@HOST:PORT -s -o /dev/null -w "%{http_code}\n" --max-time 20 https://<target>/
```

Пример доказанной картины (российский мессенджер, доступ из ЕС): DNS цели резолвится в набор адресов, TCP:443 — таймаут (`http=000`), при этом с того же хоста yandex.ru / mail.ru / api.telegram.org отдают 302. Вывод: дроп по IP, нужен РФ-exit.

## 4. После получения доступа — нюансы API цели

- Мессенджер MAX: база API сменилась на `platform-api2.max.ru`; токен идёт в заголовке `Authorization: <token>` **без** префикса `Bearer` (с ним — 401 «No access token»).
- Приём апдейтов: поллинг `GET /updates` надёжнее вебхука — вебхук-подписка отваливается после ~8 часов без успешного ответа endpoint'а.
- В коде бота прокси ставить только на вызовы цели, Telegram-часть оставлять напрямую (`httpx.…(proxy=...)` / `aiohttp` с per-request прокси), иначе лишний хоп и единая точка отказа.
