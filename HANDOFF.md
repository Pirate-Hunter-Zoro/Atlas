# HANDOFF: the Atlas overhaul

**What this is.** The task list for one overhaul of Atlas, executed overnight by autonomous agents.
One agent takes one task. It reads sections 1 to 4 (the preamble) and its own task section, nothing else.
The tasks build the system of section 2 on the branch `overhaul`. Task T59 then puts it live on the Mac.
The owner is away and unreachable, and nobody uses the iPad tonight. Every judgement call is made in section 3.
No agent touches the cluster. Cluster steps become the owner's morning runbook in iCloud.

---

## 1. Vision

The owner's thirteen points, in his order.

1. **Keep and generalize the math tutoring session.** Handwriting on the board, feedback, auto-typed
   transcription, rendered math and exercises, applied to anything: Colibri, the LIBR compute-node
   system, diarization, the counterfactual pipeline, LeetCode.
2. **One catch-all tutor.** A session starts generic. The owner names the course or project, new or
   existing, and uploads materials. The tutor organizes storage at its own discretion. Families, maps,
   threads and deliverables go.
3. **Only courses and projects.** research/ and practice/ merge into projects/. Creating a course or
   project is trivial. Deleting a course, project or textbook from the iPad works at any time.
4. **Courses are plain content in Atlas.** The private course-repo machinery is purged.
5. **Sessions persist** until the owner ends them.
6. **Coach-coding** on the LIBR compute node, plus vibe-coding, in harmony through git.
7. **Auto writeups** whenever the owner hand-writes solutions to tutor-posed questions.
8. **On demand, from any session:** a beamer deck to PDF, or a Markdown manuscript to .docx.
9. **Meeting notes:** select recent work, get a tweakable deck, saved and replaced next time.
10. **A blank lecture-notes canvas,** saved to a course or project at the tutor's discretion.
11. **Import a PDF to write on,** saved to a course or project at the tutor's discretion.
12. **Cluster harmony.** The tutor edits on the Mac and pushes. The node pulls, submits Slurm jobs, and
    the tutor reads the results back. Colibri is monitored. Coach and vibe work stay in sync. No hosted
    model runs on an institute machine, no PHI enters git, and every commit is public.
13. **Massive simplification,** with performance, scalability, ease and pleasantness.

---

## 2. Target design

### Processes

- **Mac.** One LaunchAgent, label `tutor-board` (KeepAlive true, absolute interpreter path,
  ThrottleInterval 10), runs one `board/serve.py` on port 8778. `tailscale serve` publishes HTTPS to
  127.0.0.1:8778 once; nothing re-points it. serve.py refuses to start where Slurm exists.
- **Inside serve.py:** the HTTP routes, one event-driven hub per viewed session, the runner, a cluster
  thread and a freshness thread.
- **Runner.** One FIFO per session, at most 2 turns at once. A turn is one fresh provider process
  (`claude -p` by default), cwd = the Atlas root, with `TUTORBOARD_SESSION=<session dir>`,
  `TUTORBOARD_TURN=1` and `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1`. The prompt carries the brief and the
  recap; the global CLAUDE.md still loads. The message is persisted as `owed` first and re-queued at startup.
- **Cluster thread** (only with `TUTORBOARD_CLUSTER=1`). Every 20 s, `git ls-remote origin` for `main`
  and `refs/heads/code/*`. On a change: a fast-forward pull, a vendor submodule update, then hearing.
- **Freshness thread.** Exits 0 once committed board code changed and no turn runs; launchd restarts it.
- **Cluster.** No board server and no model, ever. scrontab runs `board/scripts/relay-pass.sh` every
  2 minutes: flock, a bash fast-forward pull, a re-exec when board/ changed, then
  `python3 board/bin/relay --once --quiet`. The owner runs `board code <session>` by hand to coach.
- **GitHub is the only channel:** `main`, plus `code/<session-id>` per open cluster coding session.
  `board` is the Mac CLI (`board code` also runs on the cluster); `board/bin/relay` is the cluster's
  scheduled entry. bin/tutor does not exist.

### Data model

- **Subject.** A directory directly under `courses/` or `projects/`. Its kind is the parent. No
  registry, no marker. Optional `tutorboard.json` holds {name, phi, check, relay}. `relay` holds
  `exports`, `colibri` and `fingerprint`. Check output and log excerpts leave the cluster only when
  `phi` is literally `false` on disk and at HEAD.
- **Session.** `sessions/<YYYYMMDD-HHMMSS>/`, Mac-only and ignored. `session.json` holds {id, title,
  subject|null, mode teach|do, opened, ended|null, writeup|null, seen, code|null, view}. A session starts
  unbound in teach. Only End ends it. A cluster report for an ended session reopens it.
- **Artifact.** A directory holding `doc.json` = {title, source, sessions, asked_at}. Type comes from
  the source extension and its document class. Status comes from mtimes. New ones live at
  `<subject>/docs/<slug>/`. Legacy trees get a doc.json written in place, so their ids hold.
- **Material.** A third-party or uploaded file in `<subject>/materials/` (ignored), readable and inkable.
- **Ink.** One kind. Card ink lives in the session; document ink in `<subject>/.ink/` (ignored), keyed
  `doc/<id>/p<n>`, where a material's id derives from its path.
- **Memory.** `<subject>/RULES.md` is the owner's (enforced, tutor cannot commit it).
  `<subject>/TUTOR.md` is the tutor's: sections "Where things are", "Now", "Open decisions",
  "Done recently", at most 800 words, written only with `board memo <section>`.
- **Git carries** text the owner or tutor wrote. Sessions, ink, materials and built PDFs stay on the Mac.

```
Atlas/
  board/  vendor/  .githooks/  ai-config/ (private nested repo, ignored)
  relay/status.json          tracked; the relay's health, committed only on change
  sessions/<id>/             session.json cards/ slate/ answers/ turns.jsonl inbox/messages.jsonl
                             uploads/ text/ annotations/ agent.json cost.jsonl agent.log
  sessions/.tikz/            TikZ cache keyed by hash(source + subject macros)
  courses/<Name>/  projects/<Name>/
    tutorboard.json  RULES.md  TUTOR.md  README.md (owner's, never fed to the brief)
    materials/  .ink/        ignored
    docs/<slug>/             doc.json  <slug>.tex|.md  handwritten/
    <own tree>               e.g. chapters/chNN-*/homework/*.tex with doc.json in place
    relay/requests/  relay/reports/  exports/     tracked: the cluster channel
    relay/state/             ignored: jobs.jsonl, reported/, colibri/, exit files
    phi/  results/  .env     cluster only, ignored, never read by an agent
  projects/Meetings/         "phi": true; the meeting deck is its artifact docs/meeting/
```

### Flows

- **Start generic, then bind.** "New session" opens `/s/<id>/board`, unbound, in teach. The tutor runs
  `board bind courses/Topology [--create]`, or the owner taps the subject chip. Binding sets `subject`
  and appends a non-waking `[bind]` line; nothing moves or restarts. "Do it" flips `mode` the same way.
- **Create.** "+ course", "+ project" or `bind --create`. A new project asks "patient data?". The answer
  sets `phi`, and yes also writes the PHI ignore stanza. Creation makes the directory, tutorboard.json
  and a TUTOR.md skeleton in one commit.
- **Delete.** A subject needs its name typed; a material, document or session a second tap. Targets go
  to `~/.local/share/tutor-board/trash/<stamp>/` (kept 30 days); tracked files leave by `git rm` in one
  commit. A subject delete needs `"phi": false` literally at HEAD and no open session, coding session or
  outstanding request on it. A PHI subject is removed only through a cluster runbook.
- **Uploads** land in the session's `uploads/` with a non-waking line; the tutor files them (`board file`).
- **Build.** One builder, `board build <file>`: pdflatex for `.tex` (beamer or article detected), pandoc
  for `.md` to .docx plus PDF when an engine exists. Output lands beside the source.
- **Writeups.** In teach mode every agreed answer goes in with `board writeup add` and the PDF is
  rebuilt. A course's assigned set is the same artifact, written in place.
- **Deck or paper.** The Make menu creates the doc.json; a `[writeup]` turn writes and builds it.
- **Meeting.** Pick a period and items, get one brief, and the deck in `projects/Meetings/docs/meeting/`
  is replaced. git history keeps the old ones.
- **Reading.** One reader shows every PDF. "Say what's wrong" sends the marked pages to a `[revise]`
  turn. The tutor decides whether to edit the source or write TUTOR.md.
- **Notes canvas.** A session in full-slate view; End has the tutor transcribe a `notes.md`.
- **Annotate a PDF.** Upload, ink; "Keep a marked copy" writes `<name>-marked.pdf` beside it. Filing
  the upload re-keys its ink.
- **Non-session asks** (library feedback, Make from home, meeting asks) go to the newest open session
  bound to the target subject, else to a new session bound to it, because the owner asked.

### Coding

- **Learn.** The tutor traces any path in Atlas. board/ and vendor/ are read-only. Excerpts carry
  `path#Lx-y`, and a read-only source viewer opens them, highlighted.
- **Coach on the Mac.** Teach mode; the tutor reads the working tree directly.
- **Coach on the cluster.** `board code <session> [paths]` snapshots the held paths to `code/<id>`
  through a temporary index after 10 s of quiet, runs the check, and pushes. The Mac wakes the session
  with a `[code] step N` line, and the tutor answers on the iPad. `--end` makes one commit on main. While
  the session is open the relay tolerates the held paths and the Mac refuses commits to them on main.
- **Vibe (do mode).** The tutor edits, runs `board check`, pushes, then files `board job` pinned to that
  commit. A failed job gets up to 3 repair turns. While a cluster coding session is open, the session's
  pushes go to `code/<id>` instead of main.
- **The board itself** is edited only in a worktree; the main checkout serves the iPad.

### Cluster round trip

- The Mac pushes; relay-pass.sh pulls fast-forward only. The relay validates (recipe tracked and
  unchanged, HEAD contains the pinned commit, `#RELAY-VAR` holds, `kind: turn` refused) and submits
  through the exit-file wrapper with the shared fingerprint library.
- A report carries RELAY lines, `ran_at`, gated exports, and a sanitized log excerpt only where `phi`
  is literally false. The Mac hears it and wakes the filing session, reopening it if ended; with no
  session it becomes a home notice and starts no turn.
- `relay/status.json` carries errors and Colibri state. A request unsubmitted 15 min after its commit
  shows "relay looks down".

### Docs that remain

`README.md` (at most 200 lines), `board/README.md` (600), `board/TEACHING.md` (600); per subject
`RULES.md`, `TUTOR.md` and the owner's README.md; `HANDOFF.md` (only what is left); `NOTICE.md`.

---

## 3. Decisions

Made by the owner or on his behalf. Do not reopen them.

- **D1 Visibility.** Atlas stays public; the TRD-EHR paper1 manuscript links to it. Textbooks,
  `reading/`, `lectures/`, professors' slides, `assignment*`, `materials/` and session `uploads/` are
  ignored, never tracked. Owner-authored work is tracked. When paths move, the manuscript's links move.
- **D2 Course history.** Each course folds in as one snapshot commit. Full histories are bundled in
  `~/Archive/atlas-migration/2026-10-07/` (HEADS.txt lists the shas). Nested `.git` dirs go there too.
- **D3 Worked solutions** are tracked: homework, exam practice, writeups, handwritten answer PNGs.
- **D4 Relay traffic** (requests, reports, status, coding refs) stays in Atlas.
- **D5 No watcher job.** The relay scrontab runs every 2 minutes. `board job --batch` stays. There is
  no `--watch` and no poke file. The owner re-installs the relay on the cluster.
- **D6 Providers.** claude is the default, codex the fallback, `vision_agent` stays. The DeepSeek recipe
  through opencode stays. aider, cursor and plain opencode go. Colibri runs only as relay tasks, so
  carry/hop code goes. Colibri warmth is unchanged.
- **D7 Global CLAUDE.md** stays in tutor turns. Only the brief and recap are injected.
- **D8 Paper-Writer** stays an ordinary project with the board coupling removed. TRD-EHR's
  `scripts/rebuild-packet.sh` runs `board build`, so one md-to-docx converter exists.
- **D9 Old archives.** Each `live/archive/` is tarred to `~/Archive/atlas-migration/<date>/`.
  `import_live` turns each workspace's current `live/` into one open session. Every entry has a
  destination (T14).
- **D10 Meeting deck** is an artifact of `projects/Meetings/` (`"phi": true`). No root `meetings/`.
- **D11 Exports.** The LaTeX transcript export is retired. The screenshot export stays. Old course
  `transcripts/` are archived.
- **D12** highlight.js core (Python, Go, Bash, Lean, R, SQL) is vendored, its licence in NOTICE.md.
- **D13 Subject READMEs** stay as the owner's docs and never feed the brief. The open items of
  `PSYCH-ASR_TODO.txt` and `LOCAL-LLM_TODO.txt` move into TUTOR.md, then both files go.
- **D14 Memory files.** The tutor's file is `TUTOR.md`; the owner's is `RULES.md`. The pre-commit hook
  refuses any commit touching `*/RULES.md` while `TUTORBOARD_TURN` is set. The brief reads RULES.md at
  HEAD and flags a working-tree difference. The verb is `board memo <section>`.
- **D15 One ink kind on documents.** Direction ink, `proposals.py`, the `dir:1` stroke kind,
  `page_map`, `\meetingws` and the reader `mode` go. `check_sources` stays.
- **D16 Cluster reports** wake the filing session, reopening it if ended. A request with no session
  becomes a home-screen notice with no turn. Nothing auto-creates sessions for reports.
- **D17 Coach-coding** uses one ref per cluster coding session, `code/<id>`. Replies appear on the iPad.
  No `coach/<id>`, no `--ask`, no `code-diff`, no terminal echo of cards. Vibe pushes go to the same
  `code/<id>` while it is open.
- **D18 atlas.json is deleted.** bootstrap.sh and adopt_private hard-code the ai-config URL,
  `https://github.com/Pirate-Hunter-Zoro/ai-config.git`. `subjects.root()` derives from `board/`.
- **D19 One Mac CLI.** `board` absorbs pull, cost and doctor; bin/tutor is deleted (T49).
  `board/bin/relay` is the cluster's scheduled entry. Tests are repointed at new modules, with no
  attribute-write forwarding.
- **D20 Notes canvas and PDFs.** As in section 2. No `notes` or `annotated` artifact kinds. One root
  ignore rule covers LaTeX scratch and built PDFs.
- **D21 Uploads** always land in the session's `uploads/`, with a non-waking line. No per-upload prompt.
- **D22 Continuity.** NEXT.md and `board note` are deleted. Continuity is the injected recap, TUTOR.md
  and RULES.md.
- **D23 iPad delete** of a subject is refused unless tutorboard.json at HEAD literally says `"phi": false`.
- **D24 Execution context.** The cutover runs at the end without the owner. Every cluster step goes to
  `/Users/mikeyferguson/Library/Mobile Documents/com~apple~CloudDocs/HANDOFF-cluster.md`. Agents
  never ssh to the cluster.
- **D25 Already done** before this file: see 4.1. Time Machine has no destination; that is an owner
  item, not a blocker.
- **D26 Rehearsals.** Fixture tests and rehearsals on copies of the live dirs replace every rehearsal
  with the owner. At most one real model turn per task, only where an Accept line demands it, on the
  cheapest working provider.
- **D27 Simplicity, adopted.** relay-pass.sh pulls in bash, has no last-known-good copy, and re-execs
  after a pull that changed board/. Colibri state on the Mac comes only from status.json. No `follow`
  flag. The audit runs in the pre-commit hook and tracked.py only. all.sh is a one-line exec of run.py.
  The hub has no lock. `/subject.json` carries only surviving data. The build port touches only
  surviving callers. Shims are time-boxed and T55 removes them. No per-session provider override.
- **D28 Docs during the overhaul.** T02 deletes SETTLED.md, board/AI_INSTRUCTIONS.md and
  board/tools/docs-audit.md, and cuts board/README.md to 60 lines. After that no task edits doc prose
  except TEACHING.md, until T57 writes README.md and board/README.md. T60 rewrites this file.

---

## 4. Rules for every task

### 4.1 State at the start

- T00 is done: every repository is bundled into `~/Archive/atlas-migration/2026-10-07/` (Atlas,
  ai-config, Galois-Theory, Probability; HEADS.txt). `live-dirs.tgz` there holds every workspace's
  `live/`. Rehearsals extract it into a temp dir instead of touching the real `live/`.
- Probability's exam1-practice work is committed in its nested repo.
- TRD-EHR's HANDOFF.md edits and `placed-*.json` are committed on main (40f13c66).
- `atlas.json` has `"relay": {"sync": false}` on main, pushed.
- The main checkout runs the old system: three `serve.py --root` boards (ports 9098, 8808, 8937),
  `tutor headless` daemons, and LaunchAgents `tutor-board.tutor-watch` and `tutor-board.tutor-pull`.
- `TUTORBOARD_TURN` appears nowhere in the code yet. No Python file uses a walrus or `match`.
- The TRD-EHR manuscript's code link, `https://github.com/Pirate-Hunter-Zoro/TRD-EHR`, returns 404.

### 4.2 Execution model

The integration branch is `overhaul`. Nothing checks it out. Each task, with
`G=/Users/mikeyferguson/Developer/Atlas` and `T=<task id>`:

```
# 0. create overhaul once; the zero sha makes a second creator fail harmlessly
git -C $G update-ref refs/heads/overhaul $(git -C $G rev-parse main) 0000000000000000000000000000000000000000 2>/dev/null || true
# 1. own worktree
git -C $G worktree add $G-wt/$T -b ov/$T overhaul
# 2. private, ignored pieces (.git/info/exclude already ignores both links)
ln -s $G/ai-config $G-wt/$T/ai-config
ln -s $G/board/node_modules $G-wt/$T/board/node_modules
# 3. implement and commit on ov/$T (see 4.3)
# 4. rebase onto the latest overhaul and run the suite
old=$(git -C $G rev-parse overhaul); git -C $G-wt/$T rebase $old
cd $G-wt/$T && python3 board/test/run.py     # before T01 lands: bash board/test/all.sh
# 5. advance overhaul by compare-and-swap; on failure overhaul moved: repeat 4 and 5
git -C $G update-ref refs/heads/overhaul $(git -C $G-wt/$T rev-parse HEAD) $old
# 6. clean up
git -C $G worktree remove --force $G-wt/$T && git -C $G branch -D ov/$T
```

- Before starting, confirm each dependency landed: `git -C $G log overhaul --oneline --grep '(Txx)'`.
  A missing dependency means stop and report; the orchestrator should not have started you.
- Other tasks advance `overhaul` while you work. Resolve rebase conflicts yourself, keeping both sides'
  intent, and re-run the suite after every rebase.
- Never push `overhaul` or any `ov/*` branch. Never merge into main. Only T59 and T60 touch main.
- **The main checkout serves the iPad live.** No task edits a file under `$G`, except T59 and T60,
  and except `$G/ai-config` commits where a task says so. Reading the main checkout is allowed.
- Worktrees lack ignored content: course dirs (until T27), `.venv`, `.lake`, `live/`. Copy what a test
  needs into a temp dir; never symlink live data into a worktree.
- Never `git stash`. Never force-push. Never `git add -A` at the Atlas root of the main checkout.

### 4.3 Commits

- Commit with `git -c core.hooksPath=$G/.githooks commit`. The owner is the author. The commit-msg hook
  strips trailers; add none.
- Subject style: `<area>: <what, present tense> (Txx)`. The `(Txx)` suffix is how later tasks and T60
  find what landed.
- Delete a test suite in the same commit as the code it covers.
- `ai-config` is the owner's private repo. A task that must change it commits there in its own commit,
  in `$G/ai-config`, and pushes it with `git -C $G/ai-config push`. Say so in the report.

### 4.4 The suite

- `python3 board/test/run.py` once T01 lands (all.sh then just execs it). `--guards` runs the PHI and
  relay guards only.
- Suites can collide on ports while other worktrees test at once. Re-run a failed suite alone before
  believing it.
- A task leaves the suite green. A suite deleted with its code is the only acceptable way to lose one.

### 4.5 PHI and public commits

- Never read, list or copy anything under `phi/`, `results/`, or any directory named in
  `board/tutorboard/fenced.py` `NEVER`. Existence checks only.
- Keep, and never weaken: `board/test/tracked.py`, `ai-config/policy/phi.py` fencing by name, the
  anchored `/phi/` ignores, `.githooks/commit-msg`, `jobs.NO_TURN`, and the rule that a Colibri task
  changing a tracked file fails.
- Every commit to Atlas is public. Never commit a session, ink, an upload, a material, a third-party
  file, a log tail, a participant id or a lab storage path.

### 4.6 Cluster compatibility

- Relay-path code runs on the cluster's python3, which may be 3.7: board/bin/relay, board/bin/board's
  `code` subcommand, and the modules relay, jobs, colibri, exports, cluster, code, fenced, leaving,
  paths, worktree, gitops, audit and anything they import.
- In those files: no walrus, no `match`, no `str.removeprefix`, no `functools.cache`, no `dict | dict`,
  no builtin generics like `list[str]` evaluated at runtime. T05a adds a check that enforces this.
- Bash that runs on the cluster (relay-pass.sh, move-residue.sh, job_env.sh) is also tested on the
  Mac's bash 3.2: no `mapfile`, no associative arrays, no `${var,,}`. `timeout` and `flock` exist only
  on the cluster; guard each with `command -v`.

### 4.7 Rehearsals and real turns (D26)

- Prove behaviour with fixture tests: temp repos, bare remotes, fake `squeue`/`sbatch`, a fake
  provider script that writes a card.
- Rehearse on copies: extract `~/Archive/atlas-migration/2026-10-07/live-dirs.tgz` or `cp -R` a live
  dir into `mktemp -d`. Never point a test at a real `live/` or the real `sessions/`.
- At most one real model turn per task, and only where Accept says "one real turn". Use the deepseek
  recipe when `~/.config/tutor-board/keys.env` has its key, else claude.
- A test server never binds 8778 and never sets `TUTORBOARD_CLUSTER=1` against the real origin. Use
  port 8779 or an ephemeral port.

### 4.8 Docs (D28)

- After T02, edit no doc prose (README files, subject READMEs, this file) except `board/TEACHING.md`,
  until T57. Code comments and prompt strings are code, not docs.
- A doc reference that goes stale because of your change is recorded in your report for T57.

### 4.9 Cluster runbook lines

- A task with a **Runbook** section appends those lines, after it advanced `overhaul`, to
  `/Users/mikeyferguson/Library/Mobile Documents/com~apple~CloudDocs/HANDOFF-cluster.md`, under a
  heading `## Pending from Txx`. Create the file if missing.
- T59 rewrites the file into the final ordered runbook. Nothing in it runs tonight.

### 4.10 Failure

- A task that cannot meet its Accept lines after real effort stops. Its report says what failed, why,
  and what it left.
- It leaves `overhaul` untouched, or advanced only by commits with a green suite that stand on their own.
- Its dependents are skipped. T59 still runs if T26 and T29 landed.

