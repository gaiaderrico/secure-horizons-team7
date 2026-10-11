"""A clean "analyst incident report" page served by core at ``GET /report``.

Same-origin, so plain ``fetch`` reaches the API with no CORS setup. It polls
``/incidents`` every 2s and, for the newest incident, renders the AI narrator's
report (``/incidents/{id}/summary``) as a serious, printable SOC document:
a severity header band from ``/incidents/{id}/card``, the AI DRAFT summary with
its markdown rendered to HTML, a collapsible NIS2 early-warning draft, and a
cosmetic "Approve draft" button. This is OPTION A of the demo bake-off; the
stopgap console at ``GET /`` (viewer.py) and the hero card (option B) are separate.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

report_router = APIRouter()

_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MIRAGE Incident Report</title>
<style>
  :root{
    --page:#eef0f2; --paper:#ffffff; --ink:#1b2023; --muted:#5e6a70;
    --line:#dfe3e6; --faint:#f4f6f7; --accent:#1f6f6a;
    --l1:#b7960f; --l2:#c76b16; --l3:#b3261e; --l4:#7a0f0a;
    --ok:#2f7a4a; --bad:#b3261e;
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{background:var(--page);color:var(--ink);
    font:16px/1.65 Georgia,"Times New Roman",'Noto Serif',serif;
    -webkit-font-smoothing:antialiased;padding:28px 16px 80px}
  .sans{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
  .paper{max-width:820px;margin:0 auto;background:var(--paper);
    border:1px solid var(--line);border-radius:4px;
    box-shadow:0 1px 3px rgba(0,0,0,.06),0 12px 40px rgba(0,0,0,.06)}
  /* ---- masthead ---- */
  .mast{display:flex;align-items:center;gap:12px;padding:20px 40px;
    border-bottom:2px solid var(--ink)}
  .mast .brand{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-weight:800;letter-spacing:3px;font-size:15px}
  .mast .sub{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    color:var(--muted);font-size:12px;letter-spacing:1px;text-transform:uppercase}
  .guard{margin-left:auto;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size:12px;color:var(--muted);display:flex;align-items:center;gap:7px}
  .guard .dot{width:9px;height:9px;border-radius:50%;background:var(--ok)}
  .guard.silent{color:var(--bad)} .guard.silent .dot{background:var(--bad);box-shadow:0 0 7px var(--bad)}
  /* ---- severity band ---- */
  .band{color:#fff;padding:16px 40px;display:flex;align-items:center;gap:18px;flex-wrap:wrap}
  .band.l1{background:var(--l1)} .band.l2{background:var(--l2)}
  .band.l3{background:var(--l3)} .band.l4{background:var(--l4)}
  .band .lvl{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-weight:800;letter-spacing:1px;font-size:20px;text-transform:uppercase}
  .band .lvl small{display:block;font-weight:500;font-size:12px;letter-spacing:.5px;
    opacity:.92;text-transform:none;margin-top:2px;max-width:420px}
  .band .lost{margin-left:auto;text-align:right;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
  .band .lost b{display:block;font-size:30px;line-height:1;font-weight:800}
  .band .lost span{font-size:11px;letter-spacing:1px;text-transform:uppercase;opacity:.92}
  /* ---- fact strip ---- */
  .facts{display:flex;flex-wrap:wrap;gap:0;border-bottom:1px solid var(--line);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
  .facts .f{flex:1;min-width:150px;padding:14px 40px;border-right:1px solid var(--line)}
  .facts .f:last-child{border-right:0}
  .facts .k{font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:var(--muted)}
  .facts .v{font-size:16px;font-weight:700;margin-top:3px}
  /* ---- body ---- */
  .doc{padding:30px 40px 38px}
  .ribbon{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    display:inline-flex;align-items:center;gap:8px;background:var(--faint);
    border:1px dashed #c3ac5a;color:#7a640f;border-radius:3px;
    padding:7px 13px;font-size:12px;letter-spacing:.5px;margin-bottom:22px}
  .ribbon.approved{border-style:solid;border-color:var(--ok);background:#eef7f0;color:var(--ok)}
  .ribbon b{font-weight:800;letter-spacing:1px}
  .doc h1{font-size:25px;line-height:1.25;margin:.2em 0 .5em;font-weight:700}
  .doc h2{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size:14px;letter-spacing:.6px;text-transform:uppercase;color:var(--accent);
    margin:1.6em 0 .5em;padding-bottom:5px;border-bottom:1px solid var(--line)}
  .doc p{margin:.7em 0}
  .doc ul{margin:.6em 0;padding-left:1.3em}
  .doc li{margin:.25em 0}
  .doc strong{font-weight:700}
  /* ---- actions ---- */
  .actions{display:flex;gap:12px;align-items:center;flex-wrap:wrap;
    margin-top:28px;padding-top:20px;border-top:1px solid var(--line)}
  button.act{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size:14px;font-weight:600;padding:11px 20px;border-radius:6px;
    border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
  button.act:hover{filter:brightness(1.07)}
  button.act[disabled]{background:#eef7f0;color:var(--ok);border-color:var(--ok);cursor:default;filter:none}
  .sig{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size:12px;color:var(--muted);margin-left:auto}
  /* ---- NIS2 disclosure ---- */
  details.nis2{margin-top:26px;border:1px solid var(--line);border-radius:6px;overflow:hidden}
  details.nis2>summary{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    cursor:pointer;list-style:none;padding:14px 20px;background:var(--faint);
    font-size:13px;letter-spacing:.5px;text-transform:uppercase;color:var(--accent);
    font-weight:700;display:flex;align-items:center;gap:10px}
  details.nis2>summary::-webkit-details-marker{display:none}
  details.nis2>summary::before{content:"\25B8";transition:transform .15s}
  details.nis2[open]>summary::before{transform:rotate(90deg)}
  details.nis2 .inner{padding:8px 24px 22px}
  /* ---- idle ---- */
  .idle{padding:90px 40px;text-align:center}
  .idle .pulse{width:14px;height:14px;border-radius:50%;background:var(--ok);margin:0 auto 18px;
    animation:pulse 2s infinite}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(47,122,74,.5)}
    70%{box-shadow:0 0 0 14px rgba(47,122,74,0)}100%{box-shadow:0 0 0 0 rgba(47,122,74,0)}}
  .idle h2{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size:19px;margin:0 0 6px;color:var(--ink);border:0;text-transform:none;letter-spacing:0}
  .idle p{color:var(--muted);margin:0}
  .foot{max-width:820px;margin:16px auto 0;text-align:center;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:11px;color:var(--muted)}
  @media (max-width:560px){
    .mast,.band,.doc,.facts .f{padding-left:20px;padding-right:20px}
    .band .lost{margin-left:0;text-align:left}
  }
</style></head>
<body>
<div class="paper" id="paper">
  <div class="mast">
    <div>
      <div class="brand">MIRAGE</div>
      <div class="sub">Security Operations &middot; Incident Report</div>
    </div>
    <div class="guard" id="guard"><span class="dot"></span><span id="guardtxt">guard ok</span></div>
  </div>
  <div id="main">
    <div class="idle">
      <div class="pulse"></div>
      <h2>No active incident</h2>
      <p>System monitoring. This report will populate automatically when a mine is opened.</p>
    </div>
  </div>
</div>
<div class="foot">MIRAGE &mdash; drafts are AI-generated and require analyst approval. Nothing is sent automatically.</div>

<script>
const LV={1:["l1","Low"],2:["l2","Medium"],3:["l3","High"],4:["l4","Critical"]};
let curId=null;         // incident currently rendered
let approved=false;     // cosmetic approval, reset per new incident

function esc(s){return (s==null?"":String(s)).replace(/[&<>"]/g,c=>(
  {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

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
  return String(src||"").replace(/^\s*AI DRAFT[^\n]*\n?/,'').replace(/^\s+/,'');
}

function renderIdle(){
  curId=null;
  document.getElementById('main').innerHTML=
    '<div class="idle"><div class="pulse"></div>'+
    '<h2>No active incident</h2>'+
    '<p>System monitoring. This report will populate automatically when a mine is opened.</p></div>';
}

function render(inc,card,summary){
  const sv=card.severity||{level:1,label:"Low",reasons:[]};
  const [cls,name]=LV[sv.level]||["l1","Low"];
  const intr=card.intruder||{kind:"unknown",confidence:"low"};
  const kindName=({ai_agent:"AI agent",ai_guided_by_human:"AI agent (human-guided)",
    script:"Automated script",human:"Human operator"})[intr.kind]||esc(intr.kind);
  const lost=(inc.real_files_lost||[]).length;
  const cost=card.cost||{};
  const body=md(stripBanner(summary.summary));
  const nis2=md(stripBanner(summary.nis2));
  const ribbon=approved
    ? '<div class="ribbon approved"><b>APPROVED</b> Reviewed and signed off by analyst (demo).</div>'
    : '<div class="ribbon"><b>AI DRAFT</b> Pending analyst approval &mdash; not sent.</div>';

  document.getElementById('main').innerHTML=`
    <div class="band ${cls}">
      <div class="lvl">${name} severity<small>${esc((sv.reasons||[]).join(' · '))}</small></div>
      <div class="lost"><b>${lost}</b><span>real files lost</span></div>
    </div>
    <div class="facts">
      <div class="f"><div class="k">Intruder</div><div class="v">${kindName}</div>
        <div class="k">${esc(intr.confidence)} confidence</div></div>
      <div class="f"><div class="k">Decoy files taken</div><div class="v">${(inc.fakes_taken||[]).length}</div></div>
      <div class="f"><div class="k">Swap time</div><div class="v">${inc.swap_ms!=null?esc(inc.swap_ms)+' ms':'–'}</div></div>
      <div class="f"><div class="k">Time on decoys</div><div class="v">${cost.seconds_on_fakes!=null?esc(cost.seconds_on_fakes)+' s':'–'}</div></div>
    </div>
    <div class="doc">
      ${ribbon}
      <div class="rendered">${body}</div>
      <details class="nis2">
        <summary>NIS2 early-warning draft (Article 23)</summary>
        <div class="inner">${nis2}</div>
      </details>
      <div class="actions">
        <button class="act" id="approve" ${approved?'disabled':''}>${approved?'✓ Draft approved':'Approve draft'}</button>
        <span class="sig">Incident ${esc(inc.id)} &middot; status: ${esc(inc.status)}</span>
      </div>
    </div>`;
  const btn=document.getElementById('approve');
  if(btn) btn.onclick=()=>{ approved=true; if(curId) render(inc,card,summary); };
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
    if(inc.id===curId) return;              // same incident: keep UI state (approval, open NIS2)
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


@report_router.get("/report", response_class=HTMLResponse)
def report() -> str:
    return _PAGE
