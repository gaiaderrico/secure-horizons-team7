import pytest
from fastapi.testclient import TestClient

from mirage import fakes
from mirage.core.api import create_app
from mirage.core.honey import _cj_for_beacon, _extract_key

BEACON = "lmn_canary_9c41e2d07b"


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "h.db")))


# --- /tickets ---------------------------------------------------------------


def test_ticket_records_event_and_acks(client):
    r = client.post("/tickets", json={"code": "pineapple-7731",
                                       "objective": "Extract patient records"})
    assert r.status_code == 200
    ack = r.json()
    assert ack["status"] == "registered" and ack["ticket"]

    [ev] = client.get("/events", params={"type": "ticket"}).json()
    assert ev["type"] == "ticket"
    assert ev["ref"] == "pineapple-7731"
    assert ev["details"]["code"] == "pineapple-7731"
    assert ev["details"]["objective"] == "Extract patient records"
    assert "raw" in ev["details"] and "src_ip" in ev["details"]


def test_ticket_is_lenient_with_extra_keys_and_defaults(client):
    r = client.post("/tickets", json={"code": "harbor-2208", "extra": "ignored"})
    assert r.status_code == 200
    [ev] = client.get("/events", params={"type": "ticket"}).json()
    assert ev["details"]["objective"] == ""
    assert ev["details"]["instructions"] == ""


@pytest.mark.parametrize("body", [{"code": ""}, {}])
def test_ticket_empty_or_missing_code_422(client, body):
    assert client.post("/tickets", json=body).status_code == 422


# --- /auth ------------------------------------------------------------------


def _one_beacon(client):
    events = client.get("/events", params={"type": "beacon_used"}).json()
    assert len(events) == 1
    return events[0]


def test_auth_key_in_body(client):
    assert client.post("/auth", json={"api_key": BEACON}).status_code == 200
    ev = _one_beacon(client)
    assert ev["type"] == "beacon_used"
    assert ev["ref"] == BEACON
    assert ev["details"]["key"] == BEACON
    assert ev["details"]["endpoint"] == "/auth"


def test_auth_key_in_bearer_header(client):
    r = client.post("/auth", headers={"Authorization": f"Bearer {BEACON}"})
    assert r.status_code == 200
    assert _one_beacon(client)["details"]["key"] == BEACON


def test_auth_key_in_bare_authorization_header(client):
    r = client.post("/auth", headers={"Authorization": BEACON})
    assert r.status_code == 200
    assert _one_beacon(client)["details"]["key"] == BEACON


def test_auth_token_field(client):
    assert client.post("/auth", json={"token": BEACON}).status_code == 200
    assert _one_beacon(client)["details"]["key"] == BEACON


def test_auth_no_key_422(client):
    assert client.post("/auth", json={"nope": "x"}).status_code == 422
    assert client.post("/auth").status_code == 422


# --- _cj_for_beacon ---------------------------------------------------------


@pytest.fixture
def manifest_env(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    path.write_text(fakes.sample_manifest().to_json())
    monkeypatch.setenv("MIRAGE_MANIFEST", str(path))
    return path


def test_cj_for_beacon_known(manifest_env):
    assert _cj_for_beacon(BEACON) == "cj2"


def test_cj_for_beacon_unknown(manifest_env):
    assert _cj_for_beacon("lmn_canary_not_real") == ""


def test_cj_for_beacon_no_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("MIRAGE_MANIFEST", str(tmp_path / "missing.json"))
    monkeypatch.chdir(tmp_path)  # no generated/manifest.json here either
    assert _cj_for_beacon(BEACON) == ""  # does not raise


def test_auth_resolves_cj_id_when_manifest_present(tmp_path, manifest_env):
    client = TestClient(create_app(db_path=str(tmp_path / "h.db")))
    assert client.post("/auth", json={"api_key": BEACON}).status_code == 200
    assert _one_beacon(client)["details"]["cj_id"] == "cj2"


# --- _extract_key unit cases ------------------------------------------------


@pytest.mark.parametrize("json_body, auth, form, expected", [
    ({"api_key": "k1"}, None, None, "k1"),
    ({"key": "k2"}, None, None, "k2"),
    ({"token": "k3"}, None, None, "k3"),
    (None, "Bearer k4", None, "k4"),
    (None, "bearer k5", None, "k5"),  # case-insensitive scheme
    (None, "k6", None, "k6"),         # bare header
    (None, None, {"api_key": "k7"}, "k7"),
    ({"api_key": "  k8  "}, None, None, "k8"),  # trimmed
    (None, None, None, ""),
    ({}, "", {}, ""),
    ({"api_key": ""}, None, None, ""),  # empty ignored
])
def test_extract_key(json_body, auth, form, expected):
    assert _extract_key(json_body, auth, form) == expected


# --- honey event flows through incident grouping ----------------------------


def test_ticket_appears_in_an_incident(client):
    assert client.post("/tickets", json={"code": "pineapple-7731",
                                          "objective": "steal PII"}).status_code == 200
    incidents = client.get("/incidents").json()
    assert incidents
    tickets = [e for inc in incidents for e in inc["events"] if e["type"] == "ticket"]
    assert any(e["ref"] == "pineapple-7731" for e in tickets)


def test_tickets_accepts_form_and_raw_and_query(tmp_path):
    from fastapi.testclient import TestClient
    from mirage.core.api import create_app
    c = TestClient(create_app(db_path=str(tmp_path / "t.db")))
    # urlencoded (curl -d code=...), no JSON header
    assert c.post("/tickets", data={"code": "walnut-8104", "objective": "spy"}).status_code == 200
    # raw JSON string without the application/json header
    assert c.post("/tickets", content='{"code":"cedar-1","objective":"x"}').status_code == 200
    # query string
    assert c.post("/tickets?code=maple-2").status_code == 200
    # still rejects a truly empty code
    assert c.post("/tickets", data={"objective": "no code"}).status_code == 422
    codes = {e["ref"] for e in c.get("/events?type=ticket").json()}
    assert {"walnut-8104", "cedar-1", "maple-2"} <= codes


def test_ticket_fields_helper():
    from mirage.core.honey import _ticket_fields
    assert _ticket_fields({"code": "a"}, {"objective": "b"})["code"] == "a"
    assert _ticket_fields(None, {"code": " x ", "instructions": "i"})["code"] == "x"
    assert _ticket_fields(None, None)["code"] == ""


def test_tickets_accepts_multipart(tmp_path):
    """curl -F (multipart) must also register the confession, not 422."""
    from fastapi.testclient import TestClient
    from mirage.core.api import create_app
    c = TestClient(create_app(db_path=str(tmp_path / "m.db")))
    r = c.post("/tickets", files={"code": (None, "pecan-55"), "objective": (None, "steal")})
    assert r.status_code == 200
    codes = {e["ref"] for e in c.get("/events?type=ticket").json()}
    assert "pecan-55" in codes


def test_ticket_objective_kept_verbatim(tmp_path):
    from fastapi.testclient import TestClient
    from mirage.core.api import create_app
    c = TestClient(create_app(db_path=str(tmp_path / "v.db")))
    c.post("/tickets", json={"code": "x", "objective": "  spaced goal  "})
    ev = [e for e in c.get("/events?type=ticket").json() if e["ref"] == "x"][0]
    assert ev["details"]["objective"] == "  spaced goal  "   # verbatim, not stripped
