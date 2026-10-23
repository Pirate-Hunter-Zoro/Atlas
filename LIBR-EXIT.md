# LIBR exit

The prompt for removing LIBR, and the scrapped Paper-Writer, from Atlas. HANDOFF.md says when it
runs. Point a Claude Code session at this file and use ultracode.

Afterwards, Atlas is a Mac-only system. It has no compute node, relay, Slurm, cluster sync, PHI
machinery or vendored Colibri, and nothing LIBR is left in the tree. The one exception is
`courses/Colibri`, which teaches Colibri using LIBR's cluster as its example and names nothing
else of LIBR. Git history keeps the past. `main` stays the only branch, with no archive branch
or tag. The last commit deletes this file.

## Decided

- **Leaving:**
  - `projects/TRD-EHR`, `projects/PSYCH-ASR`, `projects/libr-local-llm` and `projects/Meetings`.
  - The meeting-deck feature.
  - `vendor/colibri` and `vendor/colibri-build`.
  - Every PHI guard, and the cluster.
- **Atlas stays public.** The TRD-EHR manuscript's code link pins a commit in this repository.
- **The public-repo gate stays** for what it guards besides PHI:
  - copyrighted course material (`textbook/`, `reading/`, `lectures/`, `assignment*`, `materials/`, `.ink/`);
  - keys;
  - audio and large binaries.
  `.githooks/pre-commit` refuses every commit when `audit.py` is missing, so audit.py is cut
  down, never deleted.
- **Colibri's source is not zipped.** It is a public Apache-2.0 upstream,
  `https://github.com/JustVugg/colibri.git`. Its pins are `bf2442915d6e3dd4cdfd2eb9c2a3d2aa44a25850`
  (vendor/colibri, v2.0.0) and `fd93c41aa6ae2c7d1cc1a1e2d6b79dbe6d341708` (colibri-build,
  v1.10.2). Record both in `VENDOR.txt` in the handoff folder.
- **TRD-EHR's zip includes `exports/`.** It is tracked, aggregate output, and it is the only result
  set on the Mac.
