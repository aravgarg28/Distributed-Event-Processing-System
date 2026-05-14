import threading
import pytest
from state_store import StateStore


def test_set_and_get():
    store = StateStore()
    store.set("entity-1", {"count": 1})
    assert store.get("entity-1") == {"count": 1}


def test_get_missing_key_returns_none():
    store = StateStore()
    assert store.get("no-such-key") is None


def test_overwrite_replaces_value():
    store = StateStore()
    store.set("entity-1", {"count": 1})
    store.set("entity-1", {"count": 99})
    assert store.get("entity-1") == {"count": 99}


def test_delete_removes_key():
    store = StateStore()
    store.set("entity-1", {"x": 1})
    store.delete("entity-1")
    assert store.get("entity-1") is None


def test_delete_missing_key_is_a_no_op():
    store = StateStore()
    store.delete("ghost")  # must not raise


def test_snapshot_is_a_copy_not_a_reference():
    store = StateStore()
    store.set("entity-1", {"count": 1})
    snap = store.snapshot()
    snap["entity-1"]["count"] = 999
    # Mutation of snapshot must not affect the store
    assert store.get("entity-1") == {"count": 1}


def test_restore_merges_into_existing_state():
    store = StateStore()
    store.set("entity-1", {"count": 1})
    store.restore({"entity-2": {"count": 2}, "entity-3": {"count": 3}})
    assert store.get("entity-1") == {"count": 1}
    assert store.get("entity-2") == {"count": 2}
    assert store.get("entity-3") == {"count": 3}


def test_on_write_callback_invoked_on_set():
    calls = []
    store = StateStore(on_write=lambda eid, state: calls.append((eid, state)))
    store.set("entity-1", {"count": 5})
    assert calls == [("entity-1", {"count": 5})]


def test_on_write_not_invoked_when_replicate_false():
    calls = []
    store = StateStore(on_write=lambda eid, state: calls.append((eid, state)))
    store.set("entity-1", {"count": 5}, replicate=False)
    assert calls == []


def test_thread_safe_concurrent_writes():
    store = StateStore()
    errors = []

    def writer(entity_id: str, n: int) -> None:
        for i in range(n):
            try:
                store.set(entity_id, {"count": i})
            except Exception as exc:
                errors.append(exc)

    threads = [threading.Thread(target=writer, args=(f"entity-{t}", 200))
               for t in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent writes raised: {errors}"
    # Each entity should have a valid final state
    for t in range(10):
        state = store.get(f"entity-{t}")
        assert state is not None
        assert 0 <= state["count"] < 200
