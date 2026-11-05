# upkeep

One machine upkeep, carried byte for byte by every repo that has `upkeep/`
(Atlas and Media-Orchestrator). A Mac with either repo cloned gets everything
installed and kept current. Edit it in one repo, copy it to the other, and bump
`VERSION`: the installed copy follows the highest `VERSION` among registered repos.

## Commands

    bash upkeep/setup-mac.sh          a bare Mac: Homebrew, install, a forced run, owner steps
    bash upkeep/setup-mac.sh --homebrew   Homebrew only, when missing (a repo's setup calls it)
    upkeep install --repo ROOT        register ROOT, copy upkeep in, load the agents
    upkeep run [--force] [--dry-run]  the hourly tick; --force skips the gate
    upkeep opencode [--dry-run]       step 5 alone, for a repo's setup: prints each change, `changed: N`
                                      (files the server reads, written or due), and `stale: M` (files newer
                                      than the running server); restart it when either is above 0
    upkeep doctor                     the one-minute opencode tick
    upkeep status                     the last run's findings; exit 1 on any problem
    upkeep off | on                   every run and doctor tick does nothing, or works again
    sudo bash upkeep/root/install.sh  once per Mac: Xcode license and first launch, App Store auto-updates

`upkeep` is `~/.local/bin/upkeep`, a link to the installed copy.

## Files

| Path | What |
| --- | --- |
| `~/.local/share/upkeep/` | the installed copy (copied, so deleting a repo breaks nothing); `install` leaves an identical one alone |
| `~/.config/upkeep/repos.json` | registered repo roots; a root whose directory is gone is dropped |
| `~/.config/upkeep/off` | the off switch |
| `~/.local/state/upkeep/` | `state.json`, `doctor.json`, `upkeep.log` (trimmed at 2 MB), `upkeep.lock`, `Brewfile.all` |
| `~/.zprofile` | the block between `# >>> upkeep >>>` and `# <<< upkeep <<<`: JAVA_HOME, ANDROID_HOME, SDK paths, `opencode/shell.zsh` |
| `launchd/` | `com.mikeyferguson.upkeep` (hourly) and `com.mikeyferguson.opencode-doctor` (every 60 s) |
| `opencode/` | the DeepSeek parity layer: `install.py`, `coder`, `shell.zsh`; its `launchd/*.plist` load like the others |
| `appearance/` | `vscode.json` (the only VS Code keys set) and the Terminal profile |
| `root/` | the root LaunchDaemon `com.mikeyferguson.upkeep-root`; status in `/Library/Application Support/upkeep-root/status.json` |

Templates use `@HOME@`, `@UPKEEP@` (the installed copy), `@PREFIX@` (brew's prefix) and `@PATH@`.
A plist is rewritten and reloaded only when its render changes.

## A run

Each failure is recorded and the run goes on.

1. Copy in the highest registered `VERSION` and re-exec it; re-render the agents.
2. `brew update`, formulae, casks one at a time without `--greedy`, then the
   `greedy-casks` with `--greedy-auto-updates`. Held: pinned formulae and a cask whose
   app ran at three ticks in a row. Left alone, in `protected` and never a problem line:
   names a hook prints for `protected-casks` (the hook upgrades them itself).
3. `brew bundle install --no-upgrade` over `Brewfile` plus each hook's `brewfiles`.
   Only a bare `tap "x"`, `brew "x"` or `cask "x"` joins, rebuilt from its kind and name:
   a name is `[a-z0-9][a-z0-9+._@-]*`, and `owner/repo/name` needs a `tap` line from
   the same repo. Any other line, options included, is logged and left out, since a
   pulled Brewfile runs off the gate and an option such as `postinstall:` runs a
   command. Never `--cleanup`. Hand-copied fonts that block a font cask move to
   `~/Library/Fonts/.before-upkeep/`, and back if the cask fails; a hand-installed app keeps its cask out of the bundle.
4. `npm update -g` with brew's npm, after npm's `allow-scripts` names opencode-ai.
5. The opencode doctor, the DeepSeek key sync, then `opencode/install.py` and
   `npm install` of the plugin's pinned packages when one is missing or off its pin.
6. Android: `sdkmanager --update`, the newest stable platform and build-tools,
   licenses, `flutter config` to the SDK and Android Studio's JBR, `flutter precache`
   when flutter moved, then `flutter doctor -v`: every section not `[✓]` is a problem.
7. Xcode: missing, xcode-select, first launch, license, App Store auto-updates, the
   root helper's status, and an iOS simulator runtime for the SDK this Xcode ships (downloaded
   when missing, because an Xcode update otherwise turns `flutter doctor` red). `mas outdated` is shown in `status`, not counted.
8. Appearance: the VS Code keys in `appearance/vscode.json` (comments and other keys
   kept), the Terminal profile as default and startup, the `Dart-Code.flutter` extension.
9. Each repo's `upkeep.d/hook`: `after-brew`, `toolchain`, then `status` (its stdout
   lines are problems). `locked-install` (pinned tools at their locked versions, nothing
   upgraded) runs only after a pull (*Pull* below).
