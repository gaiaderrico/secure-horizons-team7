"""Tests for the Contain / Restore endpoints and their offline guard client.

The guard is never actually called over the network: every HTTP test replaces
``app.state.guard`` with a FakeGuard, and the one offline-mode test drives the
default client with MIRAGE_GUARD_DISABLED set.
"""

import time

import pytest
from fastapi.testclient import TestClient

from mirage.contracts import ATTACK_USER, HOST
from mirage.core.api import create_app
from mirage.core.control import GuardClient, _attacker_user, _restored_files
from mirage.core.incidents import build_incidents, incident_id


class FakeGuard:
    """Stand-in for GuardClient: records calls, returns a chosen (ok, detail)."""

    def __init__(self, ok=True, detail="ok"):
        self.ok = ok
        self.detail = detail
        self.token = ""  # set by tests that want to assert the header value
        self.calls = []  # list of (action, payload)

    def contain(self, payload):
        self.calls.append(("contain", payload))
        return self.ok, self.detail

    def restore(self, payload):
        self.calls.append(("restore", payload))
        return self.ok, self.detail


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "c.db")))


def _seed_incident(client, start_ts):
    """POST a mine_opened + swap_done so one incident exists, return its id."""
    client.post("/events", json=[
        {"ts": start_ts, "type": "mine_opened", "ref": "m1",
         "details": {"path": "/srv/share/00_passwords_backup.txt"}},
        {"ts": start_ts + 0.4, "type": "swap_done",
         "details": {"duration_ms": 412, "files": ["cj1", "cj2", "cj3"]}},
    ])
    return incident_id(HOST, start_ts)


# --- contain -----------------------------------------------------------------


def test_contain_ok_flips_status_and_calls_guard(client):
    start = time.time()
    inc_id = _seed_incident(client, start)
    fake = FakeGuard(ok=True)
    fake.token = "tok-123"
    client.app.state.guard = fake

    r = client.post(f"/incidents/{inc_id}/contain")
    assert r.status_code == 200
    assert r.json()["status"] == "contained"

    # contain_done event recorded
    done = client.get("/events", params={"type": "contain_done"}).json()
    assert len(done) == 1
    assert done[0]["details"] == {"user": ATTACK_USER, "by": "analyst"}

    # guard got the call with the right payload + token
    assert fake.calls == [("contain", {"user": ATTACK_USER, "incident": inc_id, "by": "analyst"})]
    assert fake.token == "tok-123"


def test_contain_custom_analyst_user(client):
    inc_id = _seed_incident(client, time.time())
    client.app.state.guard = FakeGuard(ok=True)
    r = client.post(f"/incidents/{inc_id}/contain", json={"user": "soc_jane"})
    assert r.status_code == 200
    done = client.get("/events", params={"type": "contain_done"}).json()
    assert done[0]["user"] == "soc_jane"
    assert done[0]["details"]["by"] == "soc_jane"


def test_contain_uses_attacker_user_from_events(client):
    start = time.time()
    # a command event carries the attacker's real login
    client.post("/events", json=[
        {"ts": start, "type": "command", "user": "evil_svc",
         "details": {"cmd": "id"}},
        {"ts": start + 1, "type": "mine_opened", "ref": "m1",
         "details": {"path": "/srv/share/00_passwords_backup.txt"}},
        {"ts": start + 1.4, "type": "swap_done",
         "details": {"files": ["cj1"]}},
    ])
    inc_id = incident_id(HOST, start)
    fake = FakeGuard(ok=True)
    client.app.state.guard = fake
    client.post(f"/incidents/{inc_id}/contain")
    assert fake.calls[0][1]["user"] == "evil_svc"


def test_contain_guard_failure_is_502_and_records_nothing(client):
    inc_id = _seed_incident(client, time.time())
    client.app.state.guard = FakeGuard(ok=False, detail="boom")
    r = client.post(f"/incidents/{inc_id}/contain")
    assert r.status_code == 502
    assert "boom" in r.json()["detail"]
    assert client.get("/events", params={"type": "contain_done"}).json() == []


