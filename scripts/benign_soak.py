"""benign_soak: false-positive test. Only normal activity on the live victim, no attack.

jdupont repeats the normal-employee plan; svc_backup runs the backup job every few minutes
(both plans from mirage.attacker.scripted). Afterwards we count what the guard and core did.

    python scripts/benign_soak.py --minutes 15
Needs: docker compose --profile core up -d and keys/test_key (installed for both users).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from mirage.attacker.scripted import backup_job_plan, benign_user_plan

ROOT = Path(__file__).resolve().parent.parent
SSH = ["ssh", "-i", "keys/test_key", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
       "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-p", "2222"]


def ssh(user: str, cmd: str) -> None:
    subprocess.run(SSH + [f"{user}@localhost", cmd], cwd=ROOT, capture_output=True, timeout=30)


def loop(user: str, plan, pause_s: float, until: float, counts: dict) -> None:
    while time.time() < until:
        for step in plan():
            if time.time() >= until:
                return
            time.sleep(step.delay_s)
            ssh(user, step.cmd)
            counts[user] = counts.get(user, 0) + 1
        time.sleep(pause_s)


def guard(*args: str) -> str:
    return subprocess.run(["docker", "compose", "exec", "-T", "guard", *args], cwd=ROOT,
                          capture_output=True, text=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=15)
    ap.add_argument("--backup-every-min", type=float, default=3)
    a = ap.parse_args()

    guard("python", "guard.py", "restore")
    urllib.request.urlopen(urllib.request.Request("http://localhost:8000/admin/reset", data=b"", method="POST"))
    since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    t0 = time.time()
    until = t0 + a.minutes * 60
    counts: dict = {}
    threads = [
        threading.Thread(target=loop, args=("jdupont", benign_user_plan, 5, until, counts)),
        threading.Thread(target=loop, args=("svc_backup", backup_job_plan, a.backup_every_min * 60, until, counts)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    minutes = (time.time() - t0) / 60

    log = subprocess.run(["docker", "logs", "--since", since, "mirage-guard-1"], capture_output=True, text=True)
    lines = (log.stdout + log.stderr).splitlines()
    # docker's --since can return a few lines from just before the start: keep only what follows
    # our own reset (the first RESTORED line in the window).
    start = next((i for i, x in enumerate(lines) if "RESTORED" in x), -1)
    lines = lines[start + 1:]
    swaps = [x for x in lines if "CONTAINED: swapped" in x]
    mines = [x for x in lines if "MINE " in x and " opened " in x]
    incidents = json.load(urllib.request.urlopen("http://localhost:8000/incidents"))
    print(f"ran {minutes:.1f} min, commands: {counts}")
    print(f"swaps triggered: {len(swaps)}  mines opened: {len(mines)}  incidents in core: {len(incidents)}")
    for x in swaps + [x for x in lines if "CROWN JEWEL" in x]:
        print("  " + x)
    guard("python", "guard.py", "restore")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
