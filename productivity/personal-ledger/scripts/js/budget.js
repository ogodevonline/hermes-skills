// «Бюджет» v2 (22.09): план↔факт везде. Темп месяца, расход по группам, heat-таблица, история накоплений.
let bPeriod='month';
function bRows(){return TX.filter(t=>{
  if(bPeriod==='all')return true;
  if(bPeriod==='week')return t.date>=MSK_WEEK0&&t.date<=MSK_TODAY;
  return t.date.slice(0,7)===MSK_TODAY.slice(0,7);})}
function renderBudget(){
  const rows=bRows(), m0=MSK_TODAY.slice(0,7);
  catScope=bRows;
  const oblig=byCat(rows,OBLIG), byt=byCat(rows,BYT);
  const oSum=Object.values(oblig).reduce((s,v)=>s+v,0), bSum=Object.values(byt).reduce((s,v)=>s+v,0);
  const oPlan=OBLIG.reduce((s,c)=>s+planOf(m0,c),0), bPlan=planOf(m0,'Быт')||BYT.reduce((s,c)=>s+planOf(m0,c),0);
  const saveGoal=planFor(m0,'Накопления','savings')||0, hardCap=bPlan-saveGoal, saveLeft=bPlan-bSum;
  const okSave=saveLeft>=saveGoal;
  const PM=planMonth(m0), P=pace();
  $('bKpis').innerHTML=`
  <div class="kpi bcard"><b class="${P.end>PM.all?'neg':'pos'}">${fmtK(P.end)}</b><span>прогноз расхода за месяц · план ${fmtK(PM.all)}</span></div>
  <div class="kpi bcard"><b class="${okSave?'pos':'neg'}">${fmtK(saveLeft)}</b><span>остаток быта${saveGoal?` · цель ${fmtK(saveGoal)}+`:` · лимит ${fmtK(bPlan)}`}</span></div>
  <div class="kpi bcard"><b>${fmtK(bSum)}</b><span>быт · ${saveGoal?`потолок ${fmtK(hardCap)}`:`лимит ${fmtK(bPlan)}`}</span></div>
  <div class="kpi bcard"><b>${fmtK(oSum)}</b><span>обязательное · план ${fmtK(oPlan)}</span></div>
  <div class="kpi bcard"><b class="neg">${fmtK(bSum+oSum)}</b><span>итого расход · ${bPeriod==='week'?'7 дней':bPeriod==='month'?m0.slice(5)+' мес':'вся история'}</span></div>`;
  const diff=P.end-PM.all;
  $('cPace').innerHTML=`<div class="big ${diff>0?'neg':'pos'}">${fmtK(P.end)} <span class="bigsub">прогноз на конец ${m0.slice(5)}.${m0.slice(2,4)}</span></div>
   <div class="hint">${diff>0?`перебор плана <b>на ${fmtK(diff)} ₽</b> — режь или сдвигай план`:`в рамках плана: запас ${fmtK(-diff)} ₽ до лимита`} · темп последних 7 дней ${fmtK(P.slope)} ₽/день · клик по категории — операции</div>`;
  paceChart($('cPaceCh'),{lim:bPlan,cap:hardCap});
  // Быт
  $('cByt').innerHTML=`<div style="font-size:34px;font-weight:800;color:${okSave?'#2a9d8f':'#ff7675'};font-variant-numeric:tabular-nums">${fmtK(saveLeft)} <span style="font-size:15px;color:var(--dim)">${saveGoal?`отложено · цель ${fmtK(saveGoal)}+`:`остаток от лимита ${fmtK(bPlan)}`}</span></div>
   <div class="hint">${bSum<=bPlan?`быт ${fmt(bSum)} из ${fmt(bPlan)} — до конца месяца можно ещё ${fmt(Math.max(bPlan-bSum,0))} ₽`:`быт вышел за лимит ${fmt(bPlan)} на ${fmt(bSum-bPlan)} ₽`}</div>`;
  hbars($('cBytBars'),BYT.map(c=>({name:c,plan:planOf(m0,c),fact:byt[c]||0})).sort((a,b)=>b.fact-a.fact),openCat);
  hbars($('cOblig'),OBLIG.map(c=>({name:c,plan:planOf(m0,c),fact:oblig[c]||0})).sort((a,b)=>b.fact-a.fact),openCat);
  const rest={};rows.filter(t=>t.amount<0&&!EXCL.has(t.category)&&![...OBLIG,...BYT].includes(t.category))
    .forEach(t=>rest[t.category]=(rest[t.category]||0)-t.amount);
  hbars($('cRest'),Object.entries(rest).map(([c,v])=>({name:c,plan:planOf(m0,c),fact:v})).sort((a,b)=>b.fact-a.fact),openCat);
  pie($('cPie'),rows);
  monthStack($('cMonth'));
  heatTable($('cHeat'));
  saveHistory($('cSave'));
}
function saveHistory(el){ // цель «отложить из быта» снята (22.09) → режим лимита: быт-факт по месяцам vs 24к
  const m0=MSK_TODAY.slice(0,7);
  const bPlan=planOf(m0,'Быт')||BYT.reduce((s,c)=>s+planOf(m0,c),0);
  const goal=planFor(m0,'Накопления','savings')||0;
  const items=MONTHS.map(m=>{
    const spent=BYT.reduce((s,c)=>s+factOf(m,c),0);
    return goal
      ? [m.slice(2,7).replace('-','.'), Math.max(bPlan-spent,0), spent>bPlan?'#ff7675':'#2a9d8f']
      : [m.slice(2,7).replace('-','.'), spent, spent>bPlan?'#ff7675':'#e9c46a'];});
  bars(el,items,{planLine:goal||bPlan,h:210,color:'#e9c46a'});
  el.innerHTML+=`<div class="hint">${goal?`быт ${fmtK(bPlan)} − потрачено = отложено. Красный = перебор.`:`быт по месяцам vs лимит ${fmtK(bPlan)}; красный = перебор (июль 23к, август 26к — лимит был 20к)`}</div>`;
}
$('bChips').onclick=e=>{const c=e.target.closest('.chip');if(!c)return;
  document.querySelectorAll('#bChips .chip').forEach(x=>x.classList.remove('on'));c.classList.add('on');
  bPeriod=c.dataset.p;renderBudget();};