def test_contain_unknown_incident_is_404(client):
    client.app.state.guard = FakeGuard(ok=True)
    r = client.post("/incidents/inc-nope-1/contain")
    assert r.status_code == 404


# --- restore -----------------------------------------------------------------


def test_restore_ok_flips_status_and_records_files(client):
    start = time.time()
    inc_id = _seed_incident(client, start)
    fake = FakeGuard(ok=True)
    client.app.state.guard = fake

    r = client.post(f"/incidents/{inc_id}/restore")
    assert r.status_code == 200
    assert r.json()["status"] == "restored"

    done = client.get("/events", params={"type": "restore_done"}).json()
    assert len(done) == 1
    assert done[0]["details"] == {"files": ["cj1", "cj2", "cj3"], "by": "analyst"}
    assert fake.calls == [("restore", {"user": ATTACK_USER, "incident": inc_id, "by": "analyst"})]


def test_restore_guard_failure_is_502(client):
    inc_id = _seed_incident(client, time.time())
    client.app.state.guard = FakeGuard(ok=False, detail="nope")
    r = client.post(f"/incidents/{inc_id}/restore")
    assert r.status_code == 502
    assert client.get("/events", params={"type": "restore_done"}).json() == []


# --- pure helpers ------------------------------------------------------------


def test_attacker_user_from_command_event():
    from mirage.contracts import Event
    events = [
        Event(1.0, "mine_opened", HOST, "", "m1", {}),
        Event(2.0, "command", HOST, "svc_backup", "", {"cmd": "id"}),
        Event(3.0, "contain_done", HOST, "analyst", "", {}),
    ]
    assert _attacker_user(events) == "svc_backup"


def test_attacker_user_fallback_when_no_user():
    from mirage.contracts import Event
    events = [Event(1.0, "mine_opened", HOST, "", "m1", {})]
    assert _attacker_user(events) == ATTACK_USER


def test_attacker_user_skips_analyst_events():
    from mirage.contracts import Event
    # only the analyst's own event has a user -> must not be picked
    events = [
        Event(1.0, "swap_done", HOST, "", "", {"files": ["cj1"]}),
        Event(2.0, "restore_done", HOST, "analyst", "", {}),
    ]
    assert _attacker_user(events) == ATTACK_USER


def test_restored_files_from_swap_done():
    incs = _incident_with_swap(["cj1", "cj2"])
    assert _restored_files(incs) == ["cj1", "cj2"]


def test_restored_files_empty_without_swap():
    from mirage.contracts import Event, Incident
    inc = Incident(id="x", host=HOST, start_ts=1.0, end_ts=2.0,
                   events=[Event(1.0, "mine_opened", HOST, "", "m1", {})])
    assert _restored_files(inc) == []


def _incident_with_swap(files):
    from mirage.contracts import Event, Incident
    ev = [
        Event(1.0, "mine_opened", HOST, "", "m1", {}),
        Event(1.4, "swap_done", HOST, "", "", {"files": files}),
    ]
    return Incident(id="x", host=HOST, start_ts=1.0, end_ts=1.4, events=ev)


# --- offline / dev mode (default guard, no fake) -----------------------------


def test_offline_mode_contain_succeeds_and_records(tmp_path, monkeypatch):
    monkeypatch.setenv("MIRAGE_GUARD_DISABLED", "1")
    app = create_app(db_path=str(tmp_path / "off.db"))
    client = TestClient(app)
    # default guard, no fake
    assert isinstance(app.state.guard, GuardClient)

    inc_id = _seed_incident(client, time.time())
    r = client.post(f"/incidents/{inc_id}/contain")
    assert r.status_code == 200
    assert r.json()["status"] == "contained"
    assert len(client.get("/events", params={"type": "contain_done"}).json()) == 1
    # monkeypatch restores MIRAGE_GUARD_DISABLED automatically at teardown
