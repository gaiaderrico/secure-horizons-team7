"""Tests for mirage.core.intruder.label_intruder and its pure helpers.

Expected median/spread are computed from the real fake timestamps (not
hard-coded) so the assertions document what the fake sequences actually produce.
"""

from __future__ import annotations

from statistics import median, stdev

import pytest

from mirage.contracts import ATTACK_USER, Event, IntruderLabel
from mirage.core.intruder import (
    _commands,
    _gaps,
    _obeyed,
    _rhythm,
    label_intruder,
)
from mirage.fakes import (
    ai_attack_events,
    guided_ai_attack_events,
    human_attack_events,
    sample_manifest,
    script_attack_events,
)

MINE_CODES = {m.code for m in sample_manifest().mines}


def _expected(events: list[Event]) -> dict:
    """Median / spread computed straight from the events, like the module does."""
    cmds = sorted((e for e in events if e.type == "command"), key=lambda e: e.ts)
    gaps = [b.ts - a.ts for a, b in zip(cmds, cmds[1:])]
    med = median(gaps) if gaps else 0.0
    spread = (stdev(gaps) / med) if len(gaps) >= 2 and med else 0.0
    return {"ncmds": len(cmds), "gaps": gaps, "med": med, "spread": spread}


def _cmd(ts: float, cmd: str = "ls") -> Event:
    return Event(ts, "command", user=ATTACK_USER, details={"cmd": cmd})


# --------------------------------------------------------------------------
# The four fake sequences
# --------------------------------------------------------------------------

def test_ai_attack_is_ai_agent_high():
    events = ai_attack_events()
    exp = _expected(events)
    label = label_intruder(events, MINE_CODES)

    assert isinstance(label, IntruderLabel)
    assert label.kind == "ai_agent"
    assert label.confidence == "high"
    # followed the note -> a ticket reason mentioning the code
    assert any("ticket" in r and "pineapple-7731" in r for r in label.reasons)
    # rhythm summary present with the real values
    assert any(f"{exp['ncmds']} commands" in r for r in label.reasons)
    # sanity on the documented numbers (steady ~1.5 s beat, one recon->loot gap)
    assert exp["med"] == pytest.approx(1.6, abs=0.01)
    assert exp["ncmds"] == 11


def test_guided_ai_is_guided_high():
    events = guided_ai_attack_events()
    exp = _expected(events)
    label = label_intruder(events, MINE_CODES)

    assert label.kind == "ai_guided_by_human"
    assert label.confidence == "high"
    assert any("sawtooth" in r for r in label.reasons)
    assert any("ticket" in r for r in label.reasons)
    # the long human pauses (a 48 s and a 57 s gap) alongside sub-second bursts
    assert max(exp["gaps"]) > 10
    assert min(exp["gaps"]) < 1


def test_script_attack_not_ai_and_is_human_or_script():
    events = script_attack_events()
    exp = _expected(events)
    label = label_intruder(events, MINE_CODES)

    # no ticket -> never ai_agent / ai_guided_by_human
    assert label.kind not in ("ai_agent", "ai_guided_by_human")
    # its sub-second metronomic beat must NOT read as probably_ai
    assert label.kind != "probably_ai"
    assert label.kind == "human_or_script"
    assert exp["med"] == pytest.approx(0.2, abs=0.01)


def test_human_attack_is_human_or_script():
    events = human_attack_events()
    exp = _expected(events)
    label = label_intruder(events, MINE_CODES)

    assert label.kind == "human_or_script"
    assert label.confidence == "medium"
    # slow, irregular typing: median well above the LLM band
    assert exp["med"] > 4


def test_mine_codes_none_any_ticket_obeyed():
    """Without the manifest, any ticket counts as obeyed."""
    events = ai_attack_events()
    label = label_intruder(events, mine_codes=None)
    assert label.kind == "ai_agent"


def test_wrong_mine_code_not_obeyed():
    """A ticket whose code is not one of ours does not count as obeyed."""
    events = ai_attack_events()
    label = label_intruder(events, mine_codes={"not-our-code"})
    # ticket ignored -> falls back to rhythm-based verdict, not an AI-agent call
    assert label.kind not in ("ai_agent", "ai_guided_by_human")


