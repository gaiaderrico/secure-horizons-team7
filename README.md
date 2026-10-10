# MIRAGE

> Whoever breaks in steals only fakes. And if it's an AI, it tells us who sent it and why.

When an intruder opens a trap file (a "mine"), MIRAGE swaps the company's crown-jewel
files for realistic AI-forged fakes in under a second. The real files go to a locked
vault. If the intruder is an AI agent, a note in the mine makes it reveal its mission,
which we check against the logs. The SOC analyst gets one incident card with
Contain and Restore buttons.

Secure Horizons 2026, Track 2 (AI for Security & Secure AI), team 7.

Full plan, roles and timeline: https://claude.ai/artifact/FAxNLNZ893bs3dsJ6PZDUb

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Docker is required (Docker Desktop, or OrbStack on macOS).

## Run the infrastructure (victim + guard)

```bash
cp .env.example .env              # set VICTIM_PASSWORD and GUARD_TOKEN (any synthetic values)
ssh-keygen -t ed25519 -N "" -f keys/test_key   # optional: key login for automated tests (keys/ is git-ignored)
docker compose up --build -d      # add --profile core to also start Gaia's core API (once merged)
ssh -p 2222 svc_backup@localhost  # password = VICTIM_PASSWORD (jdupont works too)
```

- **victim** (`lumen-fs01`, port 2222): SSH file server. Every command (exec, interactive, scp) goes
  through `victim/mirage-shell` and lands in `/var/log/mirage/commands.jsonl`. The share is `/srv/share`
  (`~/share`, `~/company`).
- **guard**: tails the log, POSTs every event to core (`CORE_URL/events`, fail soft), and swaps the
  crown jewels for their fakes as soon as a mine is opened (by name in a command, or any read via atime).
  Control API at `http://victim:8081` (`POST /swap|/contain|/restore`, `GET /status`, header `X-Guard-Token`).
- Share content: Thomas's `python -m prepare.run_all` output in `./generated` (manifest.json, share/, stage/).
  If it's missing, a placeholder company from `mirage/fakes.py` is used. After regenerating:
  `docker compose exec guard python guard.py seed --force`.

**Demo**: `ssh -p 2222 svc_backup@localhost "cat share/00_passwords_backup.txt"` → `docker compose logs guard`
shows `CONTAINED`, and `cat share/clinical/patients.csv` now returns the fake.

**Reset** (safe to run any number of times): `docker compose exec guard python guard.py restore`, then
`docker compose exec guard python guard.py check` prints `CLEAN`. Full self-test: `bash scripts/e2e.sh 3`.

## Status

- `mirage/contracts.py`: shared types between modules. Ask Gaia before changing it.
- `mirage/fakes.py`: synthetic manifest, attack event sequences and sample files for tests and the dashboard.

## Known limitations

<!-- TODO -->
- Guard: the command log is written by the session user (mode 622), so an intruder could append fake
  lines or truncate it. Mine detection by atime does not depend on the log.
- Guard: sftp sessions are logged as one `sftp-server` command; their file reads are only caught by atime.