### 4.11 Report

End with: the commits that landed on `overhaul` (sha and subject), each Accept line and its result,
runbook lines appended, stale doc references for T57, and anything left undone with the reason.

---

## 5. Tasks

Dependencies are exact. A task starts only when every task it names has landed on `overhaul`.
Sections appear in dependency order. IDs follow the plan's backbone, so T41 sits before T38a.
Tasks with no dependency between them may run in parallel, each in its own worktree.

### Phase 1: foundations

#### T01. One test runner

- **Machine:** Mac.
- **Depends:** none.
- **Files:** board/test/run.py (new), board/test/all.sh, board/test/truthful.py.
- **Do:**
  - Write `board/test/run.py`, stdlib only. It discovers every suite in `board/test/` (`*.py` and
    `*.js`), minus an explicit `HELPERS` list of non-suite files. No hand-written rows.
  - It runs four suites at a time. Suites that bind fixed ports or share `~/.config` go in an explicit
    `SERIAL` list. Find them by comparing a one-worker run with a four-worker run.
  - Each suite keeps the environment all.sh gives it today (HOME, PATH, `TUTOR_*` variables).
  - It prints each suite's wall time and the total, and exits non-zero when any suite fails.
  - `--guards` runs only tracked.py, requests.py, relay.py and holds.py, in under 60 s.
  - `-j N` sets the worker count. A suite name on the command line runs only that suite.
  - It also runs Paper-Writer's unittests once (`python3 -m unittest` in projects/Paper-Writer) and
    `board/tools/sync-macros.py`'s check, as all.sh does today. It installs jsdom with
    `npm install --no-save` when `board/node_modules` is missing, as all.sh does.
  - Add `inkzoom.js`, which never runs today; discovery does it.
  - all.sh becomes one line: `exec python3 "$(dirname "$0")/run.py" "$@"`.
  - In truthful.py delete the suite-count, factory-count and family-count checks. Keep its
    retired-path check.
- **Accept:**
  - `wc -l board/test/all.sh` is 1 (plus a shebang line at most).
  - Every suite prints a duration; the total prints last; `inkzoom.js` appears.
  - "Ran N tests" from Paper-Writer appears exactly once.
  - `python3 board/test/run.py --guards` passes in under 60 s.
  - The commit message gives the wall time of the old all.sh and of run.py.
- **Prompt:**

> You are executing T01 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T01 section; nothing else. Replace board/test/all.sh's hand rows with board/test/run.py: suite
> discovery, four workers with an explicit serial list, per-suite and total timing, `--guards`, one
> Paper-Writer run, the sync-macros check, and inkzoom.js. all.sh becomes a one-line exec of run.py.
> Delete truthful.py's count checks and keep its retired-path check. Measure the old and new wall time
> and put both in the commit message. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T02. Doc purge, dead code, and the false board contract

- **Machine:** Mac.
- **Depends:** T01.
- **Files:** board/AI_INSTRUCTIONS.md, board/SETTLED.md, board/tools/docs-audit.md (all deleted),
  board/README.md, README.md (dangling references only), board/tutorboard/course/threads.py,
  board/tutorboard/machines.py, board/tutorboard/course/ledger.py, board/tutorboard/meeting.py,
  board/tutorboard/course/document.py, board/web/board.css, board/test/threads.py, board/test/node.py,
  board/test/truthful.py.
- **Do:**
  - Delete board/AI_INSTRUCTIONS.md (it says the board runs on a compute node, which is false and
    steers agents wrong), board/SETTLED.md and board/tools/docs-audit.md.
  - Cut board/README.md to at most 60 lines: the invariants with a one-clause reason each, and one
    paragraph of layout. Invariants: stdlib only and no new runtime dependency; never `git stash`;
    board edits happen in a worktree because the main checkout serves the iPad; the PHI rules of 4.5;
    the test command; how board/ ships today (`bash board/scripts/ship.sh`).
  - In README.md, delete only the sentences that point at the three deleted files.
  - Delete dead code: `threads.from_map` and its case in test/threads.py, `machines.board_port`,
    `ledger._old_for`, `meeting._author`, `document.BEAMER_HEAD`, the first, shadowed
    `author_name` in course/document.py, and board.css's `#codeanswer` block.
  - If test/node.py still exists, delete its loop over the deleted docs. Repoint any test or code that
    reads a deleted doc; truthful.py's anchor checks follow the new board/README.md.
- **Accept:**
  - `git grep -n 'board/AI_INSTRUCTIONS\|SETTLED\.md\|docs-audit' -- . ':!HANDOFF.md'` is empty.
  - `wc -l board/README.md` is at most 60.
  - `git grep -nw 'from_map\|board_port\|_old_for\|BEAMER_HEAD' -- board` is empty, and
    `git grep -n 'codeanswer' -- board` is empty.
  - The suite is green.
- **Prompt:**

> You are executing T02 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T02 section; nothing else. Delete board/AI_INSTRUCTIONS.md, board/SETTLED.md and
> board/tools/docs-audit.md. Cut board/README.md to at most 60 lines of invariants, each with its
> reason in a clause, plus one layout paragraph. Remove root README sentences that point at the deleted
> files and nothing else. Delete the listed dead functions and CSS. Keep the suite green, meet every
> Accept line, integrate by 4.2, and report by 4.11.

#### T03a. Check output opens only on an explicit `"phi": false`

- **Machine:** Mac. Reaches the cluster at cutover.
- **Depends:** T01.
- **Files:** board/tutorboard/holds.py, board/tutorboard/course/config.py,
  projects/Paper-Writer/tutorboard.json, practice/Algo-Solutions/tutorboard.json,
  practice/Lean-Theorem-Proving/tutorboard.json, board/test/holds.py.
- **Do:**
  - In `holds.output_open`, delete the `atlas.family_of(root) in ("", "research")` test.
  - Output is open only when all hold: tutorboard.json says `"phi": false` literally on disk and at
    HEAD (mirror `_head_says_phi` in course/config.py), no fence directory exists (`fenced.holds`),
    and the PHI policy loads. Anything else is closed.
  - In the same commit add `"phi": false` to Paper-Writer, Algo-Solutions and Lean-Theorem-Proving, so
    their behaviour does not change. Courses get it in T27.
- **Accept:**
  - With ai-config present, `output_open` is True for exactly Paper-Writer, Algo-Solutions and
    Lean-Theorem-Proving.
  - It is False for TRD-EHR, PSYCH-ASR, libr-local-llm, a fixture `projects/X` with no `phi` key, and a
    fixture whose `false` is on disk but not at HEAD.
  - `grep -n family_of board/tutorboard/holds.py` is empty. The suite is green.
- **Prompt:**

> You are executing T03a of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T03a section; nothing else. Make `holds.output_open` fail closed: open only when
> tutorboard.json says `"phi": false` on disk and at HEAD, no fence exists and the policy loads. Delete
> the family test. Add `"phi": false` to the three open subjects in the same commit. Add the fixture
> cases to test/holds.py. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T03b. The commit-time gate

- **Machine:** Mac + cluster runbook lines.
- **Depends:** T01.
- **Files:** board/tutorboard/audit.py (new), .githooks/pre-commit (new), board/test/tracked.py,
  board/tutorboard/leaving.py, board/bootstrap.sh, board/bin/tutor (`turn_environment`), .gitignore,
  board/test/run.py, and the dead hook copies: board/.githooks, practice/Algo-Solutions/.githooks,
  practice/Lean-Theorem-Proving/.githooks, projects/libr-local-llm/.githooks,
  research/PSYCH-ASR/.githooks, research/TRD-EHR/.githooks.
- **Do:**
  1. Move tracked.py's index audit into `board/tutorboard/audit.py` as a function over a list of
     paths that returns failure strings: the 25 MB cap, PHI suffixes and `_session` names, artifact
     suffixes, credential shapes, other people's work (`textbook/`, `reading/`, `lectures/`,
     `assignment*`, `references/*.pdf`), and any path under `sessions/`, `.ink/` or `materials/`.
     tracked.py calls it over the whole index and keeps its temp-repo self-tests.
  2. Replace tracked.py's hard-coded held paths with discovery: every directory named `phi` or
     `results` up to three levels under any `courses/*/`, `projects/*/`, `research/*/` or
     `practice/*/` must be invisible to git. Missing is fine only when none exists anywhere.
  3. Write `.githooks/pre-commit` (bash calling `python3 -m` or a small script; under 1 s):
     - run the audit and `leaving.refused` over the staged paths;
     - run PSYCH-ASR's participant-code scan (`BL` then three digits, from
       research/PSYCH-ASR/.githooks/pre-commit) over staged text in subjects whose tutorboard.json says
       `"phi": true`;
     - when `TUTORBOARD_TURN` is set: refuse a change to an existing tutorboard.json's `phi` or
       `relay.exports`, and refuse any staged path matching `*/RULES.md`.
  4. `leaving.reason` and `leaving.refused` return a refusal string when a fenced root exists but the
     policy is missing or fails to load. They still never raise.
  5. Delete the per-workspace hook copies listed above; `core.hooksPath` is the root `.githooks`.
     `board/bootstrap.sh` sets `core.hooksPath` to `$ROOT/.githooks` for Atlas itself.
  6. run.py runs `ai-config/scripts/test.sh` when ai-config exists and prints a loud SKIPPED line when
     it does not.
  7. Add root `.gitignore` rules (D1, D20), skipping any the file already has. They are inert where a
     broader rule still applies:
     ```
     /sessions/
     **/.ink/
     **/materials/
     /projects/*/phi/
     /projects/*/results/
     /courses/*/phi/
     /courses/*/textbook/
     /courses/*/chapters/*/reading/
     /courses/*/chapters/*/lectures/
     /courses/*/**/assignment*
     /relay/.lock*
     # LaTeX scratch anywhere, and built PDFs where documents are built
     *.aux
     *.toc
     *.nav
     *.snm
     *.vrb
     *.fls
     *.fdb_latexmk
     *.synctex.gz
     /courses/**/*.pdf
     /projects/*/docs/**/*.pdf
     /projects/*/homework/**/*.pdf
     ```
     A tracked file stays tracked; T34 untracks the built PDFs it moves.
  8. In bin/tutor `turn_environment`, set `TUTORBOARD_TURN=1` for every turn today, so the hook
     guards turns before the new runner exists.
- **Accept:**
  - In a scratch clone with `core.hooksPath` at its own `.githooks`, the hook refuses: a 30 MB file,
    `x_session1.wav`, a text file containing `BL123` in a `"phi": true` fixture subject, a path under
    `sessions/`, and, with `TUTORBOARD_TURN=1`, a `phi` change and a `RULES.md` change.
  - A ten-file commit spends under 1 s in the hook.
  - With a fixture policy missing, `leaving.reason` returns a string.
  - tracked.py is green on the real tree and red for a fixture `projects/X/phi` that git can see.
  - `git check-ignore -q` succeeds for one sample path per new rule.
  - commit-msg still strips attribution. The suite is green.
- **Runbook:**
  ```
  cd ~/Atlas && bash board/bootstrap.sh --no-clone
  git config core.hooksPath        # expect: /home/<you>/Atlas/.githooks (absolute)
  ls .githooks                     # expect: commit-msg pre-commit
  ```
- **Prompt:**

> You are executing T03b of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T03b section; nothing else. Move tracked.py's audit into board/tutorboard/audit.py, make
> held-directory checks discover phi/ and results/, and write .githooks/pre-commit that runs the audit,
> leaving.refused, the participant-code scan, and the TUTORBOARD_TURN refusals for phi, relay.exports
> and RULES.md. Make leaving loud when the policy is missing. Delete the dead per-workspace hooks, make
> bootstrap set core.hooksPath, add the ai-config test row to run.py, add the root ignore rules, and set
> TUTORBOARD_TURN=1 in today's turn_environment. Test the hook only in a scratch clone. Meet every
> Accept line, integrate by 4.2, append the Runbook lines by 4.9, and report by 4.11.

#### T03c. Fence the code walkers; KaTeX trusts only safe commands

- **Machine:** Mac.
- **Depends:** T01.
- **Files:** board/tutorboard/course/walk.py, board/tutorboard/course/map.py,
  board/tutorboard/course/symbols.py, board/tutorboard/fenced.py, board/tutorboard/course/reading.py,
  board/web/board.js (`typeset`) and every other KaTeX call site in board/web, board/test/walk.py,
  board/test/map.py, board/test/markdown.js.
- **Do:**
  - Add `fenced.in_fence(rel)`: true when any lower-cased path component is in `fenced.NEVER`.
    reading.py's `_fenced` uses it.
  - `walk._scan` prunes such directories. `walk.resolve` refuses a typed path with such a component.
    map.py and symbols.py return nothing for a fenced path, as a second guard.
  - Replace KaTeX `trust: true` everywhere with a function that allows `\href` and `\url` only for
    http, https and relative URLs, and `\includegraphics` only for same-origin URLs, and denies
    `\htmlId`, `\htmlClass`, `\htmlStyle` and `\htmlData`. First grep every card under the main
    checkout's `*/live/cards` (read-only) for `\html`; report any hit.
- **Accept:**
  - On a temp tree with `pkg/ok.py`, `stage1/run.py`, `raw/x.py` and `phi/y.py`, `walk.units` lists
    only `pkg/ok.py`; `walk.resolve(root, ['stage1/run.py::f'])` stays unresolved; `map.inside` draws
    no fenced box.
  - A card whose inline math is `\href{javascript:alert(1)}{x}` renders no `javascript:` anchor (jsdom).
  - `grep -rn "trust: true" board/web` is empty. The suite is green.
- **Prompt:**

> You are executing T03c of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T03c section; nothing else. Add fenced.in_fence and make walk, map and symbols prune and
> refuse fenced path components. Replace every KaTeX `trust: true` with the allowlist function. Add the
> walker and markdown tests. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T04a. Runtime trim

- **Machine:** Mac + cluster runbook lines.
- **Depends:** T01.
- **Files:** board/bin/tutor, board/bin/board, board/tutorboard/jobs.py (`PULL_BUSY`, `PULL_IDLE`),
  board/tutorboard/supervise.py, board/tutorboard/machine.py, board/tutorboard/server/spawn.py,
  board/tutorboard/server/hub.py, board/scripts/setup-node.sh (deleted), board/scripts/setup-cluster.sh
  (new), board/scripts/install-autostart.sh, board/scripts/systemd/ (deleted), board/install.sh, tests
  transcript.py, syncing.py (beat cases), hopping.py, node.py, away.js, resume.py (hop cases),
  onlyagent.py (hosts cases), carry.py.
- **Do:**
  - Delete the 90 s `lesson transcript` beat and its helpers: `beat_transcript`, `sync_transcript`,
    `keep_transcript_files`, `keep_pulled_files`. Delete `turn_pull` and set the hear-pass pull
    interval to 20 s in every state, so turns never run on a tree more than 20 s stale.
  - Delete compute-node hosting: `allocation_nodes`, `tool_line`, `ssh_tool`, `hop_to_allocation`,
    `hostnames`, `_running_jobs`, `job_holding`, `step_said`, `ensure_agent`, `ensure_agent_away`,
    `prune_dead_records`, `cmd_resume`'s node branches, `interactive_launch`, `courses`/`pick`/
    `choose`/`link`, the BRIEF.md writer, `cmd_where`, `tool_pull`/`tool_reexec`/`tool_adopt`/
    `tool_sync`, and the `hosts` map. In bin/board delete `cmd_node`, `cmd_net`, `ts_check_owner`,
    `ts_claim`. Drop supervise.py's "adopt" verdict and machine.py's node pinning.
  - D6: delete the aider, cursor and plain-opencode recipes, the colibri tutor recipe, and carry/hop:
    `take_hop`, `carry_spent`, `CARRY_EXIT`, `NOTHING_YET_EXIT`, `HEADLESS_CARRY_PROMPT`, and the hub's
    calls to `spawn.carry_missions` and `spawn.release_missions`. Keep the deepseek recipe.
  - On a Slurm host, `tutor resume` prints that boards run on the Mac and exits 0. T55 removes the stub.
  - Replace setup-node.sh with `board/scripts/setup-cluster.sh` (at most 60 lines): bootstrap, check
    ai-config, install the relay (`python3 board/bin/relay --install` when bin/relay exists, else
    `tutor relay --install`), and check `git ls-remote origin` works.
  - install-autostart.sh keeps only `--uninstall`. Delete board/scripts/systemd/ and install.sh's
    systemd branch, so install.sh never installs a timer.
  - Keep `tutor relay`, `tutor pull` (vendor), `tutor cost` and `tutor doctor`.
- **Accept:**
  - `git grep -n 'hop_to_allocation\|ensure_agent_away\|setup-node\|beat_transcript\|turn_pull\|take_hop' -- board`
    is empty.
  - With a fake `squeue` on PATH, `tutor resume` exits 0 and starts no serve.py.
  - test/relay.py is green; the whole suite is green.
- **Runbook:**
  ```
  systemctl --user disable --now tutor-pull.timer tutor-pull.service 2>/dev/null; systemctl --user list-timers | grep -c tutor   # expect 0
  bash ~/Atlas/board/scripts/install-autostart.sh --uninstall; grep -n 'tutor' ~/.bashrc   # expect no login hook line
  rm -f ~/.local/bin/tutor
  ```
- **Prompt:**

> You are executing T04a of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T04a section; nothing else. Delete the transcript beat and turn_pull (hear interval 20 s),
> compute-node hosting, the unused recipes, and Colibri carry/hop, with their tests. Replace
> setup-node.sh with setup-cluster.sh, keep only --uninstall in install-autostart.sh, and drop
> install.sh's systemd branch. Keep tutor relay, pull, cost and doctor. Meet every Accept line,
> integrate by 4.2, append the Runbook lines by 4.9, and report by 4.11.

#### T04b. Split bin/tutor into modules; a relay entry that imports only the relay

- **Machine:** Mac.
- **Depends:** T04a.
- **Files:** board/bin/tutor, board/bin/relay (new), board/tutorboard/agents/{__init__,recipes,usage}.py,
  board/tutorboard/runner/{__init__,turn,loop,prompts}.py, board/tutorboard/runner/prompts/*.md,
  board/tutorboard/gitsync.py, board/tutorboard/relay.py (`scrontab_block`), and every test that loads
  bin/tutor by path (about 32 files).
- **Do:** behaviour-preserving moves only.
  - `agents/recipes.py`: DEFAULT_CONFIG without prose, plus load, resolve, choose and unavailable.
  - `agents/usage.py`: failure markers, `failure_reason`, `result_object_error`, `turn_output`, usage
    parsers, pricing, cost.jsonl.
  - `runner/prompts/*.md`: one file per HEADLESS_* prompt, HANDOFF and TURN_TAIL; `runner/prompts.py`
    loads them.
  - `runner/turn.py`: `run_turn`, `turn_environment` (keep `TUTORBOARD_TURN=1` if T03b set it),
    `turn_plan`, `turn_timeout`, `doing_now`, `turn_signal`.
  - `runner/loop.py`: `take_turn(ctx, message) -> outcome`, plus the loop.
  - `gitsync.py`: the remaining sync and the hear pull. T10 folds it into gitops.
  - bin/tutor keeps argument parsing. Tests patch the new modules directly (D19). A thin re-export is
    allowed where repointing a test is hard; attribute-write forwarding is not.
  - `board/bin/relay` runs the pass and `--install`, `--entry`, `--status`. It imports only relay,
    jobs, colibri, fenced, leaving, paths, worktree and the holds check helpers. `tutor relay`
    delegates to it. `scrontab_block` names `board/bin/relay`.
- **Accept:**
  - `wc -l board/bin/tutor` is at most 1,200.
  - Rendered prompts are byte-identical before and after for every signal (a script renders each
    signal on both trees and diffs them).
  - `python3 -X importtime board/bin/relay --help 2>&1 | grep -c 'tutorboard\.\(server\|runner\)'` is 0.
  - A fixture turn with a fake provider script answers with a card. The suite is green.
- **Prompt:**

> You are executing T04b of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T04b section; nothing else. Split bin/tutor into agents/recipes, agents/usage, runner/turn,
> runner/loop, runner/prompts (one .md per prompt) and gitsync, without changing behaviour. Repoint
> the tests at the new modules; do not build attribute-write forwarding. Create board/bin/relay that
> imports only relay-path modules, and make `tutor relay` delegate to it. Prove prompts are
> byte-identical. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T05a. The relay launcher, a minimal status file, and the cluster-compat check

- **Machine:** Mac. Reaches the cluster at cutover.
- **Depends:** T04b.
- **Files:** board/scripts/relay-pass.sh (new), board/tutorboard/relay.py (`scrontab_block`,
  `publish`, `owned`, `run_pass`), board/bin/relay, board/test/relay.py, board/test/py37.py (new),
  board/test/run.py (`--guards`).
- **Do:**
  - `relay-pass.sh`, bash only until the last line:
    1. cd to the Atlas root from the script's own location; take `flock -n` on `relay/.lock.launcher`
       and exit 0 when it is held. The Mac has no `flock`; there, for tests, fall back to an atomic
       `mkdir relay/.lock.launcher.d` lock removed on exit;
    2. refuse to pull while a rebase, merge or cherry-pick is in progress or HEAD is detached (the
       same guards as `worktree.busy_reason`), but still run the pass, which reports why;
    3. record HEAD, then `GIT_TERMINAL_PROMPT=0 git fetch --quiet origin main` and
       `git merge --ff-only --quiet origin/main`, under `timeout 60` when available;
    4. when the merge changed anything under `board/` and `RELAY_PASS_REEXEC` is unset, re-exec itself
       once with `RELAY_PASS_REEXEC=1`, so the new launcher and new Python run;
    5. `exec python3 board/bin/relay --once --quiet`.
    A failed fast-forward still runs the pass: Python's sync handles rebases and reports the error.
  - No last-known-good copy and no `--base` flag (D27).
  - `relay/status.json` at the Atlas root, written at the end of every pass through `relay.public`:
    `{"skipped": ..., "last_error": ..., "push_pending": ..., "at": ...}`. `publish` commits it with
    the reports only when a field other than `at` changed. `owned()` treats it as the cluster's path.
  - `scrontab_block` runs `bash <atlas>/board/scripts/relay-pass.sh` (cadence stays `*/5` until T44).
  - `board/test/py37.py`: parse every relay-path file of 4.6 with
    `ast.parse(src, feature_version=(3, 7))`, and grep them for `removeprefix`, `removesuffix`,
    `functools.cache`, and `|` between dict literals. Add it to `--guards`.
- **Accept:**
  - In a fixture (bare origin, two clones): a pushed change to `board/` is pulled by relay-pass.sh,
    which re-execs once and runs the new Python; a pushed syntax error in relay.py makes the pass fail,
    and the next pushed fix is pulled by bash and used, with no manual step.
  - A skipping pass writes its reason to status.json; an identical second pass makes no commit.
  - `merged_crontab` replaces only its own block. py37.py passes. The suite is green.
- **Prompt:**

> You are executing T05a of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T05a section; nothing else. Write board/scripts/relay-pass.sh: flock, bash fast-forward pull
> with the busy guards, one re-exec after a pull that changed board/, then exec bin/relay. No
> last-known-good copy. Add relay/status.json with skipped, last_error and push_pending, committed only
> on change. Point scrontab_block at relay-pass.sh. Add test/py37.py to the guards. Prove the
> self-healing in a two-clone fixture. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T05b. De-thread the relay

- **Machine:** Mac. Reaches the cluster at cutover.
- **Depends:** T05a.
- **Files:** board/tutorboard/jobs.py, board/tutorboard/relay.py, board/tutorboard/holds.py,
  board/tutorboard/exports.py (new), board/tutorboard/cluster.py (new), board/tutorboard/course/threads.py,
  board/tutorboard/colibri.py, board/tutorboard/missions.py (`file_task`), board/bin/board (`cmd_job`,
  `_job_thread`, `cmd_colibri`), research/TRD-EHR/tutorboard.json, board/scripts/migrate-exports.py
  (new), tests requests.py, relay.py, repair.py, jobs.py, hearing.py, holds.py, colibri.py.
- **Do:**
  - Requests carry an optional `label` (slug) and `session` (Mac session id). `thread` is accepted and
    ignored. Validation never reads threads.json.
  - Replace `_job_thread` for both `board job` and `board colibri` with `--label`. `colibri.file` and
    `missions.file_task` take a label.
  - Move `EXPORT_EXTS`, `exportable`, `merged`, `finished`, `TERMINAL`, `REQUESTED` and `jobs_of` from
    course/threads.py into `exports.py`. threads.py imports them from there until it is deleted.
  - Export approval comes from tutorboard.json `relay.exports`: a list of entries `{"glob": ...}` under
    `results/`. png, pdf and svg are approved by glob. csv and json need `"aggregate": true` on their
    entry. The 5 MB cap, extension list and `names_phi` checks stay. Use it in `jobs.validate` and
    `relay.export`.
  - `migrate-exports.py` writes TRD-EHR's per-path thread marks into `relay.exports` and prints the old
    and new lists. Prove the migration in a test: every old exportable path is approved by exactly the
    new list, and no tracked file under `exports/` or `relay/reports/` names a path the new list
    approves that the old marks did not.
  - The repair brief falls back to the subject's `check` when no thread exists.
  - `jobs.drop` and `holds.wake` call `cluster.wake(subject, session, line, wake=True)`. Until T22 it
    writes today's per-workspace inbox. Reports echo `label` and `session`.
  - Keep `NO_TURN`, tracked-at-HEAD recipes, `#RELAY-VAR` declarations and `FORBIDDEN_VARS` exactly.
