# HANDOFF: what is left

This file lists the work still to do, in the order to do it. Delete an item when it lands.
Agents never ssh to the cluster; cluster steps are the owner's.

## How to run this file

The owner starts a session with "read HANDOFF.md and get to work with ultracode". Then:

0. **Commit the plan.** If HANDOFF.md or LIBR-EXIT.md shows as modified, commit both from the
   main checkout before making any worktree, with
   `bash board/scripts/save-and-push.sh "HANDOFF: the plan" -- HANDOFF.md LIBR-EXIT.md`. A
   worktree branches from HEAD.
1. **Do not ask; every decision is made.** They are under *Owner decisions*. The owner files
   under *Owner files* are pre-approved.
   - Write each owner file from its bullets, and commit it when its item runs, by pathspec in
     its own commit.
   - A new subject's RULES.md lands right after that item's `subjects.create`, which refuses a
     directory that already exists.
   - Stop for the owner only where an item says the owner acts: the iPad, the cluster, or a key.
     Ask only if the tree contradicts this file in a way it does not foresee.
2. **Then take the items in order.** Each item is one workflow chain:
   - Re-inventory against the tree. Line numbers drift, so find code by name.
   - Implement in a worktree under `~/Developer/Atlas-wt/<item>`.
   - Run `python3 board/test/run.py`.
   - Review adversarially, with independent verifiers that try to refute the change.
   - Merge.
   - Delete the item from this file in the same commit.

   When a Done-when needs the iPad or the owner, merge once everything machine-checkable
   passes. Move the on-device criteria into *On the glass* in the same commit, and name them in
   the report as the owner's.
3. **Between items, report in six lines or fewer.** Say what landed, what was skipped and why,
   and what the owner must do on the iPad or the cluster.

Rules that hold throughout:
- **The main checkout serves the iPad live.** Merging board code restarts the board. Merge only
  when `sessions/*/agent.json` shows no `turn_pid` and the owner is not mid-lesson.
- **Commit named paths only**, with `bash board/scripts/save-and-push.sh "message" -- <paths>`.
  The main checkout carries uncommitted owner work.
- **Owner files are the owner's.** These are `RULES.md`, subject `README.md`s, and
  `TUTOR.md` outside `board memo`. A tutor turn may not commit them.
- **No provider is load-bearing.** That covers text, vision and speech. Each walks a table, and
  something local ends every chain.
- **Python is standard library only. The web client is plain JavaScript.** External tools arrive
  through Homebrew or a subject's declared toolchain, never at board run time.

## Owner decisions

- **Atlas stays public.**
- **What leaves.**
  - The LIBR exit removes every PHI guard, and `projects/Meetings` with the meeting deck.
  - `projects/Paper-Writer` is scrapped in the same run, and zipped with a history bundle like
    the LIBR projects.
  - The bundles' history filter is `git-filter-repo`, installed through brew for the run and
    uninstalled after.
- **Git and sync.**
  - TUTOR.md stays tracked, but commits only with End or with real work.
  - End's commit and the sync pass push to GitHub automatically.
  - Laptops get the ignored course inputs by rsync over SSH from the Mac mini.
- **Owner files are pre-approved:** the owner's RULES.md files, the subject READMEs and the
  ai-config `update-tools` fix.
- **Galois:** the p=13, d=2 worked case of ch07 13(d) carries into the course.
- **Brew upgrades.** Both upgraders stay.
  - The external `com.mikeyferguson.brewupgrade` keeps its job.
  - `atlas.brew-upgrade` keeps a full brew upgrader on every clone (item 7).
- **Spirit-Forge:** the verification language is Lean 4 without Mathlib.
- **Defaults:**
  - Home's "Annotate a PDF" preselects Random lessons.
  - A finished textbook ingest wakes one tutor turn.
- **Speech.**
  - Azure first, OpenAI second, local last.
  - A language course auto-speaks target phrases only.
  - Gaelic means Irish (ga-IE).

## Owner files

These are pre-approved. Write each from its bullets, and commit it when its item runs.

- **`courses/Probability/RULES.md` and `courses/Galois-Theory/RULES.md` (item 2):**
  - Add after the first rule: "Arithmetic, matrix products, simplification and numeric
    evaluation they ask for are not the mathematics: compute them exactly, give that result,
    and stop."
  - Change the do-mode rule to "only for a solution the owner names as a solution".
- **`courses/Random/RULES.md` (item 12):**
  - Each session is its own topic.
  - TUTOR.md "Done recently" holds at most 15 one-line entries, newest first.
  - Cut before adding.
- **`projects/Spirit-Forge/RULES.md` (item 8):**
  - In "Tools and boundaries", the Lean paragraph.
  - Downloads arrive as lines in the subject's `mise.toml` or `Brewfile`, added in the lesson
    that introduces them. Once committed, every machine installs and updates them. That keeps
    "do not preinstall a stack" true.
  - The tutorboard.json line says "declares no check", without "or relay".
- **`projects/Spirit-Forge/README.md` (item 8):** the toolchain inventory.
- **The course READMEs and the Galois chapter `.tex` header comments:** they link
  `AI_INSTRUCTIONS.md`, `HANDOFF.md`, `PROGRESS.md` and `make split`, none of which exists. Point
  them at `RULES.md`, `TUTOR.md` and `board textbook split`.

## 2. Teach mode computes on request; do mode does only what was asked

In hw04 problem 5 the tutor refused to multiply matrices in teach mode. It said "the
multiplication is the exercise". In do mode it then finished the problem, filled SOLUTION 5 and
committed.

This item changes prompt text only. Every string reaches every live turn on merge.

