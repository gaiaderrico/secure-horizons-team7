from fastapi.testclient import TestClient
from mirage.core.api import create_app


def test_dashboard_page_served(tmp_path):
    c = TestClient(create_app(db_path=str(tmp_path / "v.db")))
    r = c.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "MIRAGE" in r.text and "/incidents" in r.text
