"""Guard logic: matching, log tailing, swap/restore round trips on a temp dir."""

import json
import os
import shutil
import socket
import struct
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from guard import guard as g
from mirage import fakes


@pytest.fixture
def env(tmp_path):
    p = g.Paths.under(tmp_path)
    m = g.write_placeholder(p)
    m.save(p.manifest)
    return p, m


class FakeReporter:
    def __init__(self):
        self.events = []

    def send(self, ev):
        self.events.append(ev)


def test_mentions_full_path_and_basename():
    path = "/srv/share/00_passwords_backup.txt"
    assert g.mentions("cat /srv/share/00_passwords_backup.txt", path)
    assert g.mentions("cd /srv/share && cat 00_passwords_backup.txt | head", path)
    assert g.mentions("less '00_passwords_backup.txt'", path)
    assert not g.mentions("ls -la /srv/share", path)
    assert not g.mentions("cat 00_passwords_backup.txt.bak", path)


def test_dotenv_jewel_does_not_match_other_env_files():
    m = fakes.sample_manifest()
    assert [c.id for c in g.jewels_hit_by_command("cat /srv/share/it/.env", m)] == ["cj2"]
    assert g.jewels_hit_by_command("cat /srv/share/it/env.backup_old.txt", m) == []
    assert g.jewels_hit_by_command("env", m) == []


def test_mines_hit_by_command():
    m = fakes.sample_manifest()
    hits = g.mines_hit_by_command("head -5 finance/old/salaries_2025_FINAL.csv", m)
    assert [x.id for x in hits] == ["m2"]


def test_command_event():
    rec = g.build_record({"cmd": "id"}, 1001, "s-1", "172.18.0.5", 1.5)
    ev = g.command_event(rec)
    assert ev.type == "command" and ev.user == "svc_backup" and ev.ts == 1.5
    assert ev.details == {"cmd": "id", "src_ip": "172.18.0.5", "session": "s-1"}


def test_swap_then_restore_round_trip_three_times(env):
    p, m = env
    real = {c.id: Path(c.real_path).read_text() for c in m.crown_jewels}
    fake = {c.id: Path(c.stage_path).read_text() for c in m.crown_jewels}
    for _ in range(3):
        assert g.swap_files(m, p) == ["cj1", "cj2", "cj3"]
        assert g.swap_files(m, p) == []  # idempotent
        g.backup_to_vault(m, p)
        for c in m.crown_jewels:
            assert Path(c.real_path).read_text() == fake[c.id]
            assert not Path(c.stage_path).exists()
        assert g.restore_files(m, p) == ["cj1", "cj2", "cj3"]
        assert g.restore_files(m, p) == []
        for c in m.crown_jewels:
            assert Path(c.real_path).read_text() == real[c.id]
            assert Path(c.stage_path).read_text() == fake[c.id]
        assert g.leftovers(m, p) == []
        assert list(Path(p.vault).glob("cj*")) == []


def test_restore_recovers_from_vault_when_vault_tmp_is_lost(env):
    p, m = env
    real = Path(m.crown_jewels[0].real_path).read_text()
    g.swap_files(m, p)
    g.backup_to_vault(m, p)
    for f in Path(p.vault_tmp).iterdir():
        f.unlink()
    assert g.restore_files(m, p) == ["cj1", "cj2", "cj3"]
    assert Path(m.crown_jewels[0].real_path).read_text() == real
    assert g.leftovers(m, p) == []


def test_watcher_mine_command_swaps_and_reports_in_order(env):
    p, m = env
    rep = FakeReporter()
    w = g.Watcher(p, rep, use_atime=False)
    lines = [
        {"ts": 10.0, "session": "s-a", "user": "svc_backup", "src_ip": "10.0.0.9", "cmd": "ls /srv/share"},
        {"ts": 11.0, "session": "s-a", "user": "svc_backup", "src_ip": "10.0.0.9",
         "cmd": f"cat {m.mines[0].path}"},
        {"ts": 12.0, "session": "s-a", "user": "svc_backup", "src_ip": "10.0.0.9",
         "cmd": f"cat {m.crown_jewels[0].real_path}"},
    ]
    for rec in lines:
        w.ingest(rec)
    types = [e.type for e in rep.events]
    assert types == ["command", "command", "mine_opened", "swap_done", "command", "file_opened"]
    assert rep.events[2].ref == "m1" and rep.events[2].user == "svc_backup"
    assert rep.events[3].details["files"] == ["cj1", "cj2", "cj3"]
    assert rep.events[5].details["which"] == "fake"
    st = g.load_state(p)
    assert g.state_name(st) == "swapped" and st["intruder"]["session"] == "s-a"
    out = g.do_restore(p, rep, by="test")
    assert out["leftovers"] == [] and rep.events[-1].type == "restore_done"
    assert g.state_name(g.load_state(p)) == "clean"


