# Project: Distributed Event Processing System (DEPS)

## Project Overview
DEPS is a high-throughput, multi-node event pipeline designed to process 1M+ real-time events/hour with high availability, utilizing consistent hashing and Kafka for resilience. It features a LangChain-powered observability plane to reduce developer debugging time.

## Tech Stack
- **Core Processing**: C++ (High-throughput ingress/egress), Python (Data processing/AI)
- **Messaging & RPC**: Kafka, gRPC
- **Infrastructure**: AWS EC2, Docker
- **Observability**: Prometheus, Grafana
- **AI/LLM**: LangChain (Log summarization)

## Operating Directives for Claude Code
1. **Single Source of Truth**: Always refer to the `docs/` folder before writing code.
2. **Read Before Coding**: Before starting a task, read `docs/ARCHITECTURE.md` and `docs/TASKS.md` to understand context.
3. **Test-Driven Development**: Write tests *before* implementing the logic. Focus on behavior, not implementation details.
4. **Atomic Commits**: Make small, incremental changes and commit frequently. Do not refactor unrelated files.
5. **Update State**: After completing a task in `docs/TASKS.md`, update the status and immediately write an entry into `docs/CHANGELOG.md`. This allows future Claude sessions to know what was done.
6. **No Assumptions**: If a requirement is ambiguous, STOP and ask the user for clarification.

## Repository Structure
- `/src/ingress/` - C++ gRPC receiver
- `/src/processor/` - Python/C++ workers
- `/src/ai_debugger/` - Python LangChain log summarizer
- `/infrastructure/` - Docker Compose, AWS provisioning scripts
- `/docs/` - System documentation (PRD, Architecture, Tasks)
