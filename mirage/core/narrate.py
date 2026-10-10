"""Expose the AI narrator on core: the analyst's incident summary + NIS2 draft.

This is the "after the attack" AI helper from the plan (role 3): it reads the
incident and drafts text for the analyst to approve. It never acts and nothing is
sent. Facts come from the incident; with MIRAGE_LLM set the model only polishes
the wording (and its text is dropped if it loses a fact).

    GET /incidents/{id}/summary          -> {"summary": md, "nis2": md}
    GET /incidents/{id}/summary?polish=1 -> same, but let the LLM reword it

Before drafting we enrich the incident with the intruder label and the checked
confession, so the draft reflects who it was and what was verified.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request

from mirage.contracts import MANIFEST_PATH, Manifest
from mirage.core import confession, narrator
from mirage.core.incidents import build_incidents
from mirage.core.intruder import label_intruder

narrate_router = APIRouter()


def _load_manifest() -> Manifest | None:
    """Best-effort manifest load (for cj-id -> file path in the draft). Never raises."""
    for path in (os.environ.get("MIRAGE_MANIFEST"), "generated/manifest.json", MANIFEST_PATH):
        if not path:
            continue
        try:
            return Manifest.load(path)
        except (OSError, ValueError):
            continue
    return None


def _find_incident(request: Request, incident_id: str):
    store = request.app.state.store
    for inc in build_incidents(store.all()):
        if inc.id == incident_id:
            return inc
    raise HTTPException(status_code=404, detail=f"incident {incident_id} not found")


@narrate_router.get("/incidents/{incident_id}/summary")
def incident_summary(incident_id: str, request: Request, polish: bool = False) -> dict:
    inc = _find_incident(request, incident_id)
    manifest = _load_manifest()
    # Enrich so the draft names the intruder and the verified claims.
    inc.intruder = label_intruder(inc.events)
    inc.claims = confession.check_incident(inc, manifest=manifest)
    return {
        "summary": narrator.summarize_incident(inc, manifest, use_llm=polish),
        "nis2": narrator.nis2_early_warning(inc, manifest, use_llm=polish),
    }
