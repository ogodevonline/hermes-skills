// «План» v2 (22.09): два сценария — «по плану» vs «как живёшь»; платежи; цели с ✓/✗ по обоим.
let pHorizon = 6;
const MONN = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
function addMonths(m, k) { const y = +m.slice(0,4), mo = +m.slice(5,7)-1+k;
  return `${y+Math.floor(mo/12)}-${String(mo%12+1).padStart(2,'0')}`; }
function scenPlan(m) { const p = planMonth(m); return { inc:p.inc, spend:p.all, save:Math.max(p.inc-p.all,0) }; }
function scenFact() { const inc = avgIncome(), sp = avgFactTotal();
  return { inc, spend:sp, save:Math.max(inc-sp,0) }; }
function schedWindow(days) { // ближайшие N дней: monthly по dom + разовые по дате
  const t = new Date(MSK_TODAY+'T00:00:00Z'), end = t.getTime()+days*864e5, rows = [];
  PAYMENTS.forEach(p => {
    if (p.repeat==='none') { if (p.date) rows.push({...p, d:p.date, one:true}); return; }
    let d = new Date(Date.UTC(+MSK_TODAY.slice(0,4), +MSK_TODAY.slice(5,7)-1, p.day));
    if (d < t) d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth()+1, p.day));
    while (d.getTime() <= end) { rows.push({...p, d:d.toISOString().slice(0,10)});
      d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth()+1, p.day)); }
  });
  return rows.sort((a,b) => a.d.localeCompare(b.d));
}
function renderPlan() {
  const m0 = MSK_TODAY.slice(0,7), NC = Math.max(completed().length,1);
  const sp = scenPlan(m0), sf = scenFact();
  const goal = planFor(m0,'Накопления','savings')||0, soon = schedWindow(45);
  $('pKpis').innerHTML = `
  <div class="kpi bcard"><b class="${sf.save>=goal?'pos':'neg'}">${fmtK(sf.save)}</b><span>откладываешь сейчас (ср. ${NC} мес)</span></div>
  <div class="kpi bcard"><b>${fmtK(sp.save)}</b><span>по плану · цель ${fmtK(goal)}</span></div>
  <div class="kpi bcard"><b>${fmtK(sf.inc)}</b><span>доход факт ≈ план ${fmtK(sp.inc)}</span></div>
  <div class="kpi bcard"><b class="neg">${fmtK(soon.reduce((s,r)=>s+r.amount,0))}</b><span>платежи · 45 дней</span></div>`;
  $('payTb').innerHTML = soon.map(r => {
    return `<tr><td style="white-space:nowrap">${r.d===MSK_TODAY?'<b style="color:var(--acc)">сегодня</b>':r.d.slice(8,10)+'.'+r.d.slice(5,7)}${r.one?' ·раз.'+r.d.slice(2,4):''}</td>
    <td>${r.title}<div class="ba">${r.category||''}</div></td><td class="td-acc" style="color:var(--dim)">${r.grp||''}</td>
    <td class="num neg">−${fmt(r.amount)}</td></tr>`; }).join('')
    || '<tr><td class="empty">нет запланированных платежей</td></tr>';
  $('payNote').textContent = '«платёж 15 числа зал 2000» / «разовый платёж 01.12 виза 15000» / «платежи» — список';
  drawCurve($('cCurve'), sp, sf);
  catScope = () => TX;
  const cats = new Set([...OBLIG, ...BYT,
    ...PLANS.filter(p=>p.kind==='expense'&&p.category!=='Быт').map(p=>p.category)]);
  hbars($('cDiv'), [...cats].map(c => ({name:c, plan:planOf(m0,c), fact:avgFact(c)}))
    .filter(r=>r.plan||r.fact).sort((a,b) => Math.abs(b.fact-b.plan)-Math.abs(a.fact-a.plan)), openCat);
  $('goalTb').innerHTML = GOALS.map(g => {
    const mo = (+g.deadline.slice(0,4)-+MSK_TODAY.slice(0,4))*12 + (+g.deadline.slice(5,7)-+MSK_TODAY.slice(5,7));
    const need = mo>0 ? g.target/mo : g.target, okp = sp.save>=need, okf = sf.save>=need;
    return `<tr><td>${g.name}<div class="ba">${g.note||''}</div></td><td class="num">${fmtK(g.target)}</td>
      <td>${MONN[+g.deadline.slice(5,7)-1]} ${g.deadline.slice(2,4)}${mo>0?' · '+mo+' мес':''}</td>
      <td class="num">${fmtK(need)}</td>
      <td class="num" style="color:${okp?'#2a9d8f':'#ff7675'}">${okp?'✓':'✗'}</td>
      <td class="num" style="color:${okf?'#2a9d8f':'#ff7675'}">${okf?'✓':'✗'}</td></tr>`; }).join('')
    || '<tr><td class="empty" colspan="6">целей нет — скажи: «цель машина 1500000 к сентябрю 2028»</td></tr>';
  $('goalNote').textContent = GOALS.length ? '✓ = хватает откладываемого (зелёный = и по факту тоже)' : '';
}
function drawCurve(el, sp, sf) {
  const H = Math.max(pHorizon, 12), m0 = MSK_TODAY.slice(0,7);
  let cp = 0, cf = 0; const P = [], F = [];
  for (let i=0;i<H;i++) { const m = addMonths(m0,i);
    cp += scenPlan(m).save; cf += sf.save; P.push(cp); F.push(cf); }
  const W = 920, Ht = 240, gm = Math.max(cp, cf, ...GOALS.map(g=>g.target))*1.1 || 1;
  const X = i => 44+i*(W-56)/(H-1), Y = v => Ht-30-v/gm*(Ht-54);
  let s = '';
  [gm/2, gm].forEach(v => { s += `<line x1="36" x2="${W-8}" y1="${Y(v)}" y2="${Y(v)}" stroke="#232935"/>
    <text x="2" y="${Y(v)+3}" font-size="9" fill="#5c6675">${fmtK(v)}</text>`; });
  GOALS.forEach(g => { if (g.target>gm) return;
    s += `<line x1="36" x2="${W-8}" y1="${Y(g.target)}" y2="${Y(g.target)}" stroke="#e9c46a" stroke-dasharray="4 4"/>
    <text x="${W-10}" y="${Y(g.target)-4}" text-anchor="end" font-size="10" fill="#e9c46a">${g.name} ${fmtK(g.target)}</text>`; });
  const line = (a,col) => `<polyline fill="none" stroke="${col}" stroke-width="2.2" points="${a.map((v,i)=>X(i)+','+Y(v)).join(' ')}"/>`;
  s += line(P,'#2a9d8f') + line(F,'#e76f51');
  s += `<circle cx="${X(H-1)}" cy="${Y(cp)}" r="3.5" fill="#2a9d8f"/>
   <text x="${X(H-1)-6}" y="${Y(cp)-8}" text-anchor="end" font-size="11.5" font-weight="700" fill="#2a9d8f">${fmtK(cp)} · по плану</text>
   <circle cx="${X(H-1)}" cy="${Y(cf)}" r="3.5" fill="#e76f51"/>
   <text x="${X(H-1)-6}" y="${Y(cf)+(cp>cf?16:-8)}" text-anchor="end" font-size="11.5" font-weight="700" fill="#e76f51">${fmtK(cf)} · как живёшь</text>`;
  const step = Math.max(Math.ceil(H/8),1);
  for (let i=0;i<H;i+=step) s += `<text x="${X(i)}" y="${Ht-10}" text-anchor="middle" font-size="9" fill="#8a93a6">${i?addMonths(m0,i).slice(2,7).replace('-','.'):'сейчас'}</text>`;
  el.innerHTML = svg(W,Ht,s) + `<div class="legend"><span><i style="background:#2a9d8f"></i>если жить по плану</span>
   <span><i style="background:#e76f51"></i>если продолжать как сейчас (среднее за ${Math.max(completed().length,1)} полных мес)</span>
   <span>разница через ${H} мес: <b style="color:${cp>=cf?'#2a9d8f':'#ff7675'}">${fmtK(cp-cf)} ₽</b></span></div>`;
}
$('hChips').onclick = e => { const c = e.target.closest('.chip'); if (!c) return;
  document.querySelectorAll('#hChips .chip').forEach(x => x.classList.remove('on')); c.classList.add('on');
  pHorizon = +c.dataset.h; renderPlan(); };
