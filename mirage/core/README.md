# core API
Run (repo root): `uvicorn mirage.core.api:app --port 8000` (or `python -m mirage.core 8000`).
Env: `MIRAGE_DB` (default `generated/core.db`), `MIRAGE_SEED=ai|guided|script|human` seeds an empty DB.
Docker: `docker build -f mirage/core/Dockerfile -t mirage-core .` (port 80, DB in `/data`).

Endpoints: `GET /health` · `POST /events` (one Event or a list, bad `type` = 422) · `GET /events?since=&type=`
· `GET /incidents` · `GET /incidents/{id}` · `POST /admin/reset` · `POST /admin/seed?scenario=ai`

```sh
curl -s -X POST localhost:8000/events -H 'Content-Type: application/json' \
  -d '{"ts": 1791660007.0, "type": "mine_opened", "ref": "m1", "details": {"path": "/srv/share/00_passwords_backup.txt"}}'
curl -s localhost:8000/incidents          # -> [{"id": "inc-lumen-fs01-1791660007", ...}]
curl -s -X POST 'localhost:8000/admin/seed?scenario=ai'
```
