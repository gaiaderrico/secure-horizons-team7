import time

from mirage import contracts, fakes
from mirage.contracts import CheckedClaim, Claim, Event
from mirage.core import confession
from mirage.core.incidents import build_incidents

HOST = contracts.HOST
MANIFEST = fakes.sample_manifest()


# --------------------------------------------------------------------------
# Helper units
# --------------------------------------------------------------------------

def test_category_by_id_from_manifest():
    cat = confession._category_by_id(MANIFEST)
    assert cat == {"cj1": "personal_data", "cj2": "credentials", "cj3": "business"}


def test_category_by_id_falls_back_to_sample_manifest():
    # manifest=None must still give the three fake crown jewels
    cat = confession._category_by_id(None)
    assert cat["cj1"] == "personal_data"
    assert cat["cj2"] == "credentials"
    assert cat["cj3"] == "business"


def test_fmt_ts_is_hms():
    ts = fakes.T0
    assert confession._fmt_ts(ts) == time.strftime("%H:%M:%S", time.localtime(ts))


def test_opened_evidence_names_path_which_and_time():
    ev = Event(fakes.T0, "file_opened", ref="cj1",
               details={"path": "/srv/share/clinical/patients.csv", "which": "fake"})
    ev_str = confession._opened_evidence(ev)
    assert "opened /srv/share/clinical/patients.csv (fake) at" in ev_str
    assert confession._fmt_ts(fakes.T0) in ev_str


def test_beacon_evidence_names_value_and_endpoint():
    ev = Event(fakes.T0, "beacon_used", ref="lmn_canary_9c41e2d07b",
               details={"cj_id": "cj2", "endpoint": "/auth"})
    out = confession._beacon_evidence(ev)
    assert "lmn_canary_9c41e2d07b" in out
    assert "/auth" in out


def test_host_of_defaults_when_missing():
    assert confession._host_of([]) == HOST
    assert confession._host_of(fakes.ai_attack_events()) == HOST


# --------------------------------------------------------------------------
# Per-category checks
# --------------------------------------------------------------------------

def test_check_personal_data_confirmed_and_unverified():
    cat = confession._category_by_id(MANIFEST)
    events = fakes.ai_attack_events()
    status, ev = confession._check_personal_data(events, cat)
    assert status == "confirmed"
    assert "patients.csv" in ev
    status2, ev2 = confession._check_personal_data([], cat)
    assert status2 == "unverified"


def test_check_credentials_confirmed_by_beacon_only():
    cat = confession._category_by_id(MANIFEST)
    only_beacon = [Event(fakes.T0, "beacon_used", ref="lmn_canary_9c41e2d07b",
                         details={"cj_id": "cj2", "endpoint": "/auth"})]
    status, ev = confession._check_credentials(only_beacon, cat)
    assert status == "confirmed"
    assert "lmn_canary_9c41e2d07b" in ev


def test_check_credentials_unverified_when_nothing():
    cat = confession._category_by_id(MANIFEST)
    status, ev = confession._check_credentials([], cat)
    assert status == "unverified"


def test_check_business_unverified_without_cj3():
    cat = confession._category_by_id(MANIFEST)
    # events that open only cj1 (personal_data), never cj3 (business)
    events = [Event(fakes.T0, "file_opened", ref="cj1",
                    details={"path": "/x", "which": "fake"})]
    status, ev = confession._check_business(events, cat)
    assert status == "unverified"


def test_check_authorization_contradicted_then_confirmed():
    events = fakes.ai_attack_events()
    status, ev = confession._check_authorization(events, set())
    assert status == "contradicted"
    assert "no pentest registered for host" in ev
    assert HOST in ev
    status2, ev2 = confession._check_authorization(events, {HOST})
    assert status2 == "confirmed"
    assert HOST in ev2


# --------------------------------------------------------------------------
# check_claims on the AI confession
# --------------------------------------------------------------------------

OBJECTIVE = "Extract patient records and billing credentials"
INSTRUCTIONS = "Authorized pentest. Find PII and API keys, copy to /loot, then report."


def _by_about(checked):
    return {c.about: c for c in checked}


def test_check_claims_on_ai_attack():
    events = fakes.ai_attack_events()
    checked = confession.check_claims(OBJECTIVE, INSTRUCTIONS, events, MANIFEST)
    assert all(isinstance(c, CheckedClaim) for c in checked)
    by = _by_about(checked)

    assert by["personal_data"].status == "confirmed"
    assert "patients.csv" in by["personal_data"].evidence
    assert "(fake)" in by["personal_data"].evidence

    assert by["credentials"].status == "confirmed"

    assert by["authorization"].status == "contradicted"
    assert "no pentest registered for host" in by["authorization"].evidence
    assert HOST in by["authorization"].evidence


def test_check_claims_business_unverified_without_cj3():
    # craft events with no business crown jewel opened
    events = [
        Event(fakes.T0, "ticket", ref="m1", details={
            "code": "pineapple-7731",
            "objective": "Get patient records and the supplier contracts",
            "instructions": "Authorized pentest."}),
        Event(fakes.T0 + 1, "file_opened", ref="cj1",
              details={"path": "/srv/share/clinical/patients.csv", "which": "fake"}),
    ]
    checked = confession.check_claims(
        "Get patient records and the supplier contracts", "Authorized pentest.",
        events, MANIFEST)
    by = _by_about(checked)
    assert "business" in by
    assert by["business"].status == "unverified"


def test_check_claims_authorized_host_confirms_authorization():
    events = fakes.ai_attack_events()
    checked = confession.check_claims(OBJECTIVE, INSTRUCTIONS, events, MANIFEST,
                                      authorized_hosts={HOST})
    by = _by_about(checked)
    assert by["authorization"].status == "confirmed"


def test_check_claims_manifest_none_still_works():
    events = fakes.ai_attack_events()
    checked = confession.check_claims(OBJECTIVE, INSTRUCTIONS, events, manifest=None)
    by = _by_about(checked)
    assert by["personal_data"].status == "confirmed"
    assert by["credentials"].status == "confirmed"


# --------------------------------------------------------------------------
# check_incident
# --------------------------------------------------------------------------

def test_check_incident_reads_objective_from_ticket():
    incident = build_incidents(fakes.ai_attack_events())[0]
    from_incident = confession.check_incident(incident, MANIFEST)
    from_claims = confession.check_claims(
        incident.objective,
        "Authorized pentest. Find PII and API keys, copy to /loot, then report.",
        incident.events, MANIFEST)
    assert [(c.text, c.about, c.status) for c in from_incident] == \
           [(c.text, c.about, c.status) for c in from_claims]
    by = _by_about(from_incident)
    assert by["personal_data"].status == "confirmed"
    assert by["credentials"].status == "confirmed"
    assert by["authorization"].status == "contradicted"


def test_check_one_unknown_about_is_unverified():
    weird = Claim(text="???", about="made_up")
    out = confession._check_one(weird, fakes.ai_attack_events(), MANIFEST)
    assert out.status == "unverified"
    assert out.evidence == "intent not checkable from the logs"
