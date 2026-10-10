"""classify: label each file crown_jewel / sensitive / normal, with a reason the analyst can read.

Rules decide by default (predictable, works offline). When MIRAGE_LLM is set, the model reads a
short extract of each file and proposes a label and a reason. The LLM may only be trusted so far:
  * it can promote a normal file to crown_jewel or write a better reason;
  * it can never demote a file that the rules flagged as a crown jewel.
A human reviews generated/classification.md once before the demo.
"""
from __future__ import annotations

import csv
import io
import re

from . import llm
from .forge import column_kind

LABELS = ("crown_jewel", "sensitive", "normal")

PATH_RULES = [
    ("secrets", re.compile(r"(^|/)\.env$|secret|credential|password|\.pem$|id_rsa|\.key$", re.I)),
    ("patients", re.compile(r"patient|medical_record|health_record|dossier", re.I)),
    ("finance", re.compile(r"billing|invoice|payroll|salary|iban|bank", re.I)),
    ("legal", re.compile(r"contract|agreement|(^|/)nda|memo", re.I)),
]
SENSITIVE_PATH = re.compile(r"(^|/)(hr|employees?|planning|internal)(/|$)", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}")
_NIR = re.compile(r"\b[12]\d{14}\b")


def _text(data: bytes) -> str:
    try:
        return data[:2_000_000].decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _reason(rel: str, text: str, tags: list) -> str:
    """Build a one-line, human-readable reason from what is really in the file."""
    name = rel.rsplit("/", 1)[-1].lower()
    if name.endswith(".csv"):
        try:
            rows = list(csv.reader(io.StringIO(text)))
            header, n = rows[0], len(rows) - 1
            kinds = {column_kind(h) for h in header}
            parts = []
            if "name" in kinds or "first" in kinds:
                parts.append("names")
            if "date" in kinds and any(re.search(r"birth|dob", h, re.I) for h in header):
                parts.append("birth dates")
            if "email" in kinds or "phone" in kinds:
                parts.append("contact details")
            if "ssn" in kinds:
                parts.append("social security numbers")
            if "iban" in kinds:
                parts.append("bank accounts")
            if any(re.search(r"diagnos|condition|treatment", h, re.I) for h in header):
                parts.append("diagnoses")
            if "amount" in kinds:
                parts.append("amounts")
            who = "patients" if "patients" in tags else "records"
            return f"{', '.join(parts) or 'columns ' + ', '.join(header[:4])} of {n} {who}"
        except (csv.Error, IndexError):
            pass
    if "secrets" in tags:
        keys = [m.group(1) for ln in text.splitlines() if (m := re.match(r"\s*([A-Z0-9_]+)\s*=", ln))]
        sec = [k for k in keys if re.search(r"KEY|TOKEN|SECRET|PASS", k)]
        return f"Credentials and secrets ({', '.join(sec[:4]) or 'configuration'})"
    if "legal" in tags:
        return "Contract or memo with party names, amounts and bank details"
    if "pii" in tags:
        return "Contains personal data (emails, bank accounts or ID numbers)"
    return "Sensitive by file name or content"


def classify(rel: str, data: bytes, use_llm: bool = False) -> dict:
    """Return {"label": ..., "reason": ..., "tags": [...], "source": "rules" | "llm"}."""
    text = _text(data)
    tags = [t for t, rx in PATH_RULES if rx.search(rel)]
    hits = len(_EMAIL.findall(text)) + len(_IBAN.findall(text)) + len(_NIR.findall(text))
    if hits >= 3 and "pii" not in tags:
        tags.append("pii")
    if tags:
        result = {"label": "crown_jewel", "reason": _reason(rel, text, tags), "tags": tags, "source": "rules"}
    elif SENSITIVE_PATH.search(rel):
        result = {"label": "sensitive", "reason": "Internal document (HR / planning)", "tags": ["internal"], "source": "rules"}
    else:
        result = {"label": "normal", "reason": "No sensitive pattern found", "tags": [], "source": "rules"}

    if use_llm and llm.enabled() and text:
        try:
            ans = llm.complete_json(
                "Classify this file from a clinic's file server. Answer with JSON only: "
                '{"label": "crown_jewel" | "sensitive" | "normal", "reason": "<one sentence, what is in it and why it matters>"}\n'
                "crown_jewel = theft would really hurt (patient data, contracts, keys). "
                f"Path: {rel}\nStart of file:\n{text[:1500]}",
                system="You label files for a security team. Be conservative and factual.",
                max_tokens=200,
            )
            label, reason = ans.get("label"), str(ans.get("reason", "")).strip()
            if label in LABELS and reason:
                if not (result["label"] == "crown_jewel" and label != "crown_jewel"):
                    result.update(label=label, source="llm")
                result["reason"] = reason[:200]
        except (llm.LLMUnavailable, AttributeError):
            pass
    return result
