# Tutor-Board

A live tutoring board. A tutor turn writes lesson cards as files, and `serve.py` pushes them to
every browser holding the session open, typeset. Handwriting, typed answers and uploads come
back into an inbox that wakes the next turn. It runs on the owner's Mac mini, the only machine
where a model is called. The cluster runs Slurm and talks to the Mac only through git.

[TEACHING.md](TEACHING.md) is the method every turn follows. The repository's own
[README](../README.md) has the hard constraints and machine setup.

## Processes

### On the Mac

- **One LaunchAgent**, label `tutor-board`, rendered from `scripts/launchd/tutor-board.plist`
  by `install.sh`. KeepAlive, an absolute interpreter path, ThrottleInterval 10. It runs one
  `serve.py` on port 8778, loopback only. `tailscale serve` publishes it over HTTPS once.
- **`serve.py`** serves every session at `/s/<id>/`, plus the unprefixed home, library and
  subject routes. `tutorboard/server/app.py` is the start. A session's Repo and Hub are made on
  first use and dropped after 10 idle minutes (`server/registry.py`).
- **The hub** (`server/hub.py`) builds one payload per viewed session and pushes it over
  server-sent events: in full on connect, then as deltas. It reacts to file changes in the
  session directory and to routes marking it dirty.
- **The runner** (`runner/service.py`) takes every turn inside the server: one FIFO per
  session, at most 2 turns at once. A turn is one fresh provider process with cwd at the Atlas
  root and `TUTORBOARD_SESSION=<session dir>`, `TUTORBOARD_TURN=1` and
  `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1`. A message is recorded as owed before the turn runs
  and re-queued at startup, so a restart loses no message.
- **The cluster thread** (`cluster.Ear`, only with `TUTORBOARD_CLUSTER=1`). Every 20 s one
  `git ls-remote origin` asks for `main` and `refs/heads/code/*`. When main moved: a
  fast-forward pull, a vendor checkout, then every subject's reports are heard.
- **The freshness thread** (only with `TUTORBOARD_FRESH=1`). Once committed board code differs
  from what the process loaded (`stamp.py`) and no turn runs or waits, the server exits 0 and
  launchd starts it on the new code.

A server started by hand or by a test sets neither variable, so it never pulls the real origin.
`serve.py` refuses to start where Slurm exists.

### On the cluster

No board server and no model, ever. scrontab runs `scripts/relay-pass.sh` every 2 minutes:
`flock`, a bash fast-forward pull, a re-exec when the pull changed `board/`, then
`python3 board/bin/relay --once --quiet`. Bash pulls so that a pushed fix lands even when the
Python it fixes cannot import. The owner runs `board code` by hand to code with the tutor.

## Layout

| Path | What it holds |
| --- | --- |
| `serve.py` | the server entry |
| `bin/board` | the CLI a tutor turn and the owner use; `board help` lists every command |
| `bin/relay` | the cluster's scheduled entry; imports only the relay path |
| `tutorboard/server/` | app, handler, hub, registry, TikZ worker, `routes/` by family |
| `tutorboard/runner/` | the runner, one turn, its prompts (`prompts/*.md`) |
| `tutorboard/lesson/` | cards, inbox, slate, turns, uploads, the save |
| `tutorboard/course/` | a subject on disk: config, Repo, homework, library, reader pages, ledger, burn |
| `tutorboard/agents/` | provider recipes, usage and cost, `board doctor` |
| `tutorboard/` (top level) | sessions, subjects, artifacts, memo, mode, brief, sense, build, writeups, briefs (the meeting deck), relay, jobs, exports, colibri, cluster, code, gitops, audit, fenced, leaving |
| `web/` | home, board, slate and library pages; reader; ink; `sw.js`; vendored KaTeX and math.js |
| `cluster/lib/` | the failure fingerprint every relayed recipe sources |
| `tex/` | `board-macros.tex` (generated from `web/macros.js` by `tools/sync-macros.py`) and the write-up template |
| `scripts/` | install, ship, save-and-push, the relay pass, cluster setup, the cutover |
| `test/` | one suite per file, run by `test/run.py` |

