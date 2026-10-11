# MIRAGE — handoff & action plan (for Thomas and Ana)

Status: core + infra + attacker + SOC console + all docs are on `main` (247 tests pass, gitleaks clean).
This is what was built overnight, how to **verify** it (don't trust it blindly), and exactly what to do
before the Sunday 12:00 freeze. Read it on GitHub, then work through the checklists.

> Honesty note: a lot was generated fast. Treat every **claim** as "verify before you present it".
> Two kinds of claim: (a) **machine-checkable** — re-run a command, it either passes or it doesn't;
> (b) **external facts** (market stats, regulations, team names, pricing) — check the source yourself.
> The "Verify" sections below say which is which.

---

## 0. First: get the code and run it (everyone, ~15 min)

```bash
git checkout main && git pull
python3 -m venv .venv && source .venv/bin/activate   # if you don't have one
pip install -r requirements.txt
python -m pytest -q          # expect: ~247 passed, few skipped (Linux-only guard tests skip on macOS)
```
If `pytest` is green, the code does what the tests say. If not, that's the first thing to fix — ask
Claude: *"pytest fails with <paste the error> — what's wrong and how do I fix it?"*

Then run the live demo once (needs Docker + Ollama; see §4). If it works end to end, you understand
the product.

---

## 1. What exists, and where (so you understand the project)

| Part | Where | What it does |
|---|---|---|
| Shared contracts | `mirage/contracts.py` | Types every module agrees on. Don't change without telling Gaia. |
| Prepare (Thomas) | `mirage/prepare/` | Synthetic company, fake twins, leak check, mines, `narrator.py` (report + NIS2). |
| Core (Gaia) | `mirage/core/` | API, incidents, intruder label, confession check, metrics, honey `/tickets` `/auth`, contain/restore, heartbeat, the **SOC console** (`console_page.py` → `/console`). |
| Infra (Leon) | `victim/`, `guard/`, `docker-compose.yml`, `scripts/e2e.sh` | File server + the guard that swaps and logs. |
| Attacker (Gaia) | `mirage/attacker/` | `ai_attacker.py` (LLM agent) + `scripted.py` (baseline). |
| Benchmark | `mirage/bench/run_bench.py` | The defense-sheet numbers. |
| Docs | `docs/` | `defense_sheet.md`, `demo_script.md`, `market_analysis.md`, this file. |
| Pitch deck | claude.ai artifact (ask Gaia for the link) | 8 slides. |

**Understand it fast — ask Claude** (in this repo, so it can read the files):
- *"Read CLAUDE.md and mirage/contracts.py and explain MIRAGE to me in 5 minutes like I've never seen it."*
- *"Walk me through what happens, file by file, from an AI opening a mine to the incident card."*
- *"Explain mirage/core/console_page.py — what does each part of the SOC console show?"*

---

## 2. Verify it (this is the anti-hallucination pass — do NOT skip)

### 2a. Machine-checkable (just run these; they either confirm or they don't)
- **Tests:** `python -m pytest -q` → ~247 passed.
- **Metrics:** `python scripts/live_bench.py --runs 10` → the live numbers on the defense sheet (10/10 caught,
  swap median 2.2 ms, 0 real files lost). `python -m mirage.bench.run_bench` is only a logic test on
  synthetic events (its swap times are hand-written). If a command disagrees with a slide, fix the slide.
- **Live demo:** `bash scripts/e2e.sh 3` → `ALL PASSED`. Then the full run in §4.
- **Secrets:** `gitleaks git .` → `no leaks found`.

### 2b. External facts — CHECK THE SOURCE yourself (these were NOT independently verified)
Open `docs/market_analysis.md` and `docs/defense_sheet.md` and confirm each figure against its cited
source before anyone says it on stage:
- ">76% of ransomware exfiltrate" (Coveware Q3 2025), "$4.44M average breach", "279 days to contain in
  health", "US healthcare costliest for 14 years" (IBM), "TAM $2.7B→$7.3B" (IMARC), "~15,000 NIS2
  entities in France", "Thinkst Canary ~$9,900/yr" (Vendr), "GTG-1002 / 80–90% by AI" (Anthropic).
- **Team names and roles** on the final deck slide — Gaia guessed them; fix surnames/roles.
- **Pricing** on the deck is a placeholder `[figure to define]` — decide it or say "TBD" out loud.
- The **NIST CSF / ATT&CK / ATLAS / OWASP** mappings in `defense_sheet.md` are reasonable but sanity-check
  the technique IDs (T1059, T1083, T1005, T1552.001, T1078; AML.T0051) against MITRE's site.

If a number can't be sourced, soften it ("industry reports suggest…") or drop it. Judges punish a wrong
confident stat harder than a missing one.

---

## 3. GitHub / integration actions (Gaia or whoever merges)

- Everything is on `main` and `gaia`. **Ana has 4 commits on branch `ana` not yet merged** — review and
  merge them: `git checkout main && git pull && git merge origin/ana` (resolve any conflict, run
  `pytest`, push). Ask Claude: *"merge origin/ana into main, run the tests, and tell me what changed."*
- One branch per person; merge to `main` only when `pytest` is green. Run `gitleaks git .` before every push.
- Never commit `.env`, `generated/`, `keys/` (already git-ignored). `GUARD_TOKEN` and `VICTIM_PASSWORD`
  live only in your local `.env`.

---

## 4. Make the demo video (Ana, ~1–2 h incl. retries)

The full script is `docs/demo_script.md` — follow it. Setup:
```bash
MIRAGE_LLM=none python -m mirage.prepare.run_all
ssh-keygen -t ed25519 -N "" -f keys/test_key
docker compose --profile core up --build -d
docker compose exec guard python guard.py restore && curl -s -X POST localhost:8000/admin/reset
```
Two windows: left = the attacker terminal, right = `http://localhost:8000/console`. Run:
```bash
python -m mirage.attacker.ai_attacker --host localhost --port 2222 --key keys/test_key --model qwen3.5:35b-a3b --max-steps 22
```
Record 2–3 min with a screen recorder, Wi-Fi off. **The AI is stochastic** — if a take skips the mine or
the confession, retry, or load the incident instantly with `curl -X POST "localhost:8000/admin/seed?scenario=ai"`
and narrate the console. **Keep the best take as a backup** to play if the live demo misbehaves on stage.

Ask Claude (in the repo) if stuck: *"I'm recording the MIRAGE demo from docs/demo_script.md; the
attacker did X instead of opening a mine — how do I get a clean run?"* or *"the /console page shows no
incident — what reset commands do I run?"*

---

## 5. Learn the pitch (presenter + everyone)

- Open the deck (ask Gaia for the link) and read `docs/demo_script.md` — the deck and the demo tell the
  same story: **threat → swap in <1s → AI confesses → we check it → 0 real files lost → analyst decides.**
- The one-liner: *"Whoever breaks in steals only fakes — and if it's an AI, it tells us who sent it."*
- Rehearse the 3 answers judges will ask:
  1. *"What's new vs Canary / SentinelOne?"* → they alert; we **swap the real data out of reach** on first
     touch, and we're the only one in the "lightweight + protects real data" quadrant (see the Competition slide).
  2. *"What if the AI doesn't follow the note?"* → the swap, detection and card still work; the confession
     is a bonus, and we report the rate per model (10/10 live with the big model, 2/10 for the small one on a simulated server).
  3. *"What if the attacker kills the guard / deletes tracks?"* → the log is root-only + hash-chained, and
     the console raises a **GUARD SILENT** alarm via the missed heartbeat (you can demo this live).
- Ask Claude to drill you: *"Act as a hackathon judge for a deception-defense product and ask me 8 hard
  questions, then critique my answers."*

---

## 6. Priorities before Sunday 12:00 (highest impact first)

1. **Everyone:** pull `main`, `pytest` green, run the live demo once. (You must be able to run it.)
2. **Ana:** record the demo video + backup take (§4). Fix team names/roles on the deck. Decide pricing or say TBD.
3. **Thomas + Ana:** the verification pass (§2b) — source-check every stat in the deck and defense sheet.
4. **Gaia:** merge Ana's branch; `make reset`-style one-command reset if time; keep `main` green.
5. **Presenter:** rehearse the pitch + the 3 judge answers (§5), timed to the demo.
6. **Nice-to-have if time:** polish one slide visually; add a screenshot of the console to the deck.
7. **Freeze discipline:** no risky merges after ~10:00 Sunday; last `pytest` + `gitleaks` + one full demo rehearsal before submitting.

---

## 7. Known weak spots to be honest about (don't let a judge surprise you)

- The swap protects files **not yet read**; a jewel opened before a mine is reported as "exposed"
  (Critical). Demo: trigger a mine first.
- The confession depends on the attacker's model (big model 10/10 live; small model 2/10 on a simulated server) — it's a bonus layer.
- Demo is one laptop + synthetic data + local Ollama; production maps to cloud-storage APIs (say this).
- Pricing and exact market numbers need the §2b check.

Questions on the code → ask Claude in the repo. Questions on what was built and why → this file + CLAUDE.md
+ the plan artifact linked in the README.