- **Sessions bound to a leaving subject go into that subject's zip**, under `sessions/`.
- **`fleet_walkthrough`** (LIBR's fleet proposal) leaves unfinished in libr-local-llm's zip.
- **`projects/Paper-Writer` is scrapped in the same run.** It is zipped with a bundle like the
  LIBR projects.
- **Bundles use `git-filter-repo`.** `brew install git-filter-repo` for the run, then
  `brew uninstall git-filter-repo` once every bundle verifies.

## Before anything

- Run from the owner's terminal session, never a tutor turn. `audit.turn_refusals` refuses
  deleting `tutorboard.json` and `RULES.md`.
- These must already be done:
  - HANDOFF's Galois rescue and Colibri course. The deck and the lesson session live in
    `courses/Colibri`, and nothing of the owner's coursework is left in a leaving project.
  - HANDOFF's "Sync without the cluster". `board/tutorboard/sync.py` exists, `code.py` imports
    neither relay nor exports, and `cluster.py` is a thin re-export.
  - The owner's section 5a. The merge deletes `relay-pass.sh`, which the cluster's scrontab runs
    every 2 minutes.
- Every owner decision is made (above and in HANDOFF.md). Ask nothing. Stop only at the owner's
  steps: 5a before starting, and 5b in section 2.
- Re-inventory first. This file gives the shape and the known callers, but line numbers drift, so
  find everything by name. Build in a worktree, `~/Developer/Atlas-wt/libr-exit`. Run
  `python3 board/test/run.py`, review adversarially, then merge. The merge restarts the live
  board, so never merge during a lesson.

## 1. Before the zips

- **The manuscript's code link.** Six URLs in five files under
  `projects/TRD-EHR/paper1-trd-prediction/` point at `tree/main/projects/TRD-EHR`, which 404s
  after the purge. The files are `manuscript.md`, `parts/manuscript/10-data-availability.md`,
  `cover_letter.md`, `tripod_ai_checklist.md` and `reserve/manuscript_reserve.md`.
  - Repoint them at `tree/<sha>/projects/TRD-EHR`, where `<sha>` is the commit before this edit.
    It has the same tree.
  - Rebuild the packet with `projects/TRD-EHR/scripts/rebuild-packet.sh`, push, and confirm the
    URL answers 200.
  - Never force-push afterwards, because that would orphan the SHA.
- **End every open session bound to a leaving subject.** Today that is `20261009-193922-3`
  (TRD-EHR, "imported").
- **Delete any `code/*` refs left on origin.**

## 2. Zips

Write these to `~/LIBR-handoff-<date>/`, outside the repository:
- one `<Project>.zip` and one `<Project>.bundle` for TRD-EHR, PSYCH-ASR, libr-local-llm and
  Paper-Writer;
- `SHA256SUMS`;
- `VENDOR.txt`;
- `README.txt`.

Meetings is empty and needs no zip.

- **Zip the working tree, not `git archive`.** Built PDFs, `.ink/`, feedback rounds, `docs/` and
  uncommitted edits exist only there. Expect roughly:
  - TRD-EHR: 65 MB, 560 files.
  - libr-local-llm: 14 MB.
  - PSYCH-ASR: 1.5 MB.
  - Paper-Writer: 4.8 MB.
- **Leave out** `.venv`, `__pycache__`, `.pytest_cache` and `relay/state`.
- **Add each bound session**, copied from `sessions/<id>/`.
- **The bundle carries the project's full history.** TRD-EHR and PSYCH-ASR lived under
  `research/<P>` before commit 1c154308. `git subtree split` keeps only the commits after the
  move, so filter over both paths. libr-local-llm and Paper-Writer only ever lived under
  `projects/`. Expect about 621, 86 and 144 commits for the first three; count Paper-Writer's
  with `git log --oneline -- projects/Paper-Writer`.
- **Never put these in a zip:** `phi/`, `results/`, `.env` or keys. The Mac holds none of them;
  check anyway.
- **`README.txt` says which results exist only on the cluster.** They are TRD `results/` (about
  1.5 GB), the PSYCH-ASR Stage 1 grid outputs and the P0 job logs. The owner moves them under
  section 5b.
- **Verify each zip:**
  - unzip it to scratch and compare file counts;
  - run `git bundle verify`;
  - compare commit counts;
  - confirm `git log --name-only` shows only that project's paths.
- **Tell the owner to copy the folder to a second disk.** Time Machine has no destination.
- **Clear the main checkout's tracked changes in the leaving projects.** Once every zip
  verifies, run `git restore --staged --worktree -- projects/TRD-EHR projects/PSYCH-ASR
  projects/libr-local-llm projects/Meetings projects/Paper-Writer`. Otherwise the merge refuses
  to overwrite them. Their content is in the zips.
- **Stop here.** The owner does section 5b, then says so. The merge waits for that.

## 3. The Mac-only system

Guards fail closed, so callers and registrations go before the files they name.

1. **Rewire callers off the cluster modules.**
   - `bin/board`:
     - its top-level `jobs` and `exports` imports, which break every command on a partial delete;
     - `cmd_job` (with `diagnose`), `cmd_ask_cluster`, `cmd_colibri` and `cmd_libr_ai`;
     - their docstring lines and their `NO_LIVE` and `SUBJECT_ONLY` entries;
     - `cmd_brief`'s repair branch.
   - Server and runner:
     - `server/app.py`: `slurm_here`, and the sync start, which reads `TUTORBOARD_SYNC` only.
     - `hub.py`: the `relay`, `jobs` and `colibri` payload keys.
     - `routes/machines.py`: `GET /relay.json` and `POST /colibri`.
     - `brief.py`: `jobs.outstanding`, the HEALTH lines and the repair section.
     - `handler.py`: the `cluster` import, and the `/relay.json`, `/colibri` and `/meeting`
       registrations.
     - `runner/turn.py` and `runner/loop.py`: `jobs.REPAIR`, `batch_repairs` and `records`.
   - Subject and session code:
     - `subjects.py`: the `jobs.outstanding` delete blocker and the "cluster runbook" wording.
     - `sessions.py` and `gitops.py`: wording only.
   - `code.py`:
     - `pin_ok`, which only `jobs.check` calls;
     - the held-path acceptance;
     - `CHANNEL`;
     - the cluster wording.
   - Smaller pieces:
     - `audit.py`: the `relay.exports` refusal and the `exports/` skip.
     - `course/config.py`: the `relay` key.
     - `paths.EXPORTS`/`exported`, and the `exports/results` twins in `course/library.py` and
       `build.py`.
     - `agents/recipes.in_fence` and `private` recipes.
     - `machine.slurm_nodes` and `machine_shape`, plus bin/board's `machine_shape` wrapper and the
       `shape:` line in `machine_check`, which `board doctor` prints.
     - `install.sh`'s `chmod` of `bin/relay`.
     - `tutorboard/__init__.py`'s docstring.
2. **What survives.**
   - In `sync.py`:
     - drop the `jobs.hear` call and the `TUTORBOARD_CLUSTER` fallback;
     - `relay.pull_health` moves in;
     - a `health()` returns the not-synced lines plus `brewcare.lines`, served as
       `GET /sync.json`, which replaces `/relay.json`.
   - Home's `#health` and the board's `#healthbar` stay, relabelled "sync".
   - Notices stay: `sync.wake` and `sync.notices`.
   - `relay.pull_vendor` is deleted, not moved.
3. **Delete the cluster code.**
   - Modules and commands: `relay.py`, `jobs.py`, `colibri.py`, `libr_ai.py`, `exports.py`,
     `cluster.py`, `bin/relay` and `cluster/lib`.
   - Board scripts: `relay-pass.sh`, `libr-ai-task.sh` and `libr-ai-task.json`,
     `install-autostart.sh` (with test/node.py's check), `move-residue.sh` (with
     test/move_residue.py) and `phi-probe.sh`.
   - Setup: both `setup-cluster.sh` files, and `scripts/setup.sh`'s Slurm and non-Darwin branches.
   - Relay conventions: the root `relay/` (with `relay/status.json`), and the subjects' `relay/`
     and `exports/` conventions.
   - Web: the Colibri panel, job cards, the job-waiting strip and the repair prompt.
   - Python 3.7: the rule and `test/py37.py`.
   - `.gitignore`: the relay-state, `.nfs*`, `/research/` and `/practice/` rules.
   - The `test/run.py` `GUARDS` entries for deleted suites.
4. **Vendor.**
   - Delete `.gitmodules`.
   - In the code, delete `gitops._vendor_moved` and the submodule block in `gitops.pull`, and
     `bootstrap.sh`'s submodule fill.
   - In the docs and tests, delete `--recurse-submodules` from README's clone lines and the vendor
     fixtures in `test/gitremote.py` and `test/commands.py`. Retire `test/truthful.py`'s
     `~/colibri*` targets.
   - In the main checkout, run `git submodule deinit -f --all` before the merge. Without it the
     merge leaves `?? vendor/`. *After the merge* removes the rest.
   - `setup-mac.sh` does the same once on any clone where `.gitmodules` is gone and
     `.git/modules/vendor` exists.
5. **PHI, all of it.**
   - First move what is not PHI. `leaving.uncommitted` and `leaving.git_here` are generic git
     checks: move them into `gitops.py`, and re-point `course/ledger.py` (a round's snapshot) and
     `routes/library.py` (the overhaul guard). Move `fenced.RESULT_DIRS` into `course/library.py`
     as its `LOOK_IN`.
   - Then remove every remaining `fenced.` and `leaving.` use, found with
     `git grep -n -E '\b(fenced|leaving)\b' -- board scripts`, not from this list. Known users:
     - top-level imports in `bin/board`, `lesson/git.py` (the push-time scan) and
       `routes/library.py`;
     - `code.py`, where `output_open` then always shows check output;
     - `seeing.py`, `briefs.py`, `audit.py`, `sessions.py`, `sense.py`, `artifacts.py` and `hub.py`;
     - `routes/pages.py`, `course/library.py`, `course/walk.py`, `course/burn.py` and
       `course/ledger.py`;
     - `sync.py`'s fence filter, `web/library.js` and `test/tracked.py`.
   - Delete `fenced.py` and `leaving.py` last.
   - Drop `setup-mac.sh`'s `ai-config/policy/phi.py` check, and the PHI rules and comments in
     the root `.gitignore`.
   - In `audit.py`, delete the participant scan, `says_phi_true`, the `phi` change refusal, the
     held-name walk and the ai-config policy load. Keep the copyright, key and binary refusals.
   - Delete the `phi` key: `course/config.read_config`, `subjects.create`, the home "+ new"
     patient-data question in `home.js`, the phi-subject delete refusal, and `phi` in every
     staying subject's `tutorboard.json`.
   - Delete the PHI-only tests, and the PHI paragraphs in README's hard constraints and the board
     docs.
   - `~/.claude/hooks/block-phi.py` is a symlink into ai-config, and a registered hook whose
     target is missing blocks every tool call. The owner unregisters it in ai-config before its
     target goes (section 4). Leave it alone in the tree.
6. **Meetings and the meeting deck.**
   - Delete the deck code:
     - `briefs.py`'s deck: `MEETINGS`, `SLUG`, `meetings_root` and their users.
     - `bin/board`'s `cmd_meeting`, with its COMMANDS and SUBJECT_ONLY entries.
     - `POST /meeting` in `routes/machines.py`, and `ask_meeting`/`meeting_deck` in
       `routes/library.py`.
     - `/subjects.json`'s `meetings`, and the home meeting UI.
     - The meeting-deck rules in the root `.gitignore`.
   - Delete `test/meeting.py` and the meeting cases in other suites.
   - Keep `briefs.tutor_diff` only if something besides the deck uses it.
7. **Purge.**
   - In the worktree, run `git rm -r projects/TRD-EHR projects/PSYCH-ASR projects/libr-local-llm
     projects/Meetings projects/Paper-Writer`.
   - The main checkout's ignored leftovers (`.venv`, `docs` builds, `.ink`, `relay/state`) survive
     the merge, and `subjects.walk` lists any directory under `projects/` as a subject. So
     *After the merge* deletes them outright.
   - `setup-mac.sh` does the same once on other clones: it deletes any of those five, or
     `projects/Lean-Theorem-Proving`, that holds no tracked file, and prints what it deleted.
   - Paper-Writer's dependents outside it:
     - `build.py` keeps its markdown converter but stops calling it a copy of Paper-Writer's.
     - `agents/oneshot.py` and `board/README.md` stop naming Paper-Writer's daemon and
       unittests.
     - Synthetic test subjects named Paper-Writer (`test/briefs.py`, `test/mode.py`,
       `test/subjects.py`) take a neutral name, and `test/truthful.py` drops `~/Paper-Writer`.
     - The Brewfile keeps `font-dejavu`, commented as `board build`'s PDF face.
8. **LIBR text in staying subjects.**
   - `courses/Colibri` may name LIBR's cluster (partitions, node names, the A40s) as its example.
     It names no lab storage path, person or dataset.
   - `git grep -n -i -w -E 'libr|trd-ehr|psych-asr|slurm|scrontab|relay|colibri|cluster|phi|fenced|meetings?|ehr_study' -- . ':!courses/Colibri' ':!HANDOFF.md' ':!LIBR-EXIT.md'`
     prints nothing that describes the current system. List any remaining hit with its reason in
     the final report.
9. **Tests.** First move `test/jobs.py`'s per-subject marker check (each code marker has a
   `check`, and `pyproject.toml` has a `uv.lock` beside it) into `test/subjects.py`. Then delete
   tests of removed behaviour. Board suites use synthetic subjects, and
   subject-owned suites under `tests/board/` disappear with their subjects. `python3
   board/test/run.py` passes.
10. **Docs.**
    - README.md, board/README.md, board/TEACHING.md and HANDOFF.md describe the Mac-only system in
      present tense.
    - `test/truthful.py` section 4 fails on any core doc that still names `board job`, `board
      colibri` or `board libr-ai`. Rewrite TEACHING.md's "Check, push and run on the cluster" and
      board/README.md's relay sections in the same commit.
    - `truthful.py` and `teaching.py` stay green. Delete this file.
11. **Never zip, move or delete `ai-config/`, and never move the Atlas checkout.**

After the merge, in the main checkout:
- Run `rm -rf projects/TRD-EHR projects/PSYCH-ASR projects/libr-local-llm projects/Meetings
  projects/Paper-Writer` and `rm -rf .git/modules/vendor vendor`. Done when `ls projects` shows
  only Spirit-Forge.
- Run `bash board/install.sh` so the LaunchAgent carries `TUTORBOARD_SYNC`. Done when
  `launchctl print gui/$(id -u)/tutor-board` shows it and `~/.local/state/tutor-board/pull.json`
  updates.
- `git status --porcelain` names no path under the purged projects, `vendor/` or `relay/`, and
  nothing this run created. The owner's own uncommitted work is left as it was.
- The iPad home lists no leaving subject.

## 4. Outside the tree

The owner edits these, all after the merge and the main checkout's cleanup. HANDOFF item 1 has
already copied the policy files into `courses/Colibri/materials/policy/`. In ai-config,
unregister `block-phi.py` in the Claude settings before deleting `policy/phi.py` or the
adapters. The session lists what it finds.

- **ai-config:**
  - `shell.sh`'s NFS wrappers.
  - The systemd timers: port the daily audit and CLI updates to launchd.
  - The egress and LOCAL-MODELS fence, the lab-path deny rules and the `~/Atlas` paths.
  - `policy/phi.py` and the PHI hook adapters.
  - `README.md`'s Colibri line.
- **`~/.claude/CLAUDE.md`'s "AI Providers: None Is Load-Bearing" section.** It names the
  cluster, PHI, Colibri and `projects/libr-local-llm/docs/deepseek-egress.md`. Also
  `~/.config/opencode/AGENTS.md`.
- **Memory notes that name the cluster, LIBR or Colibri's data access**, in
  `~/.claude/projects/-Users-mikeyferguson-Developer-Atlas/memory/`.
- **Leftover config and files:**
  - the dead `serve_partition`, `serve_time`, `serve_cpus` and `serve_mem` keys in
    `~/.config/tutor-board/config.json`;
  - `~/.local/state/tutor-board/scrontab.*`;
  - `~/Archive/atlas-migration/`.

## 5. The cluster

These are the owner's steps; agents never ssh.

**5a, before the session starts:**
- Remove the relay's scrontab entry.
- Confirm `squeue -u $USER` shows nothing Atlas started, and cancel any job that remains.
- Close open requests.

**5b, after section 2's zips verify and before the merge:**
- Move `phi/`, `results/` and `.env` where each data agreement says. Seed the owner's own LIBR
  repository from the bundles.
- Delete `~/.config/libr-ai/key`.
- Log out of every CLI, because tokens are group-readable on NFS.
- Check nothing in `~/atlas-migration/courses.pre-fold/<Name>` is missing from
  `~/Atlas/courses/<Name>` (`diff -rq`, ignoring `.git`). Then delete `courses.pre-fold`.
- Delete `~/Atlas`, including the ignored Lean `.lake/` (about 14 GB).
