import pytest
from consistent_hash import ConsistentHashRing


@pytest.fixture
def ring_2():
    """Ring pre-loaded with two nodes."""
    r = ConsistentHashRing(vnodes=150)
    r.add_node("worker-1")
    r.add_node("worker-2")
    return r


@pytest.fixture
def ring_3():
    r = ConsistentHashRing(vnodes=150)
    r.add_node("worker-1")
    r.add_node("worker-2")
    r.add_node("worker-3")
    return r


# ---------------------------------------------------------------------------
# Basic routing
# ---------------------------------------------------------------------------

def test_empty_ring_returns_none():
    r = ConsistentHashRing()
    assert r.get_node("any-key") is None


def test_single_node_owns_all_keys():
    r = ConsistentHashRing(vnodes=50)
    r.add_node("worker-1")
    for key in ["a", "b", "entity-123", "order-xyz", "user-456"]:
        assert r.get_node(key) == "worker-1"


def test_same_key_always_routes_to_same_node(ring_2):
    key = "entity-stable"
    first = ring_2.get_node(key)
    for _ in range(100):
        assert ring_2.get_node(key) == first, "routing must be deterministic"


def test_all_keys_routed_to_a_known_node(ring_3):
    keys = [f"entity-{i}" for i in range(500)]
    nodes = ring_3.nodes()
    for key in keys:
        assert ring_3.get_node(key) in nodes


# ---------------------------------------------------------------------------
# Node lifecycle
# ---------------------------------------------------------------------------

def test_adding_node_redistributes_some_keys():
    r = ConsistentHashRing(vnodes=150)
    r.add_node("worker-1")

    keys = [f"key-{i}" for i in range(1000)]
    before = {k: r.get_node(k) for k in keys}

    r.add_node("worker-2")
    after = {k: r.get_node(k) for k in keys}

    # Some keys moved to worker-2; no key should have moved AWAY from worker-1
    # to a non-existent node.
    moved = sum(1 for k in keys if before[k] != after[k])
    assert moved > 0, "adding a node should redistribute at least some keys"
    assert all(v in {"worker-1", "worker-2"} for v in after.values())


def test_removing_node_routes_its_keys_to_remaining_nodes(ring_2):
    keys = [f"key-{i}" for i in range(500)]
    before = {k: ring_2.get_node(k) for k in keys}

    ring_2.remove_node("worker-2")
    assert ring_2.nodes() == {"worker-1"}

    for key in keys:
        assert ring_2.get_node(key) == "worker-1"


def test_distribution_is_roughly_even(ring_3):
    """With 150 vnodes per node the load imbalance should be < 30%."""
    keys = [f"entity-{i}" for i in range(3000)]
    counts = {"worker-1": 0, "worker-2": 0, "worker-3": 0}
    for k in keys:
        counts[ring_3.get_node(k)] += 1

    expected = len(keys) / 3
    for node, count in counts.items():
        assert abs(count - expected) / expected < 0.30, (
            f"node {node} has {count} keys (expected ~{expected:.0f}); "
            "distribution too imbalanced"
        )


# ---------------------------------------------------------------------------
# Replica routing
# ---------------------------------------------------------------------------

def test_replica_node_differs_from_primary(ring_2):
    for key in [f"entity-{i}" for i in range(200)]:
        primary = ring_2.get_node(key)
        replica = ring_2.get_replica_node(key)
        assert primary != replica, f"key={key}: replica must differ from primary"


def test_replica_returns_none_with_single_node():
    r = ConsistentHashRing(vnodes=50)
    r.add_node("worker-1")
    assert r.get_replica_node("any-key") is None


def test_replica_is_a_known_node(ring_3):
    for key in [f"entity-{i}" for i in range(200)]:
        replica = ring_3.get_replica_node(key)
        assert replica in ring_3.nodes()


def test_replica_is_stable_for_same_key(ring_2):
    key = "entity-stable"
    first_replica = ring_2.get_replica_node(key)
    for _ in range(50):
        assert ring_2.get_replica_node(key) == first_replica
