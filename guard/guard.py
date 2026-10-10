"""MIRAGE guard: swaps the crown jewels for their fakes as soon as a mine is opened.

Runs in its own container that shares the victim's network and PID namespaces and the
/srv and /var/log/mirage volumes (see docker-compose.yml). Stdlib only.

    python guard.py                 daemon: tail the command log, watch mines, control API on :8081
    python guard.py restore         real files back, users unblocked, state clean (= demo reset)
    python guard.py swap            swap now, as if a mine had been opened
    python guard.py contain [USER]  block USER (default: last intruder) and kill their sessions
    python guard.py status          print the state
    python guard.py check           exit 1 if the share is not clean (leftovers after restore)
    python guard.py seed [--force]  (re)load the share from /seed (Thomas's prepare output)
                                    or the built-in placeholder company

How a swap works (contracts: SHARE_DIR, STAGE_DIR, VAULT_TMP_DIR, VAULT_DIR), per crown jewel:
    rename real_path -> VAULT_TMP_DIR/<stage name>     (same filesystem: atomic and fast)
    rename stage_path -> real_path                     (the fake is now live)
then the real files are copied to VAULT_DIR (a volume the victim does not mount).
Restore does the reverse. Every step is idempotent, so restore can always be re-run.

Two mine detectors, both behind `mines_hit_by_command` / `mines_read`:
  1. a command in the log names the mine (gives user, session and source IP);
  2. the mine's atime moves (catches `grep -r`, globs, sftp...). Mines are "armed" with
     atime < mtime, so with relatime the first read updates atime.
"""

from __future__ import annotations

import fcntl
import json
import os
import queue
import re
import shutil
import signal
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from mirage.contracts import (
    COMMAND_LOG,
    CORE_URL,
    MANIFEST_PATH,
    SHARE_DIR,
    STAGE_DIR,
    VAULT_DIR,
    VAULT_TMP_DIR,
    CrownJewel,
    Event,
    Manifest,
    Mine,
)

POLL_S = float(os.environ.get("GUARD_POLL_S", "0.2"))
CONTROL_PORT = int(os.environ.get("GUARD_PORT", "8081"))
GUARD_TOKEN = os.environ.get("GUARD_TOKEN", "")
# victim user -> uid (fixed in victim/Dockerfile), used to kill sessions on contain
VICTIM_UIDS = dict(
    (kv.split(":")[0], int(kv.split(":")[1]))
    for kv in os.environ.get("VICTIM_UIDS", "svc_backup:1001,jdupont:1002").split(",")
    if ":" in kv
)
MINE_DEDUP_S = 5.0  # atime hit right after a command hit on the same mine = same event


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} guard: {msg}", flush=True)


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


@dataclass
class Paths:
    share: str = SHARE_DIR
    stage: str = STAGE_DIR
    vault_tmp: str = VAULT_TMP_DIR
    vault: str = VAULT_DIR
    manifest: str = MANIFEST_PATH
    command_log: str = COMMAND_LOG
    guard_dir: str = "/srv/.guard"  # world-readable: victim reads blocked_users from here
    seed: str = "/seed"  # ./generated on the host (prepare.run_all output), read-only

    @classmethod
    def under(cls, root: str | Path) -> Paths:
        """Same layout under a temp dir, for tests. Matches fakes.sample_manifest(root)."""
        r = str(root)
        return cls(f"{r}/share", f"{r}/.stage", f"{r}/.vault_tmp", f"{r}/vault",
                   f"{r}/etc/manifest.json", f"{r}/log/commands.jsonl", f"{r}/.guard", f"{r}/seed")

    @property
    def state_file(self) -> str:
        return f"{self.vault}/state.json"

    @property
    def lock_file(self) -> str:
        return f"{self.vault}/.lock"

    @property
    def events_file(self) -> str:
        return f"{self.vault}/events.jsonl"  # local copy of every event sent

    @property
    def blocked_file(self) -> str:
        return f"{self.guard_dir}/blocked_users"


def held_path(p: Paths, cj: CrownJewel) -> str:
    """Where the real file waits during a swap (named after its stage file: unique)."""
    return f"{p.vault_tmp}/{os.path.basename(cj.stage_path)}"


def backup_path(p: Paths, cj: CrownJewel) -> str:
    return f"{p.vault}/{os.path.basename(cj.stage_path)}"


