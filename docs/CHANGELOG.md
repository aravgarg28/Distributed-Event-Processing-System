# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-05-14
### Added
- Phase 3 complete: Processor & Sharding Logic.
- `src/processor/consistent_hash.py`: `ConsistentHashRing` with configurable vnodes (default 150) using MD5 hashing. `get_node(key)` returns the primary; `get_replica_node(key)` returns the first distinct clockwise node — the hot-standby. Tested for determinism, even distribution (<30% imbalance), and correct replica/primary separation.
- `src/processor/state_store.py`: Thread-safe (RLock) per-entity state store with `get`/`set`/`delete`/`snapshot` (deep copy)/`restore`. Optional `on_write` callback for write-through replication; `replicate=False` suppresses it for replica ingestion.
- `src/processor/worker.py`: `ProcessorWorker` — Kafka consumer that routes events via `ConsistentHashRing`; primary node accumulates per-entity state (event_count, last_event_type, last_timestamp_ms) and replicates to the `state-updates` topic via `on_write`. Replica node stores updates from `state-updates`. Background threads: heartbeat publisher (5 s interval), heartbeat checker (30 s timeout → `handle_node_failure`), aux topic consumer. `handle_node_failure(node_id)` removes node from ring and promotes matching replica state to primary. `EventData` dataclass decouples proto from business logic, enabling pure-Python unit tests.
- `src/processor/main.py`: Reads `NODE_ID`, `ALL_NODES`, `KAFKA_BROKERS`, `KAFKA_TOPIC`, `STATE_TOPIC`, `HEARTBEAT_TOPIC` from env; SIGTERM/SIGINT graceful shutdown.
- `src/processor/Dockerfile`: Multi-stage Python 3.11-slim build; generates Python proto stubs from shared `src/ingress/event.proto` at build time using `grpcio-tools`.
- `src/processor/requirements.txt`: `confluent-kafka==2.3.0`, `protobuf==4.25.3`, `grpcio-tools==1.62.2`.
- `infrastructure/docker-compose.yml`: Added `processor-1` (worker-1) and `processor-2` (worker-2) services; both use internal Kafka listener (`kafka:29092`), share `ALL_NODES=worker-1,worker-2`, and depend on Kafka health check.
- `tests/processor/test_consistent_hash.py`: 11 tests — determinism, full coverage, node lifecycle, distribution quality, replica correctness.
- `tests/processor/test_state_store.py`: 10 tests — CRUD, snapshot isolation (deep copy), callback control, thread safety.
- `tests/processor/test_worker.py`: 9 tests — primary event accumulation, non-primary skip, replica storage, non-replica ignore, self-update exclusion, failover ring removal, replica promotion, scoped promotion. All 30 tests pass.
- `pytest.ini`: root-level pytest configuration pointing at `tests/`.

### Fixed
- `state_store.py` snapshot() was returning a shallow copy; nested dict mutation escaped the store. Changed to `copy.deepcopy` (caught by TDD test before any production code ran this path).

## [0.2.0] - 2026-05-14
### Added
- Phase 2 complete: Ingress & Messaging Layer.
- `src/ingress/event.proto`: protobuf schema defining `Event` (event_id, entity_id, event_type, timestamp_ms, payload), `EventIngress` gRPC service with `Submit` and `SubmitBatch` RPCs.
- `src/ingress/kafka_producer.h`: `IKafkaProducer` abstract interface (enables test doubles) + `KafkaProducer` PIMPL implementation wrapping librdkafka C++ API. Configured with `linger.ms=5`, `batch.num.messages=10000`, and `lz4` compression for throughput.
- `src/ingress/server.h / server.cpp`: `EventIngressServiceImpl` routes each event to Kafka using `entity_id` as the partition key (consistent hash distribution). `IngressServer` wraps a multi-threaded gRPC sync server (configurable poller pool).
- `src/ingress/main.cpp`: reads `KAFKA_BROKERS`, `KAFKA_TOPIC`, `GRPC_LISTEN_ADDRESS` from env; graceful shutdown on SIGTERM/SIGINT.
- `src/ingress/CMakeLists.txt`: generates pb/grpc sources from event.proto at build time; exports `ingress_lib` (static) linked by both the binary and the test suite.
- `src/ingress/Dockerfile`: multi-stage build (Ubuntu 22.04 builder → minimal runtime); installs grpc++, protobuf, rdkafka via apt.
- `CMakeLists.txt` (root): top-level project wiring `src/ingress` + `tests/ingress`.
- `tests/ingress/test_server.cpp`: 6 GMock-based unit tests covering Submit (success, Kafka failure, missing event) and SubmitBatch (full success, partial failure, empty batch) — written before implementation per TDD.
- `tests/ingress/test_kafka_producer.cpp`: compile-time IS-A assertion + offline-broker behavior tests.
- `infrastructure/docker-compose.yml`: added `ingress` service (builds from `src/ingress/Dockerfile`, exposes gRPC:50051 and metrics:8080, depends on Kafka health check).
- `Makefile`: added `build` and `test` targets for local C++ development.

## [0.1.0] - 2026-05-14
### Added
- Phase 1 complete: Infrastructure & Scaffolding.
- `src/ingress/`, `src/processor/`, `src/ai_debugger/` directory stubs (`.gitkeep`) matching the architecture spec.
- `infrastructure/docker-compose.yml`: Kafka 7.6.1 in KRaft mode (no Zookeeper), Prometheus v2.52.0, Grafana 10.4.3 on a shared `deps-network` bridge. Dual Kafka listeners (PLAINTEXT:9092 for host clients, PLAINTEXT_INTERNAL:29092 for inter-container). Health checks on all services.
- `infrastructure/prometheus/prometheus.yml`: 15s global scrape interval; placeholder scrape jobs for `deps-ingress` and `deps-processor` ready for Phase 4 instrumentation.
- `infrastructure/grafana/provisioning/datasources/prometheus.yml`: Prometheus auto-provisioned as the default Grafana datasource at startup (configuration as code).
- `Makefile`: `up`, `down`, `logs`, `clean`, `status` targets wrapping `docker compose`.

### Initial
- Initial project documentation structure initialized for Claude Code.
