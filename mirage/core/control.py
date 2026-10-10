"""Contain / Restore endpoints: the analyst's two buttons.

The dashboard POSTs here; core calls the guard's control API (contain = lock the
attacker account + kill the session, restore = swap the real files back), then
records a ``contain_done`` / ``restore_done`` event so the incident status flips.

The guard is reached through an injectable client on ``app.state.guard`` so tests
stay offline (they replace it with a fake). There is also a dev/offline mode for
the demo without the victim container - see ``GuardClient`` below.

Only new code lives here; api.py just registers ``control_router`` and puts a
default ``GuardClient`` on ``app.state.guard``.
"""

from __future__ import annotations

import os

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from mirage.contracts import ATTACK_USER, GUARD_CONTROL_URL, Event
from mirage.core.incidents import build_incidents

# contain_done / restore_done carry the analyst's name; everything else is attacker.
_ANALYST_EVENT_TYPES = frozenset({"contain_done", "restore_done"})


# --- pure helpers (unit-tested directly) -------------------------------------


def _attacker_user(events: list[Event]) -> str:
    """The account the attacker logged in with, read off the incident's events.

    First non-empty ``user`` on an attacker event (everything except our own
    contain/restore records); falls back to ``ATTACK_USER`` when none is set.
    """
    for e in events:
        if e.type in _ANALYST_EVENT_TYPES:
            continue
        if e.user:
            return e.user
    return ATTACK_USER


def _restored_files(incident) -> list[str]:
    """Crown-jewel ids that were swapped, taken from the incident's swap_done event."""
    for e in incident.events:
        if e.type == "swap_done":
            files = e.details.get("files", [])
            return list(files) if files else []
    return []


# --- injectable guard client -------------------------------------------------


def _guard_offline() -> bool:
    """Dev/offline mode: skip the real HTTP call so the demo works with no victim.

    True when ``MIRAGE_GUARD_DISABLED`` is set, OR when no ``GUARD_TOKEN`` is
    configured AND ``MIRAGE_GUARD_OPTIONAL=1``. Read at call time so tests (and
    the demo) can toggle it via the environment.
    """
    if os.environ.get("MIRAGE_GUARD_DISABLED"):
        return True
    if not os.environ.get("GUARD_TOKEN") and os.environ.get("MIRAGE_GUARD_OPTIONAL") == "1":
        return True
    return False


class GuardClient:
    """POSTs to the guard's control API with the shared token header.

    ``.contain(payload)`` / ``.restore(payload)`` each return ``(ok, detail)``.
    In offline/dev mode (see ``_guard_offline``) the HTTP call is skipped and the
    methods return ``(True, "guard disabled (dev)")``. Default behaviour, with a
    ``GUARD_TOKEN`` set and no disable flag, really calls the guard.
    """

    def __init__(self, base_url: str = GUARD_CONTROL_URL, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def token(self) -> str:
        return os.environ.get("GUARD_TOKEN", "")

    def _post(self, path: str, payload: dict) -> tuple[bool, str]:
        if _guard_offline():
            return True, "guard disabled (dev)"
        url = f"{self.base_url}{path}"
        try:
            resp = requests.post(url, json=payload, headers={"X-Guard-Token": self.token},
                                 timeout=self.timeout)
        except requests.RequestException as exc:
            return False, f"guard unreachable at {url}: {exc}"
        if not (200 <= resp.status_code < 300):
            return False, f"guard returned {resp.status_code}: {resp.text[:200]}"
        return True, resp.text[:200]

    def contain(self, payload: dict) -> tuple[bool, str]:
        return self._post("/contain", payload)

    def restore(self, payload: dict) -> tuple[bool, str]:
        return self._post("/restore", payload)


# --- endpoints ---------------------------------------------------------------

control_router = APIRouter()


class ActionIn(BaseModel):
    """Optional request body; the analyst performing the action."""

    user: str = "analyst"


def _find_incident(request: Request, incident_id: str):
    store = request.app.state.store
    for inc in build_incidents(store.all()):
        if inc.id == incident_id:
            return inc
    raise HTTPException(status_code=404, detail=f"incident {incident_id} not found")


def _refresh(request: Request, incident_id: str) -> dict:
    """Recompute incidents and return the one with this id (with its new status)."""
    store = request.app.state.store
    for inc in build_incidents(store.all()):
        if inc.id == incident_id:
            return inc.to_dict()
    raise HTTPException(status_code=404, detail=f"incident {incident_id} not found")


@control_router.post("/incidents/{incident_id}/contain")
def contain(incident_id: str, request: Request, body: ActionIn | None = None) -> dict:
    analyst = (body or ActionIn()).user
    incident = _find_incident(request, incident_id)
    attacker = _attacker_user(incident.events)

    ok, detail = request.app.state.guard.contain(
        {"user": attacker, "incident": incident_id, "by": analyst})
    if not ok:
        raise HTTPException(status_code=502, detail=f"guard contain failed: {detail}")

    request.app.state.store.add(Event(
        ts=Event.now(), type="contain_done", host=incident.host, user=analyst,
        details={"user": attacker, "by": analyst}))
    return _refresh(request, incident_id)


@control_router.post("/incidents/{incident_id}/restore")
def restore(incident_id: str, request: Request, body: ActionIn | None = None) -> dict:
    analyst = (body or ActionIn()).user
    incident = _find_incident(request, incident_id)
    files = _restored_files(incident)
    attacker = _attacker_user(incident.events)

    ok, detail = request.app.state.guard.restore(
        {"user": attacker, "incident": incident_id, "by": analyst})
    if not ok:
        raise HTTPException(status_code=502, detail=f"guard restore failed: {detail}")

    request.app.state.store.add(Event(
        ts=Event.now(), type="restore_done", host=incident.host, user=analyst,
        details={"files": files, "by": analyst}))
    return _refresh(request, incident_id)
