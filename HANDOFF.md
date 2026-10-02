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
sitting is held at the cluster (item 5). While the hold lasts, those files are the cluster's
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
  the cluster only while it has a task (item 6). `vendor/colibri` moves forward on the cluster's
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
  committed. On the Mac it is written from `~/.config/api-keys/` (item 1). If an item needs a key that file lacks, say so in one line naming the path.
- `bash board/test/all.sh` is green before and after. Bump `VERSION` in `board/web/sw.js` if a
  shell file changed. Ship `board/` with `bash board/scripts/ship.sh`. Ship everything else
  with `bash board/scripts/save-and-push.sh "msg" -- <paths>`.
- `projects/libr-local-llm/HANDOFF.md` is that project's own handoff and stays live.

## How to work from this file

1. Each item says what it depends on. Items with no dependency between them can go to parallel
   agents. Give each agent its own worktree and one item.
2. Each item ends with a **Prompt**, which is the instruction to give that agent verbatim. Read
   the whole item first. Extend the existing code it names. A second mechanism beside an
   existing one is how this repository ends up with two of everything.
3. When an item lands, delete it from this file. Write its rule into `board/README.md` in the
   present tense. Renumber what is left.
4. If part of an item proves wrong once the code is in front of you, leave that part here with
   one line saying why. Do not drop it quietly.

---

## What to build

### 1. The Mac mini runs the board — depends on nothing

**The owner's part:** Claude Code and Codex installed, and this repository cloned:

```bash
git clone --recurse-submodules https://github.com/Pirate-Hunter-Zoro/Atlas.git ~/Developer/Atlas
cd ~/Developer/Atlas && claude
```

Then: *"Do HANDOFF item 1."* Tailscale and Homebrew are already on the Mac. Claude Code and
Codex sign in to the owner's enterprise plan and need no API key. DeepSeek is the only provider
that needs one, and it is in `~/.config/api-keys/deepseek_key`.

**The agent's part, in order.** Where a step needs `sudo` or an interactive login, give the owner
the one command to type with the `!` prefix and wait for it. Never ask for a password in chat.

1. **Power.** Read `pmset -g` and `pmset -g custom`. The Mac must not sleep, must not spin down
   its disk, must wake on network access, and must start after a power failure: `sleep 0`,
   `disksleep 0`, `womp 1`, `autorestart 1` on AC power. Display sleep is fine. Set whatever
   differs with one `sudo pmset` command for the owner, then read it back and confirm each value.
2. **Tailscale.** Confirm the system Tailscale is up on the tailnet the iPad is on, and record
   this Mac's tailnet name and address. If it is logged out, give the owner the login command.
3. **GitHub.** Confirm `gh auth status`. If it fails, `brew install gh` and give the owner
   `gh auth login`. Clone the private `ai-config` into `~/Developer/Atlas/ai-config` and run its
   installer, as the root `README.md` says.
4. **Keys.** Write `~/.config/tutor-board/keys.env`, mode 600, from the files in
   `~/.config/api-keys/`. Name each variable the way `board/tutorboard/keys.py` and the recipes
   that use them expect (`deepseek_key` becomes `DEEPSEEK_API_KEY`). Never print a value, never
   put one on a command line, and never commit one. Claude and Codex recipes use their
   enterprise logins, so they need no key here. Name any other key a recipe needs that has no
   file, in one line.
5. **Codex.** The owner installs Codex and signs in to the enterprise plan. Register it as an
   agent recipe the way `board/tutorboard/assistants.py` registers the others, using that
   login, so it can be chosen per sitting.

