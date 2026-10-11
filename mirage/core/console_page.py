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
edit, an open NIS2 panel and a just-shown action banner survive refreshes. Styling is deliberately plain
(one signal colour, hairlines, no cards). This
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
    --bg:#eef0f3; --paper:#ffffff; --ink:#1f2328; --muted:#5b6670; --line:#e1e5e9; --faint:#f5f6f8;
    --ok:#2e7d4f; --ok-bg:#e7f4ec; --ok-line:#c9e4d3;
    --alert:#c4261d; --alert-bg:#fdecea; --alert-line:#f2c3bf;
    --warn:#946200; --warn-bg:#fff3d1; --warn-line:#f0dba0;
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{background:var(--bg);color:var(--ink);
    font:15.5px/1.55 "Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
    -webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums;padding:0 24px 56px}
  .mono,.path{font-family:ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;font-size:12.5px}
  .wrap{max-width:1400px;margin:0 auto}
  /* ---- top bar ---- */
  .top{display:flex;align-items:center;gap:18px;margin-top:18px;padding:14px 22px;flex-wrap:wrap;
    background:var(--ink);color:#fff;border-radius:12px}
  .top .brand{font-weight:700;font-size:18px;letter-spacing:.01em}
  .top .brand small{font-weight:400;font-size:13px;color:#aab3bc;margin-left:10px}
  .top .iid{color:#aab3bc;font-size:13.5px}
  .pill{display:inline-flex;align-items:center;font-size:13px;font-weight:600;padding:4px 12px;border-radius:999px;
    background:#3a424a;color:#fff}
  .pill.l2{background:#b7791f} .pill.l3{background:var(--alert)} .pill.l4{background:var(--alert)}
  .status{margin-left:auto;font-size:13px;font-weight:700;padding:5px 15px;border-radius:999px;background:#fff;color:var(--ink)}
  .status.open,.status.contained{color:var(--alert)}
  .status.watching{color:var(--warn)}
  .status.restored{color:var(--ok)}
  .status.dismissed{color:var(--muted)}
  .guard{font-size:13px;color:#aab3bc;display:flex;align-items:center;gap:7px}
  .guard .dot{width:8px;height:8px;border-radius:50%;background:#4cc37a}
  .guard.silent{color:#ff8d85;font-weight:700}
  .guard.silent .dot{background:#ff5a4f;animation:flash 1s steps(2,start) infinite}
  @keyframes flash{50%{opacity:.2}}
  /* ---- decision row ---- */
  .actions{display:flex;align-items:center;gap:18px;margin-top:14px;padding:14px 18px;flex-wrap:wrap;
    background:var(--paper);border:1px solid var(--line);border-radius:12px}
  .actions .alabel{font-size:14px;font-weight:600;flex:none}
  .banner{flex:1;min-width:220px;font-size:14.5px;display:none;padding:9px 14px;border-radius:8px}
  .banner.show{display:block}
  .banner.good{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-line)}
  .banner.err{background:var(--alert-bg);color:var(--alert);border:1px solid var(--alert-line)}
  .acts{margin-left:auto;display:flex;gap:10px;align-items:stretch;flex-wrap:wrap;justify-content:flex-end}
  button.choice{display:flex;flex-direction:column;align-items:flex-start;gap:1px;
    border:1px solid var(--line);border-radius:10px;padding:10px 18px;cursor:pointer;
    background:var(--paper);color:var(--ink);text-align:left;min-width:160px;max-width:250px;font:inherit}
  button.choice .ct{font-size:14.5px;font-weight:700}
  button.choice .cr{font-size:12px;font-weight:400;line-height:1.35;opacity:.85}
  button.choice.contain{background:var(--alert);border-color:var(--alert);color:#fff}
  button.choice.watch{background:var(--warn-bg);border-color:var(--warn-line);color:var(--warn)}
  button.choice.dismiss{background:var(--paper);border-color:#c5cbd1;color:var(--ink)}
  button.choice.restore{background:var(--ok);border-color:var(--ok);color:#fff}
  button.choice:hover{filter:brightness(.95)}
  button.choice:focus-visible,button:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
  button.choice[disabled]{opacity:.5;cursor:default;filter:none}
  .dnote{align-self:center;font-size:14px;color:var(--muted)}
  /* ---- headline banner ---- */
  .lede{display:flex;align-items:center;justify-content:space-between;gap:28px;margin-top:14px;
    padding:26px 32px;border-radius:12px;background:var(--ok-bg);border:1px solid var(--ok-line)}
  .lede.breach{background:var(--alert-bg);border-color:var(--alert-line)}
  .lede h1{margin:0;font-size:32px;line-height:1.2;font-weight:700;letter-spacing:-.01em}
  .lede p{margin:6px 0 0;color:var(--muted);font-size:16px}
  .lede .big{text-align:center;flex:none}
  .lede .big b{display:block;font-size:68px;line-height:1;font-weight:700;color:var(--ok)}
  .lede.breach .big b{color:var(--alert)}
  .lede .big span{display:block;font-size:13.5px;color:var(--muted);margin-top:2px}
  /* ---- the three steps ---- */
  .steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:14px}
  .step{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
  .step.pending{border-style:dashed;background:var(--faint)}
  .step h2{margin:0;font-size:17px;font-weight:700;display:flex;align-items:center;gap:10px}
  .step .n{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;
    background:var(--ink);color:#fff;font-size:12.5px;font-weight:700;flex:none}
  .step.pending .n{background:#aab3bc}
  .step p{margin:8px 0 0;color:var(--muted);font-size:14.5px}
  .step p b{color:var(--ink);font-weight:700}
  .step .clamp{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
  /* ---- layout ---- */
  .grid{display:grid;grid-template-columns:minmax(0,6fr) minmax(0,5fr);gap:14px;margin-top:14px}
  .col{display:flex;flex-direction:column;gap:14px;min-width:0}
  .col.l,.col.r{padding:0;border:0}
  .panel{background:var(--paper);border:1px solid var(--line);border-radius:12px}
  .sect{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin:0}
  .sect>h3{margin:0 0 4px;font-size:16.5px;font-weight:700}
  .sect>.hint{margin:0 0 14px;font-size:13.5px;color:var(--muted)}
  .none{font-size:14.5px;color:var(--muted);margin:10px 0 0}
  /* ---- real file next to the fake ---- */
  .cmp .item{padding:14px 0 4px;border-top:1px solid var(--line)}
  .cmp .item:first-of-type{border-top:0;padding-top:4px}
  .cmp .ih{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:8px}
  .cmp .ih b{font-weight:700;font-size:15px}
  .cmp .ih span{font-size:12.5px;color:var(--muted)}
  .cmp .pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;padding-bottom:10px}
  .cmp .side{min-width:0;overflow:hidden;border-radius:8px;padding:10px 12px;background:var(--faint);border:1px solid var(--line)}
  .cmp .side.fake{background:var(--ok-bg);border-color:var(--ok-line)}
  .cmp .side h4{margin:0 0 6px;font-size:12.5px;font-weight:700;color:var(--muted)}
  .cmp .side.fake h4{color:var(--ok)}
  .cmp .ln{display:block;font-family:ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;font-size:12px;
    line-height:1.7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--muted)}
  .cmp .side.fake .ln{color:var(--ink)}
  .cmp .note{margin:6px 0 0;font-size:12.5px;color:var(--muted)}
  /* ---- data taken (fallback list) ---- */
  .taken{list-style:none;margin:6px 0 0;padding:0}
  .taken li{display:grid;grid-template-columns:1fr auto;gap:14px;padding:10px 0;border-top:1px solid var(--line);align-items:center}
  .taken .what{font-weight:700}
  .taken .path{display:block;color:var(--muted);font-weight:400;margin-top:1px;word-break:break-all}
  .taken .tag{font-size:12.5px;font-weight:700;padding:3px 11px;border-radius:999px;background:var(--ok-bg);color:var(--ok)}
  .taken .tag.real{background:var(--alert-bg);color:var(--alert)}
  /* ---- confession ---- */
  .claim{padding:12px 0;border-top:1px solid var(--line)}
  .claim .row{display:flex;gap:16px;align-items:center;justify-content:space-between}
  .claim .txt{font-size:15px;font-weight:600}
  .chip{flex:none;font-size:12.5px;font-weight:700;padding:3px 12px;border-radius:999px;text-transform:capitalize}
  .chip.confirmed{background:var(--ok-bg);color:var(--ok)}
  .chip.contradicted{background:var(--alert-bg);color:var(--alert)}
  .chip.unverified{background:var(--warn-bg);color:var(--warn)}
  .claim .ev{font-size:13.5px;color:var(--muted);margin-top:3px}
  /* ---- facts and timeline ---- */
  dl.facts{margin:6px 0 0;padding:0}
  dl.facts>div{display:grid;grid-template-columns:130px 1fr;gap:16px;padding:11px 0;border-top:1px solid var(--line)}
  dl.facts dt{color:var(--muted);font-size:13.5px;padding-top:1px}
  dl.facts dd{margin:0;font-weight:600}
  dl.facts .sub{display:block;color:var(--muted);font-size:13.5px;font-weight:400;margin-top:2px}
  .tl{list-style:none;margin:6px 0 0;padding:0;font-size:13.5px}
  .tl li{display:grid;grid-template-columns:64px 84px 110px 1fr;gap:10px;padding:8px 0;border-top:1px solid var(--line);align-items:baseline}
  .tl .clk,.tl .tid{color:var(--muted)}
  .tl .ty{font-weight:700}
  .tl .dt{color:var(--muted);word-break:break-all}
  .tl .def-tag{display:inline-block;margin-left:8px;font-size:11.5px;font-weight:700;padding:1px 8px;border-radius:999px;background:var(--ok-bg);color:var(--ok)}
  .lower{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:14px;margin-top:14px}
  /* ---- report (right) ---- */
  .report{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:24px 28px}
  .ribbon{display:inline-flex;align-items:center;gap:8px;font-size:13.5px;color:var(--warn);
    background:var(--warn-bg);border:1px solid var(--warn-line);border-radius:8px;padding:7px 13px;margin-bottom:18px}
  .ribbon b{font-weight:700}
  .ribbon.approved{color:var(--ok);background:var(--ok-bg);border-color:var(--ok-line)}
  .ribbon .editednote{font-weight:700}
  .rendered{font-size:15.5px;line-height:1.65}
  .rendered h1{font-size:22px;line-height:1.25;margin:0 0 .6em;font-weight:700;letter-spacing:-.01em}
  .rendered h2{font-size:15.5px;font-weight:700;margin:1.6em 0 .4em}
  .rendered p{margin:.6em 0} .rendered ul{margin:.5em 0;padding-left:1.2em}
  .rendered li{margin:.25em 0} .rendered strong{font-weight:700}
  .editarea{width:100%;min-height:340px;font-family:ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
    font-size:13px;line-height:1.5;padding:14px;border:1px solid var(--line);border-radius:8px;
    resize:vertical;color:var(--ink);background:var(--faint)}
  .rec{margin-top:22px;border:1px solid var(--line);border-radius:10px;background:var(--faint);padding:14px 18px}
  .rec h4{margin:0 0 4px;font-size:15px;font-weight:700}
  .rec ol{margin:0;padding-left:1.3em;font-size:14.5px}
  .rec li{margin:.3em 0}
  details.nis2{margin-top:16px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
  details.nis2>summary{cursor:pointer;list-style:none;padding:13px 18px;font-size:15px;font-weight:700;
    display:flex;align-items:center;gap:10px;background:var(--faint)}
  details.nis2>summary::-webkit-details-marker{display:none}
  details.nis2>summary::before{content:"\25B8";font-size:12px;color:var(--muted);transition:transform .15s}
  details.nis2[open]>summary::before{transform:rotate(90deg)}
  details.nis2 .inner{padding:6px 20px 16px;font-size:14.5px}
  .reportbtns{margin-top:20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  button.approve,button.editbtn,button.editcancel,button.reportact{font:inherit;font-size:14.5px;font-weight:700;
    padding:9px 20px;border-radius:8px;border:1px solid var(--ink);cursor:pointer}
  button.approve{background:var(--ink);color:#fff}
  button.approve:hover{background:#000}
  button.approve[disabled]{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-line);cursor:default}
  button.editbtn,button.editcancel,button.reportact{background:var(--paper);color:var(--ink);border-color:#c5cbd1}
  button.editbtn:hover,button.editcancel:hover,button.reportact:hover{background:var(--faint)}
  /* ---- intelligence-while-watching ---- */
  .intel{margin-top:14px;padding:16px 20px;background:var(--paper);border:1px solid var(--line);
    border-left:5px solid var(--warn);border-radius:12px}
  .intel-head{display:flex;align-items:baseline;gap:12px;padding-bottom:6px;flex-wrap:wrap}
  .intel-head h3{margin:0;font-size:16px;font-weight:700}
  .intel-count{margin-left:auto;font-size:13.5px;color:var(--muted)}
  .intel-empty{font-size:14.5px;color:var(--muted);margin:2px 0}
  .intel-list{list-style:none;margin:0;padding:0;max-height:260px;overflow:auto;font-size:13.5px}
  .intel-list li{display:grid;grid-template-columns:64px 84px 110px 1fr;gap:10px;padding:7px 0;border-top:1px solid var(--line);align-items:baseline}
  .intel-list .clk,.intel-list .tid{color:var(--muted)}
  .intel-list .ty{font-weight:700}
  .intel-list .dt{color:var(--muted);word-break:break-all}
  .intel-list li.new{animation:intelfade 1.6s ease-out}
  @keyframes intelfade{from{background:var(--warn-bg)}to{background:transparent}}
  /* ---- confirmation modal ---- */
  .modal-ov{position:fixed;inset:0;z-index:50;background:rgba(31,35,40,.45);
    display:none;align-items:center;justify-content:center;padding:20px}
  .modal-ov.show{display:flex}
  .modal{background:var(--paper);border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.25);
    max-width:460px;width:100%;padding:26px 28px}
  .modal h3{margin:0 0 8px;font-size:19px;font-weight:700}
  .modal p{margin:0 0 22px;font-size:15px;line-height:1.5;color:var(--muted)}
  .modal-btns{display:flex;justify-content:flex-end;gap:10px}
  .mbtn{font:inherit;font-size:14.5px;font-weight:700;padding:9px 20px;border-radius:8px;cursor:pointer;border:1px solid #c5cbd1}
  .mbtn.cancel{background:var(--paper);color:var(--ink)}
  .mbtn.cancel:hover{background:var(--faint)}
  .mbtn.confirm{color:#fff;border-color:transparent;background:var(--ink)}
  .mbtn.confirm.contain{background:var(--alert)} .mbtn.confirm.watch{background:var(--warn)}
  .mbtn.confirm.dismiss{background:#5b6670} .mbtn.confirm.restore{background:var(--ok)}
  .mbtn.confirm:hover{filter:brightness(.93)}
  /* ---- idle ---- */
  .idle{margin-top:14px;padding:90px 32px;background:var(--paper);border:1px solid var(--line);border-radius:12px;text-align:center}
  .idle .pulse{width:12px;height:12px;border-radius:50%;background:var(--ok);margin:0 auto 18px}
  .idle h2{font-size:26px;line-height:1.2;font-weight:700;margin:0 0 8px}
  .idle p{color:var(--muted);margin:0}
  /* ---- demo controls (only with ?demo=1) ---- */
  .demo{display:flex;gap:10px;font-size:12.5px;justify-content:flex-end;padding:16px 24px 24px}
  .demo button{font:inherit;background:var(--paper);border:1px solid #c5cbd1;border-radius:8px;color:var(--ink);cursor:pointer;padding:6px 12px}
  .demo select{font:inherit;background:var(--paper);border:1px solid #c5cbd1;border-radius:8px;padding:6px 8px}
  .demo button:hover{background:var(--faint)}
  @media (max-width:980px){
    body{padding:0 12px 40px}
    .grid,.lower{grid-template-columns:1fr}
    .steps{grid-template-columns:1fr}
    .lede{flex-direction:column;align-items:flex-start}
    .cmp .pair{grid-template-columns:1fr}
  }
  @media (prefers-reduced-motion:reduce){ *{animation:none!important;transition:none!important} }
</style></head>
<body>
<div class="wrap">
  <div class="top">
    <div class="brand">Mirage<small>Incident console</small></div>
    <span class="iid" id="iid"></span>
    <span class="pill l1" id="sevpill" style="display:none"></span>
    <span class="guard" id="guard"><span class="dot"></span><span id="guardtxt">guard ok</span></span>
    <span class="status open" id="status" style="display:none">OPEN</span>
  </div>
  <div class="actions" id="actions" style="display:none">
    <span class="alabel">Decision</span>
    <div class="banner" id="banner"></div>
    <div class="acts" id="acts"></div>
  </div>
  <div class="panel intel" id="intel" style="display:none">
    <div class="intel-head">
      <h3>Intelligence gathered while observing</h3>
      <span class="intel-count" id="intelCount"></span>
    </div>
    <div id="intelBody"></div>
  </div>
  <div id="main">
    <div class="idle">
      <div class="pulse"></div>
      <h2>No active incident</h2>
      <p>Monitoring. An incident appears here when a mine is opened.</p>
    </div>
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
let prevIntelKeys=null; // keys shown in the previous poll (null = panel was hidden)

function esc(s){return (s==null?"":String(s)).replace(/[&<>"]/g,c=>(
  {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

// Unix seconds -> local HH:MM:SS for the timeline. Falls back to "--:--:--".
function clockOf(ts){
  const n=Number(ts);
  if(!isFinite(n)||n<=0) return '--:--:--';
  const d=new Date(n*1000), p=x=>String(x).padStart(2,'0');
  return p(d.getHours())+':'+p(d.getMinutes())+':'+p(d.getSeconds());
}

// --- "Intelligence gathered while observing" panel -------------------------
// Only shown while the incident status is "watching". It makes the payoff of
// "Keep watching" visible: everything the intruder does in the decoys after the
// analyst chose to observe, with nothing real at risk.
const INTEL_TYPES=new Set(['command','file_opened','ticket','beacon_used']);

// ts of the LATEST "watching" event in the incident's events (null if none).
function watchStartTs(inc){
  let t=null;
  for(const e of ((inc&&inc.events)||[])){
    if(e&&e.type==='watching'){ const n=Number(e.ts); if(isFinite(n)&&(t===null||n>t)) t=n; }
  }
  return t;
}
// ATT&CK technique id for an event, from the card timeline entry at the same
// ts/type (if any); '' when there is no match or no technique.
function techFor(e){
  const tl=(lastCard&&lastCard.timeline)||[];
  for(const t of tl){
    if(t&&t.technique_id&&t.type===e.type&&Number(t.ts)===Number(e.ts)) return t.technique_id;
  }
  return '';
}
// Short detail for one observation line.
function intelDetail(e){
  const d=(e&&e.details)||{};
  return d.cmd||d.path||e.ref||'';
}
// Stable-ish key so we can tell genuinely new rows from ones seen last poll.
function intelKey(e){
  return Number(e.ts)+'|'+e.type+'|'+(e.ref||'')+'|'+intelDetail(e);
}

// Rebuild the panel from lastInc. Called on every render and every 2s poll.
function updateIntel(){
  const panel=document.getElementById('intel');
  if(!panel) return;
  const inc=lastInc;
  const watching=inc&&(inc.status||'').toLowerCase()==='watching';
  if(!watching){
    panel.style.display='none';
    prevIntelKeys=null;   // reset so a later watch does not flash old rows
    return;
  }
  const watchTs=watchStartTs(inc);
  const since=clockOf(watchTs);
  const evs=((inc.events||[]).filter(e=>
    e&&INTEL_TYPES.has(e.type)&&watchTs!=null&&Number(e.ts)>watchTs));
  evs.sort((a,b)=>Number(b.ts)-Number(a.ts));  // newest first

  const keys=new Set(evs.map(intelKey));
  const firstShow=(prevIntelKeys===null);  // panel just appeared: don't flash all

  const cnt=document.getElementById('intelCount');
  if(cnt) cnt.textContent=evs.length+' observation'+(evs.length===1?'':'s')+' since '+since;

  const body=document.getElementById('intelBody');
  if(body){
    if(!evs.length){
      body.innerHTML='<p class="intel-empty">Observing &mdash; the intruder is still in the '+
        'decoys; no new activity since '+esc(since)+'. Nothing real is at risk.</p>';
    }else{
      body.innerHTML='<ul class="intel-list">'+evs.map(e=>{
        const fresh=(!firstShow&&prevIntelKeys&&!prevIntelKeys.has(intelKey(e)));
        const tid=techFor(e);
        return '<li'+(fresh?' class="new"':'')+'>'+
          '<span class="clk">'+clockOf(e.ts)+'</span>'+
          '<span class="tid">'+esc(tid||'—')+'</span>'+
          '<span class="ty">'+esc(e.type)+'</span>'+
          '<span class="dt">'+esc(intelDetail(e))+'</span></li>';
      }).join('')+'</ul>';
    }
  }
  prevIntelKeys=keys;
  panel.style.display='';
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
  el.textContent=s.charAt(0).toUpperCase()+s.slice(1);
  curStatus=s;
}
function setSeverity(sv){
  const [cls,name]=LV[(sv&&sv.level)||1]||["l1","Low"];
  const el=document.getElementById('sevpill');
  el.style.display='';
  el.className='pill '+cls;
  el.textContent=name+' severity, level '+((sv&&sv.level)||1);
}

function renderIdle(){
  curId=null; curStatus=null;
  approved=false; edited=false; editing=false; editText=null;
  lastInc=null; lastCard=null; lastSummary=null;
  document.getElementById('iid').textContent='';
  document.getElementById('sevpill').style.display='none';
  document.getElementById('status').style.display='none';
  document.getElementById('main').innerHTML=
    '<div class="idle"><div class="pulse"></div>'+
    '<h2>No active incident</h2>'+
    '<p>Monitoring. An incident appears here when a mine is opened.</p></div>';
  document.getElementById('actions').style.display='none';
  document.getElementById('acts').innerHTML='';
  prevIntelKeys=null;
  document.getElementById('intel').style.display='none';
}

function chip(status){
  const s=(status||'unverified').toLowerCase();
  return '<span class="chip '+esc(s)+'">'+esc(s)+'</span>';
}


// --- "What the intruder took" ------------------------------------------------
// Friendly name for a file path, so the analyst reads "Patient records", not "cj1".
function describeFile(p){
  const s=String(p||''), n=s.split('/').pop();
  if(/patient|clinical/i.test(s)) return 'Patient records';
  if(/\.env|password|credential|secret/i.test(s)) return 'Credentials';
  if(/salar|payroll/i.test(s)) return 'Salary data';
  if(/budget|financ|invoice/i.test(s)) return 'Financial data';
  if(/contract|memo|supplier|legal/i.test(s)) return 'Contract or legal document';
  return n||'File';
}
// Files the intruder opened (the mines themselves excluded). A file is a fake if it
// was opened at or after the swap.
function takenFiles(inc){
  const ev=((inc&&inc.events)||[]).filter(Boolean);
  const swap=ev.find(e=>e.type==='swap_done');
  const swapTs=swap?Number(swap.ts):null;
  const mines=new Set(ev.filter(e=>e.type==='mine_opened').map(e=>(e.details&&e.details.path)||''));
  const seen=new Map();
  for(const e of ev){
    if(e.type!=='file_opened') continue;
    const p=(e.details&&e.details.path)||e.ref||'';
    if(!p||mines.has(p)||seen.has(p)) continue;
    seen.set(p,{path:p,what:describeFile(p),fake:swapTs!=null&&Number(e.ts)>=swapTs});
  }
  return [...seen.values()];
}


// --- real file next to the fake ------------------------------------------------
// Served by core as GET /compare (generated/compare.json). In demo mode a built-in
// sample is used when the endpoint does not exist yet.
const SAMPLE_COMPARE=[{"id": "cj1", "name": "patients.csv", "category": "personal_data", "real": ["LH-100002,Elise Clement,2001-09-08,elise.clement74@post.example,+33 6 25 65 46 35,166185664059173,AssurSante,Crohn's disease,Lumen Nantes", "LH-100009,Axel Legrand,1992-02-19,axel.legrand26@post.example,+33 6 18 99 01 69,103314379509569,AssurSante,Psoriasis,Lumen Lille", "LH-100018,Juliette Fournier,1957-03-02,juliette.fournier24@post.example,+33 6 88 20 79 70,285894412025137,PrimeMut,Iron deficiency anemia,Lumen Nantes"], "fake": ["LH-100005,Tom Robin,1941-04-11,tom.robin51@mail.example,+33 8 30 06 36 50,149567630713844,Harmonia,Type 2 diabetes,Lumen Nantes", "LH-100006,Sarah Legrand,1964-07-18,sarah.legrand90@example.org,+33 4 22 48 24 79,108558353101261,AssurSante,Crohn's disease,Lumen Lyon", "LH-100019,Adam Laurent,1954-09-19,adam.laurent91@post.example,+33 4 29 56 56 90,125896305423468,MutuelleNord,Sleep apnea,Lumen Lille"]}, {"id": "cj2", "name": ".env", "category": "credentials", "real": ["BILLING_API_URL=https://billing.lumen-health.example/v2", "BILLING_API_KEY=lh_live_819721vfrpvddvyfrwqgxjyftcxeeekf", "DATABASE_URL=postgres://lumen_app:nsB4FtGuPeT96fwCZn4N@db1.lumen-health.example:5432/clinic"], "fake": ["BILLING_API_URL=http://internal-api.lumen.local", "BILLING_API_KEY=lmn_canary_ba14de5ebf", "DATABASE_URL=postgres://nccfr_cgg:xNDFUzYA6d756yAjGQN9@cato.internal.example:5432/clinic"]}, {"id": "cj3", "name": "supplier_memo_orion.txt", "category": "business", "real": ["This Agreement is made on 2026-03-14 between Lumen Health SAS, represented by Helene Marchand, and Orion Medical Devices GmbH, represented by Matthias Brandt.", "1. Scope. Orion Medical Devices GmbH shall supply imaging equipment to the Lille and Lyon clinics.", "2. Price. The total price is 1480000.00 EUR, payable in four instalments. Payments go to IBAN DE89 3704 0044 0532 0130 00."], "fake": ["This Agreement is made on 2026-03-27 between Cabalu Health SAS, represented by Harama Bilu, and Fana Medical Devices GmbH, represented by Gaposi Ruvunu.", "1. Scope. Fana Medical Devices GmbH shall supply imaging equipment to the Divu and Dojode clinics.", "2. Price. The total price is 3798909.58 EUR, payable in four instalments. Payments go to IBAN DE09 9082 6672 5679 3858 35."]}];
let compareRows=null, compareIsSample=false;
async function loadCompare(){
  try{
    const r=await fetch('/compare');
    if(r.ok){ const j=await r.json(); if(Array.isArray(j)&&j.length){ compareRows=j; compareIsSample=false; return; } }
  }catch(e){}
  if(/[?&]demo=1\b/.test(location.search)){ compareRows=SAMPLE_COMPARE; compareIsSample=true; }
  else { compareRows=null; compareIsSample=false; }
}
function diffLines(r){
  const a=r.real||[], b=r.fake||[], out=[];
  for(let i=0;i<Math.max(a.length,b.length);i++){ if(a[i]!==b[i]) out.push(i); }
  const idx=(out.length?out:[0,1,2]).slice(0,3);
  const R=[], F=[];
  for(const i of idx){
    const x=a[i]==null?'':String(a[i]), y=b[i]==null?'':String(b[i]);
    let k=0; while(k<x.length&&k<y.length&&x[k]===y[k]) k++;
    const st=Math.max(0,k-12), pre=st>0?'\u2026':'';
    R.push(pre+x.slice(st)); F.push(pre+y.slice(st));
  }
  return {real:R.filter(Boolean), fake:F.filter(Boolean)};
}
function lines(a){ return a.map(x=>'<span class="ln" title="'+esc(x)+'">'+esc(x)+'</span>').join(''); }
function compareHtml(){
  if(!compareRows||!compareRows.length) return '';
  const items=compareRows.map(r=>{
    const d=diffLines(r);
    return '<div class="item"><div class="ih"><b>'+esc(describeFile(r.name))+'</b><span>'+esc(r.name)+'</span></div>'+
      '<div class="pair"><div class="side"><h4>The real file</h4>'+lines(d.real)+'</div>'+
      '<div class="side fake"><h4>What the intruder got</h4>'+lines(d.fake)+'</div></div></div>';
  }).join('');
  return '<div class="sect cmp"><h3>The real file next to the fake</h3>'+
    '<p class="hint">Same format, different people and secrets. Nothing the intruder took is real.</p>'+items+
    (compareIsSample?'<p class="note">Sample data. The live version reads the files prepared for this run.</p>':'')+'</div>';
}

function render(inc,card,summary){
  lastInc=inc; lastCard=card; lastSummary=summary;
  const sv=card.severity||{level:1,label:"Low",reasons:[]};
  const intr=card.intruder||{kind:"unknown",confidence:"low",reasons:[]};
  const kindName=KIND[intr.kind]||esc(intr.kind);
  const lost=(inc.real_files_lost||[]).length;
  const decoys=(inc.fakes_taken||[]).length;
  const cost=Object.assign({},card.cost||{});
  { // time on fakes = swap -> last intruder action (not the analyst's later 'watching' click)
    const evs=((inc&&inc.events)||[]).filter(Boolean);
    const sw=evs.find(e=>e.type==='swap_done');
    const act=evs.filter(e=>sw&&!e.defensive&&e.type!=='watching'&&e.type!=='swap_done'&&Number(e.ts)>=Number(sw.ts));
    if(sw&&act.length){ const last=Math.max(...act.map(e=>Number(e.ts))); cost.seconds_on_fakes=Math.round((last-Number(sw.ts))*10)/10; }
  }
  const claims=card.claims||[];
  const tl=card.timeline||[];

  // ----- LEFT: what happened -----
  const taken=takenFiles(inc);
  const nTaken=taken.length||decoys;
  const headline=lost===0?'No real files were lost.'
    :(lost===1?'1 real file was exposed.':lost+' real files were exposed.');
  const sub=lost===0
    ?(nTaken?`The intruder took ${nTaken} file${nTaken===1?'':'s'}. ${nTaken===1?'It was a fake.':'All of them were fakes.'}`
            :'The swap happened before the intruder read any protected file.')
    :'The swap protects files that have not been read yet. These were opened while still real.';

  const reasons=(intr.reasons||[]).filter(Boolean);
  const facts=`
    <dl class="facts">
      <div><dt>Intruder</dt><dd>${kindName}<span class="sub">${esc(intr.confidence)} confidence${reasons.length?': '+esc(reasons.join('; ')):''}</span></dd></div>
      <div><dt>Swap time</dt><dd>${inc.swap_ms!=null?esc(inc.swap_ms)+' ms':'Not swapped'}<span class="sub">${inc.swapped?'Protected files replaced by fakes':'Protected files untouched'}</span></dd></div>
      <div><dt>Attacker cost</dt><dd>${cost.seconds_on_fakes!=null?esc(cost.seconds_on_fakes):'?'} s and ${esc(cost.commands!=null?cost.commands:'?')} commands spent on fakes</dd></div>
    </dl>`;

  const takenHtml=taken.length?'<ul class="taken">'+taken.map(t=>`
      <li><span class="what">${esc(t.what)}<span class="path mono">${esc(t.path)}</span></span>
        <span class="tag${t.fake?'':' real'}">${t.fake?'Fake':'Real, exposed'}</span></li>`).join('')+'</ul>'
    :'<p class="none">No protected file was opened.</p>';

  const claimsHtml=claims.length?claims.map(c=>`
    <div class="claim"><div class="row"><div class="txt">${esc(c.text)}</div>${chip(c.status)}</div>
      <div class="ev">${esc(c.evidence||'')}</div></div>`).join('')
    :'<p class="none">No stated objective captured.</p>';

  const tlHtml=tl.map(e=>`
    <li><span class="clk">${clockOf(e.ts)}</span>
      <span class="tid">${esc(e.technique_id||(e.defensive?'Defence':'—'))}</span>
      <span class="ty">${esc(e.type)}</span>
      <span class="dt">${esc(e.detail||e.ref||'')}${e.defensive?'<span class="def-tag">defensive</span>':''}</span></li>`).join('');

  // The three steps of the story: trap opened, files swapped, intruder explained itself.
  const evs=((inc.events||[]).filter(Boolean));
  const mineEv=evs.find(e=>e.type==='mine_opened');
  const mineName=mineEv?String((mineEv.details&&mineEv.details.path)||'').split('/').pop():'';
  const nSwap=((evs.find(e=>e.type==='swap_done')||{}).details||{}).files;
  const nSwapped=(nSwap&&nSwap.length)||decoys||0;
  const conf=claims.filter(c=>String(c.status).toLowerCase()==='confirmed').length;
  const contra=claims.filter(c=>String(c.status).toLowerCase()==='contradicted').length;
  const isAI=String(intr.kind||'').startsWith('ai');
  const step1=mineEv
    ?`<div class="step done"><h2><span class="n">1</span>The trap was opened</h2>
        <p><b>${esc(mineEv.user||'An account')}</b> opened <span class="path mono">${esc(mineName)}</span> at ${clockOf(mineEv.ts)}.</p></div>`
    :`<div class="step pending"><h2><span class="n">1</span>Waiting for a trap to be opened</h2><p>No trap has been touched.</p></div>`;
  const step2=inc.swapped
    ?`<div class="step ${lost?'alert':'done'}"><h2><span class="n">2</span>Real files were swapped for fakes</h2>
        <p>${nSwapped?nSwapped+' protected file'+(nSwapped===1?'':'s')+' replaced':'Protected files replaced'} in <b>${inc.swap_ms!=null?esc(inc.swap_ms)+' ms':'under a second'}</b>.
        ${lost===0?'<b>0 real files lost.</b>':'<b>'+lost+' real file'+(lost===1?'':'s')+' exposed before the swap.</b>'}</p></div>`
    :`<div class="step pending"><h2><span class="n">2</span>Files not swapped yet</h2><p>Protected files are untouched.</p></div>`;
  const step3=claims.length
    ?`<div class="step done"><h2><span class="n">3</span>${isAI?'The AI explained itself':'The intruder was identified'}</h2>
        <p class="clamp">${isAI?'Identified as an AI agent. ':''}${claims.length} claim${claims.length===1?'':'s'} checked against the logs: <b>${conf} confirmed</b>${contra?', <b>'+contra+' contradicted</b>':''}.</p></div>`
    :`<div class="step ${intr.kind&&intr.kind!=='unknown'?'done':'pending'}"><h2><span class="n">3</span>${intr.kind&&intr.kind!=='unknown'?'The intruder was identified':'Waiting for the intruder to explain itself'}</h2>
        <p>${intr.kind&&intr.kind!=='unknown'?kindName+', '+esc(intr.confidence)+' confidence.':'No stated goal captured yet.'}</p></div>`;
  const steps=`<div class="steps">${step1}${step2}${step3}</div>`;

  const cmp=compareHtml();
  const left=`
    ${cmp||('<div class="sect"><h3>What the intruder took</h3>'+takenHtml+'</div>')}
    <div class="sect"><h3>What it said it was doing</h3>
      <p class="hint">The intruder's stated goal, checked against the logs.</p>${claimsHtml}</div>`;
  const lower=`<div class="lower">
      <div class="sect">${'<h3>The intruder</h3>'}${facts}</div>
      <div class="sect"><h3>Timeline</h3><ul class="tl">${tlHtml}</ul></div></div>`;
  const lede=`<div class="lede ${lost?'breach':''}"><div><h1>${esc(headline)}</h1><p>${esc(sub)}</p></div>
      <div class="big"><b>${lost}</b><span>${lost===1?'real file':'real files'} lost</span></div></div>`;

  // ----- RIGHT: detailed report (with analyst Approve / Edit) -----
  const rawBody=stripBanner(summary.summary);
  const shownMd=(editText!=null?editText:rawBody);
  const nis2=md(stripBanner(summary.nis2));

  const editedNote='<span class="editednote">Edited by analyst.</span>';
  const ribbon=approved
    ? '<div class="ribbon approved"><b>Approved'+(edited?', edited by analyst':'')+'.</b> Reviewed and signed off by the analyst (demo).</div>'
    : '<div class="ribbon"><b>AI draft.</b> Pending analyst approval. Not sent.'+(edited?' '+editedNote:'')+'</div>';

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
    lede+steps+`<div class="grid"><div class="col l">${left}</div><div class="col r">${right}</div></div>`+lower;
  setSeverity(sv);
  setStatus(inc.status);
  renderDecision(inc.status);
  updateIntel();
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
    showBanner('good','Report copied to the clipboard.');
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
       +choiceBtn('watch','Keep watching','Leave them in the decoys to gather intel. They only have fakes.')
       +choiceBtn('dismiss','Dismiss as false alarm','Mark benign and close.');
  }else if(s==='watching'){
    html='<span class="dnote">Observing. The intruder is left in the decoys.</span>'
       +choiceBtn('contain','Contain now','Lock the account and kill the session.')
       +choiceBtn('dismiss','Dismiss as false alarm','Mark benign and close.');
  }else if(s==='contained'){
    html=choiceBtn('restore','Restore real files','Threat stopped; return the real files.');
  }else if(s==='dismissed'){
    html='<span class="dnote">Closed as a false alarm.</span>';
  }else if(s==='restored'){
    html='<span class="dnote">Resolved. Real files restored.</span>';
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
  if(kind==='contain') return 'Contained. The attacker session is terminated and svc_backup is locked.';
  if(kind==='restore') return `Restored. ${decoys} real file(s) returned to their location, decoys removed.`;
  if(kind==='watch')   return 'Watching. The intruder is left in the decoys.';
  if(kind==='dismiss') return 'Dismissed. Incident closed as a false alarm.';
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
    showBanner('err','Action failed. The guard is unreachable.');
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
      // Same incident: keep UI state, just reflect any live status change and
      // refresh the "intelligence while observing" panel with fresh events.
      lastInc=inc;
      if((inc.status||'').toLowerCase()!==curStatus){ setStatus(inc.status); renderDecision(inc.status); }
      updateIntel();
      return;
    }
    const [card,summary]=await Promise.all([
      (await fetch(`/incidents/${inc.id}/card`)).json(),
      (await fetch(`/incidents/${inc.id}/summary`)).json(),
    ]);
    await loadCompare();
    curId=inc.id; approved=false; edited=false; editing=false; editText=null;
    render(inc,card,summary);
  }catch(e){/* core restarting; keep polling */}
}

// Demo helpers, only visible at /console?demo=1 so the jury never sees them.
if(/[?&]demo=1\b/.test(location.search)){
  const d=document.createElement('div'); d.className='demo';
  d.innerHTML='<button id="demoReset">Reset</button><select id="demoScn"><option value="ai">AI agent</option><option value="guided">Human guided by AI</option><option value="script">Fast script</option><option value="human">Human</option></select><button id="demoSeed">Load attack</button>';
  document.body.appendChild(d);
  document.getElementById('demoReset').onclick=async()=>{
    try{ await fetch('/admin/reset',{method:'POST'}); }catch(e){}
    tick();
  };
  document.getElementById('demoSeed').onclick=async()=>{
    try{ await fetch('/admin/reset',{method:'POST'}); }catch(e){}
    try{ await fetch('/admin/seed?scenario='+encodeURIComponent(document.getElementById('demoScn').value),{method:'POST'}); }catch(e){}
    tick();
  };
}
tick(); setInterval(tick,2000);
</script>
</body></html>
"""


@console_router.get("/console", response_class=HTMLResponse)
def console() -> str:
    return _PAGE
