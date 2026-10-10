"""narrator: after the attack, draft the incident summary and the NIS2 early warning for the analyst.

Both are drafts. They start with "AI DRAFT - pending analyst approval. Not sent." and nothing is sent
anywhere: the analyst reads, edits and approves. The narrator reads the incident, it never acts.

Input is a mirage.contracts.Incident (or its to_dict()). Optionally pass the Manifest (object, dict or
None) so crown jewel ids like "cj1" are shown as file paths.

    summarize_incident(incident, manifest)   -> Markdown text
    nis2_early_warning(incident, manifest)   -> Markdown text

Facts come from the incident, never from the LLM. With MIRAGE_LLM set the model only polishes the
wording, and its text is thrown away if it drops a key fact (files lost, swap time, the banner).
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone

from prepare import llm

LABEL_TEXT = {
    "ai_agent": "AI agent",
    "ai_guided_by_human": "AI agent guided by a human",
    "probably_ai": "probably an AI agent",
    "human_or_script": "a human or a script",
}
DRAFT_BANNER = "AI DRAFT - pending analyst approval. Not sent."


def _as_dict(x):
    if x is None:
        return {}
    if is_dataclass(x) and not isinstance(x, type):
        return asdict(x)
    return dict(x)


def _utc(ts) -> str:
    try:
        return datetime.fromtimestamp(float(ts), timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    except (TypeError, ValueError, OSError):
        return "unknown"


def _facts(incident, manifest=None) -> dict:
    inc = _as_dict(incident)
    man = _as_dict(manifest)
    paths = {c["id"]: c.get("real_path", c["id"]) for c in man.get("crown_jewels", [])}
    name = lambda cj_id: paths.get(cj_id, cj_id)  # noqa: E731
    events = [_as_dict(e) for e in inc.get("events", [])]

    def first(type_):
        return next((e for e in events if e.get("type") == type_), None)

    mine = first("mine_opened")
    swap = first("swap_done")
    src_ip = next((e["details"]["src_ip"] for e in events if e.get("details", {}).get("src_ip")), "unknown")
    user = next((e["user"] for e in events if e.get("user")), "unknown")
    intr = _as_dict(inc.get("intruder"))
    tickets = [e for e in events if e.get("type") == "ticket"]
    objective = inc.get("objective") or (tickets[0]["details"].get("objective", "") if tickets else "")
    protected = len((swap or {}).get("details", {}).get("files", [])) if swap else None
    swap_ms = inc.get("swap_ms")
    if swap_ms is None and swap:
        swap_ms = swap.get("details", {}).get("duration_ms")
    return {
        "id": inc.get("id") or "unknown",
        "host": inc.get("host") or "unknown",
        "user": user, "ip": src_ip,
        "when": _utc((mine or {}).get("ts", inc.get("start_ts"))),
        "mine": (mine or {}).get("details", {}).get("path", "unknown"),
        "swapped": bool(inc.get("swapped", swap is not None)),
        "swap_ms": round(swap_ms) if isinstance(swap_ms, (int, float)) else "unknown",
        "protected": protected if protected is not None else "unknown",
        "fake": [name(c) for c in inc.get("fakes_taken", [])],
        "real_lost_list": [name(c) for c in inc.get("real_files_lost", [])],
        "real_lost": len(inc.get("real_files_lost", [])),
        "label": LABEL_TEXT.get(intr.get("kind", ""), "unknown"),
        "confidence": intr.get("confidence", "unknown"),
        "reasons": intr.get("reasons", []),
        "objective": objective,
        "claims": [_as_dict(c) for c in inc.get("claims", [])],
        "beacons": [{"id": e.get("ref", "?"), "at": _utc(e.get("ts")), "ip": e.get("details", {}).get("src_ip", "?"),
                     "file": name(e.get("details", {}).get("cj_id", "?"))}
                    for e in events if e.get("type") == "beacon_used"],
        "status": inc.get("status", "open"),
    }


def _summary_template(f: dict) -> str:
    lines = [DRAFT_BANNER, "", f"# Incident {f['id']} - summary", ""]
    lines.append(f"At {f['when']}, the decoy file {f['mine']} was opened on {f['host']} by account {f['user']} "
                 f"from {f['ip']}. "
                 + (f"MIRAGE replaced {f['protected']} sensitive files with fakes in {f['swap_ms']} ms."
                    if f["swapped"] else "No swap has happened yet."))
    lines.append("")
    lines.append(f"**Real files lost: {f['real_lost']}.** "
                 + (f"The intruder took {len(f['fake'])} file(s), all fake: " + ", ".join(f["fake"]) + "."
                    if f["fake"] else "No fake file was taken."))
    if f["real_lost_list"]:
        lines.append("Real files opened before the swap: " + ", ".join(f["real_lost_list"]) + ".")
    lines += ["", f"**Intruder:** {f['label']} ({f['confidence']} confidence)."]
    lines += [f"- {r}" for r in f["reasons"]]
    if f["objective"]:
        lines += ["", f"**Declared objective:** {f['objective']}", "", "Claims checked against the logs:"]
        lines += [f"- {c.get('text', '?')}: {c.get('status', 'unverified')}"
                  + (f" ({c['evidence']})" if c.get("evidence") else "") for c in f["claims"]]
    if f["beacons"]:
        lines += ["", "**Stolen data was used:** " + "; ".join(
            f"beacon {b['id']} (from {b['file']}) at {b['at']} from {b['ip']}" for b in f["beacons"])]
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


def summarize_incident(incident, manifest=None, use_llm: bool = True) -> str:
    f = _facts(incident, manifest)
    t = _summary_template(f)
    return _llm_polish(t, f, "incident summary") if use_llm else t


def nis2_early_warning(incident, manifest=None, use_llm: bool = True) -> str:
    f = _facts(incident, manifest)
    t = _nis2_template(f)
    return _llm_polish(t, f, "regulatory early warning") if use_llm else t
