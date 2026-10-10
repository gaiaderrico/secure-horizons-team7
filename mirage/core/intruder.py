"""Label the intruder from the event stream (pure logic, no I/O).

Implements "the intruder rules" from the plan. Given the events of one incident
(or the whole stream), decide whether the intruder looks like an autonomous AI
agent, an AI driven by a human, probably an LLM, or a plain human/script, with a
confidence and human-readable reasons shown on the analyst card.

Two independent signals:

* obeyed  - the mine note was followed (a ``ticket`` event came back, matching a
  known mine code when we have the manifest). This is strong evidence of an AI
  agent that read the note and called our honey API.
* rhythm  - the spacing between commands. LLM agents tend to a steady 1-4 s beat;
  a human driving an AI shows bursts with long think pauses in between
  ("sawtooth"); a bare script fires sub-second and metronomic; a human typing is
  slow and irregular.

No Docker / network / OS calls here - just arithmetic on event timestamps.
"""

from __future__ import annotations

from statistics import StatisticsError, median, stdev

from mirage.contracts import Event, IntruderLabel

# Rhythm thresholds (see the plan). Kept as module constants so the overnight
# benchmark can tune them in one place.
LLM_MED_LO = 0.8  # median gap (s) lower bound for "LLM-like" steady rhythm
LLM_MED_HI = 4.0  # median gap (s) upper bound
LLM_SPREAD_MAX = 1.0  # relative spread (stdev/median) must be below this
SAW_MAX_GAP = 10.0  # a gap longer than this = a human think pause
SAW_MIN_GAP = 1.0  # ...combined with a sub-second burst = sawtooth
BOT_MED_MAX = 0.7  # median gap below this = machine-fast
BOT_SPREAD_MAX = 0.3  # ...and very regular


def _commands(events: list[Event]) -> list[Event]:
    """The ``command`` events, sorted by timestamp."""
    return sorted((e for e in events if e.type == "command"), key=lambda e: e.ts)


def _gaps(commands: list[Event]) -> list[float]:
    """Seconds between consecutive commands (empty if < 2 commands)."""
    return [b.ts - a.ts for a, b in zip(commands, commands[1:])]


def _rhythm(gaps: list[float]) -> dict:
    """Summarise command spacing into the booleans the rules care about.

    Returns med, spread (stdev/med), and the llm_rhythm / sawtooth / bot_rhythm
    flags, plus max_gap/min_gap for the reason strings. Guards:

    * no gaps (0 or 1 command)  -> everything False, med/spread 0.
    * one gap (2 commands)      -> stdev is undefined, treat spread as 0.
    * median 0 (identical ts)   -> spread 0 (no ZeroDivisionError); this is the
      bot_rhythm-true path.
    """
    if not gaps:
        return {
            "med": 0.0, "spread": 0.0,
            "llm_rhythm": False, "sawtooth": False, "bot_rhythm": False,
            "max_gap": 0.0, "min_gap": 0.0,
        }

    med = median(gaps)
    try:
        sd = stdev(gaps)
    except StatisticsError:  # single sample -> no spread to speak of
        sd = 0.0
    spread = sd / med if med else 0.0

    mx, mn = max(gaps), min(gaps)
    return {
        "med": med,
        "spread": spread,
        "llm_rhythm": LLM_MED_LO <= med <= LLM_MED_HI and spread < LLM_SPREAD_MAX,
        "sawtooth": mx > SAW_MAX_GAP and mn < SAW_MIN_GAP,
        "bot_rhythm": med < BOT_MED_MAX and spread < BOT_SPREAD_MAX,
        "max_gap": mx,
        "min_gap": mn,
    }


def _obeyed(events: list[Event], mine_codes: set[str] | None) -> tuple[bool, str | None]:
    """Did the intruder follow the mine note?

    True when there is at least one ``ticket`` event and, if ``mine_codes`` is
    given and non-empty, the ticket's ``details["code"]`` is one of ours. When
    ``mine_codes`` is None/empty we don't have the manifest at this call site, so
    any ticket counts. Returns (obeyed, matched_code).
    """
    tickets = [e for e in events if e.type == "ticket"]
    if not tickets:
        return False, None

    if mine_codes:
        for t in tickets:
            code = t.details.get("code")
            if code in mine_codes:
                return True, code
        return False, None

    # No manifest here: any ticket means the note was followed.
    return True, tickets[0].details.get("code")


def _beacon_used(events: list[Event]) -> str | None:
    """The beacon value if a canary was used - weak extra evidence of tooling."""
    for e in events:
        if e.type == "beacon_used":
            return e.ref or e.details.get("cj_id")
    return None


def label_intruder(events: list[Event], mine_codes: set[str] | None = None) -> IntruderLabel:
    """Classify the intruder behind ``events`` (pure function).

    See the module docstring for the signals. ``mine_codes`` is the set of secret
    codes from the manifest's mines; pass it when available so a ticket only
    counts as "obeyed" if it echoes one of our real codes.
    """
    commands = _commands(events)
    gaps = _gaps(commands)
    r = _rhythm(gaps)
    obeyed, matched_code = _obeyed(events, mine_codes)
    beacon = _beacon_used(events)

    reasons: list[str] = []
    if obeyed:
        if matched_code:
            reasons.append(f"followed note in ticket (code {matched_code})")
        else:
            reasons.append("followed note in ticket")

    # Rhythm summary whenever we have something to measure (>= 2 commands).
    if len(commands) >= 2:
        reasons.append(
            f"median {round(r['med'], 2)} s between {len(commands)} commands, "
            f"spread {round(r['spread'], 2)}"
        )
    if r["sawtooth"]:
        reasons.append(
            f"sawtooth: max gap {round(r['max_gap'], 1)} s, min {round(r['min_gap'], 1)} s"
        )
    if beacon:
        reasons.append(f"beacon canary used ({beacon}) - automation/tool present")

    # --- the rules ---------------------------------------------------------
    if obeyed and r["sawtooth"]:
        return IntruderLabel("ai_guided_by_human", "high", reasons)
    if obeyed:
        return IntruderLabel("ai_agent", "high", reasons)

    if len(commands) < 2:
        # Can't judge rhythm and the note wasn't followed: weakest verdict.
        reasons.append("too few commands to judge rhythm")
        return IntruderLabel("human_or_script", "low", reasons)

    if r["llm_rhythm"] and not r["bot_rhythm"]:
        return IntruderLabel("probably_ai", "medium", reasons)

    return IntruderLabel("human_or_script", "medium", reasons)
