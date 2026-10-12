# LIBR exit

The prompt for the day the owner leaves LIBR. Point a Claude Code session at this file. It
leaves Atlas a Mac-only system: no compute node, relay, Slurm or cluster sync, and nothing LIBR in
the current tree. Git history keeps the past; `main` stays the only branch, with no archive branch
or tag. The last commit deletes this file.

## Before anything

- Run from the owner's terminal session, never a tutor turn: `audit.turn_refusals` refuses deleting
  `tutorboard.json` and `RULES.md`.
- Confirm the Colibri deck and its revise rounds are finished. The deck lives in
  `projects/libr-local-llm` and leaves with it.
- Confirm the cluster steps (section 5) are done. The merge deletes `relay-pass.sh`, which the
  cluster's scrontab runs every 2 minutes, and a cluster pull deletes tracked files while `phi/`,
  `results/` and `.env` stay behind.
- Ask the owner, in one AskUserQuestion:
  - PHI machinery: keep the generic public-repo gate and `fenced.py` and remove the LIBR-specific
    parts (participant scan, PSYCH-ASR patterns, egress fence, in-fence recipe, libr-ai gating),
    or remove all of it.
  - Which `projects/Meetings` documents are LIBR's, and whether its `phi` becomes `false`.
  - Paper-Writer's `REFERENCE_MANUSCRIPT` fixture quotes the TRD manuscript: replace or delete.
  - Sessions bound to leaving subjects: into the zips, or the trash.
  - History rewriting tool: `git-filter-repo` (a Brewfile line) or a standard-library
    fast-export filter.
  - Whether Atlas stays public. Its only stated reason was the TRD-EHR manuscript's link.
- Use ultracode. Re-inventory first: this file gives the shape, not the census. Build in a worktree
  under `~/Developer/Atlas-wt/`, run `python3 board/test/run.py`, review adversarially, then merge.
  The merge restarts the live board, so never during a lesson.

## 1. Zips

Leaving: `projects/TRD-EHR`, `projects/PSYCH-ASR`, `projects/libr-local-llm`. `vendor/colibri`
stays.

- Write `~/LIBR-handoff-<date>/<Project>.zip` and a `SHA256SUMS`, outside the repository.
- Zip the working tree, not `git archive`. Built PDFs, feedback ledgers, `.ink/` and uncommitted
  edits exist only there. Leave out `.venv`, `__pycache__` and `relay/state`.
- Add `<Project>.bundle` with the project's full history. TRD-EHR and PSYCH-ASR lived under
  `research/<P>` before commit 1c154308, and `git subtree split` keeps only commits after the move,
  10 of TRD-EHR's 610. Filter over both paths. libr-local-llm only ever lived under `projects/`.
- Never in a zip: `phi/`, `results/`, `.env`, `exports/results`, keys. The Mac holds no PHI; check
  anyway.
- Verify each: unzip to scratch and compare file counts, `git bundle verify`, compare commit counts,
  and confirm `git log --name-only` shows only that project's paths.

## 2. Before the purge commit

- The manuscript's code link. Six URLs in five sources under
  `projects/TRD-EHR/paper1-trd-prediction/` point at `tree/main/projects/TRD-EHR`, which 404s
  after the purge: `manuscript.md:400`, `parts/manuscript/10-data-availability.md:12`,
  `cover_letter.md:89`, `tripod_ai_checklist.md:98`, `reserve/manuscript_reserve.md:335`.
  Repoint them at `tree/<sha>/projects/TRD-EHR`, where the SHA is the commit before the edit
  (same tree). Rebuild the packet with `scripts/rebuild-packet.sh`, push, and confirm the URL
  answers 200. A force-push afterwards would orphan that SHA, so there is none. If a lab-owned
  repository hosts the code instead, the owner names it.
- End the open sessions bound to leaving subjects (`20261009-193922-3` on TRD-EHR,
  `20261009-193922-5` on libr-local-llm), or package them per the owner's answer.
- Delete any `code/*` refs left on origin.

## 3. The Mac-only system

Guards fail closed, so callers and registrations go before the files they name.