## Sessions

A session is `sessions/<YYYYMMDD-HHMMSS>/` under the Atlas root. It is Mac-only and ignored,
and the audit refuses any path under it.

`session.json` holds `id`, `title`, `subject` (a subject id or null), `mode` (teach or do),
`opened`, `ended`, `writeup`, `seen`, `code` (a cluster coding session, or null) and `view`
(`board`, or `slate` for a notes canvas). Beside it: `cards/`, `slate/`, `answers/`,
`turns.jsonl`, `inbox/messages.jsonl`, `uploads/`, `annotations/`, `agent.json`,
`cost.jsonl`, `agent.log`.

- **New.** Home's "New session" opens `/s/<id>/board`, unbound, in teach mode.
- **Bind.** `board bind courses/<Name>` or the subject chip sets `subject` and appends a
  non-waking `[bind]` line. Nothing moves or restarts. `--create` makes the subject first.
- **Mode.** `board mode teach|do`, `POST /mode`, or the tutor obeying "do it". Nothing infers
  do mode. A change is a non-waking line, so the next turn reads it.
- **Persist.** A session stays open until the owner taps End. End sets `ended`, commits the
  subject's `TUTOR.md` and the session's artifacts, then queues a wrap-up turn that brings
  `TUTOR.md` up to date with `board memo`. A second End retries the commit.
- **Reopen.** A cluster report for an ended session reopens it.
- **Delete.** A second tap moves the directory to `~/.local/share/tutor-board/trash/<stamp>/`,
  kept 30 days.

**The inbox wakes turns.** A line in `inbox/messages.jsonl` is unread until a turn takes it.
A line written `"wake": false` (bind, mode, filing, upload) queues nothing, and the next turn
takes it with the rest.

**Every turn is cold.** The prompt carries the brief and the recap (`brief.py`); the global
CLAUDE.md still loads. The brief is the method from `sense.py`, the subject's `RULES.md` at
HEAD, its `TUTOR.md`, what the owner did away from the board, and work out on the cluster. A
subject's `README.md` never enters it. `board brief` and `board recap` print the same text.

**Uploads** land in the session's `uploads/` with a non-waking line. The tutor files them into
the bound subject with `board file`, `materials/` by default, and their ink follows.

**Non-session asks** (library feedback, Make from home, a meeting ask) go to the newest open
session bound to the target subject, else to a new session bound to it.

## Subjects

A subject is a directory directly under `courses/` or `projects/` (`subjects.py`). No registry,
no marker file.

