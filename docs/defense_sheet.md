# MIRAGE — Defense Sheet

*Secure Horizons 2026 · Track 2 · Team 7*

**Whoever breaks in steals only fakes. And if it's an AI, it tells us who sent it.**

## Threat scenario

An attacker, possibly an autonomous AI agent, logs into **Lumen Health**'s file server (a fictional clinic chain, synthetic data only) with a stolen password (`svc_backup` over SSH). It explores the share looking for patient records and credentials to exfiltrate.

1. **Detect:** the intruder opens a mine (`00_passwords_backup.txt`), a file no employee ever needs.
2. **Protect:** in under a second, plain code moves the real crown jewels to a locked vault and puts AI-forged fake twins at the same paths.
3. **Identify:** an AI intruder that follows the note in the mine registers its objective at our internal API. Every claim is checked against the command logs.
4. **Track:** the attacker steals the fakes. If it uses the beacon API key from the fake `.env`, we know what was taken, when, and from which IP.
5. **Respond / Recover:** the analyst sees one incident card and clicks **Contain** (lock the account, end the session) and **Restore** (put the real files back).

## NIST CSF 2.0 functions

| Function | How MIRAGE covers it |
| --- | --- |
| Identify | AI labels each file (crown jewel / sensitive / normal) with a reason |
| Protect | Automatic, reversible swap of crown jewels for fake twins; vault unreadable by the intruder |
| Detect | Mine-open sensor (inotify), beacon use on `/auth`, AI-intruder label |
| Respond | Incident card, Contain button, AI-drafted NIS2 early warning for analyst approval |
| Recover | Restore button returns the real files; nothing is ever deleted |

## Threat and defence mapping

| Framework | Items |
| --- | --- |
| MITRE ATT&CK | T1078 Valid Accounts · T1021.004 Remote Services: SSH · T1083 File and Directory Discovery · T1039 Data from Network Shared Drive · T1005 Data from Local System · T1552.001 Credentials In Files · T1048 Exfiltration Over Alternative Protocol |
| MITRE D3FEND | Decoy File · Decoy User Credential |
| MITRE ATLAS / OWASP | LLM Prompt Injection (ATLAS AML.T0051, OWASP LLM01) and agent goal hijack (OWASP Agentic ASI01), **used defensively, on our own server only** |

## Metrics *(measured on our lab, to fill on Sunday)*

| Metric | How measured | Result |
| --- | --- | --- |
| Time to detect | Mine opened → event stored in core | [__] s |
| Time to swap | Event → all crown jewels replaced | [__] s |
| Real files protected | Over [__] runs: fakes stolen vs real stolen | [__] % fakes |
| False positives | [__] h of normal activity + backup job | [__] swaps |
| Leak check | Real values found in fakes | [__] |
| Confession rate | AI runs that followed the note, per model | [__] |
| Label accuracy | [__] AI + [__] script runs + 1 manual attacker | [__] / [__] |

## How the human stays in control

- **No AI in the critical second:** detection and swap are plain code; no LLM call in the guard.
- **Automatic only where reversible:** the swap moves files and never deletes them; one click restores them.
- **Anything that affects people needs a click:** locking the account, ending the session, restoring files, sending the NIS2 early warning.
- **AI output is never trusted blindly:** the intruder label shows its reasons and triggers nothing; confession claims are tagged confirmed / unverified / contradicted against the logs; summaries stay marked "AI draft" until approved.

## Known limitations

- Files copied **before** any mine is touched are lost; mines sit where attackers look first.
- A **root** attacker on the same machine could reach the vault; in production the vault is a separate machine.
- A careful AI that never opens a mine, or ignores the note, is only labelled from command rhythm.
- Backups and antivirus can open mines; the demo ignores the backup window, production needs process identification (auditd/fanotify).
- Tested on one synthetic file server, not on cloud storage (SharePoint, Google Drive, S3).

## Rules we keep

Attacks only against our own containers · no hack back · synthetic data only (GDPR) · no secrets in the repo (gitleaks).