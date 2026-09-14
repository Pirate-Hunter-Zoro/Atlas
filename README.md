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

**THIS FILE DOES NOT LIST THE WORKSPACES, AND THAT IS THE POINT.** A workspace is a
second-level directory holding `tutorboard.json`, `AI_INSTRUCTIONS.md` or `live/` — found by
looking, never declared. `atlas.json` names the *families* and their order and nothing else.

A list of courses in a README is a registry, and a registry is a file somebody has to
remember to edit when a directory appears or goes. Nobody does, so it stops being true
quietly, and then it is worse than nothing: a reader believes it. This paragraph replaced
such a list, and what prompted the replacement was the list having gone stale.

To see what is actually here:

```bash
ls courses research projects practice      # or open the front door, which draws it
```

Starting something new is `mkdir courses/Topology`. The front door draws it on the next
poll; the board finds it; nothing needs telling.

Two levels, and the levels mean something. A **family** is a kind of work. A **workspace** is one
course or one project — the board treats those identically, which is why there is one word for
both.

Nothing lists the workspaces. A second-level directory holding `tutorboard.json`,
`AI_INSTRUCTIONS.md` or `live/` *is* a workspace, found by looking. Starting a new course is
`mkdir courses/Topology`, and the front door draws it on the next poll. `atlas.json` names and
orders the five families and says which ones are somebody else's work. That is all it does.

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

> **The rule this repository used to open with, and reversed on 14 September 2026:** if it
> cannot go into a public repository, it does not live in the repository — it lives outside the
> tree and something inside the tree says where.
>
> **The rule now:** it lives WITH ITS PROJECT, inside the tree, and three independent guards keep
> git blind to it.

This is written out rather than shrugged off, because a reversal recorded as a shrug gets
re-reversed by the next person who reads the old reasoning and finds it good — and the old
reasoning **is** good. A `.gitignore` line is one line, in one file, that anybody can delete by
accident, and this repository has been bitten by exactly that twice: an unanchored `artifacts/`
silently swallowed the `psych_asr/artifacts/` source subpackage, and `.claude/settings.local.json`
at the root matched one file and missed the nine that existed. A thing that is public for an hour
has been published, and git remembers.

What outweighed it is not tidiness. A project's data belongs with the project. Data kept somewhere
nobody can find is data somebody eventually re-creates in a worse place, and a workspace you cannot
hand to a colleague whole is one that only works on the machine it grew on. The old rule bought
safety by making the repository an incomplete description of the work.

So the rule changed and the guards were built. Three, none of them trusted alone:

1. **An anchored ignore rule**, first in the workspace's own `.gitignore`. Anchored because of the
   `artifacts/` lesson above.
2. **`board/test/tracked.py` asks GIT ITSELF**, on every run of the suite, whether it can see
   either directory — `git status --porcelain --untracked-files=all` over each one, which must come
   back empty. That is the part that makes this safe rather than merely allowed: it fails BEFORE a
   commit rather than after, and it catches an ignore rule that reads perfectly well and does not
   work, which is the only failure mode that has ever actually happened here. Break it and the
   whole suite goes red with the words GIT CAN SEE.
3. **`ai-config/policy/phi.py` fences the directory by NAME**, so an assistant cannot read a
   syllable of the audio wherever it sits.

| What | Where it lives | What keeps it out of the public repository |
|---|---|---|
| Therapy session audio (308 MB) | `research/PSYCH-ASR/phi/` | All three guards above. The filenames alone carry participant IDs |
| Job results and model dumps (1.5 GB) | `research/TRD-EHR/results/` | `results/` was already ignored there; `tracked.py` asks git whether it can see it |
| Other authors' published papers | on disk, beside their citation library | Their copyright, not mine. The library **indexes** are tracked, so a clone arrives with the bibliography described but not carried |
| My assistant configuration | `ai-config/`, its own private repository | The settings name real paths on lab storage, and the PHI guard describes what it is guarding |

**The directory is called `phi` for the third reason, and the name is load-bearing in a way the
tree cannot show you.** Renaming it silently unfences 308 MB of identifiable PHI while four
documents go on promising a guard that has stopped matching. `.gitignore`, the workspace README,
its `AI_INSTRUCTIONS.md` and `job_env.sh` each say DO NOT RENAME IT where somebody would be about
to. Neither directory is symlinked, either: a symlink is a tracked file pointing at PHI, which
hands the next reader a map to it. `PSYCH_ASR_DATA` finds the audio — read by `psych_asr/config.py`,
exported by `slurm_jobs/lib/job_env.sh`, both deriving their default from **their own file's
location** rather than from `$HOME`, so a clone anywhere finds its own data and never another
checkout's.

Two things worth knowing because they are the shape of what will be found next. Three copyrighted
textbooks and forty chapter excerpts were tracked in three courses: `split-textbook.sh` said of its
own output "they are derived artifacts and git-ignored" — the intent was there from the start and
the ignore rule never was. TRD-EHR's `.env` was tracked for 477 commits; no credentials in it, but
it enumerated the on-disk locations of identifiable patient data on lab storage. Both were dropped
from history on the way in.

One caution, not a blocker: Galois-Theory's tracked `live/archive` is 114 MB of lesson transcript
and Probability's tracked `live/` is another 20 MB. It is all small files and it is the transcript,
so it is right that it is tracked. Do not "solve" it by untracking the transcript.

**Each workspace keeps its own `.gitignore` and those are the load-bearing ones** — in particular
the `live/*` allowlist (cards, slate, answers, archive, inbox, text, `state.json`, `turns.jsonl`
tracked, the rest ignored), which is what makes a lecture the same lesson on whichever machine
picks it up. Nothing in the root file may shadow one of those: git will not descend into a
directory ignored higher up, so a rule for `live/` written at the root would make every deeper
`!live/cards/` unreachable. The root `.gitignore` holds two honest categories: files a command
regenerates, and other people's papers and books.

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
- **Run `bash board/test/all.sh` before every ship.** 36 suites. Keep them green.
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
where it now lives. `git log --follow` works through the move. Every old history is archived at
`~/archive/*.bundle` — twelve bundles, 298 MB, each verified with `git bundle verify`, and for
TRD-EHR that is the only copy of the unfiltered history once its old remote is deleted.

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
