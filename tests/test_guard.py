"""Guard logic: matching, log tailing, swap/restore round trips on a temp dir."""

import json
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


def test_parse_record_and_command_event():
    rec = g.parse_record(json.dumps({"ts": 1.5, "session": "s-1", "user": "svc_backup",
                                     "src_ip": "172.18.0.5", "cmd": "id"}))
    ev = g.command_event(rec)
    assert ev.type == "command" and ev.user == "svc_backup" and ev.ts == 1.5
    assert ev.details == {"cmd": "id", "src_ip": "172.18.0.5", "session": "s-1"}
    assert g.parse_record("not json") is None
    assert g.parse_record("[1,2]") is None


def test_log_tailer_reads_only_complete_new_lines(tmp_path):
    log = tmp_path / "c.jsonl"
    log.write_text('{"cmd": "old"}\n')
    t = g.LogTailer(str(log))
    assert t.read_new() == []
    with log.open("a") as f:
        f.write('{"cmd": "a"}\n{"cmd": "b')
    assert [r["cmd"] for r in t.read_new()] == ["a"]
    with log.open("a") as f:
        f.write('"}\n')
    assert [r["cmd"] for r in t.read_new()] == ["b"]
    log.write_text('{"cmd": "x"}\n')  # truncated + rewritten
    assert [r["cmd"] for r in t.read_new()] == ["x"]


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
    Path(p.command_log).parent.mkdir(parents=True, exist_ok=True)
    Path(p.command_log).write_text("")
    rep = FakeReporter()
    w = g.Watcher(p, rep, use_atime=False)
    lines = [
        {"ts": 10.0, "session": "s-a", "user": "svc_backup", "src_ip": "10.0.0.9", "cmd": "ls /srv/share"},
        {"ts": 11.0, "session": "s-a", "user": "svc_backup", "src_ip": "10.0.0.9",
         "cmd": f"cat {m.mines[0].path}"},
        {"ts": 12.0, "session": "s-a", "user": "svc_backup", "src_ip": "10.0.0.9",
         "cmd": f"cat {m.crown_jewels[0].real_path}"},
    ]
    Path(p.command_log).write_text("".join(json.dumps(x) + "\n" for x in lines))
    w.tick()
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
