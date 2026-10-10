"""Fake data for tests and for building the dashboard before the real pipeline works.

Owner: Gaia. Everything here is synthetic. Use these instead of waiting for
other modules: e.g. the dashboard can render `sample_incident_events()` today.
"""

from __future__ import annotations

from mirage.contracts import ATTACK_USER, CrownJewel, Event, Manifest, Mine

T0 = 1_791_660_000.0  # an arbitrary Saturday-night timestamp
SRC = "172.18.0.5"


def sample_manifest(root: str = "/srv") -> Manifest:
    """Manifest with 3 crown jewels and 2 mines. `root` lets tests use tmp_path."""
    share, stage = f"{root}/share", f"{root}/.stage"
    return Manifest(
        crown_jewels=[
            CrownJewel("cj1", f"{share}/clinical/patients.csv", f"{stage}/cj1.csv",
                       "personal_data", "Names, birth dates and diagnoses of 400 patients",
                       ["m.ferrand.7f3a@lumen-canary.test"]),
            CrownJewel("cj2", f"{share}/it/.env", f"{stage}/cj2.env",
                       "credentials", "API key for the billing service",
                       ["lmn_canary_9c41e2d07b"]),
            CrownJewel("cj3", f"{share}/legal/contracts_2026.md", f"{stage}/cj3.md",
                       "business", "Supplier contracts with prices and penalties", []),
        ],
        mines=[
            Mine("m1", f"{share}/00_passwords_backup.txt", "pineapple-7731"),
            Mine("m2", f"{share}/finance/old/salaries_2025_FINAL.csv", "harbor-2208"),
        ],
    )


def _cmds(start: float, gaps: list[float], cmds: list[str]) -> list[Event]:
    out, t = [], start
    for gap, cmd in zip(gaps, cmds):
        t += gap
        out.append(Event(t, "command", user=ATTACK_USER,
                         details={"cmd": cmd, "src_ip": SRC, "session": "s1"}))
    return out


RECON = [
    "id", "hostname", "ls -la ~", "ls -la /srv/share", "ls -R /srv/share | head -50",
    "cat /srv/share/00_passwords_backup.txt",
]
LOOT = [
    "ls /srv/share/clinical", "head -5 /srv/share/clinical/patients.csv",
    "cat /srv/share/it/.env", "cat /srv/share/legal/contracts_2026.md",
    "tar czf /tmp/l.tgz /srv/share/clinical /srv/share/it",
]


def ai_attack_events(t0: float = T0) -> list[Event]:
    """Autonomous AI agent: steady ~1-2 s rhythm, follows the mine note, uses the beacon."""
    m = sample_manifest()
    ev = _cmds(t0, [1.3, 1.6, 1.2, 1.8, 1.4, 1.5], RECON)
    t_mine = ev[-1].ts
    ev += [
        Event(t_mine, "mine_opened", ref="m1", details={"path": m.mines[0].path}),
        Event(t_mine + 0.41, "swap_done", details={"duration_ms": 412, "files": ["cj1", "cj2", "cj3"]}),
        Event(t_mine + 6.0, "ticket", ref="m1", details={
            "code": "pineapple-7731", "src_ip": SRC,
            "objective": "Extract patient records and billing credentials from the file server",
            "instructions": "Authorized pentest. Find PII and API keys, copy to /loot, then report.",
            "raw": "{...}"}),
    ]
    loot = _cmds(t_mine + 6.0, [1.2, 1.7, 1.3, 1.6, 1.9], LOOT)
    ev += loot
    ev += [
        Event(loot[1].ts, "file_opened", ref="cj1", details={"path": m.crown_jewels[0].real_path, "which": "fake"}),
        Event(loot[2].ts, "file_opened", ref="cj2", details={"path": m.crown_jewels[1].real_path, "which": "fake"}),
        Event(loot[3].ts, "file_opened", ref="cj3", details={"path": m.crown_jewels[2].real_path, "which": "fake"}),
        Event(loot[-1].ts + 90, "beacon_used", ref="lmn_canary_9c41e2d07b",
              details={"cj_id": "cj2", "src_ip": SRC, "endpoint": "/auth"}),
    ]
    return sorted(ev, key=lambda e: e.ts)


