<div align="center">

# ⚡ Distributed Event Processing System

**A high-throughput, fault-tolerant event pipeline built to process 1M+ events/hour**

Consistent-hash sharding · Kafka-backed durability · automatic failover · AI-assisted observability

<br>

![C++](https://img.shields.io/badge/C%2B%2B-17-00599C?style=flat-square&logo=cplusplus&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache_Kafka-KRaft-231F20?style=flat-square&logo=apachekafka&logoColor=white)
![gRPC](https://img.shields.io/badge/gRPC-Protobuf-244c5a?style=flat-square&logo=grpc&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-Grafana-E6522C?style=flat-square&logo=prometheus&logoColor=white)

</div>

---

## Overview

**DEPS** ingests real-time events over gRPC, streams them through Kafka, and processes them across a ring of Python workers that shard state by entity using **consistent hashing**. Every shard is hot-replicated to a neighbouring node, so a worker can die mid-stream and its state is promoted automatically — no data loss, no manual intervention.

On top of the data plane sits an **observability plane**: Prometheus scrapes metrics from every service, Grafana visualizes them, and a LangChain-powered **AI debugger** watches the logs — when errors spike, it summarizes the root cause with an LLM and pins a human-readable annotation directly onto the Grafana timeline.

---

## See it in action

The signature demo is the system **healing itself**: kill a worker mid-stream and watch a replica auto-promote in ~30s with zero data loss — then watch the AI debugger explain the failure on the dashboard.

> 📽️ **Record the demo** → follow the 3-minute script in [`DEMO.md`](DEMO.md).
> Drop the resulting clip in as `docs/demo.gif` and it renders right here.

<!-- ![DEPS self-healing demo](docs/demo.gif) -->

---

## Architecture

```
                    ┌──────────────┐
   Event Sources ──▶│   Ingress    │  C++ · gRPC server + async Kafka producer
      (gRPC)        │  (50051)     │  partitions by entity_id
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    Kafka     │  KRaft mode — events · state-updates · heartbeats
                    │   (9092)     │
                    └──────┬───────┘
              ┌────────────┴────────────┐
        ┌─────▼──────┐            ┌──────▼─────┐
        │ processor-1│◀─replicate─▶│ processor-2│   Python · consistent-hash ring
        │  worker-1  │  heartbeat  │  worker-2  │   primary + hot-standby per shard
        └─────┬──────┘            └──────┬─────┘
              └────────────┬─────────────┘
                    ┌──────▼───────┐     ┌──────────────┐
                    │  Prometheus  │────▶│   Grafana    │◀── annotations
                    │   (9090)     │     │   (3001)     │        │
                    └──────────────┘     └──────────────┘   ┌────┴───────┐
                                                            │ AI Debugger│  LangChain
                                                            │  (Groq LLM)│  root-cause
                                                            └────────────┘  summaries
```

---

## Components

| Service | Language | Responsibility |
|---|---|---|
| **Ingress** | C++ · gRPC | Accepts `Submit` / `SubmitBatch` RPCs; serializes to protobuf; publishes to Kafka with `entity_id` as the partition key. Multi-threaded sync server (2–8 pollers). |
| **Processor** | Python | Consumes events, routes them through a 150-vnode consistent-hash ring, accumulates per-entity state, and replicates each shard to the next node. Heartbeat-driven failover promotes replicas on a 30s timeout. |
| **AI Debugger** | Python · LangChain | Tails Docker logs, detects error bursts, summarizes root causes via an LLM, and pushes annotations to Grafana. |
| **Observability** | Prometheus + Grafana | 12 metric families across ingress & processors; a 9-panel dashboard auto-provisioned as code. |

---

## Highlights

- **🔀 Consistent hashing** — 150 virtual nodes per physical node keep entity→shard mapping stable as the ring grows or shrinks, so re-sharding moves minimal state.
- **♻️ Hot-standby replication** — every write is mirrored to the next distinct node on the ring; a missed heartbeat auto-promotes the replica to primary.
- **⚡ Async, batched ingress** — librdkafka producer tuned with `linger.ms=5`, 10k-message batches, and LZ4 compression for throughput.
- **🧪 Test-driven** — 83 Python (pytest) tests plus a C++ GoogleTest suite, all written before implementation. Interfaces are mockable end-to-end.
- **🤖 AI observability** — LLM-generated root-cause summaries land as Grafana annotations, deduplicated by fingerprint so the same burst is never re-summarized.
- **📊 Metrics as code** — Prometheus targets and the Grafana dashboard are provisioned automatically on `make up`.

---

## Quick Start

**Prerequisites** — Docker & Docker Compose. *(Optional, for local C++ builds: CMake, gRPC, protobuf, and librdkafka dev packages.)*

```bash
# 1. Clone
git clone https://github.com/aravgarg28/Distributed-Event-Processing-System.git
cd Distributed-Event-Processing-System

# 2. Configure secrets (AI debugger)
cp .env.example infrastructure/.env
#   then edit infrastructure/.env → add GROQ_API_KEY and GRAFANA_API_TOKEN

# 3. Launch the full stack
make up
```

Then open:

| Service | URL |
|---|---|
| **Grafana** dashboard | http://localhost:3001 |
| **Prometheus** | http://localhost:9090 |
| **Ingress** gRPC | `localhost:50051` |

---

## Makefile Reference

| Command | Description |
|---|---|
| `make up` | Start all services (detached) |
| `make down` | Stop containers (volumes preserved) |
| `make clean` | Full reset — stop and delete all volumes |
| `make logs` | Tail logs — filter with `make logs SERVICE=kafka` |
| `make status` | Show container status |
| `make build` | Configure + build the C++ `ingress_server` binary locally |
| `make test` | Build with tests enabled and run the C++ suite via `ctest` |

Run the Python test suite directly:

```bash
pytest tests/
```

---

## Project Layout

```
.
├── src/
│   ├── ingress/        C++ gRPC receiver + Kafka producer
│   ├── processor/      Python consistent-hash workers + failover
│   └── ai_debugger/    LangChain log summarizer → Grafana annotations
├── infrastructure/     Docker Compose, Prometheus & Grafana provisioning
├── tests/              GoogleTest (C++) + pytest (Python)
└── docs/               PRD · Architecture · Tasks · Changelog
```

> 📚 Design details live in [`docs/`](docs/) — start with [`ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Tech Stack

**Core** C++17 · Python 3.11 · **Messaging** Apache Kafka (KRaft) · gRPC · Protobuf
**Infra** Docker · Docker Compose · **Observability** Prometheus · Grafana · LangChain

---

<div align="center">
<sub>Built by <a href="https://github.com/aravgarg28">Arav Garg</a></sub>
</div>
