# HANDOFF — the Mac hosts, the cluster computes

**The board, the tutor and every writing turn run on the owner's Mac mini at home. The cluster
keeps only what must stay at the institute: the data, the GPUs and Slurm.** The two never talk
directly. They talk through the repository: the Mac commits a *request*, the cluster pulls it
on a timer, does the work, and commits a *report*. GitHub is the only channel, over the same
outbound HTTPS git already uses. Nothing tunnels into the cluster, and nothing here works
around the institute's network controls.

`board/README.md` is the architecture. `board/SETTLED.md` holds the rules already built.
This file says what is left to build.

---

## The split

| | Mac mini (home) | Cluster (institute) |
|---|---|---|
| Runs | the board, tutor turns, compiles, decks, meetings | Slurm jobs, the relay, cluster turns |
| Holds | the whole repository, no PHI, no `results/` | the repository, `results/`, PSYCH-ASR `phi/`, EHR extracts, models |
| Providers | any, including DeepSeek | Claude with the PHI guard, and Colibri on demand |
| Writes to git | everything except `relay/reports/`, `exports/` and a held thread's files | `relay/reports/`, `exports/`, and the files of a thread held at the cluster |
| iPad reaches it | over the owner's own tailnet | never |

**Path ownership is what makes two writers on one branch safe.** The Mac never writes a
report or an export. The cluster writes nothing else, except the files of a thread whose
sitting is held at the cluster (`board hold`). While the hold lasts, those files are the cluster's
and the Mac refuses to write them. So a pull on either side fast-forwards or rebases without a
conflict.

**The Mac holds no PHI by construction.** Every provider is therefore allowed there, and a
PHI rule on the Mac is a rule about what the cluster may export.

### By workspace

- **Courses and practice:** all on the Mac. Nothing goes to the cluster.
- **research/TRD-EHR:** writing, figures from exports, code and tests on `test_data/` on the
  Mac. Sweeps, model fits and anything reading `results/` or the EHR run on the cluster as
  requests.
- **research/PSYCH-ASR:** code on the Mac. Every run on the cluster. The owner listens to the
  recordings at the institute, never through the relay.
- **projects/libr-local-llm:** the deck and the learning sittings on the Mac. Colibri runs on
  the cluster only while it has a task (Colibri on demand, in `board/README.md`). `vendor/colibri` moves forward on the cluster's
  relay pass.
- **projects/Paper-Writer:** all on the Mac.

---

## The relay

A workspace that uses the cluster keeps two tracked directories at its root, outside `live/`
for the reason `threads.json` sits there:

- `relay/requests/<id>.json` — written by the Mac. One file per request, never edited after
  the commit that adds it.
- `relay/reports/<id>.json` — written by the cluster. Rewritten as the job moves:
  `refused`, `submitted`, `running`, `completed` or `failed`.

One file per request means two machines never append to the same file.

A request has one of two kinds.

**`recipe`** runs a tracked `.sbatch` file in the workspace, with no judgement needed.

```json
{"id": "2026-10-03-knn-bge-small", "kind": "recipe", "thread": "knn-across-embedders",
 "recipe": "slurm_jobs/quick_runs/neighbor_count_sweep.sbatch",
 "env": {"EMBEDDER": "bge-small-en-v1.5"},
 "produces": ["results/bge-small-en-v1.5/google_medgemma-27b-text-it/neighbor_count_sweep/best_k_panels.json"],
 "export": ["results/cross_embedder_retrieval/cross_embedder_sweep.png"]}
```

- The recipe must be tracked at the commit the relay pulled. Its header declares the
  variables it accepts, one comment line per variable naming a pattern its value must match.
  Anything undeclared is refused, and the report says which key.
- The relay never runs a shell string from a request. It runs `sbatch` with the recipe path and
  `--export` built from the declared variables, through `jobs.submit`.

**`turn`** wakes a headless Claude turn on the cluster, in that workspace, under the PHI guard.
It is for work that needs judgement next to the data: diagnosing a failed job, choosing a rerun
or reading an output too large to export.

```json
{"id": "2026-10-03-why-l1-dense", "kind": "turn", "thread": "knn-across-embedders",
 "brief": "bge-small kept 384/384 dimensions. Read dimension_importance.json and say whether L1 took effect."}
```

- Off by default. A workspace opts in with `relay.turns: true` in its `tutorboard.json`,
  because it is an unattended agent beside the data.
- The turn ends on a report, like a board turn. Its prose goes in the report's `note`, written
  for a public repository: aggregate numbers only, no patient-level values, no identifiers.

**A report is public.** It carries state, Slurm job id, times, exit code, which `produces` paths
now exist, which exports landed, and a `note`. It never carries a raw log tail, because a log
can print anything. It carries only lines the job printed behind a `RELAY:` prefix, plus the
exception type of a crash. The full log stays on the cluster. A `turn` request reads it there.

