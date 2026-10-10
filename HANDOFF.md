# HANDOFF: what is left

Work still to do, and nothing else. Delete an item when it lands. Agents never ssh to the cluster:
cluster steps are the owner's.

## 1. After the cutover

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

## 2. The owner's

- **Time Machine** has no destination (`tmutil destinationinfo` reports none). Set one.
- **Read `board/TEACHING.md` once.** Every turn is told to follow it.
- **The manuscript's code link.** These sentences point at
  `https://github.com/Pirate-Hunter-Zoro/Atlas/tree/main/projects/TRD-EHR`, which answers 200.
  Confirm their wording before submission. All are under `projects/TRD-EHR/paper1-trd-prediction/`:
  `manuscript.md:378`, `parts/manuscript/10-data-availability.md:12`, `cover_letter.md:89`,
  `tripod_ai_checklist.md:98`, `reserve/manuscript_reserve.md:335`.
- **Algo-Solutions.** `leetcode/totalbeauty` imports `algo-solutions/helpermath` and
  `algo-solutions/leetcode` without using them, so `go vet` and `go test` fail in that package.
- **TRD-EHR's TUTOR.md** is at 797 of 800 words. `board memo` refuses the next addition until it
  is trimmed.
- **The dimension-count versus best-k scatter.** Decide in a session whether it enters the k-sweep
  write-up. It stays out until then.
- **The provider.** `~/.config/tutor-board/config.json` sets `provider` deepseek and no
  `fallback`, so a limited provider has nowhere to fall back to. Set `fallback` if that is not
  intended. Its `default_agent` key is ignored.
- **Subject READMEs and course `.tex` headers** link `AI_INSTRUCTIONS.md`, `HANDOFF.md` and
  `PROGRESS.md`, which do not exist. `RULES.md` and `TUTOR.md` hold their content. These are the
  owner's files, so the owner edits them.
- **Decide: when the wrap-up's TUTOR.md edit is committed.** End commits TUTOR.md, then queues the
  wrap-up turn. The wrap-up's edit therefore waits for the next commit or a second End.

## 3. Loose ends in the code

- The handover button ("you do this step") shows only when `aim` is `coach`, and nothing sets
  `aim`. It never shows. Key it on mode teach (`coaching` in `board/web/board.js`).
- The past-lessons path is unreachable: `openHistory`, `showSession` and `#history` in
  `board/web/board.js`, and `GET /archive` in `board/tutorboard/server/routes/lesson.py`.
- `board job` in a session with an open cluster coding session pins HEAD, so an uncommitted held
  file refuses it. The relay already accepts a pin on `code/<id>` (`code.pin_ok`); the Mac side
  does not file one.
- The pre-commit hook does not refuse held paths. Only `gitops.commit` does, so a turn running
  raw `git commit` is not stopped.

## 4. On the glass

Built and not yet used for real. Strike each one after an evening on the iPad.

- Home: Continue rows, New session, the Courses and Projects lists, "+ new" with the patient-data
  question, and a subject delete with its typed name.
- A new session starts unbound; "this is for Topology" binds it and the subject chip updates.
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

## 5. The work it is for

In this order. Each item's open tasks live in its subject's TUTOR.md.

1. **Paper 1** (`projects/TRD-EHR`, `paper1-trd-prediction/`). The writing happens on the Mac.
   Anything that reruns a model goes to the cluster as a request.
   - k-sweep across embedders: the section, Figure 5 and the cross-encoder figures are written.
     Open: the scatter decision (section 2), re-splitting `parts/`, and a teach session on the
     shape of the k-sweep.
   - Reviewer findings: the round-1 pairs on the manuscript, judged fine or not fixed; Martin's
     open questions; the TRIPOD+AI rows.
   - Consistency pass, after the reviewer findings: clarity, cross-document numbers, refs 10 and 12
     at proof, and a strict packet rebuild (`scripts/rebuild-packet.sh`, which runs `board build`).
2. **The Colibri deck** (`projects/libr-local-llm`). Teach sessions on the PHI path and the LIBR
   hardware first, so the owner can defend every slide. Then Make, Deck.
3. **PSYCH-ASR grid sweep**, as cluster requests, and the owner's recording review at the
   institute.
4. **Paper 2** (`projects/TRD-EHR`, `paper2-counterfactual/`). Teach sessions on estimand
   identification, then coach sessions on the four robustness rungs. The owner writes that code on
   the Mac against `test_data/`, or on the cluster with `board code` when it needs real rows. Then
   build.
