from fastapi.testclient import TestClient

from mirage.core.api import create_app


def test_report_page_served(tmp_path):
    c = TestClient(create_app(db_path=str(tmp_path / "r.db")))
    r = c.get("/report")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    # Branded, and wired to the same-origin incident endpoints it renders.
    assert "MIRAGE" in r.text
    assert "/incidents" in r.text


def test_report_page_renders_seeded_incident_endpoints(tmp_path):
    # The page is static HTML; confirm the endpoints it fetches work end-to-end
    # so a demo against a seeded DB actually populates.
    c = TestClient(create_app(db_path=str(tmp_path / "r2.db"), seed="ai"))
    assert c.get("/report").status_code == 200
    incs = c.get("/incidents").json()
    assert incs, "seeded DB should produce an incident"
    iid = incs[0]["id"]
    assert c.get(f"/incidents/{iid}/card").status_code == 200
    summary = c.get(f"/incidents/{iid}/summary").json()
    assert summary["summary"].startswith("AI DRAFT")
    assert "nis2" in summary