1. **Rewire callers** off the cluster modules: `bin/board` (its top-level imports of `jobs` and
   `exports` break every command on a partial delete), `server/app.py`, `hub.py`,
   `routes/machines.py`, `handler.py`, `brief.py`, `runner/turn.py`, `runner/loop.py`,
   `subjects.py`, `sessions.py`, `gitops.py`.
2. **Move what survives:**
   - `cluster.Ear` becomes `tutorboard/sync.py`: ls-remote of `main` and `code/*` (laptop coding
     sessions push those), the fast-forward pull, ai-config sync, `pull.json`, and
     `relay.pull_health`. It is the Mac's only automatic pull. Rename `TUTORBOARD_CLUSTER`.
   - `relay.pull_vendor` moves into `sync.py` as a daily `vendor/colibri` bump. It runs on the
     board machine only, and only when `vendor/colibri` is the sole dirty path, HEAD equals
     `origin/main` after a fetch, and git is neither mid-merge nor detached. It commits and pushes.
   - `board check`'s spec helpers (`code.check_spec` and its neighbours, `exports.rel`) move to
     `tutorboard/check.py`.
   - `code.py` keeps the coding-session protocol for the Mac and laptops. Only `pin_ok`, the relay's
     held-path acceptance and the cluster wording go.
3. **Delete:** `relay.py`, `jobs.py`, `colibri.py`, `libr_ai.py`, `exports.py`, `cluster.py`,
   `bin/relay`, `cluster/lib`, `board/scripts/relay-pass.sh`, both `setup-cluster.sh`,
   `scripts/setup.sh`'s Slurm branches, the root `relay/`, `vendor/colibri-build` with its
   `.gitmodules` entry, the subjects' `relay/` and `exports/` conventions, the web layer's relay
   health strip, Colibri panel, job cards and notices, the repair prompt, the Python 3.7 rule with
   `board/test/py37.py`, and Lean's `slurm_jobs/` with its `setup.sh` cluster branch.
4. **Tests:** delete the cluster tests. Convert every test that reads a leaving subject from the real
   tree (`writing_up.py`, `rules_fence.py`, `exporting.py` and whatever the census finds) to fixtures.
5. **PHI**, per the owner's answer. `~/.claude/hooks/block-phi.py` is a symlink into ai-config, and a
   registered hook with a missing target blocks every tool call. The pre-commit hook refuses every
   commit when `audit.py` is missing.
6. **Purge** the leaving subjects with `git rm -r`, then delete the directories outright.
   `subjects.walk` lists any directory under `projects/` as a subject, and ignored `.venv`, `docs`
   and `relay/state` survive `git rm`.
7. **LIBR text in staying subjects:** Algo-Solutions `README.md:78-89` (lab paths), the Lean
   README and TUTOR.md cluster text, Paper-Writer's TRD examples and fixture, the Meetings
   documents the owner named.
8. **Other clones:** a pull there leaves the `vendor/colibri-build` checkout, its `.git/modules`
   entry and the purged project directories. `sync.py` or `setup-mac.sh` removes them, and
   `gitops.pull`'s vendor update must not fail on the removed submodule.
9. **Docs:** README.md, board/README.md, board/TEACHING.md and HANDOFF.md describe the Mac-only
   system in present tense. `truthful.py` and `teaching.py` stay green. Delete this file.
10. Never zip, move or delete `ai-config/`, and never move the Atlas checkout.

## 4. Outside the tree

The owner edits these; the session lists what it finds.

- ai-config: `shell.sh`'s NFS wrappers, the systemd timers (port the daily audit and CLI updates
  to launchd), the egress and LOCAL-MODELS fence, lab-path deny rules, `~/Atlas` paths.
- `~/.claude/CLAUDE.md`'s AI Providers section and `~/.config/opencode/AGENTS.md`.
- Memory notes that name the cluster or LIBR, in
  `~/.claude/projects/-Users-mikeyferguson-Developer-Atlas/memory/`.
- `~/.local/state/tutor-board/scrontab.*` and `~/Archive/atlas-migration/`.

## 5. The cluster

The owner's; agents never ssh. Done before the merge: remove the relay's scrontab entry, cancel
jobs, close open requests, move `phi/`, `results/` and `.env` where each data agreement says,
delete `~/.config/libr-ai/key`, log out of every CLI (tokens are group-readable on NFS), then
delete `~/Atlas`.
