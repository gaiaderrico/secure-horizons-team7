"""live_bench: run the real AI attacker N times against the live victim with the guard on.

Each run starts clean (guard restore + core reset), nobody presses Contain, and we record what
core saw. Results: generated/live_bench.csv (one row per run) and a summary on stdout.

    python scripts/live_bench.py --runs 10 --model qwen3.5:35b-a3b
Needs: docker compose --profile core up -d, keys/test_key, Ollama with the model.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = "http://localhost:8000"
OUT = ROOT / "generated" / "live_bench.csv"
FIELDS = ["run", "model", "steps", "stop", "mine_hit", "first_trigger", "swapped", "swap_ms",
          "real_lost", "fakes_taken", "note_followed", "attacker_says_stolen", "seconds"]


def core(path: str, method: str = "GET"):
    req = urllib.request.Request(CORE + path, method=method, data=b"" if method == "POST" else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def reset() -> None:
    subprocess.run(["docker", "compose", "exec", "-T", "guard", "python", "guard.py", "restore"],
                   cwd=ROOT, check=True, capture_output=True)
    core("/admin/reset", "POST")
    time.sleep(1)


def attack(model: str, max_steps: int, log: Path) -> str:
    cmd = [sys.executable, "-m", "mirage.attacker.ai_attacker", "--host", "localhost", "--port", "2222",
           "--key", "keys/test_key", "--model", model, "--max-steps", str(max_steps)]
    with log.open("w") as f:
        subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, env={"PYTHONUNBUFFERED": "1",
                       **__import__("os").environ}, timeout=1800)
    return log.read_text(errors="replace")


def first_trigger(events: list) -> str:
    for e in events:
        if e["type"] == "mine_opened":
            return f"mine {e['details'].get('path', '').rsplit('/', 1)[-1]}"
        if e["type"] == "swap_done" and e["details"].get("via") == "crown_jewel_named":
            return "crown jewel named"
    return ""


def one_run(i: int, model: str, max_steps: int, logdir: Path) -> dict:
    reset()
    t0 = time.time()
    text = attack(model, max_steps, logdir / f"run_{i:02d}.log")
    seconds = round(time.time() - t0)
    m = re.search(r"=== summary === steps=(\d+).*?stolen=(\[.*?\]) followed_note=(\w+).*?stop=(\w+)", text)
    incidents = core("/incidents") or []
    events = sorted(core("/events") or [], key=lambda e: e["ts"])
    inc = incidents[0] if incidents else {}
    return {
        "run": i, "model": model,
        "steps": m.group(1) if m else "", "stop": m.group(4) if m else "crashed",
        "mine_hit": any(e["type"] == "mine_opened" for e in events),
        "first_trigger": first_trigger(events),
        "swapped": bool(inc.get("swapped")), "swap_ms": inc.get("swap_ms"),
        "real_lost": ";".join(inc.get("real_files_lost", [])),
        "fakes_taken": ";".join(inc.get("fakes_taken", [])),
        "note_followed": any(e["type"] == "ticket" for e in events),
        "attacker_says_stolen": m.group(2) if m else "", "seconds": seconds,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--model", default="qwen3.5:35b-a3b")
    ap.add_argument("--max-steps", type=int, default=22)
    a = ap.parse_args()
    logdir = ROOT / "generated" / "live_bench_logs"
    logdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(1, a.runs + 1):
        row = one_run(i, a.model, a.max_steps, logdir)
        rows.append(row)
        print(f"run {i}: trigger={row['first_trigger'] or 'none'} swapped={row['swapped']} "
              f"swap_ms={row['swap_ms']} real_lost=[{row['real_lost']}] fakes=[{row['fakes_taken']}] "
              f"note={row['note_followed']} stop={row['stop']} ({row['seconds']} s)", flush=True)
        with OUT.open("w", newline="") as f:  # rewrite after every run: partial results survive
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            w.writerows(rows)
    reset()

    done = [r for r in rows if r["stop"] != "crashed"]
    swaps = [r["swap_ms"] for r in done if r["swap_ms"] is not None]
    print(f"\n=== {len(done)}/{len(rows)} runs completed, model {a.model} ===")
    print(f"swap triggered:       {sum(r['swapped'] for r in done)}/{len(done)}")
    print(f"0 real files lost:    {sum(not r['real_lost'] for r in done)}/{len(done)}")
    print(f"note followed:        {sum(r['note_followed'] for r in done)}/{len(done)}")
    if swaps:
        print(f"swap time ms:         median {statistics.median(swaps)}, min {min(swaps)}, max {max(swaps)}")
    print(f"results: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
