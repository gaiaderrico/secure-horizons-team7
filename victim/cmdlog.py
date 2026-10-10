"""Append one command record to the MIRAGE command log (JSON lines). Called by mirage-shell.

    python3 cmdlog.py <cmd> [mode]      mode: exec | interactive | login | blocked

The log file is created by the entrypoint with mode 622: users can append, not read.
"""

import json
import os
import sys
import time

LOG = "/var/log/mirage/commands.jsonl"  # contracts.COMMAND_LOG


def record(cmd: str, mode: str) -> dict:
    conn = os.environ.get("SSH_CONNECTION", "").split()
    try:
        cwd = os.getcwd()
    except OSError:
        cwd = ""
    return {
        "ts": time.time(),
        "session": os.environ.get("MIRAGE_SID", ""),
        "user": os.environ.get("USER", ""),
        "src_ip": conn[0] if conn else "",
        "cmd": cmd,
        "mode": mode,
        "cwd": cwd,
    }


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    mode = sys.argv[2] if len(sys.argv) > 2 else "exec"
    line = (json.dumps(record(cmd, mode)) + "\n").encode()
    fd = os.open(LOG, os.O_WRONLY | os.O_APPEND)  # one write = one atomic line
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
