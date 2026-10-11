"""A minimal built-in SOC console served by core at ``GET /``.

Same-origin so the browser can call the API with no CORS setup. It polls
``/incidents`` + ``/incidents/{id}/card`` every 2s and renders the latest
incident: a coloured severity badge, who the intruder is, the checked
confession, the ATT&CK timeline, "0 real files lost" and Contain/Restore.
This is a stopgap viewer for the demo; the full dashboard is P5's (Ana).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

viewer_router = APIRouter()

_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MIRAGE SOC console</title>
<style>
  :root{--bg:#0f1617;--card:#172122;--line:#2a3a3c;--fg:#e2ecec;--muted:#94a9ab;
        --ok:#2f7a4a;--l1:#c9a227;--l2:#c76b16;--l3:#b3261e;--l4:#7a0f0a}
  *{box-sizing:border-box}
  body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--fg)}
  header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px}
  header h1{font-size:18px;margin:0;letter-spacing:.5px}
  .dot{width:12px;height:12px;border-radius:50%;background:var(--ok)}
  .dot.alert{background:var(--l3);box-shadow:0 0 10px var(--l3)}
  main{max-width:760px;margin:0 auto;padding:20px}
  .idle{color:var(--muted);text-align:center;padding:60px 20px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:0;overflow:hidden;margin-bottom:16px}
  .sev{padding:14px 18px;font-weight:700;font-size:17px;letter-spacing:.5px;color:#fff}
  .sev small{display:block;font-weight:400;font-size:13px;opacity:.9;margin-top:4px}
  .sev.l1{background:var(--l1)} .sev.l2{background:var(--l2)} .sev.l3{background:var(--l3)} .sev.l4{background:var(--l4)}
  .body{padding:16px 18px}
  .row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
  .stat{background:#0f1617;border:1px solid var(--line);border-radius:8px;padding:8px 12px;flex:1;min-width:120px}
  .stat b{display:block;font-size:20px} .stat span{color:var(--muted);font-size:12px}
  .stat.good b{color:#6cc28c}
  h3{font-size:13px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin:16px 0 8px}
  .who b{font-size:15px}
  .reasons{color:var(--muted);font-size:13px;margin:4px 0 0;padding-left:18px}
  .claim{display:flex;gap:8px;align-items:center;padding:5px 0;border-bottom:1px solid var(--line)}
  .tag{font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;text-transform:uppercase}
  .tag.confirmed{background:#163b25;color:#6cc28c} .tag.contradicted{background:#3b1513;color:#f07a70}
  .tag.unverified{background:#2a2a1a;color:#d6c15a}
  .tl{font:12px/1.5 ui-monospace,Menlo,monospace;color:var(--muted);max-height:200px;overflow:auto}
  .tl .att{color:#45c2b8} .tl .def{color:#6cc28c}
  .btns{display:flex;gap:10px;margin-top:16px}
  button{flex:1;padding:12px;border:0;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;color:#fff}
  .contain{background:#b3261e} .restore{background:#0d6e69}
  .st{font-size:12px;color:var(--muted);margin-top:10px}
</style></head>
<body>
<header><span class="dot" id="dot"></span><h1>MIRAGE — SOC console</h1>
  <span id="guard" class="st" style="margin-left:auto"></span></header>
<main id="main"><div class="idle">No incident. Monitoring…</div></main>
<script>
const LV={1:["l1","LOW"],2:["l2","MEDIUM"],3:["l3","HIGH"],4:["l4","CRITICAL"]};
let curId=null;
function esc(s){return (s||"").replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function act(path){ if(!curId)return; await fetch(`/incidents/${curId}/${path}`,{method:'POST'}); tick(); }
async function tick(){
  try{
    const g=await (await fetch('/health/guard?host=lumen-fs01&max_silence_s=15')).json();
    document.getElementById('guard').textContent = g.alarm ? '⚠ GUARD SILENT' : 'guard ok';
    const incs=await (await fetch('/incidents')).json();
    const dot=document.getElementById('dot'), main=document.getElementById('main');
    if(!incs.length){ dot.className='dot'; curId=null; main.innerHTML='<div class="idle">No incident. Monitoring…</div>'; return; }
    const inc=incs[0]; curId=inc.id; dot.className='dot alert';
    const c=await (await fetch(`/incidents/${inc.id}/card`)).json();
    const sv=c.severity, [cls,name]=LV[sv.level]||["l1","?"];
    const claims=(c.claims||[]).map(x=>`<div class="claim"><span class="tag ${x.status}">${x.status}</span>${esc(x.text)}</div>`).join('')||'<div class="st">no confession</div>';
    const tl=(c.timeline||[]).map(e=>{const t=e.defensive?`<span class="def">DEFENCE</span>`:(e.technique_id?`<span class="att">${e.technique_id}</span>`:'·');return `${t} ${esc(e.type)} ${esc((e.detail||'').slice(0,46))}`}).join('<br>');
    main.innerHTML=`<div class="card">
      <div class="sev ${cls}">SEVERITY ${sv.level} · ${name}<small>${esc((sv.reasons||[]).join(' · '))}</small></div>
      <div class="body">
        <div class="row">
          <div class="stat good"><b>${inc.real_files_lost.length}</b><span>real files lost</span></div>
          <div class="stat"><b>${inc.fakes_taken.length}</b><span>fakes taken</span></div>
          <div class="stat"><b>${inc.swap_ms??'–'} ms</b><span>swap time</span></div>
          <div class="stat"><b>${c.cost.seconds_on_fakes}s</b><span>wasted on fakes</span></div>
        </div>
        <div class="who"><h3>Intruder</h3><b>${esc(c.intruder.kind)}</b> · ${esc(c.intruder.confidence)} confidence
          <ul class="reasons">${(c.intruder.reasons||[]).map(r=>`<li>${esc(r)}</li>`).join('')}</ul></div>
        <h3>Confession (checked vs logs)</h3>${claims}
        <h3>Timeline · ATT&CK</h3><div class="tl">${tl}</div>
        <div class="btns"><button class="contain" onclick="act('contain')">Contain</button>
          <button class="restore" onclick="act('restore')">Restore</button></div>
        <div class="st">status: ${esc(inc.status)} · ${esc(inc.id)}</div>
      </div></div>`;
  }catch(e){ /* core restarting; keep polling */ }
}
tick(); setInterval(tick,2000);
</script></body></html>
"""


@viewer_router.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return _PAGE
