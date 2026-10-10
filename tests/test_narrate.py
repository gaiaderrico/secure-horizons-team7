from fastapi.testclient import TestClient
from mirage.core.api import create_app


def _client(tmp_path):
    app = create_app(db_path=str(tmp_path / "n.db"))
    return TestClient(app)


def test_summary_and_nis2_drafts(tmp_path):
    c = _client(tmp_path)
    c.post("/admin/seed?scenario=ai")
    inc_id = c.get("/incidents").json()[0]["id"]
    r = c.get(f"/incidents/{inc_id}/summary")
    assert r.status_code == 200
    body = r.json()
    # Both drafts carry the "AI DRAFT - pending approval" banner (nothing is sent).
    assert "AI DRAFT" in body["summary"]
    assert "AI DRAFT" in body["nis2"]
    # The summary reflects the enriched incident (AI agent, 0 real files lost).
    assert "AI agent" in body["summary"]
    assert "0" in body["summary"]


def test_summary_unknown_incident_404(tmp_path):
    c = _client(tmp_path)
    assert c.get("/incidents/nope/summary").status_code == 404
