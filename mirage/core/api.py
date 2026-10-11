"""Core HTTP API: receives events from the guard, serves incidents to the dashboard.

Run from the repo root:  uvicorn mirage.core.api:app --port 8000
Env: MIRAGE_DB (default generated/core.db), MIRAGE_SEED (ai|guided|script|human, seeds an empty DB).

Each area is its own APIRouter; the honey API (/tickets, /auth) gets its own router too.
Routes reach the EventStore through `request.app.state.store`.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from mirage import fakes
from mirage.contracts import HOST, Event, EventType
from mirage.core.control import GuardClient, control_router
from mirage.core.db import EventStore
from mirage.core.card import card_router
from mirage.core.heartbeat import heartbeat_router
from mirage.core.honey import honey_router
from mirage.core.narrate import narrate_router
from mirage.core.report_page import report_router
from mirage.core.viewer import viewer_router
from mirage.core.hero_page import hero_router
from mirage.core.incidents import build_incidents

DEFAULT_DB = "generated/core.db"

SCENARIOS = {
    "ai": fakes.ai_attack_events,
    "guided": fakes.guided_ai_attack_events,
    "script": fakes.script_attack_events,
    "human": fakes.human_attack_events,
}


class EventIn(BaseModel):
    """Mirror of contracts.Event for request validation (bad `type` -> 422)."""

    ts: float
    type: EventType
    host: str = HOST
    user: str = ""
    ref: str = ""
    details: dict[str, Any] = Field(default_factory=dict)

    def to_event(self) -> Event:
        return Event(self.ts, self.type, self.host, self.user, self.ref, self.details)


def get_store(request: Request) -> EventStore:
    return request.app.state.store


def seed_store(store: EventStore, scenario: str) -> list[int]:
    """Load a fakes.* attack scenario, anchored to ~now so the incident is 'recent'
    and the analyst's Contain/Restore (stamped now) groups with it. Raises KeyError
    for unknown names."""
    import time
    events = SCENARIOS[scenario](time.time() - 300)
    return store.add_many(events)


# --- /health -----------------------------------------------------------------

health_router = APIRouter()


@health_router.get("/health")
def health() -> dict:
    return {"ok": True}


# --- /events -----------------------------------------------------------------

events_router = APIRouter()


@events_router.post("/events")
def post_events(body: EventIn | list[EventIn], request: Request) -> dict:
    items = body if isinstance(body, list) else [body]
    ids = get_store(request).add_many([e.to_event() for e in items])
    return {"ok": True, "ids": ids}


@events_router.get("/events")
def get_events(request: Request, since: float | None = None, type: str | None = None) -> list[dict]:
    return [e.to_dict() for e in get_store(request).all(since=since, type=type)]


# --- /incidents --------------------------------------------------------------

incidents_router = APIRouter()


@incidents_router.get("/incidents")
def get_incidents(request: Request) -> list[dict]:
    return [inc.to_dict() for inc in build_incidents(get_store(request).all())]


@incidents_router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, request: Request) -> dict:
    for inc in build_incidents(get_store(request).all()):
        if inc.id == incident_id:
            return inc.to_dict()
    raise HTTPException(status_code=404, detail=f"incident {incident_id} not found")


# --- /admin ------------------------------------------------------------------

admin_router = APIRouter(prefix="/admin")


@admin_router.post("/reset")
def admin_reset(request: Request) -> dict:
    get_store(request).reset()
    return {"ok": True}


@admin_router.post("/seed")
def admin_seed(request: Request, scenario: str = "ai") -> dict:
    if scenario not in SCENARIOS:
        raise HTTPException(status_code=400,
                            detail=f"unknown scenario {scenario!r}, use one of {sorted(SCENARIOS)}")
    return {"ok": True, "scenario": scenario, "ids": seed_store(get_store(request), scenario)}


# --- app factory -------------------------------------------------------------


def create_app(db_path: str | None = None, seed: str | None = None) -> FastAPI:
    """Build the app. db_path/seed default to env MIRAGE_DB / MIRAGE_SEED."""
    db_path = db_path or os.environ.get("MIRAGE_DB", DEFAULT_DB)
    seed = seed if seed is not None else os.environ.get("MIRAGE_SEED") or None
    if seed is not None and seed not in SCENARIOS:
        raise ValueError(f"unknown MIRAGE_SEED {seed!r}, use one of {sorted(SCENARIOS)}")

    store = EventStore(db_path)
    if seed and store.count() == 0:
        seed_store(store, seed)

    app = FastAPI(title="MIRAGE core")
    app.state.store = store
    app.state.guard = GuardClient()
    app.state.heartbeats = {}
    for router in (health_router, events_router, incidents_router, admin_router,
                   honey_router, control_router, narrate_router, card_router,
                   heartbeat_router, viewer_router, report_router, hero_router):
        app.include_router(router)
    return app


app = create_app()
