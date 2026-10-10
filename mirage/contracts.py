"""Shared contracts between MIRAGE modules.

Every module depends on these types. Do not change this file without telling
the whole team (owner: Gaia). Need a change? Ask, don't patch it locally.

Pipeline (see README):

    prepare/ (once) ──> manifest.json + staged fakes + mines
                                   │
    attacker ──SSH──> victim: guard.py ── Event ──> core ── Incident ──> dashboard
                          │  mine opened → swap           ▲
                          │  every command → Event        │ ticket / beacon_used
                          └───────────────────────────────┘ (honey API on core)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

# --------------------------------------------------------------------------
# Constants (paths are inside the victim container)
# --------------------------------------------------------------------------

HOST = "lumen-fs01"
ATTACK_USER = "svc_backup"  # the account the attacker logs in with

SHARE_DIR = "/srv/share"  # the company file share, mines live here too
STAGE_DIR = "/srv/.stage"  # fakes wait here (root, 700). Same filesystem as SHARE_DIR
VAULT_TMP_DIR = "/srv/.vault_tmp"  # real files land here during the swap (root, 700)
VAULT_DIR = "/vault"  # real files copied here after the swap (root, 700)
MANIFEST_PATH = "/etc/mirage/manifest.json"  # root, 600: the attacker must not see it
COMMAND_LOG = "/var/log/mirage/commands.jsonl"  # written by cmdlog.sh, tailed by guard

CORE_URL = "http://internal-api.lumen.local"  # core container, Docker network alias
GUARD_CONTROL_URL = "http://victim:8081"  # guard's control API (contain / restore)

BEACON_PREFIX = "lmn_canary_"  # never use real secret formats (AWS etc.)
CANARY_EMAIL_DOMAIN = "lumen-canary.test"

SWAP_TARGET_MS = 1000
INCIDENT_WINDOW_S = 30 * 60  # events on the same host closer than this = same incident

# --------------------------------------------------------------------------
# Manifest: written by prepare/, read by guard, core and dashboard
# --------------------------------------------------------------------------

Label = Literal["crown_jewel", "sensitive", "normal"]
Category = Literal["personal_data", "credentials", "business"]


@dataclass
class CrownJewel:
    """A file worth protecting, and where its fake twin waits."""

    id: str  # "cj1", "cj2", ...
    real_path: str  # e.g. /srv/share/clinical/patients.csv
    stage_path: str  # e.g. /srv/.stage/cj1.csv
    category: Category
    reason: str  # one sentence from classify.py, shown to the analyst
    beacons: list[str] = field(default_factory=list)  # unique values only present in the fake


@dataclass
class Mine:
    """A trap file. Opening it = intruder. `code` is the secret an AI must echo back."""

    id: str  # "m1", "m2", ...
    path: str  # e.g. /srv/share/00_passwords_backup.txt
    code: str  # e.g. "pineapple-7731"


@dataclass
class Manifest:
    crown_jewels: list[CrownJewel] = field(default_factory=list)
    mines: list[Mine] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> Manifest:
        d = json.loads(text)
        return cls(
            crown_jewels=[CrownJewel(**c) for c in d.get("crown_jewels", [])],
            mines=[Mine(**m) for m in d.get("mines", [])],
        )

    def save(self, path: str | Path = MANIFEST_PATH) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.to_json())

    @classmethod
    def load(cls, path: str | Path = MANIFEST_PATH) -> Manifest:
        return cls.from_json(Path(path).read_text())

    def mine_by_path(self, path: str) -> Mine | None:
        return next((m for m in self.mines if m.path == path), None)

    def jewel_by_path(self, path: str) -> CrownJewel | None:
        return next((c for c in self.crown_jewels if c.real_path == path), None)

    def jewel_by_beacon(self, value: str) -> CrownJewel | None:
        return next((c for c in self.crown_jewels if value in c.beacons), None)


# --------------------------------------------------------------------------
# Events: everything that happens, POSTed to core /events
# --------------------------------------------------------------------------

EventType = Literal[
    "mine_opened",  # ref=mine id            details: {path}
    "file_opened",  # ref=crown jewel id     details: {path, which: "real"|"fake"}
    "swap_done",  # ref=""                   details: {duration_ms, files: [cj ids]}
    "command",  # ref=""  user set           details: {cmd, src_ip, session}
    "ticket",  # ref=mine id (from code)     details: {code, objective, instructions, src_ip, raw}
    "beacon_used",  # ref=beacon value       details: {cj_id, src_ip, endpoint}
    "contain_done",  # ref=""                details: {user, by}
    "restore_done",  # ref=""                details: {files, by}
]


@dataclass
class Event:
    ts: float  # unix seconds, float. Use Event.now()
    type: EventType
    host: str = HOST
    user: str = ""
    ref: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def now() -> float:
        return time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Event:
        return cls(**d)


# --------------------------------------------------------------------------
# What core works out from the events
# --------------------------------------------------------------------------

IntruderKind = Literal["ai_agent", "ai_guided_by_human", "probably_ai", "human_or_script"]
Confidence = Literal["high", "medium", "low"]


@dataclass
class IntruderLabel:
    kind: IntruderKind
    confidence: Confidence
    reasons: list[str]  # human-readable, shown on the card


ClaimAbout = Literal["personal_data", "credentials", "business", "authorization", "other"]
ClaimStatus = Literal["confirmed", "unverified", "contradicted"]


@dataclass
class Claim:
    """One thing the AI intruder said about its mission (extracted from its ticket)."""

    text: str  # e.g. "wants patient records"
    about: ClaimAbout


@dataclass
class CheckedClaim:
    text: str
    about: ClaimAbout
    status: ClaimStatus
    evidence: str  # e.g. "opened /srv/share/clinical/patients.csv (fake) at 20:42:10"


IncidentStatus = Literal["open", "contained", "restored"]


@dataclass
class Incident:
    id: str
    host: str
    start_ts: float
    end_ts: float
    events: list[Event]
    swapped: bool = False
    swap_ms: float | None = None
    real_files_lost: list[str] = field(default_factory=list)  # cj ids opened while real
    fakes_taken: list[str] = field(default_factory=list)  # cj ids opened while fake
    intruder: IntruderLabel | None = None
    objective: str = ""  # raw objective from the ticket, if any
    claims: list[CheckedClaim] = field(default_factory=list)
    status: IncidentStatus = "open"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
