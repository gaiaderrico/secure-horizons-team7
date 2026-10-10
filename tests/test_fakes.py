from mirage import fakes
from mirage.contracts import Event


def test_fake_sequences_are_sorted_events():
    for seq in (fakes.ai_attack_events(), fakes.guided_ai_attack_events(),
                fakes.script_attack_events(), fakes.human_attack_events()):
        assert all(isinstance(e, Event) for e in seq)
        assert [e.ts for e in seq] == sorted(e.ts for e in seq)
