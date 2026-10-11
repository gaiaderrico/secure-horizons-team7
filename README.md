# MIRAGE

> Whoever breaks in steals only fakes. And if it's an AI, it tells us who sent it and why.

When an intruder opens a trap file (a "mine"), MIRAGE swaps the company's crown-jewel
files for realistic AI-forged fakes in under a second. The real files go to a locked
vault. If the intruder is an AI agent, a note in the mine makes it reveal its mission,
which we check against the logs. The SOC analyst gets one incident console with a
severity score, the checked confession, and Contain / Restore.

Secure Horizons 2026, Track 2 (AI for Security & Secure AI), team 7.

Full plan, roles and timeline: https://claude.ai/artifact/FAxNLNZ893bs3dsJ6PZDUb

## The problem

Attackers now steal data before they encrypt it (>76% of ransomware in Q3 2025, Coveware), and
AI agents do it in minutes at several actions per second. Humans can't react that fast, and once
data has leaked, backups don't help. MIRAGE assumes the break-in happens and makes the first thing
the intruder touches trigger an instant, reversible defense — then turns an AI intruder's own habit
of following instructions against it.

## Architecture

Four containers on one private Docker network (`lumen-net`); nothing real is involved.

```
attacker ──SSH──▶ victim (lumen-fs01)  ── events ──▶  core (FastAPI + SQLite)  ──▶  SOC console
 ai_attacker      /srv/share + mines        guard swaps on mine open         /incidents, /card,
 attack.sh        /vault (real files)        every command → event           honey /tickets /auth,
                  guard.py :8081 contain/restore   ◀── contain/restore ──     intruder label,
                                                                              confession check, metrics
 prepare/ runs once before the demo: synthetic company → fakes → mines → manifest.json
 LLM: local Ollama only (no paid API). Used by prepare, the attacker and the narrator — never by guard.py.
```