- **`board/tutorboard/sense.py`:**
  - `METHOD_SENSE`: add computation to the requests done in the card. "COMPUTATION IS NOT THE
    EXERCISE": arithmetic, a matrix product or power, a simplification or a numeric value on
    their route is computed exactly (python3 `fractions`). The card gives that result and
    nothing past it. Asked for pP³ or its (1,3) entry, it gives that, never E[X₃]. Only a
    request to prove or solve stays theirs.
  - SIZE THE STEP: the arithmetic of their own route is never a rung.
  - `TEACH_SENSE`: add "mechanical computation they ask for is yours". `board mode do` is for
    "do the whole task". "Just do this for me" about one computation is done in teach mode. Keep
    the literal `board mode do` and the method words that `test/mode.py` checks.
  - `DO_SENSE` and `DOING_SENSE`: add "DO WHAT WAS ASKED, NOT THE REST". In a lesson or homework,
    the request is the scope: no finishing the exercise, no filling a SOLUTION region, and no
    write-up or commit they did not ask for. Make the code-only sentences conditional on the work
    being code.
- **`mode.py` `LINE["do"]`:** "Do what they ask yourself -- code, a computation, a file -- and
  only that; report what changed."
- **`brief.py`:** the write-up debt line drops the "`board writeup add <label>` for each agreed
  answer" clause in do mode.
- **`board/TEACHING.md`:**
  - The "said outright" line adds "any computation they ask for".
  - The teach/do section gets one paragraph.
  - Do mode gets "Do what was asked, and stop".
  - It sits at exactly the 600-line cap. Shorten the body of "Where a new thing goes" to its
    one bolded sentence, but keep the heading. `DOING_SENSE` points at it, and
    `test/teaching.py` requires a named section to be a heading.
- **`test/teaching.py`:** two-places checks for "computation is not the exercise" and "do what
  was asked". Count the 30-phrase budget first.
- **The two course RULES.md edits** (*Owner files*).

Done when a fresh teach session replaying "tell me the (1,3) result" gets 169/432 and stops, with
no E[X₃], no write-up, no commit and the mode unchanged. In do mode it gets the same card and
touches no file.

## 4. Sync without the cluster

The Mac hears laptop coding sessions through `cluster.Ear`. It lives in `cluster.py`, which the
exit deletes, and it is gated on `TUTORBOARD_CLUSTER`. Move it first, so the laptop path and
the exit stop depending on each other.

- **Create `board/tutorboard/sync.py`** holding `Ear` (renamed `Sync`), `wake`, `notices`,
  `notices_path`, `atlas_of` and `PULL_STATE`.
  - Re-point `app.py`, `handler.py` (`/notices.json`), `hub.py`, `brief.py` and `jobs.py`.
  - `cluster.py` re-exports them until the exit deletes it.
  - `Sync.once` calls `jobs.hear` only while `jobs.py` exists.
- **Rename the env var to `TUTORBOARD_SYNC`** in `app.py`, `board/scripts/launchd/tutor-board.plist`
  and the tests that set or scrub it (`hearing.py`, `making.py`, `health.py`, `meeting.py`).
  `app.py` accepts both names until `bash board/install.sh` has re-rendered the plist. Run it
  right after the merge.
- **Take `code.py` off the relay.**
  - Inline `exports.rel` and `relay.public` (with its regexes) into `code.py`.
  - The `--end` lock becomes `board-code.lock` in `git rev-parse --git-common-dir`, and
    `relay.py` takes the same lock.
- **No divergence.** Today `sessions.end` commits and never pushes, and `Sync` pulls ff-only, so
  a laptop's `--end` leaves the Mac diverged.
  - `sessions.end` commits and pushes.
  - `gitops.push` merges upstream with a dirty tree and lets git refuse overlaps. It never leaves
    a merge standing.
  - `Sync.once` merges when HEAD is ahead and origin is not contained, then pushes. Merge only
    when the index matches HEAD; git refuses a true merge while anything is staged. Otherwise
    record `skipped: staged changes` in `pull.json` and the sync health.
  - Test the merge first with `git merge-tree --write-tree`. Never run `merge --abort` over
    uncommitted work, and abort only a merge this pass started.
  - The new test also covers a Mac clone with a staged file.

Done when:
- `test/hearing.py` and `test/code.py` import `sync`, and `code.py` imports neither relay nor
  exports.
- A new test passes in which a Mac clone holding a local End commit, plus a laptop clone's
  `--end`, end on one main after one sync pass.
- `launchctl print gui/$(id -u)/tutor-board` shows `TUTORBOARD_SYNC`.

## 5. The LIBR exit

Run `LIBR-EXIT.md`. It needs item 4 landed and the owner's first cluster steps (its
section 5a) done, and it stops midway for the owner's section 5b.

It zips TRD-EHR, PSYCH-ASR, libr-local-llm and Paper-Writer with their write-ups, results and
sessions to `~/LIBR-handoff-<date>/`. It records Colibri's upstream instead of zipping it. It
removes the cluster, every PHI guard, Meetings, Paper-Writer and the vendored Colibri.

## 6. What git tracks

Git tracks durable work: code, tests, `tutorboard.json`, RULES.md, TUTOR.md, `doc.json`, artifact
sources, write-ups, `notes.md`, `handwritten/` pages, already-tracked PDFs and owner-placed
review files. It does not track session detail.

- **Feedback rounds are untracked.** These are board-generated ink SVGs, crops, page renders,
  before/after copies, `items.json`, `states.json`, ledgers and round notes.
  - The root `.gitignore` already has `/courses/**/feedback/*[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-v[0-9]*`
    and the same rule under `/projects/`.
  - Nothing reads rounds from git; `ledger.py` reads the disk.
  - `test/deck_loop.py` becomes "End leaves the round on disk and out of the commit".
  - `test/tracked.py` fails on any tracked match.
  - `artifacts.kept` stops returning round files: the `feedback/` loop goes, and the docstring
    says rounds stay on disk. Otherwise End names an ignored path to `git add`, which fails and
    commits nothing, TUTOR.md included.
  - Add a `test/deck_loop.py` case for a document placed in place that has a round, and confirm
    End commits.
  - Update board/README's Reader text and README's Tracked table.
