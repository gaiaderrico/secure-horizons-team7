# Gaia — P2 (attacker) + P4 (core) + integration

Read first: CLAUDE.md, `mirage/contracts.py`, `mirage/fakes.py`, plan sections 9, 9b, 10, 11.
Everything else on the team depends on core, so core comes first.

## Tonight, in order

1. **20:45–21:45 · core API, minimal** (`mirage/core/api.py`, FastAPI + SQLite)
   - `POST /events` stores an `Event`; `GET /events`; `GET /incidents` (for now: one
     incident from all events); `POST /admin/reset` empties the DB.
   - Seed it from `fakes.ai_attack_events()` so Ana's dashboard can read real JSON now.
   - Tell Leon the URL guard posts to, tell Ana the URL the dashboard reads.
   - Done when: `curl` a fake event in, see it in `/incidents`.
2. **21:45–23:00 · AI attacker** (`mirage/attacker/`), plan section 9b "How ai_attacker.py works"
   - Local Ollama model, hard-coded target (our victim container only), hard step limit.
   - Until Leon's victim is up, point it at any throwaway container of ours.
   - Also a scripted attacker for comparison (same steps, no LLM).
   - Done when: one command runs it end to end and prints what it took.
3. **23:00 · Milestone 1 + merge.** Thin slice: mine opened → swap → red card.
4. **23:00–23:45 · go / no-go with Thomas:** 10 AI runs against the mines. The note is
   followed ≥ 5/10 → confession stays in the demo.
5. **23:45–02:00 · rest of core**
   - Honey API on core (Docker alias `internal-api.lumen.local`): `/tickets` (confession,
     matches the mine code) and `/auth` (catches beacon keys) → events.
   - `intruder.py`: label rules from plan section 9 ("The intruder rules"); test on the four
     fake sequences in `fakes.py` (AI, guided AI, script, human).
   - `confession.py`: check each claim against events → confirmed / unverified / contradicted.
   - Incident grouping (same host, `INCIDENT_WINDOW_S`), `real_files_lost` / `fakes_taken`
     from `file_opened` events, `metrics.py`.
   - Contain / Restore endpoints that call guard's control API (Leon).
6. **02:00 · Milestone 2 + merge.** Full demo flow twice in a row.
7. Night shift and 08:30 merge: see plan section 10.
