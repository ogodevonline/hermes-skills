// charts2: темп месяца, heat факт÷план, стек расхода по месяцам (22.09, переиспользуются Бюджет/План)
function paceChart(el, o = {}) {
  const m0 = MSK_TODAY.slice(0, 7),
    D = new Date(+m0.slice(0, 4), +m0.slice(5, 7), 0).getDate(), dim = +MSK_TODAY.slice(8, 10);
  const inC = t => !o.cats || o.cats.includes(t.category);
  const dd = {};
  TX.forEach(t => { if (t.amount < 0 && !EXCL.has(t.category) && inC(t) && t.date.slice(0, 7) === m0)
    dd[t.date] = (dd[t.date] || 0) - t.amount; });
  const cum = []; let c = 0;
  for (let d = 1; d <= D; d++) { if (d <= dim) c += dd[m0 + '-' + String(d).padStart(2, '0')] || 0; cum.push(c); }
  const slope = (cum[dim - 1] - (dim > 7 ? cum[dim - 8] : 0)) / Math.min(7, dim);
  const end = Math.max(cum[dim - 1] + slope * (D - dim), cum[dim - 1]);
  const lim = o.lim || Math.max(end, cum[dim - 1]) * 1.1 || 1;
  const W = 440, H = 218, bot = 24, top = 14, pad = 10;
  const max = Math.max(end, lim, o.cap || 0) * 1.12 || 1;
  const X = d => pad + (d - 1) * (W - 2 * pad) / (D - 1), Y = v => H - bot - v / max * (H - bot - top);
  const pts = cum.map((v, d) => X(d + 1) + ',' + Y(v));
  let s = `<polyline fill="none" stroke="#4f7dc9" stroke-width="1.2" stroke-dasharray="4 3" opacity=".8" points="${X(1)},${Y(0)} ${X(D)},${Y(lim)}"/>`;
  s += `<polygon fill="rgba(233,196,106,.10)" points="${X(1)},${Y(0)} ${pts.join(' ')} ${X(dim)},${Y(0)}"/>`;
  s += `<polyline fill="none" stroke="#e9c46a" stroke-width="2" points="${pts.join(' ')}"/>`;
  if (dim < D) s += `<polyline fill="none" stroke="#e9c46a" stroke-width="2" stroke-dasharray="1 5" points="${X(dim)},${Y(cum[dim - 1])} ${X(D)},${Y(end)}"/>`;
  s += `<line x1="${pad}" x2="${W - pad}" y1="${Y(lim)}" y2="${Y(lim)}" stroke="#ff7675" stroke-width="1.4"/>
   <text x="${pad + 2}" y="${Y(lim) - 4}" font-size="9.5" fill="#ff7675">лимит ${fmtK(lim)}</text>
   <text x="${W - pad - 2}" y="${Y(lim) + 11}" text-anchor="end" font-size="9" fill="#5c6675">синий пунктир = разрешённый темп</text>`;
  if (o.cap && o.cap > 0 && o.cap < lim) s += `<line x1="${pad}" x2="${W - pad}" y1="${Y(o.cap)}" y2="${Y(o.cap)}" stroke="#e9c46a" stroke-dasharray="5 4"/>
   <text x="${W - pad - 2}" y="${Y(o.cap) - 4}" text-anchor="end" font-size="9.5" fill="#e9c46a">потолок ${fmtK(o.cap)} (отложить ${fmtK(lim - o.cap)}+)</text>`;
  const over = end > lim;
  s += `<line x1="${X(dim)}" x2="${X(dim)}" y1="${top}" y2="${H - bot}" stroke="#2a3348"/>
   <circle cx="${X(dim)}" cy="${Y(cum[dim - 1])}" r="3" fill="#e9c46a"/>
   <text x="${X(dim) - 5}" y="${Y(cum[dim - 1]) - 7}" text-anchor="end" font-size="11" fill="#e8eaed">${fmtK(cum[dim - 1])}</text>
   <circle cx="${X(D)}" cy="${Y(end)}" r="3.5" fill="${over ? '#ff7675' : '#2a9d8f'}"/>
   <text x="${X(D)}" y="${Y(end) + (over && Y(end) < top + 14 ? 16 : -8)}" text-anchor="end" font-size="11.5" font-weight="700" fill="${over ? '#ff7675' : '#2a9d8f'}">прогноз ${fmtK(end)} ₽</text>
   <text x="${X(dim) + 4}" y="${H - bot + 12}" font-size="9" fill="#8a93a6">сегодня</text>
   <text x="${pad}" y="${H - 8}" font-size="9.5" fill="#8a93a6">01.${m0.slice(5)}</text>
   <text x="${W - pad}" y="${H - 8}" text-anchor="end" font-size="9.5" fill="#8a93a6">${D}.${m0.slice(5)}</text>`;
  el.innerHTML = svg(W, H, s);
}
function heatTable(el) { // категория × месяц: факт, фон = доля от плана (клик = операции)
  const cats = [...new Set(MONTHS.flatMap(m => Object.keys(CATM[m] || {})))]
    .filter(c => !SAL_CATS.includes(c) && !c.includes('Иной доход'));
  const catTot = c => MONTHS.reduce((s, m) => s + factOf(m, c), 0);
  cats.sort((a, b) => catTot(b) - catTot(a));
  const m0 = MSK_TODAY.slice(0, 7);
  const head = `<tr><th>Категория</th>${MONTHS.map(m => `<th class="num">${m.slice(5, 7)}.${m.slice(2, 4)}</th>`).join('')}<th class="num">план</th></tr>`;
  const cell = (c, m) => {
    const f = factOf(m, c), p = planOf(m, c), r = p ? f / p : -1;
    let bg = 'rgba(92,102,117,.16)';
    if (p && f > 0) bg = r <= 1 ? `rgba(46,204,113,${.1 + .35 * (1 - r)})` : `rgba(255,118,117,${.15 + .5 * Math.min(r - 1, .9)})`;
    else if (!p && f > 0) bg = 'rgba(92,102,117,.3)';
    const tt = `${c} · ${m}: факт ${fmt(f)} ₽${p ? ' · план ' + fmt(p) + ' = ' + Math.round(r * 100) + '%' : ' · плана нет'}`;
    return `<td class="num heatc" data-cat="${c}" title="${tt}" style="background:${f ? bg : 'transparent'}">${f ? fmtK(f) : '·'}</td>`;
  };
  const plAll = planMonth(m0).all;
  el.innerHTML = `<div class="heatwrap"><table class="heat"><thead>${head}</thead><tbody>`
    + cats.map(c => `<tr><td class="hcat" data-cat="${c}">${c}</td>${MONTHS.map(m => cell(c, m)).join('')}
       <td class="num" style="color:var(--dim)">${planOf(m0, c) ? fmtK(planOf(m0, c)) : '—'}</td></tr>`).join('')
    + `<tr class="tot"><td>ИТОГО</td>${MONTHS.map(m => `<td class="num">${fmtK(factTotal(m))}</td>`).join('')}
       <td class="num" style="color:var(--dim)">${fmtK(plAll)}</td></tr></tbody></table></div>`;
  el.onclick = e => { const x = e.target.closest('[data-cat]'); if (!x) return;
    catScope = () => TX; openCat(x.dataset.cat); };
}
function monthStack(el) { // стек: обязательное / быт / остальное по месяцам (тек. —Partial + прогноз)
  const W = 440, H = 214, bot = 24, top = 18;
  const data = MONTHS.map(m => {
    const ob = OBLIG.reduce((s, c) => s + factOf(m, c), 0);
    const byt = BYT.reduce((s, c) => s + factOf(m, c), 0);
    return { m, ob, byt, rest: Math.max(factTotal(m) - ob - byt, 0) };
  });
  const P = pace(), plAll = planMonth(P.m0).all;
  const end = P.end, endRest = Math.max(end - data[data.length - 1].ob - data[data.length - 1].byt, 0);
  const max = Math.max(...data.map(d => d.ob + d.byt + d.rest), end, plAll) * 1.12 || 1;
  const n = data.length, bw = (W - 16) / n;
  const Y = v => H - bot - v / max * (H - bot - top);
  let s = '';
  const seg = (x, y, h, col, op) => `<rect x="${x}" y="${y}" width="${bw * .62}" height="${Math.max(h, 0)}" rx="2" fill="${col}" opacity="${op}"/>`;
  data.forEach((d, i) => {
    const x = 8 + i * bw + bw * .19, tot = d.ob + d.byt + d.rest, cur = i === n - 1;
    let y = Y(d.rest); s += seg(x, y, d.rest / max * (H - bot - top), '#a06cd5', cur ? .5 : .85);
    y = Y(d.rest + d.byt); s += seg(x, y, d.byt / max * (H - bot - top), '#e9c46a', cur ? .5 : .85);
    y = Y(tot); s += seg(x, y, d.ob / max * (H - bot - top), '#e76f51', cur ? .5 : .85);
    if (cur && end > tot) { const h = (end - tot) / max * (H - bot - top);
      s += `<rect x="${x}" y="${Y(end)}" width="${bw * .62}" height="${Math.max(h, 0)}" rx="2" fill="#2a3348" stroke="#8a93a6" stroke-dasharray="3 2"><title>прогноз до конца месяца: ещё ${fmt(end - tot)} ₽</title></rect>`; }
    s += `<text x="${x + bw * .31}" y="${(cur && end > tot ? Y(end) : Y(tot)) - 5}" text-anchor="middle" font-size="9.5" fill="#e8eaed">${fmtK(tot)}${cur ? ' +' + fmtK(end - tot) : ''}</text>`;
    s += `<text x="${x + bw * .31}" y="${H - 8}" text-anchor="middle" font-size="9.5" fill="${cur ? 'var(--acc)' : '#8a93a6'}">${d.m.slice(2, 7).replace('-', '.')}${cur ? ' ◐' : ''}</text>`;
  });
  s += `<line x1="8" x2="${W - 8}" y1="${Y(plAll)}" y2="${Y(plAll)}" stroke="#ff7675" stroke-dasharray="5 4"/>
   <text x="${W - 10}" y="${Y(plAll) - 4}" text-anchor="end" font-size="9.5" fill="#ff7675">план ${fmtK(plAll)}/мес</text>`;
  el.innerHTML = svg(W, H, s) + `<div class="legend"><span><i style="background:#e76f51"></i>обязательное</span>
   <span><i style="background:#e9c46a"></i>быт</span><span><i style="background:#a06cd5"></i>остальное</span>
   <span><i style="background:#2a3348;border:1px dashed #8a93a6"></i>прогноз</span></div>`;
}
