# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
