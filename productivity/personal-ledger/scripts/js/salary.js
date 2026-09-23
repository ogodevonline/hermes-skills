// «Зарплата»: KPI в ряд; лента зачислений (чипы месяцев, только дни переводов); графики компактнее.
let salMonth=null;
function renderSalary(){
  const mk=[...new Set(TX.map(t=>t.date.slice(0,7)))].sort();
  const m0=MSK_TODAY.slice(0,7); if(!mk.includes(m0))mk.push(m0);
  if(!salMonth)salMonth=m0;
  const plan=planFor('*','Зарплата','income')||300000;
  const sal=TX.filter(t=>SAL_CATS.includes(t.category)&&t.amount>0);
  const salOf=m=>sal.filter(t=>t.date.slice(0,7)===m).reduce((s,t)=>s+t.amount,0);
  const cardOf=m=>TX.filter(t=>t.date.slice(0,7)===m&&t.category==='Зарплата (карта)').reduce((s,t)=>s+t.amount,0);
  const cashOf=m=>salOf(m)-cardOf(m);
  const cur=salOf(m0),gapM=mk.map(m=>Math.max(plan-salOf(m),0));
  $('sKpis').innerHTML=`
  <div class="kpi bcard"><b>${fmtK(cur)}</b><span>заработано ${m0.slice(5)}</span></div>
  <div class="kpi bcard"><b class="${plan-cur>0?'neg':'pos'}">${fmtK(Math.max(plan-cur,0))}</b><span>недоплата ${m0.slice(5)}</span></div>
  <div class="kpi bcard"><b class="neg">${fmtK(gapM.reduce((s,g)=>s+g,0))}</b><span>недоплата всего</span></div>
  <div class="kpi bcard"><b>${fmtK(mk.reduce((s,m)=>s+salOf(m),0))}</b><span>зп за период</span></div>`;
  // лента зачислений: чипы месяцев (как в «По дням»), только дни переводов
  const smk=[...new Set(sal.map(t=>t.date.slice(0,7)))].sort().reverse();
  if(!smk.includes(salMonth))salMonth=smk[0]||m0;
  $('salChips').innerHTML=smk.map(m=>`<div class="chip${m===salMonth?' on':''}" data-m="${m}">${MON[+m.slice(5,7)-1]} ${m.slice(2,4)} · ${fmtK(salOf(m))}</div>`).join('');
  const ops=sal.filter(t=>t.date.slice(0,7)===salMonth).sort((a,b)=>b.date.localeCompare(a.date));
  const days=[...new Set(ops.map(t=>t.date))];
  $('cashTb').innerHTML=days.map(d=>{
    const day=ops.filter(t=>t.date===d);
    return day.map((t,j)=>`<tr${j===0&&d!==days[0]?` style="border-top:2px solid #2a3348"`:''}>
      <td style="white-space:nowrap">${fmtDay(d)}</td>
      <td class="td-acc">${cardShort(t.account)}</td>
      <td>${(t.payee||'').replace('KORONAPAY — ','').slice(0,34)}<div class="td-sub">${cardShort(t.account)}</div></td>
      <td class="num pos" style="white-space:nowrap">+${fmt(t.amount)}</td></tr>`).join('');
  }).join('')||'<tr><td colspan=4 class="empty">в этом месяце зачислений не было</td></tr>';
  $('salChips').onclick=e=>{const c=e.target.closest('.chip');if(!c)return;
    salMonth=c.dataset.m;renderSalary();};
  bars($('cSal'),mk.map(m=>[m,salOf(m),salOf(m)>=plan?'#2ecc71':'#ff7676',m.slice(2,7)]),{planLine:plan,h:150});
  const W=440,H=150,max=plan*1.12,bw=(W-16)/mk.length;
  $('cSplit').innerHTML=svg(W,H,mk.map((m,i)=>{
    const x=8+i*bw,ch=cardOf(m)/max*(H-46),sh=cashOf(m)/max*(H-46);
    return `<rect x="${x+bw*.16}" y="${H-26-ch}" width="${bw*.68}" height="${Math.max(ch,1)}" fill="#4f7dc9"><title>карта ${fmt(cardOf(m))}</title></rect>
    <rect x="${x+bw*.16}" y="${H-26-ch-sh}" width="${bw*.68}" height="${Math.max(sh,1)}" fill="#e9c46a"><title>конверт ${fmt(cashOf(m))}</title></rect>
    <text x="${x+bw/2}" y="${H-10}" text-anchor="middle" font-size="10" fill="#8a93a6">${m.slice(2,7)}</text>`}).join('')
    +`<g font-size="10"><rect x="16" y="6" width="9" height="9" fill="#4f7dc9"/><text x="30" y="14" fill="#8a93a6">на карту</text><rect x="92" y="6" width="9" height="9" fill="#e9c46a"/><text x="106" y="14" fill="#8a93a6">конверт (внес в банкомат / наличные)</text></g>`);
  $('cashNote').textContent='Считаю всю зарплату: официальные зачисления + всё внесённое на карты (банк видит) + ручные наличные. План меняется: «план зарплата 350000».';
  bars($('cGap'),mk.map((m,i)=>[m,gapM[i],gapM[i]?'#ff7676':'#2ecc71',m.slice(2,7)]),{h:150});
}
