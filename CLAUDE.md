# MIRAGE — instructions for Claude Code (and humans)

Secure Horizons 2026 hackathon, Track 2, team 7. Code freeze Sunday 12:00, so prefer
simple, working, tested code over clever code.

MIRAGE: when an intruder opens a trap file ("mine") on the company file server, the
crown-jewel files are swapped for AI-forged fakes in under a second (real files go to a
locked vault). If the intruder is an AI agent, a note in the mine makes it reveal its
mission via our internal "honey" API; core checks those claims against the logs. The SOC
analyst sees one incident card with Contain / Restore.

Full plan (architecture, contracts, roles, timeline): https://claude.ai/artifact/FAxNLNZ893bs3dsJ6PZDUb
Sections 9, 9b, 10 and 11 are the technical ones.

## Rules

- `mirage/contracts.py` is the contract between modules. Never edit it unless the task
  says so; if it must change, stop and say why (owner: Gaia).
- `mirage/fakes.py` has synthetic manifests, attack event sequences and sample files.
  Build and test against it instead of waiting for other modules.
- Only edit your own module's files and their tests.
- Pure logic in small functions with no Docker/network/OS calls, tested in `tests/`.
- Before every commit: `python -m pytest -q` passes.
- One branch per person; Gaia merges into `main` at 23:00, 02:00, 08:30.
- No secrets, no real personal data. `.env` is git-ignored. Run `gitleaks git .` before pushing.
- LLM: local Ollama only (`MIRAGE_LLM=ollama`, models `qwen2.5:7b`, `qwen3.5:35b-a3b`).
  No paid API. From containers, Ollama is at `http://host.docker.internal:11434`.
- Attacks only against our own containers on the Docker network. Synthetic data only.
- Python 3.12+ (local venv: `.venv`). Docker via OrbStack (`~/.orbstack/bin` on PATH).

## Owners

| Area | Owner |
|---|---|
| `docker-compose.yml`, victim container, guard (swap, contain/restore), command log | Leon (P1) |
| `mirage/prepare/` (synthetic company, labelling, fake twins, leak check, mines), claim extraction, narrator | Thomas (P3) |
| `mirage/attacker/` (AI attacker, scripted attacker, benign jobs, bench), `mirage/core/` (API, honey API, incidents, intruder label, confession check, metrics), merges | Gaia (P2 + P4) |
| `mirage/dashboard/`, deck, video, defense sheet, README | Ana (P5) |
