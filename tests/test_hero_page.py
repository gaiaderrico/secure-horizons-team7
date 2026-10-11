from fastapi.testclient import TestClient
from mirage.core.api import create_app


def test_hero_page_served(tmp_path):
    c = TestClient(create_app(db_path=str(tmp_path / "h.db")))
    r = c.get("/hero")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "REAL FILES LOST" in r.text.upper()
    assert "/incidents" in r.text


def test_hero_page_consumes_endpoints(tmp_path):
    c = TestClient(create_app(db_path=str(tmp_path / "h2.db")))
    body = c.get("/hero").text
    # it must fetch the three same-origin endpoints it renders from
    assert "/incidents" in body
    assert "/card" in body
    assert "/health/guard" in body
