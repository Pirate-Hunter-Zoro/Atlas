# Atlas

Every course and project I work on, in one public repository, with a tutoring board that
teaches it, codes it, writes it up and sends long work to the cluster.

The board is `board/`. Its own README, [board/README.md](board/README.md), covers processes,
sessions, the relay and the invariants. How a tutor turn teaches is
[board/TEACHING.md](board/TEACHING.md).

## Hard constraints

- **The repository is public.** Every commit is published the moment it is pushed, and git
  keeps it forever. The TRD-EHR manuscript links here, so it stays public.
- **No PHI in git.** Patient data lives only on the cluster, in ignored `phi/` and `results/`
  directories. Anchored ignore rules, `.githooks/pre-commit` and `board/test/tracked.py` each
  refuse it on their own, because any one guard can be deleted by accident.
- **No AI provider is load-bearing.** Every AI use in Atlas reads one provider table and walks
  it in order, so any provider can be added, removed, or go away. DeepSeek on the Mac mini alone
  runs all of it. The README in `board/` says how to add one.
- **No hosted model reads PHI**, and the system never runs one at the cluster: the relay refuses
  a `turn` request. `claude` or `codex` may be installed there for the owner's own use. The one
  model beside the data is Colibri, which is local; IT's model server takes work only from
  subjects with no PHI. DeepSeek is blocked from the compute nodes
  (`projects/libr-local-llm/docs/deepseek-egress.md`), and nothing works around that.
- **The Mac is the only brain.** Every model turn, compile and deck runs on the Mac mini.
  The cluster runs Slurm jobs and the relay, nothing else.
- **Commits are authored by the owner.** `.githooks/commit-msg` strips assistant trailers.

## Layout

```
Atlas/
  README.md  LICENSE  NOTICE.md  HANDOFF.md  Brewfile
  scripts/setup-mac.sh   sets the Mac up, or brings it up to date: the one command there
  scripts/setup-cluster.sh  the same on the cluster, from a compute node
  scripts/setup.sh       builds every subject's environment; both of the above run it
  .githooks/             pre-commit (the public-repo gate) and commit-msg
  board/                 the tutoring board: server, CLI, relay, web client, tests
  vendor/                other people's repositories, as submodules
  ai-config/             the AI assistant configuration; a private repository, ignored here
  relay/status.json      the cluster relay's health, committed by the relay on change
  sessions/<id>/         tutoring sessions; Mac only, ignored
  courses/<Name>/        one directory per course
  projects/<Name>/       one directory per project
```

A **subject** is any directory directly under `courses/` or `projects/`. Its kind is its
parent. Nothing lists the subjects: `mkdir projects/X` makes a project, because a registry is
a file somebody forgets to edit. `ls courses projects` or the board's home screen shows them.

Inside a subject:

| Path | What it is | Tracked |
| --- | --- | --- |
| `tutorboard.json` | `name`, `phi`, `check`, `relay` | yes |
| `RULES.md` | the owner's standing rules; a tutor turn may not commit it | yes |
| `TUTOR.md` | the tutor's memory, written only with `board memo` | yes |
| `README.md` | the owner's own notes; never fed to a turn | yes |
| `docs/<slug>/` | an artifact: `doc.json` plus its source | yes |
| `relay/requests/`, `relay/reports/`, `exports/` | the cluster channel | yes |
| `materials/`, `.ink/` | uploaded and third-party files, and ink on documents | no |
| `relay/state/` | the relay's job registry and Colibri queue | no |
| `phi/`, `results/`, `.env` | cluster data; never read by an agent | no |

`phi` gates what leaves the cluster. Check output and log excerpts cross only when
`tutorboard.json` sets `phi` to `false` literally, on disk and at HEAD.

`projects/Meetings/` is a PHI subject and holds the meeting deck at `docs/meeting/`.

Textbooks, lecture slides, assignment handouts, `materials/` and session uploads are ignored.
Worked solutions, write-ups and the owner's handwritten answers are tracked.

## The Mac and the cluster

The two machines never talk directly. GitHub is the only channel: `main`, plus one
`code/<session-id>` branch per open cluster coding session.

| | Mac mini (home) | Cluster (institute) |
| --- | --- | --- |
| Runs | the board server, every model turn, every build | Slurm jobs, and the relay every 2 minutes from scrontab |
| Models | every provider in the table, in order: DeepSeek through `opencode`, `claude`, `codex` | Colibri and IT's model server, each as a relay task |
| Holds | Atlas, sessions, materials, ink | Atlas, `phi/`, `results/`, model weights |

- The Mac pushes a request under `<subject>/relay/requests/`. The relay pulls it, checks it,
  submits it to Slurm and pushes a report. The Mac hears the report and wakes the session that
  filed it.
- A failed job is repaired on the Mac, by up to three repair turns. No model runs beside the
  data.
- To code at the cluster, the owner runs `board code <session> <paths>` in a cluster terminal.
  Each pause becomes a step on `code/<session>`, and the tutor on the Mac answers on the iPad.

The iPad reaches the Mac over the owner's tailnet. Nothing on the cluster serves a board.

## Setting up the Mac

```
git clone --recurse-submodules https://github.com/Pirate-Hunter-Zoro/Atlas.git
cd Atlas && bash scripts/setup-mac.sh
```

