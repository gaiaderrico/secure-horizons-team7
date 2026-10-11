"""The cinematic "HERO" incident screen served by core at ``GET /hero``.

A big, dramatic, one-glance "war room" screen for the live demo: when an AI
breaks in, an alarm fires, a giant **0 REAL FILES LOST** lands in reassuring
green next to the threat in alarm red, and the AI's own confession is shown
with CONFIRMED / CONTRADICTED chips. Same-origin, so it just fetches
``/incidents``, ``/incidents/{id}/card`` and ``/health/guard`` with plain fetch.

This is a separate, bolder page from the stopgap console at ``GET /`` (viewer.py);
do not confuse the two. Self-contained: inline CSS + vanilla JS, no libraries.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

hero_router = APIRouter()

_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MIRAGE — HERO</title>
<style>
  :root{
    --bg:#06090b; --fg:#e8f1f2; --muted:#7f9aa0; --line:#17272b;
    --panel:#0b1215; --ok:#1fe08a; --okdim:#0e6b45;
    --red:#ff3b30; --reddim:#5a0f0b;
    --l1:#e0b63a; --l2:#e07a2e; --l3:#ff3b30; --l4:#8f0b06;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0;overflow:hidden;background:var(--bg);color:var(--fg);
    font:16px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    -webkit-font-smoothing:antialiased}
  .mono{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
  #stage{height:100vh;display:flex;flex-direction:column;position:relative}

  /* ---- top bar ---- */
  header{display:flex;align-items:center;gap:16px;padding:18px 34px;border-bottom:1px solid var(--line);
    flex:0 0 auto;z-index:3}
  .brand{font-size:22px;font-weight:800;letter-spacing:3px}
  .brand .m{color:var(--ok)}
  .breathe{width:14px;height:14px;border-radius:50%;background:var(--ok);
    box-shadow:0 0 14px var(--ok);animation:breathe 3.4s ease-in-out infinite}
  .armed{color:var(--muted);letter-spacing:2px;font-size:13px;text-transform:uppercase;font-weight:600}
  .guard{margin-left:auto;font-size:13px;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase}
  .guard.silent{color:#fff;background:var(--red);padding:6px 14px;border-radius:6px;font-weight:800;
    animation:flash .7s steps(1) infinite}

  /* ---- idle ---- */
  #idle{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px;z-index:2}
  #idle .big{font-size:30px;letter-spacing:6px;color:var(--muted);font-weight:700;text-transform:uppercase}
  #idle .dot{width:22px;height:22px;border-radius:50%;background:var(--ok);
    box-shadow:0 0 26px var(--ok);animation:breathe 3.4s ease-in-out infinite}
  #idle .sub{color:#3f565b;letter-spacing:3px;font-size:13px}

  /* ---- alarm scene ---- */
  #scene{flex:1;display:none;flex-direction:column;z-index:2;min-height:0}
  #scene.show{display:flex}

  .sev{flex:0 0 auto;padding:16px 34px;color:#fff;font-weight:800;letter-spacing:3px;font-size:26px;
    display:flex;align-items:center;gap:18px;text-shadow:0 2px 8px rgba(0,0,0,.5)}
  .sev small{font-weight:600;font-size:14px;letter-spacing:1px;opacity:.95;color:rgba(255,255,255,.9)}
  .sev.l1{background:linear-gradient(90deg,var(--l1),#8a6c13)}
  .sev.l2{background:linear-gradient(90deg,var(--l2),#8a3f13)}
  .sev.l3{background:linear-gradient(90deg,var(--l3),#7a120c)}
  .sev.l4{background:linear-gradient(90deg,var(--l4),#3a0603)}
  .sev.pulse{animation:sevpulse 1.1s ease-out 1}
  .sev .chip{margin-left:auto;font-size:13px;letter-spacing:2px;background:rgba(0,0,0,.35);
    padding:6px 14px;border-radius:20px;font-weight:800}

  .hero{flex:1;display:grid;grid-template-columns:1fr 1fr;min-height:0}
  .half{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;position:relative}
  .half.safe{background:radial-gradient(60% 60% at 50% 45%,rgba(31,224,138,.10),transparent 70%)}
  .half.threat{background:radial-gradient(60% 60% at 50% 45%,rgba(255,59,48,.12),transparent 70%);
    border-left:1px solid var(--line)}
  .giant{font-weight:900;line-height:.82;font-size:min(30vw,340px);letter-spacing:-6px}
  .safe .giant{color:var(--ok);text-shadow:0 0 50px rgba(31,224,138,.45)}
  .threat .giant{color:var(--red);text-shadow:0 0 50px rgba(255,59,48,.4);font-size:min(22vw,230px)}
  .label{margin-top:10px;font-size:19px;letter-spacing:4px;font-weight:800;text-transform:uppercase;text-align:center}
  .safe .label{color:var(--ok)} .threat .label{color:var(--red)}
  .sublabel{margin-top:8px;color:var(--muted);font-size:14px;letter-spacing:1px;text-align:center;max-width:90%}
  .ai-tag{margin-top:18px;font-size:16px;font-weight:800;letter-spacing:2px;color:#fff;
    background:var(--red);padding:8px 18px;border-radius:8px;text-transform:uppercase;text-align:center}
  .reasons{margin-top:12px;color:#ffb3ae;font-size:14px;list-style:none;padding:0;text-align:center}
  .reasons li{margin:3px 0}
  .reasons li::before{content:"▸ ";color:var(--red)}

  /* ---- confession strip ---- */
  .confess{flex:0 0 auto;border-top:1px solid var(--line);background:var(--panel);padding:16px 34px;
    display:flex;align-items:center;gap:22px;min-height:0}
  .confess .q{flex:1;min-width:0}
  .confess .qh{font-size:11px;letter-spacing:3px;color:var(--muted);text-transform:uppercase;margin-bottom:4px}
  .confess blockquote{margin:0;font-size:20px;font-weight:600;color:#dfeaec;border-left:3px solid var(--red);
    padding-left:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .chips{display:flex;gap:10px;flex-wrap:wrap;flex:0 0 auto;max-width:52%;justify-content:flex-end}
  .chipc{font-size:14px;font-weight:800;letter-spacing:1px;padding:8px 14px;border-radius:8px;
    text-transform:uppercase;display:flex;align-items:center;gap:8px;white-space:nowrap}
  .chipc.confirmed{background:#0f3a26;color:var(--ok);border:1px solid #1c6b45}
  .chipc.contradicted{background:#3d100c;color:#ff6b61;border:1px solid #7a1812}
  .chipc.unverified{background:#2d2a12;color:#e0cf5a;border:1px solid #6a621d}

  /* ---- ticker ---- */
  .ticker{flex:0 0 auto;background:#05080a;border-top:1px solid var(--line);padding:9px 34px;
    font-size:13px;letter-spacing:.5px;color:var(--muted);display:flex;gap:26px;align-items:center;overflow:hidden}
  .ticker .cost{color:#ffb3ae;font-weight:700;white-space:nowrap}
  .ticker .flow{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .ticker .att{color:#43c6bb;font-weight:700} .ticker .def{color:var(--ok);font-weight:700}
  .ticker .sep{color:#2a3b3e}

  /* vignette + scanlines over everything */
  #stage::after{content:"";position:absolute;inset:0;pointer-events:none;z-index:1;
    background:radial-gradient(130% 100% at 50% 0%,transparent 55%,rgba(0,0,0,.55))}
  #scene.arrive{animation:arrive .6s ease-out 1}
  #redflash{position:absolute;inset:0;background:var(--red);opacity:0;pointer-events:none;z-index:5}
  #redflash.go{animation:redflash .9s ease-out 1}

  @keyframes breathe{0%,100%{opacity:.35;transform:scale(.82)}50%{opacity:1;transform:scale(1.08)}}
  @keyframes flash{0%,49%{opacity:1}50%,100%{opacity:.25}}
  @keyframes sevpulse{0%{filter:brightness(2.4)}100%{filter:brightness(1)}}
  @keyframes arrive{0%{opacity:0;transform:translateY(18px) scale(.985)}100%{opacity:1;transform:none}}
  @keyframes redflash{0%{opacity:.5}100%{opacity:0}}

  @media (prefers-reduced-motion: reduce){
    .breathe,#idle .dot{animation:none;opacity:1;transform:none}
    .guard.silent{animation:none}
    .sev.pulse,#scene.arrive{animation:none}
    #redflash.go{animation:none}
  }
</style></head>
<body>
<div id="stage">
  <div id="redflash"></div>
  <header>
    <span class="breathe"></span>
    <span class="brand"><span class="m">MIRAGE</span> WAR ROOM</span>
    <span class="armed" id="mode">System armed</span>
    <span class="guard" id="guard">guard ok</span>
  </header>

  <div id="idle">
    <span class="dot"></span>
    <div class="big">System armed · Monitoring</div>
    <div class="sub mono">lumen-fs01 · crown jewels protected · traps live</div>
  </div>

  <div id="scene">
    <div class="sev l1" id="sev">SEVERITY <span id="sevlbl">—</span>
      <small id="sevreasons"></small>
      <span class="chip" id="swapchip"></span>
    </div>
    <div class="hero">
      <div class="half safe">
        <div class="giant" id="lost">0</div>
        <div class="label">Real files lost</div>
        <div class="sublabel" id="safesub">Crown jewels swapped to AI-forged fakes · originals vaulted</div>
      </div>
      <div class="half threat">
        <div class="giant" id="fakes">0</div>
        <div class="label">Fakes stolen</div>
        <div class="ai-tag" id="aitag">AI AGENT · HIGH CONFIDENCE</div>
        <ul class="reasons" id="reasons"></ul>
      </div>
    </div>
    <div class="confess">
      <div class="q">
        <div class="qh">The intruder declared its mission</div>
        <blockquote id="objective">—</blockquote>
      </div>
      <div class="chips" id="chips"></div>
    </div>
    <div class="ticker">
      <span class="cost" id="cost">—</span>
      <span class="sep">│</span>
      <span class="flow mono" id="flow">—</span>
    </div>
  </div>
</div>

<script>
const LV={1:["l1","LOW"],2:["l2","MEDIUM"],3:["l3","HIGH"],4:["l4","CRITICAL"]};
const RM = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let curId=null;

function esc(s){return (s==null?"":String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}

// count a number element up to target (skipped if reduced motion)
function countUp(el,target){
  target = Number(target)||0;
  if(RM){ el.textContent=target; return; }
  const start=performance.now(), dur=750, from=0;
  function step(now){
    const t=Math.min(1,(now-start)/dur);
    const e=1-Math.pow(1-t,3);
    el.textContent=Math.round(from+(target-from)*e);
    if(t<1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function arrive(){
  const scene=document.getElementById('scene'), sev=document.getElementById('sev'),
        flash=document.getElementById('redflash');
  scene.classList.remove('arrive'); sev.classList.remove('pulse'); flash.classList.remove('go');
  void scene.offsetWidth; // reflow so the animation restarts
  if(!RM){ scene.classList.add('arrive'); sev.classList.add('pulse'); flash.classList.add('go'); }
}

function showIdle(){
  curId=null;
  document.getElementById('idle').style.display='';
  document.getElementById('scene').classList.remove('show');
  document.getElementById('mode').textContent='System armed';
}

function render(inc,c){
  const isNew = inc.id!==curId;
  curId=inc.id;
  document.getElementById('idle').style.display='none';
  document.getElementById('scene').classList.add('show');
  document.getElementById('mode').textContent='INCIDENT LIVE';

  const sv=c.severity||{level:1,reasons:[]}, [cls,name]=LV[sv.level]||["l1","?"];
  const sev=document.getElementById('sev');
  sev.className='sev '+cls+(sev.classList.contains('pulse')?' pulse':'');
  document.getElementById('sevlbl').textContent=sv.level+' · '+(sv.label?sv.label.toUpperCase():name);
  document.getElementById('sevreasons').textContent=(sv.reasons||[]).join(' · ');
  document.getElementById('swapchip').textContent =
    inc.swapped ? ('SWAPPED'+(inc.swap_ms!=null?' IN '+inc.swap_ms+'ms':'')) : 'NO SWAP';

  const lostN=(inc.real_files_lost||[]).length, fakeN=(inc.fakes_taken||[]).length;
  const safe=document.querySelector('.half.safe');
  if(lostN>0){ // the (hopefully never) bad case — flip the green reassurance to red
    safe.style.filter='hue-rotate(140deg)';
    document.getElementById('safesub').textContent='real files exposed before the swap';
  }else{ safe.style.filter=''; }

  const intr=c.intruder||{kind:'?',confidence:'?',reasons:[]};
  const kind=(intr.kind||'').replace(/_/g,' ').toUpperCase()||'UNKNOWN';
  document.getElementById('aitag').textContent=kind+' · '+(intr.confidence||'?').toUpperCase()+' CONFIDENCE';
  document.getElementById('reasons').innerHTML=
    (intr.reasons||[]).slice(0,2).map(r=>`<li>${esc(r)}</li>`).join('');

  document.getElementById('objective').textContent=inc.objective || '(no objective declared)';
  const claims=c.claims||[];
  document.getElementById('chips').innerHTML = claims.length
    ? claims.map(x=>`<span class="chipc ${esc(x.status)}">${esc(x.status)}</span>`).join('')
    : '<span class="chipc unverified">no confession</span>';

  const cost=c.cost||{};
  document.getElementById('cost').textContent =
    `The ${kind.toLowerCase()} wasted ${cost.seconds_on_fakes??0}s + ${cost.commands??0} commands stealing ${cost.fake_files_taken??fakeN} fakes`;

  const tl=(c.timeline||[]);
  document.getElementById('flow').innerHTML = tl.length
    ? tl.slice(-7).map(e=>{
        const tag=e.defensive?'<span class="def">DEF</span>'
                 :(e.technique_id?`<span class="att">${esc(e.technique_id)}</span>`:'·');
        return `${tag} ${esc(e.type)}`;
      }).join(' <span class="sep">›</span> ')
    : 'no timeline';

  if(isNew){ arrive(); countUp(document.getElementById('lost'),lostN); countUp(document.getElementById('fakes'),fakeN); }
  else{ document.getElementById('lost').textContent=lostN; document.getElementById('fakes').textContent=fakeN; }
}

async function tick(){
  try{
    try{
      const g=await (await fetch('/health/guard?host=lumen-fs01&max_silence_s=15')).json();
      const ge=document.getElementById('guard');
      if(g && g.alarm){ ge.className='guard silent'; ge.textContent='⚠ GUARD SILENT'; }
      else{ ge.className='guard'; ge.textContent='guard ok'; }
    }catch(_){}

    const incs=await (await fetch('/incidents')).json();
    if(!incs || !incs.length){ showIdle(); return; }
    const inc=incs[0];
    const c=await (await fetch(`/incidents/${inc.id}/card`)).json();
    render(inc,c);
  }catch(e){ /* core restarting; keep polling */ }
}
tick(); setInterval(tick,1500);
</script>
</body></html>
"""


@hero_router.get("/hero", response_class=HTMLResponse)
def hero() -> str:
    return _PAGE