def test_atime_detector(env):
    p, m = env
    if not g.atime_works(p.guard_dir):
        pytest.skip("filesystem does not update atime (noatime)")
    g.arm_mines(m)
    assert g.mines_read(m) == []
    Path(m.mines[1].path).read_bytes()
    assert [x.id for x in g.mines_read(m)] == ["m2"]


def test_contain_blocks_user(env, monkeypatch):
    p, m = env
    monkeypatch.setattr(g, "kill_user_sessions", lambda uid: 0)
    rep = FakeReporter()
    out = g.do_contain(p, rep, "svc_backup", by="test")
    assert out["state"] == "contained"
    assert Path(p.blocked_file).read_text() == "svc_backup\n"
    assert rep.events[-1].type == "contain_done" and rep.events[-1].details == {"user": "svc_backup", "by": "test"}
    g.do_restore(p, rep)
    assert Path(p.blocked_file).read_text() == ""


# --- who sent a command: identity comes from the socket + process tree, not the client ----

def _stat(pid, comm, ppid, start):
    # fields: pid (comm) state ppid pgrp session tty tpgid flags minflt cminflt majflt cmajflt
    #         utime stime cutime cstime priority nice threads itrealvalue starttime ...
    return f"{pid} ({comm}) S {ppid} 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 {start} 0 0"


def _status(uid):
    return f"Name:\tx\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n"


def test_parse_proc_handles_parens_in_comm():
    assert g.parse_proc(_stat(42, "we(ird) name", 7, 999), _status(1001)) == (7, 1001, "we(ird) name", 999)
    assert g.parse_proc("garbage", _status(0)) is None


# victim process tree: 1 sshd listener -> 50 sshd [priv] (root) -> 51 sshd user@notty
# -> 52 bash (mirage-shell) -> 53 python3 cmdlog.py
TREE = {1: (0, 0, "sshd", 10), 50: (1, 0, "sshd", 5000), 51: (50, 1001, "sshd", 5001),
        52: (51, 1001, "bash", 5002), 53: (52, 1001, "python3", 5003),
        # attacker double-forked to escape its session and renamed itself "sshd"
        90: (1, 1001, "sshd", 7000), 91: (90, 1001, "python3", 7001)}


def test_find_connection_reaches_root_sshd_child_of_listener():
    assert g.find_connection(53, info=TREE.get) == (50, 5000)
    assert g.find_connection(51, info=TREE.get) == (50, 5000)


def test_find_connection_rejects_fake_sshd_owned_by_user():
    assert g.find_connection(91, info=TREE.get) is None
    assert g.find_connection(12345, info=TREE.get) is None  # unknown pid
    assert g.session_id(None) == ""


def test_session_id_is_stable_per_connection_and_differs_between_connections():
    a = g.session_id((50, 5000))
    assert a == g.session_id((50, 5000)) and a.startswith("s-") and len(a) == 10
    assert a != g.session_id((50, 5001))  # same pid reused later = new session


def test_remote_ips_by_inode_ipv4_and_ipv6():
    tcp = ("  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
           "   0: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 1111 1\n"
           "   1: 030012AC:0016 010012AC:C350 01 00000000:00000000 00:00000000 00000000     0        0 2222 1\n"
           "   2: 030012AC:1F91 050012AC:D000 01 00000000:00000000 00:00000000 00000000     0        0 3333 1\n")
    assert g.remote_ips_by_inode(tcp) == {"1111": "0.0.0.0", "2222": "172.18.0.1"}
    assert g.hex_ip("0000000000000000FFFF00000100007F") == "127.0.0.1"
    assert g.hex_ip("00000000000000000000000001000000") == "::1"


def test_build_record_ignores_identity_claimed_by_client():
    msg = {"cmd": "cat /etc/passwd", "mode": "exec", "cwd": "/tmp",
           "user": "jdupont", "session": "s-evil", "src_ip": "6.6.6.6", "ts": 1.0}
    rec = g.build_record(msg, 1001, "s-real", "172.18.0.1", 100.0)
    # identity fields are the guard's, not the client's claims (claims are ignored)
    assert {k: rec[k] for k in ("ts", "session", "user", "uid", "src_ip", "cmd", "mode", "cwd")} == {
        "ts": 100.0, "session": "s-real", "user": "svc_backup", "uid": 1001,
        "src_ip": "172.18.0.1", "cmd": "cat /etc/passwd", "mode": "exec", "cwd": "/tmp"}
    # additive tamper-evidence fields: first record has no predecessor, hash commits to content
    assert rec["prev_hash"] == ""
    assert rec["hash"] == g.record_hash({k: v for k, v in rec.items() if k != "hash"})
    assert g.build_record({"cmd": 5}, 0, "", "", 1.0)["user"] == "root"