> **Prompt:** Do item 1 of `HANDOFF.md` on this Mac mini, so it replaces the compute node as the
> board's host. Do the five steps above first, in order. Then read the root `README.md`,
> "The split", and `board/README.md` on install, serving, autostart and networking. Install
> what the board and the paper builders need on macOS with Homebrew, and nothing else. Find
> that list by reading the code, not by guessing: python3 at the version the README states, a
> TeX distribution with latexmk, poppler for pdftotext, and node for the test suite's headless
> browser. Run `bash board/install.sh`, then `bash board/test/all.sh`. Where a suite fails only
> because it assumes Linux or Slurm, make the code notice the platform, the way the README says
> the Slurm parts already do. Do not skip the suite. Add launchd autostart beside
> `board/scripts/systemd/` (the tutor-pull service and timer), so a reboot brings every board
> and the periodic pull back with nobody logged in. Serve on the tailnet with the Mac's system
> Tailscale. `board/tutorboard/net/tailscale.py`'s userspace updater does not apply here; make
> it stand down on a machine whose Tailscale it did not install. The clone is at
> `~/Developer/Atlas`, not `~/Atlas`: find every place that assumes `$HOME/Atlas`
> (`ai-config/scripts/audit.sh`'s `REPO_ROOTS` is one) and derive the path from the file's own
> location instead. Finish by opening the atlas and TRD-EHR from the iPad's point of view (the
> tailnet address), and report both URLs, the power settings as read back, and the test result.
> Ship with the repository's scripts. Then do item 7.

### 2. A request and a report — depends on nothing

Extend `board/tutorboard/jobs.py`. Do not add a second registry beside it.

- `board job <thread> [--produces …] [--export …] -- <recipe> [VAR=value …]` submits directly
  on a machine with Slurm. On a machine without Slurm, it writes `relay/requests/<id>.json`,
  commits and pushes it with the workspace-scoped save. `board ask-cluster <thread> "<brief>"`
  files a `turn` request the same way.
- `jobs.registry` merges three sources into one view: the existing `live/jobs.jsonl`, requests,
  and reports. A request with no report yet reads `requested`. The thread status table gains
  that state between `running` and `written`, and a box says "waiting for the cluster".
- Validation is a pure function, beside `threads.validate`, shared by both machines: recipe
  tracked and in the workspace, variables declared with a matching value, export paths marked
  on the thread, ids unique. The Mac refuses a bad request before committing it. The cluster
  refuses it again before running it.
- `threads.json` threads gain an optional `exports` list of paths, each with `aggregate: true`
  once the owner has said so. `board thread export <thread> <path>` asks for it on a card.
- Every assistant contract says: **long work goes through `board job`.** On the Mac that means
  a request, and a bare `sbatch` there is an error.

> **Prompt:** Build item 2 of `HANDOFF.md`: requests and reports in `board/tutorboard/jobs.py`,
> `board job` writing a request on a machine without Slurm, `board ask-cluster`, the merged
> registry, the `requested` status, the shared validator, and the thread file's `exports` with
> `board thread export`. Read "The relay" and "Rules that bind every item" first. The JSON
> shapes there are the contract; change them only with a one-line reason left in HANDOFF.
> Tests: validation refusing each bad case with every problem listed, the registry merge, status
> derivation with a request outstanding, and the request commit touching only `relay/requests/`.
> Update all eight workspace contracts. Ship with the repository's scripts.

### 3. The relay on the cluster — depends on 2

A `scrontab` entry, every five minutes, runs `tutor relay` once. `scrontab` is available on
this cluster. Each pass does the following, in order, and is safe to run twice at once (take a
lock, and skip the pass if the lock is held):

1. Pull from origin, fast-forward only. If the tree has commits or edits outside the cluster's
   own paths, skip the pass and say so in `relay/state.json`, which is ignored. Then move
   `vendor/colibri` forward with `pull_vendor`.
2. For each request with no report, validate it. Then submit it through `jobs.submit`, or
   refuse it in a report.
3. Poll unfinished jobs with the existing `jobs.poll`. The board daemon's poll moves here.
   **`sacct` is refused on this cluster** (its database connection is refused), so a job's end
   cannot be read from Slurm's accounting. `jobs.submit` wraps every recipe so its last act
   writes the exit code to `relay/state/<id>.exit`, which is ignored. A job that has left
   `squeue` with that file is ended with that code. A job that has left `squeue` without it
   died: timeout, node failure or a cancel. On an ended job, copy the exports, check them
   against the thread file and the size cap, and write the report.
