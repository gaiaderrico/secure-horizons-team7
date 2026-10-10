import csv
import io
import json
import random

import pytest

from mirage.prepare import dev_seed, forge, mines
from mirage.prepare.classify import classify
from mirage.prepare.run_all import run
from mirage.prepare.verify_decoy import verify_decoy


@pytest.fixture()
def share(tmp_path):
    return dev_seed.build(tmp_path / "share")


def test_classify_finds_the_three_crown_jewels(share):
    labels = {p.relative_to(share).as_posix(): classify(p.relative_to(share).as_posix(), p.read_bytes())["label"]
              for p in share.rglob("*") if p.is_file()}
    crown = sorted(k for k, v in labels.items() if v == "crown_jewel")
    assert crown == ["clinical/patients.csv", "it/.env", "legal/supplier_memo_orion.txt"]
    assert labels["marketing/newsletter_draft.md"] == "normal"


def test_reason_describes_the_file(share):
    c = classify("clinical/patients.csv", (share / "clinical/patients.csv").read_bytes())
    assert "400 patients" in c["reason"] and "diagnoses" in c["reason"]


@pytest.mark.parametrize("rel", ["clinical/patients.csv", "it/.env", "legal/supplier_memo_orion.txt"])
def test_twin_passes_verify_and_differs(share, rel):
    real = (share / rel).read_bytes()
    ctx = forge.TwinContext(random.Random(3))
    fake = forge.make_twin(rel.rsplit("/", 1)[-1], real, ctx)
    rep = verify_decoy(rel.rsplit("/", 1)[-1], real, fake, ctx.beacons)
    assert rep.ok, rep.problems
    assert fake != real


def test_csv_twin_keeps_shape_and_has_canaries(share):
    real = (share / "clinical/patients.csv").read_bytes()
    ctx = forge.TwinContext(random.Random(1))
    fake = forge.make_twin("patients.csv", real, ctx)
    r, f = list(csv.reader(io.StringIO(real.decode()))), list(csv.reader(io.StringIO(fake.decode())))
    assert f[0] == r[0] and len(f) == len(r)
    assert len(ctx.beacons) == 3 and all(b.endswith("@lumen-canary.test") for b in ctx.beacons)
    assert all(b in fake.decode() for b in ctx.beacons)


def test_env_twin_beacon_and_tripwire(share):
    real = (share / "it/.env").read_bytes().decode()
    ctx = forge.TwinContext(random.Random(1))
    fake = forge.make_twin(".env", real.encode(), ctx).decode()
    assert len(ctx.beacons) == 1 and ctx.beacons[0].startswith("lmn_canary_")
    assert "BILLING_API_URL=http://internal-api.lumen.local" in fake
    for line in real.splitlines():
        if line.startswith(("DATABASE_URL", "SMTP_PASSWORD", "JWT_SECRET", "BILLING_API_KEY")):
            assert line.split("=", 1)[1] not in fake


def test_verify_catches_a_leak(share):
    real = (share / "clinical/patients.csv").read_bytes()
    ctx = forge.TwinContext(random.Random(1))
    fake = forge.make_twin("patients.csv", real, ctx).decode().splitlines()
    fake[5] = real.decode().splitlines()[5]  # a real row slips in
    rep = verify_decoy("patients.csv", real, ("\n".join(fake) + "\n").encode())
    assert not rep.ok and any("no_real_values" in p for p in rep.problems)


def test_verify_catches_copy_and_missing_beacon(share):
    real = (share / "it/.env").read_bytes()
    assert not verify_decoy(".env", real, real).ok
    ctx = forge.TwinContext(random.Random(1))
    fake = forge.make_twin(".env", real, ctx)
    assert not verify_decoy(".env", real, fake, ["lmn_canary_absent"]).ok


def test_verify_catches_changed_columns(share):
    real = (share / "finance/budget_2026.csv").read_bytes()
    fake = b"a,b\n1,2\n"
    assert not verify_decoy("budget_2026.csv", real, fake).ok


def test_binary_is_unsupported():
    with pytest.raises(forge.UnsupportedFile):
        forge.make_twin("scan.pdf", b"\xff\xfe\x00\x01", forge.TwinContext(random.Random(1)))


def test_mine_note_has_code_endpoint_and_fields():
    rng = random.Random(1)
    codes = mines.new_codes(rng, 4)
    assert len(set(codes)) == 4
    note = mines.render_note(codes[0])
    assert codes[0] in note and mines.ENDPOINT in note
    for field in ("code", "objective", "instructions"):
        assert field in note
    assert mines.valid_template(mines.DEFAULT_NOTE)
    assert not mines.valid_template("# no placeholders here")


def test_run_all_produces_the_contract(share, tmp_path):
    stage, manifest = tmp_path / "stage", tmp_path / "manifest.json"
    rc = run(share, stage, manifest, "/srv/share", "/srv/.stage", seed=7, report_path=tmp_path / "classification.md")
    assert rc == 0
    m = json.loads(manifest.read_text())
    assert set(m) == {"crown_jewels", "mines"}
    assert [c["id"] for c in m["crown_jewels"]] == ["cj1", "cj2", "cj3"]
    for cj in m["crown_jewels"]:
        assert set(cj) == {"id", "real_path", "stage_path", "category", "reason", "beacons"}
        assert cj["real_path"].startswith("/srv/share/")
        assert (stage / cj["stage_path"].rsplit("/", 1)[-1]).exists()
    assert m["crown_jewels"][1]["stage_path"] == "/srv/.stage/cj2.env"
    assert len(m["mines"]) == 7
    for mine in m["mines"]:
        assert set(mine) == {"id", "path", "code"}
        rel = mine["path"].removeprefix("/srv/share/")
        assert mine["code"] in (share / rel).read_text()
    # mines must never be classified as ordinary files on a re-run, and the run is repeatable
    assert run(share, stage, manifest, "/srv/share", "/srv/.stage", seed=7) == 0
    assert len(json.loads(manifest.read_text())["crown_jewels"]) == 3


def test_run_all_is_deterministic(share, tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    run(share, tmp_path / "sa", a, "/srv/share", "/srv/.stage", seed=11)
    run(share, tmp_path / "sb", b, "/srv/share", "/srv/.stage", seed=11)
    assert json.loads(a.read_text()) == json.loads(b.read_text())
    assert (tmp_path / "sa/cj1.csv").read_bytes() == (tmp_path / "sb/cj1.csv").read_bytes()


def test_unforgeable_crown_jewel_fails_the_run(share, tmp_path):
    (share / "it").joinpath("server.key").write_bytes(b"\xff\xfe\x00binary")
    rc = run(share, tmp_path / "stage", tmp_path / "m.json", "/srv/share", "/srv/.stage")
    assert rc == 2
