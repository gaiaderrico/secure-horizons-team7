"""Guard heartbeat: core records pings and raises the GUARD SILENT alarm when they stop."""

import pytest
from fastapi.testclient import TestClient

from mirage.contracts import HOST
from mirage.core.api import create_app
from mirage.core.heartbeat import guard_health


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "hb.db")))


# --- /heartbeat + /health/guard over HTTP -----------------------------------


def test_heartbeat_then_health_shows_alive(client):
    assert client.post("/heartbeat", json={}).json() == {"ok": True}
    h = client.get("/health/guard").json()
    assert h["host"] == HOST
    assert h["alive"] is True and h["alarm"] is False
    assert h["last_seen"] is not None and h["silent_for_s"] is not None
    assert h["silent_for_s"] < 5


def test_heartbeat_accepts_explicit_host_and_ts(client):
    client.post("/heartbeat", json={"host": "other-host", "ts": 123.0})
    h = client.get("/health/guard", params={"host": "other-host", "max_silence_s": 15}).json()
    assert h["last_seen"] == 123.0
    # 123.0 is far in the past -> silent -> alarm
    assert h["alarm"] is True and h["alive"] is False


def test_health_alarms_when_no_heartbeat_ever(client):
    h = client.get("/health/guard").json()
    assert h["alive"] is False and h["alarm"] is True
    assert h["last_seen"] is None and h["silent_for_s"] is None


def test_stale_heartbeat_alarms(client):
    # a heartbeat older than max_silence_s is treated as the guard going silent
    client.post("/heartbeat", json={"ts": 100.0})
    h = client.get("/health/guard", params={"max_silence_s": 1}).json()
    assert h["alarm"] is True and h["alive"] is False
    assert h["last_seen"] == 100.0 and h["silent_for_s"] > 1


# --- guard_health pure unit cases -------------------------------------------


def test_guard_health_fresh():
    h = guard_health(last_seen=100.0, now=105.0, max_silence_s=15)
    assert h == {"alive": True, "last_seen": 100.0, "silent_for_s": 5.0, "alarm": False}


def test_guard_health_stale():
    h = guard_health(last_seen=100.0, now=130.0, max_silence_s=15)
    assert h["alarm"] is True and h["alive"] is False and h["silent_for_s"] == 30.0


def test_guard_health_never_seen():
    assert guard_health(last_seen=None, now=130.0, max_silence_s=15) == {
        "alive": False, "last_seen": None, "silent_for_s": None, "alarm": True}


def test_guard_health_boundary_not_alarm_at_exactly_max():
    # exactly at the threshold is still alive (alarm only when strictly older)
    assert guard_health(last_seen=100.0, now=115.0, max_silence_s=15)["alarm"] is False
    assert guard_health(last_seen=100.0, now=115.001, max_silence_s=15)["alarm"] is True
