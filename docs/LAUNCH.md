# 📣 Launch Copy

Ready-to-post copy for showing DEPS off. Swap in your own links and voice.

---

## LinkedIn post (short, punchy)

> I built a distributed event pipeline that **debugs itself with an LLM.** 🧠⚡
>
> Most backends that handle real-time events at scale share three hard problems:
> they can't drop data, they can't fall over, and when something *does* break,
> an engineer burns hours reading logs to find out why.
>
> So I built **DEPS** — a fault-tolerant pipeline designed for 1M+ events/hour:
>
> 🔀 A C++ gRPC ingress node accepts the firehose and buffers it in Kafka
> ♻️ Python workers shard state by entity using consistent hashing — and each
>    one keeps a *hot copy* of its neighbour's data
> 🚑 Kill a worker mid-stream and its replica auto-promotes in ~30s. Zero data
>    loss, zero human intervention.
> 🤖 And the part I'm most excited about: when errors spike, a LangChain service
>    asks an LLM for the root cause and pins a plain-English explanation right
>    onto the Grafana dashboard.
>
> Instead of scrolling 10,000 log lines at 3am, you see:
> *"processor-1 lost its Kafka connection — check broker health first."*
>
> Built test-first (80+ tests), fully containerized, one `make up` to run it.
>
> 🔗 Code + architecture: [your repo link]
>
> #DistributedSystems #Kafka #CPlusPlus #Python #SRE #Observability #LLM

---

## Blog post intro (long-form opener)

### How I Built a Self-Healing Event Pipeline That Debugs Itself With an LLM

Every real-time system eventually hits the same wall. Events arrive faster than
any single machine can handle. You spread the work across many machines — and
now you've traded a throughput problem for a much harder one: **what happens
when one of those machines dies at 3am, mid-stream, with state in memory?**

That question is the whole game in distributed systems. Get it wrong and you
lose data, corrupt state, or page a human. Get it right and the system quietly
heals itself while everyone sleeps.

I wanted to build the machinery that gets it right — end to end — and then add
something I hadn't seen done well: **an observability layer that doesn't just
show you a red graph, but tells you, in plain English, why it went red.**

The result is **DEPS** (Distributed Event Processing System). It's built to
handle a million-plus events an hour across a ring of workers, survive a node
failure with no data loss, and use a language model to summarize the root cause
of failures directly onto the monitoring dashboard.

Here's how each piece works, and the engineering decisions behind them.

*[→ continue with: the C++ ingress and why C++; Kafka as the shock absorber;
consistent hashing and the 150-virtual-node trick; hot-standby replication and
heartbeat failover; and the LangChain AI debugger.]*

---

## Elevator pitch (30 seconds, spoken)

> "DEPS is a fault-tolerant event-processing pipeline — think of the backbone
> behind a fraud-detection or real-time-analytics system. It handles a huge
> stream of events, spreads them across multiple workers by consistent hashing,
> and if a worker dies, a replica takes over automatically with no data loss.
> The twist is the observability layer: when something breaks, an LLM reads the
> logs and writes the root cause straight onto the dashboard. So it doesn't just
> scale and survive — it explains itself."

---

## Where to post

| Channel | Angle |
|---|---|
| **LinkedIn** | The self-healing + AI hook. Lead with the outcome, not the stack. |
| **GitHub README** | The demo GIF up top; let the architecture speak. |
| **Dev.to / Hashnode** | The long-form blog — deep-dive one subsystem (consistent hashing or failover) with diagrams. |
| **Portfolio site** | One-line pitch + the demo GIF + "read the architecture." |
| **Interviews** | Your answer to *"tell me about a system that handles scale and failure."* |