4. For a `turn` request in a workspace that opted in, run a headless Claude turn there, with the
   brief, the thread, and the rule that its note is public. Only one turn runs at a time; the
   rest wait for later passes.
5. Commit only `relay/reports/` and `exports/`, rebase onto origin, and push. On a rejected push,
   retry once next pass. Never force.

`tutor relay --once` and `tutor relay --status` run it by hand and show what it sees.
`relay/state.json` records the last pass, the last error and the last pushed commit.

> **Prompt:** Build item 3 of `HANDOFF.md`: `tutor relay` and its scrontab entry on this
> cluster. Read "The relay", "Rules that bind every item", and item 2's code. First prove that a
> compute node in the `c3_short` partition can reach github.com with git over HTTPS. If it
> cannot, stop and report that in one line. Reuse `jobs.submit`, `jobs.poll` and `pull_vendor`.
> `sacct` is refused here: end jobs from `squeue` plus the exit-code file, and test a job that
> leaves `squeue` without one. Write a report's note so it can be published, and enforce the `RELAY:` line rule and the
> export checks in code, not only in the turn's instructions. Install the scrontab entry with a
> command the README names, and make `tutor where` show the relay's last pass. Tests use a temp
> repository with a fake `sbatch` and `squeue`, and cover: a request run, a refusal, two passes
> at once, an export over the cap refused, a dirty tree skipping the pass, and a push retried.
> Then run one real request end to end: the TRD-EHR neighbour-count sweep on its smallest
> embedder, filed from the Mac side of the code. Ship with the repository's scripts.

### 4. The Mac hears the cluster — depends on 2

- The Mac's periodic pull (item 1's launchd timer, `tutor-pull`) runs every two minutes while a
  request is outstanding, and hourly otherwise.
- A report that changed state in a pull drops a `[job]` message in that workspace's inbox, the
  way `jobs.poll` does now. That wakes a turn through `turn_signal`. The turn reports what
  finished, what it produced, any non-zero exit, and the `RELAY:` lines. Then it moves the
  thread on.
- `board brief` lists the thread's outstanding requests and its last report.
- The paper builders and the library resolve a missing `results/…` path to `exports/results/…`.
  `board thread --check` counts a path present in either place as present.

> **Prompt:** Build item 4 of `HANDOFF.md`: the Mac side of the relay. Read item 2's code and
> `jobs.poll`'s inbox wake. Make a pulled report wake a turn the way a finished local job does,
> without a second wake mechanism. Make the pull's cadence depend on outstanding requests, and
> make `results/` paths fall back to `exports/results/` in the paper builders, the library and
> `board thread --check`. Test the wake, the cadence, and a manuscript compiling on a tree with
> no `results/`. Ship with the repository's scripts.

### 5. Coding at the cluster, coached on the glass — depends on 2, 3 and 4

The owner sometimes writes code on the cluster, beside the data: an estimator they are being
coached on, or a fix that only real rows reproduce. The coach still lives on the Mac and the
card still lands on the iPad. The step's check runs on the cluster, because it needs the data.

**A sitting is held at the cluster.** `board hold <thread>`, run in the cluster checkout, records
the hold in `relay/holds/<thread>.json` and pushes it. From then until `board release <thread>`:

- The thread's `files` belong to the cluster. The Mac's turns refuse to write them and say why.
  The tutor's plumbing for that thread waits for the release, or goes in files outside the
  thread's list.
- The relay's pass leaves the owner's uncommitted edits alone. It pulls with rebase and
  autostash, which is safe because nothing upstream touches the held files.
- The Mac polls every 20 seconds instead of on its usual cadence.

**`board send`** is the owner's one command per step, typed in the cluster terminal:

1. It commits the thread's changed `files` with the message `<thread>: step` and the owner as
   author.
