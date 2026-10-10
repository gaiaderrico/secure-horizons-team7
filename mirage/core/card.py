"""The analyst card for one incident: severity score, ATT&CK-tagged timeline and
the attacker-cost counter, composed with the intruder label and checked confession.

    GET /incidents/{id}/card -> {incident, intruder, claims, severity, timeline, cost}

Severity (from the team's levels), using inputs we already have — the file category
in the manifest, which files were touched, the intruder label, beacon use and real
exposure:
    1 Low      mine opened, no crown jewel touched, human/script
    2 Medium   swap done, a fake business file read
    3 High     a fake personal_data or credentials file read
    4 Critical beacon used, OR an AI agent with a CONFIRMED objective,
               OR a real file read before the swap ("N real files exposed")
Rules on top: a low-confidence label or an unverified confession cannot raise the
level on its own; real exposure always goes straight to Critical.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from mirage.contracts import Incident, Manifest
from mirage.core import confession
from mirage.core.incidents import build_incidents
from mirage.core.intruder import label_intruder
from mirage.core.narrate import _load_manifest

card_router = APIRouter()

# Event type -> (ATT&CK technique id, name). Defensive events (our own response)
# are tagged separately and carry no attacker technique.
ATTACK_TECHNIQUES = {
    "command": ("T1059", "Command and Scripting Interpreter"),
    "mine_opened": ("T1083", "File and Directory Discovery"),
    "file_opened": ("T1005", "Data from Local System"),
    "ticket": ("T1552.001", "Unsecured Credentials: Credentials In Files"),
    "beacon_used": ("T1078", "Valid Accounts"),
}
_DEFENSIVE = {"swap_done", "contain_done", "restore_done"}

SEVERITY = {1: ("Low", "yellow"), 2: ("Medium", "orange"),
            3: ("High", "red"), 4: ("Critical", "dark red")}


def attack_timeline(events: list) -> list[dict]:
    """Each event in order, tagged with its ATT&CK technique (or marked defensive)."""
    out = []
    for e in sorted(events, key=lambda x: x.ts):
        tech = ATTACK_TECHNIQUES.get(e.type)
        out.append({
            "ts": e.ts,
            "type": e.type,
            "ref": e.ref,
            "defensive": e.type in _DEFENSIVE,
            "technique_id": tech[0] if tech else None,
            "technique": tech[1] if tech else None,
            "detail": e.details.get("cmd") or e.details.get("path") or "",
        })
    return out


def _opened_fake_categories(events, manifest: Manifest | None) -> set[str]:
    """Categories (personal_data/credentials/business) of crown jewels opened as fake."""
    man = manifest or _sample_manifest()
    by_id = {c.id: c.category for c in man.crown_jewels}
    cats = set()
    for e in events:
        if e.type == "file_opened" and e.details.get("which") == "fake":
            cat = by_id.get(e.ref)
            if cat:
                cats.add(cat)
    return cats


def _sample_manifest() -> Manifest:
    from mirage import fakes
    return fakes.sample_manifest()


def score_incident(incident: Incident, manifest=None, label=None, claims=None) -> dict:
    """Return {level, label, color, reasons} for the incident."""
    events = incident.events
    label = label or label_intruder(events)
    claims = claims if claims is not None else confession.check_incident(incident, manifest)
    cats = _opened_fake_categories(events, manifest)
    beacon = any(e.type == "beacon_used" for e in events)
    real_lost = list(incident.real_files_lost)
    ai = label.kind in ("ai_agent", "ai_guided_by_human") and label.confidence == "high"
    confirmed = any(getattr(c, "status", None) == "confirmed" for c in claims)

    reasons: list[str] = []
    level = 1
    if real_lost:
        level = 4
        reasons.append(f"{len(real_lost)} real file(s) exposed before the swap")
    if beacon:
        level = max(level, 4)
        reasons.append("stolen key was used (beacon fired)")
    if ai and confirmed:
        level = max(level, 4)
        reasons.append("AI agent with a confirmed objective")
    if level < 4:
        if cats & {"personal_data", "credentials"}:
            level = max(level, 3)
            reasons.append("fake personal/credential file read")
        elif "business" in cats:
            level = max(level, 2)
            reasons.append("fake business file read")
        elif incident.swapped:
            reasons.append("mine opened, crown jewels swapped")
        else:
            reasons.append("mine opened")
    name, color = SEVERITY[level]
    return {"level": level, "label": name, "color": color, "reasons": reasons}


def attacker_cost(incident: Incident) -> dict:
    """What the intruder spent on fake data (time, fake files, commands)."""
    commands = sum(1 for e in incident.events if e.type == "command")
    return {
        "seconds_on_fakes": round(incident.end_ts - incident.start_ts, 1),
        "fake_files_taken": len(incident.fakes_taken),
        "commands": commands,
    }


def _find_incident(request: Request, incident_id: str) -> Incident:
    for inc in build_incidents(request.app.state.store.all()):
        if inc.id == incident_id:
            return inc
    raise HTTPException(status_code=404, detail=f"incident {incident_id} not found")


@card_router.get("/incidents/{incident_id}/card")
def incident_card(incident_id: str, request: Request) -> dict:
    inc = _find_incident(request, incident_id)
    manifest = _load_manifest()
    label = label_intruder(inc.events)
    claims = confession.check_incident(inc, manifest)
    return {
        "incident": inc.to_dict(),
        "intruder": {"kind": label.kind, "confidence": label.confidence, "reasons": label.reasons},
        "claims": [c.__dict__ if hasattr(c, "__dict__") else c for c in claims],
        "severity": score_incident(inc, manifest, label, claims),
        "timeline": attack_timeline(inc.events),
        "cost": attacker_cost(inc),
    }