**An export is a copy of an aggregate artifact into tracked `exports/`**, at the same relative
path it has under `results/`. Only a path the thread file marks exportable goes there. Paths in
a request's `export` list are checked against that mark. The extension must be png, pdf, svg,
csv or json, and each file is at most 5 MB. Whether a csv or json is aggregate is the owner's
call, made once per path on the thread. The Mac's paper builder reads `exports/results/…`
where `results/…` is absent, so a manuscript names one path on both machines.

---

## Rules that bind every item

- **The PHI rules in the root `README.md` bind everything here, and the repository is
  public.** A request, a report, an export and a commit message are all published. Raw data,
  patient-level rows, `results/` wholesale, log tails, participant ids and lab storage paths
  never cross. `board/test/tracked.py` stays green on both machines. It needs the private
  `ai-config/`, which a fresh worktree lacks; `tracked` and `colibri` fail there for that
  reason alone.
- **No tunnels, no reverse shells, no port forwards into the cluster, no exit nodes.** The
  cluster makes outbound git calls to GitHub and nothing else. If GitHub is unreachable from a
  compute node, stop and tell the owner in one line. Do not route around it.
- Provider keys live in `~/.config/tutor-board/keys.env` on each machine and are never
  committed. On the Mac it is written from `~/.config/api-keys/`. If an item needs a key that file lacks, say so in one line naming the path.
- `bash board/test/all.sh` is green before and after. Bump `VERSION` in `board/web/sw.js` if a
  shell file changed. Ship `board/` with `bash board/scripts/ship.sh`. Ship everything else
  with `bash board/scripts/save-and-push.sh "msg" -- <paths>`.
- `projects/libr-local-llm/HANDOFF.md` is that project's own handoff and stays live.

## Start here — which machine does what

**A session told to work from this file finds its machine and does that machine's items, in
the order below, without being told which.** It is on the Mac if `uname` says Darwin, and on the
cluster if `sbatch` exists.

| Item | Runs on | When |
|---|---|---|
| 9. One environment per workspace: TRD-EHR's switch to the lockfile | cluster | now |

The Mac already runs the board: `board/README.md` §6 of the setup, "The Mac mini, which is the
host".