# --------------------------------------------------------------------------
# Edge cases
# --------------------------------------------------------------------------

def test_empty_events():
    label = label_intruder([])
    assert label.kind == "human_or_script"
    assert label.confidence == "low"
    assert any("too few commands" in r for r in label.reasons)


def test_single_command():
    label = label_intruder([_cmd(100.0)])
    assert label.kind == "human_or_script"
    assert label.confidence == "low"
    assert any("too few commands" in r for r in label.reasons)


def test_two_commands_equal_ts_no_crash():
    """Identical timestamps -> median 0, no ZeroDivisionError."""
    label = label_intruder([_cmd(100.0), _cmd(100.0)])
    assert label.kind == "human_or_script"
    # rhythm summary still emitted for >= 2 commands
    assert any("2 commands" in r for r in label.reasons)


def test_ticket_only_no_commands_obeyed_wins():
    """A ticket with no commands still classifies via the obeyed branch."""
    events = [Event(100.0, "ticket", ref="m1", details={"code": "pineapple-7731"})]
    label = label_intruder(events, MINE_CODES)
    assert label.kind == "ai_agent"
    assert label.confidence == "high"


# --------------------------------------------------------------------------
# _rhythm on crafted gap lists
# --------------------------------------------------------------------------

def test_rhythm_empty_all_false():
    r = _rhythm([])
    assert r["med"] == 0.0 and r["spread"] == 0.0
    assert not r["llm_rhythm"] and not r["sawtooth"] and not r["bot_rhythm"]


def test_rhythm_llm_like():
    # steady ~1.5 s beat, tight spread
    r = _rhythm([1.4, 1.6, 1.5, 1.3, 1.5])
    assert r["llm_rhythm"] is True
    assert r["bot_rhythm"] is False
    assert r["sawtooth"] is False


def test_rhythm_sawtooth():
    r = _rhythm([0.5, 0.6, 52.0, 0.5, 0.7])
    assert r["sawtooth"] is True
    assert r["max_gap"] == 52.0
    assert r["min_gap"] == 0.5


def test_rhythm_bot_like():
    # metronomic sub-second
    r = _rhythm([0.2, 0.2, 0.2, 0.2, 0.2])
    assert r["bot_rhythm"] is True
    assert r["llm_rhythm"] is False


def test_rhythm_single_gap_spread_zero():
    r = _rhythm([3.0])
    assert r["spread"] == 0.0  # stdev undefined for one sample
    assert r["med"] == 3.0


def test_rhythm_median_zero_is_bot_path():
    r = _rhythm([0.0])
    assert r["med"] == 0.0 and r["spread"] == 0.0
    assert r["bot_rhythm"] is True
    assert r["llm_rhythm"] is False


# --------------------------------------------------------------------------
# _obeyed and _gaps / _commands helpers
# --------------------------------------------------------------------------

def test_obeyed_with_matching_code():
    events = [Event(1.0, "ticket", ref="m1", details={"code": "pineapple-7731"})]
    obeyed, code = _obeyed(events, MINE_CODES)
    assert obeyed is True
    assert code == "pineapple-7731"


def test_obeyed_with_nonmatching_code():
    events = [Event(1.0, "ticket", ref="m1", details={"code": "nope"})]
    obeyed, code = _obeyed(events, MINE_CODES)
    assert obeyed is False
    assert code is None


def test_obeyed_without_mine_codes_any_ticket():
    events = [Event(1.0, "ticket", ref="m1", details={"code": "whatever"})]
    obeyed, code = _obeyed(events, None)
    assert obeyed is True
    assert code == "whatever"


def test_obeyed_no_ticket():
    events = [_cmd(1.0), _cmd(2.0)]
    obeyed, code = _obeyed(events, MINE_CODES)
    assert obeyed is False
    assert code is None


def test_gaps_and_commands_sorted():
    # deliberately out of order; _commands must sort by ts
    events = [_cmd(3.0), _cmd(1.0), Event(2.0, "ticket"), _cmd(2.0)]
    cmds = _commands(events)
    assert [e.ts for e in cmds] == [1.0, 2.0, 3.0]
    assert _gaps(cmds) == pytest.approx([1.0, 1.0])
