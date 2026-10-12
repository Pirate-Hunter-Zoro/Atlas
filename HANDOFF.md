# HANDOFF: what is left

Work still to do, and nothing else. Delete an item when it lands. Agents never ssh to the cluster:
cluster steps are the owner's.

## 1. Next session: build, then the Colibri lesson

Build with ultracode: one workflow per stage, every agent in a worktree under
`~/Developer/Atlas-wt/`, `python3 board/test/run.py` green, and an adversarial review before the
merge. A merge restarts the live board, so everything lands before the lesson starts. No Mathlib
build runs during the lesson.

First ask the owner, in one AskUserQuestion: the deck's audience and length; a new deck through
Make or a rework of `projects/libr-local-llm/docs/fleet_walkthrough.tex`; whether the lesson
continues open session `20261009-193922-5` or starts fresh; whether the deck names the live gaps
(loopback is not a boundary, ollama has no auth, KV persistence) or only the controls.

### Build

1. **The deck loop: the owner's yes.** `projects/libr-local-llm/.gitignore:15` ignores `*.json`,
   so a deck's feedback ledgers never commit. It is the owner's file. The proposal, after
   `!/docs/*/doc.json`: `!/docs/**/feedback/*.ledger.json`, `!/docs/**/feedback/*/items.json` and
   `!/docs/**/feedback/*/states.json`. The round directory's other JSON is cache and stays
   ignored. Commit only on a yes.
2. **Mathlib on the Mac.** The Mac already has Mathlib from `lake exe cache get`; the sbatch exists
   because the cluster blocks the cache host. Add `projects/Lean-Theorem-Proving/scripts/build-mathlib.sh`:
   cache first, then an incremental `lake build`; `--source` skips the cache; `--status` exits 0
   built, 1 missing, 2 running, 3 failed. It backgrounds itself under `caffeinate -is` and nohup,
   with its lock, log and status file under `~/.local/state/atlas-setup/`, and caps
   `LEAN_NUM_THREADS` at 8 for 24 GB of RAM (`LEANTP_THREADS` overrides). The project's
   `scripts/setup.sh` calls it instead of compiling in the foreground, and `setup-mac.sh` gains a
   last step that reports built, running or started. `scripts/build.sh` refuses fast while a build
   runs or Mathlib is missing. Exercise `--source` once on a scratch clone: a source build writes
   about 7 GB and 52 GB are free. `RULES.md:9` forbids compiling from source; it is the owner's
   file, so propose the change.
