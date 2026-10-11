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
  button flips it to APPROVED), an "Edit" button that lets the analyst edit the
  draft in place (client-side only), a static "Recommended actions" box and the
  NIS2 early-warning draft in a ``<details>``;
* the human decision (a clean action panel directly under the top bar) — a real
  DECISION panel keyed to the incident status. While ``open`` it offers CONTAIN
  (red) / KEEP WATCHING (amber) / DISMISS (grey); while ``watching`` it still
  offers CONTAIN / DISMISS; once ``contained`` it offers RESTORE (green); once
  ``dismissed`` or ``restored`` it shows a closed note. Each choice first opens
  an in-page confirmation modal; only on Confirm does it POST to the real
  control endpoints, so clicking really drives the guard / incident store. The
  result is made unmistakable: the whole view is re-fetched and re-rendered with
  the new state and a prominent (emoji-free) result banner is shown, while the
  big status word changes colour and text.

It polls ``/incidents`` (+ card + summary for the newest) every 2s and only
rebuilds the DOM when the incident id changes, so the approve state, the analyst
edit, an open NIS2 panel and a just-shown action banner survive refreshes. This
is a NEW page; ``/report`` (Option A), ``/`` (viewer) and the hero card are
untouched.
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
    --ok:#2f7a4a; --bad:#b3261e; --warn:#b07908; --grey:#5e6a70;
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
  .status.open{color:var(--bad);border-color:var(--bad);background:#fbecea}
  .status.watching{color:var(--warn);border-color:var(--warn);background:#fdf6e6}
  .status.contained{color:var(--bad);border-color:var(--bad);background:#fbecea}
  .status.dismissed{color:var(--grey);border-color:var(--grey);background:#eef1f2}
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
  .ribbon .editednote{font-weight:700;letter-spacing:.3px;color:var(--accent)}
  .ribbon.approved .editednote{color:var(--ok)}
  .rendered{font-family:Georgia,"Times New Roman",'Noto Serif',serif;font-size:15.5px;line-height:1.65}
  .rendered h1{font-size:23px;line-height:1.25;margin:.2em 0 .5em;font-weight:700}
  .rendered h2{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size:13px;letter-spacing:.6px;text-transform:uppercase;color:var(--accent);
    margin:1.5em 0 .5em;padding-bottom:5px;border-bottom:1px solid var(--line)}
  .rendered p{margin:.6em 0} .rendered ul{margin:.5em 0;padding-left:1.3em}
  .rendered li{margin:.22em 0} .rendered strong{font-weight:700}
  .editarea{width:100%;min-height:340px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:13px;line-height:1.5;padding:14px;border:1px solid var(--line);border-radius:6px;
    resize:vertical;color:var(--ink);background:var(--faint)}
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
  .reportbtns{margin-top:18px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  button.approve{font-size:13px;font-weight:600;padding:9px 18px;border-radius:6px;
    border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
  button.approve:hover{filter:brightness(1.08)}
  button.approve[disabled]{background:#eef7f0;color:var(--ok);border-color:var(--ok);cursor:default;filter:none}
  button.editbtn,button.editcancel,button.reportact{font-size:13px;font-weight:600;padding:9px 18px;border-radius:6px;
    border:1px solid var(--line);background:var(--paper);color:var(--ink);cursor:pointer}
  button.editbtn:hover,button.editcancel:hover,button.reportact:hover{background:var(--faint)}
  /* ---- decision panel (under top bar) ---- */
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
  .acts{margin-left:auto;display:flex;gap:12px;align-items:stretch;flex-wrap:wrap;justify-content:flex-end}
  button.choice{display:flex;flex-direction:column;align-items:flex-start;gap:2px;border:0;
    border-radius:8px;padding:9px 15px;cursor:pointer;color:#fff;text-align:left;
    min-width:148px;max-width:230px;font:inherit}
  button.choice .ct{font-size:14px;font-weight:800;letter-spacing:.6px;text-transform:uppercase}
  button.choice .cr{font-size:10.5px;font-weight:500;line-height:1.3;opacity:.93;
    text-transform:none;letter-spacing:.1px}
  button.choice.contain{background:var(--bad)} button.choice.watch{background:var(--warn)}
  button.choice.dismiss{background:var(--grey)} button.choice.restore{background:var(--ok)}
  button.choice:hover{filter:brightness(1.08)}
  button.choice[disabled]{opacity:.55;cursor:default;filter:none}
  .dnote{align-self:center;font-size:12.5px;font-weight:700;padding:7px 13px;border-radius:6px;
    border:1px solid}
  .dnote.amber{color:var(--warn);border-color:var(--warn);background:#fdf6e6}
  .dnote.grey{color:var(--grey);border-color:#c7cfd3;background:#eef1f2}
  .dnote.ok{color:var(--ok);border-color:var(--ok);background:#eaf5ee}
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
  .mbtn.confirm.watch{background:var(--warn)}
  .mbtn.confirm.dismiss{background:var(--grey)}
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
    <div class="acts" id="acts"></div>
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
let edited=false;      // analyst edited the draft, reset per new incident
let editing=false;     // the report body is in textarea edit mode
let editText=null;     // the analyst-edited markdown (null = use the AI draft)
let lastInc=null,lastCard=null,lastSummary=null;  // for in-place re-renders

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
  approved=false; edited=false; editing=false; editText=null;
  lastInc=null; lastCard=null; lastSummary=null;
  document.getElementById('iid').textContent='';
  document.getElementById('sevpill').style.display='none';
  document.getElementById('status').style.display='none';
  document.getElementById('main').innerHTML=
    '<div class="panel"><div class="idle"><div class="pulse"></div>'+
    '<h2>No active incident</h2>'+
    '<p>System monitoring. This console populates automatically when a mine is opened.</p></div></div>';
  document.getElementById('actions').style.display='none';
  document.getElementById('acts').innerHTML='';
}

function chip(status){
  const s=(status||'unverified').toLowerCase();
  return '<span class="chip '+esc(s)+'">'+esc(s)+'</span>';
}

function render(inc,card,summary){
  lastInc=inc; lastCard=card; lastSummary=summary;
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

  // ----- RIGHT: detailed report (with analyst Approve / Edit) -----
  const rawBody=stripBanner(summary.summary);
  const shownMd=(editText!=null?editText:rawBody);
  const nis2=md(stripBanner(summary.nis2));

  const editedNote='<span class="editednote">&mdash; Edited by analyst</span>';
  const ribbon=approved
    ? '<div class="ribbon approved"><b>APPROVED'+(edited?' (edited by analyst)':'')+'</b> Reviewed and signed off by analyst (demo).</div>'
    : '<div class="ribbon"><b>AI DRAFT</b> &mdash; pending analyst approval. Not sent.'+(edited?' '+editedNote:'')+'</div>';

  let bodyRegion, btnRegion;
  if(editing){
    bodyRegion='<textarea class="editarea" id="editArea">'+esc(shownMd)+'</textarea>';
    btnRegion='<div class="reportbtns">'+
      '<button class="approve" id="saveEdit">Save</button>'+
      '<button class="editcancel" id="cancelEdit">Cancel</button></div>';
  }else{
    bodyRegion='<div class="rendered" id="reportBody">'+md(shownMd)+'</div>';
    btnRegion='<div class="reportbtns">'+
      '<button class="approve" id="approve" '+(approved?'disabled':'')+'>'+(approved?'Draft approved':'Approve draft')+'</button>'+
      (approved
        ? '<button class="reportact" id="downloadReport">Download report</button>'+
          '<button class="reportact" id="shareReport">Share</button>'
        : '')+
      '<button class="editbtn" id="editReport">Edit</button></div>';
  }
  const right=`
    <div class="panel report">
      ${ribbon}
      ${bodyRegion}
      <div class="rec"><h4>Recommended actions</h4><ol>
        <li>Contain the session.</li>
        <li>Rotate svc_backup + billing credentials.</li>
        <li>File the NIS2 early warning within 24h.</li>
      </ol></div>
      <details class="nis2"><summary>NIS2 early-warning draft (Article 23)</summary>
        <div class="inner">${nis2}</div></details>
      ${btnRegion}
    </div>`;

  document.getElementById('iid').textContent='Incident '+esc(inc.id);
  document.getElementById('actions').style.display='flex';
  document.getElementById('main').innerHTML=
    `<div class="grid"><div class="col">${left}</div><div class="col">${right}</div></div>`;
  setSeverity(sv);
  setStatus(inc.status);
  renderDecision(inc.status);
  wireReport();
}

// Wire the report Approve / Edit / Save / Cancel buttons (re-created each render).
function wireReport(){
  const ap=document.getElementById('approve');
  if(ap) ap.onclick=()=>{ approved=true; editing=false; render(lastInc,lastCard,lastSummary); };
  const ed=document.getElementById('editReport');
  if(ed) ed.onclick=()=>{ editing=true; render(lastInc,lastCard,lastSummary); };
  const sv=document.getElementById('saveEdit');
  if(sv) sv.onclick=()=>{
    const ta=document.getElementById('editArea');
    if(ta) editText=ta.value;
    edited=true; editing=false; render(lastInc,lastCard,lastSummary);
  };
  const cx=document.getElementById('cancelEdit');
  if(cx) cx.onclick=()=>{ editing=false; render(lastInc,lastCard,lastSummary); };
  const dl=document.getElementById('downloadReport');
  if(dl) dl.onclick=downloadReport;
  const sh=document.getElementById('shareReport');
  if(sh) sh.onclick=shareReport;
}

// Build one combined plain-text/markdown document from the APPROVED report:
// the incident summary (analyst-edited text when edited, else the AI draft) plus
// the NIS2 early-warning draft. Used by Download report and Share.
function buildReportDoc(){
  const id=(lastInc&&lastInc.id)||'';
  const rawBody=stripBanner(lastSummary&&lastSummary.summary);
  const summaryMd=(editText!=null?editText:rawBody);
  const nis2Md=stripBanner(lastSummary&&lastSummary.nis2);
  const when=new Date().toLocaleString();
  return 'MIRAGE — Incident report\n'+
    'Incident: '+id+'    Approved by analyst'+(edited?', edited':'')+' — '+when+'\n\n'+
    '===== Incident summary =====\n'+summaryMd+'\n\n'+
    '===== NIS2 early warning (Article 23) =====\n'+nis2Md+'\n';
}

function safeId(){
  const id=String((lastInc&&lastInc.id)||'incident');
  return id.replace(/[^A-Za-z0-9._-]/g,'_')||'incident';
}

// Download report: client-side only — a text/markdown Blob + object URL.
function downloadReport(){
  const doc=buildReportDoc();
  try{
    const blob=new Blob([doc],{type:'text/markdown'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url; a.download='MIRAGE-incident-'+safeId()+'.md';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),0);
  }catch(e){ showManualCopy(doc); }
}

// Share: Web Share API inside the click (user gesture), else copy to clipboard,
// else a selectable textarea modal for manual copy.
async function shareReport(){
  const doc=buildReportDoc();
  const title='MIRAGE incident report '+((lastInc&&lastInc.id)||'');
  const data={title:title,text:doc};
  if(navigator.share && (typeof navigator.canShare!=='function' || navigator.canShare(data))){
    try{
      await navigator.share(data);
      return;
    }catch(e){
      if(e && e.name==='AbortError') return;  // user cancelled; nothing to do
      // any other share failure falls through to the clipboard fallback
    }
  }
  try{
    await navigator.clipboard.writeText(doc);
    showBanner('good','Report copied to clipboard — ready to send to the authority.');
  }catch(e){
    showManualCopy(doc);
  }
}

// Last-resort fallback: a simple selectable modal so the analyst can copy manually.
function showManualCopy(doc){
  let ov=document.getElementById('copyOv');
  if(!ov){
    ov=document.createElement('div');
    ov.id='copyOv'; ov.className='modal-ov';
    ov.innerHTML='<div class="modal" role="dialog" aria-modal="true">'+
      '<h3>Copy the report</h3>'+
      '<p>Select all and copy the report below to send it to the authority.</p>'+
      '<textarea class="editarea" id="copyArea" readonly style="min-height:260px"></textarea>'+
      '<div class="modal-btns" style="margin-top:16px">'+
      '<button class="mbtn cancel" id="copyClose">Close</button></div></div>';
    document.body.appendChild(ov);
    ov.onclick=e=>{ if(e.target.id==='copyOv') ov.classList.remove('show'); };
    ov.querySelector('#copyClose').onclick=()=>ov.classList.remove('show');
  }
  const ta=ov.querySelector('#copyArea');
  ta.value=doc;
  ov.classList.add('show');
  ta.focus(); ta.select();
}

// Build the decision panel for the given status and wire its choices.
function choiceBtn(kind,label,rationale){
  return '<button class="choice '+kind+'" data-k="'+kind+'">'+
    '<span class="ct">'+esc(label)+'</span>'+
    '<span class="cr">'+esc(rationale)+'</span></button>';
}
function renderDecision(status){
  const s=(status||'open').toLowerCase();
  const acts=document.getElementById('acts');
  let html='';
  if(s==='open'){
    html=choiceBtn('contain','Contain now','Lock the account and kill the session.')
       +choiceBtn('watch','Keep watching','Leave them in the decoys to gather intel — they only have fakes.')
       +choiceBtn('dismiss','Dismiss — false alarm','Mark benign and close.');
  }else if(s==='watching'){
    html='<span class="dnote amber">Observing — intruder left in the decoys</span>'
       +choiceBtn('contain','Contain now','Lock the account and kill the session.')
       +choiceBtn('dismiss','Dismiss — false alarm','Mark benign and close.');
  }else if(s==='contained'){
    html=choiceBtn('restore','Restore real files','Threat stopped; return the real files.');
  }else if(s==='dismissed'){
    html='<span class="dnote grey">Closed as false alarm</span>';
  }else if(s==='restored'){
    html='<span class="dnote ok">Resolved — real files restored</span>';
  }
  acts.innerHTML=html;
  acts.querySelectorAll('button.choice').forEach(b=>{
    b.onclick=()=>openConfirm(b.getAttribute('data-k'));
  });
}

// Result banner (emoji-free). Lives outside #main and #acts so a full
// re-render or the 2s poll never wipes it; it fades out after a few seconds.
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
  }else if(kind==='watch'){
    title.textContent='Keep watching this incident?';
    msg.textContent='The intruder stays in the decoys; nothing real is at risk. You can escalate and contain later.';
    cf.className='mbtn confirm watch'; cf.textContent='Keep watching';
  }else if(kind==='dismiss'){
    title.textContent='Dismiss as a false alarm?';
    msg.textContent='This marks the incident benign and closes it.';
    cf.className='mbtn confirm dismiss'; cf.textContent='Dismiss';
  }else{ // restore
    title.textContent='Restore the real files?';
    msg.textContent='The threat is stopped. Return the real files to their location and remove the decoys.';
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

// Result banner text per action (emoji-free).
function actionBanner(kind,decoys){
  if(kind==='contain') return 'CONTAINED — attacker session terminated, account svc_backup locked, no new logins.';
  if(kind==='restore') return `RESTORED — ${decoys} real file(s) returned to their location, decoys removed.`;
  if(kind==='watch')   return 'WATCHING — intruder left in the decoys for intelligence.';
  if(kind==='dismiss') return 'DISMISSED — incident closed as a false alarm.';
  return '';
}

async function doAction(kind){
  if(!curId) return;
  const id=curId;
  const acts=document.getElementById('acts');
  acts.querySelectorAll('button.choice').forEach(b=>{ b.disabled=true; });
  const opts={method:'POST'};
  if(kind==='watch'){
    opts.headers={'Content-Type':'application/json'}; opts.body=JSON.stringify({user:'analyst'});
  }else if(kind==='dismiss'){
    opts.headers={'Content-Type':'application/json'}; opts.body=JSON.stringify({user:'analyst',reason:''});
  }
  try{
    const r=await fetch(`/incidents/${id}/${kind}`,opts);
    if(!r.ok) throw new Error('bad status '+r.status);
    const inc=await r.json();
    // Re-fetch card + summary and FULLY re-render so the view shows the new
    // state (timeline gains the decision step, status flips, panel changes).
    const [card,summary]=await Promise.all([
      (await fetch(`/incidents/${id}/card`)).json(),
      (await fetch(`/incidents/${id}/summary`)).json(),
    ]);
    const decoys=(inc.fakes_taken||[]).length;
    render(inc,card,summary);
    showBanner('good',actionBanner(kind,decoys));
  }catch(e){
    showBanner('err','Action failed — guard unreachable.');
    // Re-fetch to reflect the true status regardless.
    try{
      const incs=await (await fetch('/incidents')).json();
      const inc=incs.find(i=>i.id===id);
      if(inc){ setStatus(inc.status); renderDecision(inc.status); }
      else renderDecision(curStatus);
    }catch(_){ renderDecision(curStatus); }
  }
}

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
      if((inc.status||'').toLowerCase()!==curStatus){ setStatus(inc.status); renderDecision(inc.status); }
      return;
    }
    const [card,summary]=await Promise.all([
      (await fetch(`/incidents/${inc.id}/card`)).json(),
      (await fetch(`/incidents/${inc.id}/summary`)).json(),
    ]);
    curId=inc.id; approved=false; edited=false; editing=false; editText=null;
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
