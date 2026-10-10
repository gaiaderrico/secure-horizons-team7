"""Non-LLM attacker profiles and benign jobs: the baseline the AI attacker is
measured against.

The intruder classifier (plan section 9) tells AI / scripted / human / benign
apart by command *rhythm* and whether the mine note was followed. These profiles
exist to produce the right SHAPES of activity so that comparison is meaningful:

  - script  : a plain loot script. Regular sub-second rhythm, opens the mine,
              tars the crown jewels away, but can NEVER understand the note in the
              mine, so it never contacts the honey API / /tickets.
  - benign  : a normal employee. A handful of reads of ordinary files with slow,
              irregular, human-like pauses. Touches no mine. This is the
              false-positive test: the classifier must NOT flag it.
  - backup  : an automated backup job. Reads many files fast (the known
              backup-window case the guard must ignore). Legitimate, touches no
              mine.

Everything here is pure, injectable logic so it is testable without SSH, network
or real sleeping. The canonical command lists come from ``mirage.fakes`` so this
module and the classifier reference stay in sync.

Only ever run the live (SSH) path against our own throwaway lab container on the
isolated Docker network, with synthetic data.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass, field

from mirage.fakes import LOOT, RECON, sample_manifest

# ---------------------------------------------------------------------------
# Plan model
# ---------------------------------------------------------------------------


@dataclass
class StepPlan:
    """One step of a scripted profile.

    ``delay_s`` is slept BEFORE ``cmd`` is run, so a list of StepPlans encodes
    both the commands and the rhythm between them.
    """

    cmd: str
    delay_s: float


@dataclass
class ScriptResult:
    commands: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    touched_mine: bool = False
    stolen: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure detection helpers (tested directly)
# ---------------------------------------------------------------------------

# Verbs that move/collect data off the box. A plain read (cat/head/ls) or a
# backup copy (cp to /backup) is NOT exfiltration; archiving/transferring is.
_EXFIL_VERBS = ("tar", "zip", "gzip", "scp", "rsync", "curl", "nc")
_SHARE_PREFIX = "/srv/share"


def _touched_mine(cmds: list[str], mine_paths: list[str]) -> bool:
    """True if any command references a mine (trap file) path."""
    return any(any(mp in c for mp in mine_paths) for c in cmds)


def _stolen(cmds: list[str]) -> list[str]:
    """Share paths handed to an exfiltration/archive command, in order, deduped.

    Reusing the AI attacker's idea (archive the loot, ship it out) but kept
    independent: we only look at the command text.
    """
    stolen: list[str] = []
    for c in cmds:
        toks = c.split()
        if not toks:
            continue
        if toks[0] in _EXFIL_VERBS:
            for t in toks[1:]:
                if t.startswith(_SHARE_PREFIX):
                    stolen.append(t)
    return list(dict.fromkeys(stolen))  # dedupe, keep order


def _default_mine_paths() -> list[str]:
    """Mine paths from the synthetic manifest, so callers/tests are self-contained."""
    return [m.path for m in sample_manifest().mines]


# ---------------------------------------------------------------------------
# Canonical plans, built from the shared command lists
# ---------------------------------------------------------------------------


def recon_then_loot_plan() -> list[StepPlan]:
    """Plain loot script: RECON + LOOT from ``fakes`` at a regular ~0.2s rhythm.

    Opens the mine ``00_passwords_backup.txt``, reads the crown jewels and tars
    them away. NEVER contacts the honey API / /tickets: a script cannot read or
    act on the note in the mine.
    """
    return [StepPlan(cmd, 0.2) for cmd in (*RECON, *LOOT)]


def benign_user_plan() -> list[StepPlan]:
    """A normal employee: a few reads of ordinary files, slow and irregular.

    No mine, no crown jewel, no archiving. The false-positive baseline.
    """
    steps = [
        ("id", 2.5),
        ("ls -la /srv/share", 11.0),
        ("cat /srv/share/README.md", 6.5),
        ("ls /srv/share/projects", 23.0),
        ("head -40 /srv/share/projects/roadmap_q3.md", 8.0),
        ("cat /srv/share/hr/onboarding_checklist.md", 17.0),
    ]
    return [StepPlan(cmd, delay) for cmd, delay in steps]


def backup_job_plan() -> list[StepPlan]:
    """Automated nightly backup: reads many files fast (the backup window).

    Legitimate: copies ordinary and crown-jewel files to /backup, but never
    enumerates the trap (mine) files, so the classifier must not flag it.
    """
    files = [
        "/srv/share/README.md",
        "/srv/share/projects/roadmap_q3.md",
        "/srv/share/projects/backlog.md",
        "/srv/share/hr/onboarding_checklist.md",
        "/srv/share/hr/holiday_schedule.csv",
        "/srv/share/clinical/patients.csv",
        "/srv/share/clinical/visits.csv",
        "/srv/share/it/network_diagram.png",
        "/srv/share/it/.env",
        "/srv/share/legal/contracts_2026.md",
        "/srv/share/legal/nda_templates.md",
        "/srv/share/finance/budget_2026.xlsx",
        "/srv/share/finance/invoices_q1.csv",
        "/srv/share/marketing/campaign_plan.md",
        "/srv/share/ops/runbook.md",
        "/srv/share/ops/inventory.csv",
    ]
    steps = [StepPlan("id", 0.05), StepPlan("ls -R /srv/share", 0.08)]
    steps += [StepPlan(f"cp {p} /backup/{p.rsplit('/', 1)[-1]}", 0.05) for p in files]
    return steps


PROFILES = {
    "script": recon_then_loot_plan,
    "benign": benign_user_plan,
    "backup": backup_job_plan,
}


# ---------------------------------------------------------------------------
# Pure driver
# ---------------------------------------------------------------------------


def run_plan(
    plan: list[StepPlan],
    run_command,
    sleep=time.sleep,
    mine_paths: list[str] | None = None,
) -> ScriptResult:
    """Run a plan. ``run_command(cmd) -> str`` is injected (real = SSH, tests = fake);
    ``sleep`` is injected so tests record delays instead of waiting.

    ``duration_s`` is the planned (slept) time, which is deterministic and does
    not depend on wall-clock, so tests are stable.
    """
    if mine_paths is None:
        mine_paths = _default_mine_paths()

    commands: list[str] = []
    outputs: list[str] = []
    duration = 0.0
    for step in plan:
        sleep(step.delay_s)
        duration += step.delay_s
        commands.append(step.cmd)
        outputs.append(run_command(step.cmd))

    return ScriptResult(
        commands=commands,
        outputs=outputs,
        duration_s=duration,
        touched_mine=_touched_mine(commands, mine_paths),
        stolen=_stolen(commands),
    )


# ---------------------------------------------------------------------------
# Real SSH adapter (not used by tests). LAB CONTAINER ONLY.
# ---------------------------------------------------------------------------


def ssh_runner(host: str, user: str, password: str, port: int = 22, timeout_s: int = 15):
    """Return a ``run_command`` that runs each command over SSH via ``sshpass``.

    LAB ONLY: only ever point this at our own throwaway victim container on the
    isolated Docker network. Needs ``sshpass`` and ``ssh`` on PATH.
    """

    def run(cmd: str) -> str:
        argv = [
            "sshpass",
            "-p",
            password,
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            f"ConnectTimeout={timeout_s}",
            "-p",
            str(port),
            f"{user}@{host}",
            cmd,
        ]
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout_s + 10
        )
        return proc.stdout + proc.stderr

    return run


def _dry_run_shell(cmd: str) -> str:
    """Fake shell for --dry-run: no network, canned output."""
    return f"[dry-run] {cmd}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _summary(profile: str, result: ScriptResult) -> str:
    return (
        f"profile={profile} commands={len(result.commands)} "
        f"duration_s={result.duration_s:.2f} touched_mine={result.touched_mine} "
        f"stolen={result.stolen}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MIRAGE non-LLM attacker / benign job runner (lab container only)."
    )
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan with a fake shell, no SSH and no real sleeping",
    )
    parser.add_argument("--host", default="lumen-fs01")
    parser.add_argument("--user", default="svc_backup")
    parser.add_argument("--password", default="")
    parser.add_argument("--port", type=int, default=22)
    args = parser.parse_args(argv)

    plan = PROFILES[args.profile]()

    if args.dry_run:
        run_command = _dry_run_shell
        sleep = lambda _s: None  # noqa: E731  - don't actually wait when smoke-testing
    else:
        run_command = ssh_runner(args.host, args.user, args.password, args.port)
        sleep = time.sleep

    print(f"# MIRAGE scripted attacker: profile={args.profile} "
          f"({'dry-run' if args.dry_run else args.host})")
    for step in plan:
        print(f"  +{step.delay_s:>5.2f}s  {step.cmd}")

    result = run_plan(plan, run_command, sleep=sleep)
    print("# " + _summary(args.profile, result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
