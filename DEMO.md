# 🎬 DEPS Live Demo Guide

This is the script for demoing DEPS in **under 3 minutes**. The narrative arc —
**scale → failure → self-healing → AI explanation** — is what makes it land.
Practice it once end-to-end before showing anyone live.

---

## The one-liner (say this first)

> *"This is a fault-tolerant event pipeline — the kind of backbone behind a
> real-time fraud-detection or analytics system. It processes a live stream
> across multiple workers, survives a worker dying without losing data, and
> uses an LLM to explain its own failures in plain English. Let me show you."*

---

## Before the demo (setup — do this off-camera)

```bash
# Fill in your keys once
cp .env.example infrastructure/.env
# edit infrastructure/.env → GROQ_API_KEY, GRAFANA_API_TOKEN

# Bring the whole stack up and let it warm up (~30-60s)
make up
make status        # confirm every container is "healthy"
```

Open two things in your browser, ready to switch between:
- **Grafana** → http://localhost:3001  (the DEPS Overview dashboard)
- A terminal, large font, ready to type

---

## The demo script (≈3 minutes, live)

### Beat 1 — "Here's the system running at scale" (30s)

Point at the Grafana dashboard. Narrate what's live:

> *"Two worker nodes are splitting a live event stream. Events come in over
> gRPC to a C++ ingress node, get buffered in Kafka, and each worker owns
> about half the entities — decided by a consistent-hashing ring."*

Point at the **"Store Entities per Node"** panel — two workers, roughly balanced.

### Beat 2 — "Watch what happens when a machine dies" (30s)

This is the hook. Kill a worker **live**, on camera:

```bash
docker kill deps-processor-1
```

> *"I've just hard-killed worker-1 — no graceful shutdown, like a real crash.
> In most systems, that entity's state is now gone or stuck."*

### Beat 3 — "It heals itself" (45s)

Switch to the dashboard. Within ~30 seconds:

- The **failover counter** ticks up
- worker-2's **"Store Entities"** gauge jumps as it absorbs worker-1's shards

> *"Worker-2 noticed the missed heartbeat, and because it was already keeping a
> hot copy of worker-1's state, it promoted that state to primary and took over.
> No data lost. No human touched anything."*

### Beat 4 — "And it explains its own failure" (45s)

Because processor-1 died, its error logs spiked. Switch to the dashboard timeline:

> *"Here's the part nobody else builds. The AI debugger saw the error burst,
> asked an LLM for the root cause, and pinned a plain-English explanation right
> onto the dashboard."*

Point at the **Grafana annotation** — an LLM-written summary like
*"processor-1 lost its Kafka connection and shut down; check broker health."*

> *"So instead of an engineer scrolling 10,000 log lines at 3am, the system
> hands them the root cause."*

### Close (10s)

```bash
make clean     # tear everything down
```

> *"Scale, failure, self-healing, and AI-assisted debugging — all in one
> pipeline. Everything's in the repo, fully test-driven."*

---

## Recording it as a GIF / video (highest-ROI asset)

A 60–90 second clip of the **failover + annotation moment** embedded at the top
of the README is worth more than any paragraph. How to make one:

### macOS (simplest)

1. **Record** with QuickTime: `⌘⇧5` → record a screen region covering the
   dashboard + terminal. Run Beats 2–4 above.
2. Keep it tight — **60-90 seconds max**. Trim dead air where you wait for
   failover (or speed that section up 2× in editing).
3. **Convert to GIF** (crisp, small file) with `ffmpeg`:

   ```bash
   # High-quality palette-based conversion
   ffmpeg -i demo.mov -vf "fps=12,scale=1000:-1:flags=lanczos,palettegen" palette.png
   ffmpeg -i demo.mov -i palette.png -vf "fps=12,scale=1000:-1:flags=lanczos,paletteuse" demo.gif
   ```

4. Keep the GIF **under ~10 MB** so it renders inline on GitHub. If it's larger,
   lower `fps` to 10 or `scale` to 800.

### Embedding it in the README

```markdown
![DEPS self-healing demo](docs/demo.gif)
```

Put the file at `docs/demo.gif` and drop that line near the top of `README.md`.

> 💡 **No live stack handy?** Use the animated walkthrough artifact (the
> self-healing visualization) as a stand-in — screen-record *that* instead. It
> shows the same narrative and never depends on a running cluster.

---

## Tips for a demo that doesn't flop

- **Rehearse the timing.** Failover takes ~30s; know that dead air is coming and
  fill it by narrating what the system is doing under the hood.
- **Pre-warm the stack.** Never run `make up` on camera — cold start is boring.
- **Big terminal font.** 18pt+. People at the back (or on a shared screen) need
  to read the `docker kill`.
- **Have a fallback.** If Groq is rate-limited and no annotation appears, say
  *"the annotation lands on the next poll cycle"* and show a previous one.
- **Know your caveats** (see the README) — engineers respect "this is a
  reference implementation, the architecture scales, the demo's on a laptop."
