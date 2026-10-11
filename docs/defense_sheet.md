# MIRAGE — Defense sheet (one page)

**Secure Horizons 2026 · Track 2 (AI for Security & Secure AI) · Team 7**

## Threat scenario

An attacker (human, script, or autonomous AI agent) reaches a mid-size clinic's file server with a
stolen `svc_backup` credential and sets out to exfiltrate patient records and billing credentials.
Data-theft-before-encryption is now the main extortion lever (>76% of ransomware, Coveware Q3 2025),
and AI agents act in seconds — faster than any analyst. MIRAGE assumes the break-in happens: the first
trap file touched triggers an automatic, reversible swap of the crown jewels for AI-forged fakes, and
an AI intruder is induced to reveal its mission, which is then checked against the logs.

## NIST CSF 2.0 mapping

| Function | How MIRAGE delivers it |
|---|---|
| **Identify** | `prepare/` labels files, picks crown jewels, forges leak-checked fake twins, places mines + beacons. |
| **Protect** | Real files move to a root-only vault on first mine touch; the command log is root-only and hash-chained. |
| **Detect** | Mine open (command or inotify read), honey `/tickets` (AI confession) and `/auth` (beacon use); intruder label from rhythm + note-following. |
| **Respond** | Sub-second swap (automatic); analyst Contain / Keep-watching / Dismiss / Restore; AI-drafted incident + NIS2 report. |
| **Recover** | Restore returns the real files and re-arms the traps; nothing was deleted, so recovery is one click. |
| **Govern** | Human-in-the-loop on every irreversible action; AI drafts are marked "pending approval, not sent". |

## ATT&CK / ATLAS / OWASP mapping

- **MITRE ATT&CK** (tagged live on the incident timeline): T1059 Command & Scripting Interpreter ·
  T1083 File & Directory Discovery · T1005 Data from Local System · T1552.001 Credentials in Files
  (the mine) · T1078 Valid Accounts (stolen beacon key used). Defense: deception (honeyfiles/honeytokens),
  pre-swap of the targeted data.
- **MITRE ATLAS** (the attacker is an AI agent): AML.T0051 LLM Prompt Injection — we turn it *against the
  attacker* on our own server (the mine note makes the agent confess); the declared objective is treated
  as untrusted data and checked, never followed.
- **OWASP**: aligns with the LLM Top-10 view of prompt injection / excessive agency — here used
  defensively and sandboxed; and with data-exfiltration controls (DLP) that MIRAGE complements by making
  the stolen data worthless.

## Metrics (from our test bench and live runs)

| Metric | Result |
|---|---|
| Detection rate | **100%** (4/4 intruder scenarios raised an incident) |
| False-positive rate | **0%** (normal user + backup job not flagged) |
| Time to respond (swap) | **~0.4 s** (0.38–0.41 s) |
| Real files lost | **0** across the attack scenarios |
| Intruder label | AI agent / AI-guided / human-or-script — correct on all four fake sequences |
| AI confession (note-follow) | **7/10** qwen3.5:35b-a3b · 2/10 qwen2.5:7b (local Ollama, no API key) |
| Confession checking | each claim confirmed / unverified / **contradicted** vs the logs (e.g. "authorized pentest" → contradicted) |

Reproduce: `python -m mirage.bench.run_bench` → `generated/bench_results.csv`.

## How humans stay in control

Automatic only where it is safe and reversible (the swap, <1 s). Every action that touches people or
business waits for the analyst: **Contain** (lock the account, kill the session — token-protected),
**Keep watching** (leave the intruder in the decoys to gather intelligence — safe, they only hold fakes),
**Dismiss** (false alarm), **Restore** (return the real files). The intruder label never triggers an
action, so a wrong label costs nothing. The incident summary and NIS2 early-warning are AI *drafts*,
marked "pending analyst approval — not sent", that the analyst edits and approves.

## Known limitations

- The swap protects files not yet read; a jewel opened before a mine is "exposed" and scored Critical (honest).
- The confession is a bonus layer and depends on the attacker's model (rate reported per model).
- If the guard is killed, commands aren't logged meanwhile — but the console raises a "guard silent" heartbeat alarm.
- Demo runs on one laptop with synthetic data and local models; production maps to cloud-storage APIs, a
  separate vault account, and the customer's SIEM.
