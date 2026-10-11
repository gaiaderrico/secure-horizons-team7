"""A single wide "SOC Incident Console" served by core at ``GET /console``.

Same-origin, so plain ``fetch`` reaches the API with no CORS setup. One
landscape, projector-friendly page that combines three things kept deliberately
uncluttered:

* a live dashboard (left column) — the "0 real files lost" hero, compact tiles
  for intruder / swap time / decoys / attacker cost, the checked confession as
  CONFIRMED/CONTRADICTED/UNVERIFIED chips with their evidence line, and a compact
  ATT&CK timeline;
* the AI narrator's detailed report (right column) — ``/incidents/{id}/summary``
  markdown rendered to HTML, an "AI DRAFT" ribbon (a cosmetic "Approve draft"
  button flips it to APPROVED), a static "Recommended actions" box and the NIS2
  early-warning draft in a ``<details>``;
* the two human decisions (a clean action panel directly under the top bar) —
  CONTAIN (red) and RESTORE (green). Each first opens an in-page confirmation
  modal; only on Confirm do they POST to the real control endpoints, so clicking
  really drives the guard. The result is made unmistakable: the whole view is
  re-fetched and re-rendered with the new state and a prominent (emoji-free)
  result banner is shown, while the big status word changes colour and text.

It polls ``/incidents`` (+ card + summary for the newest) every 2s and only
rebuilds the DOM when the incident id changes, so the approve state, an open
NIS2 panel and a just-shown action banner survive refreshes. This is a NEW page;
``/report`` (Option A), ``/`` (viewer) and the hero card are untouched.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

console_router = APIRouter()

_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MIRAGE Console</title>
<style>
  :root{
    --page:#eceff1; --paper:#ffffff; --ink:#1b2023; --muted:#5e6a70;
    --line:#dfe3e6; --faint:#f4f6f7; --accent:#1f6f6a;
    --l1:#b7960f; --l2:#c76b16; --l3:#b3261e; --l4:#7a0f0a;
    --ok:#2f7a4a; --bad:#b3261e; --warn:#b07908;
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{background:var(--page);color:var(--ink);
    font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased;padding:18px 16px 40px}
  .serif{font-family:Georgia,"Times New Roman",'Noto Serif',serif}
  .wrap{max-width:1400px;margin:0 auto}
  /* ---- top bar ---- */
  .top{background:var(--paper);border:1px solid var(--line);border-radius:6px;
    box-shadow:0 1px 3px rgba(0,0,0,.06);
    display:flex;align-items:center;gap:16px;padding:14px 20px;flex-wrap:wrap}
  .top .brand{font-weight:800;letter-spacing:3px;font-size:16px}
  .top .brand small{display:block;font-weight:600;letter-spacing:1px;font-size:10px;
    color:var(--muted);text-transform:uppercase;margin-top:2px}
  .top .iid{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
  .pill{display:inline-flex;align-items:center;gap:7px;color:#fff;font-weight:800;
    letter-spacing:.6px;font-size:12px;text-transform:uppercase;border-radius:999px;
    padding:6px 13px}
  .pill.l1{background:var(--l1)} .pill.l2{background:var(--l2)}
  .pill.l3{background:var(--l3)} .pill.l4{background:var(--l4)}
  .status{margin-left:auto;font-weight:800;letter-spacing:1.5px;font-size:20px;
    text-transform:uppercase;padding:4px 14px;border-radius:6px;border:2px solid}
  .status.open{color:var(--warn);border-color:var(--warn);background:#fdf6e6}
  .status.contained{color:var(--bad);border-color:var(--bad);background:#fbecea}
  .status.restored{color:var(--ok);border-color:var(--ok);background:#eaf5ee}
  .guard{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:7px}
  .guard .dot{width:9px;height:9px;border-radius:50%;background:var(--ok)}
  .guard.silent{color:var(--bad);font-weight:700}
  .guard.silent .dot{background:var(--bad);animation:flash 1s steps(2,start) infinite}
  @keyframes flash{50%{opacity:.2}}
  /* ---- grid ---- */
  .grid{display:grid;grid-template-columns:minmax(0,38fr) minmax(0,62fr);gap:16px;margin-top:16px}
  .panel{background:var(--paper);border:1px solid var(--line);border-radius:6px;
    box-shadow:0 1px 3px rgba(0,0,0,.06)}
  .col{display:flex;flex-direction:column;gap:16px}
  /* ---- hero ---- */
  .hero{padding:20px;text-align:center;border-left:5px solid var(--ok)}
  .hero.breach{border-left-color:var(--bad)}
  .hero b{display:block;font-size:52px;line-height:1;font-weight:800;color:var(--ok)}
  .hero.breach b{color:var(--bad)}
  .hero span{font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted)}
  /* ---- tiles ---- */
  .tiles{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);
    border-radius:6px;overflow:hidden}
  .tile{background:var(--paper);padding:13px 15px}
  .tile .k{font-size:10px;letter-spacing:.8px;text-transform:uppercase;color:var(--muted)}
  .tile .v{font-size:19px;font-weight:800;margin-top:3px}
  .tile .x{font-size:11px;color:var(--muted);margin-top:2px}
  .tile.wide{grid-column:1 / -1}
  /* ---- section headings ---- */
  .sect{padding:15px 18px}
  .sect>h3{margin:0 0 11px;font-size:12px;letter-spacing:.8px;text-transform:uppercase;
    color:var(--accent);border-bottom:1px solid var(--line);padding-bottom:7px}
  /* ---- confession chips ---- */
  .claim{margin:0 0 11px;padding-left:11px;border-left:3px solid var(--line)}
  .claim:last-child{margin-bottom:0}
  .claim .row{display:flex;gap:9px;align-items:flex-start}
  .claim .txt{font-size:13px;flex:1}
  .chip{flex:none;font-size:10px;font-weight:800;letter-spacing:.5px;padding:2px 8px;
    border-radius:999px;color:#fff;text-transform:uppercase}
  .chip.confirmed{background:var(--ok)} .chip.contradicted{background:var(--bad)}
  .chip.unverified{background:var(--warn)}
  .claim .ev{font-size:11px;color:var(--muted);margin-top:3px;font-style:italic}
  /* ---- timeline ---- */
  .tl{list-style:none;margin:0;padding:0;font-size:12.5px}
  .tl li{display:flex;gap:9px;padding:6px 0;border-bottom:1px dashed var(--line);align-items:baseline}
  .tl li:last-child{border-bottom:0}
  .tl .tid{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
    font-weight:700;color:var(--accent);flex:none;width:72px}
  .tl .tid.def{color:var(--ok)}
  .tl .clk{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
    color:var(--muted);flex:none;width:64px;font-variant-numeric:tabular-nums}
  .tl .ty{flex:none;font-weight:700;width:96px}
  .tl .dt{color:var(--muted);flex:1;word-break:break-all}
  .tl .def-tag{flex:none;font-size:9px;font-weight:800;letter-spacing:.5px;color:var(--ok);
    text-transform:uppercase}
  /* ---- report (right) ---- */
  .report{padding:22px 26px}
  .ribbon{display:inline-flex;align-items:center;gap:8px;background:var(--faint);
    border:1px dashed #c3ac5a;color:#7a640f;border-radius:3px;
    padding:7px 13px;font-size:12px;letter-spacing:.5px;margin-bottom:18px}
  .ribbon.approved{border-style:solid;border-color:var(--ok);background:#eef7f0;color:var(--ok)}
  .ribbon b{font-weight:800;letter-spacing:1px}
  .rendered{font-family:Georgia,"Times New Roman",'Noto Serif',serif;font-size:15.5px;line-height:1.65}
  .rendered h1{font-size:23px;line-height:1.25;margin:.2em 0 .5em;font-weight:700}
  .rendered h2{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size:13px;letter-spacing:.6px;text-transform:uppercase;color:var(--accent);
    margin:1.5em 0 .5em;padding-bottom:5px;border-bottom:1px solid var(--line)}
  .rendered p{margin:.6em 0} .rendered ul{margin:.5em 0;padding-left:1.3em}
  .rendered li{margin:.22em 0} .rendered strong{font-weight:700}
  .rec{margin-top:20px;border:1px solid var(--accent);border-radius:6px;overflow:hidden}
  .rec h4{margin:0;background:var(--accent);color:#fff;font-size:12px;letter-spacing:.7px;
    text-transform:uppercase;padding:9px 16px}
  .rec ol{margin:0;padding:12px 16px 12px 34px;font-size:14px}
  .rec li{margin:.3em 0}
  details.nis2{margin-top:20px;border:1px solid var(--line);border-radius:6px;overflow:hidden}
  details.nis2>summary{cursor:pointer;list-style:none;padding:13px 18px;background:var(--faint);
    font-size:12px;letter-spacing:.5px;text-transform:uppercase;color:var(--accent);
    font-weight:700;display:flex;align-items:center;gap:10px}
  details.nis2>summary::-webkit-details-marker{display:none}
  details.nis2>summary::before{content:"\25B8";transition:transform .15s}
  details.nis2[open]>summary::before{transform:rotate(90deg)}
  details.nis2 .inner{padding:4px 22px 18px;font-family:Georgia,serif;font-size:14px}
  button.approve{margin-top:18px;font-size:13px;font-weight:600;padding:9px 18px;border-radius:6px;
    border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
  button.approve:hover{filter:brightness(1.08)}
  button.approve[disabled]{background:#eef7f0;color:var(--ok);border-color:var(--ok);cursor:default;filter:none}
  /* ---- action panel (under top bar) ---- */
  .actions{margin-top:16px;background:var(--paper);border:1px solid var(--line);border-radius:6px;
    box-shadow:0 1px 3px rgba(0,0,0,.06);display:flex;align-items:center;gap:14px;
    padding:12px 16px;flex-wrap:wrap}
  .actions .alabel{font-size:11px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;
    color:var(--muted);flex:none}
  .banner{flex:1;min-width:220px;font-weight:700;font-size:14px;padding:10px 15px;border-radius:6px;
    border:1px solid transparent;display:none}
  .banner.show{display:block}
  .banner.good{background:#eaf5ee;color:var(--ok);border-color:var(--ok)}
  .banner.err{background:#fbecea;color:var(--bad);border-color:var(--bad)}
  .acts{margin-left:auto;display:flex;gap:12px}
  button.big{font-size:16px;font-weight:800;letter-spacing:1px;text-transform:uppercase;
    padding:12px 28px;border-radius:8px;border:0;color:#fff;cursor:pointer;min-width:150px}
  button.big.contain{background:var(--bad)} button.big.restore{background:var(--ok)}
  button.big:hover{filter:brightness(1.08)}
  button.big[disabled]{opacity:.55;cursor:default;filter:none}
  button.big.done{background:#43515a}
  /* ---- confirmation modal ---- */
  .modal-ov{position:fixed;inset:0;z-index:50;background:rgba(20,25,28,.45);
    display:none;align-items:center;justify-content:center;padding:20px}
  .modal-ov.show{display:flex}
  .modal{background:var(--paper);border:1px solid var(--line);border-radius:8px;
    box-shadow:0 12px 44px rgba(0,0,0,.28);max-width:460px;width:100%;padding:22px 24px}
  .modal h3{margin:0 0 10px;font-size:18px}
  .modal p{margin:0 0 20px;font-size:14px;line-height:1.5;color:var(--ink)}
  .modal-btns{display:flex;justify-content:flex-end;gap:10px}
  .mbtn{font-size:14px;font-weight:700;padding:10px 20px;border-radius:6px;cursor:pointer;
    border:1px solid}
  .mbtn.cancel{background:var(--paper);border-color:var(--line);color:var(--ink)}
  .mbtn.cancel:hover{background:var(--faint)}
  .mbtn.confirm{color:#fff;border-color:transparent}
  .mbtn.confirm:hover{filter:brightness(1.08)}
  .mbtn.confirm.contain{background:var(--bad)}
  .mbtn.confirm.restore{background:var(--ok)}
  /* ---- idle ---- */
  .idle{padding:120px 40px;text-align:center}
  .idle .pulse{width:16px;height:16px;border-radius:50%;background:var(--ok);margin:0 auto 20px;
    animation:pulse 2.4s infinite}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(47,122,74,.5)}
    70%{box-shadow:0 0 0 16px rgba(47,122,74,0)}100%{box-shadow:0 0 0 0 rgba(47,122,74,0)}}
  .idle h2{font-size:21px;margin:0 0 6px} .idle p{color:var(--muted);margin:0}
  @media (max-width:980px){ .grid{grid-template-columns:1fr} }
  @media (prefers-reduced-motion:reduce){ *{animation:none!important;transition:none!important} }
</style></head>
<body>
<div class="wrap">
  <div class="top">
    <div class="brand">MIRAGE<small>Security Operations</small></div>
    <span class="iid" id="iid"></span>
    <span class="pill l1" id="sevpill" style="display:none"></span>
    <span class="guard" id="guard"><span class="dot"></span><span id="guardtxt">guard ok</span></span>
    <span class="status open" id="status" style="display:none">OPEN</span>
  </div>
  <div class="actions" id="actions" style="display:none">
    <span class="alabel">Analyst decision</span>
    <div class="banner" id="banner"></div>
    <div class="acts">
      <button class="big contain" id="btnContain" disabled>Contain</button>
      <button class="big restore" id="btnRestore" disabled>Restore</button>
    </div>
  </div>
  <div id="main">
    <div class="panel"><div class="idle">
      <div class="pulse"></div>
      <h2>No active incident</h2>
      <p>System monitoring. This console populates automatically when a mine is opened.</p>
    </div></div>
  </div>
</div>

<div class="modal-ov" id="modalOv">
  <div class="modal" role="dialog" aria-modal="true">
    <h3 id="modalTitle"></h3>
    <p id="modalMsg"></p>
    <div class="modal-btns">
      <button class="mbtn cancel" id="modalCancel">Cancel</button>
      <button class="mbtn confirm contain" id="modalConfirm">Confirm</button>
    </div>
  </div>
</div>

<script>
const LV={1:["l1","Low"],2:["l2","Medium"],3:["l3","High"],4:["l4","Critical"]};
const KIND={ai_agent:"AI agent",ai_guided_by_human:"AI agent (human-guided)",
  script:"Automated script",human:"Human operator"};
let curId=null;        // incident currently rendered
let curStatus=null;    // last status shown (so we only touch the DOM on change)
let approved=false;    // cosmetic approval, reset per new incident

function esc(s){return (s==null?"":String(s)).replace(/[&<>"]/g,c=>(
  {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

// Unix seconds -> local HH:MM:SS for the timeline. Falls back to "--:--:--".
function clockOf(ts){
  const n=Number(ts);
  if(!isFinite(n)||n<=0) return '--:--:--';
  const d=new Date(n*1000), p=x=>String(x).padStart(2,'0');
  return p(d.getHours())+':'+p(d.getMinutes())+':'+p(d.getSeconds());
}

// Small, safe markdown -> HTML. Input is escaped FIRST, so no raw HTML can pass.
function md(src){
  const inline=t=>esc(t).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  const lines=String(src||"").split(/\r?\n/);
  let out=[],ul=null,para=[];
  const flushP=()=>{ if(para.length){out.push('<p>'+para.map(inline).join('<br>')+'</p>');para=[];} };
  const flushU=()=>{ if(ul){out.push('<ul>'+ul.join('')+'</ul>');ul=null;} };
  for(const raw of lines){
    const line=raw.trimEnd();
    if(!line.trim()){ flushP();flushU();continue; }
    if(/^##\s+/.test(line)){ flushP();flushU();out.push('<h2>'+inline(line.replace(/^##\s+/,''))+'</h2>');continue; }
    if(/^#\s+/.test(line)){ flushP();flushU();out.push('<h1>'+inline(line.replace(/^#\s+/,''))+'</h1>');continue; }
    if(/^[-*]\s+/.test(line)){ flushP(); (ul=ul||[]).push('<li>'+inline(line.replace(/^[-*]\s+/,''))+'</li>');continue; }
    flushU(); para.push(line);
  }
  flushP();flushU();
  return out.join('\n');
}
// Strip the leading "AI DRAFT ..." banner line; it is shown as a ribbon instead.
function stripBanner(src){
  return String(src||"").replace(/^\s*AI DRAFT[^\n]*\n?/i,'').replace(/^\s+/,'');
}

// --- top bar: status word + severity pill (updated live, no full rebuild) ----
function setStatus(st){
  const el=document.getElementById('status');
  const s=(st||'open').toLowerCase();
  el.style.display='';
  el.className='status '+s;
  el.textContent=s.toUpperCase();
  curStatus=s;
}
function setSeverity(sv){
  const [cls,name]=LV[(sv&&sv.level)||1]||["l1","Low"];
  const el=document.getElementById('sevpill');
  el.style.display='';
  el.className='pill '+cls;
  el.textContent=(sv&&sv.level>=4?'CRITICAL ':'')+name.toUpperCase()+' · L'+((sv&&sv.level)||1);
}

function renderIdle(){
  curId=null; curStatus=null;
  document.getElementById('iid').textContent='';
  document.getElementById('sevpill').style.display='none';
  document.getElementById('status').style.display='none';
  document.getElementById('main').innerHTML=
    '<div class="panel"><div class="idle"><div class="pulse"></div>'+
    '<h2>No active incident</h2>'+
    '<p>System monitoring. This console populates automatically when a mine is opened.</p></div></div>';
  document.getElementById('actions').style.display='none';
  const bc=document.getElementById('btnContain'), br=document.getElementById('btnRestore');
  bc.disabled=true; br.disabled=true; bc.className='big contain'; br.className='big restore';
  bc.textContent='Contain'; br.textContent='Restore';
}

function chip(status){
  const s=(status||'unverified').toLowerCase();
  return '<span class="chip '+esc(s)+'">'+esc(s)+'</span>';
}

function render(inc,card,summary){
  const sv=card.severity||{level:1,label:"Low",reasons:[]};
  const intr=card.intruder||{kind:"unknown",confidence:"low",reasons:[]};
  const kindName=KIND[intr.kind]||esc(intr.kind);
  const lost=(inc.real_files_lost||[]).length;
  const decoys=(inc.fakes_taken||[]).length;
  const cost=card.cost||{};
  const claims=card.claims||[];
  const tl=card.timeline||[];

  // ----- LEFT: live dashboard -----
  const tiles=`
    <div class="tiles">
      <div class="tile wide"><div class="k">Intruder</div><div class="v">${kindName}</div>
        <div class="x">${esc(intr.confidence)} confidence${(intr.reasons||[]).length?' · '+esc((intr.reasons||[]).join('; ')):''}</div></div>
      <div class="tile"><div class="k">Swap time</div><div class="v">${inc.swap_ms!=null?esc(inc.swap_ms)+' ms':'–'}</div>
        <div class="x">${inc.swapped?'crown jewels swapped':'not swapped'}</div></div>
      <div class="tile"><div class="k">Decoys taken</div><div class="v">${decoys}</div>
        <div class="x">AI-forged fakes</div></div>
      <div class="tile wide"><div class="k">Attacker cost</div>
        <div class="v">wasted ${cost.seconds_on_fakes!=null?esc(cost.seconds_on_fakes):'?'}s + ${esc(cost.commands!=null?cost.commands:'?')} commands on fakes</div></div>
    </div>`;

  const claimsHtml=claims.length?claims.map(c=>`
    <div class="claim"><div class="row"><div class="txt">${esc(c.text)}</div>${chip(c.status)}</div>
      <div class="ev">${esc(c.evidence||'')}</div></div>`).join('')
    :'<div class="x" style="color:var(--muted)">No stated objective captured.</div>';

  const tlHtml=tl.map(e=>`
    <li><span class="clk">${clockOf(e.ts)}</span>
      <span class="tid${e.defensive?' def':''}">${esc(e.technique_id||(e.defensive?'DEFEND':'—'))}</span>
      <span class="ty">${esc(e.type)}</span>
      <span class="dt">${esc(e.detail||e.ref||'')}</span>
      ${e.defensive?'<span class="def-tag">defensive</span>':''}</li>`).join('');

  const left=`
    <div class="panel hero ${lost?'breach':''}">
      <b>${lost}</b><span>${lost===0?'real files lost':'REAL FILES EXPOSED'}</span>
    </div>
    <div class="panel" style="padding:15px">${tiles}</div>
    <div class="panel sect"><h3>Confession &mdash; checked against logs</h3>${claimsHtml}</div>
    <div class="panel sect"><h3>ATT&amp;CK timeline</h3><ul class="tl">${tlHtml}</ul></div>`;

  // ----- RIGHT: detailed report -----
  const body=md(stripBanner(summary.summary));
  const nis2=md(stripBanner(summary.nis2));
  const ribbon=approved
    ? '<div class="ribbon approved"><b>APPROVED</b> Reviewed and signed off by analyst (demo).</div>'
    : '<div class="ribbon"><b>AI DRAFT</b> &mdash; pending analyst approval. Not sent.</div>';
  const right=`
    <div class="panel report">
      ${ribbon}
      <div class="rendered">${body}</div>
      <div class="rec"><h4>Recommended actions</h4><ol>
        <li>Contain the session.</li>
        <li>Rotate svc_backup + billing credentials.</li>
        <li>File the NIS2 early warning within 24h.</li>
      </ol></div>
      <details class="nis2"><summary>NIS2 early-warning draft (Article 23)</summary>
        <div class="inner">${nis2}</div></details>
      <button class="approve" id="approve" ${approved?'disabled':''}>${approved?'Draft approved':'Approve draft'}</button>
    </div>`;

  document.getElementById('iid').textContent='Incident '+esc(inc.id);
  document.getElementById('actions').style.display='flex';
  document.getElementById('main').innerHTML=
    `<div class="grid"><div class="col">${left}</div><div class="col">${right}</div></div>`;
  setSeverity(sv);
  setStatus(inc.status);
  reflectButtons(inc.status);

  const btn=document.getElementById('approve');
  if(btn) btn.onclick=()=>{ approved=true;
    btn.disabled=true; btn.textContent='Draft approved';
    const r=document.querySelector('.ribbon');
    if(r){ r.className='ribbon approved';
      r.innerHTML='<b>APPROVED</b> Reviewed and signed off by analyst (demo).'; } };
}

// Enable/disable + label the big buttons to match the real status.
function reflectButtons(status){
  const s=(status||'open').toLowerCase();
  const bc=document.getElementById('btnContain'), br=document.getElementById('btnRestore');
  const contained=(s==='contained'||s==='restored'), restored=(s==='restored');
  bc.disabled=contained; bc.className='big contain'+(contained?' done':'');
  bc.textContent=contained?'Contained':'Contain';
  br.disabled=restored; br.className='big restore'+(restored?' done':'');
  br.textContent=restored?'Restored':'Restore';
}

// Result banner (emoji-free). Lives outside #main so a full re-render or the 2s
// poll never wipes it; it fades out on its own after a few seconds.
let bannerTimer=null;
function showBanner(kind,msg){
  const b=document.getElementById('banner');
  b.className='banner show '+kind; b.textContent=msg;
  if(bannerTimer) clearTimeout(bannerTimer);
  bannerTimer=setTimeout(()=>{ b.className='banner '+kind; },6000);
}

// --- in-page confirmation modal (no window.confirm/alert) ----
let pendingKind=null;
function openConfirm(kind){
  if(!curId) return;
  pendingKind=kind;
  const title=document.getElementById('modalTitle');
  const msg=document.getElementById('modalMsg');
  const cf=document.getElementById('modalConfirm');
  if(kind==='contain'){
    title.textContent='Contain this incident?';
    msg.textContent="The attacker's session will be terminated and the account locked.";
    cf.className='mbtn confirm contain'; cf.textContent='Contain';
  }else{
    title.textContent='Restore the real files?';
    msg.textContent='Restore the real files for this incident?';
    cf.className='mbtn confirm restore'; cf.textContent='Restore';
  }
  document.getElementById('modalOv').classList.add('show');
}
function closeConfirm(){
  document.getElementById('modalOv').classList.remove('show');
  pendingKind=null;
}
document.getElementById('modalCancel').onclick=closeConfirm;
document.getElementById('modalConfirm').onclick=()=>{ const k=pendingKind; closeConfirm(); if(k) doAction(k); };
document.getElementById('modalOv').onclick=e=>{ if(e.target.id==='modalOv') closeConfirm(); };
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closeConfirm(); });

async function doAction(kind){
  if(!curId) return;
  const id=curId;
  const bc=document.getElementById('btnContain'), br=document.getElementById('btnRestore');
  bc.disabled=true; br.disabled=true;
  try{
    const r=await fetch(`/incidents/${id}/${kind}`,{method:'POST'});
    if(!r.ok) throw new Error('bad status '+r.status);
    const inc=await r.json();
    // Re-fetch card + summary and FULLY re-render so the view shows the new
    // state (timeline gains the contain/restore step, status flips, etc.).
    const [card,summary]=await Promise.all([
      (await fetch(`/incidents/${id}/card`)).json(),
      (await fetch(`/incidents/${id}/summary`)).json(),
    ]);
    const decoys=(inc.fakes_taken||[]).length;
    render(inc,card,summary);
    if(kind==='contain'){
      showBanner('good','CONTAINED — attacker session terminated, account svc_backup locked, no new logins.');
    }else{
      showBanner('good',`RESTORED — ${decoys} real file(s) returned to their location, decoys removed.`);
    }
  }catch(e){
    showBanner('err','Action failed — guard unreachable.');
    // Re-fetch to reflect the true status regardless.
    try{
      const incs=await (await fetch('/incidents')).json();
      const inc=incs.find(i=>i.id===id);
      if(inc){ setStatus(inc.status); reflectButtons(inc.status); }
      else reflectButtons(curStatus);
    }catch(_){ reflectButtons(curStatus); }
  }
}
document.getElementById('btnContain').onclick=()=>openConfirm('contain');
document.getElementById('btnRestore').onclick=()=>openConfirm('restore');

async function tick(){
  // Guard indicator (best-effort).
  try{
    const g=await (await fetch('/health/guard?host=lumen-fs01&max_silence_s=15')).json();
    const el=document.getElementById('guard');
    el.className='guard'+(g.alarm?' silent':'');
    document.getElementById('guardtxt').textContent=g.alarm?'GUARD SILENT':'guard ok';
  }catch(e){/* ignore */}
  // Latest incident.
  try{
    const incs=await (await fetch('/incidents')).json();
    if(!incs.length){ if(curId!==null) renderIdle(); return; }
    const inc=incs[0];
    if(inc.id===curId){
      // Same incident: keep UI state, just reflect any live status change.
      if((inc.status||'').toLowerCase()!==curStatus){ setStatus(inc.status); reflectButtons(inc.status); }
      return;
    }
    const [card,summary]=await Promise.all([
      (await fetch(`/incidents/${inc.id}/card`)).json(),
      (await fetch(`/incidents/${inc.id}/summary`)).json(),
    ]);
    curId=inc.id; approved=false;
    render(inc,card,summary);
  }catch(e){/* core restarting; keep polling */}
}
tick(); setInterval(tick,2000);
</script>
</body></html>
"""


@console_router.get("/console", response_class=HTMLResponse)
def console() -> str:
    return _PAGE
