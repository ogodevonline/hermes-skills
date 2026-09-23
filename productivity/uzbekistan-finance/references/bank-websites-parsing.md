# Парсинг курсов узбекских банков — проверенные URL и приёмы

## InfinBank (Invest Finance Bank)

**URL:** https://www.infinbank.com/ru/private/exchange-rates/

**Метод:** `browser_navigate` — страница отдаёт таблицу StaticText, видимую в snapshot. Никаких капч.

**Структура таблицы (snapshot):**
- Строка 1: Курс ЦБ — USD, EUR, GBP, RUB, JPY, CHF
- Строка 2: Обменный пункт — Покупка (все валюты)
- Строка 3: Обменный пункт — Продажа (все валюты)
- Строка 4: Приложение — Покупка (только USD, остальное `—`)
- Строка 5: Приложение — Продажа (только USD)
- Строка 6: Банкомат — Покупка (USD, EUR)
- Строка 7: Банкомат — Продажа (USD)

**Примечание:** InFinBank = Invest Finance Bank. Не показывать как разные банки.

**Телефон:** +998 (71) 202 50 60 / 1214 (короткий)

---

## Bank.uz (агрегатор)

**URL:** https://bank.uz/currency

**Метод:** `browser_navigate` — показывает топ-3 банка по покупке и продаже для каждой валюты.

**Особенности:**
- Показывает только топ-3 (не полный список)
- USD/RUB/EUR/GBP/KZT — переключение по табам
- Данные с агрегатора — всегда верифицировать на сайте банка
- `body.innerText` через `browser_console` даёт полную таблицу

**Курс ЦБ РУз** виден в шапке страницы (USD 12 XXX, RUB XXX и т.д.)

---

## NBU (Национальный банк Узбекистана)

**URL:** https://nbu.uz/

**Метод:** `browser_navigate` — курсы видны в футере главной страницы (список ссылок с курсами). Специальная страница /ru/exchange-rates/ выдаёт 404.

**Данные в футере (ссылки):**
- `USD Sotib olish: 12 000 ▲ Sotish: 12 060 ▼`
- `RUB Sotib olish: 130 ▲ Sotish: 155 ▼`
- `EUR Sotib olish: 13 550 ▲ Sotish: 13 740 ▼`
- `GBP Sotib olish: 15 760 ▲ Sotish: 16 360 ▼`
- `CHF Sotib olish: 14 470 ▲ Sotish: 15 070 ▼`
- `CNY Sotib olish: 1 625 ▲ Sotish: 1 830 ▼`
- `JPY Sotib olish: 65 ▲ Sotish: 80 ▼`

**Примечание:** Sotib olish = покупка (банк покупает у тебя), Sotish = продажа.

---

## Anor Bank

**URL:** https://www.anorbank.uz/ru/exchange-rates (404), правильный путь: главная → «Курс валют» в меню

**Метод:** `browser_navigate` на главную, затем `browser_click` по ссылке «Курс валют». SPA-роутинг, но контент грузится. `body.innerText` через browser_console даёт полную таблицу.

**Структура:**
- **В обменных пунктах (обновлено 27.07.2026 / 09:00:00):**
  USD: 12 000 / 12 070 (Покупка/Продажа). Примечание: курс отличается в зависимости от региона.
- **В мобильном приложении (прогрессивный курс USD):**
  - от 0.1 до 999 $: 12 000 / 12 070
  - от 1 000 до 9 999 $: 12 003 / 12 067
  - от 10 000+ $: 12 005 / 12 065
  - EUR: 13 430 / 13 890
  - RUB: 50 / 158 (⚠️ RUB покупка 50 — плохой курс)

---

## Universal Bank

**URL:** https://universalbank.uz/currency

**Метод:** `browser_navigate` — таблица StaticText, видна в snapshot. Язык узбекский.

**Структура таблицы:**
- MB kursi (курс ЦБ) / Sotib olish (покупка) / Sotuv (продажа)
- USD: 12,019.08 / 11,990 / 12,075 (Бош офис, 27.07.2026)
- EUR: 13,689.73 / 13,000 / 15,000
- RUB: 153.87 / 0 / 154 (покупка 0 = не покупают рубли)
- JPY: 73.43 / 70 / 100
- GBP: 16,008.21 / 15,200 / 18,000

**Примечание:** Надпись "Kun davomida kurs o'zgarib borishi mumkin! Hududlar kesimida ham kurslar farq qilishi mumkin!" — курс меняется в течение дня и различается по филиалам. Комбобокс "Bo'lim" позволяет выбрать отделение.

**Важно:** 27.07.2026 агрегатор bank.uz показывал 12 020, а на сайте банка — 11 990. Разница 30 сум. Агрегатор врёт.

---

## Ipak Yuli Bank

**URL:** https://ipakyulibank.uz → меню "Valyuta ayirboshlash"

**Метод:** `browser_navigate` на главную, `browser_click` на пункт меню "Valyuta ayirboshlash" (ref=e18). SPA, контент через browser_console.

**Структура (27.07.2026, 04:30):**
- Kassada (касса): USD Xarid 11,980 / Sotuv 12,070
- EUR: 13,300 / 13,820
- JPY: 55 / 75
- GBP: 15,450 / 16,320
- CHF: 14,180 / 15,000
- RUB: 100 / 149 (⚠️ RUB покупка 100 — плохой)

**Примечание:** Xarid = покупка (банк покупает у тебя), Sotuv = продажа. Есть переключение Kassada / Bankomatda / Ilovada (не реализовано на сайте, только в приложении). Телефон: 1296.

---

## TBC Bank

**URL:** https://tbcbank.uz/

**Метод:** `browser_navigate` → `browser_click` на "VALYUTA AYIRBOSHLASH KURSI" (ref=e80). SPA, контент через browser_console.

**Структура (27.07.2026 00:00):**
| Валюта | Sotish | Sotib olish | MB kursi |
|--------|:-----:|:-----------:|:--------:|
| EUR | 14,100.00 | 13,300.00 | 13,689.73 |
| USD | 12,150.00 | **11,970.00** | 12,019.08 |
| GBP | — | 16,008.21 | 16,008.21 |
| RUB | — | 153.87 | 153.87 |

**Примечание:** Sotish = продажа (банк продаёт), Sotib olish = покупка (банк покупает). USD покупка 11,970 — один из худших курсов среди проверенных банков.

---

## Банки, которые НЕ работают

| Банк | URL | Проблема |
|------|-----|----------|
| Asakabank | asakabank.uz | Access Denied (бот-детект) |
| Xalq Banki | xalqbanki.uz | Домен не резолвится |
| Davr Bank | davrbank.uz | DDoS-Guard блокировка |
| Kapitalbank | kapitalbank.uz/ru/currency-exchange | Cloudflare challenge (только через bank.uz/currency/bank/kapitalbank) |
