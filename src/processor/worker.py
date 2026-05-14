import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

from confluent_kafka import Consumer, KafkaError, Producer

from consistent_hash import ConsistentHashRing
from state_store import StateStore
import metrics as m

logger = logging.getLogger(__name__)


@dataclass
class EventData:
    """
    Transport-neutral representation of an ingress Event.
    Decouples business logic from the protobuf generated code so that
    unit tests can construct events without a proto dependency.
    """
    event_id: str = ""
    entity_id: str = ""
    event_type: str = ""
    timestamp_ms: int = 0
    payload: bytes = field(default_factory=bytes)


class ProcessorWorker:
    """
    Kafka consumer that routes events to the correct shard via consistent
    hashing, maintains per-entity state, replicates that state to the next
    node in the ring, and promotes replica state to primary on node failure.
    """

    HEARTBEAT_INTERVAL_S = 5
    HEARTBEAT_TIMEOUT_MS = 30_000
    STORE_GAUGE_INTERVAL_S = 15

    def __init__(
        self,
        node_id: str,
        brokers: str,
        event_topic: str,
        state_topic: str,
        heartbeat_topic: str,
        all_nodes: List[str],
    ) -> None:
        self.node_id = node_id
        self._event_topic = event_topic
        self._state_topic = state_topic
        self._heartbeat_topic = heartbeat_topic
        self._running = False
        self._peer_heartbeats: dict = {}

        self.ring = ConsistentHashRing(vnodes=150)
        for node in all_nodes:
            self.ring.add_node(node)

        # primary_store: entities owned by this node; on_write triggers replication.
        # replica_store: hot-standby copy of the next-upstream node's entities.
        self.primary_store = StateStore(on_write=self._replicate_state)
        self.replica_store = StateStore()

        consumer_base = {
            "bootstrap.servers": brokers,
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
        }
        self._event_consumer = Consumer(
            {**consumer_base, "group.id": f"deps-events-{node_id}"}
        )
        self._state_consumer = Consumer(
            {**consumer_base, "group.id": f"deps-state-{node_id}"}
        )
        self._heartbeat_consumer = Consumer(
            {**consumer_base, "group.id": f"deps-hb-{node_id}"}
        )
        self._producer = Producer({"bootstrap.servers": brokers})

    # ------------------------------------------------------------------
    # Replication
    # ------------------------------------------------------------------

    def _replicate_state(self, entity_id: str, state: dict) -> None:
        msg = json.dumps(
            {"entity_id": entity_id, "state": state, "owner": self.node_id}
        )
        self._producer.produce(
            self._state_topic,
            key=entity_id.encode(),
            value=msg.encode(),
        )
        self._producer.poll(0)

    # ------------------------------------------------------------------
    # Core routing logic (tested independently of Kafka)
    # ------------------------------------------------------------------

    def _process_event(self, event: EventData) -> None:
        """Route event to primary or replica based on the hash ring."""
        primary = self.ring.get_node(event.entity_id)

        if primary == self.node_id:
            t0 = time.monotonic()
            current = self.primary_store.get(event.entity_id) or {
                "event_count": 0,
                "last_event_type": "",
                "last_timestamp_ms": 0,
            }
            current["event_count"] += 1
            current["last_event_type"] = event.event_type
            current["last_timestamp_ms"] = event.timestamp_ms
            # set() triggers _replicate_state via the on_write callback.
            self.primary_store.set(event.entity_id, current)
            m.record_event_processed(self.node_id)
            m.record_processing_duration(self.node_id, time.monotonic() - t0)
            logger.debug(
                "primary | entity=%s type=%s count=%d",
                event.entity_id,
                event.event_type,
                current["event_count"],
            )
        else:
            m.record_event_skipped(self.node_id)
            logger.debug(
                "skip | entity=%s → primary=%s replica=%s",
                event.entity_id,
                primary,
                self.ring.get_replica_node(event.entity_id),
            )

    def _apply_state_update(
        self, entity_id: str, state: dict, owner: str
    ) -> None:
        """
        Store an incoming state update in the replica store if:
          - this node is the designated replica for `entity_id`, AND
          - the update did not originate from this node itself.
        """
        if owner == self.node_id:
            return
        if self.ring.get_replica_node(entity_id) == self.node_id:
            self.replica_store.set(entity_id, state, replicate=False)
            logger.debug("replica stored | entity=%s from=%s", entity_id, owner)

    # ------------------------------------------------------------------
    # Failover
    # ------------------------------------------------------------------

    def handle_node_failure(self, failed_node_id: str) -> None:
        """
        Remove the failed node from the ring. Entity IDs that were previously
        hashed to that node now hash to this worker (the replica). Promote
        those replica states to primary so processing can resume.
        """
        logger.warning("node %s missed heartbeat — initiating failover", failed_node_id)
        self.ring.remove_node(failed_node_id)

        promoted = 0
        for entity_id, state in self.replica_store.snapshot().items():
            if self.ring.get_node(entity_id) == self.node_id:
                self.primary_store.set(entity_id, state)
                promoted += 1

        m.record_failover(self.node_id)
        logger.info(
            "failover complete: promoted %d entities from replica → primary",
            promoted,
        )

    # ------------------------------------------------------------------
    # Kafka deserialization
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_event(value: bytes) -> Optional[EventData]:
        try:
            from proto import event_pb2  # generated at Docker build time
            pb = event_pb2.Event()
            pb.ParseFromString(value)
            return EventData(
                event_id=pb.event_id,
                entity_id=pb.entity_id,
                event_type=pb.event_type,
                timestamp_ms=pb.timestamp_ms,
                payload=pb.payload,
            )
        except Exception:
            logger.exception("failed to deserialize event proto")
            return None

    # ------------------------------------------------------------------
    # Background threads
    # ------------------------------------------------------------------

    def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                payload = json.dumps(
                    {
                        "node_id": self.node_id,
                        "timestamp_ms": int(time.time() * 1000),
                    }
                )
                self._producer.produce(
                    self._heartbeat_topic,
                    key=self.node_id.encode(),
                    value=payload.encode(),
                )
                self._producer.poll(0)
            except Exception:
                logger.exception("heartbeat publish failed")
            time.sleep(self.HEARTBEAT_INTERVAL_S)

    def _check_heartbeats_loop(self) -> None:
        while self._running:
            now_ms = int(time.time() * 1000)
            for node_id, last_ms in list(self._peer_heartbeats.items()):
                if node_id == self.node_id:
                    continue
                if now_ms - last_ms > self.HEARTBEAT_TIMEOUT_MS:
                    if node_id in self.ring.nodes():
                        self.handle_node_failure(node_id)
                        self._peer_heartbeats.pop(node_id, None)
            time.sleep(self.HEARTBEAT_INTERVAL_S)

    def _store_gauge_loop(self) -> None:
        """Periodically push store-size gauges so Grafana always has fresh data."""
        while self._running:
            m.update_store_sizes(
                self.node_id,
                primary=len(self.primary_store.snapshot()),
                replica=len(self.replica_store.snapshot()),
            )
            time.sleep(self.STORE_GAUGE_INTERVAL_S)

    def _consume_aux_topics(self) -> None:
        """Drain state-updates and heartbeats topics on a dedicated thread."""
        self._state_consumer.subscribe([self._state_topic])
        self._heartbeat_consumer.subscribe([self._heartbeat_topic])

        while self._running:
            msg = self._state_consumer.poll(timeout=0.5)
            if msg and not msg.error():
                try:
                    data = json.loads(msg.value().decode())
                    self._apply_state_update(
                        data["entity_id"], data["state"], data["owner"]
                    )
                except Exception:
                    logger.exception("failed to apply state update")

            hb = self._heartbeat_consumer.poll(timeout=0.5)
            if hb and not hb.error():
                try:
                    data = json.loads(hb.value().decode())
                    self._peer_heartbeats[data["node_id"]] = data["timestamp_ms"]
                except Exception:
                    logger.exception("failed to process heartbeat")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._running = True
        self._event_consumer.subscribe([self._event_topic])

        daemon_threads = [
            threading.Thread(target=self._heartbeat_loop,        daemon=True, name="hb-pub"),
            threading.Thread(target=self._check_heartbeats_loop, daemon=True, name="hb-chk"),
            threading.Thread(target=self._consume_aux_topics,    daemon=True, name="aux-consumer"),
            threading.Thread(target=self._store_gauge_loop,      daemon=True, name="gauge-updater"),
        ]
        for t in daemon_threads:
            t.start()

        logger.info("worker %s started | topics: events=%s", self.node_id, self._event_topic)
        try:
            while self._running:
                msg = self._event_consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error("consumer error: %s", msg.error())
                        m.record_kafka_error(self.node_id)
                    continue
                event = self._parse_event(msg.value())
                if event:
                    self._process_event(event)
        finally:
            self._event_consumer.close()
            self._state_consumer.close()
            self._heartbeat_consumer.close()
            logger.info("worker %s stopped", self.node_id)

    def shutdown(self) -> None:
        self._running = False
