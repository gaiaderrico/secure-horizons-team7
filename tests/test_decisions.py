"""Tests for the analyst decisions Keep watching / Dismiss (no guard call).

Unlike Contain / Restore, /watch and /dismiss never touch the guard: they only
record the analyst's decision so the incident status reflects it. The FakeGuard
is installed so a stray contain/restore call would be caught.
"""

import time

import pytest
from fastapi.testclient import TestClient

from mirage.contracts import HOST
from mirage.core.api import create_app
from mirage.core.incidents import incident_id


class FakeGuard:
    """Records calls so tests can assert the guard was NOT touched."""

    def __init__(self, ok=True, detail="ok"):
        self.ok = ok
        self.detail = detail
        self.token = ""
        self.calls = []

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


# --- watch -------------------------------------------------------------------


def test_watch_sets_status_records_event_no_guard(client):
    inc_id = _seed_incident(client, time.time())
    fake = FakeGuard()
    client.app.state.guard = fake

    r = client.post(f"/incidents/{inc_id}/watch")
    assert r.status_code == 200
    assert r.json()["status"] == "watching"

    events = client.get("/events", params={"type": "watching"}).json()
    assert len(events) == 1
    assert events[0]["host"] == HOST
    assert events[0]["user"] == "analyst"
    assert events[0]["details"] == {"by": "analyst"}

    # a decision, not a guard action
    assert fake.calls == []


def test_watch_custom_analyst_user(client):
    inc_id = _seed_incident(client, time.time())
    client.app.state.guard = FakeGuard()
    r = client.post(f"/incidents/{inc_id}/watch", json={"user": "soc_jane"})
    assert r.status_code == 200
    ev = client.get("/events", params={"type": "watching"}).json()[0]
    assert ev["user"] == "soc_jane"
    assert ev["details"]["by"] == "soc_jane"


def test_watch_unknown_incident_is_404(client):
    client.app.state.guard = FakeGuard()
    r = client.post("/incidents/inc-nope-1/watch")
    assert r.status_code == 404


# --- dismiss -----------------------------------------------------------------


def test_dismiss_sets_status_records_event_no_guard(client):
    inc_id = _seed_incident(client, time.time())
    fake = FakeGuard()
    client.app.state.guard = fake

    r = client.post(f"/incidents/{inc_id}/dismiss", json={"reason": "known pentest"})
    assert r.status_code == 200
    assert r.json()["status"] == "dismissed"

    events = client.get("/events", params={"type": "dismissed"}).json()
    assert len(events) == 1
    assert events[0]["details"] == {"by": "analyst", "reason": "known pentest"}

    assert fake.calls == []


def test_dismiss_default_reason_is_empty(client):
    inc_id = _seed_incident(client, time.time())
    client.app.state.guard = FakeGuard()
    r = client.post(f"/incidents/{inc_id}/dismiss")
    assert r.status_code == 200
    ev = client.get("/events", params={"type": "dismissed"}).json()[0]
    assert ev["details"] == {"by": "analyst", "reason": ""}


def test_dismiss_unknown_incident_is_404(client):
    client.app.state.guard = FakeGuard()
    r = client.post("/incidents/inc-nope-1/dismiss")
    assert r.status_code == 404


# --- decisions compose (latest-by-ts wins) -----------------------------------


def test_watch_then_contain_then_restore(client):
    inc_id = _seed_incident(client, time.time())
    client.app.state.guard = FakeGuard(ok=True)

    assert client.post(f"/incidents/{inc_id}/watch").json()["status"] == "watching"
    # a later Contain overrides the earlier Watch
    assert client.post(f"/incidents/{inc_id}/contain").json()["status"] == "contained"
    # and a later Restore overrides that
    assert client.post(f"/incidents/{inc_id}/restore").json()["status"] == "restored"
