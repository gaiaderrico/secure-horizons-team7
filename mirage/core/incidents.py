"""Turn the raw event stream into incidents (pure logic, no I/O).

An incident = events on one host with no gap > window_s between consecutive
events, containing at least one trigger (mine opened, ticket, beacon used).
Recomputed from scratch on every call; ids are deterministic so the dashboard
and contain/restore endpoints can rely on them.
"""

from __future__ import annotations

from mirage.contracts import INCIDENT_WINDOW_S, Event, Incident, IncidentStatus

TRIGGER_TYPES = frozenset({"mine_opened", "ticket", "beacon_used"})


def group_events(events: list[Event], window_s: float = INCIDENT_WINDOW_S) -> list[list[Event]]:
    """Split events per host, then into time groups (new group when gap > window_s)."""
    by_host: dict[str, list[Event]] = {}
    for e in events:
        by_host.setdefault(e.host, []).append(e)

    groups: list[list[Event]] = []
    for host_events in by_host.values():
        current: list[Event] = []
        for e in sorted(host_events, key=lambda e: e.ts):
            if current and e.ts - current[-1].ts > window_s:
                groups.append(current)
                current = []
            current.append(e)
        if current:
            groups.append(current)
    return groups


def is_incident(group: list[Event]) -> bool:
    return any(e.type in TRIGGER_TYPES for e in group)


def incident_id(host: str, start_ts: float) -> str:
    return f"inc-{host}-{int(start_ts)}"


def _opened_files(group: list[Event], which: str) -> list[str]:
    """Unique cj ids of file_opened events with details.which == which, first-seen order."""
    out: list[str] = []
    for e in group:
        if e.type == "file_opened" and e.details.get("which") == which and e.ref not in out:
            out.append(e.ref)
    return out


def _status(group: list[Event]) -> IncidentStatus:
    """'open' unless contained/restored; the latest of the two (by ts) wins."""
    status: IncidentStatus = "open"
    for e in group:  # group is sorted by ts, so the last match wins
        if e.type == "contain_done":
            status = "contained"
        elif e.type == "restore_done":
            status = "restored"
    return status


def _incident_from_group(group: list[Event]) -> Incident:
    """Build an Incident from one ts-sorted group of events on a single host."""
    first, last = group[0], group[-1]
    swaps = [e for e in group if e.type == "swap_done"]
    tickets = [e for e in group if e.type == "ticket"]
    swap_ms = swaps[0].details.get("duration_ms") if swaps else None
    return Incident(
        id=incident_id(first.host, first.ts),
        host=first.host,
        start_ts=first.ts,
        end_ts=last.ts,
        events=list(group),
        swapped=bool(swaps),
        swap_ms=float(swap_ms) if swap_ms is not None else None,
        real_files_lost=_opened_files(group, "real"),
        fakes_taken=_opened_files(group, "fake"),
        objective=tickets[0].details.get("objective", "") if tickets else "",
        status=_status(group),
        # Plug-in points for other modules (core/intruder.py, core/confession.py):
        # intruder = label_intruder(group); claims = check_claims(objective, group)
        intruder=None,
        claims=[],
    )


def build_incidents(events: list[Event], window_s: float = INCIDENT_WINDOW_S) -> list[Incident]:
    """All incidents found in `events`, newest first (by start_ts)."""
    incidents = [_incident_from_group(g) for g in group_events(events, window_s) if is_incident(g)]
    return sorted(incidents, key=lambda i: i.start_ts, reverse=True)
