from fastapi.testclient import TestClient

from mirage.core.api import create_app


def test_console_page_served(tmp_path):
    c = TestClient(create_app(db_path=str(tmp_path / "c.db")))
    r = c.get("/console")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    # Branded, wired to the same-origin incident endpoints, and shows the
    # human-decision buttons.
    assert "MIRAGE" in r.text
    assert "/incidents" in r.text
    assert "CONTAIN" in r.text.upper()
    # Decision panel offers the "keep watching" choice, and the report can be
    # edited by the analyst.
    assert "Keep watching" in r.text
    assert "Edit" in r.text
    # Once approved, the report can be exported / shared to the authority.
    assert "Download" in r.text
    assert "Share" in r.text
    # The "Keep watching" payoff panel is present in the page source.
    assert "Intelligence" in r.text


def test_console_page_endpoints_work_end_to_end(tmp_path):
    # The page is static HTML; confirm every endpoint it fetches works against a
    # seeded DB so a live demo actually populates and the buttons can act.
    c = TestClient(create_app(db_path=str(tmp_path / "c2.db"), seed="ai"))
    assert c.get("/console").status_code == 200
    incs = c.get("/incidents").json()
    assert incs, "seeded DB should produce an incident"
    iid = incs[0]["id"]
    assert c.get(f"/incidents/{iid}/card").status_code == 200
    summary = c.get(f"/incidents/{iid}/summary").json()
    assert summary["summary"].startswith("AI DRAFT")
    assert "nis2" in summary
