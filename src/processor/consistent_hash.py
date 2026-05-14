import hashlib
from typing import Dict, List, Optional, Set


class ConsistentHashRing:
    """
    Hash ring with virtual nodes (vnodes) for even key distribution.

    Each physical node is represented by `vnodes` points on the ring.
    Keys are routed to the first node whose ring position is >= the key's hash,
    wrapping around if necessary (standard consistent hashing).

    Replica routing returns the first *distinct* node clockwise after the primary,
    which is the node that holds the hot-standby copy for failover.
    """

    def __init__(self, vnodes: int = 150) -> None:
        self.vnodes = vnodes
        self._ring: Dict[int, str] = {}      # ring_position -> node_id
        self._sorted_keys: List[int] = []

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode(), usedforsecurity=False).hexdigest(), 16)

    def _rebuild_sorted_keys(self) -> None:
        self._sorted_keys = sorted(self._ring.keys())

    # ------------------------------------------------------------------
    # Node lifecycle
    # ------------------------------------------------------------------

    def add_node(self, node_id: str) -> None:
        for i in range(self.vnodes):
            pos = self._hash(f"{node_id}:{i}")
            self._ring[pos] = node_id
        self._rebuild_sorted_keys()

    def remove_node(self, node_id: str) -> None:
        for i in range(self.vnodes):
            pos = self._hash(f"{node_id}:{i}")
            self._ring.pop(pos, None)
        self._rebuild_sorted_keys()

    def nodes(self) -> Set[str]:
        return set(self._ring.values())

    # ------------------------------------------------------------------
    # Key routing
    # ------------------------------------------------------------------

    def get_node(self, key: str) -> Optional[str]:
        """Return the primary node for `key`, or None if the ring is empty."""
        if not self._ring:
            return None
        h = self._hash(key)
        for pos in self._sorted_keys:
            if h <= pos:
                return self._ring[pos]
        return self._ring[self._sorted_keys[0]]  # wrap around

    def get_replica_node(self, key: str) -> Optional[str]:
        """
        Return the first node clockwise after the primary that is distinct
        from it — the designated hot-standby replica for `key`.
        Returns None when fewer than two distinct nodes exist.
        """
        if len(self.nodes()) < 2:
            return None

        primary = self.get_node(key)
        h = self._hash(key)

        # Walk clockwise from key's position, skipping the primary's vnodes.
        for pos in self._sorted_keys:
            if pos >= h and self._ring[pos] != primary:
                return self._ring[pos]

        # Wrap around from the start of the ring.
        for pos in self._sorted_keys:
            if self._ring[pos] != primary:
                return self._ring[pos]

        return None
