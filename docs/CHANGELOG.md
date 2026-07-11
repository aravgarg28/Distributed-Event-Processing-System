# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] - 2026-07-11
### Security
- Added `.gitignore` — `infrastructure/.env` (real Groq/Grafana API keys) and OS/build artifacts can no longer be accidentally committed.
- Grafana admin password is now configurable via `GRAFANA_ADMIN_PASSWORD` in `.env` instead of hardcoded `admin`.
- Capped log text sent to the LLM at 50 lines / 6000 chars per burst (bounds token spend; keeps prompts inside context limits).

### Fixed
- `log_monitor.tail_container`: `container.logs(tail=N)` returns a single bytes blob, not an iterable of lines — iterating it yielded ints and crashed with `AttributeError` on the first real scan. Now decodes and `splitlines()`.
- Error bursts are now deduplicated by SHA-256 fingerprint — previously the same tail-window errors were re-summarized (new Groq call) and re-annotated every 30 s poll, forever.
- `grafana_annotator`: 10 s HTTP timeout (a hung Grafana froze the poll loop indefinitely); connection errors raise `RuntimeError` instead of propagating raw.
- `main.py`: per-burst exception isolation — one LLM/Grafana failure no longer kills the service (which previously crash-looped under `restart: on-failure`); `threading.Event`-based shutdown makes SIGTERM immediate; startup warnings when API keys are empty.
- `src/ingress/Dockerfile`: removed inline comments on `EXPOSE` lines (Dockerfiles parse them as extra port arguments and the build fails).
- Grafana host port moved 3000 → 3001 to avoid clashing with another local project (container-internal URL unchanged).

## [0.5.0] - 2026-05-14
### Added
- Phase 5 complete: AI Log Summarizer.
- `src/ai_debugger/log_monitor.py`: `LogMonitor` tails Docker container logs via `docker-py`; `is_error_line` detects error/fatal/exception/traceback/panic/critical (case-insensitive); `collect_burst` returns `ErrorBurst` when error line count meets configurable threshold (default 5); `scan` iterates all watched containers and yields bursts.
- `src/ai_debugger/summarizer.py`: `LogSummarizer` wraps a LangChain chain (`ChatPromptTemplate | ChatAnthropic | StrOutputParser`) using `claude-haiku-4-5-20251001`; SRE-tuned system prompt instructs the LLM to identify what failed, why, and the first remediation step in 2-4 sentences; chain built lazily on first `summarize()` call.
- `src/ai_debugger/grafana_annotator.py`: `GrafanaAnnotator` POSTs to Grafana `/api/annotations` with Bearer token auth; merges default `ai-debugger` tag with per-burst container tag; `annotate_burst` convenience method formats `[container] summary` text and returns annotation id; raises `RuntimeError` on non-200 status.
- `src/ai_debugger/main.py`: poll loop (configurable interval, default 30s) — `scan → summarize → annotate`; reads all config from env vars; graceful SIGTERM/SIGINT shutdown.
- `src/ai_debugger/Dockerfile`: `python:3.11-slim`; installs requirements; mounts Docker socket at runtime via docker-compose volume.
- `src/ai_debugger/requirements.txt`: `docker==7.1.0`, `langchain==0.2.16`, `langchain-anthropic==0.1.23`, `anthropic==0.34.2`, `requests==2.32.3`.
- `.env.example`: documents `ANTHROPIC_API_KEY` and `GRAFANA_API_TOKEN` — copy to `.env` before `make up`.
- `infrastructure/docker-compose.yml`: `ai-debugger` service mounts `/var/run/docker.sock` (read-only); depends on Grafana health check; reads secrets from `.env` via `${VAR}` interpolation.
- `tests/ai_debugger/conftest.py`, `test_log_monitor.py`, `test_summarizer.py`, `test_grafana_annotator.py`: 37 unit tests covering all behaviour paths (TDD — written before implementation).

## [0.4.0] - 2026-05-14
### Added
- Phase 4 complete: Observability Integration.
- `src/ingress/metrics.h/cpp`: `IngressMetrics` wraps prometheus-cpp; 5 families — `deps_ingress_requests_total`, `deps_ingress_requests_errors_total`, `deps_ingress_request_duration_seconds` (histogram, 11 buckets), `deps_ingress_kafka_published_total`, `deps_ingress_kafka_publish_errors_total`. `start_http_server=false` for unit tests.
- `src/ingress/server.h/cpp`: `EventIngressServiceImpl` now accepts optional `shared_ptr<IngressMetrics>`; records per-method counters + duration in `Submit`/`SubmitBatch`; kafka publish outcome in `PublishEvent`. Backward-compatible (nullptr disables recording — existing tests unchanged).
- `src/ingress/CMakeLists.txt`: FetchContent pulls prometheus-cpp v1.2.4 at configure time (shallow clone, testing + compression disabled).
- `src/ingress/Dockerfile`: added `git` for FetchContent; split configure (dep download) and build into separate layers for Docker cache efficiency; added `METRICS_ADDRESS` env var.
- `tests/ingress/test_metrics.cpp`: 6 tests verifying all 5 metric families register and counters increment correctly.
- `src/processor/metrics.py`: 7 metric families (`EVENTS_PROCESSED`, `EVENTS_SKIPPED`, `PROCESSING_DURATION` histogram, `KAFKA_CONSUMER_ERRORS`, `PRIMARY/REPLICA_STORE_ENTITIES` gauges, `FAILOVERS_TOTAL`); helper functions for every record path.
- `src/processor/worker.py`: records processed/skipped + latency in `_process_event`; kafka errors in run loop; failover counter in `handle_node_failure`; store-size gauges refreshed every 15 s via `_store_gauge_loop`.
- `src/processor/main.py`: starts prometheus HTTP server on `METRICS_PORT` (default 8081).
- `tests/processor/test_metrics.py`: 7 tests covering every record function.
- `infrastructure/grafana/provisioning/dashboards/dashboards.yml`: file-based dashboard provisioner, 30 s reload.
- `infrastructure/grafana/provisioning/dashboards/deps_overview.json`: 9-panel dashboard — ingress RPS, error rate, p50/p95/p99 latency, Kafka publish rate; processor events/s per node, processing latency p99, store entity gauges, failover stat, consumer errors.
- `infrastructure/prometheus/prometheus.yml`: concrete scrape targets — `ingress:8080`, `processor-1:8081`, `processor-2:8081`.
- `infrastructure/docker-compose.yml`: processor-1 exposes `:8081`, processor-2 exposes `:8082→8081`; Grafana mounts datasources and dashboards dirs separately.

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
