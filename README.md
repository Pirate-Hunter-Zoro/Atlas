# Atlas

Every course and project I work on, in one public repository, with a tutoring board that
teaches it, codes it and writes it up.

The board is `board/`. Its own README, [board/README.md](board/README.md), covers processes,
sessions and the invariants. How a tutor turn teaches is
[board/TEACHING.md](board/TEACHING.md).

## Hard constraints

- **The repository is public.** Every commit is published the moment it is pushed, and git
  keeps it forever. A published manuscript's code link pins a commit here, so it stays public.
- **Nothing private in git.** Other people's work, keys, recordings and large binaries stay on
  disk. Ignore rules, `.githooks/pre-commit` and `board/test/tracked.py` each refuse them on
  their own, because any one guard can be deleted by accident.
- **DeepSeek through OpenCode is the AI.** Every turn, vision request and one-off prompt goes
  to DeepSeek through one recipe, `board/tutorboard/agents/recipes.py`. Nothing chooses another
  assistant. Speech is not AI: Azure Speech first, this Mac's local tools last.
- **The Mac is the only brain.** Every model turn, compile and deck runs on the Mac mini.
- **Commits are authored by the owner.** `.githooks/commit-msg` strips assistant trailers.

## Layout

```
Atlas/
  README.md  LICENSE  NOTICE.md  HANDOFF.md  Brewfile
  Brewfile.taps          the only taps a Brewfile may name, one owner/repo a line
  scripts/setup-mac.sh   sets the Mac up, or brings it up to date: the one command there
  scripts/setup-opencode.sh  OpenCode, DeepSeek and the parity layer; setup-mac.sh runs it
  scripts/setup.sh       builds every subject's environment; setup-mac.sh runs it
  scripts/tools.sh       installs and updates the subjects' tool descriptors
  scripts/brew-upgrade.py  Atlas's upkeep hook (`atlas-brew`): repairs, toolchain, status
  upkeep/                the machine upkeep both repos carry (upkeep/README.md)
  upkeep.d/hook          what upkeep asks of Atlas
  .githooks/             pre-commit (the public-repo gate) and commit-msg
  board/                 the tutoring board: server, CLI, web client, tests
  ai-config/             the AI assistant configuration; a private repository, ignored here
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
| `tutorboard.json` | `name`, `check`, `speech` | yes |
| `Brewfile`, `mise.toml`, `mise.lock`, `tools/<name>.sh` | the machine tools and toolchains it needs; a tap must be in the root `Brewfile.taps` | yes |
| `RULES.md` | the owner's standing rules; a tutor turn may not commit it | yes |
| `TUTOR.md` | the tutor's memory, written only with `board memo`; committed with End or real work, never alone | yes |
| `README.md` | the owner's own notes; never fed to a turn | yes |
| `docs/<slug>/` | an artifact: `doc.json` plus its source | yes |
| `**/feedback/<stem>-<date>-v<n>*` | a document's feedback rounds, read from disk by `ledger.py` | no |
| `materials/`, `.ink/` | uploaded and third-party files, and ink on documents | no |
| `results/`, `.env` | job output, and a machine's secrets | no |

Textbooks, lecture slides, assignment handouts, `materials/` and session uploads are ignored.
Worked solutions, write-ups and the owner's handwritten answers are tracked.

## The Mac and the laptops

GitHub is the only channel between machines: `main`, plus one `code/<session-id>` branch per
open coding session. To code on a laptop, the owner runs `board code <session> <paths>` in a
terminal there. Each pause becomes a step on `code/<session>`, and the tutor on the Mac answers
on the iPad. The iPad reaches the Mac over the owner's tailnet.

## Setting up the Mac

```
git clone https://github.com/Pirate-Hunter-Zoro/Atlas.git
cd Atlas && bash scripts/setup-mac.sh
```

`setup-mac.sh` is also how an existing Mac is brought up to date; a second run changes nothing.
It pulls main, runs `board/bootstrap.sh`, runs `upkeep/setup-mac.sh` and `scripts/setup.sh`, has
tailscale serve the board, and checks that the board answers. Its header lists each step. On a
Mac with no Homebrew it installs Homebrew first, which asks for the password once.

- `bootstrap.sh` clones `ai-config/`, sets `core.hooksPath` to `.githooks/` by
  absolute path, and runs `board/install.sh`. That links `board` into `~/.local/bin` and installs
  the board's LaunchAgent, `tutor-board`, which keeps `board/serve.py` up on port 8778.
- `upkeep/setup-mac.sh` registers this clone with upkeep and runs it once (see
  *Machine upkeep*), then prints the steps only the owner can take: install Xcode, run
  `sudo bash upkeep/root/install.sh` once, and put the DeepSeek key in
  `~/.config/api-keys/deepseek_key`.
- `scripts/setup-opencode.sh` puts the assistant on a Mac; `setup-mac.sh` runs it in step 4,
  after `upkeep/setup-mac.sh`, and running it alone redoes only the assistant. It installs
  Homebrew's Node and the `opencode-ai` package when missing, then hands the rest to upkeep:
  `upkeep install --repo` (the persistent `opencode-serve` LaunchAgent, `oc` and `ocrun`) and
  `upkeep opencode` (the doctor, upkeep's DeepSeek key sync, the parity layer in
  `upkeep/opencode/` and its pinned packages). It restarts the OpenCode server only when a file the
  server reads changed, in that run or since the server started, so a second run changes and
  restarts nothing.
  It clones `Pirate-Hunter-Zoro/ai-config` with `gh` when that is missing and authenticated, and
  runs its installer for the personal contract. `--dry-run`, `--no-agents` and `--no-contract`
  narrow it.
- `scripts/setup.sh` runs `brew bundle --no-upgrade` on the root Brewfile (Atlas's own tools;
  upkeep/Brewfile has the shared ones) joined with every subject's own (`~/.local/state/atlas-setup/Brewfile.all`), never `--cleanup`. It then builds
  each subject's environment from what it holds (`pyproject.toml`, `lean-toolchain`, `go.mod`).
  A `lean-toolchain` subject gets elan in `~/.elan` when it is missing, then `lake build`.
- A subject pins a toolchain in `mise.toml` and `mise.lock` (written by `mise lock`, which records
  each platform's download URL that `--locked` requires): setup runs `mise install --locked` on
  the tools that `mise.toml` names, so the owner's global mise tools never fail it. Atlas's own
  root `mise.toml` is installed the same way, before the subjects. Then, through
  `mise exec`, at the subject's root and one directory down: `cargo fetch --locked` for a
  `Cargo.toml`, `flutter pub get --enforce-lockfile` for a `pubspec.yaml`, and
  `zig build --fetch` for a `build.zig.zon`, which is its own lockfile, only when the nearest
  `mise.toml` pins zig. A pin moves only by a commit. mise runs in a directory only when every
  config it reads there holds plain `[tools]` versions, with no template character even in a
  comment, no `path:` pin and no miserc (toolplan's `mise_chain_problem`); a refused directory is
  skipped and named, never installed. Each marker needs its lockfile beside it
  and a check in `tutorboard.json`.
  `scripts/setup.sh` refuses any machine but a Mac.
- A tool neither brew nor mise keeps current is a descriptor, `<subject>/tools/<name>.sh`, read
  by `scripts/tools.sh` (its header lists the fields). Setup installs what is missing. One name
  in two subjects must be the same bytes. Nothing is uninstalled: a deleted subject's tools and
  Brewfile entries are named by `board doctor` while they stay installed.
- A tool requested on the iPad is declared with `board tools add brew|cask|mise <name>
  [--subject <id>] [--why ...]`. The name, the version and `--why` are checked first, and every
  mise config in the target directory and above it must hold only `[tools]` versions. It writes a
  line in the root or subject `Brewfile`, or an entry in its `mise.toml` (committing `mise.lock`
  with it), and commits and pushes the file. Then it installs narrowly: `brew bundle
  --no-upgrade` on `Brewfile.all`, or `mise install --locked` of that one tool. It never
  upgrades. Setup and the hourly upkeep hook install what the repository declares, so a
  declaration on one Mac reaches every clone through git. `board tools list` shows them, and
  nothing is uninstalled.
- A Brewfile line that is not a bare `tap`, `brew` or `cask` with a checked name never reaches
  `Brewfile.all`: it shows as `refused Brewfile line` in `board doctor` and `atlas-brew status`.
  A mise directory whose configs hold anything but `[tools]` versions is never installed by
  setup or the hook, and shows as refused.
- Turn on automatic login, so the LaunchAgents come back after a reboot.
- The DeepSeek key is `DEEPSEEK_API_KEY` in the environment, else in
  `~/.config/tutor-board/keys.env`, else the file `~/.config/api-keys/deepseek_key`. A file other
  accounts can read is refused, so keep both at mode 600. Azure's keys sit in keys.env too. `config.json` holds
  timeouts and the host, and picks no assistant. All of it stays off the tree.
- `board doctor --dry` reports what the machine has without spending a turn.
- Step 4 links `ai-config` and installs `opencode`, the one assistant CLI (see *Assistant
  CLIs*). Step 6 runs the board's own readiness check: opencode, the key, the allowance.

## Machine upkeep

`upkeep/` keeps the Mac current; `upkeep/README.md` has its commands, files and rules. Media-Orchestrator
carries the same bytes, so a Mac with either repo gets it. Hourly, gated to once a day in
03:00-07:59, it upgrades brew (never `--greedy`, except flutter and android-studio), installs the
Brewfile union, updates brew's npm globals, keeps opencode, the DeepSeek key, the Android SDK,
Flutter, Xcode's checks, fonts, VS Code and Terminal in order, and makes `flutter doctor` green.

Atlas's part is `upkeep.d/hook`, which runs `scripts/brew-upgrade.py`:

- It holds tailscale while the host runs it as a brew service, because it carries the board's
  tailnet, and hands upkeep the Brewfile union (`~/.local/state/atlas-setup/Brewfile.all`).
- After brew moves, it re-syncs a subject's broken `.venv` and reinstalls the board's LaunchAgent
  whose interpreter is gone. TeX and the board's reachability are reported, never touched.
- Its toolchain phase runs uv's Pythons, `mise install --locked` in Atlas's own root and every
  subject with a `mise.toml`, `mise prune --tools` of the tools those files name (never a bare prune,
  which reaches the owner's other projects), and `scripts/tools.sh update`. The pins it installs
  are the declarations committed on whichever Mac made them. It runs `mise lock` first only
  when `mise.lock` is missing, `mise.toml` or `mise.lock` differs from HEAD, or a pinned tool
  has no lock entry (`lock_stale`), so a clean clone is never re-locked.
- A failed tool shows as `tool:<name>`, and a mise pin behind (`mise outdated --json --bump
  --local` gives it a `bump`) as `pin behind`, in `atlas-brew status`, `board doctor` and on home.
  A pin behind is also in that subject's session brief, so the session proposes the bump: a
  commit of `mise.toml` and `mise.lock`.
- upkeep's problems and the hook's reach `atlas-brew status`, `board doctor` and home, and arrive
  as notifications on every Mac. `upkeep off` stops it.

On the iPad, open the tailnet address in Safari and use Share, then Add to Home Screen.

## Setting up a laptop

```
git clone https://github.com/Pirate-Hunter-Zoro/Atlas.git
cd Atlas && bash scripts/setup-mac.sh --coding
```

A laptop is a coding checkout: it runs `board code` and no board. `--coding` writes `coding` to
`~/.config/tutor-board/role`, so every later run stays a coding checkout. That run does the Mac's
steps without the board's LaunchAgent, and boots out one left from before. It skips tailscale
serve, the DeepSeek key check and the port-8778 check. Deleting the role file makes the next run a
host.

- `board pull` brings the laptop up to date: Atlas and ai-config. It names
  each subject whose lockfile moved, and `bash scripts/setup.sh` rebuilds those. `board code
  <session> <paths>` pulls main first too.
- `board pull --materials [<subject>...]` copies the Mac mini's ignored inputs over SSH:
  `materials/`, textbooks, chapter readings and lectures, and assignment sheets. It never copies
  `.ink/`, `sessions/` or any `.env*`, and deletes nothing. It reads `host` (the Mac mini's tailnet
  name, which setup asks for) and `host_atlas` (default `Developer/Atlas` under the remote home)
  from `~/.config/tutor-board/config.json`, and refuses without `host`.
- **The owner's one step:** turn on Remote Login on the Mac mini (System Settings, General,
  Sharing), and add the laptop's public SSH key to the Mac mini's `~/.ssh/authorized_keys`.
- The same upkeep runs here. Outside the window it upgrades only when 48 hours overdue, on AC,
  and idle 20 minutes, because a laptop is shut at night. Problems arrive as notifications.
- A tool declared on the iPad reaches the laptop within the hour: `upkeep.d/pull` has upkeep fast-forward a clean
  `main` and install only what moved (*Pull* in `upkeep/README.md`); a dirty or diverged checkout is skipped, never forced.

## Assistant CLIs

The one assistant is OpenCode running DeepSeek, described in `ai-config/assistants/opencode.sh`:
where it keeps its config and how to install, update and run it. The board needs only
`opencode`, the npm global `opencode-ai`; upkeep's opencode doctor repairs it when it breaks.
`setup-mac.sh` fast-forwards `ai-config` first, since Atlas's pull never moves it. Then it
runs these two, which a second run leaves unchanged:

- `ai-config/scripts/install.sh` links the contract (`INSTRUCTIONS.md`) and each settings
  file, and loads the daily audit's LaunchAgent.
- `scripts/setup-opencode.sh --no-contract` installs opencode when it is missing and the rest
  of the assistant (see *Setting up the Mac*).

`ai-tools-update` updates each CLI the way that machine installed it: npm for a copy in
`node_modules`, the CLI's own `update` otherwise. Nothing schedules it; upkeep keeps opencode.

## Working in here

- Commit named paths only, never `git add -A` at the root: one repository holds every
  subject, and a blanket add files somebody else's unfinished work.
  `bash board/scripts/save-and-push.sh "message" -- <paths>` commits and pushes named paths.
- Edit `board/` only in a git worktree under `~/Developer/Atlas-wt/`. The main checkout serves
  the iPad live, so a half-finished edit there breaks a lesson in progress.
- Run `python3 board/test/run.py` before shipping board code.
- `HANDOFF.md` holds only the work still to do.

Python standard library only; plain browser JavaScript; no package manager at run time.

## Licence

MIT, in `LICENSE`. Coursework and manuscripts are mine; the files `NOTICE.md` lists carry
their own licences.
