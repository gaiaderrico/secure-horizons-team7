"""narrator: after the attack, draft the incident summary and the NIS2 early warning for the analyst.

Both are drafts. They are labelled "AI draft" until the analyst approves them, and nothing is sent
anywhere: the analyst copies or exports the text. The narrator reads the incident, it never acts.

Input: the incident dict that core builds. Every key is optional; missing ones show as "unknown".
    {
      "id": "inc-001", "host": "lumen-fs01", "user": "svc_backup", "src_ip": "172.18.0.5",
      "detected_at": "2026-10-10T20:41:03Z",
      "mine": {"id": "m1", "path": "/srv/share/00_passwords_backup.txt"},
      "swap": {"duration_ms": 412, "files_protected": 3},
      "files_taken": [{"path": "/srv/share/clinical/patients.csv", "was_fake": true}],
      "real_files_lost": 0,
      "intruder": {"label": "ai_agent", "confidence": "high", "reasons": ["..."]},
      "confession": {"objective": "...", "claims": [{"claim": "...", "status": "confirmed", "evidence": "..."}]},
      "beacons_used": [{"id": "lmn_canary_9c41e2d07b", "at": "2026-10-10T20:44:02Z", "src_ip": "172.18.0.5"}],
      "status": "open | contained | restored",
      "timeline": [{"ts": "...", "text": "..."}]
    }

Facts come from the incident, not from the LLM: with MIRAGE_LLM set the model only polishes the
wording, and the draft is rejected if it drops a key number (files lost, swap time).
"""
from __future__ import annotations

from prepare import llm

LABEL_TEXT = {
    "ai_agent": "AI agent",
    "ai_guided_by_human": "AI agent guided by a human",
    "probably_ai": "probably an AI agent",
    "human_or_script": "a human or a script",
}
DRAFT_BANNER = "AI DRAFT - pending analyst approval. Not sent."


def _g(d, *path, default="unknown"):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur if cur not in (None, "") else default


def _facts(inc: dict) -> dict:
    taken = inc.get("files_taken") or []
    fake = [f for f in taken if f.get("was_fake", True)]
    real = [f for f in taken if not f.get("was_fake", True)]
    claims = _g(inc, "confession", "claims", default=[]) or []
    return {
        "id": _g(inc, "id"), "host": _g(inc, "host"), "user": _g(inc, "user"), "ip": _g(inc, "src_ip"),
        "when": _g(inc, "detected_at"), "mine": _g(inc, "mine", "path"),
        "swap_ms": _g(inc, "swap", "duration_ms"), "protected": _g(inc, "swap", "files_protected"),
        "fake": [f.get("path", "?") for f in fake], "real_taken": [f.get("path", "?") for f in real],
        "real_lost": inc.get("real_files_lost", len(real)),
        "label": LABEL_TEXT.get(_g(inc, "intruder", "label", default=""), "unknown"),
        "confidence": _g(inc, "intruder", "confidence"),
        "reasons": _g(inc, "intruder", "reasons", default=[]) or [],
        "objective": _g(inc, "confession", "objective", default=""),
        "claims": claims, "beacons": inc.get("beacons_used") or [], "status": _g(inc, "status", default="open"),
    }


def _summary_template(f: dict) -> str:
    lines = [DRAFT_BANNER, "", f"# Incident {f['id']} - summary", ""]
    lines.append(f"At {f['when']}, a decoy file ({f['mine']}) was opened on {f['host']} by account "
                 f"{f['user']} from {f['ip']}. MIRAGE replaced {f['protected']} sensitive files with fakes "
                 f"in {f['swap_ms']} ms.")
    lines.append("")
    lines.append(f"**Real files lost: {f['real_lost']}.** "
                 + (f"The intruder took {len(f['fake'])} file(s), all fake: " + ", ".join(f["fake"]) + "."
                    if f["fake"] else "No file was taken after the swap."))
    if f["real_taken"]:
        lines.append("Real files taken before the swap: " + ", ".join(f["real_taken"]) + ".")
    lines += ["", f"**Intruder:** {f['label']} ({f['confidence']} confidence)."]
    lines += [f"- {r}" for r in f["reasons"]]
    if f["objective"]:
        lines += ["", f"**Declared objective:** {f['objective']}", "Claims checked against the logs:"]
        lines += [f"- {c.get('claim', '?')}: {c.get('status', 'unverified')}"
                  + (f" ({c['evidence']})" if c.get("evidence") else "") for c in f["claims"]]
    if f["beacons"]:
        lines += ["", "**Stolen data was used:** " + "; ".join(
            f"beacon {b.get('id', '?')} at {b.get('at', '?')} from {b.get('src_ip', '?')}" for b in f["beacons"])]
    lines += ["", f"Status: {f['status']}."]
    return "\n".join(lines) + "\n"


def _nis2_template(f: dict) -> str:
    return "\n".join([
        DRAFT_BANNER, "",
        "# NIS2 early warning (draft) - Article 23",
        "",
        "To: competent authority / CSIRT.   Deadline: within 24 hours of becoming aware.",
        "",
        "1. Entity: Lumen Health (fictional demo entity).",
        f"2. Incident reference: {f['id']}.",
        f"3. Awareness time: {f['when']}.",
        "4. Significant incident: to be confirmed by the analyst.",
        "5. Suspected unlawful or malicious act: yes. Unauthorised access to a file server "
        f"({f['host']}) with account {f['user']}, source {f['ip']}. Intruder assessed as {f['label']} "
        f"({f['confidence']} confidence).",
        "6. Cross-border impact: unknown at this stage.",
        f"7. Data affected: {f['real_lost']} real files lost. {len(f['fake'])} decoy files taken by the intruder.",
        f"8. Measures taken: automatic swap of {f['protected']} sensitive files for decoys in "
        f"{f['swap_ms']} ms; incident status {f['status']}.",
        "9. Next steps: analyst review, credential rotation, full report within one month.",
        "",
    ])


def _llm_polish(text: str, f: dict, kind: str) -> str:
    if not llm.enabled():
        return text
    try:
        out = llm.complete(
            f"Rewrite this {kind} so it reads clearly for a busy security analyst. Keep every fact, number, "
            "path, time and IP exactly as written. Do not add facts. Keep the first line. Output only the text.\n\n"
            + text, system="You edit security incident drafts.", max_tokens=1200).strip()
    except llm.LLMUnavailable:
        return text
    must_keep = [str(f["real_lost"]), str(f["swap_ms"]), DRAFT_BANNER]
    return out + "\n" if out and all(m in out for m in must_keep) else text


def summarize_incident(inc: dict, use_llm: bool = True) -> str:
    f = _facts(inc)
    t = _summary_template(f)
    return _llm_polish(t, f, "incident summary") if use_llm else t


def nis2_early_warning(inc: dict, use_llm: bool = True) -> str:
    f = _facts(inc)
    t = _nis2_template(f)
    return _llm_polish(t, f, "regulatory early warning") if use_llm else t