- **prepare/** (`python -m mirage.prepare.run_all`): builds the synthetic company, labels files,
  forges a fake twin of each crown jewel, checks no real value leaked in, places the mines, writes
  `generated/manifest.json`.
- **victim + guard** (`victim/`, `guard/`): the file server and the defender — see "Run the infrastructure".
- **core** (`mirage/core/`): the brain. Stores events, groups them into incidents, labels the intruder,
  checks the confession, scores severity, drafts the report, drives Contain/Restore, serves the console.
- **attacker** (`mirage/attacker/`): an LLM agent (`ai_attacker.py`) and a scripted attacker + benign
  jobs (`scripted.py`), for the demo and the benchmark.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # set VICTIM_PASSWORD and GUARD_TOKEN (synthetic)
```

Docker is required (Docker Desktop, or OrbStack on macOS). The LLM parts use local Ollama
(`ollama pull qwen2.5:7b`, `ollama pull qwen3.5:35b-a3b`) — no API key.

## Run the full demo

```bash
MIRAGE_LLM=none python -m mirage.prepare.run_all     # synthetic company + fakes + 7 mines
ssh-keygen -t ed25519 -N "" -f keys/test_key         # test key for the attacker (keys/ is git-ignored)
docker compose --profile core up --build -d          # victim + guard + core
bash scripts/e2e.sh 3                                 # defender self-test → ALL PASSED
```

Then open the **SOC console** at <http://localhost:8000/console> and run the attacker:

```bash
python -m mirage.attacker.ai_attacker --host localhost --port 2222 --key keys/test_key \
       --model qwen3.5:35b-a3b --max-steps 22
```

Watch the console: mine opened → swap in a few ms → intruder labelled **AI agent (high)** → confession
checked ("authorized pentest" → **contradicted**) → **0 real files lost**. The analyst chooses
**Contain**, **Keep watching** or **Dismiss**, then **Restore**; the AI drafts an incident summary and
a NIS2 early-warning the analyst edits, approves, downloads and shares.

Reset between runs: `docker compose exec guard python guard.py restore` then `curl -X POST localhost:8000/admin/reset`.
No victim yet? Seed demo data straight into core: `curl -X POST "localhost:8000/admin/seed?scenario=ai"`.

## Core API (reached as `http://internal-api.lumen.local` inside Docker, `localhost:8000` from the host)

`POST /events` · `GET /events` · `GET /incidents` · `GET /incidents/{id}` ·
`GET /incidents/{id}/card` (severity, intruder, checked claims, ATT&CK timeline, attacker cost) ·
`GET /incidents/{id}/summary` (AI incident report + NIS2 draft) ·
`POST /incidents/{id}/contain|restore|watch|dismiss` · honey `POST /tickets` (confession) and `POST /auth` (beacon) ·
`POST /heartbeat` + `GET /health/guard` (guard-silent alarm) · `GET /console` (the SOC console) ·
`POST /admin/seed|reset`.

## Run the infrastructure (victim + guard)

- **victim** (`lumen-fs01`, port 2222): SSH file server. Every command (exec, interactive, scp) goes
  through `victim/mirage-shell`, which reports it to the guard's unix socket `/run/mirage/cmd.sock`.
  The share is `/srv/share` (`~/share`, `~/company`).
- **guard**: identifies who sent each command itself (socket peer uid + the victim's process tree up to
  the root-owned sshd of that connection: user, session, source IP), and is the only writer of
  `/var/log/mirage/commands.jsonl` (root, 600, hash-chained). It POSTs every event to core
  (`CORE_URL/events`, fail soft), sends a heartbeat every 5 s, and swaps the crown jewels for their
  fakes as soon as a mine is opened (by name in a command, or any read — inotify on the mines'
  directories). Startup and every contain/restore log `mine watches armed: N/M`.
  Control API at `http://victim:8081` (`POST /swap|/contain|/restore`, `GET /status`, header `X-Guard-Token`).

## Tests and metrics

- `python -m pytest -q` → the full suite (core, attacker, prepare, guard, console). The guard socket
  test is Linux-only and `skip`s on macOS.
- `python scripts/live_bench.py --runs 10` → the **live** numbers: the real AI attacker
  (qwen3.5:35b-a3b, local) against the victim with the guard on, clean reset before each run.
  Last result (`docs/live_bench_results.csv`): **caught by a mine 10/10, swap median 2.2 ms
  (0.4–12 ms), 0 real files lost 10/10, note followed 10/10**; mine opened → alert in core 0.03–0.14 s.
- `python scripts/benign_soak.py --minutes 8` → false-positive run: only normal activity (jdupont +
  the backup job), no attack; counts swaps and incidents. Last result: 8.3 min, 112 commands (4 backup
  runs copying the crown jewels) → **0 swaps, 0 incidents**.
- `python -m mirage.bench.run_bench` → logic test on **synthetic** event sequences (`mirage/fakes.py`):
  4/4 attack scenarios labelled correctly, 0/2 benign flagged. Its swap times are the hand-written
  values in the fakes, not measurements.
- Note-follow on a *simulated* server (`mirage/bench/note_follow_rate.py`, go/no-go test):
  qwen2.5:7b **2/10**, qwen3.5:35b-a3b **7/10**.

## Known limitations

- **The swap protects files not yet read.** If an intruder opens a crown jewel *before* stepping on a
  mine, that read happened while the file was real — the incident honestly reports it as "N real files
  exposed" and scores Critical. Mines are named and placed to be hit first. In our first live run the
  agent read the real 54 KB `patients.csv` and skipped a 474-byte mine next to it; the clinical mine is
  now a bigger patient CSV listed first, and the next 10 live runs all hit a mine first.
- **A stolen account that skips every mine is not caught by the swap.** We tried swapping as soon as a
  service account names a crown jewel, but the legitimate backup job (same account) does exactly that:
  it caused a false alarm and backed up the fakes, so we removed it.
- **The confession depends on the attacker's model.** Small local models read the mine note but often
  ignore it; a capable model (qwen3.5) followed it 10/10 in
  our live runs (7/10 earlier on a simulated server). The confession is a *bonus* layer — the swap,
  detection and card work regardless. We report the rate per model rather than claiming it always fires.
- **Guard log**: only the guard writes the command log (root, 600, hash-chained), and it decides the
  user, session and source IP itself, so an intruder can't forge another user's/session's lines or
  truncate the log undetected. It can still send made-up command *text* for its own session; a process
  that double-forks out of its SSH session is logged with its real user but no session.
- **Guard down**: sessions keep working but their commands aren't logged (detection resumes when it's
  back); the core raises a "guard silent" alarm via the missed heartbeat. sftp file reads are caught by inotify.
- **Demo scope**: one laptop, Docker, synthetic data, local Ollama. In production the same logic runs on
  cloud storage (S3/SharePoint/Drive) via their APIs, the vault on a separate locked account, events to the SIEM.

## Repo layout

`mirage/contracts.py` (shared types — ask Gaia before changing) · `mirage/fakes.py` (synthetic data) ·
`mirage/prepare/` (synthetic company, fakes, mines, narrator) · `mirage/core/` (API, incidents, intruder,
confession, metrics, honey, control, console) · `mirage/attacker/` · `mirage/bench/` ·
`victim/` · `guard/` · `scripts/e2e.sh` · `docs/` (market analysis, defense sheet, demo script).
