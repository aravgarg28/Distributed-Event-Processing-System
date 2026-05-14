import copy
import threading
from typing import Any, Callable, Dict, Optional


class StateStore:
    """
    Thread-safe in-memory key-value store for per-entity processor state.

    An optional `on_write` callback is invoked synchronously after every
    successful set() with replicate=True — used by the primary node to
    publish state updates to the Kafka replication topic.
    """

    def __init__(
        self, on_write: Optional[Callable[[str, Any], None]] = None
    ) -> None:
        self._data: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._on_write = on_write

    def get(self, entity_id: str) -> Optional[Any]:
        with self._lock:
            return self._data.get(entity_id)

    def set(self, entity_id: str, state: Any, replicate: bool = True) -> None:
        with self._lock:
            self._data[entity_id] = state
        if replicate and self._on_write:
            self._on_write(entity_id, state)

    def delete(self, entity_id: str) -> None:
        with self._lock:
            self._data.pop(entity_id, None)

    def snapshot(self) -> Dict[str, Any]:
        """Return a deep copy so callers cannot mutate stored state."""
        with self._lock:
            return copy.deepcopy(self._data)

    def restore(self, data: Dict[str, Any]) -> None:
        """Merge `data` into the store — used during failover to seed state."""
        with self._lock:
            self._data.update(data)