- **Accept:**
  - A request with no thread validates where no threads.json exists. `kind: turn` is refused.
  - A png matching a glob exports. A csv without `aggregate` is refused with a reason naming
    tutorboard.json.
  - Old TRD-EHR reports still fold into `jobs.view`.
  - `board colibri` files a task in a fixture subject with no threads.json.
  - The migration test proves list equality. `git grep -n course_threads -- board/tutorboard/relay.py board/tutorboard/jobs.py`
    is empty. The suite is green.
- **Prompt:**

> You are executing T05b of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T05b section; nothing else. Re-key requests from thread to optional label and session, with
> `thread` accepted and ignored. Move the export helpers into exports.py and take export approval from
> tutorboard.json relay.exports; migrate TRD-EHR's marks and prove equality in a test, since this is the
> PHI-adjacent gate. Route wakes through cluster.wake. Keep NO_TURN, tracked-at-HEAD recipes,
> #RELAY-VAR and FORBIDDEN_VARS untouched. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T05c. Cluster runtime state out of live/

- **Machine:** Mac. Reaches the cluster at cutover.
- **Depends:** T05b.
- **Files:** board/tutorboard/colibri.py (absorbs missions' `TASK`, `task_id`, `file_task`, `tasks`,
  `next_task`, `claim_task`, `finish_task`, `requeue_task`, `task_verdict`, `recover_tasks`,
  `update_task`), board/tutorboard/missions.py, board/tutorboard/relay.py, board/tutorboard/jobs.py
  (registry, heard-claims), board/tutorboard/holds.py, tests colibri.py, jobs.py, tracked.py, and the
  `!live/jobs.jsonl` lines in the workspace .gitignore files.
- **Do:**
  - The Colibri queue, the job registry and the heard-claims move to
    `<subject>/relay/state/{colibri/, jobs.jsonl, reported/}`. `**/relay/state/` already ignores them.
  - Expose `jobs.migrate_state(subject_root)`: it renames old records (`live/missions/`,
    `live/jobs.jsonl`, `live/jobs.reported`) into the new place, idempotently. Every reader calls it
    first. T14's `import_live` calls it too.
  - Hearing reads claims from both the new and the old location, so a job submitted before the move
    is still reported exactly once.
  - No `missions.` call remains in colibri.py or relay.py.
- **Accept:**
  - A fixture with old-location records migrates, and a second run changes nothing.
  - `git check-ignore -q` holds for the new paths. tracked.py checks the new Colibri trail.
  - `jobs.hear` over a copy of TRD-EHR's full report history plus its old `live/jobs.reported` (from
    live-dirs.tgz) wakes nothing.
  - The suite is green.
- **Prompt:**

> You are executing T05c of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T05c section; nothing else. Move the Colibri queue into colibri.py and the job registry and
> heard-claims into <subject>/relay/state/, with an idempotent jobs.migrate_state and a read fallback
> to the old location. Prove that hearing TRD-EHR's whole history after migration wakes nothing. Meet
> every Accept line, integrate by 4.2, and report by 4.11.

#### T06a. Event-driven hub

- **Machine:** Mac.
- **Depends:** T01.
- **Files:** board/tutorboard/server/hub.py, board/tutorboard/server/spawn.py, board/tutorboard/paths.py,
  board/test/hub.js, board/test/serving.py.
- **Do:**
  - Rebuild the payload only when a route marks the hub dirty, a 1 s mtime sentinel over the session
    files changes (cards/, turns.jsonl, inbox/messages.jsonl, state, agent.json, annotations/, slate/),
    or 30 s pass (for slow sources).
  - Move the ship, carry and release walks out of the poll loop if they remain; no lock (D27).
  - The payload shape does not change.
- **Accept:**
  - An idle serve.py on a copy uses under 3 CPU-seconds per 10 minutes (baseline about 53).
  - A `board write` card reaches `/events` within 1.5 s. Ink autosave still triggers no push.
  - The suite is green.
- **Prompt:**

> You are executing T06a of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T06a section; nothing else. Replace the hub's 0.25 s full rebuild with dirty marks, a 1 s
> mtime sentinel and a 30 s slow rebuild, with no lock and an unchanged payload. Measure idle CPU on a
> copy served from your worktree on an ephemeral port. Meet every Accept line, integrate by 4.2, and
> report by 4.11.

#### T06b. Service worker: automatic version, allowlist cache, gzip

- **Machine:** Mac.
- **Depends:** T01.
- **Files:** board/web/sw.js, board/tutorboard/server/routes/pages.py, board/tutorboard/server/handler.py,
  board/test/showing.py, board/test/paper.py.
- **Do:**
  - Serve `/sw.js` with `VERSION` set to a hash of the files in its own SHELL list, computed once per
    process and again on mtime change.
  - The fetch handler serves from cache only exact SHELL paths, fonts and KaTeX. Delete the `LIVE` regex.
  - Drop math.js from precache; calc.js loads it lazily.
  - Gzip JS, CSS and HTML when the client accepts it, cached by path and mtime.
  - Delete every "bump VERSION" rule from code comments and tests.
- **Accept:**
  - Editing only board.js changes GET `/sw.js`.
  - `/archive/x`, `/atlas.json`, `/map/inside/x` and `/notes/what` are never cache-matched (node test).
  - Gzipped board.js is under 200 KB. The update strip still fires (typed.js shell-version checks).
  - The suite is green.
- **Prompt:**

> You are executing T06b of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T06b section; nothing else. Make the service worker version a hash of its SHELL files, cache
> only an allowlist, stop precaching math.js, and gzip text assets. Meet every Accept line, integrate by
> 4.2, and report by 4.11.

#### T07. One build pipeline: `board build <file>`

- **Machine:** Mac.
- **Depends:** T01.
- **Files:** board/tutorboard/build.py (new), board/tutorboard/build/pdf_fit.lua (new copy),
  board/bin/board (`hw_build`, `cmd_eyes`, new `cmd_build`), board/tutorboard/sense.py (prompt strings),
  board/TEACHING.md (lines 828-848), research/TRD-EHR/scripts/rebuild-packet.sh, board/test/build.py (new).
- **Do:**
  - `.tex`: detect beamer or article; run `pdflatex -interaction=nonstopmode -halt-on-error` twice, a
    third time when the log says "Rerun", with cwd = the source's directory. TEXINPUTS comes from
    `tex.tex_env` plus `<subject>/latex` and `board/tex`. Output goes beside the source; scratch files
    go on success. No latexmk.
  - `.md`: copy (do not import) from projects/Paper-Writer/paperwriter/stages/building.py:
    `convert_one`, `_format_flags`, `_format_timeout`, `_pandoc_input`, `_resource_path`,
    `_image_targets`, `_media_count`, `text_width_in`, `figure_layout_problems`, `figures_lost`, and
    copy `pdf_fit.lua`. Copy config's pandoc lookup (`PAPER_PANDOC_BIN`, then PATH), `PDF_ENGINE`
    (`PAPER_PDF_ENGINE`, default xelatex), `PDF_MAINFONT` and `PDF_MONOFONT` with the same defaults.
  - The reference docx resolves as rebuild-docs.sh does: `--reference-doc`, then
    `PAPER_REFERENCE_DOCX`, then exactly one `.docx` in a `formats/` directory found from the source
    upward to the repository top (TRD-EHR has `formats/`).
  - `board build <file> [--format docx|pdf] [--strict]`: .md builds .docx, plus .pdf when an engine
    exists. `--strict` fails on figure-layout problems. A lost figure always fails. Missing pandoc or
    engine is reported by name.
  - Repoint only surviving callers (D27): `hw_build` (drop the course `scripts/build.sh` branch),
    `cmd_eyes`, and every prompt string that names a compiler (sense.py, TEACHING.md 828-848). Leave
    document.py, meeting.py and sittings.py alone; later tasks delete or merge them.
  - Repoint `research/TRD-EHR/scripts/rebuild-packet.sh` at `board build` for its four documents, both
    formats, passing `--strict` through (D8).
  - `homework.compiled_pdf` searches both beside the source and `build/` until T34.
- **Accept:**
  - test/build.py builds a beamer deck, an article using coursemacros from a temp `latex/`, and a `.md`
    with a figure in a sibling directory into a .docx whose image count equals its image references.
  - TRD-EHR's manuscript.md built by `board build` and by Paper-Writer's `scripts/rebuild-docs.sh`
    (both into temp dirs) gives identical `word/styles.xml` and equal image counts.
  - `git grep -n 'pdflatex' -- board/tutorboard board/bin` shows invocations only in build.py (the
    doctor's presence check aside); latexmk appears only in comments.
  - The suite is green.
- **Prompt:**

> You are executing T07 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T07 section; nothing else. Write board/tutorboard/build.py and `board build`: pdflatex for
> .tex beside the source, and a full copy of Paper-Writer's md-to-docx converter (flags, timeouts,
> pdf_fit.lua, reference docx lookup, engine and fonts, lost-figure and layout checks). Repoint only
> hw_build, cmd_eyes, prompt strings and rebuild-packet.sh. Prove style equivalence on TRD-EHR's
> manuscript against the old converter in temp dirs. Meet every Accept line, integrate by 4.2, and
> report by 4.11.

#### T08. One session-path object

- **Machine:** Mac.
- **Depends:** T04b.
- **Files:** board/tutorboard/course/repo.py, board/bin/board (`Live` class deleted, `find_repo`),
  board/bin/tutor and runner modules, board/tutorboard/{sittings,machines,progress,jobs,missions,handoff,carry,brief}.py,
  board/tutorboard/course/{config,document}.py, board/tutorboard/server/{app,hub,spawn}.py,
  board/tutorboard/lesson/*.py.
- **Do:** module by module, one commit each: bin/tutor and runner, bin/board, tutorboard core,
  server, lesson.
  - `Repo(root, session=None)`. `session` defaults to `<root>/live`; every session path hangs off it.
  - One resolver for both CLIs: `TUTORBOARD_SESSION` when set, else `find_repo()` plus `/live`.
  - `find_repo` never returns the Atlas root. Run there, it exits non-zero and creates nothing.
  - Route every `os.path.join(root, "live", ...)` through Repo. Prompt strings stay unchanged.
  - Delete the empty stray `Atlas/live/` in the worktree if present (it is untracked).
- **Accept:**
  - `git grep -nE "join\(.*['\"]live['\"]" -- board/bin board/tutorboard` hits only course/repo.py.
  - `board status` at the Atlas root without the variable exits non-zero and creates nothing.
  - The suite is green.
- **Prompt:**

> You are executing T08 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T08 section; nothing else. Give Repo a session directory and one resolver
> (TUTORBOARD_SESSION, else find_repo plus live), delete bin/board's Live class, and route every live/
> join through Repo, one module group per commit, with the grep as the gate. find_repo must never
> return the Atlas root. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T09. subjects.py: two kinds, no registry

- **Machine:** Mac.
- **Depends:** T03a.
- **Files:** board/tutorboard/subjects.py (new), board/tutorboard/atlas.py, board/tutorboard/course/config.py,
  board/tutorboard/colibri.py, board/tutorboard/manuscript.py, board/test/subjects.py (new).
- **Do:**
  - Every non-dot directory directly under `courses/` is a course and under `projects/` a project. No
    marker file. `research/` and `practice/` read as projects until T29.
  - `all()` returns records `{id, kind, slug, name, root}`; `find(ident)` matches only against `all()`
    by qualified id, slug or root; a qualified id that no longer exists falls back to its basename
    (shim, removed in T55); `kind_of(path)`; `root()` is the parent of `board/`, from this file's path.
  - `read_config` returns `name`, `phi` (true, false or absent), `check`, `relay`, and ignores
    `stance`, `aim` and `subtitle`.
  - `atlas.workspaces`, `find`, `family_of` and `identify` become shims over subjects with an unchanged
    record shape for their importers. T50 deletes atlas.py.
  - `colibri.WORKSPACE` and `manuscript.WRITER` resolve by slug.
- **Accept:**
  - `all()` lists the 8 subjects with kinds; an empty `projects/X` appears.
  - `atlas.workspaces()` output is unchanged on the real tree.
  - In a fixture where `research/PSYCH-ASR` moved to `projects/PSYCH-ASR`, `find('research/PSYCH-ASR')`
    resolves the new one. The suite is green.
- **Prompt:**

> You are executing T09 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T09 section; nothing else. Write subjects.py (all, find, kind_of, root) with no registry and
> no marker, reduce read_config to name, phi, check and relay, and turn atlas.py's lookups into shims
> with an unchanged record shape. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T10. One git module

- **Machine:** Mac.
- **Depends:** T08.
- **Files:** board/tutorboard/gitops.py (new), board/tutorboard/lesson/git.py, board/tutorboard/jobs.py
  (`commit_alone`), board/tutorboard/gitsync.py (folded in and deleted), board/bin/tutor (`pull_vendor`),
  board/scripts/save-and-push.sh, board/scripts/ship.sh, board/scripts/tool.sh and
  board/scripts/catch-up.sh (deleted), tests beside.py, beside_lesson.py, catchup.py (deleted), shipped.py.
- **Do:** gitops has three functions and one helper.
  - `commit(root, paths, message, refuse=None)`: named paths only, no trailers. `refuse(paths)` may
    return a reason to refuse; T38b uses it for held paths.
  - `push(root)`: fetch, rebase or merge, push. `GIT_TERMINAL_PROMPT=0`, a timeout, never forced.
  - `pull(root)`: fast-forward only, refused during a rebase, merge or cherry-pick and on a detached
    HEAD. After any pull that moved a gitlink under `vendor/`, run
    `git submodule update --init -- vendor`, so the Mac's vendor checkouts stay clean. The cluster
    relay is the only machine that bumps vendor pointers.
  - Delete both inline git fallbacks (lesson/git.py, `jobs.commit_alone`). save-and-push.sh becomes a
    thin CLI over gitops. Delete tool.sh and catch-up.sh with test/catchup.py.
  - Leave relay.py's cluster sync semantics and holds alone; T38c deletes them.
- **Accept:**
  - Outside gitops.py and relay.py (and holds.py until T38c), no Python file runs `git commit` or
    `git push`.
  - test/beside.py proves a save in a throwaway repo never commits Atlas.
  - In a bare-remote fixture, a save pushes, and a pull that moves a vendor gitlink leaves
    `git status --porcelain` empty. The suite is green.
- **Prompt:**

> You are executing T10 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T10 section; nothing else. Write gitops.py with commit (named paths, refusal hook), push
> (never forced) and pull (fast-forward, guarded, vendor submodule update), fold gitsync into it,
> delete the inline fallbacks, tool.sh and catch-up.sh, and thin save-and-push.sh. Keep every caller's
> pathspec exactly. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T11. move-residue.sh and a job_env.sh that never recreates a data root

- **Machine:** Mac. The script runs on both machines at cutover.
- **Depends:** T09, T03b.
- **Files:** board/scripts/move-residue.sh (new), board/test/move_residue.py (new),
  research/PSYCH-ASR/slurm_jobs/lib/job_env.sh.
- **Do:** `move-residue.sh <old> <new> [--apply]`, a dry run by default.
  - Refuse unless `<new>` holds tracked files (`git ls-files <new>` is non-empty) and both paths are on
    one filesystem (device ids: `stat -c %d` on Linux, `stat -f %d` on macOS).
  - List `<old>`'s leftover entries by name only (`find <old> -mindepth 1 -maxdepth 1`) and move each
    with `mv -n`. Refuse on any collision, naming it, and move nothing.
  - Rewrite the old absolute prefix in `.env` path values, printing only the changed key names.
  - Remove emptied directories, including `research/` and `practice/` once empty. Never list below a
    directory named `phi`.
  - Print a log of every move, so a rollback can reverse it.
  - job_env.sh exits non-zero with a `RELAY:` line when `PSYCH_ASR_DATA` does not exist, so a missing
    data root is never recreated empty.
- **Accept:**
  - A temp ignored `phi/` and `.env` move, and the old directory is gone.
  - Cross-device and collision cases move nothing. The dry run changes nothing.
  - Non-path `.env` values stay byte-identical. The suite is green.
- **Prompt:**

> You are executing T11 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T11 section; nothing else. Write move-residue.sh: dry run by default, same-filesystem renames
> only, names only, collisions refused, .env path prefixes rewritten, never listing under phi. Make
> job_env.sh refuse a missing data root. Test it on temp trees only. Meet every Accept line, integrate
> by 4.2, and report by 4.11.

### Phase 2: sessions, one server, one runner

#### T12. Session store: new, end, delete

- **Machine:** Mac.
- **Depends:** T08, T09, T10.
- **Files:** board/tutorboard/sessions.py (new), board/tutorboard/course/repo.py,
  board/tutorboard/lesson/state.py, board/tutorboard/sittings.py (`_shown`), board/bin/board
  (`session new|show|end|delete`, `hw`), board/test/sessions.py (new).
- **Do:**
  - `sessions.new(title=None)` creates `sessions/<YYYYMMDD-HHMMSS>/` (suffix `-2` on a clash) with
    `session.json` = {id, title, subject: null, mode: "teach", opened, ended: null, writeup: null,
    seen: 0, code: null, view: "board"} and the layout of section 2. It never touches another session.
  - `Repo(root, session_dir)` serves a session: root is the bound subject's root, or the Atlas root
    while unbound. `Repo.state()` reads session.json and exposes the legacy `hw` key when `writeup`
    points at a homework set, so `board hw` works on the session's writeup. Readers tolerate missing
    legacy keys (`chapter`, `aim`, `kind`, `stance`, `thread`).
  - `end(id)` sets `ended` and commits, through gitops, the bound subject's TUTOR.md and every artifact
    whose doc.json lists this session (an empty list until T31). Nothing else ends a session.
  - `reopen(id)` clears `ended`. `delete(id)` moves the directory to
    `~/.local/share/tutor-board/trash/<stamp>/`.
  - `sittings._shown` walks `sessions/*/session.json` (ended sessions plus their subject) instead of
    `live/archive`, so the meeting gather survives.
  - `/sessions/` is ignored and the audit refuses it (T03b). Verify both here.
- **Accept:**
  - new, then a card, then a slate page, then a second `new`: both sessions keep every file, and
    `next_turn_id` continues in the first. Only `end` sets `ended`.
  - `git add -f sessions/x/cards/0001.md` is refused by the pre-commit hook in a scratch clone.
  - The meeting gather's session walk reads a fixture ended session. The suite is green.
- **Prompt:**

> You are executing T12 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T12 section; nothing else. Write sessions.py (new, end, reopen, delete to the trash) with
> session.json as specified, make Repo serve a session directory, add `board session`, and repoint
> sittings._shown at sessions. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T13. Subject create, bind and file

- **Machine:** Mac.
- **Depends:** T12.
- **Files:** board/tutorboard/subjects.py (`create`), board/tutorboard/sessions.py (`bind`, `file`),
  board/bin/board (`bind <subject> [--create] [--phi yes|no]`, `file <upload> [materials|<relpath>]`),
  board/test/sessions.py, board/test/subjects.py.
- **Do:**
  - `bind(session, subject)` validates against `subjects.all()`, sets `subject`, and appends a
    non-waking `[bind] <subject>` line. It files nothing (D21).
  - `--create` slugifies the name. It refuses an existing slug, `..`, absolute paths and anything
    outside `courses/` and `projects/`. It writes tutorboard.json: courses get `"phi": false`;
    projects get `"phi": true` or `false` from `--phi` (the iPad asks "patient data?"; the CLI refuses
    a project without `--phi`). A `"phi": true` project also gets a `.gitignore` with `/phi/`,
    `/results/` and `.env`. It writes a TUTOR.md skeleton with the four section headings of section 2.
    One gitops commit holds all of it.
  - `file(session, upload, dest)` moves a file from the session's `uploads/` into the bound subject:
    `materials/` by default, or a relative path inside the subject. It refuses anything that leaves
    the subject, refuses an unbound session, and moves that upload's ink keys from the session's
    annotations to `<subject>/.ink/`, re-keyed by the new path.
- **Accept:**
  - `bind courses/Test --create` on a fixture makes one commit; `git check-ignore -q
    projects/New/phi/x` succeeds right after `bind projects/New --create --phi yes`.
  - `--create` refuses `../x`, `/abs` and `research/x`.
  - `file` moves an upload and its ink; the old keys are gone and the new ones load. The suite is green.
- **Prompt:**

> You are executing T13 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T13 section; nothing else. Add bind (validated, non-waking line, no filing), subject creation
> (slug rules, phi from the owner's answer, the PHI ignore stanza, TUTOR.md skeleton, one commit) and
> `board file` with ink re-keying. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T14. import_live: each workspace's current live/ becomes one open session

- **Machine:** Mac. The cutover runs it for real.
- **Depends:** T12, T05c.
- **Files:** board/tutorboard/sessions.py (`import_live`), board/scripts/import-live.py (new CLI),
  the live/ stanzas in .gitignore files of research/TRD-EHR, research/PSYCH-ASR,
  projects/libr-local-llm, projects/Paper-Writer, practice/Algo-Solutions and board/.gitignore,
  practice/Algo-Solutions/live (`git rm -r`), board/test/import_live.py (new).
- **Do:**
  - `import-live.py --atlas <root> --workspace <dir> --subject <post-merge id> [--dry-run]` imports one
    workspace and appends every move to a manifest (JSON lines, `{"from", "to"}`).
    `--reverse <manifest>` restores the original tree. The subject id is the post-merge one
    (`research/X` and `practice/X` become `projects/X`); ink goes to `<atlas>/<subject id>/.ink/`.
  - Destination of every live/ entry:

    | live/ entry | destination |
    | --- | --- |
    | state.json (may be missing) | session.json: title `<subject name>: <chapter, hw or session>`, else `<subject name>: imported`; mode `do` when stance is do, else teach; `writeup` = the bound homework source when `hw` is set |
    | .seen.json | `seen` in session.json |
    | cards/, slate/, answers/, text/, turns.jsonl, .turnseq | same names in the session |
    | inbox/messages.jsonl | same, read marks kept, so an unread message is answered after cutover |
    | inbox/uploads/ | uploads/ |
    | annotations/, card records (numeric names) | annotations/ |
    | annotations/, document records (`doc-*` .json, .png, .gone) | `<subject>/.ink/` |
    | annotations/*.dir.png and directions/ | not migrated (D15); the live tar keeps them |
    | NEXT.md, handoffs/*.md | one `note` card titled "Carried over" appended to cards/, so the recap carries it |
    | hw.json, tikzcache/, paper/, push.json, .board.json, board.log, BRIEF.md, TEACHING.md | dropped |
    | marked/ | `<subject>/materials/marked/` |
    | export.json | export.json in the session |
    | jobs.reported, jobs.jsonl, missions/ | `jobs.migrate_state` (T05c) into `<subject>/relay/state/` |
    | agent.json | agent.json with state idle and `owed` kept |
    | cost.jsonl, agent.log | same names |
    | archive/ | left for the caller, which tars it (D9) and then removes it |
    | anything else | `imported/` in the session, named in the output |
  - A live/ with no cards, no turns and no messages produces no session.
  - In imported card text, rewrite links of the old grammar (`#/w/<family>/<ws>/card/NNNN`) for this
    workspace to `#/s/<session id>/card/NNNN`.
  - Write `sessions/.imported.json`: `{old workspace id: session id}`. T23's link redirect uses it.
  - Overhaul side: delete the live/ stanzas from the listed .gitignore files and `git rm -r` the 56
    tracked files under practice/Algo-Solutions/live. The cutover copies them into a session first.
