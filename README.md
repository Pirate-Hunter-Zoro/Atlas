# Atlas

Every course, project and tool I work on, in one place — with a tutoring board that maps each
one, teaches it, writes it up, and says what is next.

```
git clone --recurse-submodules https://github.com/Pirate-Hunter-Zoro/Atlas.git
```

`--recurse-submodules` matters. Without it `vendor/` arrives empty.

---

## What is in here

```
Atlas/
  README.md          this file
  atlas.json         the families, in the order the front door draws them
  board/             Tutor-Board — the tool. `bash board/install.sh` installs it

  courses/           a workspace per course
  research/          a workspace per line of research
  projects/          a workspace per piece of infrastructure
  practice/          a workspace per thing kept sharp

  vendor/            somebody else's repositories, as submodules
  ai-config/         the AI assistant configuration. Its OWN private repository,
                     ignored by this one — see below
```

**NOTHING LISTS THE WORKSPACES, AND THAT IS THE POINT.** A workspace is a second-level
directory holding `tutorboard.json`, `AI_INSTRUCTIONS.md` or `live/` — found by looking, never
declared. A list of them in a README is a registry, and a registry is a file somebody has to
remember to edit when a directory appears or goes. Nobody does, so it goes quietly false, and
then it is worse than nothing because a reader believes it.

```bash
ls courses research projects practice      # or open the front door, which draws it
```

Starting something new is `mkdir courses/Topology`. The front door draws it on the next poll;
the board finds it; nothing needs telling.

Two levels, and they mean something. A **family** is a kind of work. A **workspace** is one
course or one project — the board treats those identically, which is why there is one word for
both. `atlas.json` names and orders the five families and says which hold somebody else's work.
That is all it does.

---

## The board is the way in

`board/` is a tutoring board: a local web app you open on a tablet, one per workspace, each on
its own port. It reads the workspace off disk, draws a **map** of it, opens a **sitting**, and
runs an assistant against it — as a tutor that explains and makes you do the work, or as a pair
that writes the code, per sitting.

```
bash board/install.sh          once, per machine
tutor                          pick a workspace; it starts the board and the tutor
tutor galois                   go straight there
tutor where                    what is running, on this machine and the tailnet
```

Opening the app lands on the **atlas**: one picture of every workspace, what is next in each, and
which ones have a board up. Tapping one opens that workspace's own map where you left it.

Three questions are answerable from any surface in here, and they are the reason the thing exists:

| | from |
|---|---|
| **What has been done** | commits, closed plan steps, the archive of finished sittings |
| **What must be done next** | the plan, drawn as chips on the box of the map it belongs to |
| **How to tell somebody** | a write-up, a deck, or meeting notes whose links land where they say |

None of those three comes from a status somebody typed into a file by hand.

---

## What is in the tree that git cannot see

**Data lives with its project, inside the tree, and three independent guards keep git blind to
it.** None of the three is trusted alone:

1. **An anchored ignore rule** in the workspace's own `.gitignore`. Anchored, because a pattern
   with no leading slash matches at every depth — an unanchored `artifacts/` swallows a source
   subpackage of the same name, and one with a slash in it matches only its own directory.
2. **`board/test/tracked.py` asks GIT ITSELF**, on every run of the suite, whether it can see
   either directory — `git status --porcelain --untracked-files=all` over each, which must come
   back empty. This is the part that makes the arrangement safe rather than merely allowed: it
   fails before a commit rather than after, and it catches an ignore rule that reads perfectly
   well and does not work. Break it and the suite goes red with the words GIT CAN SEE.
3. **`ai-config/policy/phi.py` fences the directory by NAME**, so an assistant cannot read a
   syllable of the audio wherever it sits.

| What | Where | Why it cannot be tracked |
|---|---|---|
| Therapy session audio (308 MB) | `research/PSYCH-ASR/phi/` | Identifiable PHI; the filenames carry participant IDs |
| Job results and model dumps (1.5 GB) | `research/TRD-EHR/results/` | Regenerable, and seven files over GitHub's 50 MB warning |
| Other authors' published papers | on disk, beside their citation library | Their copyright. The library **indexes** are tracked, so a clone arrives with the bibliography described but not carried |
| The assistant configuration | `ai-config/`, its own private repository | Its settings name real paths on lab storage, and the PHI guard describes what it is guarding |

**The directory is called `phi` because the fence matches that name, and nothing in the tree
shows you that.** Renaming it unfences 308 MB of identifiable PHI while four documents go on
promising a guard that has stopped matching. `.gitignore`, the workspace README, its
`AI_INSTRUCTIONS.md` and `job_env.sh` each say DO NOT RENAME IT where somebody would be about to.

Neither directory is symlinked: a symlink is a tracked file pointing at PHI, which hands the next
reader a map to it. `PSYCH_ASR_DATA` finds the audio — read by `psych_asr/config.py`, exported by
`slurm_jobs/lib/job_env.sh`, both deriving their default from **their own file's location** rather
than from `$HOME`, so a clone anywhere finds its own data and never another checkout's.

