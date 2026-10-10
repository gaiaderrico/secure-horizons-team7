import pytest
from fastapi.testclient import TestClient

from mirage import fakes
from mirage.contracts import HOST
from mirage.core.api import create_app

MINE = {"ts": fakes.T0, "type": "mine_opened", "ref": "m1",
        "details": {"path": "/srv/share/00_passwords_backup.txt"}}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "core.db")))


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_post_single_event_defaults(client):
    r = client.post("/events", json={"ts": 1.5, "type": "command"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and len(body["ids"]) == 1
    [e] = client.get("/events").json()
    assert e == {"ts": 1.5, "type": "command", "host": HOST, "user": "", "ref": "", "details": {}}


def test_post_list_of_events(client):
    batch = [{"ts": 1.0 + i, "type": "command", "user": "svc_backup", "details": {"cmd": f"c{i}"}}
             for i in range(3)]
    r = client.post("/events", json=batch)
    assert r.status_code == 200 and len(r.json()["ids"]) == 3
    assert [e["details"]["cmd"] for e in client.get("/events").json()] == ["c0", "c1", "c2"]


@pytest.mark.parametrize("bad", [
    {"ts": 1.0, "type": "not_a_type"},
    {"type": "command"},  # ts missing
    [{"ts": 1.0, "type": "command"}, {"ts": 2.0, "type": "nope"}],
])
def test_invalid_event_422(client, bad):
    assert client.post("/events", json=bad).status_code == 422
    assert client.get("/events").json() == []


def test_get_events_filters(client):
    client.post("/admin/seed")
    all_ev = client.get("/events").json()
    mines = client.get("/events", params={"type": "mine_opened"}).json()
    assert len(mines) == 1
    t = mines[0]["ts"]
    later = client.get("/events", params={"since": t}).json()
    assert 0 < len(later) < len(all_ev) and all(e["ts"] >= t for e in later)
    cmds = client.get("/events", params={"since": t, "type": "command"}).json()
    assert cmds and all(e["type"] == "command" for e in cmds)


def test_reset(client):
    client.post("/events", json=MINE)
    assert client.post("/admin/reset").json() == {"ok": True}
    assert client.get("/events").json() == []
    assert client.get("/incidents").json() == []


@pytest.mark.parametrize("scenario,factory", [
    ("ai", fakes.ai_attack_events),
    ("guided", fakes.guided_ai_attack_events),
    ("script", fakes.script_attack_events),
    ("human", fakes.human_attack_events),
])
def test_seed_scenarios(client, scenario, factory):
    r = client.post("/admin/seed", params={"scenario": scenario})
    assert r.status_code == 200
    assert len(r.json()["ids"]) == len(factory())
    assert len(client.get("/events").json()) == len(factory())


def test_seed_unknown_scenario_400(client):
    assert client.post("/admin/seed", params={"scenario": "aliens"}).status_code == 400


def test_seed_on_startup_only_if_empty(tmp_path):
    db = str(tmp_path / "core.db")
    n = len(fakes.ai_attack_events())
    c = TestClient(create_app(db_path=db, seed="ai"))
    assert len(c.get("/events").json()) == n
    c2 = TestClient(create_app(db_path=db, seed="ai"))  # restart: not seeded twice
    assert len(c2.get("/events").json()) == n


def test_no_incidents_without_trigger(client):
    client.post("/events", json={"ts": 1.0, "type": "command", "details": {"cmd": "id"}})
    assert client.get("/incidents").json() == []


def test_incidents_contain_posted_mine(client):
    client.post("/events", json=MINE)
    incs = client.get("/incidents").json()
    assert isinstance(incs, list) and len(incs) >= 1
    assert all(isinstance(i, dict) for i in incs)
    found = [i for i in incs
             if any(e["type"] == "mine_opened" and e["ref"] == "m1" for e in i["events"])]
    assert found
    inc = found[0]
    assert inc["host"] == HOST
    assert client.get(f"/incidents/{inc['id']}").json()["id"] == inc["id"]


def test_incidents_after_seed_ai(client):
    client.post("/admin/seed", params={"scenario": "ai"})
    incs = client.get("/incidents").json()
    assert len(incs) >= 1
    assert any(e["type"] == "mine_opened" for i in incs for e in i["events"])
    for key in ("id", "host", "start_ts", "end_ts", "events", "status"):
        assert key in incs[0]


def test_incident_404(client):
    client.post("/events", json=MINE)
    assert client.get("/incidents/inc-nope-0").status_code == 404
