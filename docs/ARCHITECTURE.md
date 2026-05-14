# System Architecture

## 1. High-Level Flow
1. **Event Source** -> Pushes events via gRPC to **Ingress Node**.
2. **Ingress Node (C++)** -> Batches events asynchronously and publishes to **Kafka Topics**.
3. **Processor Nodes (Python/C++)** -> Consume from Kafka. They use **Consistent Hashing** to ensure events for the same entity go to the same node state.
4. **Data Sink** -> Processed events are pushed to their final destination (mocked database or external API).

## 2. Component Details

### A. Ingress Service (C++)
- Exposes a gRPC server.
- Uses asynchronous I/O to avoid blocking on high traffic.
- Acts as a Kafka Producer.

### B. Message Queue (Kafka & Zookeeper/KRaft)
- Hosted in Docker for local dev (later AWS MSK or EC2 Kafka cluster).
- Topics partitioned to match the hashing strategy.

### C. Processor Workers (Python)
- Deployed as multiple Docker containers.
- Implements consistent hashing algorithm.
- Replicates state to a secondary node for failover.

### D. Observability & AI Debugger
- **Prometheus**: Scrapes metrics from Ingress and Processors (latency, throughput, error rates).
- **Grafana**: Visualizes Prometheus metrics.
- **AI Debugger (LangChain)**: A Python service that listens to the application log stream. When a crash or spike in error rate occurs, it feeds the stack trace and recent logs into an LLM via LangChain, generates a summary, and pushes a Grafana Annotation via the Grafana API.

## 3. Deployment Strategy
- Local Development: `docker-compose.yml` spinning up Kafka, Zookeeper, Prometheus, Grafana, and the app containers.
- Production (Simulated): AWS EC2 instances orchestrating Docker containers.
