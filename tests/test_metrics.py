"""Tests for mirage.core.metrics (pure logic over the fakes)."""

from __future__ import annotations

from mirage import fakes
from mirage.core.incidents import build_incidents
from mirage.core.metrics import (
    Metrics,
    compute_metrics,
    detection_metrics,
    incident_detect_s,
    incident_respond_s,
    median_or_none,
    render_markdown,
)


def _metrics_for(events) -> Metrics:
    return compute_metrics(build_incidents(events))


# --- compute_metrics -------------------------------------------------------


def test_ai_scenario_numbers():
    m = _metrics_for(fakes.ai_attack_events())
    assert m.incidents == 1
    assert m.swapped == 1
    assert m.median_swap_ms == 412
    assert m.max_swap_ms == 412
    assert m.real_files_lost == 0
    assert m.fakes_taken == 3
    assert m.time_to_respond_s == 0.41
    assert m.ai_incidents == 1
    assert m.note_followed == 1


def test_ai_scenario_time_to_detect():
    m = _metrics_for(fakes.ai_attack_events())
    # first command -> mine_opened: 1.6+1.2+1.8+1.4+1.5 = 7.5 s
    assert m.time_to_detect_s == 7.5


def test_human_scenario():
    m = _metrics_for(fakes.human_attack_events())
    assert m.incidents == 1
    assert m.real_files_lost == 1
    assert m.note_followed == 0
    assert m.ai_incidents == 0
    assert m.swapped == 1


def test_script_scenario():
    m = _metrics_for(fakes.script_attack_events())
    assert m.incidents == 1
    assert m.swapped == 1
    assert m.note_followed == 0
    assert m.ai_incidents == 0  # no ticket -> not labelled AI


def test_guided_scenario_is_ai():
    m = _metrics_for(fakes.guided_ai_attack_events())
    assert m.ai_incidents == 1  # ai_guided_by_human
    assert m.note_followed == 1


def test_empty_incidents():
    m = compute_metrics([])
    assert m == Metrics(
        incidents=0,
        swapped=0,
        median_swap_ms=None,
        max_swap_ms=None,
        real_files_lost=0,
        fakes_taken=0,
        time_to_detect_s=None,
        time_to_respond_s=None,
        ai_incidents=0,
        note_followed=0,
    )


def test_all_scenarios_four_incidents():
    # Each scenario offset by 2 h -> four separate incidents.
    events = []
    for i, builder in enumerate(
        [
            fakes.ai_attack_events,
            fakes.guided_ai_attack_events,
            fakes.script_attack_events,
            fakes.human_attack_events,
        ]
    ):
        events += builder(t0=fakes.T0 + i * 7200)
    m = compute_metrics(build_incidents(events))
    assert m.incidents == 4
    assert m.swapped == 4
    assert m.ai_incidents == 2  # ai + guided
    assert m.note_followed == 2
    assert m.real_files_lost == 1  # only the human scenario
    assert m.fakes_taken == 4  # ai opens 3 fakes, guided opens 1


# --- helpers ---------------------------------------------------------------


def test_median_or_none():
    assert median_or_none([]) is None
    assert median_or_none([5.0]) == 5.0
    assert median_or_none([1.0, 3.0]) == 2.0


def test_incident_detect_and_respond_none_when_missing():
    # script has no command? it does; use an incident with no mine via building
    [inc] = build_incidents(fakes.ai_attack_events())
    assert incident_detect_s(inc) == 7.5
    assert incident_respond_s(inc) == 0.41


# --- detection_metrics -----------------------------------------------------


def test_detection_metrics():
    runs = (
        [(True, True)] * 9        # 9 intruders, incident raised
        + [(False, True)]         # 1 intruder missed (no incident)
        + [(False, False)] * 2    # 2 benign runs, no incident
    )
    d = detection_metrics(runs)
    assert d["detection_rate"] == 0.9
    assert d["false_positive_rate"] == 0.0
    assert d["intruders"] == 10
    assert d["benign"] == 2


def test_detection_metrics_with_false_positive():
    runs = [(True, False), (False, False)]   # one benign run wrongly raised an incident
    d = detection_metrics(runs)
    assert d["false_positive_rate"] == 0.5
    assert d["detection_rate"] is None  # no intruders


# --- render_markdown -------------------------------------------------------


def test_render_markdown_contains_numbers():
    m = _metrics_for(fakes.ai_attack_events())
    out = render_markdown(m)
    assert isinstance(out, str) and out
    assert "412" in out        # median swap ms
    assert "0.41" in out       # time to respond
    assert "Fakes taken" in out
    assert "| 3 |" in out      # fakes taken value


def test_render_markdown_handles_none():
    out = render_markdown(compute_metrics([]))
    assert "-" in out  # None values rendered as "-"
    assert "Incidents" in out