2. It runs the thread's `check` right there, on the node the owner is on. `check` is a tracked
   script named on the thread, written by the tutor, which prints only `RELAY:` lines. Its exit
   code and those lines go into `relay/reports/check-<thread>-<n>.json`.
3. It pushes both, then waits up to three minutes for the coach's reply and prints it in the
   terminal.

**On the Mac**, the pull carrying a `check-` report drops a `[coach]` message into the inbox. The
woken turn is a coach turn under `board/TEACHING.md`. It reads the step's diff and the check's
lines, and writes the next card on the board. It also writes the same text to
`relay/coach/<thread>.md` and pushes it, which is what `board send` prints. The text is public:
it talks about the code and the check's aggregate numbers, never about rows.

A round trip takes about a minute or two: push, a 20-second poll, the turn, and the push back.

**Coaching right here** stays possible. Claude Code on the cluster runs under the same contract,
with the data beside it, and is faster. Its sitting records itself with `board push` like any
turn, so the board shows the steps afterwards. `board hold` is for when the owner wants the
iPad as the coach's page.

> **Prompt:** Build item 5 of `HANDOFF.md`: holds, `board hold`, `board release`, `board send`,
> the thread's `check`, the `[coach]` wake and `relay/coach/`. Read "The relay", items 2 to 4's
> code, `board/TEACHING.md`'s coach section, and the coach division of labour in the workspace
> contracts. Extend the validator so a hold is refused on a thread that already has one, a
> `check` must be tracked, and a Mac turn writing a held file is refused. Make the relay's
> rebase-with-autostash safe against the owner's edits, and prove it with a temp repository
> where the owner has uncommitted edits to a held file while the Mac pushes elsewhere. Add a
> test for each piece, plus one full round trip with fake push and pull. Then run one real round
> trip on a TRD-EHR Paper 2 coach thread with a trivial check. Ship with the repository's
> scripts.

### 6. Colibri on demand — depends on 3

Colibri is not kept warm. It runs while it has work and stops when it has none. A task survives
the job running it.

- **A task queue on the cluster**, in the libr-local-llm workspace's ignored state, because a
  Colibri task may name session content. A task has a thread, a brief, a state, an attempt
  count, and the conversation name `coli-code` resumes by. It is filed by
  `board colibri <thread> "<task>"` on the cluster, or by a `colibri` request through the relay
  from the Mac.
- **Filing a task starts a generation if none is queued or running.** The generation loads,
  then works through the queue one task at a time. It exits cleanly once the queue has been
  empty for 20 minutes.
- **Each generation submits its own clone at start**, depending on itself ending not-ok and
  killed if that dependency can never be met. A generation that dies (timeout, node failure,
  out of memory) starts the clone. A clean exit lets Slurm drop it. The clone does the same in
  turn. So a death costs one cold load, about 68 minutes, and no work.
- **A task interrupted by a death is resumed by the clone**, through the existing exit-75 hop and
  resume-by-name in `coli-code`. After three deaths on the same task, the task is marked failed
  and is not retried.
- **The warm overlapping chain (`coli_chain_watch`, `COLI_CHAIN`) is off by default.**
  `coli-up --warm` turns it on for a session that wants Colibri answering live.
- **What comes back is public.** Colibri may read PHI, so its output never goes into a report
  directly. A finished task is shipped the way that project's HANDOFF already requires: a
  hosted follow-up turn reviews the diff, `names_phi` runs before anything leaves the machine,
  and the relay report carries only state and that turn's public note.
- The board's Colibri status (`off`, `queued`, `loading`, `warm`) stays, and `off` is now the
  normal state with nothing queued.

