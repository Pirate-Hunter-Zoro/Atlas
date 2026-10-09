# Tutor-Board

A live board for tutoring sessions. A tutor turn writes lesson cards into files; `serve.py`
pushes them to every browser holding the board open, where they render as typeset mathematics.
Handwriting, typed answers and photos travel back into an inbox the next turn reads. It runs on
the owner's Mac mini, the only machine where a model is called. The cluster keeps the data and
Slurm, and talks to the Mac only through git.

## Invariants

- **Stdlib only; add no runtime dependency.** The relay runs on a compute node with no `sudo`
  and possibly Python 3.7, and every dependency is one more thing to install there.
- **Never `git stash`.** A stash hides the owner's uncommitted work where nobody looks for it.
- **Edit the board in a worktree, never in the main checkout.** The main checkout serves the
  iPad live, so a half-finished edit there is a broken lesson now.
- **Bump `VERSION` in `web/sw.js` when a shell file changes.** Otherwise the installed app
  keeps serving its cached copy and the change is invisible.
- **Never read, list or copy anything under `phi/`, `results/`, or a directory named in
  `tutorboard/fenced.py` `NEVER`.** They hold identifiable patient data; existence checks only.
- **Never weaken the PHI guards:** `test/tracked.py`, `ai-config/policy/phi.py` fencing by
  name, the anchored `/phi/` ignores, `.githooks/commit-msg`, `jobs.NO_TURN`, and the rule that
  a Colibri task changing a tracked file fails. Each is the only thing standing between a
  mistake and a public commit.
- **Every commit is public.** Never commit a session, ink, an upload, a material, a third-party
  file, a log tail, a participant id or a lab storage path, because git keeps it forever.
- **Run `python3 board/test/run.py` before shipping, and leave it green.** It discovers every
  suite and runs four at a time; `--guards` runs only the PHI and relay guards, and a suite
  name runs that suite alone. A failing suite means the change is wrong, not the test.
- **Ship with `bash board/scripts/ship.sh "message"`.** It commits only `board/`, pushes, and
  restarts every running board, because a board keeps the code it started with and a commit
  alone changes nothing on the iPad.

## Layout

`serve.py` is the HTTP server; its routes, hub and spawning live in `tutorboard/server/`.
`bin/board` is the CLI a tutor turn and the owner use, and `bin/relay` is the cluster's
scheduled entry. `tutorboard/` holds the library: `lesson/` (cards, slate,
uploads, turns), `course/` (documents, homework, threads, the library), `net/` (Tailscale and
egress), and top-level modules for the relay, jobs, Colibri, holds, the brief and the PHI fence
(`fenced.py`). `web/` is the browser side (board, home and library pages, `sw.js`, vendored
KaTeX). `tex/board-macros.tex` is generated from `web/macros.js` by `tools/sync-macros.py`.
`scripts/` holds shipping, autostart (launchd, systemd) and node setup. `test/` holds one suite
per file, run by `test/run.py`. `TEACHING.md` is the method every tutor turn follows, and
`NOTICE.md` lists vendored third-party code and its licences.