3. **Coding sessions on the Mac mini and a laptop.** `board code` (`board/tutorboard/code.py`) needs
   no Slurm, and `board/test/code.py` passes on the Mac.
   - Laptop: a plain clone runs the same protocol and pushes `code/<sid>` to GitHub, which the Mac's
     Ear already hears. Only the wording changes ("at the cluster", "beside the data" in
     `runner/prompts/code.md`, TEACHING.md and the board header's command strip).
   - Mac-local, detected when `<top>/sessions/<sid>/session.json` exists: steps go to a local
     `refs/heads/code/<sid>` that is never pushed; the Ear also lists local refs, without network,
     and never releases them; the loop waits while `agent.json` has `owed` set; `--end` exempts its
     own session from `gitops.held_refusal`, commits on main, pushes and deletes the local ref; a
     linked worktree or a branch other than main is refused. The three end-path changes ship
     together, or `--end` is refused by its own held paths.
   - The pre-commit hook refuses held paths, with a bypass that only `board code --end` sets.
4. **Laptop setup.** `scripts/setup-mac.sh --coding` writes `~/.config/tutor-board/role` so a rerun
   stays a coding checkout: pull, bootstrap, `install.sh` with no LaunchAgent (and a stray one
   booted out), `scripts/setup.sh`, ai-config fast-forward and install, no tailscale serve, no
   port-8778 check. `install.sh` loads the LaunchAgent wherever launchctl exists, so it is gated
   first. Setup checks `ai-config/policy/phi.py` is present, because without it check output never
   reaches the tutor. `board pull` also fast-forwards ai-config and names subjects whose lockfiles
   moved. README gains the laptop section.

### Then the lesson

Walk the owner through it on the iPad, one step per reply. Note every rough edge for TEACHING.md.

1. A teach session bound to `projects/libr-local-llm`. In order: what Colibri is and where it runs;
   why it is safe with PHI (local weights, fences, the egress block, what a hosted model may read);
   how it rides LIBR's HPC (Slurm, the relay, `relay/status.json`, the cold start). Sources: README
   §4c, DESIGN §9, P0-STATUS findings 16-22, FLEET-BUILD.md, `docs/deepseek-egress.md`,
   `board/tutorboard/{colibri,relay,jobs,cluster,leaving,fenced}.py`, `ai-config/policy/`. The
   subject is `phi: true` but holds no PHI on the Mac, so a hosted turn reads tracked docs and code
   only. No live Colibri task: a cold load takes 68 minutes. Its TUTOR.md is at 686 of 800 words.
2. Rework `projects/libr-local-llm/docs/fleet_walkthrough.tex` from the library: ink it, "Say
   what's wrong" as an overhaul with the agreed purpose, then at least two revise rounds. Each
   round goes to the lesson session while it is the newest open one on the subject. The deck
   builds today with four Overfull vboxes (pages 3, 5, 8, 10), which the first round must fix.
3. Let the last round finish, then End. It settles the rounds and commits the deck's own files:
   the .tex, doc.json, its feedback and the rebuilt PDF, which is tracked. The rest of `docs/`
   stays out of the commit.
4. The owner's feedback goes into board/TEACHING.md and the prompts, in a worktree, merged after
   the lesson.

## 2. The LIBR exit

`LIBR-EXIT.md` is the prompt for the day the owner leaves LIBR. It runs only after section 1's deck
is finished.

## 3. After the cutover

Both machines are set up: `scripts/setup-mac.sh` and `scripts/setup-cluster.sh` each end clean,
the relay has committed `relay/status.json`, and research/ and practice/ are gone on both. The
cluster's Mathlib compiles as a Slurm job (`squeue -n mathlib`); rerunning `setup-cluster.sh`
reports it built once it is.

1. **The manual cluster items.** Each needs judgement, so none is in `setup-cluster.sh`.
   - **One round trip.** In an iPad session bound to projects/TRD-EHR, ask the tutor to file its
     cheapest diagnostic recipe; a completed `[job]` card arrives within about 5 minutes. In one
     bound to the diarization project, ask for a dry job; its report completes, and job_env.sh
     resolves its data variable inside that subject's fenced directory.
   - **One coding-session trial.** Start an iPad session bound to projects/Algo-Solutions and run
     the command its header shows on the cluster (`board code <session-id> leetcode/<dir>`). Edit
     one file; a `[code] step` card shows within about a minute. `board code <session-id> --end`
     leaves one new commit and no `code/*` ref on origin.
   - **TRD-EHR's lockfile.** The conda environment on lab storage stays until the lockfile
     reproduces it. Build uv.lock into lab storage through UV_PROJECT_ENVIRONMENT with
     `uv sync --locked --extra test --extra cluster`, rewrite setup_envs.sh to call that, and
     compare one real sweep and one causal run against the conda environment's last results.
     causal_forest_env folds in too (econml 0.17.0 accepts scikit-learn 1.7.1). Only then remove
     both conda environments, and decide how `scripts/setup.sh`'s per-subject .venv and
     UV_PROJECT_ENVIRONMENT meet.
   - **From 2026-10-16: the moved-aside course clones.** Check nothing in them is missing from
     Atlas (`diff -rq ~/atlas-migration/courses.pre-fold/<Name> ~/Atlas/courses/<Name>`, ignoring
     `.git`), then `rm -rf ~/atlas-migration/courses.pre-fold`. The bundles in
     `~/atlas-migration/` stay.
   - **Removing a fenced subject**, when decided. The iPad refuses it. On the cluster, confirm no
     job, request or coding session is open for it, move its fenced data, results and .env where
     its data agreement says, then `git rm -r projects/<Name>`, commit and push from the cluster
     checkout.
2. **Code the cutover left behind**, now safe to remove:
   - The old-location claim fallback in `board/tutorboard/jobs.py`: `_old_claim_dirs`,
     `_old_live`, and `migrate_state` with its calls in jobs.py and colibri.py, which have
     nothing left to move. Remove board/test/jobs.py's TRD-EHR old-claims check with them; it
     reads `~/Archive/atlas-migration/2026-10-07/live-dirs.tgz`.
   - The `/research/` and `/practice/` rules in the root `.gitignore`, with the comment above
     them.

## 4. The owner's

- **Time Machine** has no destination (`tmutil destinationinfo` reports none). Set one.
- **Read `board/TEACHING.md` once.** Every turn is told to follow it.
- **The manuscript's code link.** These sentences point at
  `https://github.com/Pirate-Hunter-Zoro/Atlas/tree/main/projects/TRD-EHR`, which answers 200.
  Confirm their wording before submission. All are under `projects/TRD-EHR/paper1-trd-prediction/`:
  `manuscript.md:400`, `parts/manuscript/10-data-availability.md:12`, `cover_letter.md:89`,
  `tripod_ai_checklist.md:98`, `reserve/manuscript_reserve.md:335`.
- **Algo-Solutions.** `leetcode/totalbeauty` imports `algo-solutions/helpermath` and
  `algo-solutions/leetcode` without using them, so `go vet` and `go test` fail in that package.
- **TRD-EHR's TUTOR.md** is at 797 of 800 words. `board memo` refuses the next addition until it
  is trimmed.
- **The dimension-count versus best-k scatter.** Decide in a session whether it enters the k-sweep
  write-up. It stays out until then.
- **Subject READMEs and course `.tex` headers** link `AI_INSTRUCTIONS.md`, `HANDOFF.md` and
  `PROGRESS.md`, which do not exist. `RULES.md` and `TUTOR.md` hold their content. These are the
  owner's files, so the owner edits them.

## 5. Loose ends in the code

- The past-lessons path is unreachable: `openHistory`, `showSession` and `#history` in
  `board/web/board.js`, and `GET /archive` in `board/tutorboard/server/routes/lesson.py`.
- `board job` in a session with an open cluster coding session pins HEAD, so an uncommitted held
  file refuses it. The relay already accepts a pin on `code/<id>` (`code.pin_ok`); the Mac side
  does not file one.

## 6. On the glass

Built and not yet used for real. Strike each one after an evening on the iPad.

- Home: Continue rows, New session, the Courses and Projects lists, "+ new" with the patient-data
  question, and a subject delete with its typed name.
- A new session starts unbound; "this is for Topology" binds it and the subject chip updates.
- A generic lecture sent at End: the send picker, its filter, a new course made from it, and
  the wrap-up's write-up in that course. One that ended unbound, sent later from its chip.
- Who teaches, switched from the tutor's chip mid-session.
- The session header: subject chip, teach and do, Make, End. Teach and do persist until switched;
  a do turn runs `board check`.
- A `[job]` card waking the filing session when a cluster report lands, and a report reopening an
  ended session. A request filed with no session showing as a home notice.
- "Relay looks down", and the Colibri panel with its cold-start estimate.
- One document all the way round: Make, build, read, ink, "Say what's wrong", revise.
- Pinch-zoom on a paper and a deck in the one reader. Safari's own page zoom never starts, ink stays
  on its words, and one finger scrolls a zoomed page sideways.
- The round as pairs on the TRD-EHR manuscript, round 1 being the 09-29 round: tap the chip, a row
  and a pip, and mark pairs fine or not fixed.
- The meeting deck in projects/Meetings, written by a real turn, read and inked in the one reader.
- The notes canvas: a full-slate session whose End leaves a notes.md.
- Annotate a PDF: upload, ink, "Keep a marked copy", and the tutor files it.
- Delete from the iPad: a material, a document and a session, each with a second tap.
- A writeup appearing after hand-written answers in a project session, not a course.
- A code excerpt with `path#L` highlighted and numbered, opening the read-only source viewer.
- A `[code]` step card from `board code` on the cluster, started from the command the session
  header shows.
- Sending selected annotations.
- A response typing out, and the typed half of the answer panel, in a real session.
- Whether the verdict band and streak chip feel like information or like a scoreboard.

## 7. The work it is for

In this order. Each item's open tasks live in its subject's TUTOR.md.

1. **Paper 1** (`projects/TRD-EHR`, `paper1-trd-prediction/`). The writing happens on the Mac.
   Anything that reruns a model goes to the cluster as a request.
   - k-sweep across embedders: the section, Figure 5 and the cross-encoder figures are written.
     Open: the scatter decision (section 4), re-splitting `parts/`, and a teach session on the
     shape of the k-sweep.
   - Reviewer findings: the round-1 pairs on the manuscript, judged fine or not fixed; Martin's
     open questions; the TRIPOD+AI rows.
   - Consistency pass, after the reviewer findings: clarity, cross-document numbers, refs 10 and 12
     at proof, and a strict packet rebuild (`scripts/rebuild-packet.sh`, which runs `board build`).
2. **The Colibri deck** (`projects/libr-local-llm`): section 1.
3. **PSYCH-ASR grid sweep**, as cluster requests, and the owner's recording review at the
   institute.
4. **Paper 2** (`projects/TRD-EHR`, `paper2-counterfactual/`). Teach sessions on estimand
   identification, then coach sessions on the four robustness rungs. The owner writes that code on
   the Mac against `test_data/`, or on the cluster with `board code` when it needs real rows. Then
   build.
