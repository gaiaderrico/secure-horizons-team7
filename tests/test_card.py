from fastapi.testclient import TestClient
from mirage.core.api import create_app
from mirage.core.card import score_incident, attack_timeline, attacker_cost
from mirage.core.incidents import build_incidents
from mirage import fakes


def _client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "c.db")))


def test_severity_levels():
    ai = build_incidents(fakes.ai_attack_events())[0]
    assert score_incident(ai)["level"] == 4          # beacon used
    human = build_incidents(fakes.human_attack_events())[0]
    s = score_incident(human)
    assert s["level"] == 4                            # real file exposed before swap
    assert any("real file" in r for r in s["reasons"])
    script = build_incidents(fakes.script_attack_events())[0]
    assert score_incident(script)["level"] == 1       # no crown jewel touched, script


def test_attack_timeline_tags():
    ai = build_incidents(fakes.ai_attack_events())[0]
    tl = attack_timeline(ai.events)
    kinds = {e["type"]: e for e in tl}
    assert kinds["command"]["technique_id"] == "T1059"
    assert kinds["beacon_used"]["technique_id"] == "T1078"
    assert kinds["swap_done"]["defensive"] is True


def test_attacker_cost():
    ai = build_incidents(fakes.ai_attack_events())[0]
    c = attacker_cost(ai)
    assert c["fake_files_taken"] == 3 and c["commands"] >= 1 and c["seconds_on_fakes"] > 0


def test_card_endpoint(tmp_path):
    cl = _client(tmp_path)
    cl.post("/admin/seed?scenario=ai")
    inc_id = cl.get("/incidents").json()[0]["id"]
    r = cl.get(f"/incidents/{inc_id}/card")
    assert r.status_code == 200
    b = r.json()
    assert b["severity"]["level"] == 4
    assert b["intruder"]["kind"] == "ai_agent"
    assert any(c.get("status") == "confirmed" for c in b["claims"])
    assert cl.get("/incidents/nope/card").status_code == 404
