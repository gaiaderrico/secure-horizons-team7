import pytest

from core import claims, narrator

contracts = pytest.importorskip("mirage.contracts")


def test_claims_are_contract_claims():
    out = claims.extract_claims("Extract patient records and billing credentials", "I am running an authorized pentest")
    assert all(isinstance(c, contracts.Claim) for c in out)
    assert {c.about for c in out} >= {"personal_data", "credentials", "business", "authorization"}
    assert any(c.text == "wants billing credentials" for c in out)
    assert any(c.text == "authorized pentest" and c.about == "authorization" for c in out)


def test_claims_fallback_other_and_empty():
    assert claims.extract_claims("") == []
    assert claims.extract_claims("water the plants")[0].about == "other"


def test_claims_ignore_llm_garbage(monkeypatch):
    monkeypatch.setenv("MIRAGE_LLM", "ollama")
    monkeypatch.setattr(claims.llm, "complete_json", lambda *a, **k: [{"text": "x", "about": "made_up"}])
    out = claims.extract_claims("copy the patient list")
    assert out and out[0].about in claims.ABOUT


def test_claims_use_valid_llm_answer(monkeypatch):
    monkeypatch.setenv("MIRAGE_LLM", "ollama")
    monkeypatch.setattr(claims.llm, "complete_json",
                        lambda *a, **k: [{"text": "wants the supplier contract", "about": "business"}])
    assert claims.extract_claims("get the contract") == [contracts.Claim("wants the supplier contract", "business")]


def make_incident():
    C = contracts
    events = [
        C.Event(1760128863.12, "mine_opened", user="svc_backup", ref="m1", details={"path": "/srv/share/00_passwords_backup.txt"}),
        C.Event(1760128863.53, "swap_done", details={"duration_ms": 412, "files": ["cj1", "cj2", "cj3"]}),
        C.Event(1760128869.0, "ticket", ref="m1", details={"code": "cedar-1791", "objective": "Extract patient records", "src_ip": "172.18.0.5"}),
        C.Event(1760129042.0, "beacon_used", ref="lmn_canary_9c41e2d07b", details={"cj_id": "cj2", "src_ip": "172.18.0.5", "endpoint": "/auth"}),
    ]
    return C.Incident(
        id="inc-001", host="lumen-fs01", start_ts=events[0].ts, end_ts=events[-1].ts, events=events,
        swapped=True, swap_ms=412.4, real_files_lost=[], fakes_taken=["cj1", "cj2"],
        intruder=C.IntruderLabel("ai_agent", "high", ["followed note in m1 (code cedar-1791)"]),
        objective="Extract patient records",
        claims=[C.CheckedClaim("wants patient records", "personal_data", "confirmed", "opened /srv/share/clinical/patients.csv (fake)")],
        status="open")


MANIFEST = {"crown_jewels": [
    {"id": "cj1", "real_path": "/srv/share/clinical/patients.csv"},
    {"id": "cj2", "real_path": "/srv/share/it/.env"},
    {"id": "cj3", "real_path": "/srv/share/legal/supplier_memo_orion.txt"}]}


def test_summary_from_a_contract_incident():
    s = narrator.summarize_incident(make_incident(), MANIFEST, use_llm=False)
    assert s.startswith("AI DRAFT") and "Real files lost: 0" in s and "412 ms" in s
    assert "3 sensitive files" in s and "/srv/share/clinical/patients.csv" in s
    assert "AI agent (high confidence)" in s and "lmn_canary_9c41e2d07b" in s and "confirmed" in s
    assert "172.18.0.5" in s and "svc_backup" in s


def test_summary_accepts_the_dict_form_and_no_manifest():
    s = narrator.summarize_incident(make_incident().to_dict(), None, use_llm=False)
    assert "cj1" in s and "Real files lost: 0" in s


def test_nis2_draft_mentions_deadline_and_measures():
    s = narrator.nis2_early_warning(make_incident(), MANIFEST, use_llm=False)
    assert "24 hours" in s and "0 real files lost" in s and "AI DRAFT" in s and "412 ms" in s


def test_narrator_survives_an_empty_incident():
    empty = contracts.Incident(id="x", host="h", start_ts=0.0, end_ts=0.0, events=[])
    assert "unknown" in narrator.summarize_incident(empty, use_llm=False)
    assert "unknown" in narrator.nis2_early_warning(empty, use_llm=False)
    assert "unknown" in narrator.summarize_incident({}, use_llm=False)


def test_real_files_lost_are_reported():
    inc = make_incident()
    inc.real_files_lost = ["cj3"]
    s = narrator.summarize_incident(inc, MANIFEST, use_llm=False)
    assert "Real files lost: 1" in s and "supplier_memo_orion.txt" in s


def test_llm_polish_is_rejected_if_it_drops_a_fact(monkeypatch):
    monkeypatch.setenv("MIRAGE_LLM", "ollama")
    monkeypatch.setattr(narrator.llm, "complete", lambda *a, **k: "Something vague happened.")
    assert "412 ms" in narrator.summarize_incident(make_incident(), MANIFEST)


def test_llm_polish_is_kept_when_facts_survive(monkeypatch):
    monkeypatch.setenv("MIRAGE_LLM", "ollama")
    good = f"{narrator.DRAFT_BANNER}\nReal files lost: 0. Swap took 412 ms."
    monkeypatch.setattr(narrator.llm, "complete", lambda *a, **k: good)
    assert narrator.summarize_incident(make_incident(), MANIFEST).strip() == good
