"""Command-log hash chain: verify_log accepts an untouched chain and flags any tampering.

The log file is already append-only and root-only (Leon's permissions); this adds
tamper-EVIDENCE on top so we can prove after the fact that no line was changed or removed.
"""

import json
from pathlib import Path

import pytest

from guard import guard as g


def _write_chain(path, msgs):
    """Append real records built through build_record, linking each to the previous hash."""
    prev = ""
    recs = []
    with open(path, "a") as f:
        for i, msg in enumerate(msgs):
            rec = g.build_record(msg, 1001, "s-a", "10.0.0.9", float(i), prev_hash=prev)
            prev = rec["hash"]
            recs.append(rec)
            f.write(json.dumps(rec) + "\n")
    return recs


@pytest.fixture
def log(tmp_path):
    return str(tmp_path / "commands.jsonl")


def test_verify_ok_on_clean_chain(log):
    _write_chain(log, [{"cmd": "ls"}, {"cmd": "id"}, {"cmd": "cat secret"}])
    ok, reason = g.verify_log(log)
    assert ok is True and "3 records" in reason


def test_empty_log_is_ok(log):
    Path(log).write_text("")
    assert g.verify_log(log) == (True, "ok: 0 records")


def test_chain_links_across_records(log):
    recs = _write_chain(log, [{"cmd": "a"}, {"cmd": "b"}])
    assert recs[0]["prev_hash"] == ""
    assert recs[1]["prev_hash"] == recs[0]["hash"]


def test_detects_modified_line(log):
    _write_chain(log, [{"cmd": "ls"}, {"cmd": "cat /etc/passwd"}, {"cmd": "whoami"}])
    lines = Path(log).read_text().splitlines()
    rec = json.loads(lines[1])
    rec["cmd"] = "ls"  # attacker rewrites a command but cannot recompute the whole chain
    lines[1] = json.dumps(rec)
    Path(log).write_text("\n".join(lines) + "\n")
    ok, reason = g.verify_log(log)
    assert ok is False and "line 2" in reason


def test_detects_deleted_line(log):
    _write_chain(log, [{"cmd": "ls"}, {"cmd": "cat /etc/passwd"}, {"cmd": "whoami"}])
    lines = Path(log).read_text().splitlines()
    del lines[1]  # drop the incriminating middle record
    Path(log).write_text("\n".join(lines) + "\n")
    ok, reason = g.verify_log(log)
    assert ok is False and "broken chain link" in reason


def test_build_record_chain_feeds_verify(log):
    # build records exactly as the server does (feeding prev_hash forward), then verify
    msgs = [{"cmd": f"cmd{i}", "mode": "exec", "cwd": "/tmp"} for i in range(5)]
    _write_chain(log, msgs)
    assert g.verify_log(log)[0] is True


def test_missing_log_file_reports_not_ok(tmp_path):
    ok, reason = g.verify_log(str(tmp_path / "does_not_exist.jsonl"))
    assert ok is False and "cannot read log" in reason
