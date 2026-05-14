# Implementation Roadmap

**Status Key:** [ ] Not Started | [~] In Progress | [x] Completed

## Phase 1: Infrastructure & Scaffolding
- [x] Set up project directory structure.
- [x] Create `docker-compose.yml` containing Kafka (KRaft), Prometheus, and Grafana.
- [x] Create a `Makefile` or build scripts for easy environment spin-up.

## Phase 2: Ingress & Messaging Layer
- [x] Define the protobuf (`.proto`) schema for the Event payload.
- [x] Build the C++ gRPC Server (Ingress) to accept events.
- [x] Integrate a C++ Kafka Producer into the Ingress service to asynchronously batch and publish events.

## Phase 3: Processor & Sharding Logic
- [ ] Build the Python Kafka Consumer worker.
- [ ] Implement the consistent-hashing ring logic to route events to specific internal processors.
- [ ] Implement state replication and automatic failover logic for the Python workers.

## Phase 4: Observability Integration
- [ ] Instrument the C++ Ingress node with Prometheus metrics (requests/sec, latency).
- [ ] Instrument the Python workers with Prometheus metrics (processing time, error rate).
- [ ] Provision a default Grafana dashboard via configuration as code.

## Phase 5: The AI Log Summarizer
- [ ] Build a Python service using LangChain that tails the Docker logs or receives error events.
- [ ] Prompt engineer the LangChain service to extract root causes from raw error logs.
- [ ] Connect the LangChain service to the Grafana API to push human-readable text as Annotations on the metrics graphs.
