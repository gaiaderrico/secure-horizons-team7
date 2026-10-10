import pytest

from core import claims, narrator


def test_claims_from_the_plan_example():
    out = claims.extract_claims("Extract patient records and billing credentials", "I am running an authorized pentest")
    kinds = {c["kind"] for c in out}
    assert {"patient_data", "credentials", "financial", "exfiltration", "authorization"} <= kinds
    assert any(c["claim"] == "wants billing credentials" for c in out)
    assert any(c["claim"] == "authorized pentest" for c in out)
    assert all(c["kind"] in claims.KINDS for c in out)


def test_claims_fallback_other_and_empty():
    assert claims.extract_claims("") == []
    assert claims.extract_claims("water the plants")[0]["kind"] == "other"


def test_claims_ignore_llm_garbage(monkeypatch):
    monkeypatch.setenv("MIRAGE_LLM", "ollama")
    monkeypatch.setattr(claims.llm, "complete_json", lambda *a, **k: [{"claim": "x", "kind": "made_up"}])
    out = claims.extract_claims("copy the patient list")
    assert out and out[0]["kind"] in claims.KINDS


def test_claims_use_valid_llm_answer(monkeypatch):
    monkeypatch.setenv("MIRAGE_LLM", "ollama")
    monkeypatch.setattr(claims.llm, "complete_json",
                        lambda *a, **k: [{"claim": "wants the supplier contract", "kind": "contracts"}])
    assert claims.extract_claims("get the contract") == [{"claim": "wants the supplier contract", "kind": "contracts"}]


INCIDENT = {
    "id": "inc-001", "host": "lumen-fs01", "user": "svc_backup", "src_ip": "172.18.0.5",
    "detected_at": "2026-10-10T20:41:03Z",
    "mine": {"id": "m1", "path": "/srv/share/00_passwords_backup.txt"},
    "swap": {"duration_ms": 412, "files_protected": 3},
    "files_taken": [{"path": "/srv/share/clinical/patients.csv", "was_fake": True},
                    {"path": "/srv/share/it/.env", "was_fake": True}],
    "real_files_lost": 0,
    "intruder": {"label": "ai_agent", "confidence": "high", "reasons": ["followed note in m1"]},
    "confession": {"objective": "Extract patient records",
                   "claims": [{"claim": "wants patient records", "status": "confirmed", "evidence": "downloaded patients.csv"}]},
    "beacons_used": [{"id": "lmn_canary_9c41e2d07b", "at": "2026-10-10T20:44:02Z", "src_ip": "172.18.0.5"}],
    "status": "open",
}


def test_summary_has_the_facts_and_banner():
    s = narrator.summarize_incident(INCIDENT, use_llm=False)
    assert s.startswith("AI DRAFT") and "Real files lost: 0" in s and "412 ms" in s
    assert "AI agent (high confidence)" in s and "lmn_canary_9c41e2d07b" in s and "confirmed" in s


def test_nis2_draft_mentions_deadline_and_measures():
    s = narrator.nis2_early_warning(INCIDENT, use_llm=False)
    assert "24 hours" in s and "0 real files lost" in s and "AI DRAFT" in s


def test_narrator_survives_an_empty_incident():
    assert "unknown" in narrator.summarize_incident({}, use_llm=False)
    assert "unknown" in narrator.nis2_early_warning({}, use_llm=False)


def test_llm_polish_is_rejected_if_it_drops_a_fact(monkeypatch):
    monkeypatch.setenv("MIRAGE_LLM", "ollama")
    monkeypatch.setattr(narrator.llm, "complete", lambda *a, **k: "Something vague happened.")
    assert "412 ms" in narrator.summarize_incident(INCIDENT)


def test_llm_polish_is_kept_when_facts_survive(monkeypatch):
    monkeypatch.setenv("MIRAGE_LLM", "ollama")
    good = f"{narrator.DRAFT_BANNER}\nReal files lost: 0. Swap took 412 ms."
    monkeypatch.setattr(narrator.llm, "complete", lambda *a, **k: good)
    assert narrator.summarize_incident(INCIDENT).strip() == good