- **Untrack in the main checkout, not a worktree.** A worktree commit that removes files deletes
  them from the Mac's tree on fast-forward.
  1. Tar the rounds to `~/Archive/feedback-rounds-<date>.tgz`.
  2. Have the owner settle the staged index.
  3. Run `git rm -r --cached` on the matches, and confirm each still exists on disk.
  4. Commit with no pathspec, because `gitops.commit --only` drops a staged `rm --cached`.
- **TUTOR.md is quiet.**
  - A `board push` or iPad save whose only change is TUTOR.md commits nothing. The memo rides
    along with the next End or real-work commit.
  - `board memo` never commits on its own.
  - The default save message is `save: <changed files>` instead of "lesson complete".
  - `gitops` gets one `is_save(message)` that matches the old exact strings and the new prefix.
    `lesson/git.py`'s commit filter and `briefs.is_save` (if it survives the exit) both call it.

Done when:
- `git ls-files | grep -E 'feedback/.*-v[0-9]'` is empty, and the library still shows every round.
- A lesson that changes only TUTOR.md leaves no commit until End.
- The suite passes.

## 7. Tools on every machine

Today only the root Brewfile declares tools, and `scripts/setup.sh` hard-codes three markers.
On the Mac mini, `atlas.brew-upgrade` sits in defer mode behind `com.mikeyferguson.brewupgrade`,
so `ai-tools-update` and `uv python upgrade` have never run there. Nothing updates any non-brew
toolchain.

Three layers fix this. The board server never runs any of them.

1. **Machine tools: the Brewfile.**
   - A subject may carry its own `Brewfile`. `setup.sh` bundles the root file plus every subject
     Brewfile, as a sorted and deduplicated union in `~/.local/state/atlas-setup/Brewfile.all`
     rewritten only on change, with `--no-upgrade`.
   - `brew-upgrade.py` `probe_brewfile` checks the same union.
   - Add `brew "mise"`, plus `ghostscript` and `tesseract`, which item 13 needs and which today
     arrive only through texlive.
   - Never run `brew bundle --cleanup`: the Mac mini holds many non-Atlas formulae.
2. **Subject toolchains: mise.**
   - A subject that pins a toolchain tracks `mise.toml` and `mise.lock` at its root.
   - `setup.sh` runs `mise install --locked` there. Then `Cargo.toml` runs `mise exec -- cargo
     fetch --locked`, and `pubspec.yaml` runs `mise exec -- flutter pub get --enforce-lockfile`.
   - Markers count at the root and one directory down. Skip `target/`, `build/`, `.dart_tool/`,
     `.venv/` and `node_modules/`.
   - `gitops.LOCKFILES` gains `mise.toml`, `mise.lock`, `Cargo.lock` and `pubspec.lock` at both
     depths. `test/subjects.py`, which receives `test/jobs.py`'s marker check in the exit,
     requires a check and a lockfile beside each new marker.
   - The tutor-board plist's `AGENT_PATH` (`board/install.sh`) and setup's PATH gain
     `~/.local/share/mise/shims`.
   - A pin moves only by a commit. Nothing auto-bumps it, and nothing runs `flutter upgrade` on a
     mise-managed SDK.
3. **What neither brew nor mise keeps current: descriptors.**
   - `<subject>/tools/<name>.sh` follows the shape of `ai-config/assistants/<name>.sh`. Its
     fields are `T_NAME`, `T_BIN`, `T_BIN_DIR`, `T_ROLES` (`host`/`coding`), `T_INSTALL`,
     `T_MANUAL`, `T_UPDATE`, `T_VERSION`, `T_CHECK`, `T_EVERY_DAYS` and `T_STALE_DAYS`.
   - The reader is `scripts/tools.sh` (`install | update | list | path | check`), which names no
     tool. State goes to `~/.local/state/tutor-board/tools.json`.
   - The same name in two subjects must be byte-identical.
   - Cover these with `board/test/tools.py`.
4. **Upkeep.**
   - `brew-upgrade.py` gets a toolchain phase: `ai-tools-update`, `uv python upgrade`,
     `mise install` over every subject plus `mise prune`, and `tools.sh update`.
   - It runs in own AND defer mode, under the existing window and laptop gate, because none of
     it takes brew's lock.
   - **Brew itself.** Both upgraders stay. Where the external upgrader is loaded,
     `atlas.brew-upgrade` still runs its brew probes and repairs every tick. If the external
     job's last success (read from its log or state) is older than 26 hours, it runs its own
     full brew upgrade that day, under brew's own lock, and reports that it covered. Everywhere
     else it upgrades brew as it does today.
   - Failures enter `brew.json` `failed` as `tool:<name>`.
   - It also runs `mise outdated --json` in each subject with a `mise.toml`. Behind pins go
     into `tools.json` and show as `pin behind: <subject> <tool> <pinned> -> <latest>`. The bump
     is a commit of `mise.toml` and `mise.lock`, proposed in the subject's next session.
   - Check what `brew outdated --json=v2` returns for an `auto_updates` cask today. Then make the
     "NEVER GREEDY" docstring and README say what the job does.
   - In ai-config, `update-tools` adds each descriptor's `A_BIN_DIR` to PATH. Without it a
     curl-installed opencode is never updated. That is a commit in the private repo, and it is
     pre-approved.
5. **Reporting.** `brewcare.py` reads `tools.json` too. It gives one line per failed tool, per tool
   older than `T_STALE_DAYS`, and per `no longer declared: <name> at <dir>`. `board doctor` prints
   a `tools:` line, and the home screen shows them through the sync health (`/sync.json` after
   the exit).
