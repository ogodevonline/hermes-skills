"""HTML report builder for Nukus houses — CSS, JS, table, filters."""


def build_html(total, avg_price, avg_area, price_dist, with_gas, with_phone,
               rows, all_rooms, all_dist, all_types, today_str):
    """Build full interactive HTML report with filters + sorting."""
    # ── Stats boxes ──
    stats = f"""<div class="stats">
<div class="stat-box"><div class="num">{total}</div><div class="lab">total</div></div>
<div class="stat-box green"><div class="num">{avg_price:.0f}</div><div class="lab">avg mln</div></div>
<div class="stat-box blue"><div class="num">{avg_area:.0f}</div><div class="lab">avg m²</div></div>
<div class="stat-box"><div class="num">{price_dist['-200']}/{price_dist['200-250']}/{price_dist['250-300']}/{price_dist['300+']}</div><div class="lab"><200 / 200-250 / 250-300 / 300+</div></div>
<div class="stat-box red"><div class="num">{with_gas}</div><div class="lab">gas</div></div>
<div class="stat-box blue"><div class="num">{with_phone}</div><div class="lab">phone</div></div>
</div>"""
    # ── Filter row ──
    rooms_opts = "".join(f'<option value="{r}">{r}</option>' for r in all_rooms)
    if all_rooms:
        rooms_opts += '<option value="6">6+</option>'
    dist_opts = "".join(f'<option value="{d}">{d}</option>' for d in all_dist) if all_dist else ""
    types_opts = "".join(f'<option value="{t}">{t}</option>' for t in all_types)
    filters = f"""<div class="filters">
<label>Type</label><select id="ftp" onchange="a()"><option value="">all</option>{types_opts}</select>
<label>💰</label><input type="range" id="pmin" min="0" max="400" value="0" oninput="a()"><span class="rv" id="pmnv">0</span>
<input type="range" id="pmax" min="0" max="400" value="400" oninput="a()"><span class="rv" id="pmxv">400</span>
<label>Rooms</label><select id="fr" onchange="a()"><option value="">all</option>{rooms_opts}</select>
<label>📍Dist</label><select id="fd" onchange="a()"><option value="">all</option>{dist_opts}</select>
<label>🔥Gas</label><select id="fg" onchange="a()"><option value="">any</option><option value="1">yes</option><option value="0">no</option></select>
<label>📞Phone</label><select id="fph" onchange="a()"><option value="">any</option><option value="1">yes</option><option value="0">no</option></select>
<label>Days</label><select id="fdn" onchange="a()"><option value="">all</option><option value="0">today</option><option value="7">7+</option><option value="14">14+</option><option value="30">30+</option></select>
<span class="stat" id="st">showing 0</span>
</div>"""
    # ── Table ──
    rows_html = ""
    for i, r in enumerate(rows):
        pc = "#4ade80" if r["price_sum"] and r["price_sum"] < 200e6 else (
            "#f1c40f" if r["price_sum"] and r["price_sum"] < 300e6 else "#f87171")
        today_cls = ' style="border-left:3px solid #f1c40f"' if r["days_online"] == 0 else ""
        rows_html += f"""<tr{today_cls} data-p="{r['price_sum'] or 0}" data-r="{r['rooms'] or 0}"\
 data-d="{r['district'] or ''}" data-g="{1 if r.get('gas') else 0}"\
 data-ph="{1 if r.get('phone') else 0}" data-st="{r['days_online']}"\
 data-pt="{r.get('prop_type') or ''}">
<td>{i+1}</td><td class="price" style="color:{pc}">{(r['price_sum'] or 0)/1e6:.0f} mln</td>
<td><a href="{r['url']}">{(r['title'] or '')[:50]}</a></td>
<td>{r['rooms'] or '?'}</td><td>{int(r['area_sqm']) if r['area_sqm'] else '?'}</td>
<td style="font-size:10px">{r['district'] or ''}</td>
<td>{'🔥' if r.get('gas') else ''}</td><td>{'💧' if r.get('water') else ''}</td>
<td class="phone">{(r.get('phone') or '')[:14]}</td>
<td style="font-size:10px;color:#64748b">{r['days_online']}d</td></tr>"""
    # ── CSS ──
    css = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;background:#0b1121;color:#e2e8f0;padding:12px}