`setup-mac.sh` is also how an existing Mac is brought up to date; a second run changes nothing.
It pulls main, runs `board/bootstrap.sh`, runs `scripts/setup.sh`, has tailscale serve the
board, and checks that the board answers. Its header lists each step.

- `bootstrap.sh` fills `vendor/`, clones `ai-config/`, sets `core.hooksPath` to `.githooks/` by
  absolute path, and runs `board/install.sh`. That links `board` into `~/.local/bin` and installs
  the one LaunchAgent, `tutor-board`, which keeps `board/serve.py` up on port 8778.
- `scripts/setup.sh` runs `brew bundle` on the Brewfile, then builds each subject's
  environment from what it holds (`pyproject.toml`, `lean-toolchain`, `go.mod`).
- Turn on automatic login, so the LaunchAgent comes back after a reboot.
- The providers are set in `~/.config/tutor-board/config.json` (`provider`, optional
  `fallback`, `vision_agent`, extra `agents`); keys sit in `~/.config/tutor-board/keys.env`.
  Both stay off the tree.
- `board doctor --dry` reports what the machine has without spending a turn.
- Step 4 installs the assistant CLIs and links `ai-config` (see *Assistant CLIs*). Log in to
  each one you use, once.

On the iPad, open the tailnet address in Safari and use Share, then Add to Home Screen.

## Setting up the cluster

```
git clone --recurse-submodules https://github.com/Pirate-Hunter-Zoro/Atlas.git ~/Atlas
cd ~/Atlas && bash scripts/setup-cluster.sh
```

Run it on a compute node (`salloc`, then ssh to the node), never on `submit0`. It is also how the
cluster is brought up to date. It pulls main, runs `board/scripts/setup-cluster.sh` (bootstrap,
ai-config, the relay's scrontab entry, origin), runs `scripts/setup.sh`, checks the PHI guards,
submits `projects/Lean-Theorem-Proving/slurm_jobs/build_mathlib.sbatch` when Mathlib is not built,
and runs one relay pass. No board and no LaunchAgent is installed there, and nothing in setup
needs a hosted model's login.

- Step 5 installs the assistant CLIs and links `ai-config` (see *Assistant CLIs*). Log in to
  each one you use, once; nothing in setup or the relay needs a login.
- The relay's scrontab entry runs `board/scripts/relay-pass.sh` every 2 minutes.
- The cluster blocks `dl.google.com` and Mathlib's cache host. So Go comes from conda-forge into
  `~/.local/goenv` with `GOPROXY=direct`, and Mathlib is compiled by the job above.
- `vendor/colibri-build` is built by hand; `projects/libr-local-llm/README.md` has the line.
- The cluster's `python3` may be 3.7, so relay-path code avoids newer syntax.
  `board/test/py37.py` enforces it.

## Assistant CLIs

Every assistant is one descriptor in `ai-config/assistants/<name>.sh`: where it keeps its
config, its PHI hook, and how to install, update and run it. The scripts that act on the
descriptors name no vendor, so adding an assistant is one file, and none is required.
Both setup scripts run these two, which a second run leaves unchanged:

- `ai-config/scripts/install.sh` links the contract (`INSTRUCTIONS.md`), each PHI hook and
  settings file, the daily audit and update timers, and one marked block in `~/.bashrc` that
  sources `ai-config/scripts/shell.sh`.
- `ai-config/scripts/install-clis.sh` runs the vendor's own installer for any CLI that is
  missing, under `$HOME`, with no prompt and no login. It prints each login command. A failed
  install is reported and the rest go on.

`ai-tools-update`, on a daily timer, updates each CLI the way that machine installed it: npm
for a copy in `node_modules`, the CLI's own `update` otherwise.

**On the cluster** the home is NFS with institute-wide group ACLs, and `chmod` cannot change
them. `shell.sh` sees the network home and wraps any CLI whose descriptor asks. Codex runs with
`--no-daemon`, because its background server refuses a socket in a folder other users can
write to. Its temp folder points at node-local `/tmp`, because files it holds open cannot be
deleted over NFS. A function already defined in `~/.bashrc` is left alone. On the Mac,
`shell.sh` does nothing.

The same group ACLs cover each CLI's login token in the home folder, so anyone in
`domain users` can read it. Log out on the cluster when that matters.

## Working in here

- Commit named paths only, never `git add -A` at the root: one repository holds every
  subject, and a blanket add files somebody else's unfinished work.
  `bash board/scripts/save-and-push.sh "message" -- <paths>` commits and pushes named paths.
- Edit `board/` only in a git worktree under `~/Developer/Atlas-wt/`. The main checkout serves
  the iPad live, so a half-finished edit there breaks a lesson in progress.
- Run `python3 board/test/run.py` before shipping board code.
- `vendor/colibri` moves forward on the cluster: every relay pass bumps the pointer and commits
  it, and only when nothing else in the tree is dirty. `vendor/colibri-build` is pinned and
  moved only by hand, because a build tree that moves under a build is the failure it exists
  to avoid.
- `HANDOFF.md` holds only the work still to do.

Python standard library only; plain browser JavaScript; no package manager at run time.

## Licence

MIT, in `LICENSE`. Coursework and manuscripts are mine; `vendor/` and the files `NOTICE.md`
lists carry their own licences.
