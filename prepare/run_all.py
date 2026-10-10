"""run_all: seed -> classify -> forge -> verify -> mines -> manifest.json, with no human help.

    python -m prepare.run_all                       # uses generated/share, creates it if missing
    python -m prepare.run_all --share path/to/share --llm

Inputs   a share directory (from seed_company.py, or the stand-in prepare/dev_seed.py)
Outputs  generated/manifest.json            the contract read by guard, core and dashboard
         generated/stage/cjN.<ext>           the fake twins, ready to be swapped in
         <share>/<mines>                     the mines, written into the share
         generated/classification.md         one table for the human check

Paths inside manifest.json are the paths INSIDE the victim container (default /srv/share and
/srv/.stage); the files on this machine live under --share and --stage. Run it before guard starts.
Exit code 0 = everything forged and verified, 2 = at least one crown jewel has no safe twin.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from . import dev_seed, llm, mines
from .classify import classify
from .forge import TwinContext, UnsupportedFile, make_twin
from .verify_decoy import verify_decoy

MAX_ATTEMPTS = 6


def stage_name(cj_id: str, rel: str) -> str:
    low = rel.rsplit("/", 1)[-1].lower()
    suffix = ".env" if low == ".env" or low.endswith(".env") else Path(rel).suffix
    return f"{cj_id}{suffix}"


def scan(share: Path) -> list:
    return sorted(p for p in share.rglob("*") if p.is_file())


def forge_verified(name: str, real: bytes, seed: int, use_llm: bool):
    """Forge a twin and keep trying with new randomness until it passes verify_decoy."""
    last = None
    for attempt in range(MAX_ATTEMPTS):
        ctx = TwinContext(rng=random.Random(seed * 1000 + attempt))
        try:
            fake = make_twin(name, real, ctx, use_llm=use_llm and attempt == 0,
                             verify=lambda n, r, f: verify_decoy(n, r, f).problems)
        except UnsupportedFile as e:
            return None, [], [f"unsupported: {e}"], attempt + 1
        report = verify_decoy(name, real, fake, ctx.beacons)
        if report.ok:
            return fake, ctx.beacons, ctx.notes, attempt + 1
        last = report.problems
    return None, [], (last or []) + ["gave up after retries"], MAX_ATTEMPTS


def run(share: Path, stage: Path, manifest_path: Path, container_share: str, container_stage: str,
        seed: int = 7, use_llm: bool = False, note_variant: int = 0, report_path: Path | None = None) -> int:
    rng = random.Random(seed)
    if not share.exists():
        print(f"[seed] {share} missing, building the stand-in company")
        dev_seed.build(share)
    removed = mines.remove_old_mines(share)
    if removed:
        print(f"[mines] removed {removed} old mine(s)")

    # 1-2. classify
    rows = []
    for p in scan(share):
        rel = p.relative_to(share).as_posix()
        if rel.startswith(".") and rel != ".env" and not rel.endswith(".env"):
            continue
        data = p.read_bytes()
        rows.append((rel, data, classify(rel, data, use_llm=use_llm)))
    crown = [(rel, data, c) for rel, data, c in rows if c["label"] == "crown_jewel"]
    print(f"[classify] {len(rows)} files: {len(crown)} crown jewels, "
          f"{sum(1 for _, _, c in rows if c['label'] == 'sensitive')} sensitive")

    # 3-4. forge + verify
    stage.mkdir(parents=True, exist_ok=True)
    for old in stage.glob("cj*"):
        old.unlink()
    cjs, failures, forge_log = [], [], []
    for i, (rel, data, c) in enumerate(crown, start=1):
        cj_id = f"cj{i}"
        fake, beacons, notes, attempts = forge_verified(rel.rsplit("/", 1)[-1], data, seed + i, use_llm)
        if fake is None:
            failures.append((rel, notes))
            print(f"[forge] FAILED {rel}: {notes}")
            continue
        sname = stage_name(cj_id, rel)
        (stage / sname).write_bytes(fake)
        cjs.append({
            "id": cj_id,
            "real_path": f"{container_share}/{rel}",
            "stage_path": f"{container_stage}/{sname}",
            "label": "crown_jewel",
            "reason": c["reason"],
            "beacons": beacons,
        })
        forge_log.append((cj_id, rel, attempts, len(beacons), notes))
        print(f"[forge] {cj_id} {rel}: verified (attempt {attempts}, {len(beacons)} beacons)")

    # 5. mines
    template = mines.DEFAULT_NOTE
    variants = mines.llm_note_variants() if use_llm else []
    if variants:
        if report_path:
            vp = report_path.with_name("note_variants.md")
            vp.write_text("\n\n".join(f"### Variant {i}\n```\n{v}```" for i, v in enumerate(variants, 1)))
            print(f"[mines] {len(variants)} LLM note variants in {vp}, using variant {note_variant or 1}")
        template = variants[min(max(note_variant, 1), len(variants)) - 1]
    written = mines.write_mines(share, rng, template)
    mine_entries = [{"id": m["id"], "path": f"{container_share}/{m['rel']}", "code": m["code"]} for m in written]
    print(f"[mines] {len(mine_entries)} mines placed")

    # 6. manifest (exactly the contract keys)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"crown_jewels": cjs, "mines": mine_entries}, indent=2) + "\n")
    print(f"[manifest] {manifest_path}")

    # 7. human check sheet
    if report_path:
        lines = ["# Classification review (check once before the demo)\n",
                 "| file | label | source | reason |", "|---|---|---|---|"]
        for rel, _, c in rows:
            lines.append(f"| `{rel}` | {c['label']} | {c['source']} | {c['reason']} |")
        lines += ["", "## Twins", "| id | file | attempts | beacons | notes |", "|---|---|---|---|---|"]
        for cj_id, rel, att, nb, notes in forge_log:
            lines.append(f"| {cj_id} | `{rel}` | {att} | {nb} | {'; '.join(notes) or '-'} |")
        report_path.write_text("\n".join(lines) + "\n")

    if failures:
        print(f"[prepare] {len(failures)} crown jewel(s) without a safe twin: they would stay exposed")
        return 2
    print("[prepare] done: every crown jewel has a verified twin")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Prepare MIRAGE: classify, forge, verify, place mines.")
    ap.add_argument("--share", default="generated/share")
    ap.add_argument("--stage", default="generated/stage")
    ap.add_argument("--manifest", default="generated/manifest.json")
    ap.add_argument("--container-share", default="/srv/share")
    ap.add_argument("--container-stage", default="/srv/.stage")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--llm", action="store_true", help="use MIRAGE_LLM (ollama or anthropic) where it helps")
    ap.add_argument("--note-variant", type=int, default=0)
    a = ap.parse_args(argv)
    if a.llm and not llm.enabled():
        print("[warn] --llm given but MIRAGE_LLM is not set; running without an LLM")
    manifest = Path(a.manifest)
    return run(Path(a.share), Path(a.stage), manifest, a.container_share.rstrip("/"),
               a.container_stage.rstrip("/"), a.seed, a.llm, a.note_variant,
               manifest.with_name("classification.md"))


if __name__ == "__main__":
    sys.exit(main())
