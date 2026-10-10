from mirage import fakes
from mirage.contracts import HOST, Event
from mirage.core.db import EventStore


def test_add_and_roundtrip(tmp_path):
    store = EventStore(tmp_path / "sub" / "core.db")  # parent dir is created
    e = Event(10.0, "mine_opened", ref="m1", details={"path": "/srv/share/x"})
    i = store.add(e)
    assert isinstance(i, int)
    [back] = store.all()
    assert back == e
    assert back.host == HOST


def test_add_many_and_ordering(tmp_path):
    store = EventStore(tmp_path / "core.db")
    ids = store.add_many([Event(3.0, "command"), Event(1.0, "command"), Event(1.0, "ticket")])
    assert len(ids) == 3 and ids == sorted(ids)
    got = store.all()
    assert [(e.ts, e.type) for e in got] == [(1.0, "command"), (1.0, "ticket"), (3.0, "command")]


def test_filters(tmp_path):
    store = EventStore(tmp_path / "core.db")
    store.add_many(fakes.ai_attack_events())
    mines = store.all(type="mine_opened")
    assert len(mines) == 1 and mines[0].ref == "m1"
    t = mines[0].ts
    assert all(e.ts >= t for e in store.all(since=t))
    assert len(store.all(since=t)) < len(store.all())
    assert store.all(since=t, type="command")
    assert all(e.type == "command" for e in store.all(since=t, type="command"))


def test_reset_and_persistence(tmp_path):
    path = tmp_path / "core.db"
    store = EventStore(path)
    store.add(Event(1.0, "command", details={"cmd": "id"}))
    store.close()
    store2 = EventStore(path)
    assert store2.count() == 1
    store2.reset()
    assert store2.all() == [] and store2.count() == 0
