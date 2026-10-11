# MIRAGE — Defense sheet

**Secure Horizons 2026 · Track 2 (AI for Security & Secure AI) · Team 7**

*Whoever breaks in steals only fakes. And if it's an AI, it tells us who sent it.*

**Who it is for:** clinics and the medical sector: private clinics and clinic groups, medical laboratories and imaging centres, starting in France. They keep patient files on shared drives, run small IT teams, often use an outsourced SOC, and are now in NIS2 scope. MIRAGE is sold to them directly and through the MSSPs that run their SOC.

## Threat scenario

An attacker (human, script, or autonomous AI agent) reaches a mid-size clinic's file server with a stolen `svc_backup` credential and sets out to exfiltrate patient records and billing credentials. Health is the EU's most attacked critical sector (309 significant incidents in 2023, European Commission), healthcare breaches cost the most (USD 7.42 M, IBM 2025), data theft before encryption is now the main extortion lever (> 76% of ransomware attacks, Coveware Q3 2025), and AI agents act in seconds, faster than any analyst. MIRAGE assumes the break-in happens: the first trap file touched triggers an automatic, reversible swap of the crown jewels for AI-forged fakes, and an AI intruder is induced to reveal its mission, which is then checked against the logs.

Demo company: Lumen Health, a fictional clinic chain. All data is synthetic.

## NIST CSF 2.0 mapping

| Function | How MIRAGE delivers it |
|---|---|
| **Identify** | `prepare/` labels files, picks crown jewels, forges leak-checked fake twins, places mines and beacons. |
| **Protect** | Real files move to a root-only vault on first mine touch; the command log is root-only and hash-chained. |
| **Detect** | Mine open (command or inotify read), honey `/tickets` (AI confession) and `/auth` (beacon use); intruder label from command rhythm and note-following. |
| **Respond** | Sub-second swap (automatic); analyst Contain / Keep watching / Dismiss / Restore; AI-drafted incident summary and NIS2 report. |
| **Recover** | Restore returns the real files and re-arms the traps; nothing was deleted, so recovery is one click. |
| **Govern** | Human in the loop on every action that affects people; AI drafts are marked "pending approval, not sent". |

## ATT&CK / ATLAS / OWASP mapping

- **MITRE ATT&CK** (tagged live on the incident timeline): T1059 Command and Scripting Interpreter · T1083 File and Directory Discovery · T1005 Data from Local System · T1552.001 Credentials in Files (the mine) · T1078 Valid Accounts (stolen beacon key used).
- **MITRE D3FEND**: Decoy File · Decoy User Credential, plus pre-emptive swap of the targeted data.
- **MITRE ATLAS** (the attacker is an AI agent): AML.T0051 LLM Prompt Injection, turned *against the attacker* on our own server (the mine note makes the agent confess). The declared objective is treated as untrusted data and checked, never followed.
- **OWASP**: aligns with the LLM Top 10 view of prompt injection and excessive agency, here used defensively and sandboxed; complements data-exfiltration controls (DLP) by making the stolen data worthless.

## Metrics

| What | Result | How it was obtained |
|---|---|---|
| Detection and intruder label | Correct on **4/4** scenarios (AI agent, AI guided by a human, script, human) | Logic test on hand-written event sequences (`mirage/fakes.py`), not live attacks |
| AI confession (note followed) | **7/10** qwen3.5:35b-a3b · **2/10** qwen2.5:7b | Live runs, local Ollama models, no API key |
| Confession checking | Each claim tagged confirmed / unverified / **contradicted** against the logs (e.g. "authorized pentest" → contradicted) | Live runs |
| Time to swap, real files lost | Shown on the incident card for each live run (target < 1 s, 0 real files lost) | Live demo |
| Detection and false-positive rates at scale | **Not yet measured** | Planned for 2–3 clinic pilots |

The swap times in `mirage/fakes.py` are hard-coded test values, so we do not report them as measurements.

## How humans stay in control

Automatic only where it is safe and reversible: the swap, in under a second. Every action that touches people or the business waits for the analyst:

- **Contain**: lock the account and kill the session (token-protected).
- **Keep watching**: leave the intruder in the decoys to gather intelligence; safe, because it only holds fakes.
- **Dismiss**: mark a false alarm.
- **Restore**: return the real files and re-arm the traps.

The intruder label never triggers an action, so a wrong label costs nothing. The incident summary and NIS2 early warning are AI *drafts*, marked "pending analyst approval, not sent", that the analyst edits and approves.

## Known limitations

- The swap protects files not yet read. A crown jewel opened before a mine is "exposed" and scored Critical, honestly.
- The confession is a bonus layer and depends on the attacker's model; we report the rate per model.
- If the guard is killed, commands are not logged meanwhile, but the console raises a "guard silent" heartbeat alarm.
- A root attacker on the same machine could reach the vault; in production the vault is a separate machine or account.
- Not yet tested in a real clinic; the demo runs on one laptop with synthetic data and local models. Production maps to cloud-storage APIs, a separate vault account and the customer's SIEM.

## Rules we keep

Attacks only against our own containers · no hack back · synthetic data only (GDPR) · no secrets in the repo (gitleaks).