// core: хелперы, баннер счетов (всегда сверху), вкладки.
const $=id=>document.getElementById(id);
const fmt=n=>Math.round(n).toLocaleString('ru-RU');
const fmtK=n=>Math.abs(n)>=1e6?(n/1e6).toFixed(1)+'м':Math.abs(n)>=1e3?Math.round(n/1e3)+'к':Math.round(n);
const EXCL=new Set(['Переводы','Возврат']);
const SAL_CATS=['Зарплата (карта)','Зарплата (нал)'];
const PAL=['#e9c46a','#2a9d8f','#e76f51','#4f7dc9','#f4a261','#a06cd5','#2ecc71','#ff7675','#d4a373','#8ab2f2'];
const svg=(w,h,inner)=>`<svg viewBox="0 0 ${w} ${h}">${inner}</svg>`;
function planFor(month,cat,kind){const p=PLANS.find(x=>x.category===cat&&x.kind===kind&&(x.month===month||x.month==='*'));return p?p.amount:0}
const planOf=(m,c)=>planFor(m,c,'expense');
// группы категорий (Бюджет и План общие)
const OBLIG=['Нейросети','Связь','Подписки','Транспорт','Зал/спорт','Здоровье','ЖКХ','Хостинг/техника'];
const BYT=['Продукты','Кафе и рестораны','Прочее'];
// факт-срезы: месяц->категория->сумма расходов (22.09, связь план↔факт)
const MONTHS=[...new Set(TX.map(t=>t.date.slice(0,7)))].sort();
const CATM={};
TX.forEach(t=>{if(t.amount<0&&!EXCL.has(t.category)){const m=t.date.slice(0,7);if(!CATM[m])CATM[m]={};CATM[m][t.category]=(CATM[m][t.category]||0)-t.amount;}});
function factOf(m,c){return (CATM[m]||{})[c]||0}
function factTotal(m){return Object.values(CATM[m]||{}).reduce((s,v)=>s+v,0)}
function byCat(rows,cats){const o={};rows.filter(t=>t.amount<0&&!EXCL.has(t.category)&&cats.includes(t.category))
  .forEach(t=>o[t.category]=(o[t.category]||0)-t.amount);return o}
const completed=()=>{const m0=MSK_TODAY.slice(0,7);return MONTHS.filter(m=>m<m0);};
function avgFact(cat){const cs=completed().slice(-3);if(!cs.length)return 0;
  return cs.reduce((s,m)=>s+factOf(m,cat),0)/cs.length;}
function avgFactTotal(){const cs=completed().slice(-3);if(!cs.length)return 0;
  return cs.reduce((s,m)=>s+factTotal(m),0)/cs.length;}
function avgIncome(){const cs=completed().slice(-3);if(!cs.length)return 0;let s=0;
  TX.forEach(t=>{if(t.amount>0&&SAL_CATS.includes(t.category)&&cs.includes(t.date.slice(0,7)))s+=t.amount;});
  return s/cs.length;}
// план месяца целиком {inc,ob,byt,rest,all}
function planMonth(m){const inc=planFor(m,'Зарплата','income');
  const ob=OBLIG.reduce((s,c)=>s+planOf(m,c),0);
  const byt=planOf(m,'Быт')||BYT.reduce((s,c)=>s+planOf(m,c),0);
  let rest=0;PLANS.forEach(p=>{if(p.kind==='expense'&&(p.month===m||p.month==='*')
    &&!OBLIG.includes(p.category)&&p.category!=='Быт'&&!BYT.includes(p.category))rest+=p.amount;});
  return {inc,ob,byt,rest,all:ob+byt+rest};}
// темп текущего месяца: cum по дням + прогноз до конца
function pace(){const m0=MSK_TODAY.slice(0,7),
  D=new Date(+m0.slice(0,4),+m0.slice(5,7),0).getDate(), dim=+MSK_TODAY.slice(8,10);
  const dd={};TX.forEach(t=>{if(t.amount<0&&!EXCL.has(t.category)&&t.date.slice(0,7)===m0)
    dd[t.date]=(dd[t.date]||0)-t.amount;});
  const cum=[];let c=0;for(let d=1;d<=D;d++){if(d<=dim)c+=dd[m0+'-'+String(d).padStart(2,'0')]||0;cum.push(c);}
  const slope=(cum[dim-1]-(dim>7?cum[dim-8]:0))/Math.min(7,dim);
  return {m0,D,dim,cum,slope,end:cum[dim-1]+slope*(D-dim)};}
