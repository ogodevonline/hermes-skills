// Сбор организаций из Яндекс.Карт: поиск -> список -> карточка (телефон, адрес, рейтинг, отзывы, Instagram/Telegram).
// NODE_PATH=$(npm root -g) node ymaps.mjs "<запрос>" <сегмент> [макс=40] ["город"=Ургенч] ["lon,lat"=60.63,41.553]
// Результат: out_<сегмент>.jsonl (дописывается, повторы пропускает). ~20 с на карточку, запускать в фоне.
import { chromium } from 'playwright';
import fs from 'fs';

const [query, segment, maxArg, cityArg, llArg] = process.argv.slice(2);
const MAX = Number(maxArg || 40);
const CITY = cityArg || 'Ургенч';
const [LON, LAT] = (llArg || '60.63,41.553').split(',');
const out = `out_${segment}.jsonl`;
const seen = new Set(fs.existsSync(out) ? fs.readFileSync(out, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l).url) : []);

const browser = await chromium.launch({ channel: 'chrome', headless: true });
const ctx = await browser.newContext({ locale: 'ru-RU', viewport: { width: 1400, height: 1000 },
  userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36' });
const page = await ctx.newPage();
// центр карты = город поиска
const url = `https://yandex.uz/maps/?ll=${LON}%2C${LAT}&z=13&text=${encodeURIComponent(query + ' ' + CITY)}`;
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(6000);

// прокрутка списка
let links = new Set();
for (let i = 0; i < 25 && links.size < MAX; i++) {
  const hrefs = await page.$$eval('a.search-snippet-view__link-overlay, a[href*="/org/"]', as => as.map(a => a.href));
  hrefs.map(h => (h.match(/^(https:\/\/[^/]+\/maps\/org\/[^/]+\/\d+\/)/) || [])[1]).filter(Boolean).forEach(h => links.add(h));
  await page.evaluate(() => {
    const s = document.querySelector('.scroll__container');
    if (s) s.scrollTop = s.scrollHeight;
  });
  await page.waitForTimeout(1500);
}
console.error(`[${segment}] найдено ссылок: ${links.size}`);

let n = 0;
for (const link of [...links].slice(0, MAX)) {
  if (seen.has(link)) continue;
  try {
    await page.goto(link, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(2500);
    const btn = await page.$('.card-phones-view__more, .orgpage-phones-view__more');
    if (btn) { await btn.click().catch(() => {}); await page.waitForTimeout(700); }
    const d = await page.evaluate(() => {
      const t = s => document.querySelector(s)?.textContent?.trim() || '';
      const phones = [...document.querySelectorAll('.card-phones-view__phone-number, .orgpage-phones-view__phone-number')].map(e => e.textContent.trim());
      const links = [...document.querySelectorAll('a[href]')].map(a => a.href)
        .filter(h => /instagram\.com|t\.me\/|telegram|facebook\.com|^https?:\/\/(?!yandex)/.test(h) && !/yandex|ya\.ru|yastatic|apple\.com|google\.com/.test(h));
      return {
        name: t('h1.orgpage-header-view__header, h1'),
        category: t('.business-categories-view, .orgpage-categories-info-view'),
        address: t('.orgpage-header-view__address, .business-contacts-view__address-link'),
        rating: t('.business-rating-badge-view__rating-text'),
        reviews: t('.business-header-rating-view__text'),
        phones, links: [...new Set(links)].slice(0, 6),
      };
    });
    d.url = link; d.segment = segment;
    fs.appendFileSync(out, JSON.stringify(d) + '\n');
    n++;
  } catch (e) { console.error('ERR', link, e.message.slice(0, 80)); }
}
console.error(`[${segment}] сохранено новых: ${n}`);
await browser.close();