- **Accept:**
  - On copies of Galois-Theory, Probability and TRD-EHR from live-dirs.tgz: one open session each,
    with equal card count, equal turns, the same unread message count and the same `owed`.
  - TRD-EHR's missing state.json imports. Probability's handoffs/ lands as a "Carried over" card.
  - `board hw status` in the Galois session resolves ch07.
  - `--reverse` restores the copy: `diff -r` against a pristine copy is empty. The suite is green.
- **Prompt:**

> You are executing T14 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T14 section; nothing else. Write import_live and board/scripts/import-live.py with a manifest
> and --reverse, following the destination table exactly. Remove the workspace live/ stanzas and
> untrack Algo-Solutions' live/. Test only on copies extracted from live-dirs.tgz, never the real
> live/. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T15. Mode: teach or do

- **Machine:** Mac.
- **Depends:** T12.
- **Files:** board/tutorboard/course/config.py (STANCES through `aim_for`, KINDS through `kind_for`,
  `family_aim`, `sitting_kind`, per-kind agents), board/tutorboard/sense.py, board/tutorboard/brief.py,
  board/tutorboard/runner/turn.py (`doing_now`), board/tutorboard/server/routes/lesson.py (`/mode`;
  the review, walk and make branches of `/session`), board/bin/board (`board mode teach|do`; `aim`,
  `--kind`, `--aim`, `--stance`, `open --review/--walk/--make` deleted), board/tutorboard/writeups.py,
  board/test/mode.py (new; replaces aiming.py, everykind.py, onthread.py).
- **Do:**
  - session.json `mode` is `teach` or `do`. It changes only by `board mode`, POST `mode`, or the
    tutor obeying "do it". There is no inference path to `do`. TRD-EHR's and Paper-Writer's
    `"stance": "do"` no longer apply.
  - sense.py has one TEACH paragraph and one DO paragraph. In teach mode the tutor picks the method
    from the conversation and TEACHING.md: lesson, homework set, walkthrough, drill or review.
  - Papers and decks are actions, not modes. POST `/handover` (one doing step) stays.
  - A mode change appends one transcript turn and one inbox line and archives nothing.
- **Accept:**
  - `git grep -n 'AIM_KIND\|KIND_SENSE\|aim_for\|kind_for\|family_aim\|stance_for' -- board` is empty.
  - POST mode `do` changes session.json, leaves cards untouched, and the next brief carries DO.
  - `doing_now` is true for `do` and for the handover signal; a do turn gets the doing timeout.
  - The suite is green.
- **Prompt:**

> You are executing T15 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T15 section; nothing else. Collapse aim, kind, stance and session kinds into session.json
> mode teach|do with no inference to do, one TEACH and one DO paragraph, `board mode`, and a mode route.
> Delete the old axes with their suites and write test/mode.py. Meet every Accept line, integrate by
> 4.2, and report by 4.11.

#### T16. Prefix routing, the session registry, and the two-session harness

- **Machine:** Mac.
- **Depends:** T12, T06a.
- **Files:** board/tutorboard/server/{app,handler}.py, board/tutorboard/paths.py, board/test/routing.py
  (new), board/test/serving.py (rewritten).
- **Do:**
  - One port from config `port`, default 8778. serve.py takes `--port` and `--atlas` for tests.
  - A request under `/s/<id>/...` has the prefix stripped. A registry builds `Repo(subject root or
    Atlas root, session dir)` and a Hub on first use, and drops both after 10 minutes without an SSE
    client. Route functions keep their signatures; they receive the session's repo.
  - Unprefixed routes are listed explicitly in one table in handler.py: `/`, `/static/*`, `/sw.js`,
    `/manifest.webmanifest`, icons, `/health`, `/sessions.json`, `/sessions/new`, `/subjects.json`,
    `/notices.json`, `/library` and its data routes with `?subject=`, and every route T17 classifies as
    cross-subject. Any other unprefixed request is 404.
  - Ink keys `card/*` go to the session; `doc/*` go to `<subject>/.ink/`.
  - test/routing.py drives every GET and POST route with two sessions bound to different subjects and
    asserts no cross-session read or write. T17 extends it module by module.
- **Accept:**
  - One listener. `/s/A/board` and `/s/B/board` serve their own cards.
  - test/routing.py passes for the routes migrated so far and lists the rest as pending for T17.
  - The suite is green.
- **Prompt:**

> You are executing T16 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T16 section; nothing else. Add the /s/<id>/ prefix, a lazy session registry with idle drop,
> one explicit table of unprefixed routes, ink key routing, and test/routing.py, the two-session
> harness. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T17. Route migration, module by module

- **Machine:** Mac.
- **Depends:** T16.
- **Files:** board/tutorboard/server/routes/{lesson,writing,saving,library,machines,pages,taking}.py,
  board/test/routing.py.
- **Do:** one commit per module, in the order lesson, writing, saving, library, machines, pages, taking.
  - Enumerate every route with a grep of each module's `get` and `post`. Classify each as session
    (prefixed) or cross-subject (unprefixed), and record the class in a comment table at the module top.
  - Cross-subject routes, listed explicitly: `/library`, `/library.json`, `/library/view/*`,
    `/library/feedback`, `/library/ledger/*`, `/library/results.json`, `/library/stamp` (all with
    `?subject=`); `/meeting`, `/meeting/view`, `/meeting/deck.json`, `/meeting/pdf`,
    `/meeting/direction`; `/notes`, `/notes/what`; `/sittings`, `/sittings/items`, `/sittings/deck`,
    `/sittings/decks`; `/writeup/scopes`; `/default-agent`; `/colibri`; `/news`, `/missions`,
    `/mission`, `/elsewhere`, `/atlas.json`, `/courses.json`, `/switch`, `/seen` (until their deletion
    tasks); `/health`.
  - Every route that writes another subject's inbox (library `[revise]`/`[rework]`, meeting asks,
    `sittings.py` deck dispatch at about line 1186, meeting.py at about 566 and 682) calls one function,
    `runner_route(subject, line)`, defined here as a stub that writes the target subject's newest open
    session inbox, else creates a session bound to that subject. T21 replaces the stub with the runner.
  - Session routes: `/board.json`, `/events`, `/say`, `/text/save`, `/handover`, `/mode`, `/session`,
    `/archive`, `/dismiss-finish`, `/slate/*`, `/annotate/*`, `/upload`, `/push`, `/export`,
    `/export/shot`, `/hw/build`, `/writeup`, `/writeup/seen`, `/view/*`, `/download/*`, `/doc/*`,
    `/result/*`, `/figure/*`, `/answers/*`, `/tikz/*`, and the rest the grep finds.
- **Accept:**
  - test/routing.py drives every route of every module with two sessions and finds no cross-session
    read or write. A library feedback, a meeting ask and a deck ask each land in the right session.
  - No route reads `self.server.repo` except through the registry. The suite is green.
- **Prompt:**

> You are executing T17 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T17 section; nothing else. Migrate every route module to the session registry, one module per
> commit, classify each route as session or cross-subject, and route every write into another subject's
> inbox through one runner_route stub. Extend test/routing.py until it covers every route. Meet every
> Accept line, integrate by 4.2, and report by 4.11.

#### T18. TikZ and page caches; serve.py refuses Slurm

- **Machine:** Mac.
- **Depends:** T16.
- **Files:** board/tutorboard/server/tikz.py, board/tutorboard/course/paper.py, board/serve.py,
  board/tutorboard/server/app.py, tests that cover TikZ and paper pages.
- **Do:**
  - One TikZ worker caches at `sessions/.tikz/`, keyed by a hash of the source plus the subject's macros.
  - PDF page PNGs cache at `~/.cache/tutor-board/pages/<digest>/`.
  - serve.py exits non-zero when `jobs.has_slurm()` is true or `TUTOR_SLURM=1`.
- **Accept:**
  - Two sessions in different subjects share one TikZ cache and get the right macros.
  - `TUTOR_SLURM=1 python3 board/serve.py --port 0` exits non-zero. The suite is green.
- **Prompt:**

> You are executing T18 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T18 section; nothing else. Move the TikZ cache to sessions/.tikz keyed by source plus macros,
> the page cache to ~/.cache/tutor-board/pages, and make serve.py refuse a Slurm host. Meet every
> Accept line, integrate by 4.2, and report by 4.11.

#### T19. The tick carries the session only

- **Machine:** Mac.
- **Depends:** T17.
- **Files:** board/tutorboard/server/hub.py, board/tutorboard/lesson/state.py,
  board/tutorboard/server/routes/lesson.py (`GET /subject.json`), board/web/board.js (null-safe reads,
  delta apply, older-cards fetch), board/test/hub.js.
- **Do:**
  - `build()` reads only: session.json, the newest 40 cards, turns, the unread count, slate, drafts,
    agent, writeup status, and the subject's macros.
  - After the first payload, pushes carry deltas: `{"cards_changed": [...], "cards_removed": [...]}`
    plus changed top-level keys. `GET /s/<id>/cards?before=<n>` serves older cards on demand.
  - `GET /s/<id>/subject.json` carries only what survives: homework sets, results, jobs and colibri.
    Payload keys for map, plan, reading, direction, news and missions become null now (D27).
  - The brief handles `subject: null` by telling the tutor to ask what the session is for.
- **Accept:**
  - With `os.walk` and `glob` patched to raise during `build()`, a payload still builds.
  - A 500-card fixture session renders each push in under 300 ms in jsdom; the payload stays under a
    fixed size.
  - Median `build()` time on a Galois copy, before and after, is in the commit message. The drawer
    fills on open. The suite is green.
- **Prompt:**

> You are executing T19 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T19 section; nothing else. Slim build() to the session, send the newest 40 cards then deltas,
> serve older cards and /subject.json (surviving data only) on demand, and make board.js null-safe.
> Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T20. Client routing

- **Machine:** Mac.
- **Depends:** T17, T06b.
- **Files:** board/web/{board,slate-core,inkkeep,shot,library,home}.js, board/web/board.html,
  board/web/slate.html, board/web/sw.js, and the JS suites that eval these files (adopt.js, typed.js,
  chain.js and others).
- **Do:**
  - `BASE` is the `/s/<id>` prefix, or empty outside one. One `api()` helper makes every
    session-scoped fetch. `EventSource(BASE + "/events")`.
  - slate-core takes its state and save URLs from options.
  - `renderMarkdown` prefixes leading-slash `/result/`, `/doc/`, `/figure/`, `/answers/` and `/slate/`
    URLs with `BASE`. Static assets stay absolute.
  - Per-course localStorage keys become per-session.
  - sw.js maps navigations to `/s/*/board` and `/s/*/slate` onto the cached shell pages, so an offline
    session URL shows the shell or the unreachable page.
- **Accept:**
  - jsdom loads `/s/A/board`: every request is under `/s/A/` except `/static/*`, and
    `![x](/result/r1)` renders `/s/A/result/r1`.
  - Offline navigation to `/s/X/board` shows the shell or the unreachable page (node test).
  - On a rehearsal server (port 8779, a Galois copy), a card renders and ink, slate and typed answers
    save under the session. The suite is green.
- **Prompt:**

> You are executing T20 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T20 section; nothing else. Make every client fetch session-scoped through BASE and api(),
> pass slate URLs as options, prefix markdown URLs, key localStorage per session, and map session
> navigations to the cached shell in sw.js. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T21. The in-process runner

- **Machine:** Mac.
- **Depends:** T17, T15.
- **Files:** board/tutorboard/runner/service.py (new), board/tutorboard/runner/loop.py,
  board/tutorboard/server/app.py, board/tutorboard/server/routes/lesson.py (`/say`),
  board/tutorboard/server/routes/writing.py (slate send), board/tutorboard/server/spawn.py,
  board/bin/board (`write` POSTs `/s/<id>/poke`; new `check`), board/bin/tutor (`cmd_cost`),
  .githooks/pre-commit, board/test/runner.py (new), board/test/hanging.js, board/test/agents.py.
- **Do:**
  - Queueing: one FIFO per session; concurrency from config (default 2). Persist `owed` in the
    session's agent.json before each turn.
  - Turn: cwd is the Atlas root. Set `TUTORBOARD_SESSION`, `TUTORBOARD_TURN=1` and
    `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1`. A fresh process per turn; never `--continue`, because
    every session shares the cwd. Inbox paths in prompts are absolute. Prompts name
    `board/TEACHING.md`; the per-workspace copy is no longer made.
  - Non-waking inbox lines (`"wake": false`) never enqueue; the next turn's prompt includes them.
  - Startup recovery kills a surviving process group recorded in agent.json, then re-enqueues `owed`.
  - The wrap-up turn runs only on `POST /s/<id>/end`. Keep `report_owed`'s repair of half-written cards.
  - Replace T17's `runner_route` stub: the newest open session bound to the subject, else a new
    session bound to it titled `<subject name>: <ask>`; enqueue the line.
  - `board check` runs the bound subject's tutorboard.json `check` through `config.clean_check`, so
    do turns stay inside the `board *` allowlist.
  - The DO paragraph says: never edit files under `board/` in the main checkout; make a worktree under
    `/Users/mikeyferguson/Developer/Atlas-wt/` and merge. The pre-commit hook refuses a commit that
    touches `board/` when `TUTORBOARD_TURN` is set and the commit is in the main worktree
    (`git rev-parse --git-dir` equals `--git-common-dir`).
  - `tutor cost` reads `sessions/*/cost.jsonl`.
  - Delete `tutor headless`, `board wait` and spawn's tutor start and stop.
- **Accept:**
  - No `tutor headless` or `board wait` starts. `/say` to provider spawn is under 300 ms (logged).
  - TERM mid-turn, then restart: the owed message is answered once, with no duplicate card and no
    wrap-up row. Two sessions sending at once are both answered; a third queues.
  - A do turn in an Algo-Solutions fixture runs `board check` with no permission refusal (fake provider).
  - One real turn on a Probability copy, on a test server at port 8779, answers with a card.
  - The suite is green.
- **Prompt:**

> You are executing T21 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T21 section; nothing else. Build the in-process runner: per-session FIFO, concurrency 2,
> owed persisted and recovered, fresh process per turn at the Atlas root with TUTORBOARD_SESSION and
> TUTORBOARD_TURN, wrap-up only on End. Replace the runner_route stub, add `board check`, add the hook
> refusal of turn commits to board/ in the main worktree, repoint tutor cost, and delete tutor headless
> and board wait. One real turn is allowed, on a Probability copy at port 8779. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T22. Hearing and freshness inside the server; one LaunchAgent

- **Machine:** Mac.
- **Depends:** T21, T05c.
- **Files:** board/tutorboard/server/app.py, board/tutorboard/cluster.py, board/tutorboard/stamp.py,
  board/scripts/launchd/tutor-board.plist (new), board/install.sh, board/scripts/ship.sh,
  board/bin/tutor (`restart`, `watch`, `agent start` refuse), board/tutorboard/jobs.py (`PULL_BUSY`,
  `PULL_IDLE`, `PULL_SLACK`, `pull_interval` deleted), board/tutorboard/holds.py (`poll_seconds`
  deleted), board/test/hearing.py.
- **Do:**
  - The cluster thread starts only when `TUTORBOARD_CLUSTER=1`. Every 20 s it runs
    `git ls-remote origin main 'refs/heads/code/*'` (`GIT_TERMINAL_PROMPT=0`, 10 s timeout), and runs
    `gitops.pull` only when main differs from HEAD. Record a pull failure in
    `~/.local/state/tutor-board/pull.json`.
  - Hearing: `jobs.hear` (and `holds.wake` until T38c) feed `cluster.wake(subject, session, line)`.
    With a session: reopen it if ended, append to its inbox, enqueue. With no session: append to
    `sessions/.notices.jsonl` and start no turn (D16). `/notices.json` serves the notices.
  - Freshness thread: once `stamp.tree()` differs from the loaded stamp, `git status --porcelain board/`
    is clean (committed code only), and no turn runs, exit 0.
  - Plist: label `tutor-board`, absolute interpreter path resolved by install.sh, `KeepAlive` true,
    `ThrottleInterval` 10, `TUTORBOARD_CLUSTER=1`, a PATH with /opt/homebrew/bin, stdout and stderr to
    `~/.local/state/tutor-board/server.log`. The server logs its stamp at boot.
  - install.sh installs only `tutor-board` and boots out `tutor-board.tutor-watch` and
    `tutor-board.tutor-pull` when present. Do not run it against the real system; T59 does.
  - ship.sh's restart step becomes `launchctl kickstart -k gui/$(id -u)/tutor-board`. `tutor restart`,
    `tutor watch` and `tutor agent start` refuse and name the LaunchAgent (T49 deletes them).
- **Accept:**
  - With a fake remote equal to HEAD there is no pull; when it differs there is one pull.
  - A report wakes an open filing session, reopens an ended one, and becomes a notice when it has no
    session.
  - Editing board/tutorboard mid-turn and committing: the turn finishes, then the server exits 0.
    An uncommitted edit triggers no exit.
  - `plutil -lint` passes. A test label `tutor-board.rehearsal` on port 8779 against a copy relaunches
    after a clean exit with the same interpreter, then is booted out. The suite is green.
- **Prompt:**

> You are executing T22 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T22 section; nothing else. Add the gated cluster thread (ls-remote, pull on change, hearing
> through cluster.wake with D16 routing and notices), the freshness thread (committed changes only,
> idle only), the tutor-board plist with KeepAlive true, and an install.sh that installs only it.
> Repoint ship.sh's restart and make the old tutor restart commands refuse. Rehearse only under a test
> label on port 8779. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T23. The home start screen

- **Machine:** Mac.
- **Depends:** T20, T15, T21.
- **Files:** board/web/home.{html,js,css} (rewritten; home.js at most 1,000 lines), board/web/address.js,
  board/web/sw.js, tests door.js and sittingsheet.js (deleted), board/test/home.js (new), board/test/link.js.
- **Do:**
  - Home shows, top to bottom:
    - Continue: open sessions, each with subject, last card title and new cards since `seen`;
    - New session;
    - notices from `/notices.json` (D16), each dismissible;
    - Courses and Projects lists, each row opening that subject's page (the library for that subject),
      each list with "+ new" (a project asks "patient data?");
    - Past sessions, read-only;
    - Notes, Annotate a PDF, Meeting deck (wired in T40 and T39b);
    - Settings: theme, face, default assistant.
  - Addresses are `#/s/<id>/...`. A parse-only shim turns `#/w/<family>/<ws>/card/NNNN` into the
    imported session from `sessions/.imported.json`, then that card. Without a match it lands on the
    subject page with a note that the link is from an archived sitting. T55 deletes the shim.
- **Accept:**
  - `/` makes no request to `/switch` or `/atlas.json` (jsdom fetch interception).
  - A new session opens unbound; creating "Linear Algebra" as a course adds it to the list and commits.
  - `#/w/Courses/Galois-Theory/card/0003` resolves to that card in the imported Galois session.
  - No visible control calls a route that 404s. The suite is green.
- **Prompt:**

> You are executing T23 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T23 section; nothing else. Rewrite home as the start screen (Continue, New session, notices,
> Courses and Projects with + new, Past sessions, the three actions, Settings) and add the #/s/ address
> grammar with a parse-only redirect for old links through sessions/.imported.json. Meet every Accept
> line, integrate by 4.2, and report by 4.11.

#### T24. The session header

- **Machine:** Mac.
- **Depends:** T23.
- **Files:** board/web/board.{html,js,css}, board/test/link.js, board/test/modes.js.
- **Do:**
  - The header holds four controls: the subject chip (pick or create; "unbound" until bound), the
    teach/do toggle, the Make menu (Writeup, Deck, Paper; wired in T33), and End.
  - End posts `/s/<id>/end` after a second tap.
  - Hide the old kind strip, map, contents, shelf and elsewhere buttons. T51 deletes their code.
- **Accept:**
  - Binding from the chip updates it without a reload; the toggle flips session.json `mode`.
  - The header shows at most four session controls (link.js count updated). The suite is green.
- **Prompt:**

> You are executing T24 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T24 section; nothing else. Build the four-control session header and hide the old strip and
> map controls. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T25. Uploads, and delete from the iPad

