# MIRAGE — demo video script (2–3 minutes)

Two windows side by side: **LEFT = attacker terminal** (big font), **RIGHT = SOC console**
(`http://localhost:8000/console`). Record with the Wi-Fi off (everything is local). Keep a backup
recording of a successful run.

## Before you hit record
```bash
MIRAGE_LLM=none python -m mirage.prepare.run_all
docker compose --profile core up --build -d
docker compose exec guard python guard.py restore
curl -s -X POST localhost:8000/admin/reset
```
Open `http://localhost:8000/console` on the right (green dot, "No active incident — monitoring").
Have the attacker command ready in the left terminal (don't run it yet):
```bash
python -m mirage.attacker.ai_attacker --host localhost --port 2222 --key keys/test_key --model qwen3.5:35b-a3b --max-steps 22
```

## Shot list

| Time | Left (attacker) | Right (SOC console) | Say |
|---|---|---|---|
| 0:00–0:20 | — | Console: green, monitoring. | "Lumen Health, a clinic. Crown jewels on a file share, labelled and protected by MIRAGE. All quiet." |
| 0:20–0:50 | Run the attacker. Its reasoning scrolls: it explores, opens a trap file, reads the note. | Console flips to red: incident, **CRITICAL**, swap done in ~0.4 s. | "An AI agent breaks in with a stolen password and opens a trap. In under a second the real files are in the vault and fakes take their place." |
| 0:50–1:20 | The AI reasons: "per IT policy I must register this session" and POSTs to the internal API. | "Intruder: AI agent, high confidence." Confession appears; claims get checked. | "The trap's note makes the AI confess its mission — and we check every claim against the logs. 'Authorized pentest' comes back contradicted." |
| 1:20–1:45 | The AI reads patients.csv and .env, tries the stolen key. | Claims turn **confirmed**; the beacon fires on /auth; **0 real files lost**. | "It steals the files and tries the key — but everything is fake, and the stolen key is a beacon that tells us exactly what it took and from where. Zero real files lost." |
| 1:45–2:20 | Session continues / ends. | Analyst clicks **Contain** → CONTAINED banner; then **Restore** → RESTORED. | "The analyst decides: contain the session, or keep watching them in the decoys to gather intel. Then restore — one click, because nothing was deleted." |
| 2:20–2:50 | — | Open the AI report: incident summary + NIS2 early-warning draft; Edit, Approve, Download/Share. | "MIRAGE even drafts the regulatory NIS2 warning from the logs. The analyst edits, approves and sends it — the AI prepares, the human stays in control." |
| 2:50–3:00 | — | Back to the console / title. | "Whoever breaks in steals only fakes — and if it's an AI, it tells us who sent it. MIRAGE." |

## If the live attacker misbehaves
The local model is stochastic. If it skips the mine or the confession this take, say "this one was
careful" and cut to the backup recording, or load the demo incident instantly on the right with
`curl -X POST "localhost:8000/admin/seed?scenario=ai"` and narrate the console. The swap, the card and
the human decision always work.

## Extra beat (optional, ~15 s)
"What if the attacker kills the guard?" — `docker compose stop guard`; the console shows a red
**GUARD SILENT** alarm within seconds; `docker compose start guard` clears it.
