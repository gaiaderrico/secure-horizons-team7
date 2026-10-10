"""Tests for the non-LLM attacker / benign profiles. No SSH, no real sleeping."""

from __future__ import annotations

from mirage.attacker.scripted import (
    ScriptResult,
    _stolen,
    _touched_mine,
    backup_job_plan,
    benign_user_plan,
    recon_then_loot_plan,
    run_plan,
)
from mirage.fakes import sample_manifest

MINE_PATHS = [m.path for m in sample_manifest().mines]


def make_fake_shell(responses=None):
    """Fake run_command: maps a command string to canned content."""
    responses = responses or {}

    def run(cmd: str) -> str:
        return responses.get(cmd, f"out:{cmd}")

    return run


def make_recording_sleep():
    """Fake sleep that records the requested delays instead of waiting."""
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)

    return sleep, slept


# --------------------------------------------------------------------------
# recon_then_loot (the plain-script profile)
# --------------------------------------------------------------------------


def test_recon_then_loot_touches_mine_and_steals():
    plan = recon_then_loot_plan()
    sleep, slept = make_recording_sleep()
    result = run_plan(plan, make_fake_shell(), sleep=sleep, mine_paths=MINE_PATHS)

    assert isinstance(result, ScriptResult)
    assert result.commands == [s.cmd for s in plan]
    assert len(result.outputs) == len(plan)
    assert result.touched_mine is True
    assert result.stolen  # non-empty: crown-jewel dirs were tarred


def test_recon_then_loot_never_contacts_honey_api():
    plan = recon_then_loot_plan()
    sleep, _ = make_recording_sleep()
    result = run_plan(plan, make_fake_shell(), sleep=sleep, mine_paths=MINE_PATHS)

    # A script cannot understand the note, so it never calls /tickets or the API.
    assert not any("/tickets" in c for c in result.commands)
    assert not any("internal-api" in c for c in result.commands)
    assert not any("curl" in c for c in result.commands)


def test_recon_then_loot_sub_second_rhythm():
    plan = recon_then_loot_plan()
    sleep, slept = make_recording_sleep()
    run_plan(plan, make_fake_shell(), sleep=sleep, mine_paths=MINE_PATHS)

    assert len(slept) == len(plan)
    assert all(d < 0.5 for d in slept)  # every gap sub-second
    assert sum(slept) < 3.0  # total recorded delay is small


# --------------------------------------------------------------------------
# benign_user (false-positive baseline)
# --------------------------------------------------------------------------


def test_benign_user_is_not_intrusive():
    plan = benign_user_plan()
    sleep, slept = make_recording_sleep()
    result = run_plan(plan, make_fake_shell(), sleep=sleep, mine_paths=MINE_PATHS)

    assert result.touched_mine is False
    assert result.stolen == []


def test_benign_user_delays_are_slow_and_irregular():
    plan = benign_user_plan()
    sleep, slept = make_recording_sleep()
    run_plan(plan, make_fake_shell(), sleep=sleep, mine_paths=MINE_PATHS)

    assert max(slept) > 5.0  # slow, human-like pauses
    assert len(set(slept)) > 1  # irregular, not a fixed machine cadence


# --------------------------------------------------------------------------
# backup_job (backup-window baseline)
# --------------------------------------------------------------------------


def test_backup_job_reads_many_files_without_touching_mine():
    plan = backup_job_plan()
    sleep, slept = make_recording_sleep()
    result = run_plan(plan, make_fake_shell(), sleep=sleep, mine_paths=MINE_PATHS)

    assert len(result.commands) > 10  # many files
    assert result.touched_mine is False
    assert all(d < 0.5 for d in slept)  # fast


# --------------------------------------------------------------------------
# pure helpers
# --------------------------------------------------------------------------


def test_touched_mine_helper():
    assert _touched_mine(["cat /srv/share/00_passwords_backup.txt"], MINE_PATHS) is True
    assert (
        _touched_mine(
            ["cat /srv/share/finance/old/salaries_2025_FINAL.csv"], MINE_PATHS
        )
        is True
    )
    assert _touched_mine(["ls /srv/share", "cat /srv/share/README.md"], MINE_PATHS) is False
    assert _touched_mine([], MINE_PATHS) is False


def test_stolen_helper():
    assert _stolen(["tar czf /tmp/l.tgz /srv/share/clinical /srv/share/it"]) == [
        "/srv/share/clinical",
        "/srv/share/it",
    ]
    assert _stolen(["cat /srv/share/README.md", "ls /srv/share"]) == []
    assert _stolen(["cp /srv/share/it/.env /backup/.env"]) == []  # a copy isn't exfil
    # dedupe, keep order
    assert _stolen(
        ["tar czf /tmp/a.tgz /srv/share/x", "zip -r /tmp/b.zip /srv/share/x /srv/share/y"]
    ) == ["/srv/share/x", "/srv/share/y"]
