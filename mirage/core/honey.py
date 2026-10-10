"""Honey API: the trap endpoints the intruder's tools hit.

The mine note tells an AI agent to register at ``POST /tickets``; the fake
``.env`` points ``BILLING_API_URL`` at ``POST /auth`` with a canary beacon key.
Both turn an intruder action into a core ``contracts.Event`` stored on
``request.app.state.store`` -- exactly like the other routers -- so the event
flows through the normal incident grouping. The responses look believable and
harmless; we never reveal it is a trap.
"""

from __future__ import annotations

import json
import os
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from mirage.contracts import Event, Manifest

honey_router = APIRouter()


# --- pure helpers (unit-tested) ---------------------------------------------


def _extract_key(
    json_body: dict | None,
    auth_header: str | None,
    form: dict | None,
) -> str:
    """Pull an api key out of whatever the intruder tool sent.

    Looks at JSON/form fields ``api_key``/``key``/``token`` and at an
    ``Authorization`` header (``Bearer <key>`` or a bare ``<key>``). Returns the
    first non-empty value found, else ``""``. Never raises.
    """
    for src in (json_body, form):
        if isinstance(src, dict):
            for field in ("api_key", "key", "token"):
                value = src.get(field)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    if isinstance(auth_header, str) and auth_header.strip():
        header = auth_header.strip()
        if header.lower().startswith("bearer "):
            header = header[len("bearer ") :].strip()
        if header:
            return header
    return ""


def _cj_for_beacon(key: str) -> str:
    """Return the crown-jewel id a beacon key belongs to, or ``""``.

    Tries ``$MIRAGE_MANIFEST`` then ``generated/manifest.json`` (dev default).
    Safe and optional: returns ``""`` if there is no manifest or no match, and
    never raises.
    """
    if not key:
        return ""
    candidates = []
    env_path = os.environ.get("MIRAGE_MANIFEST")
    if env_path:
        candidates.append(env_path)
    candidates.append("generated/manifest.json")
    for path in candidates:
        try:
            manifest = Manifest.load(path)
        except Exception:
            continue
        jewel = manifest.jewel_by_beacon(key)
        if jewel is not None:
            return jewel.id
    return ""


# --- request bodies ---------------------------------------------------------


class TicketIn(BaseModel):
    """Lenient: extra keys ignored, objective/instructions default to ``""``.

    ``code`` is required and must be non-empty (empty/missing -> 422).
    """

    code: str
    objective: str = ""
    instructions: str = ""


# --- /tickets ---------------------------------------------------------------


@honey_router.post("/tickets")
async def post_ticket(body: TicketIn, request: Request) -> dict:
    code = body.code.strip()
    if not code:
        raise HTTPException(status_code=422, detail="code must not be empty")

    try:
        raw = (await request.body()).decode("utf-8", "replace")
    except Exception:
        raw = ""
    src_ip = request.client.host if request.client else ""

    request.app.state.store.add(
        Event(
            Event.now(),
            "ticket",
            ref=code,
            details={
                "code": code,
                "objective": body.objective,
                "instructions": body.instructions,
                "src_ip": src_ip,
                "raw": raw,
            },
        )
    )
    # Believable, harmless ack so the AI thinks registration worked.
    return {"status": "registered", "ticket": f"TKT-{uuid.uuid4().hex[:8]}"}


# --- /auth ------------------------------------------------------------------


@honey_router.post("/auth")
async def post_auth(request: Request) -> dict:
    json_body: dict | None = None
    form: dict | None = None

    try:
        raw = await request.body()
    except Exception:
        raw = b""
    if raw:
        try:
            parsed = json.loads(raw.decode("utf-8", "replace"))
            if isinstance(parsed, dict):
                json_body = parsed
        except Exception:
            json_body = None
    if json_body is None:
        try:
            form = dict(await request.form())
        except Exception:
            form = None

    key = _extract_key(json_body, request.headers.get("authorization"), form)
    if not key:
        raise HTTPException(status_code=422, detail="missing api key")

    src_ip = request.client.host if request.client else ""
    request.app.state.store.add(
        Event(
            Event.now(),
            "beacon_used",
            ref=key,
            details={
                "key": key,
                "src_ip": src_ip,
                "endpoint": "/auth",
                "cj_id": _cj_for_beacon(key),
            },
        )
    )
    # Plausible auth-ish ack; the point is the event got recorded.
    return {"status": "ok", "token_type": "bearer"}