# --------------------------------------------------------------------------
# State (in the vault volume, shared by the daemon and CLI calls, guarded by a lock)
# --------------------------------------------------------------------------

CLEAN_STATE: dict[str, Any] = {"swapped": [], "swap_ts": None, "swap_ms": None,
                               "intruder": None, "blocked": []}


def load_state(p: Paths) -> dict[str, Any]:
    try:
        return {**CLEAN_STATE, **json.loads(Path(p.state_file).read_text())}
    except (OSError, ValueError):
        return dict(CLEAN_STATE)


def save_state(p: Paths, st: dict[str, Any]) -> None:
    os.makedirs(p.vault, exist_ok=True)
    tmp = p.state_file + ".tmp"
    Path(tmp).write_text(json.dumps(st, indent=2))
    os.replace(tmp, p.state_file)


def state_name(st: dict[str, Any]) -> str:
    if st["blocked"]:
        return "contained"
    return "swapped" if st["swapped"] else "clean"


class Lock:
    """Cross-process lock (daemon, control API threads and CLI all take it)."""

    def __init__(self, p: Paths):
        self.path = p.lock_file
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def __enter__(self):
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)


# --------------------------------------------------------------------------
# Pure logic: command log records, mine / crown jewel matching
# --------------------------------------------------------------------------

_BEFORE = r"(?:^|[\s/'\"=<>(;|&])"
_AFTER = r"(?=$|[\s'\";|&)<>*])"


def mentions(cmd: str, path: str) -> bool:
    """True if `cmd` names `path`, by full path or by file name (covers `cd x && cat f`)."""
    if path in cmd:
        return True
    name = os.path.basename(path)
    return bool(name) and re.search(_BEFORE + re.escape(name) + _AFTER, cmd) is not None


def parse_record(line: str) -> dict[str, Any] | None:
    """One line of commands.jsonl -> dict with ts, session, user, src_ip, cmd. None if broken."""
    try:
        rec = json.loads(line)
    except ValueError:
        return None
    if not isinstance(rec, dict) or "cmd" not in rec:
        return None
    rec.setdefault("ts", time.time())
    for k in ("session", "user", "src_ip", "mode", "cwd"):
        rec.setdefault(k, "")
    return rec


def mines_hit_by_command(cmd: str, m: Manifest) -> list[Mine]:
    return [mine for mine in m.mines if mentions(cmd, mine.path)]


def jewels_hit_by_command(cmd: str, m: Manifest) -> list[CrownJewel]:
    return [cj for cj in m.crown_jewels if mentions(cmd, cj.real_path)]


def command_event(rec: dict[str, Any]) -> Event:
    return Event(float(rec["ts"]), "command", user=rec["user"],
                 details={"cmd": rec["cmd"], "src_ip": rec["src_ip"], "session": rec["session"]})


def mine_event(mine: Mine, rec: dict[str, Any] | None, via: str) -> Event:
    rec = rec or {}
    return Event(float(rec.get("ts") or time.time()), "mine_opened", user=rec.get("user", ""),
                 ref=mine.id, details={"path": mine.path, "session": rec.get("session", ""),
                                       "src_ip": rec.get("src_ip", ""), "via": via})


def file_event(cj: CrownJewel, rec: dict[str, Any], swapped: list[str]) -> Event:
    which = "fake" if cj.id in swapped else "real"
    return Event(float(rec["ts"]), "file_opened", user=rec["user"], ref=cj.id,
                 details={"path": cj.real_path, "which": which, "session": rec["session"],
                          "src_ip": rec["src_ip"]})


class LogTailer:
    """Reads new complete lines from the command log. Starts at the end (no replay)."""

    def __init__(self, path: str, from_start: bool = False):
        self.path = path
        self.buf = b""
        try:
            self.pos = 0 if from_start else os.path.getsize(path)
        except OSError:
            self.pos = 0

    def read_new(self) -> list[dict[str, Any]]:
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return []
        if size < self.pos:  # truncated
            self.pos, self.buf = 0, b""
        if size == self.pos:
            return []
        with open(self.path, "rb") as f:
            f.seek(self.pos)
            data = f.read()
        self.pos += len(data)
        *lines, self.buf = (self.buf + data).split(b"\n")
        out = []
        for raw in lines:
            rec = parse_record(raw.decode("utf-8", "replace"))
            if rec:
                out.append(rec)
        return out