function isSalInc(t){return t.amount>0&&SAL_CATS.includes(t.category)}
function cardShort(a){a=a||'';if(a==='CASH')return 'нал';return NAMES[a]||a.slice(-4)||'другая карта'}
function bars(el,items,o={}){
  if(!items.length){el.innerHTML='<div class="empty">нет данных</div>';return;}
  const W=440,H=o.h||200,max=Math.max(...items.map(i=>i[1]),o.planLine||0)*1.15||1,bw=(W-16)/items.length;
  let s=items.map((it,i)=>{const bh=it[1]/max*(H-46),x=8+i*bw;
    return `<rect x="${x+bw*.14}" y="${H-26-bh}" width="${bw*.72}" height="${Math.max(bh,1)}" rx="3" fill="${it[2]||o.color||'#4f7dc9'}"><title>${it[0]}: ${fmt(it[1])} ₽</title></rect>
    <text x="${x+bw/2}" y="${H-10}" text-anchor="middle" font-size="10" fill="#8a93a6">${it[3]||String(it[0]).slice(5)}</text>
    <text x="${x+bw/2}" y="${H-32-bh}" text-anchor="middle" font-size="10" fill="#e8eaed">${fmtK(it[1])}</text>`}).join('');
  if(o.planLine){const py=H-26-o.planLine/max*(H-46);
    s+=`<line x1="8" x2="${W-8}" y1="${py}" y2="${py}" stroke="#e9c46a" stroke-width="1.6" stroke-dasharray="5 4"/>
        <text x="${W-10}" y="${py-5}" text-anchor="end" font-size="10" fill="#e9c46a">план ${fmtK(o.planLine)}</text>`;}
  el.innerHTML=svg(W,H,s);
}
function hbars(el,rows_,cb){
  if(!rows_.length){el.innerHTML='<div class="empty">нет планов — скажи: «бюджет продукты 15000»</div>';return;}
  const W=440,rh=34,pad=128,max=Math.max(...rows_.map(r=>Math.max(r.fact,r.plan)),1)*1.12;
  el.innerHTML=svg(W,rows_.length*rh+14,rows_.map((r,i)=>{
    const y=i*rh+2,fw=r.fact/max*(W-pad-14),pw=r.plan/max*(W-pad-14);
    const col=r.fact>r.plan?'#ff7675':'#2a9d8f',ovr=r.fact>r.plan?` <tspan fill="#ff7675">+${fmtK(r.fact-r.plan)}</tspan>`:'';
    return `<g data-cat="${r.name}" style="cursor:pointer">
    <rect x="0" y="${y}" width="${W}" height="${rh}" fill="transparent"/>
    <text x="0" y="${y+18}" font-size="11.5" fill="#e8eaed">${r.name} <tspan fill="#5c6675">›</tspan></text>
    <rect x="${pad}" y="${y+6}" width="${Math.max(pw,2)}" height="16" rx="3" fill="#232935" stroke="#4a5568"><title>план ${fmt(r.plan)}</title></rect>
    <rect x="${pad}" y="${y+9}" width="${Math.max(fw,2)}" height="10" rx="2" fill="${col}"><title>факт ${fmt(r.fact)}</title></rect>
    <text x="${pad+Math.max(fw,pw)+6}" y="${y+19}" font-size="10" fill="#8a93a6">${fmtK(r.fact)} / ${fmtK(r.plan)}${ovr}</text></g>`;
  }).join(''));
  el.onclick=cb?(e)=>{const g=e.target.closest('g[data-cat]');if(g)cb(g.dataset.cat);}:null;
}
function pie(el,rows){
  const o={};rows.forEach(t=>{if(t.amount<0&&!EXCL.has(t.category))o[t.category]=(o[t.category]||0)-t.amount;});
  const items=Object.entries(o).sort((a,b)=>b[1]-a[1]).slice(0,9);
  const sum=items.reduce((s,i)=>s+i[1],0);
  if(!sum){el.innerHTML='<div class="empty">нет расходов</div>';return;}
  const cx=95,cy=95,r=78;let a0=-Math.PI/2;
  const arcs=items.map((it,i)=>{const a1=a0+it[1]/sum*Math.PI*2,big=a1-a0>Math.PI?1:0;
    const p=`M${cx},${cy} L${cx+r*Math.cos(a0)},${cy+r*Math.sin(a0)} A${r},${r} 0 ${big} 1 ${cx+r*Math.cos(a1)},${cy+r*Math.sin(a1)} Z`;
    a0=a1;return `<path d="${p}" fill="${PAL[i%PAL.length]}" data-cat="${it[0]}" style="cursor:pointer"><title>${it[0]}: ${fmt(it[1])} ₽ (${Math.round(it[1]/sum*100)}%)</title></path>`;}).join('');
  el.innerHTML=svg(440,190,`<g>${arcs}</g><g font-size="11">${items.map((it,i)=>
    `<text x="200" y="${24+i*19}" fill="#e8eaed" data-cat="${it[0]}" style="cursor:pointer"><tspan fill="${PAL[i%PAL.length]}">■</tspan> ${it[0]} <tspan fill="#8a93a6">${fmtK(it[1])}</tspan></text>`).join('')}</g>`);
  el.onclick=(e)=>{const g=e.target.closest('[data-cat]');if(g)openCat(g.dataset.cat);};
}
// модалка «операции категории» (клик по статье в «Бюджете» или по сегменту pie)
let catScope=null;
function openCat(cat){
  const rows=(catScope?catScope():TX).filter(t=>t.category===cat)
    .sort((a,b)=>b.date.localeCompare(a.date)||((b.time||'')<(a.time||'')?-1:1));
  const incS=rows.filter(t=>t.amount>0).reduce((s,t)=>s+t.amount,0);
  $('mcTitle').textContent=`${cat} · ${rows.length} оп. · −${fmt(-rows.filter(t=>t.amount<0).reduce((s,t)=>s+t.amount,0))} / +${fmt(incS)}`;
  $('mcBody').innerHTML=rows.map(t=>`<tr>
    <td style="white-space:nowrap">${t.date.slice(8,10)}.${t.date.slice(5,7)}<span class="src">${t.source==='manual'?'вручн.':t.source==='reconciled'?'свер.':'банк'}</span></td>
    <td>${(t.payee||'—').slice(0,34)}<div class="ba">${cardShort(t.account)}${t.bal&&t.bal[t.account]!==undefined?' → после '+fmt(t.bal[t.account]):''}</div></td>
    <td class="num ${t.amount>0?'pos':'neg'}" style="white-space:nowrap">${t.amount>0?'+':''}${fmt(t.amount)}</td></tr>`).join('')
    ||'<tr><td class="empty">нет операций</td></tr>';
  $('catModal').hidden=false;
}
function closeCat(){$('catModal').hidden=true;}
$('catModal').onclick=e=>{if(e.target.id==='catModal')closeCat();};
function totals(){
  const debits=ACCOUNTS.filter(a=>a.account!=='CASH'&&!a.debt).reduce((s,a)=>s+(a.balance||0),0);
  const cash=(ACCOUNTS.find(a=>a.account==='CASH')||{}).balance||0;
  const debt=ACCOUNTS.reduce((s,a)=>s+(a.debt||0),0);
  return {debits,cash,avail:debits+cash,debt,net:debits+cash-debt};
}
function renderBanner(){
  const t=totals();
  $('banner').innerHTML=
    `<div class="bcard tot"><b>${fmtK(t.avail)}</b><span>доступно</span></div>`
    +`<div class="bcard debt"><b>${fmtK(t.debt)}</b><span>долг кредитки</span></div>`
    +`<div class="bcard"><b class="${t.net>=0?'pos':'neg'}">${fmtK(t.net)}</b><span>нетто всё</span></div>`
    +ACCOUNTS.filter(a=>!a.debt).map(a=>
    `<div class="bcard"><b>${fmtK(a.balance)}</b><span>${a.card||''}</span></div>`).join('');
  syncTopH();  // баннер мог сменить число строк — сразу пересчитаем высоту шапки
}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  document.querySelectorAll('.pane').forEach(x=>x.classList.remove('on'));
  t.classList.add('on');$('pane-'+t.dataset.t).classList.add('on');
  ({days:renderDays,salary:renderSalary,budget:renderBudget,plan:renderPlan})[t.dataset.t]();});
// высота sticky-шапки (баннер+табы) -> CSS-переменная для .cal/.feed
function syncTopH(){document.documentElement.style.setProperty('--toph',$('topwrap').offsetHeight+'px');}
addEventListener('resize',syncTopH);
new ResizeObserver(syncTopH).observe($('topwrap'));
syncTopH();