h1{color:#f1c40f;font-size:18px;display:inline}.date{color:#475569;font-size:12px;margin-left:8px}
.stats{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 10px}
.stat-box{background:#1a2340;border-radius:8px;padding:6px 10px;min-width:70px;flex:1}
.stat-box .num{font-size:16px;font-weight:700;color:#f1c40f}
.stat-box .lab{font-size:10px;color:#64748b}
.stat-box.green .num{color:#4ade80}.stat-box.blue .num{color:#60a5fa}.stat-box.red .num{color:#f87171}
.filters{display:flex;flex-wrap:wrap;gap:4px 6px;margin-bottom:8px;align-items:center;font-size:11px}
.filters label{color:#64748b;font-size:10px;text-transform:uppercase}
.filters select{background:#1a2340;border:1px solid #334155;color:#e2e8f0;padding:3px 6px;border-radius:4px;font-size:11px;max-width:120px}
.filters input[type=range]{width:70px;background:transparent;accent-color:#f1c40f}
.filters .rv{color:#f1c40f;font-size:10px;min-width:24px}
.filters .stat{color:#64748b;margin-left:auto;font-size:11px}
.wrap{overflow-x:auto;border-radius:8px;border:1px solid #1a2340}
table{width:100%;border-collapse:collapse;font-size:11px}
th{background:#1a2340;color:#94a3b8;padding:5px 6px;text-align:left;font-weight:600;position:sticky;top:0;white-space:nowrap;font-size:10px;cursor:pointer;user-select:none}
th:hover{background:#1e2d52}
th .sort{color:#f1c40f;font-size:10px;margin-left:2px;opacity:.4}
th.asc .sort,th.desc .sort{opacity:1}.th-sort{display:none}
td{padding:4px 6px;border-top:1px solid #1a2340;vertical-align:top}
tr:nth-child(even){background:#0b1121}tr:hover{background:#1a2a4a}tr.hidden{display:none}
.price{font-weight:700;white-space:nowrap}
.phone{color:#60a5fa;font-size:10px;white-space:nowrap}
a{color:#f1c40f;text-decoration:none}a:hover{text-decoration:underline}
td:first-child{color:#475569;font-size:10px}"""
    # ── JS ──
    js = """function a(){f();}
function sortRows(){
const tbody=document.querySelector('tbody'),rows=Array.from(tbody.querySelectorAll('tr:not(.hidden)'));
const col=document.querySelector('th.asc,th.desc');
if(!col)return;
let idx=[].indexOf.call(col.parentElement.children,col);
let asc=col.classList.contains('asc');
rows.sort((a,b)=>{
let av=a.cells[idx].textContent.trim(),bv=b.cells[idx].textContent.trim();
let an=parseFloat(av.replace(/[^0-9.\\-]/g,'')),bn=parseFloat(bv.replace(/[^0-9.\\-]/g,''));
if(!isNaN(an)&&!isNaN(bn))return asc?an-bn:bn-an;
return asc?av.localeCompare(bv):bv.localeCompare(av);
});
rows.forEach(r=>tbody.appendChild(r));
}
document.querySelectorAll('th').forEach((th,idx)=>{
th.addEventListener('click',function(){
let prev=document.querySelector('th.asc,th.desc');
if(prev&&prev!==this){prev.classList.remove('asc','desc');prev.querySelector('.sort').textContent='↕';}
if(this.classList.contains('asc')){this.classList.replace('asc','desc');this.querySelector('.sort').textContent='▼';}
else if(this.classList.contains('desc')){this.classList.remove('desc');this.querySelector('.sort').textContent='↕';}
else{this.classList.add('asc');this.querySelector('.sort').textContent='▲';}
document.querySelectorAll('tbody tr').forEach(r=>r.parentNode.appendChild(r));
});
});
function f(){
const pmi=+document.getElementById('pmin').value*1e6,pma=+document.getElementById('pmax').value*1e6;
const r=document.getElementById('fr').value,d=document.getElementById('fd').value,
g=document.getElementById('fg').value,ph=document.getElementById('fph').value,
dn=document.getElementById('fdn').value,pt=document.getElementById('ftp').value;
document.getElementById('pmnv').textContent=pmi/1e6;document.getElementById('pmxv').textContent=pma/1e6;
let cnt=0;
document.querySelectorAll('tbody tr').forEach(t=>{
let s=+t.dataset.p>=pmi&&+t.dataset.p<=pma;
if(r){const rm=+t.dataset.r;s=s&&(r==='6'?rm>=6:rm===+r)}
if(d)s=s&&t.dataset.d===d;
if(g==='1')s=s&&t.dataset.g==='1';if(g==='0')s=s&&t.dataset.g==='0';
if(ph==='1')s=s&&t.dataset.ph==='1';if(ph==='0')s=s&&t.dataset.ph==='0';
if(dn){const dnv=+t.dataset.st||0;s=s&&dnv>=+dn;}
if(pt)s=s&&t.dataset.pt===pt;
t.classList.toggle('hidden',!s);if(s)cnt++;
});
document.getElementById('st').textContent='showing '+cnt;
sortRows();
}
const _f=f;f();"""
    # ── Assemble ──
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Nukus — Houses {today_str}</title><style>{css}</style></head><body>
<h1>🏡 Nukus Houses</h1><span class="date">{today_str}</span>
{stats}{filters}
<div class="wrap"><table>
<thead><tr>
<th>#<span class="sort">↕</span></th><th>Price<span class="sort">↕</span></th><th>Title<span class="sort">↕</span></th>
<th>Rooms<span class="sort">↕</span></th><th>Area<span class="sort">↕</span></th><th>District<span class="sort">↕</span></th>
<th>🔥<span class="sort">↕</span></th><th>💧<span class="sort">↕</span></th><th>📞<span class="sort">↕</span></th>
<th>Days<span class="sort">↕</span></th>
</tr></thead><tbody>{rows_html}</tbody></table></div>
<script>{js}</script></body></html>"""
