"""believability: build the "real or fake?" quiz for the Believability metric (target: about 50%).

    python -m mirage.prepare.believability --share generated/share-original --stage generated/stage

Takes N matching rows (real row vs fake row of the first CSV crown jewel), shuffles each pair, and
writes generated/believability.md for the people from other teams plus believability_key.json for us.
Run it BEFORE the swap (the real file is still in the share) or point --real at a saved copy.
Score: ask 5+ people, count right guesses. 50% means they cannot tell, which is what we want.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


def build(real_csv: Path, fake_csv: Path, out_dir: Path, n: int = 5, seed: int = 1) -> None:
    rng = random.Random(seed)
    real = list(csv.reader(real_csv.open()))
    fake = list(csv.reader(fake_csv.open()))
    header = real[0]
    idx = rng.sample(range(1, min(len(real), len(fake))), n)
    lines = ["# Real or fake?", "", "For each pair, which row is the REAL one: A or B?", ""]
    key = {}
    for k, i in enumerate(idx, 1):
        pair = [("real", real[i]), ("fake", fake[i])]
        rng.shuffle(pair)
        key[k] = "A" if pair[0][0] == "real" else "B"
        lines += [f"## Pair {k}", "", "| | " + " | ".join(header) + " |", "|---|" + "---|" * len(header)]
        for label, (_, cells) in zip("AB", pair):
            lines.append(f"| {label} | " + " | ".join(cells) + " |")
        lines.append("")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "believability.md").write_text("\n".join(lines) + "\n")
    (out_dir / "believability_key.json").write_text(json.dumps(key, indent=2) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", default="generated/share/clinical/patients.csv")
    ap.add_argument("--fake", default="generated/stage/cj1.csv")
    ap.add_argument("--out", default="generated")
    ap.add_argument("-n", type=int, default=5)
    a = ap.parse_args(argv)
    build(Path(a.real), Path(a.fake), Path(a.out), a.n)
    print(f"quiz in {a.out}/believability.md, answers in {a.out}/believability_key.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
