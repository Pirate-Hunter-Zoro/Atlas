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

## What is deliberately not in here

Everything in this repository is trackable and cloneable. Four things are therefore kept
**outside** it, because the alternative is an ignore rule — and an ignore rule is a guard anybody
can delete by accident.

| What | Where it lives | Why |
|---|---|---|
| Therapy session audio (308 MB) | `~/phi/PSYCH-ASR/` | Identifiable PHI. The filenames alone carry participant IDs |
| Job results and model dumps (1.5 GB) | `~/artifacts/TRD-EHR/results/` | Regenerable output, and seven files over GitHub's 50 MB warning |
| Other authors' published papers | on disk, beside their citation library | Their copyright, not mine. The library **indexes** are tracked, so a clone arrives with the bibliography described but not carried |
| My assistant configuration | `ai-config/`, its own private repository | The settings name real paths on lab storage, and the PHI guard describes what it is guarding |

Neither of the first two is symlinked in. A symlink is a tracked file pointing at PHI, which hands
the next reader a map to it. Each workspace's README names the real path, and the pipelines take a
path as an argument.

`.gitignore` is then left holding only what a command regenerates, plus those reference PDFs.

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

## History

2,050 commits, from eleven repositories, merged in with their paths rewritten so every file sits
where it now lives. `git log --follow` works through the move. The originals are archived as git
bundles outside the tree.

`vendor/colibri` and `vendor/colibri-build` are submodules of the same upstream at two different
commits — one pulled forward on every login, one pinned. Neither is my code and neither is
committed into.

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
