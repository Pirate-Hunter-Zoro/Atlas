# libr-local-llm

## Where things are

- Shared inference on LIBR compute for PSYCH-ASR (Stage 3c, PHI) and TRD-EHR. Infrastructure, not research: no manuscript, results or data.
- ollama, user-local: qwen3-coder:30b, medgemma:27b-it-q8_0, gpt-oss:120b (needs c3_accel). slurm_jobs/ollama_serve*.sbatch; bin/ollama-up, ollama-code, ollama-down. opencode is the front end; config/opencode.json is a tracked copy of ~/.config/opencode/opencode.json.
- colibri, GLM-5.2 int4: slurm_jobs/colibri_serve.sbatch and bin/coli-build, coli-up, coli-code, coli-ask, coli-down. README §4c is its architecture; P0-STATUS.md findings 16-22 its measurements, and finding 20 governs the design.
- The fleet is designed in DESIGN.md and scheduled in FLEET-BUILD.md. None of it is built.
- The retired plan is planning/LOCAL-LLM_TODO.txt in git history.

## Now

Nothing here waits on another person, so work comes here while TRD-EHR and PSYCH-ASR are stalled.

- [ ] Raise coder's webfetch from ask to allow, leave websearch at ask and the top-level deny alone. Mirror it into the live config; opencode agent list must show every other agent still at deny.
- [ ] Build the vllm path for PSYCH-ASR Stage 3c, fleet milestone M0/M1: scrub SLURM_* before any srun or sbatch, and expect a multi-minute cold load. It is the clinical client: plain Python, no tool-calling surface. M0 exits on a schema-guided response with the fallback diagnostics read; M1 on a queue pass that loses nothing when a worker is killed.
- [ ] With it: the fidelity-rating JSON schema, operational items split from subjective scales, and a validation plan (human-human ICC, then model against humans).
- [ ] After PSYCH-ASR's numbers-only summary writer exists and the owner has eyeballed its output once: teach ai-config/policy/phi.py the *.summary.json shape and say so in PERMISSIONS.md §2. Never before.
- [ ] Decide whether a longer-lived ollama server is wanted on c3; both sbatch files default to 8 h.
- [ ] Learn, for the Colibri PHI-safety deck: why coli-code's session root ends in a directory named phi; the three layers of the PHI boundary, and why the clinical model never runs through opencode; what names_phi checks before a push or a save, and what only a hosted turn's judgement can catch.
- [ ] Learn: the cluster's partitions and nodes, the A40s, the 1 TB node, and why inactive NVLink favours replicas over shards; the measured rates, 51 tok/s per user on one A40 for the 30B helper against 3.2-4.4 tok/s for the 744B model.
- [ ] Build the deck once the owner has had those learn sittings.

After M1: M2 colibri placement, M3 the supervisor, M4 the front door, M5 the consultant tool, each only once the last exit is met. Measurements owed first: atomic rename on the NFS share, replicas against a 4-way shard, whether a yield helps the other job, 744B int4 against a well-served 27-120B model scored blind, reacquisitions that beat a yielded job (must be zero), and our fair-share factor.

Colibri on demand: `board colibri` or a relay request files a task; a generation starts, works the queue and exits 20 minutes after it empties. A turn runs inside the serve job's 9 h allocation, and a dead generation's clone resumes the task; three deaths fail it. The first task pays a 68-minute load and two to three hours of prefill, so file related asks together, and write asks that land work on disk as it goes.

## Open decisions

- How many KV slots colibri serves. Finding 22 says one: a second costs 23.9 GB at a 131072 window, ends speculation, and is slower per session. Confirm and close.
- Whether MTP is forced off. Finding 21 measured 3.23 tok/s drafting against 3.58 without (job 2073575), and the served config leaves it off. Confirm and close.
- Interactive serving across nodes (blocks M4 only). DESIGN.md §5.4 recommends single-node for anything touching PHI. Not decided, and never by a config edit.
- MedGemma or a general 30B instruct model for Stage 3c: decide by measured agreement.

## Done recently

- The colibri harness: five commands, on-demand generations that resume across deaths, reachable from the iPad. The job it was built for, the diarization repair, is done: PSYCH-ASR's reference transcript exists and the annotator approved it.