- On the Mac, nothing is left: providers on the Mac landed (`board/README.md`, "Which one, for
  this course, on this machine"), so a session there turns to "The work it is for".
- On the cluster, a session does 9's TRD-EHR part. The relay, holds, the Mac's hearing and
  Colibri on demand are built, and no compute node serves a board: `board/README.md` has their
  rules.
- A session that finds its machine's items all gone says so, then turns to "The work it is
  for".
- Ultracode, where the owner asks for it, means parallel agents across that machine's
  independent items.

## How to work from this file

1. Each item says what it depends on. Items with no dependency between them can go to parallel
   agents. Give each agent its own worktree and one item.
2. Each item ends with a **Prompt**, which is the instruction to give that agent verbatim. Read
   the whole item first. Extend the existing code it names. A second mechanism beside an
   existing one is how this repository ends up with two of everything.
3. When an item lands, delete it from this file. Write its rule into `board/README.md` in the
   present tense. Numbers stay as they are: the owner and other sessions follow them.
4. If part of an item proves wrong once the code is in front of you, leave that part here with
   one line saying why. Do not drop it quietly.

---

## What to build

### 9. One environment per workspace: what is left — no dependency

The rest of it landed: `board/README.md` §6 of the setup, "Each workspace's code has one
environment". One part is left, on the cluster.

- **TRD-EHR's cluster switch from conda to the lockfile** (cluster). The conda environment on
  lab storage stays until the lockfile reproduces it. The cluster builds `uv.lock` into lab
  storage through `UV_PROJECT_ENVIRONMENT` with `uv sync --locked --extra test --extra cluster`,
  `setup_envs.sh` is rewritten to call that, one real sweep runs on the new environment, and only
  then is the conda one removed. `causal_forest_env` folds in too: the `pyproject.toml` carries
  econml 0.17.0, which accepts the pipeline's scikit-learn 1.7.1, where that environment held
  0.16.0 on 1.6.1, so one causal run on the new environment is part of the confirmation. Until
  then the root `scripts/setup.sh` on the cluster syncs the `cluster` extra into each
  workspace's `.venv/` in the home directory; the switch decides how that and
  `UV_PROJECT_ENVIRONMENT` meet. It was to be filed from the Mac with `board ask-cluster` and
  was not: TRD-EHR has not opted in to relay turns (`relay.turns: true` in its
  `tutorboard.json`), which puts an unattended agent beside the EHR and is the owner's to say.
  Once it has, the Mac files it; until then a cluster session working from this file does it.

Parts of the item as written that proved wrong, one line each:

- **PSYCH-ASR has three environments, not one**: `diarizen_env` (torch 2.1.1) and `nemo_env`
  (NeMo's own torch) each conflict with `asr_env`'s torch 2.8.0, so `diarizen` and `nemo` are in
  no extra and stay conda prefixes for the Slurm jobs that import them.
- **elan is not in the `Brewfile`**: Lean-Theorem-Proving's `scripts/setup.sh` installs it into
  `~/.elan` on both machines, and a Homebrew copy would shadow that one on the Mac's PATH.
- **Not every `pyproject.toml` has all three extras**: Paper-Writer's tests are `unittest`, so it
  has no `test` extra and nothing GPU, so no `cluster`; libr-local-llm has no tests, so only
  `cluster`. An empty extra would say a dependency exists where none does.
- **practice/Algo-Solutions' check fails on the code**: `go test ./...` stops at
  `leetcode/totalbeauty/totalbeauty.go`, which imports `algo-solutions/helpermath` and
  `algo-solutions/leetcode` without using them. The item reports such a failure and does not
  fix it; it is the owner's solution to finish.

> **Prompt:** Do item 9 of `HANDOFF.md`, on the cluster. Build
> TRD-EHR's `uv.lock` into lab storage through `UV_PROJECT_ENVIRONMENT` with the `test` and
> `cluster` extras, rewrite `setup_envs.sh` to call that, run one real sweep and one causal run
> on it, compare against the conda environment's last results, and only then remove both conda
> environments. Ship with the repository's scripts.

### Left as they are

- `board/AI_INSTRUCTIONS.md` carries no `board job` rule. It is the contract for developing the
  tool, not one a turn's brief reads; the workspace contracts carry it.
- A course shares only the map frame with a project. A chapter sitting already knows its
  chapter, so a thread file built from `chapters.tsv` would duplicate it without changing what
  is shown.

---

## The owner's, not a build

- **Confirm the thread files.** TRD-EHR, PSYCH-ASR and libr-local-llm carry drafted
  `threads.json` files, clean under `board thread --check`. One round of corrections per
  workspace, applied with `board thread`. `PSYCH-ASR_TODO.txt` and `LOCAL-LLM_TODO.txt` still
  exist. Their next steps are thread tasks; the owner decides where the rest goes before either
  is deleted.
- **Mark exports.** For each Paper 1 thread, say which `results/` artifacts are aggregate and may
  be published to `exports/`. The Mac cannot show a figure from the cluster until this is done.

## The work it is for

In this order. Each is a thread, and its open tasks are on its box.

1. **Paper 1** (`research/TRD-EHR`, deliverable `paper1`). The writing happens on the Mac.
   Anything that reruns a model goes to the cluster as a request.
   - `knn-across-embedders`: the section, Figure 5 and the cross-encoder figures are written.
     Open: discuss the dimension-count vs best-k scatter (it stays out of the write-up until
     then), fix the last *importance-weighted* in `plot_neighbor_sweep_figure.py`'s docstring,
     re-split `parts/`, and a learn sitting on the shape of the k-sweep.
   - `reviewer-findings`: the round-1 pairs on the manuscript, judged fine or not fixed; Martin's
     open questions; the TRIPOD+AI rows.
   - `consistency-pass`, blocked by `reviewer-findings`: clarity pass, cross-document numbers,
     refs 10 and 12 at proof, and a strict packet rebuild.
2. **The Colibri deck.** Learn sittings on `phi-path` and `libr-hardware` first, so the owner can
   defend every slide. Then build `phi-deck`.
3. **PSYCH-ASR `grid-sweep`**, as cluster requests, and the owner's `recording-review` at the
   institute.
4. **Paper 2.** Learn sittings on `estimand-identification`, then coach sittings on the four
   robustness rungs. The owner writes that code on the Mac against `test_data/`, or on the
   cluster under `board hold` when it needs real rows. Then build.

## On the glass

Built and never used for real. Strike each one after an evening on the iPad.

- The thread map: frames, coloured boxes, chips, and a tap opening a sheet that asks learn,
  coach or build.
- Pinch-zoom on a paper and a deck. Safari's own page zoom never starts, ink stays on its
  words, and one finger scrolls a zoomed page sideways.
- The round as pairs on the TRD-EHR manuscript: round 1 is the 09-29 round. Tap the chip, a row
  and a pip, and mark pairs fine or not fixed.
- A `[job]` card waking a turn when a cluster report lands.
- A `working` card that ends on a report, and a `stopped without a report` card.
- One document all the way round: ask, compile, read, ink, complain, revise.
- The meeting deck written by a real turn.
- Sending selected annotations.
- A response typing out, and the typed half of the answer panel, in a real sitting.
- Whether the verdict band and streak chip feel like information or like a scoreboard.
