# libr-local-llm — the research journey

A plain-language narrative of this repository: what it is for, what is built, what is designed but
not built, and where it now stands. Written for a reader who wants the story and the current state
without reading the configuration.

`README.md` documents the architecture and the bootstrap sequence. This file is its other half —
the narrative and the reasoning behind the choices. Both live here now; until 2026-09-13 the
narrative sat in a separate `Research-Journey` hub, which was retired so that each project's
writing, planning and documents live with the project they belong to.

This repository is **not a project**. It is shared infrastructure that two projects depend on, and
their journeys are `~/TRD-EHR/JOURNEY.md` and `~/PSYCH-ASR/JOURNEY.md`. The ordered task list is
`planning/LOCAL-LLM_TODO.txt`, and it is the answer to "what do we do next".

---

## Why it exists

PSYCH-ASR's on-prem constraint is absolute: session recordings and their transcripts are
identifiable PHI, so every model that reads them has to run on LIBR hardware. TRD-EHR has the same
need — the MedGemma work there already runs locally on vllm. Rather than duplicate that setup per
project, the serving stack lives here, in a repository of its own. A model server is not a stage in
either pipeline; it is the ground both stand on.

All three repositories are public (`github.com/Pirate-Hunter-Zoro/libr-local-llm`, and the same
account's `TRD-EHR` and `PSYCH-ASR`). For this one that is defensible because it holds serving
configuration only — no PHI, no data, no credentials — but it inverts the usual assumption in a way
worth stating plainly: everything committed here is world-readable the moment it is pushed, so
nothing sensitive can ever go in, not even temporarily.

**What it provides.** Ollama installed user-local (no admin rights anywhere in the process), served
on Slurm GPU nodes via two batch jobs — one single-A40 job on `c3` for day-to-day use, one 4-GPU job
on `c3_accel` for the largest model. Weights live on the studies share, not in the 100 GB home
quota. The endpoint binds to loopback on the job's node, deliberately: binding it to the node's
external address would expose a PHI-processing endpoint to every user on the cluster. Reaching it
therefore means getting onto that node, which is done by stepping into the running allocation with
`srun --overlap` rather than by SSH — SSH depends on a key agent that is not always present, while
`srun` needs nothing and inherits the job's GPU environment.

Three tracked commands wrap all of it (2026-08-20): one brings a server up and blocks until it is
genuinely serving, one launches opencode against it from anywhere including the login node, one
tears it down. The 4-GPU shard is verified as of the same date — `gpt-oss:120b` spread 16–18 GB
across all four A40s at 100% GPU, which also settles that the multi-GPU path needed for the vllm
work below is sound on this hardware.

**Two distinct roles, deliberately kept apart.**

- *Coding assistant.* `opencode` as the front end, talking to Ollama over its OpenAI-compatible
  endpoint. This is a convenience for writing pipeline code; it does not need to see PHI. Its
  provider list is locked to the local server by a default-deny allowlist, because opencode ships
  with several hosted "free" remote models one keystroke away in the model picker.
- *Clinical inference.* The transcript-reading work of PSYCH-ASR **Stage 3c** (behavioral and content
  coding; Stage 4 is feasibility modeling and involves no LLM — an earlier version of this section
  mis-numbered it). Ollama is the right tool for prototyping prompts against a quantized model, but
  the production passes belong on vllm: continuous batching for throughput across many transcripts,
  and guided decoding against a JSON schema so that a fidelity rating is structurally incapable of
  coming back as prose. The MedGemma safetensors are already staged for exactly that.

**The boundary that matters.** The coding assistant may have web tools; anything reading transcripts
must not. Nothing prevents a tool-enabled agent from dropping a fragment of a session into a search
query, and under PSYCH-ASR's own constraint that is an exfiltration event rather than a bug. Keeping
the two configurations separate is a standing requirement, not a nicety.

A decision taken 2026-08-20 sharpens rather than loosens this. The coding assistant *will* get web
access — `webfetch` raised to allow, `websearch` deliberately left at ask, since a URL you typed is
a narrower exposure than a query built from your prompt text. Two points came out of settling it.
The first is that opencode grants these permissions **per agent, not per model**, so the boundary
that matters is the workload rather than the weights; "let the models surf" is not a thing the
configuration can express, and reasoning that way is how the wrong agent acquires the wrong tool.
The second is that web access carries an *ingress* risk alongside the obvious egress one: fetched
pages arrive as text the model cannot distinguish from instructions, and the agent holding them has
file and shell access. That risk is live even with no PHI in the session.

That boundary is now enforced in three layers, two of which exist (2026-08-17). First, opencode's
`permission` block denies `webfetch` and `websearch` globally — necessary because opencode's built-in
default for nearly every gated tool is *allow*, so an unconfigured install had working web tools
rather than absent ones. Second, a single `coder` agent raises those two back to `ask`, so the one
profile that can reach the network cannot do so without a human seeing the request; every other
agent, including opencode's built-in `explore` subagent (which ships with web access enabled),
inherits the deny. Both layers are configuration, and configuration is one bad edit from being wrong.
The third layer is the one that cannot be misconfigured and is **not yet built**: the clinical model
never runs through opencode at all, but through a plain Python client with no tool-calling surface in
the code. In practice that client is the vllm driver described above — the no-tools property falls
out of reusing TRD-EHR's serving pattern rather than being separate work.

## Where it goes next — the fleet (designed 2026-08-22, nothing built)

The setup described above serves one model at a time on one node, which is the right shape for a
single person prototyping prompts and the wrong shape for almost everything else the two projects
need. The next phase is a deliberate step up in ambition: **one service, three engines, spread across
the cluster's GPUs, that gives resources back when other researchers need them.** The design is
written down in `libr-local-llm/DESIGN.md` before any of it is coded, so the arguments survive
contact with the implementation.

Three engines, because they are good at genuinely different things and none of them is a superset of
the others. **Ollama** is unbeatable for one person switching models on a whim. **vllm** is the
industrial answer for throughput — many requests at once, and structured output that a schema makes
structurally incapable of coming back as prose, which is exactly what PSYCH-ASR's Stage 3c fidelity
ratings need. **Colibrì** is the strange and interesting one: an inference engine that treats VRAM,
RAM, and disk as a single hierarchy and streams the experts of a Mixture-of-Experts model on demand,
which lets a **744-billion-parameter** model run on hardware that cannot begin to hold it. Our nodes
turn out to be unusually well suited to it — a terabyte of RAM each, and AVX-512 with VNNI on 48
physical cores — and the honest projection is high single digits of tokens per second, which is slow
to read but perfectly usable for a hard question asked once.

The point of the third engine is not cost and not novelty. It is that **a frontier-scale model can
read PHI**, which no hosted service will ever be permitted to do here. That is the capability that
justifies the project. The counterweight, recorded in the design rather than discovered later, is
that the 744B model runs at 4-bit precision and 4-bit costs measurable accuracy on exactly the
hardest questions — so "bigger" and "better for our tasks" are two different claims, and the second
one is a measurement we owe ourselves before anything gets promoted.

What makes this a real engineering project rather than three installations is the part about other
people. The hardware is already bought and already powered, so the marginal cost of running a model
on it is not money — it is **queue time that belongs to other researchers**, plus our own
fair-share, which our *own* pipeline jobs then pay for in worse scheduling. Without admin rights
there is no preemption to configure and no priority tier to sit under, so every yield has to be
voluntary: a supervisor watches the pending queue, and when it sees somebody else's job blocked on
resources we are holding, it drains that backend, gives the node back, and refuses to re-request it
until the job it was trying to help has actually started. That last clause is the whole trick — the
obvious version of this loop releases a node and then immediately wins the race to reclaim it, which
manages to look maximally antisocial while running code written to be polite.

Two structural decisions fell out of the design and are worth recording here because both are
counter-intuitive. First, **the giant model belongs on a single-GPU node**, not on the cluster's only
four-GPU machine: the part of that engine which genuinely wants a GPU fits in 23 GB, and the part
that wants capacity wants *RAM*, which every node has a terabyte of. Giving up something like 40% of
the slowest engine's throughput to leave the scarcest node alone is a trade worth making. Second,
**the batch path should not be a network service at all** — a queue of files on the studies share,
claimed by workers with an atomic rename, is preemption-tolerant for free, inspectable with `ls`, and
enforces the PHI boundary by there being no socket to misconfigure. It also delivers the third and
final PHI layer as a property of the architecture instead of as a discipline somebody has to
maintain.

The design is staged so that each milestone is worth having on its own, and the first one that
matters is not the exciting one: get vllm running, then the batch queue, and Stage 3c is unblocked
before a single line of the fleet supervisor exists.

Architecture, bootstrap instructions, environment variables, and a list of the traps already paid
for are in `libr-local-llm/README.md`; the fleet design is `libr-local-llm/DESIGN.md`; remaining work
is in `planning/LOCAL-LLM_TODO.txt`.

---

## Current state at a glance

| | `libr-local-llm` — infrastructure |
| --- | --- |
| **Core question** | Can every model that reads PHI run on LIBR hardware, with no path off the cluster — and can we do it at industrial throughput without taking the cluster away from anyone else? |
| **Pipeline** | Ollama serving live on Slurm GPU nodes (1×A40 on `c3`, 4×A40 on `c3_accel`), loopback-only and reached via `srun --overlap`, weights on the studies share; opencode wired as the coding front end and driven by three tracked commands (2026-08-20). 4-GPU shard verified (2026-08-20). 2 of 3 PHI-boundary layers enforced (2026-08-17); the vllm path for Stage 3c is not started. **The fleet** — one front door over three engines (ollama, vllm, colibrì) with a supervisor that yields nodes to other users' blocked jobs — is designed as of 2026-08-22 in `libr-local-llm/DESIGN.md` and **none of it is built**; six milestones, each with an exit criterion, and seven measurements owed before anything is claimed |
| **Headline result** | N/A — infrastructure, not a study: no manuscript, no results, no data of its own. Success is that nothing identifiable ever leaves LIBR hardware |
| **Manuscript** | N/A — architecture and bootstrap in `libr-local-llm/README.md`; remaining work in `planning/LOCAL-LLM_TODO.txt` |
| **Immediate next step** | Web access for the coding agent — decided 2026-08-20, config edit not yet applied: `webfetch` to allow, `websearch` stays at ask, top-level deny untouched so the built-in `explore` subagent stays closed. Then, with the fleet design now settled (2026-08-22), the order changes: **install vllm** as one single-GPU replica (milestone M0), then the filesystem work queue that drives it (M1) — which unblocks PSYCH-ASR Stage 3c *and* delivers PHI-boundary layer 3 as a property of the architecture, since a queue of files on the studies share has no socket and therefore no tool-calling surface to misconfigure. The fleet supervisor, the colibrì placement measurement, and the router all come after that, and none of them are prerequisites for Stage 3c |

The dependent projects' columns of this table live in their own journeys:
`~/TRD-EHR/JOURNEY.md` and `~/PSYCH-ASR/JOURNEY.md`.