- **Machine:** Mac.
- **Depends:** T24, T13.
- **Files:** board/web/board.{js,html,css} (Materials drawer), board/web/home.js, board/web/library.js,
  board/tutorboard/lesson/uploads.py, board/tutorboard/server/routes/writing.py,
  board/tutorboard/server/routes/library.py, board/tutorboard/server/multipart.py,
  board/tutorboard/server/handler.py, board/tutorboard/sessions.py, board/tutorboard/subjects.py,
  board/test/library.py, board/test/sessions.py.
- **Do:**
  - Uploads (D21): an XHR uploader with progress and visible errors. Bodies stream to disk with a 1 GB
    cap for uploads only. Every upload lands in the session's `uploads/` and appends a non-waking
    `[uploaded] <name> (<size>)` line. No per-upload question.
  - Delete routes, each resolving its target through discovery, never from a client path:
    - `POST /subject/delete {subject, typed}`: `typed` must equal the slug. Refused (409, with the
      reason) unless tutorboard.json at HEAD literally says `"phi": false`, and while an open session is
      bound to it, a session has `code` set for it, or a request under it has no terminal report.
      Ignored residue moves to the trash with the rest. One gitops commit `git rm`s the tracked files.
    - `POST /material/delete {subject, name}` after a second tap: trash, no commit for ignored files.
    - `POST /session/delete {id}` after a second tap: trash.
  - Trash is `~/.local/share/tutor-board/trash/<stamp>/`; the server prunes entries older than 30 days
    at startup.
- **Accept:**
  - A 150 MB upload shows progress; server RSS does not grow by the file size; a forced 500 shows an
    error line; the upload writes no waking message.
  - Deleting a fixture subject makes one commit and removes it from `/subjects.json`. `../x` gets 400.
    An open session gets 409. A fixture with `"phi": true`, or with no `phi` key, gets 409.
  - The suite is green.
- **Prompt:**

> You are executing T25 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T25 section; nothing else. Build streamed uploads into the session's uploads/ with progress,
> errors and a non-waking line, and the subject, material and session delete routes with typed or
> second-tap confirmation, the D23 phi refusal, trash with 30-day pruning, and one commit per subject
> delete. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T26. The cutover script and its rollback, rehearsed on copies

- **Machine:** Mac.
- **Depends:** T22, T25, T14.
- **Files:** board/scripts/cutover.sh (new), board/scripts/cutover.py (new, stdlib helper),
  board/test/cutover.py (new).
- **Do:** `cutover.sh --plan | --rehearse <scratch> | --run | --rollback <manifest>`. Every step
  writes `~/Archive/atlas-migration/<date>/cutover-manifest.json`: the pre-merge sha, each path moved
  (from, to), the tailscale capture, labels booted out. `--run` aborts and rolls back on any failed check.
  1. **Preflight.** `git -C $G status --porcelain --untracked-files=no` is empty; record main's sha as
     PRE. Each `courses/X` repo is clean. `git -C $G status --porcelain research practice` is empty.
     The course trees match overhaul's `courses/` under the excludes in
     `board/scripts/fold-excludes.txt` (written by T27; an `rsync -n --checksum` comparison); any drift
     aborts. At least 5 GB free.
  2. **Stop the old system**, in this order:
     - `launchctl bootout gui/$(id -u)/tutor-board.tutor-watch` and `.../tutor-board.tutor-pull`
       first, because the watch loop revives boards and the pull agent writes inboxes;
     - for each `tutor headless` daemon, wait until its live/agent.json says listening with `owed` null
       (10 min timeout, then abort), then `kill -KILL` its process group and its `board wait` child.
       SIGKILL skips the old wrap-up turn, which would otherwise spend a model turn;
     - SIGTERM every `serve.py --root` board, then SIGKILL leftovers after 10 s;
     - `pgrep -f 'serve.py|tutor headless|board wait|tutor-pull|tutor watch'` prints nothing.
  3. **Snapshot.** Save `tailscale serve status --json`. Re-bundle Atlas and both course repos with
     `git bundle create --all` and verify. Tar each workspace's `live/archive/` and each course's
     `transcripts/` (D9, D11). Tar each course directory whole, `.git` included, for rollback.
  4. Append `/sessions/` and `.ink/` to `$G/.git/info/exclude`, so nothing new is visible before the merge.
  5. **Import.** For each workspace with a live/, run T14's import-live.py from the overhaul code with
     the post-merge subject id. Remove `live/archive/` (tarred) and the emptied live/. Restore every
     tracked file the import moved, such as practice/Algo-Solutions/live, with `git -C $G checkout --`,
     so status is clean again; the merge then deletes them. Remove the empty stray `$G/live/`.
  6. **Course repos.** Move each `courses/X/.git` to `<archive>/courses-git/X.git`. Remove
     `courses/X/transcripts` (tarred). The remaining files are ignored, and the merge overwrites them
     with identical tracked copies (`git merge` overwrites ignored files by default).
  7. **Merge.** `git -C $G -c core.hooksPath=$G/.githooks merge --no-ff -m "overhaul: one server, sessions, courses and projects" overhaul`.
     A conflict aborts the merge and rolls back.
  8. **Residue.** Move every untracked leftover `git status --porcelain` shows under `courses/` to
     `<archive>/pre-fold/`. For each `research/X` and `practice/X`, run
     `move-residue.sh <old> projects/X` dry, then `--apply`, and record its log. Run `uv sync` in
     projects/TRD-EHR, PSYCH-ASR, libr-local-llm and Paper-Writer. Then run, when present,
     `migrate-artifacts.py --apply-ink $G` and `--rebuild $G` (T34). `git status --porcelain` is empty.
  9. **Install.** `bash board/install.sh`. Remove every old `tailscale serve` mapping (HTTPS and each
     `--tcp` forward), then publish HTTPS to 127.0.0.1:8778 (check `tailscale serve --help` for the
     installed syntax). `tailscale serve status --json` lists only 8778.
  10. **Start and prove.** Bootstrap `tutor-board`; `/health` answers; `pgrep -f serve.py | wc -l` is 1;
      `launchctl list | grep -c tutor-board` is 1; `/sessions.json` lists each imported session. An
      unread message in an imported session is answered; else post one `/say` to the Probability
      session ("cutover check: reply with one short card") and wait up to 5 minutes for a new card.
      No duplicate card and no wrap-up row appear. `python3 board/test/run.py --guards` passes in $G.
  11. **Push** main with gitops, never forced. Nothing before this step reaches GitHub.
  - `--rollback` (valid only before the push): bootout `tutor-board`; restore the tailscale capture;
    `git -C $G reset --hard PRE`; restore each course directory from its tar; reverse the import
    manifest and the move-residue logs; restore `live/archive/` from its tar; remove the info/exclude
    lines; re-bootstrap the two old agents and wait until the three old boards answer `/health`.
  - `--rehearse <scratch>` runs steps 1 to 10 against a copy: a `git clone` of $G, copies of every
    live/ and course directory, small dummy `.venv` and `.lake` dirs, a bare clone as origin, a fake
    provider, a test label on port 8779, fake old daemons (sleep processes with the old names), and a
    printed tailscale plan instead of changes. It then runs `--rollback` and compares.
- **Accept:**
  - `--rehearse` passes: the unread `/say` queued in the Probability copy is answered (fake provider);
    no handoff row and no duplicate card; one label and one serve.py; no live/ remains; a meeting deck
    builds end to end with the fake provider; `ship.sh` afterwards leaves one serve.py.
  - The rehearsal's rollback restores the copy: `diff -r` against a pristine copy, ignoring logs and
    caches, is empty, and the fake old boards answer.
  - The suite is green.
- **Prompt:**

> You are executing T26 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T26 section; nothing else. Write board/scripts/cutover.sh and cutover.py with --plan,
> --rehearse, --run and --rollback, steps in exactly the listed order, a manifest for every move, and
> abort-plus-rollback on any failed check. Never run --run: T59 does. Rehearse on a full copy with fake
> daemons, a fake provider, a bare origin and port 8779, then roll the copy back and prove it
> identical. Meet every Accept line, integrate by 4.2, and report by 4.11.

### Phase 3: content

#### T27. Fold the courses into Atlas

- **Machine:** Mac + cluster runbook lines.
- **Depends:** T03b, T09.
- **Files:** .gitignore, courses/Galois-Theory/** and courses/Probability/** (new tracked content),
  board/tutorboard/audit.py, board/test/tracked.py, board/scripts/scaffold.sh and
  board/scripts/split-textbook.sh (moved from the courses), board/bin/board (`textbook` subcommand).
- **Do:**
  1. **Preflight.** In the main checkout, read-only: `git -C courses/X status --porcelain` is empty
     for both courses, and `git -C courses/X rev-parse HEAD` equals HEADS.txt in
     `~/Archive/atlas-migration/2026-10-07/`. If HEAD moved past HEADS.txt, bundle the course again
     into `~/Archive/atlas-migration/<date>/X.bundle` and verify it.
  2. **Copy** each course from the main checkout into the worktree with rsync, excluding `.git/`,
     `live/`, `transcripts/`, `textbook/`, `chapters/*/reading/`, `chapters/*/lectures/`, any
     `assignment*` path, `build/`, `rescued-from-mac/`, `scripts/`, `Makefile`, `.githooks/`, and every
     `*.pdf`. Keep the exclude list in `board/scripts/fold-excludes.txt`; T26's drift check reuses it.
  3. **Review.** Print every copied file whose extension is not `.tex`, `.md`, `.json`, `.tsv`, `.sty`,
     `.cls`, `.bib` or `.txt`, and every PNG outside a `handwritten/` directory. Judge each against D1:
     the owner's own work stays (D3), anything authored by someone else is removed and its pattern
     added to the excludes. Put the reviewed list and the decision per entry in the commit message.
  4. **One commit:**
     - drop `/courses/*/` from the root .gitignore (T03b's D1 rules now apply);
     - cut each course `.gitignore` to only what the root lacks;
     - set `"phi": false` in each course's tutorboard.json;
     - in audit.py, delete the courses-invisible and course-must-have-.git rules; keep refusing
       textbook/, reading/, lectures/ and `assignment*` shapes;
     - `git add courses/`.
     Subject: `courses: Galois-Theory and Probability are tracked content, snapshot of <sha> and <sha> (T27)`.
  5. Move one copy of `scaffold.sh` and `split-textbook.sh` to board/scripts/, taking the course
     directory as an argument. Add `board textbook split <course>` and `board textbook scaffold <course>`,
     so a tutor turn runs them inside the `board *` allowlist.
- **Accept:**
  - `git ls-files -s courses | grep -c ^160000` is 0. `git ls-files courses | grep -ci '\.pdf$'` is 0.
  - The tracked count per course equals the count the copy printed.
  - tracked.py refuses a forced `courses/X/textbook/a.pdf` and a forced
    `courses/X/chapters/ch01/homework/assignment-sheet/p.png`.
  - In the worktree, `git -C courses/Galois-Theory rev-parse --show-toplevel` prints the worktree root.
  - `board hw status` (or `board writeup status` after T32) on a Galois session copy resolves ch07, and
    its writeup builds with `board build`.
  - `board textbook split` on a fixture course with a 3-chapter PDF and chapters.tsv writes the
    chapter readings. Every tracked file is under 25 MB. The suite is green.
- **Runbook:**
  ```
  # course clones on the cluster: bundle, then move aside (they are the only copy of any cluster-side work)
  mkdir -p ~/atlas-migration/courses.pre-fold
  for c in ~/Atlas/courses/*/; do [ -d "$c.git" ] || continue; n=$(basename "$c"); git -C "$c" bundle create ~/atlas-migration/$n.bundle --all && git bundle verify ~/atlas-migration/$n.bundle && mv "$c" ~/atlas-migration/courses.pre-fold/; done
  ls ~/atlas-migration    # expect one verified bundle per moved clone
  ```
- **Prompt:**

> You are executing T27 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T27 section; nothing else. Copy both courses from the main checkout (read-only) into your
> worktree without .git, live, transcripts, third-party material or PDFs; review every unusual file
> against D1 yourself; and fold them in one commit with the ignore, audit and tutorboard.json changes.
> Move one shared copy of scaffold.sh and split-textbook.sh into board/scripts behind `board textbook`.
> Never edit the main checkout. Meet every Accept line, integrate by 4.2, append the Runbook lines by
> 4.9, and report by 4.11.

#### T28. Purge the private-course machinery; delete atlas.json

- **Machine:** Mac.
- **Depends:** T27.
- **Files:** atlas.json (deleted), board/bin/tutor (`adopt_private`, hear-pass per-repo loop),
  board/bootstrap.sh, scripts/setup.sh, board/scripts/setup-cluster.sh, board/tutorboard/relay.py
  (`spaces`, `relay_opts` sync), board/tutorboard/jobs.py (own-repo refusal), board/tutorboard/atlas.py,
  board/tutorboard/worktree.py, board/tutorboard/meeting.py (`repo_of`), board/tutorboard/lesson/git.py,
  board/tutorboard/sittings.py, board/tutorboard/course/config.py, .githooks/commit-msg (comment),
  board/test/tracked.py, hearing.py, beside.py, truthful.py, and every test fixture that writes atlas.json.
- **Do:**
  - Remove every code path that treats a course as its own repository. ai-config stays a private
    nested repo: `bootstrap.sh` and `adopt_private` clone or adopt it from the hard-coded URL
    `https://github.com/Pirate-Hunter-Zoro/ai-config.git` (D18).
  - Delete atlas.json. List its readers with `git grep -n atlas.json -- board scripts` and give each
    its value from code or delete it: `subjects.root()` derives from board/; families are gone;
    relay sync is always off (its code goes in T38c); `config.family_aim` is gone (T15) or returns the
    default.
  - `relay.spaces` includes every subject. `jobs.file_request` refuses any subject that contains a
    nested `.git`, generically.
  - The pull pass makes no clone attempt for anything but ai-config.
- **Accept:**
  - `git grep -n -i 'private repositor\|its own repositor\|courses/\*/' -- board scripts .githooks .gitignore`
    returns only ai-config lines.
  - atlas.json is gone and `git grep -n 'atlas\.json' -- board scripts` is empty, except tests that
    assert its absence.
  - `bash board/bootstrap.sh --no-clone` in the worktree reports no missing course.
  - A fake-git pull pass records no clone attempt. `relay.spaces` includes both courses. The suite is green.
- **Prompt:**

> You are executing T28 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T28 section; nothing else. Delete every code path that treats a course as its own
> repository, keep ai-config adoption with its URL hard-coded, and delete atlas.json after repointing
> every reader. Do not edit README prose; record stale references for T57. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T29. Merge research/ and practice/ into projects/

- **Machine:** Mac + cluster runbook lines.
- **Depends:** T28, T11, T05c.
- **Files:** research/* and practice/* (moved to projects/), .gitignore, board/tutorboard/subjects.py,
  Brewfile, projects/Paper-Writer/PROMPT_TEMPLATE.md, projects/Paper-Writer/tests/test_jobspec.py,
  projects/libr-local-llm/bin/coli-code, projects/libr-local-llm/bin/ds-code,
  research/TRD-EHR/scripts/rebuild-packet.sh, the TRD-EHR paper1 packet sources, board code comments and
  fixtures that assert real paths, board/test/tracked.py messages, board/scripts/phi-probe.sh (new);
  in ai-config (separate commit, pushed): policy/phi.py, adapters/claude_code.py,
  workspaces/algo-solutions.allow, workspaces/lean-theorem-proving.allow, README.md.
- **Do:**
  1. **ai-config first.** Read `$G/ai-config/policy/phi.py`, `adapters/claude_code.py`,
     `workspaces/*.allow` and `README.md`, and classify every `research/` and `practice/` hit as a
     pattern or prose. Make each pattern match both the old and the new path (for example
     `(research|projects)/PSYCH-ASR`); update the `.allow` paths to `projects/`. Run
     `bash $G/ai-config/scripts/test.sh`, commit in ai-config, and push it. Only then continue.
  2. **Move** in the worktree:
     `git mv research/TRD-EHR research/PSYCH-ASR practice/Algo-Solutions practice/Lean-Theorem-Proving projects/`.
     Each subject's own .gitignore moves with it.
  3. Add legacy root ignores `/research/` and `/practice/`, so residue left at the old paths on either
     machine stays invisible to git after a pull. subjects.py drops the legacy directories.
  4. Update path text in the listed files and in board comments and fixtures that assert real paths.
  5. **Manuscript links (D1).** Grep the paper1 packet sources (`manuscript.md`,
     `parts/manuscript/*.md`, `cover_letter.md`, `tripod_ai_checklist.md`, `supplement.md`,
     `reserve/*.md`) for `github.com/Pirate-Hunter-Zoro`. The code link points at
     `https://github.com/Pirate-Hunter-Zoro/TRD-EHR`, which returns 404. Repoint it at
     `https://github.com/Pirate-Hunter-Zoro/Atlas/tree/main/projects/TRD-EHR`, and repoint any
     `research/TRD-EHR` path in a link. Leave `feedback/*/before.md` and `after.md` alone: they record a
     past round. Rebuild the packet with `scripts/rebuild-packet.sh` and commit the rebuilt .docx files.
     List every changed sentence in the report for the owner.
  6. `board/scripts/phi-probe.sh <path>` exits 0 only when `leaving` and the policy refuse that path.
  7. In the worktree, run `uv sync` and each subject's `check` for TRD-EHR, PSYCH-ASR, libr-local-llm
     and Paper-Writer, and `go test ./...` for Algo-Solutions. Lean's build waits for T59, where `.lake`
     exists. Algo-Solutions' known failure (`leetcode/totalbeauty` imports it never uses) is the
     owner's to fix; report it.
- **Accept:**
  - `git log --follow` crosses the move for one file per moved subject.
  - research/ and practice/ hold nothing tracked. `bash ai-config/scripts/test.sh` is green.
  - `phi-probe.sh projects/PSYCH-ASR/phi/x` and `phi-probe.sh research/PSYCH-ASR/phi/x` both exit 0.
  - Piping a Read of `projects/PSYCH-ASR/phi/x` (the hook's JSON shape) into
    `~/.claude/hooks/block-phi.py` is refused.
  - tracked.py finds `projects/PSYCH-ASR/phi` and `projects/TRD-EHR/results` by discovery in a fixture.
  - The manuscript's code link is the Atlas URL. The suite is green.
- **Runbook:**
  ```
  cd ~/Atlas
  for d in research/* practice/*; do [ -d "$d" ] || continue; bash board/scripts/move-residue.sh "$d" "projects/$(basename "$d")"; done            # dry run, read it
  for d in research/* practice/*; do [ -d "$d" ] || continue; bash board/scripts/move-residue.sh "$d" "projects/$(basename "$d")" --apply; done
  test ! -e research && test ! -e practice && echo gone                        # expect: gone
  test -d projects/PSYCH-ASR/phi && echo phi-present                          # existence only, never list it
  git status --porcelain --untracked-files=all -- projects/PSYCH-ASR/phi projects/TRD-EHR/results | wc -l   # expect 0
  bash board/scripts/phi-probe.sh projects/PSYCH-ASR/phi/x && echo refused     # expect: refused
  python3 board/test/tracked.py                                                # expect green
  bash scripts/setup.sh                                                        # re-sync each subject's .venv after the move
  ```
- **Prompt:**

> You are executing T29 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T29 section; nothing else. First make ai-config's policy, hook and allow files match both old
> and new paths, test, commit and push ai-config. Then git mv the four subjects into projects/, add the
> legacy ignores, update path text, repoint the manuscript's dead code link at the Atlas URL and rebuild
> the packet, add phi-probe.sh, and run each subject's check. Meet every Accept line, integrate by 4.2,
> append the Runbook lines by 4.9, and report by 4.11.

#### T30a. RULES.md and TUTOR.md in the brief; `board memo`

- **Machine:** Mac.
- **Depends:** T29, T15, T05c.
- **Files:** board/tutorboard/memo.py (new), board/tutorboard/brief.py, board/tutorboard/sense.py
  (`where_sense`), board/tutorboard/carry.py (deleted), board/bin/board (`memo <section>`; `note`
  deleted), board/tutorboard/runner/prompts/*.md, board/test/memo.py (new), board/test/tokens.py.
- **Do:**
  - `board memo <section>` reads text on stdin and replaces or appends that section of the bound
    subject's TUTOR.md ("Where things are", "Now", "Open decisions", "Done recently"). It refuses a
    result over 800 words, naming the count. It never writes RULES.md.
  - The brief reads: a pointer to `board/TEACHING.md`, RULES.md at HEAD (`git show HEAD:<path>`) with a
    flag line when the working tree differs, and TUTOR.md. It no longer reads NEXT.md, HANDOFF.md,
    DIRECTION.md, threads.json or AI_INSTRUCTIONS.md sections. `where_sense` never says "read README
    first"; subject READMEs never enter the brief (D13).
  - Delete `board note`, carry.py's NEXT.md logic, and every prompt line that asks for a note (D22).
  - tokens.py becomes a brief size budget: a fixture brief is at most 14,000 characters.
- **Accept:**
  - A fixture brief contains its RULES.md text from HEAD and flags an uncommitted RULES.md edit.
  - `board memo Now` with 900 words is refused; with 100 words it lands in that section only.
  - `git grep -n 'NEXT\.md\|board note' -- board` is empty, except import_live's "Carried over" mapping.
  - The suite is green.
- **Prompt:**

> You are executing T30a of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T30a section; nothing else. Add memo.py and `board memo <section>` with the 800-word cap,
> make the brief read RULES.md at HEAD (flagging drift) and TUTOR.md, and delete NEXT.md, board note
> and carry.py. Turn tokens.py into a size budget. Meet every Accept line, integrate by 4.2, and report
> by 4.11.

#### T30b. Migrate contracts, handoffs, plans and threads into RULES.md and TUTOR.md

- **Machine:** Mac.
- **Depends:** T30a.
- **Files:** board/scripts/migrate-memory.py (new), every subject's RULES.md and TUTOR.md (new);
  in ai-config (separate commit, pushed first): policy/LOCAL-MODELS.md (new) and the README pointer.
- **Do:**
  - **ai-config first.** Move PSYCH-ASR's local-model exception text, now in
    projects/PSYCH-ASR/AI_INSTRUCTIONS.md, into `ai-config/policy/LOCAL-MODELS.md`, repoint
    ai-config's README at it, run its tests, commit and push. Only then continue.
  - `migrate-memory.py <subject>` writes:
    - **RULES.md** (at most 300 words) from the AI_INSTRUCTIONS.md section "rules that do not bend" and
      any subject-specific hard rule. PSYCH-ASR's data-fence list goes here. Omit RULES.md where no
      rule exists.
    - **TUTOR.md** (at most 800 words, the four sections) from HANDOFF.md, DIRECTION.md, PLAN.md,
      PROGRESS.md, threads.json (open tasks as `- [ ]` lines, open decisions as bullets), and the open
      items of `PSYCH-ASR_TODO.txt` and `LOCAL-LLM_TODO.txt` (D13).
  - TRD-EHR's HANDOFF.md holds the owner's edits of 2026-10-07 (committed at 40f13c66). Carry every one.
  - Review each subject's output yourself against its sources (D26). Put a per-subject summary of what
    was kept and what was condensed in the commit message.
  - Do not delete the sources here; T30c does.
- **Accept:**
  - The script asserts every open threads.json task text appears in that subject's TUTOR.md.
  - Every TUTOR.md is at most 800 words; every RULES.md at most 300.
  - PSYCH-ASR's brief contains its data-fence rule. A spot check of five TRD-EHR HANDOFF.md items
    finds each in TUTOR.md. The suite is green.
- **Prompt:**

> You are executing T30b of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T30b section; nothing else. First move PSYCH-ASR's local-model exception into
> ai-config/policy/LOCAL-MODELS.md and push ai-config. Then write migrate-memory.py and produce RULES.md
> and TUTOR.md for every subject from its contracts, handoffs, plans, threads and TODO files, carrying
> every open task and the owner's TRD-EHR edits. Review the output yourself. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T30c. Delete the old planning layer; holds refuse until T38

- **Machine:** Mac.
- **Depends:** T30b.
- **Files:** board/tutorboard/handoff.py, board/tutorboard/direction.py, board/tutorboard/course/plan.py
  (deleted with tests direction.py, plan.py, chapter.py, keeping.py), board/bin/board (`handoff`,
  `direction`, `step` deleted; `push` prefix), board/tutorboard/holds.py, board/tutorboard/meeting.py
  (gather inputs), board/tutorboard/jobs.py (contract checks), and the subject files: AI_INSTRUCTIONS.md
  (every subject), HANDOFF.md (Algo-Solutions, libr-local-llm, TRD-EHR), DIRECTION.md (TRD-EHR,
  PSYCH-ASR, Galois-Theory), PLAN.md (Galois-Theory), PROGRESS.md (Algo-Solutions), threads.json
  (TRD-EHR, PSYCH-ASR, libr-local-llm), PSYCH-ASR_TODO.txt, LOCAL-LLM_TODO.txt.
- **Do:**
  - Delete the listed modules, commands and files.
  - `board push` commit prefixes become `<subject slug>:`; the thread-id enforcement goes.
  - Holds freeze: `board hold`, `send`, `release` and `coach` refuse with "replaced by `board code`
    (T38)" instead of reading threads.json. T38c deletes them.
  - meeting.py's gather reads TUTOR.md diffs and ended sessions; with neither it still builds a brief.
  - map.py must tolerate a missing threads.json (it falls back to chapters or code) until T50.
- **Accept:**
  - No subject keeps any of the deleted files.
  - `board hold` refuses with the message above and no traceback.
  - A meeting gather over a period spanning the migration still reports progress. The suite is green.
- **Prompt:**

> You are executing T30c of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T30c section; nothing else. Delete handoff, direction and plan with their commands and suites,
> and every subject's contract, handoff, direction, plan, progress, threads and TODO file. Make holds
> refuse cleanly, make push prefixes subject slugs, and keep the meeting gather working. Meet every
> Accept line, integrate by 4.2, and report by 4.11.

### Phase 4: features

#### T31. Artifacts

- **Machine:** Mac.
- **Depends:** T07, T12.
- **Files:** board/tutorboard/artifacts.py (new), board/tutorboard/writeups.py,
  board/tutorboard/course/library.py, board/tutorboard/sessions.py (`end` paths),
  board/tutorboard/server/routes/library.py (`/doc/delete`), board/web/library.js, board/test/artifacts.py (new).
- **Do:**
  - `create(subject, title, session, ext)` makes `<subject>/docs/<slug>/` with doc.json =
    {title, source, sessions, asked_at} (D20). `place(dir, source, title)` writes doc.json in place in
    an existing tree. Also `list`, `get`, `status`, `delete`.
  - Type: a `.tex` whose class is beamer is a deck, another `.tex` an article, a `.md` a paper.
  - Status: "writing" until the source and its built output are both newer than `asked_at`; "failed"
    when the asking session's turn ended and 2 quiet minutes passed with no output; else "done".
  - `delete` moves the directory to the trash, removes that document's `.ink` keys, and `git rm`s the
    tracked files in one gitops commit. `POST /doc/delete {subject, id}` after a second tap; a path
    under a fence returns 403.
  - library.py lists doc.json artifacts first, legacy documents second with unchanged ids, and
    `materials/*.pdf` as readable materials.
  - `writeups.waiting` reads doc.json files. Delete the `library.stamp` diffing.
  - `sessions.end` commits the artifacts whose doc.json lists the session.
- **Accept:**
  - create gives "writing"; a source plus `board build` gives "done"; delete removes the directory and
    its ink and makes one commit.
  - Legacy ids do not change. The payload builds with `library.stamp` patched to raise.
  - A delete under a fenced path returns 403. The suite is green.
- **Prompt:**

> You are executing T31 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T31 section; nothing else. Write artifacts.py with doc.json = {title, source, sessions,
> asked_at}, type from extension and class, status from mtimes, and delete to the trash with ink
> removal and one commit. Make the library list artifacts, legacy documents with unchanged ids, and
> materials. Replace the library-stamp diffing. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T32. Writeups for any session

- **Machine:** Mac.
- **Depends:** T31, T15.
- **Files:** board/tutorboard/course/homework.py, board/tutorboard/artifacts.py,
  board/tex/writeup.tex.in (new), board/bin/board (`writeup new|add|build|status`; `hw` kept as an
  alias until T55), board/tutorboard/sense.py, board/tutorboard/lesson/state.py,
  board/tutorboard/course/paper.py, board/TEACHING.md (lines 780-860),
  courses/*/latex/templates/ (deleted), board/test/homework.py, board/test/writing_up.py.
