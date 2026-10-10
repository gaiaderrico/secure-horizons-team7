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

## Status

- `mirage/contracts.py`: shared types between modules. Ask Gaia before changing it.
- `mirage/fakes.py`: synthetic manifest, attack event sequences and sample files for tests and the dashboard.

## Known limitations

<!-- TODO -->
