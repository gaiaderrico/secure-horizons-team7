"""Guard heartbeat: the guard pings core; the dashboard shows "GUARD SILENT" if it stops.

This answers "what if the attacker kills the guard?". The guard POSTs ``/heartbeat``
every few seconds; core remembers the last-seen wall-clock ts per host on
``app.state.heartbeats`` and ``/health/guard`` turns that into an alarm when the guard
goes quiet (killed, crashed or network cut). It is deliberately NOT a contracts.Event
(no new Event type) -- it is a liveness ping, not something that happened on the share.

The pure helper ``guard_health`` holds the decision so it is unit-tested without HTTP.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

from mirage.contracts import HOST

heartbeat_router = APIRouter()

DEFAULT_MAX_SILENCE_S = 15.0


def guard_health(last_seen: float | None, now: float, max_silence_s: float) -> dict:
    """Pure: last-seen wall-clock ts (or None if never) -> health dict.

    ``alarm`` is True when no heartbeat ever arrived OR the last one is older than
    ``max_silence_s``. ``alive`` is simply ``not alarm``.
    """
    if last_seen is None:
        return {"alive": False, "last_seen": None, "silent_for_s": None, "alarm": True}
    silent = max(0.0, now - last_seen)
    alarm = silent > max_silence_s
    return {"alive": not alarm, "last_seen": last_seen,
            "silent_for_s": round(silent, 3), "alarm": alarm}


class HeartbeatIn(BaseModel):
    """Lenient body: ``host`` defaults to HOST, ``ts`` to 0.0 (meaning "stamp it now")."""

    host: str = HOST
    ts: float = 0.0


@heartbeat_router.post("/heartbeat")
def post_heartbeat(body: HeartbeatIn, request: Request) -> dict:
    ts = body.ts if body.ts > 0 else time.time()
    request.app.state.heartbeats[body.host] = ts
    return {"ok": True}


@heartbeat_router.get("/health/guard")
def get_guard_health(request: Request, host: str = HOST,
                     max_silence_s: float = DEFAULT_MAX_SILENCE_S) -> dict:
    last_seen = request.app.state.heartbeats.get(host)
    return {"host": host, **guard_health(last_seen, time.time(), max_silence_s)}