- **Do:**
  - In teach mode, every agreed answer to a tutor-posed question goes in with
    `board writeup add <label>`, then the PDF is rebuilt. The statement and agreed argument come on
    stdin. The handwriting PNG is copied into `handwritten/`. Code and pseudocode go in verbatim;
    nothing needs shell-escape.
  - The first add creates the artifact: the bound assignment file in place when the session's writeup
    is a homework set, else `docs/<session-slug>/writeup.tex`. An unbound session refuses, so the tutor
    binds first.
  - Walkthroughs and code sessions are no longer excluded from writeups.
  - One template, board/tex/writeup.tex.in, replaces `SCAFFOLD`, `PLAIN_PREAMBLE` and both course
    templates; it uses coursemacros when the subject has them.
  - TEACHING.md's writeup section names `board writeup`.
- **Accept:**
  - Two answers in a libr-local-llm fixture session produce a writeup.pdf with both.
  - A Galois copy still writes into `chapters/ch07-.../homework/ch07-homework.tex`, and
    `board hw status` works through the alias.
  - A build failure reaches the board's banner. An Algo-Solutions teach brief names `board writeup`.
  - The suite is green.
- **Prompt:**

> You are executing T32 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T32 section; nothing else. Add `board writeup new|add|build|status` over artifacts, with
> handwriting filed and code verbatim, one template, course sets written in place, and `board hw` as an
> alias. Remove the walkthrough and code exclusions and update TEACHING.md's writeup section. Meet every
> Accept line, integrate by 4.2, and report by 4.11.

#### T33. A deck or a paper on demand, from any session

- **Machine:** Mac.
- **Depends:** T31, T24, T21.
- **Files:** board/tutorboard/server/routes/{library,machines}.py, board/tutorboard/scopes.py (deleted),
  board/tutorboard/sense.py, board/tutorboard/runner/prompts/*.md, board/web/board.js (Make menu),
  board/web/home.js (subject page actions), board/test/revising.py.
- **Do:**
  - `POST /s/<id>/artifact {make: "deck"|"paper", about?}` creates the doc.json; the server picks the
    slug and path. It queues a `[writeup]` turn whose line names the exact source, says a deck is a
    beamer `.tex` and a paper is Markdown, and says to run `board build`. The default scope is this
    session. From a subject page the router of T21 picks the session.
  - Delete `/writeup/scopes`, scopes.py and `#docnew`. Keep the signal name `writeup`, so timeouts and
    repair still apply.
- **Accept:**
  - A paper request creates doc.json with source `<slug>.md`, and its line names `board build`. A deck
    names `.tex` and beamer.
  - A fake turn that writes the source and builds flips the strip from writing to done; the paper
    yields a .docx. The suite is green.
- **Prompt:**

> You are executing T33 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T33 section; nothing else. Add POST /s/<id>/artifact for a deck or paper, create the
> doc.json first, queue a [writeup] turn naming the source and `board build`, wire the Make menu and
> subject page, and delete scopes. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T34. Migrate existing documents and their ink

- **Machine:** Mac. T59 runs the ink and rebuild steps for real.
- **Depends:** T32, T29.
- **Files:** board/scripts/migrate-artifacts.py (new), board/scripts/artifact-moves.json (new, generated),
  board/tutorboard/course/library.py, board/tutorboard/course/homework.py (`compiled_pdf`),
  board/tutorboard/server/routes/writing.py, projects/TRD-EHR/homework/*, projects/TRD-EHR/writeups/deck-*.
- **Do:** `migrate-artifacts.py` with four modes.
  - `--plan`: prints every tree move and every ink key rename (old library id to new), changes nothing.
  - `--apply-tree`, run here in the worktree and committed: `git mv` TRD-EHR's `homework/*` and
    `writeups/deck-*` into `docs/<slug>/` with doc.json; write doc.json in place for hand-made trees
    (PSYCH-ASR/docs, libr-local-llm/docs, TRD-EHR paper1-* and paper2-*) and every course homework set;
    move feedback/ and ledger files with their document; untrack `writeups/deck-*/*.out` and built PDFs
    in moved directories; write the key map to `artifact-moves.json`.
  - `--apply-ink <atlas root>`: renames `.ink` files (`.json`, `.png`, `.gone`) by the key map. Ink
    lives only in the main checkout, so T59 runs this after import.
  - `--rebuild <atlas root>`: runs `board build` on every course writeup source and asserts a PDF
    beside each. Built PDFs are ignored, so T59 runs this in the main checkout.
  - `homework.compiled_pdf` drops its `build/` search.
- **Accept:**
  - `--plan` lists every path and key and changes nothing.
  - On a fixture made with T14's import from live-dirs.tgz copies: after `--apply-ink`, the stroke count
    is unchanged and each moved document shows its old ink through the library view.
  - TRD-EHR's 2026-09-29 round, including `placed-ce5b4dff5e1839e9.json`, opens intact.
  - `--rebuild` on the worktree builds every course writeup. The suite is green.
- **Prompt:**

> You are executing T34 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T34 section; nothing else. Write migrate-artifacts.py with --plan, --apply-tree (run and
> committed here), --apply-ink and --rebuild (run by T59 on the main checkout). Move TRD-EHR's homework
> and decks into docs/, place doc.json in hand-made trees and course sets, and keep every ink key
> reachable through the recorded map. Prove it on fixtures from live-dirs.tgz. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T35. Decouple Paper-Writer

- **Machine:** Mac.
- **Depends:** T07.
- **Files:** board/tutorboard/manuscript.py (deleted), board/bin/board (`cmd_make`),
  board/tutorboard/server/routes/library.py (Paper-Writer branches of `_revise` and `rework_refused`),
  board/tutorboard/course/library.py (`NOT_DOCUMENTS` moves in; `made: paper-writer` tagging goes),
  board/test/writing_up.py, board/test/revising.py, projects/Paper-Writer/service/ (systemd units deleted).
- **Do:**
  - First check that TRD-EHR's feedback rounds never went through the factory: grep
    `paper1-trd-prediction/feedback/` and `review/` for factory job markers. Report what you find.
  - Delete the dead drop-folder integration and the systemd units. Paper-Writer stays an ordinary
    project (D8). Its README's cluster instructions are T57's.
- **Accept:**
  - `git grep -n 'manuscript\.' -- board/tutorboard board/bin` is empty.
  - A revise note on TRD-EHR's manuscript.md starts a `[revise]` turn told to run `board build`
    (fake provider). The suite is green.
- **Prompt:**

> You are executing T35 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T35 section; nothing else. Check that TRD-EHR's feedback rounds never used the factory, then
> delete manuscript.py, cmd_make, the Paper-Writer branches in the library routes and the systemd units.
> Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T36. One ink core, one toolbar

- **Machine:** Mac.
- **Depends:** T20.
- **Files:** board/web/ink-core.js (new), board/web/slate-core.js, board/web/annotate.js,
  board/web/annbar.js, board/web/board.{html,js}, board/web/library.html, board/web/meeting.html,
  board/web/slate.html, board/web/sw.js, tests clip.js, feedback.js, chain.js, adopt.js, address.js.
- **Do:**
  - Move `Slate.ink` (catmullRom, trust, SMOOTH, MIN_STEP, RESAMPLE) into `InkCore`. slate-core and
    annotate both read it. Load ink-core.js before annotate.js on every page.
  - Delete annotate.js's raw-polyline fallback, so missing geometry is a load error.
  - annbar.js is the only toolbar. Delete the static `#annbar` markup in board.html, keeping the ids
    board.js reads, or move paintAnnTools to the annbar API.
  - Change only where the geometry comes from and how the toolbar mounts; stroke handling stays.
- **Accept:**
  - Library strokes come out densified (jsdom). `id="annbar"` is gone from board.html.
  - Nib sizes and the colour well appear on the board. The marks and clip suites are green.
- **Prompt:**

> You are executing T36 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T36 section; nothing else. Move the ink geometry into ink-core.js, delete annotate's raw
> fallback, and make annbar.js the only toolbar, touching no stroke handling. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T37. One reader, one theme, one ink kind

- **Machine:** Mac.
- **Depends:** T36.
- **Files:** board/web/reader.js (new), board/web/library.js, board/web/meeting.js, board/web/board.js
  (`openPaper` and keep-writing deleted), board/web/board.html (`#paper` deleted), board/web/typeface.js,
  board/web/board.css, board/web/home.js, board/tutorboard/proposals.py (deleted),
  board/tutorboard/server/routes/{library,machines}.py (`/library/direction`, `/meeting/direction`),
  tests paper.py, paperzoom.js, inkzoom.js, library.js, theme.js.
- **Do:**
  - `Reader.open({pagesUrl, id, title, inkKey, onClose})` on readerzoom, annotate and inkkeep. Every
    PDF view uses it. No `mode` (D15).
  - "Keep writing" becomes the marked-copy action (`/annotate/burn`).
  - D15: one ink kind. Delete the `dir:1` stroke kind, the fix/direction toggle, proposals.py and the
    direction routes. Stored strokes carrying `dir:1` load as ordinary ink; `.dir.png` files are ignored.
    "Say what's wrong" sends the marked pages to `/library/feedback`, which queues a `[revise]` turn
    through the router; the turn's line says to edit the source or write TUTOR.md, its choice.
  - Until T39b, meeting.js loses its direction mode and its marks use the same feedback path.
  - Theme: one `Typeface.theme()` on `board.theme` and `body[data-mode]`; meeting.js drops its own copy.
  - Keep `check_sources` (meeting provenance) untouched.
- **Accept:**
  - Opening a document from a card uses `Reader.open`. Old ink loads in place.
  - Every save goes through InkKeep (a failed save is retried, jsdom). One `syncSystemTheme`.
  - `git grep -n 'dir:\s*1\|proposals' -- board` is empty. The suite is green.
- **Prompt:**

> You are executing T37 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T37 section; nothing else. Extract reader.js and use it for every PDF view, make theme code
> one function, and remove direction ink completely (dir:1, the toggle, proposals.py, the direction
> routes) so "Say what's wrong" queues a revise turn. Old ink must load in place. Meet every Accept
> line, integrate by 4.2, and report by 4.11.

#### T41. Pin the commit a request runs

- **Machine:** Mac. Reaches the cluster at cutover.
- **Depends:** T05c.
- **Files:** board/tutorboard/jobs.py, board/tutorboard/relay.py, board/bin/board, board/test/jobs.py,
  board/test/relay.py.
- **Do:**
  - `file_request` stamps `commit`, the Mac's HEAD after the code push. Add the key to `REQUEST_KEYS`.
  - The cluster refuses a request whose commit HEAD does not contain (`git merge-base --is-ancestor`).
    No `follow` flag (D27).
  - Every report carries `ran_at`, the cluster's HEAD short sha. The `[job]` line says when `ran_at`
    differs from `commit`.
  - `board job` refuses while tracked files under the subject are dirty, saying "board push first".
- **Accept:** `ran_at` is always present; a non-ancestor commit is refused with that reason; a dirty
  tree files nothing. The suite is green.
- **Prompt:**

> You are executing T41 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T41 section; nothing else. Stamp each request with the pushed commit, refuse it on the
> cluster when HEAD lacks that commit, record ran_at in every report, and refuse to file over a dirty
> subject. No follow flag. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T38a. Coding sessions on the cluster: code.py and `board code`

- **Machine:** Mac (fixture only). The owner's trial is in T38c's runbook.
- **Depends:** T10, T03a, T03b, T41.
- **Files:** board/tutorboard/code.py (new; takes holds' `check_spec`, `run_check`, `check_output`,
  `relay_lines`, `crash_type`, `output_open`), board/bin/board (`code` subcommand with lazy imports),
  board/tutorboard/relay.py (held-path tolerance, code-ref pinning), board/tutorboard/jobs.py,
  board/test/code.py (new; two-clone fixture), board/test/py37.py.
- **Do:**
  - `board code <session> <paths...>` on the cluster refuses fenced paths, paths in two subjects, and
    no paths. It registers `~/.local/state/tutor-board/code/<session>.json`
    {session, subject, paths, base, last, step}.
  - Each step: after 10 s without changes under the held paths (mtime poll every 2 s), build a snapshot
    with a temporary index (`GIT_INDEX_FILE`, `read-tree`, `add -- <paths>`, `write-tree`,
    `commit-tree -p <parent>`); the parent is the previous snapshot, or HEAD for the first. Run the
    audit and `leaving.refused` over the changed paths; a refusal prints the reason and pushes nothing.
    Run the subject's check. The message holds `Step N`, `check: pass|fail`, and the sanitized output
    only where `output_open` is true. Push it to `refs/heads/code/<session>`, fast-forward only.
  - Each tick also fetches `code/<session>`. A commit the loop did not make (a vibe push from the Mac,
    D17) is applied with `git checkout <sha> -- <paths>` when the held paths are unchanged since the
    last snapshot. Otherwise it prints "both sides changed: <files>" and waits.
  - `--end` takes `relay/.lock`, commits the held paths to main as one `<subject>: <title>` commit
    through gitops (a conflict is refused with the files named), pushes main, deletes the remote ref,
    and removes the registration. `--abandon` deletes the ref and the registration only.
  - The relay tolerates registered held paths: a dirty held file never skips the pass, and an upstream
    change to one is reported "held path changed upstream" instead of overwritten.
  - A request whose session has a registered code session accepts a `commit` that is an ancestor of
    `origin/code/<session>` and whose held paths equal the working tree.
  - No `coach/<id>`, no `--ask`, no `code-diff` (D17).
- **Accept:** in a fixture with a bare origin and two clones:
  - an edit makes one snapshot on `code/S` within one tick and no commit on main;
  - check output is in the message for a `"phi": false` fixture subject and absent for `"phi": true`;
  - `--end` leaves exactly one new main commit and no `code/S` ref;
  - a relay pass with a dirty held file does not skip;
  - a commit pushed to `code/S` from the other clone lands in the cluster clone's working tree;
  - `python3 -X importtime board/bin/board code --help` imports no server or runner module;
    py37.py covers code.py. The suite is green.
- **Prompt:**

> You are executing T38a of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T38a section; nothing else. Write code.py and the cluster `board code` loop: snapshot commits
> through a temporary index onto code/<session>, audit and check per step with output only where open,
> vibe commits applied from the same ref, --end as one main commit, --abandon, and relay tolerance of
> held paths. Keep it Python 3.7-compatible. Prove it in a two-clone fixture. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T38b. The Mac hears coding sessions

