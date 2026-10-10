"""Benchmark for the defense sheet: run each attacker/benign scenario through core
and report the metrics the rules ask for — detection rate, false positives, time to
detect, time to respond, real files lost.

Deterministic and offline: it classifies the canonical event sequences from
``mirage.fakes`` plus two synthesized benign baselines (a normal user and a backup
job) with the real core logic (``build_incidents`` + ``label_intruder`` +
``metrics``). The AI note-follow rate per model comes from the live go/no-go runs
and is reported alongside as a constant (see NOTE_FOLLOW_RATE).

    python -m mirage.bench.run_bench            # prints the markdown, writes generated/bench_results.csv
"""

from __future__ import annotations

import csv
import io
import statistics
from dataclasses import dataclass

from mirage import fakes
from mirage.contracts import ATTACK_USER, HOST, Event
from mirage.core.incidents import build_incidents
from mirage.core.intruder import label_intruder
from mirage.core.metrics import compute_metrics

# Live go/no-go result (10 runs each, naive persona); documented here for the sheet.
NOTE_FOLLOW_RATE = {"qwen2.5:7b": (2, 10), "qwen3.5:35b-a3b": (7, 10)}


def _benign_user_events(t0: float = fakes.T0) -> list[Event]:
    """A normal employee: a few ordinary reads, slow/irregular, no mine. Not an intruder."""
    cmds = ["id", "ls ~", "ls /srv/share/marketing", "cat /srv/share/marketing/newsletter.md",
            "ls /srv/share/ops"]
    gaps = [3.0, 11.0, 26.0, 7.5, 40.0]
    out, t = [], t0
    for g, c in zip(gaps, cmds):
        t += g
        out.append(Event(t, "command", user="jdupont", details={"cmd": c, "src_ip": "172.18.0.9"}))
    return out


def _backup_job_events(t0: float = fakes.T0) -> list[Event]:
    """An automated backup: many fast reads of ordinary files, no mine. Not an intruder."""
    out, t = [], t0
    for i in range(18):
        t += 0.05
        out.append(Event(t, "command", user="backup_svc",
                         details={"cmd": f"cp /srv/share/ops/file_{i}.txt /backup/", "src_ip": "172.18.0.3"}))
    return out


# (name, events, is_intruder ground truth)
SCENARIOS = [
    ("ai_agent", fakes.ai_attack_events(), True),
    ("ai_guided", fakes.guided_ai_attack_events(), True),
    ("script", fakes.script_attack_events(), True),
    ("human", fakes.human_attack_events(), True),
    ("benign_user", _benign_user_events(), False),
    ("backup_job", _backup_job_events(), False),
]


@dataclass
class BenchRow:
    scenario: str
    is_intruder: bool
    detected: bool          # an incident was raised
    label: str
    confidence: str
    swapped: bool
    swap_ms: float | None
    detect_s: float | None
    respond_s: float | None
    real_lost: int
    fakes_taken: int
    note_followed: bool


def _row(name: str, events: list[Event], is_intruder: bool) -> BenchRow:
    incs = build_incidents(events)
    if not incs:
        return BenchRow(name, is_intruder, False, "none", "none",
                        False, None, None, None, 0, 0, False)
    inc = incs[0]
    lab = label_intruder(inc.events)
    m = compute_metrics([inc])
    return BenchRow(
        scenario=name, is_intruder=is_intruder, detected=True,
        label=lab.kind, confidence=lab.confidence,
        swapped=inc.swapped, swap_ms=inc.swap_ms,
        detect_s=m.time_to_detect_s, respond_s=m.time_to_respond_s,
        real_lost=len(inc.real_files_lost), fakes_taken=len(inc.fakes_taken),
        note_followed=any(e.type == "ticket" for e in inc.events),
    )


def run_bench(scenarios=SCENARIOS) -> tuple[list[BenchRow], dict]:
    rows = [_row(n, e, i) for (n, e, i) in scenarios]
    intruders = [r for r in rows if r.is_intruder]
    benign = [r for r in rows if not r.is_intruder]
    detect_s = [r.detect_s for r in intruders if r.detect_s is not None]
    respond_s = [r.respond_s for r in intruders if r.respond_s is not None]
    summary = {
        "intruders": len(intruders),
        "detected": sum(1 for r in intruders if r.detected),
        "detection_rate": (sum(1 for r in intruders if r.detected) / len(intruders)) if intruders else None,
        "benign": len(benign),
        "false_positives": sum(1 for r in benign if r.detected),
        "false_positive_rate": (sum(1 for r in benign if r.detected) / len(benign)) if benign else None,
        "median_detect_s": statistics.median(detect_s) if detect_s else None,
        "median_respond_s": statistics.median(respond_s) if respond_s else None,
        "real_files_lost_total": sum(r.real_lost for r in rows),
    }
    return rows, summary


def to_csv(rows: list[BenchRow]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["scenario", "is_intruder", "detected", "label", "confidence", "swapped",
                "swap_ms", "detect_s", "respond_s", "real_lost", "fakes_taken", "note_followed"])
    for r in rows:
        w.writerow([r.scenario, r.is_intruder, r.detected, r.label, r.confidence, r.swapped,
                    r.swap_ms, r.detect_s, r.respond_s, r.real_lost, r.fakes_taken, r.note_followed])
    return buf.getvalue()


def _pct(x):
    return "-" if x is None else f"{x * 100:.0f}%"


def render_markdown(rows: list[BenchRow], summary: dict) -> str:
    lines = ["# MIRAGE defense metrics", "", "## Headline", ""]
    lines += [
        f"- Detection rate: **{_pct(summary['detection_rate'])}** "
        f"({summary['detected']}/{summary['intruders']} intruder scenarios raised an incident)",
        f"- False-positive rate: **{_pct(summary['false_positive_rate'])}** "
        f"({summary['false_positives']}/{summary['benign']} benign scenarios flagged)",
        f"- Median time to detect: **{summary['median_detect_s']} s** · "
        f"median time to respond (swap): **{summary['median_respond_s']} s**",
        f"- Real files lost across all scenarios: **{summary['real_files_lost_total']}**",
        "",
        "## Per scenario", "",
        "| Scenario | Intruder? | Detected | Label | Conf. | Swap ms | Detect s | Respond s | Real lost | Fakes taken | Confessed |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.scenario} | {'yes' if r.is_intruder else 'no'} | {'yes' if r.detected else 'no'} | "
            f"{r.label} | {r.confidence} | {r.swap_ms} | {r.detect_s} | {r.respond_s} | "
            f"{r.real_lost} | {r.fakes_taken} | {'yes' if r.note_followed else 'no'} |"
        )
    lines += ["", "## AI note-follow rate (live go/no-go, naive persona)", ""]
    for model, (hit, n) in NOTE_FOLLOW_RATE.items():
        lines.append(f"- `{model}`: **{hit}/{n}** followed the mine note.")
    return "\n".join(lines) + "\n"


def main() -> int:
    rows, summary = run_bench()
    import os
    os.makedirs("generated", exist_ok=True)
    with open("generated/bench_results.csv", "w") as f:
        f.write(to_csv(rows))
    print(render_markdown(rows, summary))
    print("\n[wrote generated/bench_results.csv]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
