# Живая проверка админки headless-браузером (03.09.2026)

Когда Василий говорит «админка не работает / ты этого не увидишь» — НЕ копать код
и БД первым делом: открыть UI глазами headless-chromium за 5 минут и показать,
что реально рендерится и какие API падают.

## Установка (разово на vdska; chromium на машине отсутствовал)
```bash
cd /tmp
npm install playwright         # ~2s
npx playwright install chromium   # ~115 MiB, Chrome Headless Shell
```

## ⚠️ Главный подводный камень: initData из терминала замаскирован
`gen_initdata.py` выводит `user=%7B%22id%22%3A+350****2645...` — терминал Hermes
маскирует telegram_id звёздочками. Скопированный из вывода initData НЕВАЛИДЕН
(подпись не сойдётся) → фронт шлёт его → бэкенд отвечает 401 `invalid init data`.
**Решение: генерить initData ВНУТРИ node-скрипта через `execFileSync`, не печатать
в stdout и не копировать руками.**

## Рабочий скрипт (проверен 03.09: вход супер-админа + клики по всем разделам)
```js
const { chromium } = require('/tmp/node_modules/playwright');
const { execFileSync } = require('child_process');
const URL = "https://<туннель>/web/";

(async () => {
  const initData = execFileSync('python3',
    ['/home/hermes/.hermes/skills/devops/lead-platform-ops/scripts/gen_initdata.py'],
    { encoding: 'utf8' }).trim();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const bad = [];
  page.on('response', async (resp) => {
    const u = resp.url();
    if (u.includes('/api/') && resp.status() >= 400) {
      let b = ''; try { b = (await resp.text()).slice(0, 150); } catch {}
      bad.push(`${resp.status()} ${u} ${b}`);
    }
  });
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 }).catch(e => console.log('goto:', e.message));
  await page.evaluate((init) => localStorage.setItem('tg_init_data', init), initData);
  await page.reload({ waitUntil: 'networkidle', timeout: 60000 }).catch(e => console.log('reload:', e.message));
  await page.waitForTimeout(2500);
  console.log('URL:', page.url());
  console.log('BODY:', await page.evaluate(() => document.body.innerText.replace(/\n+/g, ' | ').slice(0, 500)));
  // кликать по пунктам навигации, НЕ page.goto на /clients и т.п.
  // (catch-all редиректит прямые переходы на /schedule — ложный результат)
  for (const item of ['Клиенты', 'Планы', 'Чаты', 'Настройки', 'Статистика', 'ИИ']) {
    const link = page.locator(`a:has-text("${item}")`).first();
    if (!(await link.count())) { console.log('---', item, ': нет ссылки'); continue; }
    await link.click().catch(() => {});
    await page.waitForTimeout(1500);
    const body = await page.evaluate(() => document.body.innerText.replace(/\n+/g, ' | ').slice(0, 200)).catch(() => '');
    console.log('---', item, '=>', page.url().split('/').pop(), '|', body);
  }
  console.log('BAD API:', JSON.stringify(bad, null, 1));
  await browser.close();
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
```

## Что подтвердил живой проход 03.09 (супер-админ)
- Админка рендерится, разделы есть (Расписание/Клиенты/Планы/Чаты/Настройки/Статистика/ИИ),
  API на 200 — но контент ТОЛЬКО тенанта platform (пустой).
- **Владелец бизнеса (Рашид/стоматология) войти в СВОЮ админку НЕ МОЖЕТ:** вход =
  initData токеном worker-бота тенанта, а у бизнес-тенантов worker-бота нет
  (`SELECT id, slug, worker_bot_token IS NOT NULL, client_bot_token IS NOT NULL FROM tenants;`
  → rashid-dental has_worker=f).
- Супер-админ НЕ видит список компаний и НЕ имеет переключателя тенантов (API switch
  отсутствует) — только platform.
- Dev-вход («Войти как owner/admin/specialist») висит в проде; клик → 401
  (`GET /api/me` → `invalid init data`). По глоссарию dev-вход ТОЛЬКО в dev-сборке.
- Итог: цепочка «визитка → викторина → запись → владелец видит в админке» рвётся на
  последнем звене. Доступ владельца к админке — P0, блокер продаж.
