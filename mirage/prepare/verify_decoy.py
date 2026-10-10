"""verify_decoy: code checks that a fake twin is safe to put in place of the real file.

The forger (code or LLM) can make mistakes, such as copying a real value by accident. This module is
the gate: a twin that fails any check is rejected and never staged. It is independent of how the twin
was produced.

Checks
  not_identical   the twin is not a copy of the real file
  parses          same format: valid CSV with the same header / valid .env lines / UTF-8 text
  same_shape      same columns and row count (CSV), same keys in order (.env), similar length (text)
  no_real_values  no identifying value of the real file appears in the twin
  beacons         every beacon announced for this twin really is inside it

CLI:  python -m mirage.prepare.verify_decoy REAL FAKE [--beacon VALUE ...]
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from dataclasses import dataclass, field

from .forge import (COMMON, ENV_LINE, IDENTITY_KINDS, SECRET_KEY, TEXT_TOKEN, URL_KEY,
                    column_kind, detect_kind)


@dataclass
class Report:
    name: str
    checks: dict = field(default_factory=dict)  # check name -> True/False
    problems: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(self.checks.values())

    def fail(self, check: str, msg: str) -> None:
        self.checks[check] = False
        self.problems.append(f"{check}: {msg}")

    def passed(self, check: str) -> None:
        self.checks.setdefault(check, True)


# --------------------------------------------------------------------------------------
# leak detection, by format
# --------------------------------------------------------------------------------------
def _csv_leaks(real: bytes, fake: bytes) -> list:
    r = list(csv.reader(io.StringIO(real.decode("utf-8"))))
    f = list(csv.reader(io.StringIO(fake.decode("utf-8"))))
    if not r or not f:
        return []
    leaks = []
    for i, h in enumerate(r[0]):
        if column_kind(h) in IDENTITY_KINDS:
            real_vals = {row[i] for row in r[1:] if i < len(row) and row[i]}
            fake_vals = {row[i] for row in f[1:] if i < len(row) and row[i]}
            leaks += [f"{h}={v}" for v in sorted(real_vals & fake_vals)]
    real_rows = {tuple(row) for row in r[1:]}
    leaks += [f"duplicate row starting {row[0]}" for row in map(tuple, f[1:]) if row in real_rows]
    return leaks


def _env_leaks(real: bytes, fake: bytes) -> list:
    leaks = []
    fake_text = fake.decode("utf-8")
    for line in real.decode("utf-8").splitlines():
        m = ENV_LINE.match(line)
        if not m or line.lstrip().startswith("#"):
            continue
        key, raw = m.group(2), m.group(4).strip("\"'")
        if (SECRET_KEY.search(key) or "://" in raw) and len(raw) >= 6 and raw in fake_text:
            leaks.append(f"{key} value")
        if "://" in raw and not URL_KEY.search(key):
            m2 = re.match(r"^[a-z0-9+.-]+://(?:[^:@/]*(?::[^@/]*)?@)?([^:/]+)", raw, re.I)
            if m2 and m2.group(1) in fake_text:
                leaks.append(f"{key} host")
    return leaks


def _text_leaks(real: bytes, fake: bytes) -> list:
    real_t, fake_t = real.decode("utf-8"), fake.decode("utf-8")
    leaks = set()
    for m in TEXT_TOKEN.finditer(real_t):
        kind, s = m.lastgroup, m.group(0)
        if kind == "date" or (kind == "cap" and s.lower() in COMMON):
            continue
        if re.search(rf"(?<![\w@]){re.escape(s)}(?!\w)", fake_t):
            leaks.add(s)
    return sorted(leaks)


_GENERIC_TOKEN = re.compile(r"[\w.@+-]{8,}")
_DATEISH = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{2}/\d{2}/\d{4}$")


def _generic_leaks(real: bytes, fake: bytes) -> list:
    """Format-blind safety net: any long token with a digit (ids, keys, phones) copied verbatim."""
    real_toks = {t for t in _GENERIC_TOKEN.findall(real.decode("utf-8"))
                 if any(c.isdigit() for c in t) and not _DATEISH.match(t)}
    fake_toks = set(_GENERIC_TOKEN.findall(fake.decode("utf-8")))
    return sorted(real_toks & fake_toks)


# --------------------------------------------------------------------------------------
# main entry
# --------------------------------------------------------------------------------------
def verify_decoy(name: str, real: bytes, fake: bytes, beacons: list | None = None) -> Report:
    rep = Report(name)
    kind = detect_kind(name)

    if real == fake:
        rep.fail("not_identical", "twin is identical to the real file")
    rep.passed("not_identical")

    try:
        real_t, fake_t = real.decode("utf-8"), fake.decode("utf-8")
    except UnicodeDecodeError:
        rep.fail("parses", "not UTF-8 text")
        return rep

    if kind == "csv":
        try:
            r = list(csv.reader(io.StringIO(real_t)))
            f = list(csv.reader(io.StringIO(fake_t)))
        except csv.Error as e:
            rep.fail("parses", f"csv error: {e}")
            return rep
        if not f or f[0] != r[0]:
            rep.fail("parses", "header differs from the real file")
        elif any(len(row) != len(r[0]) for row in f[1:]):
            rep.fail("parses", "a row has the wrong number of columns")
        rep.passed("parses")
        if len(f) != len(r):
            rep.fail("same_shape", f"{len(f) - 1} rows instead of {len(r) - 1}")
        rep.passed("same_shape")
        leaks = _csv_leaks(real, fake)
    elif kind == "env":
        def keys(t):
            return [m.group(2) for ln in t.splitlines() if (m := ENV_LINE.match(ln)) and not ln.lstrip().startswith("#")]
        if keys(real_t) != keys(fake_t):
            rep.fail("same_shape", "keys differ or are in another order")
        rep.passed("same_shape")
        rep.passed("parses")
        leaks = _env_leaks(real, fake)
    else:
        rep.passed("parses")
        n_r, n_f = max(len(real_t.splitlines()), 1), len(fake_t.splitlines())
        if not 0.75 <= n_f / n_r <= 1.25:
            rep.fail("same_shape", f"{n_f} lines instead of about {n_r}")
        rep.passed("same_shape")
        leaks = _text_leaks(real, fake)

    leaks = leaks + [f"token {t}" for t in _generic_leaks(real, fake)]
    if leaks:
        rep.fail("no_real_values", f"{len(leaks)} real value(s) in the twin, e.g. {leaks[:3]}")
    rep.passed("no_real_values")

    missing = [b for b in (beacons or []) if b not in fake_t]
    if missing:
        rep.fail("beacons", f"missing from the twin: {missing[:3]}")
    rep.passed("beacons")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check a fake twin against the real file.")
    ap.add_argument("real")
    ap.add_argument("fake")
    ap.add_argument("--beacon", action="append", default=[])
    a = ap.parse_args(argv)
    with open(a.real, "rb") as fr, open(a.fake, "rb") as ff:
        rep = verify_decoy(a.real.rsplit("/", 1)[-1], fr.read(), ff.read(), a.beacon)
    for check, ok in rep.checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {check}")
    for p in rep.problems:
        print("   -", p)
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
