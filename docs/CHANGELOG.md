# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