- **Machine:** Mac.
- **Depends:** T38a, T22, T24.
- **Files:** board/tutorboard/cluster.py, board/tutorboard/server/app.py (cluster thread),
  board/tutorboard/gitops.py (held-path refusal), board/tutorboard/sessions.py (`code`), board/bin/board
  (`push` in a coding session), board/tutorboard/runner/prompts/*.md (`[code]` turn), board/web/board.js
  (header line), board/test/hearing.py.
- **Do:**
  - The cluster thread watches `refs/heads/code/*`. On a changed sha it fetches, records
    `session.json.code = {ref, sha, paths, step}`, and appends a waking `[code] step N: <subject line>` to
    that session, reopening it if ended. A deleted ref clears `code`.
  - The `[code]` prompt tells the tutor to read `git diff <previous>..<sha>` itself and answer on a card.
  - While a session has `code` set, `gitops.commit` refuses Mac commits to its held paths on main, and
    `board push` from that session pushes to `code/<id>` instead (D17).
  - The header shows the exact cluster command `board code <id> <paths>` to copy.
- **Accept:** in a fixture with the server at port 8779, `TUTORBOARD_CLUSTER=1` and a bare origin:
  - a pushed `code/S` step wakes S within one tick;
  - a Mac commit to a held path on main is refused; `board push` in S lands on `code/S`;
  - deleting the ref clears `code`. The suite is green.
- **Prompt:**

> You are executing T38b of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T38b section; nothing else. Make the cluster thread hear code/* refs and wake the session with
> a [code] step line, refuse Mac main commits to held paths, send a coding session's pushes to its ref,
> and show the cluster command in the header. Use a fixture origin only. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T38c. Delete holds and relay sync

- **Machine:** Mac + cluster runbook lines.
- **Depends:** T38b.
- **Files:** board/tutorboard/holds.py (deleted), board/tutorboard/relay.py (`sync_spaces` through
  `sync_commit`, `_unwind`, `_synced`), board/tutorboard/jobs.py (`relay_opts` sync), board/bin/board
  (`hold`, `send`, `release`, `coach` deleted), any tracked `relay/holds/` and `relay/coach/`,
  board/test/syncing.py and board/test/holds.py (deleted).
- **Do:** delete holds and relay sync; T38a already moved the parts that survive into code.py. In
  run.py's `--guards`, code.py replaces holds.py.
- **Accept:** `git grep -n 'holds\.\|sync_spaces\|sync_commit' -- board` is empty. The suite is green.
- **Runbook:**
  ```
  # one coding-session trial, Algo-Solutions (go test): start a session on the iPad bound to projects/Algo-Solutions,
  # copy the command its header shows, then on the cluster:
  cd ~/Atlas && board code <session-id> leetcode/<a-problem-dir>
  # edit one file there; within about a minute the iPad shows a [code] step card
  board code <session-id> --end
  git log -1 --oneline; git ls-remote origin 'refs/heads/code/*' | wc -l   # expect one new commit and 0 refs
  ```
- **Prompt:**

> You are executing T38c of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T38c section; nothing else. Delete holds.py, relay sync and the hold, send, release and coach
> commands with their suites. Meet every Accept line, integrate by 4.2, append the Runbook lines by 4.9,
> and report by 4.11.

#### T39a. The meeting deck: one engine, in projects/Meetings

- **Machine:** Mac.
- **Depends:** T31, T30a.
- **Files:** board/tutorboard/briefs.py (new, from meeting.py and sittings.py), board/tutorboard/meeting.py
  and board/tutorboard/sittings.py (deleted or wrappers of at most 150 lines), projects/Meetings/
  (new: tutorboard.json `{"name": "Meetings", "phi": true}`, TUTOR.md skeleton), .gitignore,
  board/tutorboard/server/routes/{library,machines}.py, board/web/home.js, board/bin/board (`meeting`),
  tests meeting.py and sittings.py (merged into briefs.py), deck.js, sittingsheet.js.
- **Do:**
  - One commit classifier, one figure snapshot, one brief writer, one landing judge
    (`artifacts.status`). Keep `check_sources` and `internal_names`. Delete `page_map`, `\meetingws` and
    meetingws.sty (D15).
  - Inputs: commits and ended sessions in the period, plus TUTOR.md diffs.
  - Flow: `POST /meeting {since, items}` writes the brief and asks a `[writeup]` turn through the router
    in a session bound to projects/Meetings. The deck is the artifact `projects/Meetings/docs/meeting/`;
    `meeting.tex` is tracked; the brief, figures and PDF are ignored (root rules). Asking again replaces
    it and clears its ink; git history keeps the old one.
  - Delete the "how far back" sheet and `/notes`, `/notes/what` and `/sittings*`. Home has one meeting
    action. The `/meeting` pages stay until T39b.
- **Accept:**
  - The classifier is defined once (`git grep -n "lesson complete" -- board/tutorboard` shows one definition).
  - A brief with no TUTOR.md history builds. Asking twice leaves one doc.json and one meeting.tex.
  - `git check-ignore -q` holds for the deck's brief, figures and PDF; no `*.out` is tracked.
  - The suite is green.
- **Prompt:**

> You are executing T39a of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T39a section; nothing else. Merge meeting.py and sittings.py into briefs.py with one
> classifier, snapshot, brief writer and landing judge; create projects/Meetings ("phi": true) and make
> the deck its artifact, replaced each time; delete page_map, \meetingws and the extra meeting sheets
> and routes. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T39b. The meeting deck in the one reader

- **Machine:** Mac.
- **Depends:** T39a, T37.
- **Files:** board/web/meeting.{html,js} (deleted), board/tutorboard/server/handler.py and routes
  (`/meeting`, `/meeting/view`, `/meeting/deck.json`, `/meeting/pdf` deleted), board/web/home.js,
  board/web/library.js, board/test/meeting.py or briefs.py, deck.js.
- **Do:** home's meeting action and the library open the deck with `Reader.open`. "Say what's wrong"
  queues a `[revise]` turn on meeting.tex through the router. Delete the meeting page and its routes.
- **Accept:** the deck opens in the reader from home; a mark plus "Say what's wrong" writes feedback and
  queues one `[revise]` turn in a projects/Meetings session (fake provider); meeting.html and meeting.js
  are gone. The suite is green.
- **Prompt:**

> You are executing T39b of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T39b section; nothing else. Open the meeting deck in Reader.open from home and the library,
> route its feedback to a revise turn, and delete the meeting page and routes. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T40. The notes canvas, and annotating a PDF

- **Machine:** Mac.
- **Depends:** T37, T25.
- **Files:** board/web/{home,board,reader,slate-core}.js, board/web/slate.html, board/tutorboard/sessions.py
  (`view`), board/tutorboard/server/routes (session new with a view), board/tutorboard/course/library.py
  (uploads and materials as readable PDFs), board/tutorboard/course/burn.py, board/bin/board
  (`writeup new --md`), board/tutorboard/runner/prompts/*.md (End of a slate session), board/test/plane.js,
  board/test/library.py.
- **Do:**
  - Home "Notes" posts `/sessions/new {view: "slate", title: "Notes <date>"}` and opens
    `/s/<id>/slate`, a full-slate, multi-page view of that session's own slate pages.
  - End on a `view: slate` session queues the wrap-up turn with: transcribe the pages into
    `<subject>/docs/<session-slug>/notes.md` (`board writeup new --md`), then `board build`. When the
    session is unbound, the tutor chooses or creates the subject first, at its discretion.
  - "Annotate a PDF" (home and session menu) uploads into the session's `uploads/` (T25). An optional
    subject picker files it straight into `<subject>/materials/`. The reader then opens it. Ink ids
    derive from the file's path by the library's id rule. `board file` re-keys the ink when the tutor
    files an upload (T13).
  - "Keep a marked copy" writes `<name>-marked.pdf` beside the PDF, never over it.
  - The library lists `materials/*.pdf`; the session drawer lists `uploads/*.pdf`. The upload never
    wakes the tutor.
- **Accept:**
  - Two pages in a notes session survive a reload. End on a fixture notes session queues a wrap-up whose
    prompt names notes.md and `board build`.
  - An uploaded slides.pdf renders; ink persists across reload; the marked copy holds the ink; after
    `board file` the PDF is in materials/ and its ink follows. No waking message is written.
  - The suite is green.
- **Prompt:**

> You are executing T40 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T40 section; nothing else. Make the notes canvas a session in full-slate view whose End
> transcribes notes.md through the writeup path, and make "Annotate a PDF" an upload opened in the
> reader with marked copies beside it and ink that follows `board file`. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T42. Relay and Colibri health on the iPad

- **Machine:** Mac. Reaches the cluster at cutover.
- **Depends:** T38c, T22.
- **Files:** board/tutorboard/relay.py, board/tutorboard/cluster.py, board/tutorboard/colibri.py,
  board/tutorboard/server/hub.py, board/tutorboard/server/routes/machines.py (`/colibri`), board/bin/board
  (`brief` health line), board/web/board.js, board/web/home.js (Colibri panel), board/test/relay.py,
  board/test/hearing.py.
- **Do:**
  - status.json grows: outstanding requests per subject, and Colibri state, time left, queue length and
    current task id, all through `relay.public`. It is still committed only when a non-`at` field changes.
  - Mac health: "relay looks down" when an outstanding request has no `submitted` report 15 minutes
    after its commit. `~/.local/state/tutor-board/pull.json` failures show as "not synced: <git's words>".
  - Colibri on the Mac reads only status.json (D27). squeue stays in the relay pass.
  - A Colibri panel on libr-local-llm's subject page: file a task (through `board colibri`), the
    queue, and per-task progress from status.json and reports. Filing shows a cold-start estimate from
    the last load time the relay recorded. Warmth policy is unchanged (D6).
- **Accept:**
  - A skipping pass writes its reason; an identical pass makes no commit.
  - With a stale outstanding fixture, the payload reads down. "off" never shows while status says
    loading. A diverged fixture tree shows "not synced".
  - No absolute path or node name appears in status.json. The suite is green.
- **Prompt:**

> You are executing T42 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T42 section; nothing else. Extend status.json with outstanding requests and Colibri state,
> show relay-down, pull failures and Colibri from status.json only, and add the Colibri panel with a
> cold-start estimate. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T43. One failure fingerprint; log excerpts only where phi is false

- **Machine:** Mac. Reaches the cluster at cutover.
- **Depends:** T42.
- **Files:** board/tutorboard/relay.py, board/tutorboard/jobs.py (wrapper), board/tutorboard/code.py,
  board/cluster/lib/{relay_trap.sh,relay_hook.py,sitecustomize.py} (new home), the per-subject
  `slurm_jobs/lib` copies (two-line shims), projects/TRD-EHR/tutorboard.json and
  projects/PSYCH-ASR/tutorboard.json (`relay.fingerprint`), board/test/relayhook.py, board/test/relay.py.
- **Do:**
  - The wrapper prepends board/cluster/lib to PYTHONPATH, exports `RELAY_ROOT`, `RELAY_STAGE` and
    `RELAY_CONFIG` (the subject's `relay.fingerprint`), and prints the failure line with the checkout sha.
  - Each subject's `slurm_jobs/lib/relay_trap.sh` becomes a two-line shim sourcing the shared one. The
    duplicate relay_hook.py files go. TRD-EHR's and PSYCH-ASR's `RELAY_*` values move into tutorboard.json.
  - `relay.finish` adds `output`, `output_total` and `output_cut` from `code.check_output` only where
    `output_open` is true.
- **Accept:** an open fixture's report carries a cut, relative-path output and a `"phi": true` one
  carries none; a recipe with no `source` line still fingerprints; exactly one relay_hook.py is
  tracked. The suite is green.
- **Prompt:**

> You are executing T43 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T43 section; nothing else. Move the fingerprint library to board/cluster/lib with per-subject
> shims and config in tutorboard.json, and add sanitized log output to reports only where output_open
> is true. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T44. `board job --batch` and a 2-minute relay

- **Machine:** Mac + cluster runbook lines.
- **Depends:** T43.
- **Files:** board/tutorboard/jobs.py, board/tutorboard/relay.py (`scrontab_block` to `*/2`),
  board/bin/board, board/test/jobs.py, board/test/relay.py.
- **Do:** `board job --batch <file.json>` files many requests in one commit and one push. The scrontab
  entry runs every 2 minutes (D5). No watcher job and no poke file.
- **Accept:** a batch of 5 requests is one commit with 5 request files; `scrontab_block()` contains
  `*/2` and relay-pass.sh; `merged_crontab` still replaces only its own block. The suite is green.
- **Runbook:**
  ```
  cd ~/Atlas && python3 board/bin/relay --install
  scrontab -l | grep -c 'relay-pass.sh'     # expect 1
  scrontab -l | grep '\*/2'                 # expect the relay line
  ```
- **Prompt:**

> You are executing T44 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T44 section; nothing else. Add `board job --batch` (one commit for many requests) and set the
> relay scrontab to every 2 minutes. Meet every Accept line, integrate by 4.2, append the Runbook lines
> by 4.9, and report by 4.11.

#### T45. Readable code in cards; a read-only source viewer

- **Machine:** Mac.
- **Depends:** T03c, T20.
- **Files:** board/web/board.{js,css}, board/web/vendor/highlight/ (new), board/web/sw.js,
  board/tutorboard/server/routes/pages.py (`/source/`), NOTICE.md, board/TEACHING.md (walkthrough step 4),
  board/test/markdown.js.
- **Do:**
  - Vendor highlight.js core with Python, Go, Bash, Lean, R and SQL (D12); add its licence to NOTICE.md.
  - Code fences keep their info string. `py path#L40-58` numbers lines from 40 and adds a caption link.
    Math and tikz fences are untouched.
  - `GET /source/<path>?from=&to=` serves only git-tracked files that pass `walk.resolve` and the fence
    check, as a numbered page with the range highlighted.
  - TEACHING.md's walkthrough step says excerpts carry `path#Lx-y`.
- **Accept:** a fence over holds.py or code.py lines renders highlighted and numbered with a caption
  link; an untracked, fenced or `..` path returns 404. The suite is green.
- **Prompt:**

> You are executing T45 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T45 section; nothing else. Vendor highlight.js core with six languages and its licence,
> render code fences with path#L captions and numbering, and add the fenced, tracked-only /source
> viewer. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T46. Trace any path in Atlas; delete the vendor-tree machinery

- **Machine:** Mac.
- **Depends:** T03c, T15.
- **Files:** board/tutorboard/course/walk.py, board/tutorboard/sense.py, board/tutorboard/atlas.py,
  board/tutorboard/course/map.py, board/tutorboard/server/routes/pages.py, board/web/board.js,
  board/test/walk.py.
- **Do:**
  - `walk.resolve` falls back to the Atlas root. Units under `board/` or `vendor/` are read-only, and
    the sense says so. The basename shortcut stays subject-local.
  - Delete `ELSEWHERE`, `_elsewhere`, `tree_label`, `resolve_elsewhere`, `resolve_any`, `of_tree`,
    `/map/tree`, `atlas.trees`, `find_tree` and the tree UI.
- **Accept:** `board/tutorboard/relay.py` and `vendor/colibri/bin/coli-up` (by its shebang) resolve
  read-only; a fenced name is refused anywhere; `grep -rn 'resolve_elsewhere\|of_tree' board` is empty.
  The suite is green.
- **Prompt:**

> You are executing T46 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T46 section; nothing else. Let walk.resolve fall back to the Atlas root with board/ and
> vendor/ read-only, and delete the vendor-tree machinery. Meet every Accept line, integrate by 4.2,
> and report by 4.11.

#### T47. The brief and the recap ride in the prompt

- **Machine:** Mac.
- **Depends:** T21.
- **Files:** board/tutorboard/runner/loop.py, board/tutorboard/runner/prompts/first.md,
  board/tutorboard/brief.py (recap moved in from bin/board), board/bin/board.
- **Do:**
  - Render the brief and the recap in-process and pass them with `--append-system-prompt` for claude,
    or prepended for other providers. Guard the size: past the limit, the recap keeps the newest card
    whole and one line per earlier card.
  - The prompt says both are above and not to run `board brief` or `board recap`. The global CLAUDE.md
    stays (D7). Both commands stay for manual use.
  - Baselines: median requests, wall time and cache_write from the existing cost.jsonl files in the main
    checkout's `courses/*/live/` and `research/TRD-EHR/live/` (read-only).
- **Accept:**
  - The rendered prompt of a fixture turn contains the brief and the recap and no instruction to fetch them.
  - One real turn on a Probability copy (port 8779) uses at most 6 requests; its requests, wall time and
    cache_write are in the commit message beside the baselines. The suite is green.
- **Prompt:**

> You are executing T47 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T47 section; nothing else. Inject the brief and recap into each turn with a size guard, tell
> the model not to fetch them, keep the global CLAUDE.md, and measure one real turn against the
> cost.jsonl baselines. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T48. One provider setting

- **Machine:** Mac.
- **Depends:** T21.
- **Files:** board/tutorboard/agents/recipes.py, board/tutorboard/runner/loop.py,
  board/tutorboard/assistants.py, board/tutorboard/server/routes/machines.py (`/default-agent`),
  board/bin/tutor (`doctor`), board/test/agents.py, board/test/onlyagent.py.
- **Do:**
  - Config holds `provider` (default claude), one `fallback` (default codex) and `vision_agent`. No
    per-session override (D27).
  - Resolution: provider, else the fallback when the provider is unavailable (missing binary, missing
    key, usage limit).
  - Delete `only_agent`, `config_shadows`, the strike stand-down, the workspace `agent` key and any
    remaining per-kind agent.
  - Keep "only an in-fence model reads phi" as an explicit refusal.
  - `doctor` becomes a one-turn smoke test per provider.
- **Accept:** the resolver is under 80 lines; a limited claude falls back to codex and the card names it
  (fake providers); `/default-agent` changes the provider for the next turn without a restart. The
  suite is green.
- **Prompt:**

> You are executing T48 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T48 section; nothing else. Reduce provider choice to provider, one fallback and vision_agent,
> keep the in-fence refusal, and make doctor a one-turn smoke test. Meet every Accept line, integrate by
> 4.2, and report by 4.11.

### Phase 5: deletions

#### T49. Per-workspace server machinery; bin/tutor deleted

- **Machine:** Mac.
- **Depends:** T26, T48, T44.
- **Files:** board/tutorboard/{ports,choice,supervise,processes}.py (deleted), board/tutorboard/machines.py
  (most of it), board/tutorboard/server/routes/machines.py (`/switch`, `/courses.json`, `/atlas.json`),
  board/bin/board (`free_port`, `default_port`, `served_ports`, `recorded_ports`, `boards_serving`,
  `drop_strays`, `ts_repoint`; `vpn` reduced to status; new `pull`, `cost`, `doctor`), board/bin/tutor
  (deleted), board/serve.py (legacy `--root` mode), board/tutorboard/server/spawn.py,
  board/scripts/launchd/{tutor-watch,tutor-pull}.plist and board/scripts/tutor-pull (deleted),
  board/install.sh (no `tutor` link), board/scripts/setup-cluster.sh, tests choice.py, address.py,
  watching.py, wedged.py, waking.py, shipped.py, resume.py, and every test that still loads bin/tutor.
