// «По дням»: лента месяца; у каждой операции — остаток счёта после неё; в дне — доступно.
const MON={0:'янв',1:'фев',2:'мар',3:'апр',4:'май',5:'июн',6:'июл',7:'авг',8:'сен',9:'окт',10:'ноя',11:'дек'};
const WDAY=['вс','пн','вт','ср','чт','пт','сб'];
let selMonth=MSK_TODAY.slice(0,7), selDay=MSK_TODAY;
function dayRows(d){return TX.filter(t=>t.date===d)}
function spend(rs){return rs.filter(t=>t.amount<0&&!EXCL.has(t.category)).reduce((s,t)=>s-t.amount,0)}
function inc(rs){return rs.filter(t=>t.amount>0&&!EXCL.has(t.category)).reduce((s,t)=>s+t.amount,0)}
function fmtDay(d){const x=new Date(d+'T12:00:00Z');return `${+d.slice(8)} ${MON[+d.slice(5,7)-1]}, ${WDAY[x.getUTCDay()]}`}
// «доступно» на конец дня: последний balance_of-снимок дня (сумма дебетовых карт + нал)
function availOn(d){
  const rs=TX.filter(t=>t.date===d&&t.bal&&Object.keys(t.bal).length);
  if(!rs.length)return null;
  const b=rs[rs.length-1].bal;
  return Object.values(b).reduce((s,v)=>s+v,0);
}
function txBalHtml(t){
  if(!t.bal)return '';
  const acc=t.account==='CASH'?'CASH':t.account;
  const v=t.bal[acc];
  if(v===undefined)return '';
  return `<div class="ba">на ${cardShort(acc)} после: ${fmt(v)} ₽</div>`;
}
function renderDays(){
  const months=[...new Set(TX.map(t=>t.date.slice(0,7)))].sort().reverse();
  $('mChips').innerHTML=months.map(m=>`<div class="chip${m===selMonth?' on':''}" data-m="${m}">${MON[+m.slice(5,7)-1]} ${m.slice(2,4)}</div>`).join('');
  const days=[...new Set(TX.filter(t=>t.date.startsWith(selMonth)).map(t=>t.date))].sort().reverse();
  if(!days.includes(selDay))selDay=days[0];
  $('cal').innerHTML=days.map(d=>{const s=spend(dayRows(d)),i=inc(dayRows(d));
    return `<div class="day has${d===selDay?' on':''}" data-d="${d}"><b>${d.slice(8)}</b><i>${s?fmtK(s):i?'+'+fmtK(i):'·'}</i></div>`}).join('');
  // лента
  $('feed').innerHTML=days.map(d=>{
    const rs=dayRows(d).sort((a,b)=>((b.time||'')<(a.time||'')?-1:1));
    const av=availOn(d);
    return `<section class="dsec" id="sec-${d}">
      <div class="dhead"><span class="dh-date">${fmtDay(d)}</span>
        <span class="dh-sum">${av!==null?`<span class="pos">≈${fmtK(av)} доступно</span>`:''} ${spend(rs)?'<span class=neg>−'+fmt(spend(rs))+'</span>':''} ${inc(rs)?'<span class=pos>+'+fmt(inc(rs))+'</span>':''}
        <span class="dh-n">${rs.length} оп.</span></span></div>
      <ul class="tl">${rs.map(t=>{
        const cls=t.amount>0?(isSalInc(t)?'in':'tr'):'out';
        return `<li class="${cls}">${t.time?`<span class="tt">${t.time}</span>`:''}
          <div>${t.category}<span class="src">${t.source==='manual'?'вручную':t.source==='reconciled'?'сверено':'банк'}</span>
          <div style="color:var(--dim);font-size:11px">${(t.payee||'').slice(0,46)} · ${cardShort(t.account||'другая карта')}</div>
          ${txBalHtml(t)}</div>
          <span class="ta ${t.amount>0?'pos':'neg'}">${t.amount>0?'+':''}${fmt(t.amount)}</span></li>`}).join('')}</ul></section>`}).join('')
    ||'<div class="empty">нет операций</div>';
  syncTo(selDay,false);
}
function syncTo(d,scroll){
  selDay=d;
  document.querySelectorAll('.day').forEach(x=>x.classList.toggle('on',x.dataset.d===d));
  const el=document.querySelector(`.day[data-d="${d}"]`);
  if(el)el.scrollIntoView({inline:'center',block:'nearest'});
  if(scroll){const s=document.getElementById('sec-'+d);
    if(s){const top=s.getBoundingClientRect().top+scrollY-$('topwrap').offsetHeight-$('cal').offsetHeight;
      scrollTo({top:Math.max(top,0),behavior:'smooth'});}}
}
$('mChips').onclick=e=>{const c=e.target.closest('.chip');if(!c)return;
  selMonth=c.dataset.m;selDay=null;renderDays();
  const first=[...document.querySelectorAll('.dsec')].pop();if(first)syncTo(first.id.slice(4),false);};
$('cal').onclick=e=>{const c=e.target.closest('.day');if(c)syncTo(c.dataset.d,true);};
// скролл страницы -> подсветка дня в ленте + автопереключение чипа месяца (троттлинг по времени)
function feedTick(){
  const top=$('topwrap').offsetHeight+$('cal').offsetHeight+40;let cur=null;
  document.querySelectorAll('.dsec').forEach(s=>{if(s.getBoundingClientRect().top<=top)cur=s.id.slice(4)});
  if(cur&&cur!==selDay){selDay=cur;
    document.querySelectorAll('.day').forEach(x=>x.classList.toggle('on',x.dataset.d===cur));
    const m=cur.slice(0,7);
    if(m!==selMonth){selMonth=m;
      document.querySelectorAll('#mChips .chip').forEach(x=>x.classList.toggle('on',x.dataset.m===m));}}}
let lastTick=0,tickTimer=0;
addEventListener('scroll',()=>{const now=Date.now();
  clearTimeout(tickTimer);
  if(now-lastTick>=120){lastTick=now;feedTick();}
  else tickTimer=setTimeout(()=>{lastTick=Date.now();feedTick();},140);},{passive:true});
renderBanner();renderDays();
