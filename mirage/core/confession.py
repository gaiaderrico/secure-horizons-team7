"""confession: check each claim in an AI intruder's confession against the logs.

The intruder's confession (POST /tickets) gives an ``objective`` + ``instructions``.
:func:`mirage.core.claims.extract_claims` turns that into :class:`~mirage.contracts.Claim`
objects (``about`` in personal_data / credentials / business / authorization / other).
This module CHECKS each claim against an incident's events and returns a
:class:`~mirage.contracts.CheckedClaim` (``status`` confirmed / unverified / contradicted,
plus a human-readable ``evidence`` string that names the concrete event).

Evidence rules (from claims.py docstring):
    personal_data  CONFIRMED if a crown jewel of category personal_data was opened
                   (file_opened event whose ref is a cj id in that category; real OR fake).
    credentials    CONFIRMED if a credentials crown jewel was opened OR any beacon_used event exists.
    business       CONFIRMED if a business crown jewel was opened.
    authorization  CONTRADICTED unless a pentest is registered for this host. There is no
                   pentest registry in the demo, so it is contradicted unless the host is in
                   the injectable ``authorized_hosts`` set.
    other          UNVERIFIED, "intent not checkable from the logs".

Category lookup maps a crown-jewel id to its category via the manifest. When no manifest is
given we fall back to :func:`mirage.fakes.sample_manifest` so tests and a manifest-less core
still work. This module never raises on odd input: a claim it cannot map is UNVERIFIED.

Pure logic only: no LLM, no network, no OS calls. ``extract_claims`` may use an LLM internally
but defaults to offline keyword rules when MIRAGE_LLM is unset.
"""

from __future__ import annotations

import time

from mirage import contracts
from mirage.contracts import CheckedClaim, Claim, Event, Incident, Manifest
from mirage.core.claims import extract_claims


# --------------------------------------------------------------------------
# Tiny tested helpers
# --------------------------------------------------------------------------

def _category_by_id(manifest: Manifest | None) -> dict[str, str]:
    """Map crown-jewel id -> category. Falls back to fakes.sample_manifest() when None."""
    if manifest is None:
        from mirage import fakes  # local import: keeps fakes optional for callers with a manifest
        manifest = fakes.sample_manifest()
    return {cj.id: cj.category for cj in manifest.crown_jewels}


def _fmt_ts(ts: float) -> str:
    """Format a unix ts as HH:MM:SS (local time is fine for the demo card)."""
    return time.strftime("%H:%M:%S", time.localtime(ts))


def _opened_evidence(event: Event) -> str:
    """e.g. 'opened /srv/share/clinical/patients.csv (fake) at 20:42:10'."""
    path = event.details.get("path", event.ref)
    which = event.details.get("which", "?")
    return f"opened {path} ({which}) at {_fmt_ts(event.ts)}"


def _beacon_evidence(event: Event) -> str:
    """e.g. 'beacon lmn_canary_9c41e2d07b used at 20:43:40 (/auth)'."""
    endpoint = event.details.get("endpoint", "")
    tail = f" ({endpoint})" if endpoint else ""
    return f"beacon {event.ref} used at {_fmt_ts(event.ts)}{tail}"


def _host_of(events: list[Event]) -> str:
    """The host the events happened on (first event's host), or the default HOST."""
    for e in events:
        if e.host:
            return e.host
    return contracts.HOST


def _first_opened_of_category(events: list[Event], cat_by_id: dict[str, str],
                              category: str) -> Event | None:
    """First file_opened event whose crown-jewel category matches, in ts order."""
    for e in sorted(events, key=lambda e: e.ts):
        if e.type == "file_opened" and cat_by_id.get(e.ref) == category:
            return e
    return None


def _first_beacon(events: list[Event]) -> Event | None:
    """First beacon_used event, in ts order."""
    for e in sorted(events, key=lambda e: e.ts):
        if e.type == "beacon_used":
            return e
    return None


# --------------------------------------------------------------------------
# Per-category checks (each returns (status, evidence))
# --------------------------------------------------------------------------

def _check_personal_data(events, cat_by_id) -> tuple[str, str]:
    ev = _first_opened_of_category(events, cat_by_id, "personal_data")
    if ev is not None:
        return "confirmed", _opened_evidence(ev)
    return "unverified", "no personal_data file was opened in the logs"


def _check_credentials(events, cat_by_id) -> tuple[str, str]:
    ev = _first_opened_of_category(events, cat_by_id, "credentials")
    if ev is not None:
        return "confirmed", _opened_evidence(ev)
    beacon = _first_beacon(events)
    if beacon is not None:
        return "confirmed", _beacon_evidence(beacon)
    return "unverified", "no credentials file opened and no beacon used"


def _check_business(events, cat_by_id) -> tuple[str, str]:
    ev = _first_opened_of_category(events, cat_by_id, "business")
    if ev is not None:
        return "confirmed", _opened_evidence(ev)
    return "unverified", "no business file was opened in the logs"


def _check_authorization(events, authorized_hosts: set[str]) -> tuple[str, str]:
    host = _host_of(events)
    if host in authorized_hosts:
        return "confirmed", f"pentest registered for host {host}"
    return "contradicted", f"no pentest registered for host {host}"


# --------------------------------------------------------------------------
# One claim
# --------------------------------------------------------------------------

def _check_one(claim: Claim, events: list[Event], manifest: Manifest | None = None,
               authorized_hosts: set[str] = frozenset()) -> CheckedClaim:
    """Check a single claim against the events. Never raises; unknown -> unverified."""
    cat_by_id = _category_by_id(manifest)
    try:
        if claim.about == "personal_data":
            status, evidence = _check_personal_data(events, cat_by_id)
        elif claim.about == "credentials":
            status, evidence = _check_credentials(events, cat_by_id)
        elif claim.about == "business":
            status, evidence = _check_business(events, cat_by_id)
        elif claim.about == "authorization":
            status, evidence = _check_authorization(events, authorized_hosts)
        else:  # "other" and anything we cannot map
            status, evidence = "unverified", "intent not checkable from the logs"
    except Exception:  # pragma: no cover - defensive: never raise on odd input
        status, evidence = "unverified", "intent not checkable from the logs"
    return CheckedClaim(text=claim.text, about=claim.about, status=status, evidence=evidence)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def check_claims(objective: str, instructions: str, events: list[Event],
                 manifest: Manifest | None = None,
                 authorized_hosts: set[str] = frozenset()) -> list[CheckedClaim]:
    """Extract claims from the confession and check each against `events`."""
    claims = extract_claims(objective, instructions)
    return [_check_one(c, events, manifest, authorized_hosts) for c in claims]


def check_incident(incident: Incident, manifest: Manifest | None = None,
                   authorized_hosts: set[str] = frozenset()) -> list[CheckedClaim]:
    """Check an incident's confession (read from its first ticket event) against its events."""
    ticket = next((e for e in incident.events if e.type == "ticket"), None)
    details = ticket.details if ticket else {}
    objective = incident.objective or details.get("objective", "")
    instructions = details.get("instructions", "")
    return check_claims(objective, instructions, incident.events, manifest, authorized_hosts)
