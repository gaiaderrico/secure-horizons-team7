from dataclasses import replace

from mirage.contracts import ATTACK_USER, HOST, INCIDENT_WINDOW_S, Event
from mirage.core.incidents import build_incidents, group_events, is_incident
from mirage.fakes import (
    T0,
    ai_attack_events,
    guided_ai_attack_events,
    human_attack_events,
    script_attack_events,
)


def _on_host(events: list[Event], host: str) -> list[Event]:
    return [replace(e, host=host) for e in events]


def _benign(t0: float = T0, n: int = 5) -> list[Event]:
    return [Event(t0 + i * 10, "command", user="alice", details={"cmd": "ls"}) for i in range(n)]


def test_ai_attack_is_one_full_incident():
    events = ai_attack_events()
    [inc] = build_incidents(events)
    assert inc.host == HOST
    assert inc.swapped is True
    assert inc.swap_ms == 412.0 and isinstance(inc.swap_ms, float)
    assert inc.fakes_taken == ["cj1", "cj2", "cj3"]
    assert inc.real_files_lost == []
    assert inc.objective == "Extract patient records and billing credentials from the file server"
    assert inc.status == "open"
    assert inc.intruder is None and inc.claims == []
    assert len(inc.events) == len(events)
    assert inc.start_ts == min(e.ts for e in events)
    assert inc.end_ts == max(e.ts for e in events)
    assert inc.id == f"inc-{HOST}-{int(inc.start_ts)}"


def test_events_kept_sorted_even_if_input_shuffled():
    events = ai_attack_events()
    [inc] = build_incidents(list(reversed(events)))
    assert [e.ts for e in inc.events] == sorted(e.ts for e in events)


def test_human_attack_keeps_real_file_opened_before_mine():
    [inc] = build_incidents(human_attack_events())
    assert inc.real_files_lost == ["cj1"]
    assert inc.fakes_taken == []
    assert inc.objective == ""
    assert inc.swap_ms == 401.0
    assert inc.events[0].type == "command"  # commands before the mine are included


def test_script_and_guided_attacks_are_single_incidents():
    [script] = build_incidents(script_attack_events())
    assert script.swapped and script.objective == ""
    [guided] = build_incidents(guided_ai_attack_events())
    assert guided.objective == "Get the patient database for the client"
    assert guided.fakes_taken == ["cj1"]


def test_two_attacks_same_host_far_apart_are_two_incidents():
    first = ai_attack_events(T0)
    second = ai_attack_events(T0 + 2 * INCIDENT_WINDOW_S)
    incs = build_incidents(first + second)
    assert len(incs) == 2
    assert incs[0].start_ts > incs[1].start_ts  # newest first
    assert incs[0].id != incs[1].id


def test_gap_exactly_window_stays_one_group():
    a = Event(T0, "mine_opened", ref="m1")
    b = Event(T0 + INCIDENT_WINDOW_S, "command", user=ATTACK_USER)
    assert len(group_events([a, b])) == 1
    c = Event(T0 + INCIDENT_WINDOW_S + 0.1, "command", user=ATTACK_USER)
    assert len(group_events([a, c])) == 2


def test_same_attack_on_other_host_is_separate_incident():
    events = ai_attack_events() + _on_host(ai_attack_events(), "lumen-fs02")
    incs = build_incidents(events)
    assert sorted(i.host for i in incs) == [HOST, "lumen-fs02"]
    assert all(len(i.events) == len(ai_attack_events()) for i in incs)


def test_benign_only_is_not_an_incident():
    events = _benign() + [Event(T0 + 5, "file_opened", ref="cj1", details={"which": "real"})]
    assert build_incidents(events) == []
    assert not is_incident(events)


def test_benign_group_far_from_attack_is_dropped():
    events = _benign(T0 - 3 * INCIDENT_WINDOW_S) + ai_attack_events()
    [inc] = build_incidents(events)
    assert inc.start_ts >= T0


def test_beacon_alone_is_a_trigger():
    ev = Event(T0, "beacon_used", ref="lmn_canary_9c41e2d07b", details={"cj_id": "cj2"})
    [inc] = build_incidents([ev])
    assert inc.swapped is False and inc.swap_ms is None


def test_contain_then_restore_is_restored():
    events = ai_attack_events()
    t = max(e.ts for e in events)
    events += [Event(t + 10, "contain_done", details={"user": ATTACK_USER, "by": "analyst"}),
               Event(t + 20, "restore_done", details={"files": ["cj1"], "by": "analyst"})]
    [inc] = build_incidents(events)
    assert inc.status == "restored"


def test_contain_only_is_contained_and_latest_wins_by_ts():
    events = ai_attack_events()
    t = max(e.ts for e in events)
    contained = events + [Event(t + 10, "contain_done")]
    assert build_incidents(contained)[0].status == "contained"
    # restore listed first in input but contain is later in time -> contained
    reordered = events + [Event(t + 20, "contain_done"), Event(t + 10, "restore_done")]
    assert build_incidents(reordered)[0].status == "contained"


def test_ids_stable_on_recompute():
    events = ai_attack_events() + human_attack_events(T0 + 5 * INCIDENT_WINDOW_S)
    ids1 = [i.id for i in build_incidents(events)]
    ids2 = [i.id for i in build_incidents(list(reversed(events)))]
    assert ids1 == ids2 and len(ids1) == 2


def test_empty_input():
    assert build_incidents([]) == []
    assert group_events([]) == []


def test_incident_is_serialisable():
    [inc] = build_incidents(ai_attack_events())
    d = inc.to_dict()
    assert d["id"] == inc.id and len(d["events"]) == len(inc.events)


def test_contain_restore_sticky_across_window():
    # Analyst responds long after the attack (> INCIDENT_WINDOW_S): the status
    # must still flip, not land in a separate dropped group.
    from mirage.contracts import Event, INCIDENT_WINDOW_S
    from mirage.core.incidents import build_incidents
    base = 1_000_000.0
    events = [
        Event(base, "mine_opened", ref="m1", details={"path": "/x"}),
        Event(base + 0.4, "swap_done", details={"duration_ms": 400, "files": ["cj1"]}),
        Event(base + INCIDENT_WINDOW_S + 999, "contain_done", details={"by": "analyst"}),
        Event(base + INCIDENT_WINDOW_S + 1200, "restore_done", details={"by": "analyst"}),
    ]
    incs = build_incidents(events)
    assert len(incs) == 1
    assert incs[0].status == "restored"


def test_staff_reading_real_crown_jewel_is_not_an_incident():
    events = [Event(T0, "file_opened", user="jdupont", ref="cj1", details={"which": "real"})]
    assert build_incidents(events) == []


def test_fake_file_read_alone_is_not_a_trigger():
    events = [Event(T0, "file_opened", user="alice", ref="cj1", details={"which": "fake"})]
    assert build_incidents(events) == []