- **Do:**
  - Move `pull` (Atlas plus vendor submodules through gitops), `cost` (sessions/*/cost.jsonl) and
    `doctor` (T48's smoke test) into `board`. Then delete bin/tutor (D19).
  - Delete the per-workspace processes the cutover retires. The freshness thread replaces the
    ship-time restart.
  - `board/bin/relay` stays the cluster's scheduled entry; nothing on the cluster calls bin/tutor.
- **Accept:**
  - `git grep -n 'port_sequence\|chosen\.json\|ts_repoint\|/switch\|bin/tutor' -- board scripts ':!board/scripts/cutover*'`
    is empty. bin/tutor does not exist.
  - `board pull`, `board cost` and `board doctor --dry` work on fixtures. The suite is green.
- **Prompt:**

> You are executing T49 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T49 section; nothing else. Move pull, cost and doctor into board, delete bin/tutor, and
> delete ports, choice, supervise, processes, the switch and address routes, the old plists and
> tutor-pull, with their suites. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T50. The mapping layer, server side

- **Machine:** Mac.
- **Depends:** T30c, T46.
- **Files:** board/tutorboard/course/{map,symbols,threads,syllabus,review,shelf}.py (deleted),
  board/tutorboard/atlas.py (deleted), board/tutorboard/course/homework.py (gains syllabus's `chapters`
  and `opening`), board/tutorboard/spell.py, board/tutorboard/sense.py (node, thread, walk and review
  senses), board/tutorboard/brief.py, board/tutorboard/lesson/state.py, routes `/map/*`,
  `/thread/accept`, `/direction`, `/shelf.json`, board/bin/board (`thread`, `review`, `walk`, `open`,
  `archive`), tests map.py, region.py, threadmap.py, threads.py, review.py, walk.py (sitting cases), shelf.py.
- **Do:** delete the mapping layer's server code. Keep the course reader: move `syllabus.chapters` and
  `syllabus.opening` into homework.py, so `board writeup new chNN` and the book's chapter list in the
  brief still work. Repoint every atlas.py importer at subjects.py.
- **Accept:**
  - `git grep -n 'course\.map\|threads\.json\|families(\|from \.atlas\|import atlas' -- board/tutorboard board/bin`
    is empty; atlas.py is gone.
  - On a Galois copy, `board writeup new ch08` works and the brief lists the book's chapters.
  - The suite is green.
- **Prompt:**

> You are executing T50 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T50 section; nothing else. Delete map, symbols, threads, review, shelf, syllabus and atlas.py
> with their routes, commands and suites, after moving syllabus.chapters and opening into homework.py
> and repointing atlas importers at subjects. Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T51. The mapping layer and the old sitting UI, client side

- **Machine:** Mac.
- **Depends:** T24, T37.
- **Files:** board/web/board.js (shelf, kind strip, map, contents and elsewhere sections),
  board/web/board.html, board/web/board.css, board/web/gauge.js (deleted), board/web/library.html
  (`lib-map`), board/web/address.js (the redirect shim stays until T55), board/web/sw.js, tests map.js,
  mapfirst.js, shelf.js, overlap.js and plane.js (map halves), link.js, review.js, walk.js, modes.js,
  steering.js.
- **Do:** delete the client code behind the controls T24 hid. Find each section by its function names
  (`mapDraw`, `openElsewhere`, `openContents`, `openShelf`, `paintKindChooser`) rather than line numbers.
  Move any generic glass check from a deleted suite into a surviving one.
- **Accept:** board.js is under 7,500 lines; none of the five names remains; the render, send and
  annotate suites are green; the whole suite is green.
- **Prompt:**

> You are executing T51 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T51 section; nothing else. Delete the map, shelf, contents, elsewhere and kind-strip client
> code with gauge.js and their suites, keeping any generic glass check. Meet every Accept line,
> integrate by 4.2, and report by 4.11.

#### T52. Cross-board missions

- **Machine:** Mac.
- **Depends:** T42, T10.
- **Files:** board/tutorboard/missions.py, board/tutorboard/news.py, board/tutorboard/progress.py (deleted),
  board/web/mission.js (deleted), routes `/elsewhere`, `/missions`, `/mission`, `/news`, board/bin/board
  leftovers, board/tutorboard/server/spawn.py (ship, carry, release), tests elsewhere.py, notify.js
  (trimmed), carry.py if any remains.
- **Do:** delete cross-board missions. The Colibri queue already lives in colibri.py (T05c), and the
  home Continue rows report new cards per session.
- **Accept:** no `missions.`, `news.` or `progress.` call remains; a Colibri task filed in a fixture shows
  queued, working and done in T42's panel through status.json and its report. The suite is green.
- **Prompt:**

> You are executing T52 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T52 section; nothing else. Delete missions, news, progress and mission.js with their routes
> and suites, keeping the Colibri queue and panel working. Meet every Accept line, integrate by 4.2, and
> report by 4.11.

#### T53. One document inventory

- **Machine:** Mac.
- **Depends:** T50, T31.
- **Files:** board/tutorboard/course/library.py (absorbs reading.py and results.py's walks; the figures
  view stays as a filter), board/tutorboard/course/reading.py and results.py (deleted),
  board/tutorboard/server/routes/{library,taking}.py, board/tutorboard/sense.py,
  board/tutorboard/lesson/state.py, board/tutorboard/course/burn.py, board/tutorboard/briefs.py,
  board/tutorboard/lesson/cards.py, board/test/library.py.
- **Do:** fold the remaining document walks into library.py, keeping reading.py's size and depth
  thresholds as filters.
- **Accept:** reading.py is gone; a results figure still drops into a card; TRD-EHR's `/library.json`
  ids and order are unchanged before and after. The suite is green.
- **Prompt:**

> You are executing T53 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T53 section; nothing else. Fold reading.py and results.py into library.py with their
> thresholds as filters, proving TRD-EHR's library listing unchanged. Meet every Accept line, integrate
> by 4.2, and report by 4.11.

#### T54. The LaTeX transcript export

- **Machine:** Mac.
- **Depends:** T26.
- **Files:** board/tutorboard/course/document.py (`build`, `lessons`, `render_lesson`), board/bin/board
  (`cmd_export`), the `/export` route and the history-row button, `paper.KINDS` `lesson`,
  board/test/document.py, board/test/export.js.
- **Do:** delete the LaTeX transcript export (D11). The screenshot export (shot.js, screenshot.py) stays.
- **Accept:** `git grep -n 'board export' -- board` is empty; the screenshot export still makes a PDF
  (test/shot.py). The suite is green.
- **Prompt:**

> You are executing T54 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T54 section; nothing else. Delete the LaTeX transcript export and keep the screenshot export.
> Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T55. Remove the time-boxed shims

- **Machine:** Mac.
- **Depends:** T49, T50, T51, T52, T53.
- **Files:** board/bin/board (`hw` alias), board/tutorboard/subjects.py (basename fallback),
  board/web/address.js (`#/w/...` redirect), board/tutorboard/course/repo.py (the `<root>/live`
  default), any `tutor resume` stub left, and their tests.
- **Do:** delete each shim. Keep two things that are data compatibility, not shims: requests' ignored
  `thread` key (old reports stay readable) and T05c's old-location claim fallback (the cluster migrates
  on its first new pass; T60 lists its removal).
- **Accept:** `board hw` is unknown; `find('research/PSYCH-ASR')` returns nothing; `#/w/...` parses as
  no address; `Repo` requires a session directory. The suite is green.
- **Prompt:**

> You are executing T55 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T55 section; nothing else. Delete the board hw alias, the basename fallback, the old-address
> redirect and Repo's live default. Keep the thread read-compat and T05c's fallback. Meet every Accept
> line, integrate by 4.2, and report by 4.11.

### Phase 6: docs and cleanup

#### T56. TEACHING.md

- **Machine:** Mac.
- **Depends:** T32, T30c, T38c, T15.
- **Files:** board/TEACHING.md, board/tutorboard/sense.py, board/tutorboard/course/config.py,
  board/test/teaching.py, board/test/tokens.py.
- **Do:**
  - Cut to at most 600 lines. Delete the map, aim, threads and direction sections and the plan
    sourcing section.
  - Rewrite the sitting-kind sections as methods inside one session: homework, test review,
    walkthrough, make, coach.
  - Add: binding and creating subjects, filing uploads (`board file`), writeups everywhere
    (`board writeup`), teach and do modes, `board check`, `board memo`, coding on the cluster
    (`board code`, the `[code]` step turn), and that board/ is edited only in a worktree.
  - Remove duplicate rules; never cut a step of the method itself.
  - teaching.py and tokens.py hold at most 30 literal phrases, and every section name quoted in code
    exists as a heading.
- **Accept:** `wc -l board/TEACHING.md` is at most 600; no mention of threads, the map, families,
  DIRECTION.md, aim, stance, NEXT.md, `board note` or `board hold`; the suite is green.
- **Prompt:**

> You are executing T56 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T56 section; nothing else. Cut TEACHING.md to 600 lines: remove dead-feature sections and
> duplicates, recast sitting kinds as methods, and add binding, uploads, writeups, modes, check, memo
> and cluster coding. Keep every step of the method. Make teaching.py and tokens.py behaviour checks.
> Meet every Accept line, integrate by 4.2, and report by 4.11.

#### T57. The core docs

- **Machine:** Mac.
- **Depends:** T55, T56.
- **Files:** README.md, board/README.md, board/test/truthful.py, and the subject README passages that
  state false operations: projects/Paper-Writer/README.md (cluster checkout, systemd, the claude CLI on
  the cluster) and projects/libr-local-llm/README.md (node serving, setup-node).
- **Do:**
  - Root README at most 200 lines: what Atlas is, the layout, the hard constraints (public repo, no PHI
    in git, no hosted model on an institute machine, the Mac is the only brain), the Mac and cluster
    split, setup on each machine. No history section.
  - board/README.md at most 600 lines: processes, sessions, artifacts, the relay and coding sessions,
    invariants with one-clause reasons, tests, shipping.
  - Fix every stale reference: grep both files for every module, command and file this HANDOFF
    deletes. In the two subject READMEs, change only
    the false operational passages: Paper-Writer runs on the Mac only, and no compute node serves a board.
  - Present tense, no history (the owner's documentation rule).
- **Accept:** both length limits hold; `grep -ciE 'used to|no longer|formerly|this replaced'` is 0 for
  both files; truthful.py resolves every anchor; `git grep -n 'claude' -- projects/Paper-Writer/README.md`
  shows no instruction to run it on the cluster. The suite is green.
- **Prompt:**

> You are executing T57 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T57 section; nothing else. Write README.md (at most 200 lines) and board/README.md (at most
> 600) for the system as built, in present tense with reasons in clauses, and fix the false operational
> passages in the Paper-Writer and libr-local-llm READMEs. Find stale references by grepping both
> READMEs for every module, command and file this HANDOFF deletes. Meet every Accept line, integrate by
> 4.2, and report by 4.11.

#### T58. Comment purge

- **Machine:** Mac.
- **Depends:** T57.
- **Files:** board/tutorboard, board/bin, board/web/*.js (not vendored code).
- **Do:** module docstrings say what the module does plus the one constraint a maintainer would break.
  Replace history narration with one-clause reasons. Keep every rule; cut the story.
- **Accept:** Python comment-plus-docstring share is under 20% (AST count; give before and after);
  `git grep -nE 'used to|no longer|formerly|An earlier version' -- board/tutorboard board/bin 'board/web/*.js'`
  returns under 20 hits. The suite is green.
- **Prompt:**

> You are executing T58 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md. Read sections 1 to 4
> and the T58 section; nothing else. Purge narrated history from comments and docstrings in board/,
> keeping every constraint's reason in a clause. Meet every Accept line, integrate by 4.2, and report
> by 4.11.

### Cutover and close

#### T59. Cutover on the Mac, and the cluster runbook

- **Machine:** Mac + the whole cluster runbook.
- **Depends:** every task above that landed. It runs when T26 and T29 landed, even if feature tasks
  failed.
- **Files:** the main checkout (the first of two tasks allowed to change it),
  `~/Archive/atlas-migration/<date>/`, `~/Library/LaunchAgents/tutor-board.plist`, the tailscale serve
  configuration, and the runbook at
  `/Users/mikeyferguson/Library/Mobile Documents/com~apple~CloudDocs/HANDOFF-cluster.md`.
- **Do:**
  1. List what landed: `git -C $G log overhaul --format=%s | grep -o '(T[0-9]*[a-c]*)' | sort -u`.
     Confirm T26 and T29 are there; otherwise stop.
  2. Re-run `board/scripts/cutover.sh --rehearse <scratch>` from a worktree of the final `overhaul`.
     If it fails, fix the script on `ov/T59` by 4.2 and rehearse again. If it still fails, stop with
     main untouched.
  3. Run `cutover.sh --run` from that worktree against `$G`. It stops the old system in the order of
     T26 (LaunchAgents first, then idle daemons by SIGKILL, then boards), snapshots and tars, imports,
     moves the course `.git` dirs, merges, moves residue, installs the LaunchAgent, replaces the
     tailscale configuration, proves one real `/say`, and pushes. On any failed check it rolls back and
     leaves main on the old system with the old boards answering.
  4. In the main checkout after the push: run `scripts/build.sh` in projects/Lean-Theorem-Proving
     (stop after 15 minutes and note it), and `python3 board/test/run.py --guards`.
  5. Write the runbook below into the iCloud file, replacing it. Fill in `<SHA>` (pushed main) and
     `<DATE>`. Fold any "Pending from Txx" lines of landed tasks into the matching step. Drop a step
     whose task did not land, and say so on its line (for example step 10 without T38c).
- **Accept:**
  - The one real `/say` is answered with a card; no duplicate card and no wrap-up row appear.
  - `launchctl list | grep -c tutor-board` is 1; `pgrep -f serve.py | wc -l` is 1; no `tutor headless`,
    `board wait` or `tutor watch` process exists.
  - `tailscale serve status --json` lists only 127.0.0.1:8778 under the same HTTPS name, so the PWA URL
    is unchanged.
  - No `live/` remains in any subject. `git -C $G status --porcelain` is empty.
    `git -C $G rev-parse main` equals `git -C $G rev-parse origin/main`.
  - The runbook file exists and names `<SHA>`. Every tar, bundle and the manifest are in the archive dir.
- **Prompt:**

> You are executing T59 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md, the cutover. Read sections
> 1 to 4 and the T59 section; nothing else. You may change the main checkout; nobody uses the iPad
> tonight. Confirm T26 and T29 landed, rehearse cutover.sh against the final overhaul on copies, then
> run it for real. It must abort and roll back on any failed check, and push main only after one real
> /say is answered. Then run the Lean build and the guards, and write the runbook below into
> /Users/mikeyferguson/Library/Mobile Documents/com~apple~CloudDocs/HANDOFF-cluster.md, replacing the
> file, with <SHA> and <DATE> filled in, pending lines of landed tasks folded in, and steps of tasks
> that did not land marked as skipped. Never ssh to the cluster. Report by 4.11, including the
> rollback reason if one happened.
>
> The runbook, verbatim:
>
> ````
> # HANDOFF-cluster: the cluster's part of the Atlas overhaul
>
> The Mac merged the overhaul and pushed main at <SHA> on <DATE>. Run these steps in order on a
> login node. Each step ends with a check. Stop at the first check that fails and take its output to a
> Mac session. Never list or print anything under phi/ or results/.
>
> The old relay may already have pulled <SHA> overnight. That is expected: the new root .gitignore
> keeps research/ and practice/ residue invisible, and job_env.sh refuses a missing data root.
>
> ## 0. Look first
> cd ~/Atlas
> git log -1 --oneline                                  # <SHA> or the older main; both are fine
> squeue -u $USER                                       # wait until empty before step 5
> scrontab -l > ~/scrontab.before-overhaul; cat ~/scrontab.before-overhaul
> ls -d courses/*/ 2>/dev/null                          # course clones, if any
>
> ## 1. Pause what pulls
> systemctl --user disable --now tutor-pull.timer tutor-pull.service 2>/dev/null
> systemctl --user list-timers | grep -c tutor          # expect 0
> scrontab -e                                           # put '#' before the line that runs the relay; save
> scrontab -l | grep -v '^#' | grep -c relay            # expect 0
>
> ## 2. Course clones: bundle, then move aside (they hold the only copy of any cluster-side course work)
> mkdir -p ~/atlas-migration/courses.pre-fold
> for c in ~/Atlas/courses/*/; do [ -d "$c.git" ] || continue; n=$(basename "$c"); git -C "$c" bundle create ~/atlas-migration/$n.bundle --all && git bundle verify ~/atlas-migration/$n.bundle && mv "$c" ~/atlas-migration/courses.pre-fold/; done
> ls ~/atlas-migration                                  # one verified bundle per moved clone
> git ls-files courses | head -1 && git checkout -- courses   # restores tracked course files if <SHA> is already here
>
> ## 3. Pull
> git pull --ff-only
> git log -1 --format=%H                                # expect <SHA>
> git status --porcelain --untracked-files=no | wc -l   # expect 0
>
> ## 4. Hooks, and the old autostart
> bash board/bootstrap.sh --no-clone
> git config core.hooksPath                             # expect the absolute path of ~/Atlas/.githooks
> ls .githooks                                          # expect commit-msg and pre-commit
> bash board/scripts/install-autostart.sh --uninstall
> rm -f ~/.local/bin/tutor
> grep -n 'tutor' ~/.bashrc                             # expect no login-hook line
>
> ## 5. Move research/ and practice/ residue into projects/ (squeue must be empty)
> for d in research/* practice/*; do [ -d "$d" ] || continue; bash board/scripts/move-residue.sh "$d" "projects/$(basename "$d")"; done             # dry run; read it
> for d in research/* practice/*; do [ -d "$d" ] || continue; bash board/scripts/move-residue.sh "$d" "projects/$(basename "$d")" --apply; done
> test ! -e research && test ! -e practice && echo gone                                   # expect: gone
> test -d projects/PSYCH-ASR/phi && echo phi-present                                     # existence only; never list it
> git status --porcelain --untracked-files=all -- projects/PSYCH-ASR/phi projects/TRD-EHR/results | wc -l   # expect 0
>
> ## 6. Environments and PHI checks
> bash scripts/setup.sh                                 # re-syncs each subject's .venv after the move
> bash ai-config/scripts/test.sh                        # expect green
> bash board/scripts/phi-probe.sh projects/PSYCH-ASR/phi/x && echo refused   # expect: refused
> python3 board/test/tracked.py                         # expect green
>
> ## 7. The relay, every 2 minutes
> python3 board/bin/relay --install
> scrontab -l | grep -c 'relay-pass.sh'                 # expect 1
> scrontab -l | grep 'relay-pass'                       # expect */2 (*/5 if T44 did not land)
> bash board/scripts/relay-pass.sh; echo exit=$?        # expect exit=0
> python3 -c 'import json; print(json.load(open("relay/status.json")).get("last_error"))'   # expect None or empty
>
> ## 8. Two checks only the cluster can answer
> No hosted model's credential may be readable on the cluster, because the egress hook is defence in
> depth and a key is what a bypass would need. This prints yes or no per item and never a value. Any
> "yes" needs removing.
>
> bash -c 'yn(){ if "$@" >/dev/null 2>&1; then echo yes; else echo no; fi; }; row(){ printf "%-66s %s\n" "$1" "$2"; }; envkey(){ env | grep -qE "^[A-Za-z0-9_]*_API_KEY=.|^ANTHROPIC_AUTH_TOKEN=."; }; S="$( { ls -d /etc/claude-code/*.json 2>/dev/null; find "$HOME" -maxdepth 7 \( -name phi -o -name node_modules -o -name .git \) -prune -o -path "*/.claude/settings*.json" -print 2>/dev/null; } )"; baseurl(){ local f; while IFS= read -r f; do [ -n "$f" ] && grep -qs ANTHROPIC_BASE_URL "$f" && return 0; done <<< "$S"; return 1; }; row "~/.claude/.credentials.json exists" "$(yn test -e "$HOME/.claude/.credentials.json")"; row "~/.config/tutor-board/keys.env sets a value" "$(yn grep -qsE "^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=[^[:space:]#]" "$HOME/.config/tutor-board/keys.env")"; row "~/.local/share/opencode/auth.json exists" "$(yn test -e "$HOME/.local/share/opencode/auth.json")"; row "a login profile names *_API_KEY or ANTHROPIC_AUTH_TOKEN" "$(yn grep -qsE "_API_KEY|ANTHROPIC_AUTH_TOKEN" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile" "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.zshenv")"; row "this login shell has a *_API_KEY or ANTHROPIC_AUTH_TOKEN set" "$(yn envkey)"; row "a .claude/settings*.json or /etc/claude-code/*.json names ANTHROPIC_BASE_URL" "$(yn baseurl)"'
>
> ## 9. One round trip
> On the iPad, in a session bound to projects/TRD-EHR, ask the tutor to file its cheapest diagnostic
> recipe. Within about 5 minutes a [job] card arrives, completed.
> In a session bound to projects/PSYCH-ASR, ask for a dry job. Its report completes, and job_env.sh
> resolves PSYCH_ASR_DATA under projects/PSYCH-ASR/phi.
>
> ## 10. One coding-session trial (Algo-Solutions, go test)
> On the iPad, start a session bound to projects/Algo-Solutions and copy the command its header shows.
> cd ~/Atlas && board code <session-id> leetcode/<a-problem-dir>
> Edit one file there. Within about a minute the iPad shows a [code] step card.
> board code <session-id> --end
> git log -1 --oneline; git ls-remote origin 'refs/heads/code/*' | wc -l   # one new commit; 0 refs
>
> ## 11. TRD-EHR's switch to the lockfile (when there is time)
> The conda environment on lab storage stays until the lockfile reproduces it. Build uv.lock into lab
> storage through UV_PROJECT_ENVIRONMENT with `uv sync --locked --extra test --extra cluster` in
> projects/TRD-EHR. Rewrite setup_envs.sh to call that. Run one real sweep and one causal run on the
> new environment and compare them with the conda environment's last results. causal_forest_env folds
> in too: the pyproject.toml carries econml 0.17.0, which accepts the pipeline's scikit-learn 1.7.1.
> Only then remove both conda environments. Decide how scripts/setup.sh's per-subject .venv and
> UV_PROJECT_ENVIRONMENT meet. Commit and push from the cluster checkout; the hooks run there now.
>
> ## 12. A week later
> diff -rq ~/atlas-migration/courses.pre-fold/<Name> ~/Atlas/courses/<Name> | grep -v '/\.git' | head
> rm -rf ~/atlas-migration/courses.pre-fold             # once nothing in it is missing from Atlas; keep the bundles
>
> ## Removing a PHI subject, when you decide to
> The iPad refuses it (D23). On the cluster: confirm no job, request or coding session is open for it;
> move its phi/, results/ and .env where its data agreement says; then git rm -r projects/<Name>,
> commit and push from the cluster checkout. The Mac pulls it within a minute.
> ````

- **Owner's override (2026-10-08), which wins over anything above in T59:**
  - The cluster runbook is a **bash script**, not prose:
    `/Users/mikeyferguson/Library/Mobile Documents/com~apple~CloudDocs/cluster-runbook.sh`, mode 755.
    The owner runs it from the Atlas root on the cluster as `bash ~/path/to/cluster-runbook.sh`.
    - It refuses to start unless the cwd holds `board/` and `.git`.
    - It uses `set -euo pipefail` and runs on bash 3.2 or newer.
    - Every step echoes what it does, verifies its result, and prints `OK <step>`. The first failure
      stops the script with one line naming the step and the check that failed.
    - It is idempotent: a rerun skips the steps already done.
    - It never lists, prints or copies anything under `phi/` or `results/`.
    - Everything mechanical goes in: pull, bundling and moving aside course clones, move-residue for
      each research/ and practice/ subject, uninstalling the old autostart and timers, bootstrap and
      `core.hooksPath`, re-installing the relay scrontab, the credential check (it fails if any line
      says yes), and the verification passes.
  - What needs human judgement stays OUT of the script. That covers the TRD-EHR lockfile switch with
    its result comparison, the week-later clone cleanup, and removing a PHI subject. HANDOFF-cluster.md
    becomes a short file: the one command to run the script, then those manual items.
  - The script is the cluster's whole tonight-to-morning job. Test it on the Mac against a scratch
    clone with fake `squeue`, `scrontab` and `systemctl` on PATH before writing it to iCloud.
  - T59 does NOT write DONE.md. T60 does.

#### T60. Final sweep, and this file rewritten to what is left

- **Machine:** Mac.
- **Depends:** T59.
- **Files:** HANDOFF.md, the one-off migration scripts (board/scripts/migrate-exports.py,
  migrate-memory.py, migrate-artifacts.py, artifact-moves.json, import-live.py, cutover.sh, cutover.py,
  fold-excludes.txt), and the main checkout (the second task allowed to change it).
- **Do:**
  1. Work in `$G-wt/T60` on branch `ov/T60` made from `main` (not `overhaul`).
  2. Verify the end state and put the numbers in the commit message: every deleted concept of a landed
     task greps empty; one serve.py, one launchd label, no tutor processes when idle; idle CPU of the
     server over 10 minutes; `run.py` wall time; `git ls-files | xargs du -ch | tail -1`; tracked.py
     green; the README tree matches disk.
  3. Delete the one-off migration scripts; they ran once.
  4. Rewrite HANDOFF.md to hold only what is left: the sections of every task that did not land
     (verbatim, deps adjusted to what exists now), the removal of T05c's old-location claim fallback
     after the cluster's first new pass, the owner's items (a Time Machine destination; read
     TEACHING.md once; confirm the manuscript's new code link sentences; Algo-Solutions'
     `leetcode/totalbeauty` imports), and the "On the glass" list.
  5. Run the suite, then fast-forward the main checkout: `git -C $G merge --ff-only ov/T60`, and push
     with gitops. The freshness thread restarts the server when idle.
- **Accept:** every check above passes or is listed as undone in the new HANDOFF.md; main is pushed and
  equals origin/main; HANDOFF.md holds nothing that landed.
- **Prompt:**

> You are executing T60 of /Users/mikeyferguson/Developer/Atlas/HANDOFF.md, the last task. Read
> sections 1 to 4 and the T60 section; nothing else. In a worktree from main, verify the end state with
> numbers, delete the one-off migration scripts, and rewrite HANDOFF.md to hold only undone tasks, the
> post-cutover items, the owner's items and the on-glass checks. Run the suite, fast-forward the main
> checkout, and push. Report by 4.11.

- **Owner's override (2026-10-08):** T60's very last action, after main is pushed, is the done
  signal. Create an EMPTY file at
  `/Users/mikeyferguson/Library/Mobile Documents/com~apple~CloudDocs/DONE.md` ONLY IF every one of
  these holds:
  - every task T01 to T58 landed in full (no failed, skipped or partial task);
  - T59's cutover completed without a rollback;
  - `cluster-runbook.sh` exists and passed its scratch-clone test;
  - the suite is green on main;
  - the one real `/say` was answered.
  If any of these fails, do not create DONE.md, and delete one left over from an earlier run. Say in
  the report which condition failed.

---

## 6. The work it is for

In this order. Each item's open tasks live in its subject's TUTOR.md after T30b.

1. **Paper 1** (`projects/TRD-EHR`, `paper1-trd-prediction/`). The writing happens on the Mac. Anything
   that reruns a model goes to the cluster as a request.
   - k-sweep across embedders: the section, Figure 5 and the cross-encoder figures are written. Open:
     discuss the dimension-count versus best-k scatter (it stays out of the write-up until then), fix
     the last *importance-weighted* in `plot_neighbor_sweep_figure.py`'s docstring, re-split `parts/`,
     and a teach session on the shape of the k-sweep.
   - Reviewer findings: the round-1 pairs on the manuscript, judged fine or not fixed; Martin's open
     questions; the TRIPOD+AI rows.
   - Consistency pass, after the reviewer findings: clarity, cross-document numbers, refs 10 and 12 at
     proof, and a strict packet rebuild (`scripts/rebuild-packet.sh`, now `board build`).
   - The code-availability link pointed at a repository that does not exist. T29 points it at
     `github.com/Pirate-Hunter-Zoro/Atlas/tree/main/projects/TRD-EHR`. Confirm the sentence before
     submission.
2. **The Colibri deck** (`projects/libr-local-llm`). Teach sessions on the PHI path and the LIBR
   hardware first, so the owner can defend every slide. Then Make, Deck.
3. **PSYCH-ASR grid sweep**, as cluster requests, and the owner's recording review at the institute.
4. **Paper 2** (`projects/TRD-EHR`, `paper2-counterfactual/`). Teach sessions on estimand
   identification, then coach sessions on the four robustness rungs. The owner writes that code on the
   Mac against `test_data/`, or on the cluster with `board code` when it needs real rows. Then build.

## 7. On the glass

Built and never used for real. Strike each one after an evening on the iPad.

- Home: Continue rows, New session, the Courses and Projects lists, "+ new" with the patient-data
  question, and a subject delete with its typed name.
- A new session starts unbound; "this is for Topology" binds it and the chip updates.
- Teach and do persist until switched; a do turn runs `board check`.
- Pinch-zoom on a paper and a deck in the one reader. Safari's own page zoom never starts, ink stays on
  its words, and one finger scrolls a zoomed page sideways.
- The round as pairs on the TRD-EHR manuscript, round 1 being the 09-29 round: tap the chip, a row and a
  pip, and mark pairs fine or not fixed.
- A `[job]` card waking the filing session when a cluster report lands, and a report reopening an
  ended session. A request filed with no session showing as a home notice.
- "Relay looks down", and the Colibri panel with its cold-start estimate.
- One document all the way round: Make, build, read, ink, "Say what's wrong", revise.
- The meeting deck in projects/Meetings, written by a real turn, read and inked in the one reader.
- The notes canvas: a full-slate session whose End leaves a notes.md.
- Annotate a PDF: upload, ink, keep a marked copy, and the tutor files it.
- A writeup appearing after hand-written answers in a project session, not a course.
- A code excerpt with `path#L` highlighted and numbered, opening the source viewer.
- A `[code]` step card from `board code` on the cluster.
- Sending selected annotations.
- A response typing out, and the typed half of the answer panel, in a real session.
- Whether the verdict band and streak chip feel like information or like a scoreboard.