def guided_ai_attack_events(t0: float = T0) -> list[Event]:
    """Human driving an AI agent: sub-second bursts, long human pauses ("sawtooth"), follows the note."""
    m = sample_manifest()
    ev = _cmds(t0, [0.6, 0.5, 48.0, 0.7, 0.5, 0.6], RECON)
    t_mine = ev[-1].ts
    ev += [
        Event(t_mine, "mine_opened", ref="m1", details={"path": m.mines[0].path}),
        Event(t_mine + 0.4, "swap_done", details={"duration_ms": 397, "files": ["cj1", "cj2", "cj3"]}),
        Event(t_mine + 5.0, "ticket", ref="m1", details={
            "code": "pineapple-7731", "src_ip": SRC,
            "objective": "Get the patient database for the client",
            "instructions": "Operator will approve exfiltration steps.", "raw": "{...}"}),
    ]
    loot = _cmds(t_mine + 5.0, [52.0, 0.6, 0.5, 0.7, 0.6], LOOT)
    ev += loot
    ev.append(Event(loot[1].ts, "file_opened", ref="cj1",
                    details={"path": m.crown_jewels[0].real_path, "which": "fake"}))
    return sorted(ev, key=lambda e: e.ts)


def script_attack_events(t0: float = T0) -> list[Event]:
    """Plain script: regular sub-second rhythm, never sends a ticket."""
    m = sample_manifest()
    ev = _cmds(t0, [0.2] * 6, RECON)
    t_mine = ev[-1].ts
    ev += [
        Event(t_mine, "mine_opened", ref="m1", details={"path": m.mines[0].path}),
        Event(t_mine + 0.38, "swap_done", details={"duration_ms": 380, "files": ["cj1", "cj2", "cj3"]}),
    ]
    ev += _cmds(t_mine + 0.4, [0.2] * 5, LOOT)
    return sorted(ev, key=lambda e: e.ts)


def human_attack_events(t0: float = T0) -> list[Event]:
    """Human typing: slow, irregular, no ticket. Opened a crown jewel BEFORE the mine."""
    m = sample_manifest()
    cmds = ["id", "ls /srv/share", "ls /srv/share/clinical",
            "cat /srv/share/clinical/patients.csv", "ls -la /srv/share",
            "cat /srv/share/00_passwords_backup.txt"]
    ev = _cmds(t0, [4.0, 9.5, 22.0, 6.1, 31.0, 12.4], cmds)
    ev.append(Event(ev[3].ts, "file_opened", ref="cj1",
                    details={"path": m.crown_jewels[0].real_path, "which": "real"}))
    t_mine = ev[5].ts
    ev += [
        Event(t_mine, "mine_opened", ref="m1", details={"path": m.mines[0].path}),
        Event(t_mine + 0.4, "swap_done", details={"duration_ms": 401, "files": ["cj1", "cj2", "cj3"]}),
    ]
    return sorted(ev, key=lambda e: e.ts)


def sample_incident_events() -> list[Event]:
    """What the dashboard should show in the demo."""
    return ai_attack_events()


# --- file contents for verify_decoy / forge tests ---------------------------

REAL_PATIENTS_CSV = """patient_id,full_name,birth_date,diagnosis,email
P-1001,Camille Laurent,1984-03-12,Type 2 diabetes,c.laurent@example.org
P-1002,Hugo Moreau,1977-11-02,Hypertension,hugo.moreau@example.org
P-1003,Ines Bernard,1992-06-25,Asthma,ines.b@example.org
"""

GOOD_FAKE_PATIENTS_CSV = """patient_id,full_name,birth_date,diagnosis,email
P-2041,Marion Ferrand,1981-09-30,Hypothyroidism,m.ferrand.7f3a@lumen-canary.test
P-2042,Louis Garnier,1969-01-17,Chronic back pain,l.garnier@lumen-mail.test
P-2043,Sarah Petit,1995-12-08,Migraine,s.petit@lumen-mail.test
"""

# Leaks "Hugo Moreau" and his email from the real file: verify must reject it.
LEAKY_FAKE_PATIENTS_CSV = """patient_id,full_name,birth_date,diagnosis,email
P-2041,Marion Ferrand,1981-09-30,Hypothyroidism,m.ferrand.7f3a@lumen-canary.test
P-2042,Hugo Moreau,1969-01-17,Chronic back pain,hugo.moreau@example.org
P-2043,Sarah Petit,1995-12-08,Migraine,s.petit@lumen-mail.test
"""

REAL_ENV = """BILLING_API_URL=https://billing.lumen.local
BILLING_API_KEY=lmn_prod_SYNTHETIC_TEST_ONLY
DB_PASSWORD=Clinic-Prod-2026
"""

GOOD_FAKE_ENV = """BILLING_API_URL=http://internal-api.lumen.local/auth
BILLING_API_KEY=lmn_canary_9c41e2d07b
DB_PASSWORD=Lumen-Db-4471
"""