10. `brew cleanup --prune=7` (never autoremove; skipped while a brew runs, such as a
    hook's worker), state, and a notification for each new problem line.

## Rules

- **Gate**: 20 h since the last attempt, inside 03:00-07:59. A Mac with a battery
  runs outside the window only when 48 h overdue, on AC and idle 20 min. Battery
  at least 40%, formulae.brew.sh reachable. A refused tick re-checks recorded
  problems, report only, at most every 50 min.
- **Busy**: a running brew or legacy upgrader skips the tick. The doctor does nothing
  while a run holds `upkeep.lock`, and leaves the binary alone while opencode runs.
- **JSONC**: `opencode.jsonc` and VS Code's `settings.json` are edited key by key. A
  file that does not parse is named as a problem and left byte for byte.
- **DeepSeek key**: `DEEPSEEK_API_KEY`, else `~/.config/api-keys/deepseek_key`, else
  `~/.config/tutor-board/keys.env`, else opencode's `auth.json`, written to the
  others (a missing directory is not created, except `~/.config/api-keys`). No key is logged.
- **Legacy**: while MO main's `com.mikeyferguson.brewupgrade` is loaded, steps 2-4 and
  cleanup are its, when its `last_success` is under 20 h old, its lock is under
  6 h old, or a brew runs, `--force` or not: it knows MO's protected casks. While `com.mikeyferguson.opencodedoctor`
  is loaded, the doctor is its. Both found by label with `launchctl print`.
- **Retired**: `install` and every run boot out `atlas.brew-upgrade` and remove its plist.
- **Pull**: every tick fast-forwards each repo carrying `upkeep.d/pull`, only on its default branch with a clean tree and index; anything else is skipped and logged, never forced.
  Off the gate, a moved `Brewfile*` gets `brew bundle --no-upgrade` and a moved mise file the hook's `locked-install`.
- **Worktrees**: every tick, a registered repo's linked worktree is removed (`git worktree remove`, `git branch -d`, `git worktree prune`, then its `<repo>-wt` or `worktrees` parent when nothing but `.DS_Store` is left in it) only when unlocked, merged into main, master or origin/HEAD and not on it, no bisect, rebase, merge, cherry-pick, revert or `git am` in progress (their state and any autostash live in `worktrees/<name>/`), every per-worktree ref (`refs/worktree/*`, `refs/bisect/*`, `refs/rewritten/*`) merged, every commit in its HEAD reflog (read through `git reflog`, so reftable repos count) reachable from the default branch or another ref (removal deletes `worktrees/<name>/`, the only thing reaching them; an amended or rebased commit therefore keeps it), clean with untracked files counted and no skip-worktree or assume-unchanged file, holding no other worktree and no `.git` in an ignored directory (removal would delete it), and idle 24 h by the newest mtime of its directory, top-level entries and admin dir in the common git dir. `git worktree prune` waits while any worktree's directory is missing, since it would drop that worktree's commits. Anything else is logged and kept, never forced.
- **Hooks**: `upkeep.d/hook <phase>`, run in the repo root with `UPKEEP_STATE_DIR`,
  `UPKEEP_LOG` and `UPKEEP_DRY_RUN`; a repo with no hook is fine.
- **Protected casks fail closed**: each repo's last `protected-casks` answer is kept in
  `state.json` (`protected_by`). A hook that fails, times out or turns non-executable
  keeps those casks put; with no answer on record, no cask upgrades that run. Either
  is a failed step.

## Tests

    python3 upkeep/test_upkeep.py

Every program upkeep calls is a fake first on the PATH, except git, which runs on
temp repos with a local origin; HOME and /Applications are temp dirs. Anything that runs `setup-mac.sh` or `upkeep` under test must put
the fakes before `/opt/homebrew/bin`, or the real brew runs.