**Each workspace keeps its own `.gitignore` and those are the load-bearing ones** — in particular
the `live/*` allowlist (cards, slate, answers, archive, inbox, text, `state.json`, `turns.jsonl`
tracked, the rest ignored), which is what makes a lecture the same lesson on whichever machine
picks it up. Nothing in the root file may shadow one of those: git will not descend into a
directory ignored higher up, so a rule for `live/` at the root makes every deeper `!live/cards/`
unreachable. The root `.gitignore` holds two categories: files a command regenerates, and other
people's papers and books.

Galois-Theory's tracked `live/archive` is 114 MB of lesson transcript and Probability's tracked
`live/` is another 20 MB. It is all small files and it is the transcript, so it is right that it
is tracked. Do not "solve" it by untracking the transcript.

### `ai-config/` — inside the tree, tracked by its own git

The last row of that table is the odd one, because it is *here* and still not part of this
repository. `ai-config/` holds the operating contract every AI assistant reads, the PHI guard,
and each vendor's settings files. It is its own repository, and `/ai-config/` is in the
`.gitignore` above, so Atlas never tracks a byte of it.

Inside the tree because one directory should be the whole of the work — a machine is one clone
and one command. Ignored because a public repository must not carry it.

```bash
git clone https://github.com/Pirate-Hunter-Zoro/ai-config.git ~/Atlas/ai-config
bash ~/Atlas/ai-config/scripts/install.sh
```

**It is deliberately not tied to one AI provider.** The contract names no vendor, and neither
do the rules deciding what counts as PHI; each assistant gets a thin adapter and a symlink
under whatever filename it happens to look for. Moving to another provider is adapter work,
not a rewrite of the safety rules under time pressure. `ai-config/README.md` is the whole of
it, including the one thing that does *not* port: an assistant with no pre-tool hook cannot be
fenced off from this data at all.

---

## Working in here

**You ship what you change, in the session you change it, without being asked.** That covers a
section of a plan, a one-line fix to a stale sentence, a test you corrected, a directory somebody
removed that the tree still remembers. Work that ends a session sitting in the working tree is work
nobody has: this repository is used from an iPad, off a board that runs from the last commit, so
uncommitted work is invisible to the person using it AND it is the next session's mystery diff.

Two mechanics make "ship it" mean more than "commit it":

- `bash board/scripts/ship.sh "message"` commits **only `board/`**, pushes, and restarts every
  board. A board is a long-lived process that read `serve.py` when it started, so a commit alone
  changes nothing for somebody holding an iPad.
- **Changes outside `board/` are not covered by that**, and that is the easy half to forget.
  `bash board/scripts/save-and-push.sh "message" -- <paths>` is how those go, with a pathspec so
  one workspace's change does not sweep up another's unfinished afternoon.

And the rest of it, in the order it bites:

- **Bump `VERSION` in `board/web/sw.js`** when any shell file changed (`board.html`, `board.js`,
  `board.css`, `plane-core.js`, `gauge.js`, `home.html`, `home.js`, anything new in the cache
  list), or the installed app serves its cached copy and the work is invisible.
- **Run `bash board/test/all.sh` before every ship.** 64 suites. Keep them green.
- **`board/test/tracked.py` is the one that cannot be fixed afterwards.** It runs first and refuses
  PHI, 25-megabyte files, model dumps, other authors' papers and books, and machine-local config,
  anywhere in the repository. This is public, and git remembers.
- **The lesson must stay reachable.** Somebody is mid-proof on a tablet while the tool changes
  under them. Every surface added is one somebody can be stranded on.
- **Commits are authored by the person, with no assistant trailers.** `.githooks/commit-msg` strips
  them; `save-and-push.sh` turns the hook on for a fresh clone.
- **Do not fix things noticed in passing.** One change, shipped, checked, then the next.

---

## History

2,050 commits, from eleven repositories, merged in with their paths rewritten so every file sits
where it now lives. `git log --follow` works through the move.

**This clone is the only copy.** There are no upstream remotes for the eleven and no bundles: back
it up like anything else that exists once.

`vendor/colibri` and `vendor/colibri-build` are submodules of the same upstream at two different
commits — one pulled forward on every login, one pinned at `fd93c41` and never pulled, because a
build tree that moves underneath a build is the failure it exists to avoid. Neither is my code and
neither is committed into.

The pull is `pull_vendor()` in `board/bin/tutor`, called from `cmd_resume`, because a compute node
gets one moment and it is the login. **It commits the pointer bump itself**, with a fixed message
naming the old and new commit, and that is the only commit anything in this system makes on its
own — without it the repository is left dirty every time colibri moves and the board shows unsaved
work nobody did. It is guarded three ways: only when `vendor/colibri` is the *only* dirty path,
never mid-merge or mid-rebase, never on a detached HEAD. `scripts/catch-up.sh` does the same update
on the same guards. A clone without `--recurse-submodules` arrives with an empty `vendor/` and no
error; `bootstrap.sh` repairs it.

---

## The machine this was built for

A Slurm compute node with no root and a shared home directory reachable under two different
paths. Python standard library only; plain browser JavaScript; nothing that needs a package
manager at runtime. Logging in to a node is the one moment a node gets, so that is when the board
comes back, the repository pulls, and `vendor/colibri` moves forward.

It runs anywhere a `python3` and a browser are. The Slurm parts notice they are not needed.

---

## Licence

See `LICENSE`. Coursework and manuscripts are mine; `vendor/` is not, and carries its own.