# --------------------------------------------------------------------------
# Mines: atime detector
# --------------------------------------------------------------------------


def arm_mine(path: str) -> None:
    """Set atime 60 s before mtime: with relatime the next read moves atime past mtime."""
    try:
        st = os.stat(path)
        os.utime(path, ns=(st.st_mtime_ns - 60_000_000_000, st.st_mtime_ns))
    except OSError:
        pass


def arm_mines(m: Manifest) -> None:
    for mine in m.mines:
        arm_mine(mine.path)


def mine_was_read(path: str) -> bool:
    try:
        st = os.stat(path)
    except OSError:
        return False
    return st.st_atime_ns > st.st_mtime_ns


def mines_read(m: Manifest) -> list[Mine]:
    return [mine for mine in m.mines if mine_was_read(mine.path)]


def atime_works(probe_dir: str) -> bool:
    """Self-check: does a read update atime on this filesystem? (noatime would break it)"""
    probe = f"{probe_dir}/.atime_probe"
    try:
        os.makedirs(probe_dir, exist_ok=True)
        Path(probe).write_text("probe\n")
        arm_mine(probe)
        Path(probe).read_bytes()
        return mine_was_read(probe)
    except OSError:
        return False
    finally:
        try:
            os.remove(probe)
        except OSError:
            pass


# --------------------------------------------------------------------------
# Swap / restore (filesystem only, no locking or events: tested directly)
# --------------------------------------------------------------------------


def swap_files(m: Manifest, p: Paths) -> list[str]:
    """Real -> vault_tmp, fake -> real. Returns the crown jewel ids swapped by this call."""
    os.makedirs(p.vault_tmp, mode=0o700, exist_ok=True)
    done = []
    for cj in m.crown_jewels:
        held = held_path(p, cj)
        if os.path.exists(held):
            continue  # already swapped
        if not (os.path.exists(cj.real_path) and os.path.exists(cj.stage_path)):
            log(f"WARNING cannot swap {cj.id}: real or fake missing")
            continue
        os.rename(cj.real_path, held)
        os.rename(cj.stage_path, cj.real_path)
        done.append(cj.id)
    return done


def backup_to_vault(m: Manifest, p: Paths) -> None:
    """Copy the held real files to VAULT_DIR (not mounted in the victim). After the swap."""
    os.makedirs(p.vault, mode=0o700, exist_ok=True)
    for cj in m.crown_jewels:
        if os.path.exists(held_path(p, cj)):
            shutil.copy2(held_path(p, cj), backup_path(p, cj))


def _same_bytes(a: str, b: str) -> bool:
    try:
        return Path(a).read_bytes() == Path(b).read_bytes()
    except OSError:
        return False


def restore_files(m: Manifest, p: Paths) -> list[str]:
    """Fake -> stage, real -> real_path. Returns the crown jewel ids restored by this call."""
    done = []
    for cj in m.crown_jewels:
        held, backup = held_path(p, cj), backup_path(p, cj)
        if not os.path.exists(held) and os.path.exists(backup):
            if os.path.exists(cj.real_path) and _same_bytes(backup, cj.real_path):
                os.remove(backup)  # already restored, stale backup
                continue
            shutil.copy2(backup, held)  # vault_tmp lost: recover from the vault
        if not os.path.exists(held):
            continue
        if os.path.exists(cj.real_path):
            os.makedirs(os.path.dirname(cj.stage_path), exist_ok=True)
            os.rename(cj.real_path, cj.stage_path)
        os.rename(held, cj.real_path)
        if os.path.exists(backup):
            os.remove(backup)
        done.append(cj.id)
    return done


def leftovers(m: Manifest, p: Paths) -> list[str]:
    """Problems that mean the share is NOT in its clean state. Empty list = clean."""
    probs = []
    for cj in m.crown_jewels:
        if not os.path.exists(cj.real_path):
            probs.append(f"{cj.id}: real file missing at {cj.real_path}")
        if not os.path.exists(cj.stage_path):
            probs.append(f"{cj.id}: fake missing at {cj.stage_path}")
        if os.path.exists(held_path(p, cj)):
            probs.append(f"{cj.id}: real file still held in {p.vault_tmp}")
        if os.path.exists(cj.real_path) and os.path.exists(cj.stage_path) \
                and _same_bytes(cj.real_path, cj.stage_path):
            probs.append(f"{cj.id}: live file is identical to the fake")
    return probs


