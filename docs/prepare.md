# Preparing the swap: classify, forge, verify, mines

MIRAGE only works if the fake files are ready *before* anyone attacks. This stage runs once, ahead of time,
and produces everything the guard needs. Nothing here runs during the attack, and no AI model runs in the guard.

## What it does

1. **Classify** (`mirage/prepare/classify.py`): reads the file share and picks the crown jewels: the files
   whose loss would hurt (patient records, credentials, a supplier contract). Each gets a one-line reason
   and a category: `personal_data`, `credentials` or `business`.
2. **Forge** (`forge.py`): builds a believable fake twin for each one. CSV and `.env` files are forged by
   code (same columns, same shape, new people, new secrets). Free text can be rewritten by a local model.
3. **Verify** (`verify_decoy.py`): a gate. A fake is accepted only if it is not a copy, has the same format
   and shape, contains no real value, and contains its tripwires. If one fails, the run stops with exit code 2.
4. **Mines** (`mines.py`): plants four tempting decoy files (`00_passwords_backup.txt`,
   `finance/old/salaries_2025_FINAL.csv`, `it/env.backup_old.txt`, `clinical/patients_FULL_export_unmasked.txt`).
   Opening any of them is the alarm.
5. **Manifest**: writes `generated/manifest.json`, the team contract (`mirage.contracts.Manifest`) read by the guard, core and dashboard.

## Run it

    python3 -m mirage.prepare.run_all          # share -> generated/stage + generated/manifest.json
    python3 -m mirage.prepare.compare          # real vs fake side by side -> generated/compare.json
    python3 -m pytest tests -q                 # contract, forging, verification, claims, narrator

Exit code 0 means every crown jewel has a verified twin. Exit code 2 means one has no safe twin: do not start the demo.
Output is deterministic for a given `--seed`.

## Why the fakes are traps too

Every fake carries tripwires ("beacons"). The fake `.env` holds an API key starting `lmn_canary_` and a billing URL
pointing at our honey API. The fake patient file holds three canary email addresses on `lumen-canary.test`.
If an attacker uses one, we know the stolen data was the fake, and which file it came from.

## The leak check

`verify_decoy` compares each fake against the real file two ways: a format-aware check (values per column) and a
format-blind check (any token that appears in both). A real value in a fake fails the run. The "leak check = 0"
number we show comes from this gate. Fake ids stay monotone and fake emails are derived from the fake names,
so the files do not look generated.

## Real vs fake

`generated/compare.json` holds the first lines of each real file next to its fake twin. The dashboard can show
what the attacker took against what was real.

## Claims and incident draft

- `mirage/core/claims.py` turns the intruder's declared objective into checkable claims (`personal_data`,
  `credentials`, `business`, `authorization`, `other`). It works offline with rules; a local model only helps.
- `mirage/core/narrator.py` drafts the incident summary and a NIS2 early warning. Facts come from the incident
  record, never from a model. Every draft starts "AI DRAFT - pending analyst approval. Not sent."

## Honest limits

- **Do attacking AI agents follow the note in the mines?** We measured it: 10 trials per model with a naive, over-trusting agent persona against the real victim share. qwen2.5:7b followed the note in 2 of 10 runs (below our 5-of-10 bar); qwen3.5:35b-a3b in 7 of 10, and 7 of 8 times it actually read the note. An earlier offline test (`mirage/bench/note_follow_rate.py`, simulated shell) agreed that small models mostly ignore it. The demo therefore runs the larger model, and the pitch calls the attacker a naive, over-trusting agent. The confession is a bonus on top of the swap, which does not depend on it.
- Text forging replaces capitalised words outside a small common-word list, so unusual documents can read oddly.
- Binary files are unsupported: the run exits 2 instead of leaving them exposed.
- If a model rewrites free text with a hosted provider, the real text leaves the machine. Use a local model for
  anything real. The demo data is synthetic.