6. **Removal.** A deleted subject's descriptors and Brewfile lines leave the plan. Setup never
   uninstalls anything; doctor names what is left behind.
7. **Mac only.** Keep the layers OS-neutral so a Linux laptop stays possible later, but do not
   build one.

Done when:
- `setup-mac.sh` and `--coding` each end clean twice with no change on the second run.
- A synthetic subject with a `mise.toml` builds, and `board pull` names it when its lock moves.
- `atlas-brew run --dry-run --force` lists the toolchain phase in defer mode.
- A planted failing descriptor shows in `atlas-brew status` and `board doctor`.
- A synthetic subject pinned to an old version shows a `pin behind` line.

## 8. Spirit-Forge: the toolchain and the Lean thread

Spirit-Forge plans Rust for the simulation, Flutter/Dart for the client and Podman later. None
of them is installed. Its RULES.md forbids preinstalling, so the item-7 machinery is built now
and each declaration lands in the lesson that introduces its tool.

- **README.md gains the inventory** (owner's file, so draft it):
  - Every machine: rust via mise, with `rustfmt` and `clippy`; and flutter via mise, stable
    channel, which includes Dart.
  - First client target: Flutter web in Chrome. It needs no Xcode or Android SDK, and widget tests
    run on the Dart VM.
  - Coding laptop only, when a device target is chosen:
    - Android Studio (cask in the subject Brewfile). Its bundled JDK serves Gradle.
      `ANDROID_HOME=~/Library/Android/sdk`. Do not add the `android-commandlinetools` cask:
      Studio's SDK Manager installs cmdline-tools into that SDK, and a second SDK would shadow
      it.
    - `tools/android-sdk.sh` (`sdkmanager --update`, with a timeout and closed stdin).
    - Xcode from the App Store with automatic updates. `tools/xcode.sh` only reports.
    - No CocoaPods: Flutter uses SwiftPM by default.
  - Podman (brew) when its quest arrives, plus a descriptor that checks `podman machine`.
  - Once only, by a person: Android licences, the Xcode licence and `-runFirstLaunch`, the Studio
    wizard, AVDs, Apple ID signing and `podman machine init`.
  - Lean 4 via elan (setup.sh's lean branch), with a Mathlib-free Lake package.
- **QUESTS.md gains "Prove the rules"** after "First playable loop":
  - Oracle of the duel: the duel's step function as a pure Lean definition. A rejected action
    leaves the state unchanged, and HP and energy stay in bounds.
  - Replay judge: Rust writes seeded JSON-lines traces, and `lake exe oracle` replays them and
    stops at the first divergence.
  - Every duel ends: a decreasing measure.
  - Proven optimizations: DP forge equals brute force, BFS is shortest, union-find agrees with
    naive connectivity. Plausible falsifies before proof (confirm it needs no Mathlib), and Rust's
    proptest mirrors each property.
  - The paragraph on optimizations preserving behaviour adds: stated, and preferably proved, in
    Lean.
- **RULES.md paragraph** (*Owner files*):
  - Lean 4 is the specification language, with no Mathlib.
  - The Lake package sits at the root with sources in `spec/`.
  - The bridge is a versioned JSON trace, never bindings.
  - The owner writes definitions and proofs; the coach writes trace plumbing and
    `scripts/check.sh`.
  - "Verified" means `lake build --wfail` is green, with no `sorry`.
  - Lean starts after "A real duel" works in Rust.
- **`projects/Spirit-Forge/.gitignore`:** `/target/`, `.dart_tool/`, `*.jks`, `*.keystore`,
  `key.properties` and `/traces/*.local.jsonl`.
- **The check contract, later.** Record it in RULES.md and build it only when code runs.
  - `scripts/check.sh` runs `cargo fmt --check`, `cargo clippy --locked -- -D warnings` and
    `cargo test --locked`.
  - Then `flutter analyze` and `flutter test` where a pubspec sits.
  - Then `lake build --wfail` and the oracle over `traces/*.jsonl`.
  - `tutorboard.json` gets `check` once the script is tracked.
- **TUTOR.md "Open decisions"**, through `board memo`: the Lean thread starts after A real duel,
  and the first Flutter target is web.

Done when:
- QUESTS.md and TUTOR.md carry the above.
- The README inventory and the RULES.md paragraph are committed.
- `bash scripts/setup.sh` prints a `projects/Spirit-Forge` line reading `nothing to build`.

## 9. Coach-coded from a laptop

Item 4 makes the hearing cluster-free. This item makes the rest of the laptop path work. The
owner codes on a laptop clone, the tutor on the Mac answers, and the owner reads it on the iPad.

- **`board code <sid> <paths>` on a non-local checkout runs `gitops.pull` first**, so steps start
  from current main. A refused pull warns and goes on.
- **Add `board pull --materials [<subject>...]`.**
  - It rsyncs over SSH on the tailnet, from a new `host` key in the laptop's
    `~/.config/tutor-board/config.json` (the Mac mini's tailnet name). `setup-mac.sh --coding`
    asks for it and writes it, and the command refuses plainly when it is unset.
  - It copies only the ignored inputs: `materials/`, `courses/*/textbook/`,
    `courses/*/chapters/*/{reading,lectures}/` and `assignment*`.
  - It never copies `.ink/`, `sessions/` or `.env`.
  - README's "Setting up a laptop" names the owner's one step: Remote Login on the Mac mini, plus
    the laptop's key.
- **Rename `clusterCommand`/`paintClusterCode` in `board.js`** to code-neutral names. The header
  command reads "on your laptop".

Done when `test/laptop.py` proves the rsync include and exclude lists with a shim, and the
on-the-glass trial below passes.

## 10. The ink clipboard across pages, and typing on the iPad

**Clipboard.** `board.html`, `library.html` (annotate) and `slate.html` are separate documents
sharing `InkClip` (`web/ink-clip.js`) through localStorage `tutor-board.clip`.

The bug: `put()` writes to disk only when the clip is at most 300000 bytes (about 16k points),
and it swallows `setItem` errors. So after a big copy on one page, another page, or a
bfcache-restored one, pastes the older clip still on disk. Ties also go to memory. The fix lives
in `ink-clip.js`:
- **Stamps:** stamp `seq = max(Date.now(), newest seen + 1)` and compare on `seq`, falling back to
  `at` for old clips. Ties go to disk.
- **Too big, or `setItem` throws:** remove the key, then write a stub
  (`{v, seq, at, kind, src, big: true, n, strokes: []}`). A newer stub from another page pastes
  nothing, and `InkClip.why()` says `big`.
- **Compact v2 encoding:** flat integer deltas, which roughly triple capacity. Decode v1 and v2.
- **Back from bfcache:** on `pageshow` with `persisted` set, call `fire()`.
- **Copy and paste wording:** `annbar.js` and `slate-core.js` copy messages say "this page only
  (too large to carry)" when `put()` held it in memory only. A paste blocked by a stub says
  "copy it again here".
- **Test:** add `board/test/clipshare.js`, with several JSDOMs sharing one Map-backed
  localStorage. It covers newest-wins in both directions, a same-millisecond pair, an oversize
  copy, a throwing `setItem`, and a v1 clip. Add one same-document case to `test/clip.js`.

**Typing.** The small keyboard is iPadOS's floating keyboard, and no web page can resize it. The
owner fixes it on the device (see *The owner's*). The board's job is to keep the answer box on
the keys while the lesson scrolls behind it.
- **Docking functions:** add `dockSay()` and `dockSaySoon()` in `board.js` beside `autosize()`.
  Follow `library.js` `fitNote()` and `board.js` `placeMenu()`, coalesced to one
  requestAnimationFrame. Trigger them on visualViewport resize and scroll, `#saybox` focus and
  blur, and orientationchange.
- **When to dock:** when `#saybox` is focused and `innerHeight - visualViewport.height > 120`.
  Then `#typebox` gets `.say-docked` (position fixed at the top of the keys, z-index 45, the
  `#writer` background). A placeholder holds its in-flow height, and body bottom padding lets
  every card scroll above the dock. Undocking clears all of it.
- **Never re-parent the textarea.** Moving a focused element closes the keyboard.
- **Box size:** while docked, `autosize()` caps at about 40% of the visible height, not 144px,
  and `#said` at 25%. A new `#say-grow` beside `#say-math` toggles `.say-tall` (about 60%).
- **No focus zoom:** the `#typebox` textarea's font-size becomes at least 16px, so iOS stops
  zooming on focus.
- **No HTML keyboard:** it would lose dictation, Scribble and autocorrect.
- **Test:** add `board/test/saydock.js` with a faked visualViewport, in the style of
  `test/library.js`.

Done when, on the iPad:
- Copying on the board, then in annotate, then pasting on the board pastes the annotate ink, and
  the reverse.
- With the full keyboard up, the answer box sits on the keys, the lesson scrolls behind it, and
  the box can be made tall.

## 11. The problem stays on screen, and its givens go anywhere in one tap

Today a problem statement lives only in a card that scrolls away. Nothing records the current
problem, and the owner hand-copies every matrix. Ship this as three merges.

- **A. The current problem.**
  - `session.json` gains `problem` (a label).
  - `board writeup pose <label>` takes the statement on stdin and calls a new
    `homework.pose(tex, label, statement)`. That writes the statement only where the label is
    absent, a `\todo` or empty, adds an empty SOLUTION marker pair, and never touches a region or
    a transcribed statement. It then pins the label.
  - `POST /s/<id>/problem {label}` lets the panel switch problems, with a non-waking
    `[problem]` line.
  - With nothing pinned, the panel falls back to `hw.next` when that problem is stated.
  - The homework branch of `sense._session_sense` keys on a `session.json` `session` that stored
    sessions lack, so it never fires. Key it on `homework.bound(root, st)`.
  - `WRITEUP_SENSE` says to pose before teaching a homework problem.
- **B. The statement and its givens.**
  - Add `board/tutorboard/course/givens.py`:
    - `statement(tex, label)`;
    - `to_card(body)`, which turns `\textit`, `\emph`, `\textbf`, `\par` and enumerate/itemize
      into markdown and leaves math alone;
    - `givens(body)` returning `[{id, name, tex, calc}]`. `calc` is math.js text for a matrix
      environment or a `\left(...\right)` tuple, with `\frac`/`\tfrac` turned into `a/b`, and
      null when an entry is symbolic.
  - `lesson/state.load_problem` is mtime-cached and reads only the pinned set. `hub.py` adds
    `problem` to the payload.
  - Add `test/givens.py`:
    - hw04 problem 5 gives P with calc `P = [1/2, 1/3, 1/6; 0, 1/3, 2/3; 1/2, 0, 1/2]`, and p with
      calc `p = [1/4, 1/4, 1/2]`;
    - hw04 problem 14 gives four matrices;
    - Galois ch07 problem 17 renders (a)-(d).
- **C. The panel and the calculator.**
  - New `web/problem.js`, loaded before `board.js` and listed in `sw.js`'s shell.
  - `#probbar` sits in `#chrome` after `#hwbar`. It holds the label with a picker, and one KaTeX
    chip per given.
  - `#probpanel` is position fixed outside `#chrome`, about 45vh with its own scroll, and shows
    the whole statement. A scroller inside sticky `#chrome` does not scroll on WebKit.
  - A chip menu offers:
    - to calculator: a new `Calc.enter(text)` defines the variable;
    - into typed answer: inserts `$tex$` at the `#saybox` caret;
    - copy TeX.
  - `calc-core.js` `fracHint` covers matrices element by element, so pP³ shows
    `[[59/144, 43/216, 169/432]]`.
- **D. Typeset givens on the slate.**
  - Page JSON gains `objects: [{id, kind:'tex', tex, fig, x, y, w, h}]`, where `fig` is the
    digest of `server/tikz.py`'s kind-`latex` SVG at `/figure/<digest>.svg`.
  - `slate-core.js`:
    - `placeTex` lands at the view centre;
    - objects draw under the ink, live and in `toPNG`;
    - `pngBox` covers them;
    - lasso moves them, the eraser deletes them, and undo covers them.
  - `/slate/save` keeps stored objects when a payload has no `objects` key.
  - The `[slate]` line names placed givens, so the tutor does not credit them as working.
  - If iPad Safari taints the canvas, fall back to a server PNG.

Done when, in a hw04 session pinned to problem 5:
- Chips P and p show without scrolling, and the statement opens and closes in one tap.
- P to the calculator, then `p*P^3`, shows fractions.
- P onto the page moves with the lasso and appears in the sent PNG.
- Galois ch07 shows problem 17 whole.

## 12. Free boards and any PDF, saved to Random lessons or a subject

These already exist:
- "New session" starts unbound. The chip binds it, End on an unbound session opens the send
  picker, and the send files uploads into `materials/`.
- Home's "Annotate a PDF" takes a file from the iPad's Files.

What is missing is a catch-all, a URL or a Mac path, and a single "save to" order.
- **`courses/Random` ("Random lessons").** It is a course, so phi is false.
  - Create it with `subjects.create("courses/Random")`, which names it "Random".
  - Then set its `tutorboard.json` `name` to "Random lessons" and commit that by pathspec.
  - Its RULES.md is in *Owner files*. Never name it Inbox, Data, Raw or
  Audio while `fenced.NEVER` exists, or Scratch, which `board.js` already uses for the uploads
  drawer.
- **The constant:** `subjects.SCRATCH = "courses/Random"` and `subjects.scratch(base)`.
  `/subjects.json` returns `scratch` beside `meetings` (or alone after the exit).
- **One order in all three pickers:** "Random lessons" first, then Recent, Courses, Projects. The
  pickers are `board.js` `paintSubjects`, `home.js` `paintSender` and `openAnnot`. Annotate
  preselects Random lessons, and "not yet: it stays in the session" stays last. No route changes.
- **The notes canvas:** an unbound canvas binds to the catch-all unless its pages plainly belong
  elsewhere. Change `runner/prompts/notes.md` step 1 and `loop.notes_up`, and name the catch-all
  in `brief.py`'s unbound line.
- **The marked copy reads all ink.** `burn.strokes_by_page` reads every dir in
  `course_repo.ink_dirs(repo)`. Today ink drawn before a bind is missing from "keep a marked copy".
- **From a URL:** `POST /s/<id>/fetch {url}` in `routes/writing.py`, added to
  `handler.ENDED_REFUSES`.
  - Allow http and https only. Build the opener without `FileHandler` or `FTPHandler`, and
    recheck the scheme after redirects.
  - Use a 60 s timeout and the `multipart.MAX_UPLOAD` cap. The body must start with `%PDF-`.
  - Reply like `/upload`.
  - Home's Annotate sheet gains `#annot-url`.
- **From a Mac path:** `board open <file.pdf> [--subject <id>]` copies, never moves, the file into
  a new "Annotate <name>" session. It binds and files when given `--subject`, and prints the URL.
  It is listed in `NO_LIVE`.

Done when:
- All three pickers show Random lessons first.
- A send there files uploads into `courses/Random/materials/`.
- `/fetch` lands a local http.server PDF and refuses file://, ftp:// and a non-PDF.
- `board open` has a CLI test.
- A marked copy made after a bind holds the ink drawn before it.

## 13. Textbooks: upload a book, get an index

Both existing courses were set up by hand: someone read the running headers to make
`chapters.tsv`. The brief tells the tutor only the chapter titles, and nothing resolves
"Exercise 3.4" to a page. Both tables' page-offset comments are wrong. Probability's offset
drifts from 8 to 3, and Galois's is 9, not 11/12.

Prototypes on both real books show that the PDF outline reproduces all 31 hand-made chapter rows
exactly. Nothing here calls a model.

- **The engine: `board/tutorboard/course/book.py`.**
  - Outline: from `pdftohtml -xml -i -q -stdout -f 1 -l 1`, parsed with `xml.etree`.
  - Page text: cached in `textbook/text/pNNNN.txt` from one `pdftotext -layout` run. Any page
    with under 40 characters is OCR'd one at a time with `gs -sDEVICE=ocr -r300`. The run resumes.
  - Chapters:
    - the shallowest outline depth with at least 3 numbered items;
    - a chapter ends one page before the next item at the same or shallower depth;
    - stop at Solutions, Appendix, Index, References or Bibliography, recorded as a doubt;
    - with no outline, use a text fallback, marked as doubts.
  - Sections: from the outline, or N.M heading lines.
  - Printed pages: runs of constant offset per page range, never one offset.
  - Exercises: after a line reading "Exercises" or "Problems", reset at each section, keeping the
    increasing run.
  - Output:
    - Write ignored `textbook/index.json`: sha256, pages, chapters, sections, label runs,
      exercises and doubts.
    - Write `chapters.tsv` only when it is absent. Otherwise print the diff, and write only with
      `--write`.
    - Then run `split-textbook.sh` and `scaffold.sh --chapter-homework`.
  - `find(ref)` accepts "Exercise 3.4", "3.4", "Ch 4 #34", "Section 2.1", "§2.1" and "p. 295". It
    returns PDF pages, printed pages, the reading excerpt and page, and the text. An unresolved
    reference is flagged "not indexed", never guessed.
- **The CLI:** `board textbook ingest <course> [--upload <name>] [--write] [--check]`,
  `board textbook find [<course>] <ref> [--sheet <pdf>]` and `board textbook status <course>`.
- **The server:**
  - `POST /s/<id>/textbook {upload}`. It needs a session bound to a course and refuses a second,
    different PDF.
  - It files the upload into `textbook/` and runs `book.ingest` in a daemon thread, as
    `tikz.Compiler` does, with progress in `textbook/ingest.json`.
  - It finishes with a waking `[textbook]` line carrying counts and doubts.
  - That turn settles the doubts by reading pages, and writes TUTOR.md "Where things are".
  - Add `GET /textbook.json`.
- **The client:** the course maker sheet gets an optional "textbook PDF" field. It runs the
  `annotate()` chain, then `/textbook`, then opens the session. The library shows the textbook
  line, or "Add the textbook".
- **What the tutor is told:**
  - `brief.book_sense` adds "`board textbook find <ref>`", within `test/tokens.py`'s BUDGET.
  - The homework sense says to resolve every reference on the sheet with
    `board textbook find --sheet` before posing.
  - TEACHING.md's uploads section says a course's book goes in through `board textbook ingest`.
- **Tests:** in `board/test/textbook.py`, gs-made fixtures cover an outline with back matter, no
  outline, and an image-only page.

Done when:
- `ingest --check` on both courses reports zero chapter-row differences.
- Galois "7.6" gives PDF page 79, "Section 3.4" gives page 33, and Probability "p. 295" gives
  page 300.
- On the iPad, "+ new course" with a PDF ends in a `[textbook]` card, with excerpts and notes on
  disk and `chapters.tsv` committed.
- Nothing under `textbook/` or `reading/` is tracked.

## 14. Speech: every tutor speaks, listens and judges pronunciation

Every session gets this, math included. A language subject turns it on by default.

DeepSeek has no audio model, so the local recipe ends every chain. Run this after the exit, so
no PHI rule applies. Never track audio: the audit's binary refusal stays.

- **The table: `board/tutorboard/agents/speech.py`.**
  - `DEFAULT_SPEECH` holds the recipes:
    - `azure`: TTS by SSML. STT and assessment by the REST short-audio endpoint with the base64
      `Pronunciation-Assessment` header (Phoneme granularity, Comprehensive, EnableMiscue,
      HundredMark). The audio is WAV PCM 16 kHz mono, at most 30 s. The keys are
      `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` in keys.env.
    - `openai`: `gpt-4o-mini-tts`, and `gpt-4o-mini-transcribe` with multipart built by hand.
    - `local`:
      - TTS: `say`, rendered to m4a, falling back to `espeak-ng` for Irish (ga), which macOS
        has no voice for.
      - STT: `whisper-cli` with a ggml model in `~/.local/share/tutor-board/models/`.
      - Assessment: `tutorboard/speech/tones.py`.
  - Azure's Irish voices are `ga-IE-OrlaNeural` and `ga-IE-ColmNeural`.
  - `config.json` gets a `speech` block, laid over the defaults like `agents`, with
    `order = {tts, stt, assess}`. The default order is azure, openai, local.
  - `chain(kind, lang)` skips a recipe that is unkeyed, missing its command, limited, stood down
    or lacking the language, and always ends with local.
  - `run()` walks it the way `seeing.describe` does, and writes one cost line to `cost.jsonl`.
- **The local tone check: `speech/tones.py`, stdlib.**
  - A YIN F0 tracker, with median smoothing and octave-jump repair.
  - Semitones relative to the speaker's median.
  - Syllables come from whisper timestamps, else from voiced runs merged to the target count.
  - Classify each syllable against T1 to T4 and neutral, and run DTW against the TTS reference.
  - Output each syllable's target tone, heard tone and confidence, plus a word diff.
  - A low-confidence verdict counts as unknown. The scratch prototype found 6 voiced runs for 4
    syllables, so it ships labelled.
- **Listening: `POST /s/<id>/speech/say`.**
  - The request is multipart: audio, `answers`, `ref`, `lang` and `pinyin`.
  - Save it to `sessions/<id>/speech/`. Never use a dir named `audio`, or a file named
    `.transcript.txt` or `.aligned.json`.
  - Convert with `afconvert`, or `ffmpeg` for webm.
  - Run STT, then assess when there is a `ref`, and write `<base>.heard.json`.
  - Then write the turn record and a waking `[speech] heard: '...'. Target: '...'. <verdict>`
    line with `file:`. The tutor never gets raw audio.
  - Add the route to `ENDED_REFUSES`, and add `board hear <file>`.
- **Speaking.**
  - Cards may carry a fence opened with `say <lang>` and an optional `pinyin="ni3 hao3"`.
  - `lesson/cards.py` synthesises these, as `extract_tikz` does, into
    `~/.cache/tutor-board/speech/<sha>.m4a`, served at `/speech/<sha>.m4a`.
  - Each card head gets a speak button: `POST /speech/card` reads the prose and skips math and
    code.
  - An auto-speak toggle, stored per subject, is also the iOS audio unlock.
  - Playback fetches to a Blob, since there is no Range support.
- **Recording: `web/speak.js`.**
  - A third answer tab, `#tab-speak`, opens a `#speakbox` with record/stop, a level meter and the
    last heard block with tone chips.
  - MIME type: `audio/mp4`, else `audio/webm;codecs=opus`.
  - Call `getUserMedia` only on tap, and stop the tracks after each take.
  - Add it to the `sw.js` shell.
- **Per subject:** `tutorboard.json` may hold `speech = {lang, native, voice, auto}`.
  `course/config.read_config` keeps it, and `truthful.py` stays green. `SPEECH_SENSE` is included
  when a subject has `speech` or a session holds heard files. TEACHING.md gets a short drill
  section within its cap.
- **Setup:**
  - The Brewfile gets `whisper-cpp`, `ffmpeg` and `espeak-ng`.
  - `setup-mac.sh` downloads one whisper model with a checksum, and a second run changes nothing.
  - `board doctor` speaks one word and transcribes it back as a witness.
- **Tests:** `board/test/speech.py` covers fake HTTP recipes, chain order, WAV synthesised at run
  time with `wave`, sine-sweep tone classification and the route. A JS suite stubs MediaRecorder.

Done when, on the iPad PWA:
- A zh-CN `say` phrase plays.
- A take shows "heard: ..." within about 5 s, with per-syllable tones.
- `board doctor --dry` names a working local TTS, STT and assessment.

Expected cost at 5 hours a week is about $3-5 a month (Azure's free tier covers most of it), and
$0 local-only.

Language subjects need nothing else from the board. Handwriting already covers kanji, kana and
hanzi, and a subject only sets `speech`. Drawing and art come later. That work adds colour and
pressure brushes to the slate with a reference-image layer, and critique goes through the
existing vision route on the slate PNG.

## The owner's

- **Time Machine has no destination** (`tmutil destinationinfo`). Set one now. Materials,
  sessions, `.ink/`, the Colibri course's sources and the LIBR zips live only on the Mac disk.
- **The small iPad keyboard is the floating keyboard.** Pinch it outward with two fingers, or drag
  it to the bottom edge. A thin bar instead of keys means a hardware keyboard or Scribble is
  active.
- **For item 14:** create an Azure Speech resource and put `AZURE_SPEECH_KEY` and
  `AZURE_SPEECH_REGION` in `~/.config/tutor-board/keys.env`. Download the premium Tingting, Kyoko
  and Amélie voices in System Settings.
- **For item 9:** turn on Remote Login on the Mac mini, add the laptop's SSH key to it, and give
  `setup-mac.sh --coding` the Mac mini's tailnet name.
- **After the exit:** run `bash scripts/setup-mac.sh` once on every laptop clone, so the purged
  projects' leftovers go.
- **Read `board/TEACHING.md` once.** Every turn is told to follow it.
- **Keep `~/.elan`.** Its 2.7 GB v4.34.1 toolchain is reused by every Lean subject.
- **Before the cluster next pulls main,** check that `squeue -n mathlib` is empty. Then delete the
  ignored `projects/Lean-Theorem-Proving` there (about 14 GB of `.lake`) and on any laptop that
  has it. `subjects.walk` lists any directory under `projects/` as a subject.
- **In ai-config,** drop `workspaces/lean-theorem-proving.allow` and its `PERMISSIONS.md` rows.

## Loose ends in the code

- The past-lessons path is unreachable: `openHistory`, `showSession` and `#history` in
  `board/web/board.js`, and `GET /archive` in `board/tutorboard/server/routes/lesson.py`. Wire it
  to home's Past sessions, or delete it.

## On the glass

These are built but not yet used for real. Strike each one after an evening on the iPad.

- **Home:**
  - Continue rows, New session, the Courses and Projects lists, and "+ new".
  - A subject delete with its typed name.
  - Deletes of a material, a document and a session, each with a second tap.
- **Sessions:**
  - A new session starts unbound, and "this is for Topology" binds it.
  - A free lesson sent to Random lessons at End, leaving a TUTOR.md line and any write-up.
  - One that ended unsent, sent later from its chip.
  - A new course made from the send picker at End.
  - Who teaches, switched from the tutor's chip mid-session.
  - The session header: subject chip, teach and do, Make, End.
  - Teach and do persist until switched, and a do turn runs `board check`.
- **Documents:**
  - The Colibri deck's round 2. In the Colibri library, re-ask its revise: its 40 requests are
    unanswered, because the last revise timed out. Let it finish, then End. End commits with no
    participant-scan refusal, and the ledger shows round 2 answered.
  - One document all the way round: Make, build, read, ink, "Say what's wrong", revise.
  - The round as pairs on the Colibri deck: tap the chip, a row and a pip, and mark pairs fine
    or not fixed.
  - Pinch-zoom on a paper and a deck in the one reader. Safari's page zoom never starts, ink
    stays on its words, and one finger scrolls a zoomed page sideways.
  - The notes canvas: a full-slate session whose End leaves a notes.md.
  - Annotate from Files, from a URL and from `board open`; "Keep a marked copy"; and the copy
    following the PDF into the chosen subject.
  - Sending selected annotations.
  - A writeup appearing after handwritten answers in a project session.
  - A code excerpt with `path#L`, opening the read-only source viewer.
- **Laptop coding:**
  - In an iPad session bound to a subject with code, run the header's command on the laptop and
    edit one file. A `[code] step` card shows within a minute.
  - A do-mode `board push` lands on the laptop.
  - `board code <sid> --end` leaves one commit on main, no `code/*` ref, and the Mac pulled.
- **Answers:**
  - A response typing out, and the typed half of the answer panel.
  - Whether the verdict band and streak chip feel like information or like a scoreboard.

## The work it is for

Each item's open tasks live in its subject's TUTOR.md.

1. **Probability and Galois Theory homework**, with items 2, 10 and 11 taking the friction out.
2. **The Colibri course** (`courses/Colibri`): the lesson from card 0048, and the pitch deck's
   rounds.
3. **Spirit-Forge:** Sparring spirit in Rust, then the Lean thread.
