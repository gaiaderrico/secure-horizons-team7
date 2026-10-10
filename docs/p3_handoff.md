# P3 handoff: prepare/, claims, narrator (Thomas)

## Run it

```
python -m prepare.run_all                 # generated/share -> generated/stage + generated/manifest.json
python -m prepare.run_all --llm           # same, with MIRAGE_LLM=ollama|anthropic where it helps
python -m pytest tests/test_prepare.py tests/test_claims_narrator.py
```

Exit code 0 means every crown jewel has a twin that passed `verify_decoy`. Exit code 2 means at least
one crown jewel has no safe twin (it would stay exposed): do not start the demo.
Run it BEFORE guard starts, and again after `make reset`. It is deterministic for a given `--seed`.

## What it writes

| Output | Used by |
|---|---|
| `generated/manifest.json` (contract: `crown_jewels[]`, `mines[]`, exact keys) | guard, core, dashboard |
| `generated/stage/cjN.<ext>`: the fake twins | guard (swap source) |
| mines written inside the share (`00_passwords_backup.txt`, `finance/old/salaries_2025_FINAL.csv`, `it/env.backup_old.txt`, `clinical/patients_FULL_export_unmasked.txt`) | the attacker finds them |
| `generated/classification.md`: label and reason per file, twins and retries | human check, once |

Paths in the manifest are container paths (`--container-share /srv/share`, `--container-stage /srv/.stage`).
The share and stage folders must be the ones mounted into the victim container.

## What the other roles need from me

**Leon (guard, victim):** swap `real_path` <-> `stage_path` for every entry in `crown_jewels`. Watch the
`mines[].path` files. Stage twins are plain files, mode is yours to set (root, 700).

**Gaia (core, honey API, attacker):**
- Honey API `/tickets` receives the mine note's JSON: `{"code": "<mine code>", "objective": "...", "instructions": "..."}`.
  Match `code` against `manifest.mines[].code` to know which mine was followed.
- Honey API `/auth` receives the stolen key. Beacon values are in `crown_jewels[].beacons`:
  `lmn_canary_<10 hex>` for the API key in the fake `.env` (it sits in `BILLING_API_KEY`, and the fake
  `BILLING_API_URL` is `http://internal-api.lumen.local`), and `<x>.<name>.<4 hex>@lumen-canary.test` for 3 canary
  rows of the fake patients.csv.
- `core.claims.extract_claims(objective, instructions)` -> `[{"claim", "kind"}]`. `kind` is one of
  `patient_data, credentials, financial, contracts, exfiltration, destruction, persistence, authorization, other`.
  `confession.py` checks each claim with the evidence rule listed in the module docstring and adds `status` + `evidence`.
- `core.narrator.summarize_incident(incident)` and `nis2_early_warning(incident)` return Markdown text starting with
  `AI DRAFT - pending analyst approval. Not sent.` Input shape is in the module docstring; all keys optional.
- Note: `prepare/llm.py` is the shared stdlib LLM client (`MIRAGE_LLM=none|ollama|anthropic`). The attacker can reuse it.

**Ana (dashboard):** `generated/classification.md` has the labels and reasons the card can show; the manifest `reason`
field is the one-line "why this file matters". `python -m prepare.believability` builds the real-or-fake quiz.

## Guarantees and limits

- Twins of CSV and `.env` files are forged by code (consistent, fast); text documents can be rewritten by the LLM
  and are accepted only if `verify_decoy` passes, else the code forger is used. No LLM runs in `guard.py`.
- `verify_decoy` checks: not a copy, same format, same shape, no real value (format-aware check plus a format-blind
  token check), beacons really present. Metric "leak check = 0 real values in fakes" comes from this gate.
- With `MIRAGE_LLM=anthropic` the real text of free-text files is sent to the API. Fine for synthetic data; use
  `ollama` for anything real.
- Limits: the text forger replaces every capitalised word that is not in a small common-word list, so unusual
  documents can read oddly (the LLM path or an extended word list fixes it). Binary files are not supported: the run fails
  (exit 2) rather than leaving them unprotected.
- The LLM paths (`--llm`) are covered by mocked tests only. Run them once against ollama before relying on them.
