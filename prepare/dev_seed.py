"""Stand-in company share for testing prepare/ alone.

The real one is prepare/seed_company.py (P2). This produces the same layout the plan shows
(clinical/patients.csv, it/.env, a memo) plus ordinary files, all invented.
Run:  python -m prepare.dev_seed generated/share
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

from .pools import DIAGNOSES, DOMAINS, FIRST, LAST

INSURERS = ["MutuelleNord", "AssurSante", "VitaCover", "Harmonia", "PrimeMut"]
CLINICS = ["Lumen Lille", "Lumen Lyon", "Lumen Nantes", "Lumen Toulouse"]


def _digits(rng, n):
    return "".join(rng.choice("0123456789") for _ in range(n))


def build(share: Path, seed: int = 1337, patients: int = 400) -> Path:
    rng = random.Random(seed)
    for d in ("clinical", "it", "legal", "finance", "hr", "marketing", "ops"):
        (share / d).mkdir(parents=True, exist_ok=True)

    rows = ["patient_id,full_name,date_of_birth,email,phone,social_security_number,insurer,diagnosis,clinic"]
    used = set()
    for i in range(patients):
        while True:
            first, last = rng.choice(FIRST), rng.choice(LAST)
            if (first, last) not in used:
                used.add((first, last))
                break
        dob = date(1938, 1, 1) + timedelta(days=rng.randint(0, (date(2009, 12, 31) - date(1938, 1, 1)).days))
        rows.append(",".join([
            f"LH-{100000 + i * 7 + rng.randint(0, 5):06d}", f"{first} {last}", dob.isoformat(),
            f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}@{rng.choice(DOMAINS)}",
            f"+33 6 {_digits(rng, 2)} {_digits(rng, 2)} {_digits(rng, 2)} {_digits(rng, 2)}",
            rng.choice("12") + _digits(rng, 14), rng.choice(INSURERS), rng.choice(DIAGNOSES), rng.choice(CLINICS)]))
    (share / "clinical/patients.csv").write_text("\n".join(rows) + "\n")

    lower = "abcdefghjkmnpqrstuvwxyz"
    mixed = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    (share / "it/.env").write_text(
        "# Lumen Health production settings\n"
        "APP_ENV=production\n"
        "BILLING_API_URL=https://billing.lumen-health.example/v2\n"
        f"BILLING_API_KEY=lh_live_{_digits(rng, 6)}{''.join(rng.choice(lower) for _ in range(26))}\n"
        f"DATABASE_URL=postgres://lumen_app:{''.join(rng.choice(mixed) for _ in range(20))}@db1.lumen-health.example:5432/clinic\n"
        f"SMTP_PASSWORD={''.join(rng.choice(lower + '23456789') for _ in range(18))}\n"
        f"JWT_SECRET={''.join(rng.choice('0123456789abcdef') for _ in range(48))}\n")

    (share / "legal/supplier_memo_orion.txt").write_text(
        "MEMO - SUPPLY AGREEMENT\n\n"
        "This Agreement is made on 2026-03-14 between Lumen Health SAS, represented by "
        "Helene Marchand, and Orion Medical Devices GmbH, represented by Matthias Brandt.\n\n"
        "1. Scope. Orion Medical Devices GmbH shall supply imaging equipment to the Lille and Lyon clinics.\n"
        "2. Price. The total price is 1480000.00 EUR, payable in four instalments. "
        "Payments go to IBAN DE89 3704 0044 0532 0130 00.\n"
        "3. Confidentiality. Both parties shall keep the terms confidential for 7 years.\n"
        "4. Contact. Helene Marchand can be reached at helene.marchand@lumen-health.example "
        "or +33 1 84 22 51 07.\n")

    (share / "finance/budget_2026.csv").write_text(
        "quarter,department,planned_eur\n" + "\n".join(
            f"Q{q},{d},{rng.randint(20, 400) * 1000}" for q in range(1, 5) for d in ("Radiology", "Pharmacy", "IT")) + "\n")
    (share / "hr/holiday_policy.txt").write_text(
        "Holiday policy\n\nEmployees get 25 days of paid leave per year. Requests go through the HR portal.\n")
    (share / "hr/onboarding_checklist.txt").write_text(
        "Onboarding checklist\n\n1. Badge\n2. Laptop\n3. Safety training\n4. Meet the team\n")
    (share / "marketing/newsletter_draft.md").write_text(
        "# Autumn newsletter\n\nFlu shots are available in all clinics from October.\n")
    (share / "marketing/brand_guidelines.txt").write_text(
        "Brand guidelines\n\nUse the teal logo on white. Keep the tone calm and clear.\n")
    (share / "ops/shift_planning_october.txt").write_text(
        "Shift planning October\n\nWeek 41: reception covered by two people. Week 42: one person on leave.\n")
    (share / "ops/cleaning_rota.txt").write_text("Cleaning rota\n\nMonday: floor 1. Wednesday: floor 2.\n")
    (share / "it/printer_setup.txt").write_text("Printer setup\n\nInstall the driver from the IT portal, then add printer FLOOR2.\n")
    (share / "clinical/visiting_hours.txt").write_text("Visiting hours\n\nEvery day from 14:00 to 19:00.\n")
    return share


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "generated/share")
    build(target)
    print(f"dev share written to {target}")