> **Prompt:** Build item 6 of `HANDOFF.md`: Colibri on demand. Read `projects/libr-local-llm/`
> `README.md` §4c, its `HANDOFF.md` ("The guarantee, and what it does not cover", and the
> traps), `slurm_jobs/colibri_serve.sbatch`, `bin/coli-up` and `bin/coli-code`,
> `board/tutorboard/colibri.py` and `missions.py`. Extend the mission record into the task
> queue; do not build a second queue. Add the self-clone with a not-ok dependency and
> kill-on-invalid-dependency, idle exit after 20 minutes of an empty queue, the three-death cap,
> `board colibri`, the relay's `colibri` request kind, and `coli-up --warm` for the old chain.
> `sacct` is refused on this cluster, so tell a clean exit from a death the way item 3 does.
> Test with fake `sbatch` and `squeue`: a death mid-task resumed by the clone, a clean exit
> dropping the clone, the cap, and two tasks filed at once starting one generation. Then run
> one real small task end to end. Update that project's `README.md` and `HANDOFF.md` to
> describe on-demand as the default, in the present tense. Ship with the repository's scripts.

### 7. Providers on the Mac — depends on 1

DeepSeek and the others are already in `board/tutorboard/keys.py` and `assistants.py`. On the
Mac they become ordinary choices for any workspace: the Mac holds no PHI. What changes:

- A workspace's `tutorboard.json` may name a default provider per sitting kind, for example
  DeepSeek for learn sittings in a course and Claude for build sittings in research.
- `board/tutorboard/net/egress.py`'s endpoint list includes each configured provider.
- A cluster `turn` always uses Claude under the PHI guard. Colibri remains the only model that
  reads PHI, and it runs only on the cluster (item 6).

> **Prompt:** Build item 7 of `HANDOFF.md`. Read `keys.py`, `assistants.py`, `provider.py`, and
> the egress rules in `board/tutorboard/net/`. Let `tutorboard.json` name a default provider per
> sitting kind, show the choice on the sitting sheet, and keep the cluster's turn on Claude.
> Confirm DeepSeek answers one real turn on this Mac using the key in
> `~/.config/tutor-board/keys.env`. If the key is missing, say so in one line naming that path.
> Ship with the repository's scripts.

### 8. The compute node stops serving — depends on 1, 3, 4 and 5, after a week of use

When the Mac has served a week of sittings and the relay has carried a real request each way,
delete what only served boards from the cluster: `tutor serve`, `tutor watch`,
`tutorboard/supervise.py`, `slurm/tutor-serve.sbatch`, `test/perpetual.py`, the `serve_*` keys,
and the userspace Tailscale updater. Keep `pull_vendor`, which the relay calls.

> **Prompt:** Build item 8 of `HANDOFF.md`. First confirm both conditions from
> `relay/state.json`, the reports, and the archive dates. If either is unmet, stop and say
> which. Remove the serving chain the item lists, every reference to it in code, tests,
> contracts and READMEs, and the suites that only test it. Cancel any `tutor-serve` jobs still
> queued for this user. Rewrite the root `README.md` sections "The machine this was built for"
> and "The board is the way in" for the Mac host and the cluster relay, in the present tense.
> Ship with the repository's scripts.

### 9. Smaller board work left from the threads build — depends on nothing

Each is independent and small. Give one agent all five, one commit each.

- **Accept a proposed thread with one tap.** A rethink proposes a thread in its report. Add a
  route and a card control that runs `board thread add` on a tap. This touches shell files.
- **The thread sheet dispatches a mission.** `POST /elsewhere` already validates `thread`. Add
  the control to the sheet in `map.thread_sheet` and `board.js`.
- **A stopped card lists what the thread left.** Give `report_owed` in `bin/tutor` the thread's
  paths and the jobs registered since the turn began, and add a badge on the box.
- **A turn's commit names a real thread.** `board push "<thread>: msg"` checks the prefix
  against `threads.json` where one exists.
- **The thread sheet links its write-up.** Each `writes` anchor opens the deliverable's document
  at that heading.

> **Prompt:** Build item 9 of `HANDOFF.md`: five small changes, one commit each, each with a
> test. Read `map.thread_sheet`, the sheet code in `board.js`, `cards.stopped_body`,
> `report_owed`, and `cmd_push`. Ship with the repository's scripts.

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
  be published to `exports/`. Item 4 cannot show a figure on the Mac until this is done.

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