- **`tutorboard.json`** holds `name`, `phi`, `check` and `relay`. `relay` holds `exports`
  (the owner's approved export globs), `colibri` and `fingerprint`. `board init` writes one.
- **Create.** "+ course", "+ project" or `board bind <id> --create`. A project needs
  `--phi yes|no`; yes also writes the PHI ignore stanza. One commit makes the directory,
  `tutorboard.json` and a `TUTOR.md` skeleton.
- **Memory.** `RULES.md` is the owner's; the brief reads it at HEAD and flags a working-tree
  edit, and the pre-commit hook refuses it in a turn. `TUTOR.md` is the tutor's: sections
  "Where things are", "Now", "Open decisions", "Done recently", at most 800 words, written
  only by `board memo <section>`. The cap refuses rather than trims, because the brief carries
  the whole file.
- **Delete** from the iPad needs the name typed. It is refused unless `tutorboard.json` at HEAD
  sets `phi` to `false` literally, no open session is bound to it, no coding session holds it,
  and no request waits for a report. A PHI subject is removed only through a cluster runbook.
  Tracked files leave by `git rm` in one commit; the directory goes to the trash.
- **Check.** `board check [<path>]` runs the subject's `check` from its root.

## Artifacts and documents

An **artifact** is a directory holding `doc.json` = {title, source, sessions, asked_at}
(`artifacts.py`). Its type comes from the source's extension and document class; its status
(writing, done, failed) from mtimes. New ones live at `<subject>/docs/<slug>/`. An existing
tree gets a `doc.json` written in place, so its ids hold.

- **Build.** `board build <file>` is the only compiler: pdflatex for `.tex` (beamer or
  article, detected), pandoc for `.md` to `.docx`, plus PDF when an engine exists. Output lands
  beside the source. Built PDFs are ignored.
- **Write-ups.** In teach mode every agreed answer goes in with `board writeup add`, and the
  PDF is rebuilt. A course's assigned set is the same artifact, written in place
  (`board writeup use hw04`).
- **Deck or paper.** The Make menu creates the `doc.json`; a `[writeup]` turn writes and
  builds it.
- **Meeting deck.** `board meeting --since 7d` or home's meeting panel: one brief of the
  period (`briefs.py`), and the deck at `projects/Meetings/docs/meeting/` is replaced. git
  history keeps the old ones.
- **Reader.** One reader (`web/reader.js`) shows every PDF as page pictures drawn on the Mac.
  "Say what's wrong" files the marked pages as a round of the document's ledger and wakes a
  `[revise]` turn, which edits the source or writes `TUTOR.md`.
- **Ink** is one kind. Card ink lives in the session; document ink lives in
  `<subject>/.ink/`, keyed `doc/<id>/p<n>`. Both are ignored.
- **Materials** are third-party or uploaded files in `<subject>/materials/`, ignored, readable
  and inkable.
- **Notes canvas.** A session in slate view. End has the tutor transcribe a `notes.md`.
- **Annotate a PDF.** Upload it, ink it, and "Keep a marked copy" writes `<name>-marked.pdf`
  beside it (`course/burn.py`). Filing the upload re-keys its ink.
- **Export.** The session export is a screenshot of the scrolled board, wrapped in a PDF
  (`web/shot.js`, `course/screenshot.py`).

## The web client

- **Home** (`/`, `web/home.js`): open sessions, New session, notices, courses and projects
  (each row can make a deck or paper), past sessions, the Notes, Annotate a PDF and Meeting
  deck actions, relay and Colibri health, settings.
- **Board** (`/s/<id>/board`): the session header (subject chip, mode, End), the cards, the
  answer box, the slate. **Slate** (`/s/<id>/slate`) is the full-page writing surface.
- **Library** (`/library?subject=<id>`): every document and result of a subject, the reader,
  feedback and delete.
- **Addresses** (`web/address.js`) have one grammar: `#/s/<session>`, then `/card/<nnnn>`,
  `/doc/<ident>[/p<n>]` or `/slate/<nnnn>`. Nothing else parses as an address.
- **`sw.js`** caches an allowlist of shell files, fonts and KaTeX, and nothing else, because
  a cached lesson is a stale one. The server writes its `VERSION` as a hash of the shell
  files, so a shell edit installs a new worker by itself.

## The relay

The cluster half is `relay.py`; the Mac half is `jobs.py` and `cluster.py`. GitHub is the only
channel.

1. **File.** In do mode the tutor runs `board check`, `board push`, then
   `board job -- <recipe.sbatch> [VAR=v ...]`. Without Slurm, that commits
   `<subject>/relay/requests/<id>.json`, pinned to the pushed commit, and pushes.
   `board job --batch <file.json>` files many in one commit; one problem files none.
2. **Validate**, on both machines (`jobs.validate`). The recipe is tracked and unchanged at
   HEAD, HEAD contains the pinned commit, every variable matches its `#RELAY-VAR` pattern, and
   a `turn` request is refused, because no hosted model runs on an institute machine.
3. **Submit** through the exit-file wrapper, which sources `cluster/lib/`'s fingerprint. A
   job's end is read from `squeue` plus its exit file, because `sacct` is refused there.
4. **Report.** `relay/reports/<id>.json` carries state, Slurm id, times, exit code, `RELAY:`
   lines, which `produces` paths exist and which exports landed. A sanitized log excerpt rides
   along only where `phi` is literally `false`. Exports land under `exports/` only when
   `relay.exports` approves them: png, pdf and svg by any matching glob, csv and json only
   with `"aggregate": true`, 5 MB at most.
5. **Hear.** The Mac's cluster thread reads new reports and wakes the session that filed the
   request, reopening it if ended. A report with no session becomes a home notice and starts
   no turn.
6. **Repair.** A failed job wakes a `[repair]` turn. Up to 3 automatic attempts per failure,
   counting `board diagnose` runs; then the owner decides, and `board job --fresh` starts
   again.

`relay/status.json` at the Atlas root carries the relay's errors and Colibri's state,
committed only on change. A request unsubmitted 15 minutes after its commit shows "relay looks
down" on home.

The relay commits only what its pass wrote under `relay/reports/` and `exports/`, and
`relay/status.json`. It rebases under the owner's edits, never commits them, and never
force-pushes. Its runtime state lives in ignored `<subject>/relay/state/`.

### Colibri runs on demand

Colibri is the local model, served from a Slurm job on the cluster. `board colibri "<task>"`
files a `colibri` request from the Mac, or queues the task directly on the cluster. A
generation starts when a task is queued and none is up, works the queue, and exits once idle.
A task writes only under the subject's ignored `phi/`, so any change git can see fails it and
nothing it wrote is committed. Its `RELAY:` lines are what come back. The Mac reads Colibri's
state only from `relay/status.json`, and has no start control.

## Coding at the cluster

One git ref per coding session, `code/<session-id>` (`code.py`).

- `board code <session> <path>...`, run by the owner in a cluster terminal, holds those paths.
  After 10 s of quiet it snapshots them through a temporary index, so HEAD, the index and main
  never move. The commit-time gate and the subject's check run over the snapshot, and it is
  pushed fast-forward to `code/<session>` with `Step N` in the message.
- The Mac's cluster thread hears the ref, records it in `session.json` `code`, brings the held
  files in its working tree to the new tip, and wakes the session with `[code] step N`. The
  tutor answers on the iPad.
- A vibe push from the Mac while the session is open goes to the same ref, and the cluster loop
  applies it when its held paths are unchanged. Otherwise it prints "both sides changed".
- `--end` takes the relay's lock and makes one commit of the held paths on main, then deletes
  the ref. `--abandon` deletes the ref only.
- While a session is held, the relay tolerates edits to its paths, and the Mac refuses commits
  to them on main.

`board code` answers before anything else in `bin/board` is imported, so the cluster loads no
server, runner or model module.

## Providers

`agents/recipes.py` holds the recipe table. `~/.config/tutor-board/config.json` names one
`provider` (default `claude`), one `fallback` (`codex`) and a `vision_agent`. Nothing else
chooses: no session, subject or flag overrides it. The DeepSeek recipe runs through `opencode`.
Keys come from `~/.config/tutor-board/keys.env` (`keys.py`) and never reach a command line,
because argv shows in `ps`. A usage limit marks the provider unavailable until it expires, and the fallback takes its
turns (`limits.py`). `board doctor` spends one real turn per provider; `--dry` spends none.
`board cost` adds up every session's `cost.jsonl`.

## Invariants

- **Standard library only; add no runtime dependency.** The relay runs on a compute node with
  no `sudo`, and every dependency is one more thing to install there.
- **Relay-path code runs on Python 3.7**: `bin/relay`, `board code`, and the modules relay,
  jobs, colibri, exports, cluster, code, fenced, leaving, paths, worktree, gitops, audit and what
  they import. No walrus, no `match`, no `removeprefix`, no `functools.cache`, no `dict | dict`,
  no runtime builtin generics. `test/py37.py` enforces it, because the cluster's python3 may be
  3.7. Cluster bash stays bash 3.2 safe, and guards `flock` and `timeout` with `command -v`.
- **No hosted model on an institute machine.** `jobs.NO_TURN` refuses a `turn` request; the
  relay runs no model; Colibri is the only model beside the data.
- **Never read, list or copy anything under `phi/`, `results/`, or a directory named in
  `tutorboard/fenced.py` `NEVER`.** They hold identifiable patient data; existence checks only.
- **Never weaken the PHI guards:** `test/tracked.py`, `ai-config/policy/phi.py` fencing by
  name, the anchored `/phi/` ignores, `.githooks/commit-msg`, `jobs.NO_TURN`, and the rule that
  a Colibri task changing a tracked file fails. Each is the only thing between one mistake and
  a public commit.
- **Every commit is public.** Never commit a session, ink, an upload, a material, a third-party
  file, a log tail, a participant id or a lab storage path, because git keeps it forever.
  `.githooks/pre-commit` runs `audit.py` over the staged paths and refuses these.
- **A turn may not commit `RULES.md`, change a `tutorboard.json`'s `phi` or `relay.exports`,
  or commit `board/` in the main worktree.** The pre-commit hook refuses each while
  `TUTORBOARD_TURN` is set, because those are the owner's decisions.
- **Commit named paths only, through `gitops.commit`.** A commit carries the index, and a
  terminal in the same checkout may have staged something else.
- **Edit `board/` only in a worktree under `~/Developer/Atlas-wt/`.** The main checkout serves
  the iPad live, so a half-finished edit there is a broken lesson now.
- **Never `git stash`, never force-push.** A stash hides the owner's uncommitted work where
  nobody looks, and a force-push rewrites what the cluster already pulled.
- **A name from a browser never reaches a filesystem.** Routes take ids and look them up in what
  discovery found; a session id is matched against `sessions.ID_RE` before any path is built.
- **Nothing on the home page may throw while painting**, because that page is the way into
  every lesson.

## Tests

```
python3 board/test/run.py              every suite, four at a time
python3 board/test/run.py --guards     the PHI and relay guards only
python3 board/test/run.py relay code   the suites named
```

A suite is any `*.py` or `*.js` file in `test/` that `run.py` does not list as a helper:
discovery, not a registry. The run also covers Paper-Writer's unittests,
`tools/sync-macros.py --check`, and ai-config's PHI policy tests. The suite needs `node`;
it installs jsdom into `board/node_modules` on first run, for development only.

- `tracked.py` audits every tracked path in Atlas for PHI, size, credentials and third-party
  work. It runs early, because a public commit cannot be taken back.
- `py37.py` parses the relay path as Python 3.7.
- `teaching.py` checks that `TEACHING.md` stays under 600 lines and that every command and
  section it names exists.
- `truthful.py` checks the documents against the tree: no moved address, no dropped config
  key, every relative link and anchor resolving, every `board` command named existing.

Prove behaviour with fixtures: temp repositories, bare remotes, fake `squeue` and `sbatch`, a
fake provider script that writes a card. A test server never binds 8778 and never sets
`TUTORBOARD_CLUSTER=1`. A failing suite means the change is wrong, not the test. Suites can
collide on ports when worktrees test at once, so re-run a failure alone before believing it.

## Shipping

1. Make a worktree under `~/Developer/Atlas-wt/` and change the board there.
2. Run `python3 board/test/run.py` and leave it green.
3. Merge into main in the main checkout and push.

The freshness thread restarts the server on the new code once no turn runs.
`bash board/scripts/ship.sh "message"` commits only `board/` in the checkout it runs in,
pushes, and restarts the LaunchAgent at once; a turn in flight is cut and its message stays
owed. Changes outside `board/` go through `bash board/scripts/save-and-push.sh "message" --
<paths>`.

Commits are authored by the owner with no assistant trailers; `.githooks/commit-msg` strips
them. `bootstrap.sh` points `core.hooksPath` at `.githooks/` by absolute path, so every
worktree runs the same hooks.
