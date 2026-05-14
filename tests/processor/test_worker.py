"""
Unit tests for ProcessorWorker.

All Kafka I/O is mocked — tests cover only the pure routing, state-update,
and failover logic. The `_process_event` and `_apply_state_update` methods
accept EventData and plain dicts, so no proto or Kafka dependency is needed.
"""
import pytest
from unittest.mock import MagicMock, patch

from worker import ProcessorWorker, EventData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_worker(node_id: str = "worker-1", all_nodes=None):
    """Build a ProcessorWorker with all Kafka I/O mocked out."""
    all_nodes = all_nodes or ["worker-1", "worker-2"]
    with patch("worker.Consumer"), patch("worker.Producer"):
        w = ProcessorWorker(
            node_id=node_id,
            brokers="localhost:9092",
            event_topic="events",
            state_topic="state-updates",
            heartbeat_topic="heartbeats",
            all_nodes=all_nodes,
        )
    return w


def make_event(**kwargs) -> EventData:
    defaults = dict(
        event_id="evt-1",
        entity_id="entity-abc",
        event_type="user.click",
        timestamp_ms=1_700_000_000_000,
        payload=b"",
    )
    defaults.update(kwargs)
    return EventData(**defaults)


# ---------------------------------------------------------------------------
# _process_event — primary path
# ---------------------------------------------------------------------------

def test_primary_node_increments_event_count():
    w = make_worker("worker-1", ["worker-1", "worker-2"])
    entity_id = next(
        eid for eid in (f"entity-{i}" for i in range(500))
        if w.ring.get_node(eid) == "worker-1"
    )
    event = make_event(entity_id=entity_id)

    w._process_event(event)
    state = w.primary_store.get(entity_id)

    assert state is not None
    assert state["event_count"] == 1
    assert state["last_event_type"] == "user.click"
    assert state["last_timestamp_ms"] == 1_700_000_000_000


def test_primary_node_accumulates_count_across_calls():
    w = make_worker("worker-1", ["worker-1", "worker-2"])
    entity_id = next(
        eid for eid in (f"entity-{i}" for i in range(500))
        if w.ring.get_node(eid) == "worker-1"
    )
    for _ in range(5):
        w._process_event(make_event(entity_id=entity_id))

    assert w.primary_store.get(entity_id)["event_count"] == 5


def test_non_primary_does_not_write_to_primary_store():
    w = make_worker("worker-1", ["worker-1", "worker-2"])
    entity_id = next(
        eid for eid in (f"entity-{i}" for i in range(500))
        if w.ring.get_node(eid) == "worker-2"   # owned by the OTHER node
    )
    w._process_event(make_event(entity_id=entity_id))
    assert w.primary_store.get(entity_id) is None


# ---------------------------------------------------------------------------
# _apply_state_update — replica path
# ---------------------------------------------------------------------------

def test_replica_stores_state_from_primary():
    w = make_worker("worker-2", ["worker-1", "worker-2"])
    entity_id = next(
        eid for eid in (f"entity-{i}" for i in range(500))
        if w.ring.get_node(eid) == "worker-1"
        and w.ring.get_replica_node(eid) == "worker-2"
    )
    state = {"event_count": 42, "last_event_type": "order.placed", "last_timestamp_ms": 0}

    w._apply_state_update(entity_id, state, owner="worker-1")

    assert w.replica_store.get(entity_id) == state


def test_non_replica_ignores_state_update():
    # worker-1 receives a state update for an entity it's neither primary
    # nor replica for (three-node ring scenario).
    w = make_worker("worker-1", ["worker-1", "worker-2", "worker-3"])
    entity_id = next(
        eid for eid in (f"entity-{i}" for i in range(1000))
        if w.ring.get_node(eid) != "worker-1"
        and w.ring.get_replica_node(eid) != "worker-1"
    )
    w._apply_state_update(entity_id, {"event_count": 7}, owner="worker-2")
    assert w.replica_store.get(entity_id) is None


def test_node_does_not_store_its_own_state_as_replica():
    w = make_worker("worker-1", ["worker-1", "worker-2"])
    entity_id = next(
        eid for eid in (f"entity-{i}" for i in range(500))
        if w.ring.get_node(eid) == "worker-1"
    )
    # A state update whose owner IS this node should not be written to replica.
    w._apply_state_update(entity_id, {"event_count": 3}, owner="worker-1")
    assert w.replica_store.get(entity_id) is None


# ---------------------------------------------------------------------------
# handle_node_failure — failover
# ---------------------------------------------------------------------------

def test_failed_node_removed_from_ring():
    w = make_worker("worker-1", ["worker-1", "worker-2"])
    assert "worker-2" in w.ring.nodes()

    w.handle_node_failure("worker-2")

    assert "worker-2" not in w.ring.nodes()


def test_failover_promotes_replica_state_to_primary():
    w = make_worker("worker-2", ["worker-1", "worker-2"])
    entity_id = next(
        eid for eid in (f"entity-{i}" for i in range(500))
        if w.ring.get_node(eid) == "worker-1"
        and w.ring.get_replica_node(eid) == "worker-2"
    )
    replica_state = {"event_count": 10, "last_event_type": "checkout", "last_timestamp_ms": 0}
    w.replica_store.set(entity_id, replica_state, replicate=False)

    w.handle_node_failure("worker-1")

    promoted = w.primary_store.get(entity_id)
    assert promoted == replica_state


def test_failover_only_promotes_entities_now_owned_by_this_node():
    w = make_worker("worker-2", ["worker-1", "worker-2", "worker-3"])
    # Seed replica store with entities owned by different nodes
    owned_by_1 = next(
        eid for eid in (f"entity-{i}" for i in range(1000))
        if w.ring.get_node(eid) == "worker-1"
        and w.ring.get_replica_node(eid) == "worker-2"
    )
    owned_by_3 = next(
        eid for eid in (f"entity-{i}" for i in range(1000))
        if w.ring.get_node(eid) == "worker-3"
        and w.ring.get_replica_node(eid) == "worker-2"
    )

    w.replica_store.set(owned_by_1, {"event_count": 5}, replicate=False)
    w.replica_store.set(owned_by_3, {"event_count": 9}, replicate=False)

    w.handle_node_failure("worker-1")

    # owned_by_1 now maps to worker-2 → promoted
    assert w.primary_store.get(owned_by_1) is not None
    # owned_by_3 still maps to worker-3 → NOT promoted
    assert w.primary_store.get(owned_by_3) is None