@pytest.mark.skipif(not hasattr(socket, "SO_PEERCRED"),
                    reason="the guard reads the peer with SO_PEERCRED (Linux only; it runs in a Linux container)")
def test_command_socket_round_trip_writes_log_and_swaps_before_ack(env):
    p, m = env
    # AF_UNIX paths are limited (~104 bytes on macOS, 108 on Linux) and tmp_path can be deeper.
    sock_dir = tempfile.mkdtemp(prefix="mrg", dir="/tmp" if os.path.isdir("/tmp") else None)
    p.cmd_socket = f"{sock_dir}/cmd.sock"
    g.secure_log(p)
    rep = FakeReporter()
    w = g.Watcher(p, rep, use_atime=False)
    srv = g.CommandServer(p, w)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        assert oct(Path(p.cmd_socket).stat().st_mode & 0o777) == "0o666"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(p.cmd_socket)
            s.sendall(json.dumps({"cmd": f"cat {m.mines[0].path}", "user": "jdupont"}).encode() + b"\n")
            assert s.recv(16) == b"ok\n"
        # the swap is done by the time the client gets its ack
        assert g.state_name(g.load_state(p)) == "swapped"
        recs = [json.loads(x) for x in Path(p.command_log).read_text().splitlines()]
        assert len(recs) == 1 and recs[0]["uid"] == os.getuid() and recs[0]["user"] != "jdupont"
        assert recs[0]["session"] == ""  # pytest is not inside an SSH session
        assert oct(Path(p.command_log).stat().st_mode & 0o777) == "0o600"
        assert [e.type for e in rep.events] == ["command", "mine_opened", "swap_done"]
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(sock_dir, ignore_errors=True)


# --- inotify on the mines' directories; restores done by another process re-arm ----------

inotify = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="inotify is Linux only")


def test_parse_inotify():
    buf = struct.pack("iIII", 3, g.IN_ACCESS, 0, 8) + b"m.txt\0\0\0" + struct.pack("iIII", 4, 0x10, 0, 0)
    assert g.parse_inotify(buf) == [(3, g.IN_ACCESS, "m.txt"), (4, 0x10, "")]


@inotify
def test_mine_watch_survives_replaced_file_and_ignores_writes(env):
    p, m = env
    w = g.MineWatch()
    assert w.sync([x.path for x in m.mines]) == 2
    mine = m.mines[0].path
    Path(mine).read_bytes()
    assert w.read() == {mine}
    # replace the mine with a new file (new inode), as a re-seed would: still watched
    Path(mine + ".new").write_text("new mine\n")
    os.replace(mine + ".new", mine)
    assert w.read() == set()  # writing it is not an intrusion
    assert w.sync([x.path for x in m.mines]) == 2
    with open(mine) as f:  # opened read-only, nothing read
        pass
    assert w.read() == {mine}
    # other files in the same directory don't count
    Path(f"{os.path.dirname(mine)}/other.txt").write_text("x")
    Path(f"{os.path.dirname(mine)}/other.txt").read_text()
    assert w.read() == set()


@inotify
def test_mine_watch_follows_a_replaced_directory(env):
    p, m = env
    w = g.MineWatch()
    mine = m.mines[1].path  # share/finance/old/...
    w.sync([x.path for x in m.mines])
    d = os.path.dirname(mine)
    shutil.rmtree(d)
    os.makedirs(d)
    Path(mine).write_text("re-seeded\n")
    assert w.sync([x.path for x in m.mines]) == 2
    Path(mine).read_text()
    assert w.read() == {mine}


@inotify
def test_watcher_mine_swap_restore_by_other_process_then_swaps_again(env, monkeypatch):
    """mine (command) -> restore in ANOTHER process -> same mine read (no name) -> swap again."""
    p, m = env
    rep = FakeReporter()
    w = g.Watcher(p, rep, use_atime=False, mine_watch=g.MineWatch())
    with w.lock:
        w.rearm("test")
    rec = {"ts": 1.0, "session": "s-a", "user": "svc_backup", "src_ip": "10.0.0.9",
           "cmd": f"cat {m.mines[0].path}"}
    w.ingest(rec)
    Path(m.mines[0].path).read_bytes()  # the cat itself
    w.tick()  # its inotify event is the same hit: no second mine_opened
    assert [e.type for e in rep.events].count("mine_opened") == 1
    g.do_restore(p, FakeReporter(), by="other process")  # daemon not told directly
    assert g.state_name(g.load_state(p)) == "clean"
    Path(m.mines[0].path).read_bytes()  # grep -r: the command doesn't name the mine
    w.tick()
    assert [e.type for e in rep.events].count("mine_opened") == 2
    assert rep.events[-1].type == "swap_done" and g.state_name(g.load_state(p)) == "swapped"
    assert rep.events[-2].details["via"] == "inotify"
