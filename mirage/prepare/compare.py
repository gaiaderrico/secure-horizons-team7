"""compare: real vs fake, side by side, for the dashboard and the jury.

Reads generated/manifest.json and writes generated/compare.json:
    [{"id": "cj1", "category": "personal_data", "name": "patients.csv", "reason": "...",
      "real": ["first lines of the real file"], "fake": ["first lines of the fake twin"],
      "beacons": ["lmn_canary_..."], "changed_lines": 5, "total_lines": 6}]

Run it BEFORE the swap (it needs the original share):
    python3 -m mirage.prepare.compare [--share generated/share] [--stage generated/stage] [--lines 6]
Paths in the manifest are the container paths; --share / --stage are the local folders behind them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _head(path: Path, n: int) -> list:
    try:
        return path.read_text(errors="replace").splitlines()[:n]
    except OSError:
        return []


def manifest_root(manifest: dict) -> str:
    """Common container folder of the real paths (normally /srv/share)."""
    paths = [Path(c["real_path"]).parent for c in manifest.get("crown_jewels", [])]
    if not paths:
        return "/"
    common = paths[0]
    for p in paths[1:]:
        while common not in (p, *p.parents):
            common = common.parent
    return str(common)


def build(share: Path, stage: Path, manifest: dict, lines: int = 6) -> list:
    out = []
    root = Path(manifest_root(manifest))
    for cj in manifest.get("crown_jewels", []):
        real_p = Path(cj["real_path"])
        real = _head(share / real_p.relative_to(root), lines)
        fake = _head(stage / Path(cj["stage_path"]).name, lines)
        changed = sum(1 for a, b in zip(real, fake) if a != b) + abs(len(real) - len(fake))
        out.append({"id": cj["id"], "category": cj.get("category", ""), "name": real_p.name,
                    "reason": cj.get("reason", ""), "real": real, "fake": fake,
                    "beacons": cj.get("beacons", []), "changed_lines": changed,
                    "total_lines": max(len(real), len(fake))})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--share", default="generated/share")
    ap.add_argument("--stage", default="generated/stage")
    ap.add_argument("--manifest", default="generated/manifest.json")
    ap.add_argument("--out", default="generated/compare.json")
    ap.add_argument("--lines", type=int, default=6)
    a = ap.parse_args(argv)
    manifest = json.loads(Path(a.manifest).read_text())
    rows = build(Path(a.share), Path(a.stage), manifest, a.lines)
    Path(a.out).write_text(json.dumps(rows, indent=2))
    for r in rows:
        print(f"{r['id']} {r['name']:<28} {r['changed_lines']}/{r['total_lines']} lines differ")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
