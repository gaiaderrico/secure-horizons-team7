import json
import random

from mirage.prepare import believability, dev_seed, forge


def test_quiz_has_five_pairs_and_a_key(tmp_path):
    share = dev_seed.build(tmp_path / "share")
    real = share / "clinical/patients.csv"
    fake = tmp_path / "fake.csv"
    fake.write_bytes(forge.make_twin("patients.csv", real.read_bytes(), forge.TwinContext(random.Random(2))))
    believability.build(real, fake, tmp_path / "out", n=5)
    quiz = (tmp_path / "out/believability.md").read_text()
    key = json.loads((tmp_path / "out/believability_key.json").read_text())
    assert quiz.count("## Pair") == 5 and len(key) == 5 and set(key.values()) <= {"A", "B"}