# --------------------------------------------------------------------------
# Events to core (fail soft: never block or crash the guard)
# --------------------------------------------------------------------------


def post_event(core_url: str, ev: Event, timeout: float = 2.0) -> None:
    req = urllib.request.Request(f"{core_url.rstrip('/')}/events",
                                 data=json.dumps(ev.to_dict()).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read()


class Reporter:
    """Queues events and POSTs them to core from a background thread (or inline if sync)."""

    def __init__(self, p: Paths, core_url: str = CORE_URL, sync: bool = False):
        self.p, self.core_url, self.sync = p, core_url, sync
        self.q: queue.Queue[Event] = queue.Queue()
        self.down_logged = False
        if not sync:
            threading.Thread(target=self._loop, daemon=True).start()

    def send(self, ev: Event) -> None:
        try:
            os.makedirs(self.p.vault, exist_ok=True)
            with open(self.p.events_file, "a") as f:
                f.write(json.dumps(ev.to_dict()) + "\n")
        except OSError:
            pass
        if self.sync:
            self._post(ev, tries=1)
        else:
            self.q.put(ev)

    def _post(self, ev: Event, tries: int) -> None:
        for i in range(tries):
            try:
                post_event(self.core_url, ev)
                if self.down_logged:
                    log(f"core API back at {self.core_url}")
                self.down_logged = False
                return
            except Exception as e:  # noqa: BLE001 - any failure: retry then drop
                if i + 1 < tries:
                    time.sleep(0.5 * 2 ** i)
                elif not self.down_logged:
                    log(f"core API unreachable ({self.core_url}): {e}; events kept in {self.p.events_file}")
                    self.down_logged = True

    def _loop(self) -> None:
        while True:
            ev = self.q.get()
            self._post(ev, tries=1 if self.down_logged else 3)


# --------------------------------------------------------------------------
# Actions (lock + filesystem + state + events)
# --------------------------------------------------------------------------


def load_manifest(p: Paths) -> Manifest:
    try:
        return Manifest.load(p.manifest)
    except (OSError, ValueError):
        return Manifest()


def do_swap(p: Paths, rep: Reporter, intruder: dict[str, Any] | None = None) -> dict[str, Any]:
    m = load_manifest(p)
    with Lock(p):
        st = load_state(p)
        t0 = time.perf_counter()
        files = swap_files(m, p)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        if files:
            st["swapped"] = sorted(set(st["swapped"]) | set(files))
            st["swap_ts"], st["swap_ms"] = time.time(), ms
        if intruder and not st["intruder"]:
            st["intruder"] = intruder
        save_state(p, st)
    if files:
        backup_to_vault(m, p)
        who = intruder or {}
        log(f"CONTAINED: swapped {len(files)} files {files} in {ms} ms "
            f"(user={who.get('user', '?')} session={who.get('session', '?')} src={who.get('src_ip', '?')})")
        rep.send(Event(Event.now(), "swap_done", details={"duration_ms": ms, "files": files}))
    return {"swapped": files, "duration_ms": ms, "state": state_name(st)}


def kill_user_sessions(uid: int) -> int:
    """Kill every process of `uid` (we share the victim's PID namespace)."""
    killed = 0
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            status = Path(f"/proc/{d}/status").read_text()
        except OSError:
            continue
        line = next((x for x in status.splitlines() if x.startswith("Uid:")), "")
        if line and int(line.split()[1]) == uid:
            try:
                os.kill(int(d), signal.SIGKILL)
                killed += 1
            except OSError:
                pass
    return killed


def write_blocked(p: Paths, users: list[str]) -> None:
    os.makedirs(p.guard_dir, exist_ok=True)
    os.chmod(p.guard_dir, 0o755)
    Path(p.blocked_file).write_text("".join(f"{u}\n" for u in users))
    os.chmod(p.blocked_file, 0o644)


def do_contain(p: Paths, rep: Reporter, user: str = "", by: str = "analyst") -> dict[str, Any]:
    """Analyst 'Contain': make sure the fakes are live, block the user, kill their sessions."""
    st = load_state(p)
    user = user or (st["intruder"] or {}).get("user", "")
    swap = do_swap(p, rep)
    killed = 0
    with Lock(p):
        st = load_state(p)
        if user and user not in st["blocked"]:
            st["blocked"].append(user)
        write_blocked(p, st["blocked"])
        save_state(p, st)
    if user in VICTIM_UIDS:
        killed = kill_user_sessions(VICTIM_UIDS[user])
    log(f"CONTAIN: user={user or '?'} blocked, {killed} processes killed (by {by})")
    rep.send(Event(Event.now(), "contain_done", user=user, details={"user": user, "by": by}))
    return {"user": user, "killed": killed, "swapped": swap["swapped"], "state": state_name(load_state(p))}


def do_restore(p: Paths, rep: Reporter, by: str = "analyst") -> dict[str, Any]:
    m = load_manifest(p)
    with Lock(p):
        files = restore_files(m, p)
        save_state(p, dict(CLEAN_STATE))
        write_blocked(p, [])
        arm_mines(m)
    probs = leftovers(m, p)
    log(f"RESTORED: {len(files)} real files back {files} (by {by})"
        + (f"; LEFTOVERS: {probs}" if probs else "; share clean"))
    rep.send(Event(Event.now(), "restore_done", details={"files": files, "by": by}))
    return {"restored": files, "leftovers": probs, "state": "clean"}


def status(p: Paths) -> dict[str, Any]:
    st = load_state(p)
    m = load_manifest(p)
    return {**st, "state": state_name(st), "crown_jewels": [c.id for c in m.crown_jewels],
            "mines": [x.path for x in m.mines], "leftovers": leftovers(m, p) if not st["swapped"] else []}


# --------------------------------------------------------------------------
# Seeding the share (prepare output, else placeholder) and permissions
# --------------------------------------------------------------------------

PLACEHOLDER_NORMAL = {
    "finance/budget_2026.csv": "quarter,department,budget_eur\nQ1,clinical,410000\nQ1,it,95000\n"
                               "Q2,clinical,425000\nQ2,it,88000\n",
    "finance/invoices/INV-2026-0912.txt": "Invoice INV-2026-0912\nSupplier: MedSupply SAS\n"
                                          "Amount: 12 480.00 EUR\nDue: 2026-10-31\n",
    "hr/onboarding_checklist.md": "# Onboarding\n- Badge request\n- Laptop from IT\n- GDPR training\n",
    "hr/holidays_2026.csv": "employee_id,from,to\nE-104,2026-08-03,2026-08-21\nE-117,2026-12-21,2026-12-31\n",
    "legal/nda_template.md": "# Non-disclosure agreement (template)\nBetween Lumen Clinic and ...\n",
    "it/README.txt": "Backups run nightly at 02:00 (svc_backup). Ask IT before changing cron.\n",
    "clinical/schedule_week41.csv": "day,doctor,room\nMon,Dr. Martin,2\nTue,Dr. Robert,1\n",
}
PLACEHOLDER_CONTRACT_REAL = ("# Supplier contracts 2026\n\n| Supplier | Price/unit | Penalty |\n|---|---|---|\n"
                             "| MedSupply SAS | 4.10 EUR | 2%/week |\n| CleanCare | 1 900 EUR/month | 5% |\n")
PLACEHOLDER_CONTRACT_FAKE = ("# Supplier contracts 2026\n\n| Supplier | Price/unit | Penalty |\n|---|---|---|\n"
                             "| Novamed SARL | 3.85 EUR | 3%/week |\n| BrightServ | 2 150 EUR/month | 4% |\n")


def write_placeholder(p: Paths) -> Manifest:
    """Built-in demo company, used until Thomas's prepare output is in ./generated."""
    from mirage import fakes  # synthetic data owned by Gaia; only needed here

    m = fakes.sample_manifest(root=os.path.dirname(p.share))
    real = {"cj1": fakes.REAL_PATIENTS_CSV, "cj2": fakes.REAL_ENV, "cj3": PLACEHOLDER_CONTRACT_REAL}
    fake = {"cj1": fakes.GOOD_FAKE_PATIENTS_CSV, "cj2": fakes.GOOD_FAKE_ENV, "cj3": PLACEHOLDER_CONTRACT_FAKE}
    for rel, text in PLACEHOLDER_NORMAL.items():
        _write(f"{p.share}/{rel}", text)
    for cj in m.crown_jewels:
        _write(cj.real_path, real[cj.id])
        _write(cj.stage_path, fake[cj.id])
    for mine in m.mines:
        _write(mine.path, "# password backup - DO NOT SHARE\n"
                          "vpn: svc_vpn / see vault\nbackup-verification-code: " + mine.code + "\n")
    return m


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text(text)


def _empty_dir(d: str) -> None:
    if not os.path.isdir(d):
        return
    for name in os.listdir(d):
        full = os.path.join(d, name)
        shutil.rmtree(full) if os.path.isdir(full) and not os.path.islink(full) else os.remove(full)


def seed(p: Paths, force: bool = False) -> str:
    """Fill share + stage + manifest. Keeps an existing manifest unless force."""
    if os.path.exists(p.manifest) and not force:
        return "kept"
    for d in (p.share, p.stage, p.vault_tmp):
        _empty_dir(d)
        os.makedirs(d, exist_ok=True)
    for f in Path(p.vault).glob("cj*"):
        f.unlink()
    seed_manifest = f"{p.seed}/manifest.json"
    if os.path.exists(seed_manifest) and os.path.isdir(f"{p.seed}/share"):
        shutil.copytree(f"{p.seed}/share", p.share, dirs_exist_ok=True)
        if os.path.isdir(f"{p.seed}/stage"):
            shutil.copytree(f"{p.seed}/stage", p.stage, dirs_exist_ok=True)
        os.makedirs(os.path.dirname(p.manifest), exist_ok=True)
        shutil.copyfile(seed_manifest, p.manifest)
        source = "prepare (/seed)"
    else:
        write_placeholder(p).save(p.manifest)
        source = "placeholder (fakes.sample_manifest)"
    save_state(p, dict(CLEAN_STATE))
    write_blocked(p, [])
    return source


def fix_perms(p: Paths) -> None:
    """Share readable by everyone, stage/vault/manifest root-only."""
    for d, mode in ((os.path.dirname(p.share), 0o755), (p.share, 0o755), (p.stage, 0o700),
                    (p.vault_tmp, 0o700), (p.vault, 0o700), (os.path.dirname(p.manifest), 0o700)):
        os.makedirs(d, exist_ok=True)
        os.chmod(d, mode)
    for root, dirs, files in os.walk(p.share):
        for x in dirs:
            os.chmod(os.path.join(root, x), 0o755)
        for x in files:
            os.chmod(os.path.join(root, x), 0o644)
    for f in Path(p.stage).rglob("*"):
        os.chmod(f, 0o644 if f.is_file() else 0o755)  # the stage dir itself (700) hides them
    if os.path.exists(p.manifest):
        os.chmod(p.manifest, 0o600)


# --------------------------------------------------------------------------
# Daemon
# --------------------------------------------------------------------------


class Watcher:
    """One tick = handle new log lines, then check mine atimes."""

    def __init__(self, p: Paths, rep: Reporter, use_atime: bool = True, from_start: bool = False):
        self.p, self.rep, self.use_atime = p, rep, use_atime
        self.tailer = LogTailer(p.command_log, from_start=from_start)
        self.last_rec: dict[str, Any] | None = None
        self.recent: dict[str, float] = {}  # mine id -> time of last command hit

    def tick(self) -> None:
        m = load_manifest(self.p)
        for rec in self.tailer.read_new():
            self.handle(rec, m)
        if self.use_atime:
            for mine in mines_read(m):
                arm_mine(mine.path)
                if time.time() - self.recent.get(mine.id, 0) < MINE_DEDUP_S:
                    continue
                rec = self.last_rec if self.last_rec and time.time() - float(self.last_rec["ts"]) < 10 else None
                self.mine_opened(mine, rec, via="atime")

    def handle(self, rec: dict[str, Any], m: Manifest) -> None:
        self.last_rec = rec
        self.rep.send(command_event(rec))
        for mine in mines_hit_by_command(rec["cmd"], m):
            self.recent[mine.id] = time.time()
            self.mine_opened(mine, rec, via="command")
        jewels = jewels_hit_by_command(rec["cmd"], m)
        if jewels:
            swapped = load_state(self.p)["swapped"]
            for cj in jewels:
                self.rep.send(file_event(cj, rec, swapped))

    def mine_opened(self, mine: Mine, rec: dict[str, Any] | None, via: str) -> None:
        who = {k: (rec or {}).get(k, "") for k in ("user", "session", "src_ip")}
        log(f"MINE {mine.id} opened ({mine.path}) via {via} by user={who['user'] or '?'}")
        # Swap first (latency matters), then queue the events in order.
        ev = mine_event(mine, rec, via)
        result = do_swap(self.p, _Deferred(self.rep), intruder=who if who["user"] else None)
        self.rep.send(ev)
        if result["swapped"]:
            self.rep.send(Event(Event.now(), "swap_done",
                                details={"duration_ms": result["duration_ms"], "files": result["swapped"]}))
        arm_mine(mine.path)


class _Deferred:
    """Swallows do_swap's own swap_done so Watcher can send mine_opened first."""

    def __init__(self, rep: Reporter):
        self.rep = rep

    def send(self, ev: Event) -> None:
        pass


def make_handler(p: Paths, rep: Reporter):
    class Handler(BaseHTTPRequestHandler):
        def _reply(self, code: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorized(self) -> bool:
            return not GUARD_TOKEN or self.headers.get("X-Guard-Token") == GUARD_TOKEN

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/health", "/"):
                return self._reply(200, {"ok": True})
            if self.path == "/status":
                if not self._authorized():
                    return self._reply(401, {"error": "bad token"})
                return self._reply(200, status(p))
            self._reply(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if not self._authorized():
                return self._reply(401, {"error": "bad token"})
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                body = {}
            by = body.get("by", "analyst")
            try:
                if self.path == "/swap":
                    return self._reply(200, do_swap(p, rep))
                if self.path == "/contain":
                    return self._reply(200, do_contain(p, rep, body.get("user", ""), by))
                if self.path == "/restore":
                    return self._reply(200, do_restore(p, rep, by))
            except Exception as e:  # noqa: BLE001
                log(f"ERROR {self.path}: {e}")
                return self._reply(500, {"error": str(e)})
            self._reply(404, {"error": "not found"})

        def log_message(self, fmt: str, *args: Any) -> None:
            log("api " + fmt % args)

    return Handler


def prepare(p: Paths, force_seed: bool = False) -> None:
    os.makedirs(os.path.dirname(p.command_log), exist_ok=True)
    source = seed(p, force=force_seed)
    fix_perms(p)
    if not os.path.exists(p.blocked_file):
        write_blocked(p, [])
    m = load_manifest(p)
    if not load_state(p)["swapped"]:
        arm_mines(m)
    log(f"share: {source}; {len(m.crown_jewels)} crown jewels, {len(m.mines)} mines")


def run_daemon(p: Paths) -> None:
    prepare(p)
    rep = Reporter(p)
    use_atime = os.environ.get("GUARD_ATIME", "1") == "1" and atime_works(p.guard_dir)
    log(f"atime mine detector: {'ON' if use_atime else 'OFF'}; core: {CORE_URL}")
    server = ThreadingHTTPServer(("0.0.0.0", CONTROL_PORT), make_handler(p, rep))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log(f"control API on :{CONTROL_PORT} (token {'required' if GUARD_TOKEN else 'NOT set'})")
    w = Watcher(p, rep, use_atime=use_atime)
    log(f"watching {p.command_log}, state={state_name(load_state(p))}")
    while True:
        try:
            w.tick()
        except Exception as e:  # noqa: BLE001 - never die, the demo depends on us
            log(f"ERROR in tick: {e!r}")
        time.sleep(POLL_S)


def main(argv: list[str]) -> int:
    p = Paths()
    cmd = argv[1] if len(argv) > 1 else "run"
    if cmd == "run":
        run_daemon(p)
        return 0
    rep = Reporter(p, sync=True)
    if cmd == "restore":
        out = do_restore(p, rep, by="cli")
    elif cmd == "swap":
        out = do_swap(p, rep)
    elif cmd == "contain":
        out = do_contain(p, rep, argv[2] if len(argv) > 2 else "", by="cli")
    elif cmd == "status":
        out = status(p)
    elif cmd == "check":
        probs = leftovers(load_manifest(p), p)
        print("CLEAN" if not probs else "\n".join(probs))
        return 1 if probs else 0
    elif cmd == "seed":
        if load_state(p)["swapped"]:
            do_restore(p, rep, by="cli-seed")
        prepare(p, force_seed="--force" in argv)
        return 0
    else:
        print(__doc__)
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
