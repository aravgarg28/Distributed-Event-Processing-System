from prometheus_client import Counter, Gauge, Histogram, start_http_server

EVENTS_PROCESSED = Counter(
    "deps_processor_events_processed_total",
    "Events successfully processed by this node as primary shard owner",
    ["node_id"],
)

EVENTS_SKIPPED = Counter(
    "deps_processor_events_skipped_total",
    "Events received but routed to another node (not primary)",
    ["node_id"],
)

PROCESSING_DURATION = Histogram(
    "deps_processor_processing_duration_seconds",
    "Latency of _process_event() on the primary path",
    ["node_id"],
    buckets=[.0005, .001, .005, .01, .025, .05, .1, .25, .5, 1.0],
)

KAFKA_CONSUMER_ERRORS = Counter(
    "deps_processor_kafka_consumer_errors_total",
    "Non-EOF Kafka consumer errors",
    ["node_id"],
)

PRIMARY_STORE_ENTITIES = Gauge(
    "deps_processor_primary_store_entities",
    "Number of entities currently held in the primary state store",
    ["node_id"],
)

REPLICA_STORE_ENTITIES = Gauge(
    "deps_processor_replica_store_entities",
    "Number of entities currently held in the replica state store",
    ["node_id"],
)

FAILOVERS_TOTAL = Counter(
    "deps_processor_failovers_total",
    "Number of node failover events triggered by this worker",
    ["node_id"],
)


def record_event_processed(node_id: str) -> None:
    EVENTS_PROCESSED.labels(node_id=node_id).inc()


def record_event_skipped(node_id: str) -> None:
    EVENTS_SKIPPED.labels(node_id=node_id).inc()


def record_processing_duration(node_id: str, duration_s: float) -> None:
    PROCESSING_DURATION.labels(node_id=node_id).observe(duration_s)


def record_kafka_error(node_id: str) -> None:
    KAFKA_CONSUMER_ERRORS.labels(node_id=node_id).inc()


def record_failover(node_id: str) -> None:
    FAILOVERS_TOTAL.labels(node_id=node_id).inc()


def update_store_sizes(node_id: str, primary: int, replica: int) -> None:
    PRIMARY_STORE_ENTITIES.labels(node_id=node_id).set(primary)
    REPLICA_STORE_ENTITIES.labels(node_id=node_id).set(replica)


def start_metrics_server(port: int = 8081) -> None:
    start_http_server(port)
