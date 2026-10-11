"""The numbers for the pitch deck and defense sheet (pure logic, no I/O).

Everything here is arithmetic over ``contracts.Incident`` objects (and the
events inside them). No Docker / network / OS calls, so it runs identically on
live core data and on the synthetic ``mirage.fakes`` sequences.

The defense sheet wants: detection rate, false positives, time to detect, time
to respond, real files lost, fakes taken. ``compute_metrics`` produces the
per-incident aggregate; ``detection_metrics`` produces the detection vs
false-positive rates from a list of labelled runs.

Run ``python -m mirage.core.metrics --scenario ai`` for a one-command demo of
the slide numbers built from the fakes.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from statistics import median

from mirage.contracts import Event, Incident
from mirage.core.incidents import build_incidents
from mirage.core.intruder import label_intruder

# Intruder kinds we count as "an AI was behind this incident".
AI_KINDS = frozenset({"ai_agent", "ai_guided_by_human"})


@dataclass
class Metrics:
    incidents: int
    swapped: int                 # how many incidents did the swap
    median_swap_ms: float | None  # across incidents that swapped
    max_swap_ms: float | None
    real_files_lost: int         # total cj ids opened while real, across incidents
    fakes_taken: int             # total cj ids opened while fake
    time_to_detect_s: float | None   # per incident: first command -> mine_opened; median
    time_to_respond_s: float | None  # per incident: mine_opened -> swap_done; median
    ai_incidents: int            # incidents labelled ai_agent or ai_guided_by_human
    note_followed: int           # incidents with a ticket event


# --------------------------------------------------------------------------
# Tiny helpers (kept small so they are easy to test)
# --------------------------------------------------------------------------


def median_or_none(values: list[float]) -> float | None:
    """Median of ``values``, or ``None`` when the list is empty."""
    return median(values) if values else None


def _first_ts(events: list[Event], event_type: str) -> float | None:
    """Timestamp of the earliest event of ``event_type``, or ``None``."""
    times = [e.ts for e in events if e.type == event_type]
    return min(times) if times else None


def incident_detect_s(incident: Incident) -> float | None:
    """Seconds from the first ``command`` to the first ``mine_opened``.

    ``None`` if either event is missing. Rounded to 2 decimals.
    """
    first_cmd = _first_ts(incident.events, "command")
    first_mine = _first_ts(incident.events, "mine_opened")
    if first_cmd is None or first_mine is None:
        return None
    return round(first_mine - first_cmd, 2)


def incident_respond_s(incident: Incident) -> float | None:
    """Seconds from the first ``mine_opened`` to the first ``swap_done``.

    ``None`` if either event is missing. Rounded to 2 decimals.
    """
    first_mine = _first_ts(incident.events, "mine_opened")
    first_swap = _first_ts(incident.events, "swap_done")
    if first_mine is None or first_swap is None:
        return None
    return round(first_swap - first_mine, 2)


def _has_ticket(incident: Incident) -> bool:
    return any(e.type == "ticket" for e in incident.events)


# --------------------------------------------------------------------------
# The aggregate
# --------------------------------------------------------------------------


def compute_metrics(incidents: list[Incident]) -> Metrics:
    """Aggregate the defense-sheet numbers over ``incidents``.

    Derives everything from each incident's events and fields. Medians
    (swap ms, time to detect, time to respond) are taken only across the
    incidents that actually have the value; an empty list yields ``None``.
    """
    swap_ms = [i.swap_ms for i in incidents if i.swapped and i.swap_ms is not None]
    detects = [s for i in incidents if (s := incident_detect_s(i)) is not None]
    responds = [s for i in incidents if (s := incident_respond_s(i)) is not None]

    return Metrics(
        incidents=len(incidents),
        swapped=sum(1 for i in incidents if i.swapped),
        median_swap_ms=median_or_none(swap_ms),
        max_swap_ms=max(swap_ms) if swap_ms else None,
        real_files_lost=sum(len(i.real_files_lost) for i in incidents),
        fakes_taken=sum(len(i.fakes_taken) for i in incidents),
        time_to_detect_s=median_or_none(detects),
        time_to_respond_s=median_or_none(responds),
        ai_incidents=sum(
            1 for i in incidents if label_intruder(i.events).kind in AI_KINDS
        ),
        note_followed=sum(1 for i in incidents if _has_ticket(i)),
    )


# --------------------------------------------------------------------------
# Detection vs false positives
# --------------------------------------------------------------------------


def detection_metrics(runs: list[tuple[bool, bool]]) -> dict:
    """Detection rate and false-positive rate from labelled runs.

    Input: a list of ``(detected, is_intruder)`` tuples, one per run.

    * ``detected`` = an incident was actually raised (a mine/ticket/beacon fired).
      This is the real alert signal, NOT the rhythm label: a benign user is
      labelled ``"human_or_script"`` too, so only incident creation separates a
      false alarm from quiet, correct benign handling.
    * ``is_intruder`` is ground truth: was this run an actual intruder?

    Definitions (documented because they feed the defense sheet):

    * ``detection_rate`` = detected intruders / intruders. ``None`` if no intruders.
    * ``false_positive_rate`` = detected benign runs / benign runs. ``None`` if no benign runs.
    """
    intruders = [d for d, is_i in runs if is_i]
    benign = [d for d, is_i in runs if not is_i]
    detected = sum(1 for d in intruders if d)
    false_positives = sum(1 for d in benign if d)

    return {
        "intruders": len(intruders),
        "benign": len(benign),
        "detected": detected,
        "false_positives": false_positives,
        "detection_rate": (detected / len(intruders)) if intruders else None,
        "false_positive_rate": (false_positives / len(benign)) if benign else None,
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def _fmt(value: float | int | None) -> str:
    return "-" if value is None else str(value)


def render_markdown(metrics: Metrics) -> str:
    """A small Markdown table the deck / defense sheet can paste as-is."""
    rows = [
        ("Incidents", metrics.incidents),
        ("Swapped", metrics.swapped),
        ("Median swap (ms)", metrics.median_swap_ms),
        ("Max swap (ms)", metrics.max_swap_ms),
        ("Real files lost", metrics.real_files_lost),
        ("Fakes taken", metrics.fakes_taken),
        ("Time to detect (s)", metrics.time_to_detect_s),
        ("Time to respond (s)", metrics.time_to_respond_s),
        ("AI incidents", metrics.ai_incidents),
        ("Note followed", metrics.note_followed),
    ]
    lines = ["| Metric | Value |", "|---|---|"]
    lines += [f"| {name} | {_fmt(value)} |" for name, value in rows]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Demo
# --------------------------------------------------------------------------

# Imported lazily inside _scenario_events so the module has no hard dependency
# on fakes for library use.
_SCENARIOS = ("ai", "guided", "script", "human")


def _scenario_events(scenario: str) -> list[Event]:
    """Build the raw events for ``scenario`` from ``mirage.fakes``.

    ``all`` concatenates every scenario, each offset by 2 h so they fall into
    separate incidents (the incident window is 30 min).
    """
    from mirage import fakes

    builders = {
        "ai": fakes.ai_attack_events,
        "guided": fakes.guided_ai_attack_events,
        "script": fakes.script_attack_events,
        "human": fakes.human_attack_events,
    }
    if scenario == "all":
        events: list[Event] = []
        for i, name in enumerate(_SCENARIOS):
            events += builders[name](t0=fakes.T0 + i * 7200)
        return events
    return builders[scenario]()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="MIRAGE metrics demo over the fakes.")
    parser.add_argument(
        "--scenario",
        choices=[*_SCENARIOS, "all"],
        default="all",
        help="which fakes.* attack sequence(s) to measure",
    )
    args = parser.parse_args(argv)

    incidents = build_incidents(_scenario_events(args.scenario))
    metrics = compute_metrics(incidents)
    print(f"# MIRAGE metrics - scenario: {args.scenario}\n")
    print(render_markdown(metrics))


if __name__ == "__main__":
    main()
