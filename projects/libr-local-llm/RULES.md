# libr-local-llm rules

- PHI never leaves the cluster. Every model that reads PSYCH-ASR recordings or transcripts runs on LIBR hardware. No external API.
- Never read anything under phi/. The one exception, a model running on LIBR hardware, is ai-config/policy/LOCAL-MODELS.md.
- A serving endpoint is loopback only, reached with srun --jobid=<id> --overlap. Never rebind one to 0.0.0.0. Loopback does not stop the node's other users, so an engine that takes an API key is preferred.
- The clinical model never runs through opencode. It is driven from a plain Python client with no tool-calling surface.
- Do not widen the PHI guard until PSYCH-ASR's numbers-only summary writer exists and the owner has eyeballed its output once.
- A Colibri task is read-only analysis. It writes only under the subject's ignored phi/, and any tracked change fails it.
- opencode's top-level web deny is never relaxed. Only the coder agent is raised; web access is set per agent, never per model.
- No admin rights: everything installs under $HOME or the studies share.
- This repository is public: no PHI, data or credentials in a tracked file.
- c3_accel (compute306, the only 4-GPU node) is booked, never held: gpu:4 only for work that needs it, c3_short with gpu:1 otherwise. Fair-share lands on our own research jobs, so keep hard caps, short walltimes and idle release.
- No state file: ask Slurm. No quality-based auto-routing: a human or an agent names the big model.
- The check and every report carry only aggregate RELAY: lines.
- A blocked step is the answer: say what it waits on and stop.
