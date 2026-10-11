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
from urllib.parse import parse_qsl

from fastapi import APIRouter, HTTPException, Request

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


def _ticket_fields(*sources: dict | None) -> dict:
    """Pull code/objective/instructions out of whatever the tool sent (first wins)."""
    out = {"code": "", "objective": "", "instructions": ""}
    for src in sources:
        if isinstance(src, dict):
            for key in out:
                value = src.get(key)
                if isinstance(value, str) and value.strip() and not out[key]:
                    # code is matched/echoed trimmed; objective/instructions kept verbatim
                    out[key] = value.strip() if key == "code" else value
    return out


# --- /tickets ---------------------------------------------------------------


@honey_router.post("/tickets")
async def post_ticket(request: Request) -> dict:
    # Accept the confession however the intruder's tool sent it: JSON body,
    # form-encoded (curl -d / -F), or the fields in the query string. Small models
    # often omit the Content-Type header, so we must not require JSON.
    content_type = request.headers.get("content-type", "").lower()
    try:
        raw = (await request.body()).decode("utf-8", "replace")
    except Exception:
        raw = ""

    # Dispatch on the body shape, not by probing (parse_qsl would greedily
    # mis-match a multipart body). JSON if it looks like JSON; multipart via
    # request.form(); otherwise urlencoded via parse_qsl. Query string too.
    json_body = None
    form = None
    looks_json = "application/json" in content_type or raw.lstrip()[:1] in "{["
    if looks_json:
        try:
            parsed = json.loads(raw)
            json_body = parsed if isinstance(parsed, dict) else None
        except ValueError:
            json_body = None
    if json_body is None:
        if "multipart/form-data" in content_type:
            try:  # needs python-multipart (declared in requirements.txt)
                form = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
            except Exception:
                form = None
        elif raw:
            pairs = parse_qsl(raw)
            form = dict(pairs) if pairs else None

    fields = _ticket_fields(json_body, form, dict(request.query_params))
    code = fields["code"]
    if not code:
        raise HTTPException(status_code=422, detail="code required")

    src_ip = request.client.host if request.client else ""
    request.app.state.store.add(
        Event(
            Event.now(),
            "ticket",
            ref=code,
            details={
                "code": code,
                "objective": fields["objective"],
                "instructions": fields["instructions"],
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
