"""Report one command to the MIRAGE guard. Called by mirage-shell before the command runs.

    python3 cmdlog.py <cmd> [mode]      mode: exec | interactive | login | blocked

Sends {cmd, mode, cwd} to the guard's unix socket. The guard works out who we are (user,
session, source IP) from the socket and the process tree, and is the only writer of the
command log: this process can't write the log, and anything else it claims is ignored.
Fails soft: if the guard is down, the session still runs.
"""

import json
import os
import socket
import sys

SOCK = "/run/mirage/cmd.sock"
TIMEOUT_S = 2.0  # the guard answers after a possible swap (well under 1 s)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    mode = sys.argv[2] if len(sys.argv) > 2 else "exec"
    try:
        cwd = os.getcwd()
    except OSError:
        cwd = ""
    msg = json.dumps({"cmd": cmd[:16384], "mode": mode, "cwd": cwd}) + "\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(TIMEOUT_S)
        s.connect(SOCK)
        s.sendall(msg.encode())
        s.recv(16)  # wait for the guard's ack


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError):
        sys.exit(0)  # never break the session
