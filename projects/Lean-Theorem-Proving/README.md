# Lean-Theorem-Proving

Read `RULES.md` for the coaching contract and `TUTOR.md` for current work.

Learning Lean 4 with Mathlib, one exercise per file. Each file holds the statement
and its proof. A proof is complete when it compiles without `sorry`.

## Layout

```
Lean-Theorem-Proving/            (Lake package root)
├── Exercises/                    one file per exercise, grouped by topic
│   ├── PropositionalLogic/
│   │   ├── E01_AndComm.lean          docstring + statement + empty proof region
│   │   ├── E02_OrComm.lean
│   │   └── …
│   ├── PredicateLogic/ Sets/ Functions/ Induction/ NumberTheory/
│   ├── Structures/ GroupTheory/ RingsAndFields/
│   └── FieldExtensions/          the bridge to the Galois-Theory course
├── LeanTP/                       shared library
│   ├── Basic.lean                    reusable lemmas, once they earn it
│   └── Tactics.lean                  tactic shorthands, once they earn it
├── Exercises.lean                index module (Lake globs the real files)
├── LeanTP.lean                   shared library root
├── exercises.tsv                 order of study — the manifest
├── lakefile.toml                 package config; requires Mathlib
├── lean-toolchain                pinned Lean version (must match Mathlib's)
├── scripts/
│   ├── setup.sh                      make this machine ready to build, whichever it is
│   ├── build-mathlib.sh              Mathlib, built in the background
│   ├── new-exercise.sh               scaffold a new exercise + manifest row
│   ├── status.sh                     which exercises are proved, which still sorry
│   └── build.sh                      build and report in plain English
├── slurm_jobs/
│   └── build_mathlib.sbatch          full Mathlib build as a batch job (92 cores)
└── references/                   papers, textbook excerpts, notes
```

## The division of labour

**The statement is written for you. The proof is yours.** Every exercise ships as a correct,
elaborating theorem signature with a marked, empty proof region:

```
  -- ===== PROOF: and_comm' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: and_comm' =====
```

No assistant writes inside that region in normal mode — not a tactic, not a skeleton, not a
hint disguised as a comment. Naming a tactic in prose and saying what it does is help. Handing
over a script is doing the exercise for you.

## Order of study

`exercises.tsv` holds the order. It runs from propositional logic through predicate logic, sets,
functions, and induction — the mechanics — then into number theory, typeclasses, groups, rings
and fields, and finally field extensions.

Status is deliberately **not** recorded in the manifest; it is derived from whether a file still
contains `sorry`, because that is the only definition of "done" that cannot drift.

## The Galois connection

`Exercises/FieldExtensions/` exists to feed the Galois theory course. The tower law and the
degree of a simple extension are Garling's Theorems 4.3 and 4.4, restated in Mathlib's language —
`Module.finrank K L` for the degree [L:K], `F⟮α⟯` for adjoining an element, `minpoly F α` for the
minimal polynomial, and typeclass instances such as `IsScalarTower` carrying relationships that
the textbook states as equations.

Mathlib already proves both. Finding the existing lemma, reading how its statement is phrased,
and learning why it is phrased that way is the actual exercise — and it is the skill a Galois
final project incorporating Lean would rest on entirely.

## Getting a machine ready

```
./scripts/setup.sh            install what is missing, then start Mathlib's build
./scripts/setup.sh --check    report only; change nothing
./scripts/setup.sh --source   the same, compiling Mathlib instead of fetching the cache
```

`setup.sh` installs `elan` and the toolchain in `lean-toolchain`, hands Mathlib to
`scripts/build-mathlib.sh`, and builds the exercises only if Mathlib is already built.
`build-mathlib.sh` returns at once and builds in the background, under `nohup` and
`caffeinate -is`:

```
./scripts/build-mathlib.sh            the prebuilt cache, then an incremental `lake build Mathlib`
./scripts/build-mathlib.sh --source   no cache: compile it all (an hour and 13 GB on an M4)
./scripts/build-mathlib.sh --status   exit 0 built, 1 missing, 2 running, 3 failed
```

- Its lock, log and status file are in `~/.local/state/atlas-setup/`, named for the checkout.
- `LEAN_NUM_THREADS` is the core count capped at 8, which keeps a source build inside 24 GB of
  RAM. `LEANTP_THREADS` overrides it.
- A cache fetch that fails is retried twice, after clearing a half-written mathlib checkout,
  because Mathlib's gigabyte of git history can drop mid-clone. One that hangs past
  `LEANTP_CACHE_TIMEOUT` seconds (600) is not retried; the build compiles instead.
- Built means `Mathlib.olean` exists, the mathlib checkout is at the commit `lake-manifest.json`
  pins, and the last build did not fail. Otherwise `scripts/build.sh` refuses at once, because
  `lake build` would compile Mathlib in the foreground.
- Under Slurm it starts nothing. The cluster drops the TLS handshake to
  `lakecache.blob.core.windows.net`, so `lake exe cache get` hangs rather than fails, and
  `slurm_jobs/build_mathlib.sbatch` compiles Mathlib as a job.

Nothing needs root and nothing lands outside `$HOME`.

## Prerequisites

* `elan`, which manages the Lean toolchain — `scripts/setup.sh` installs it. The pinned version
  is in `lean-toolchain` and must match the version Mathlib was built against.
* A built Mathlib. It is not tracked (see the git section) and is regenerated per machine from
  `lean-toolchain` and `lake-manifest.json`, which are.

## Building

Handled by the assistant, never by you.

* `scripts/setup.sh` — make this machine able to build at all. Safe to re-run.
* `scripts/build-mathlib.sh` — Mathlib, built in the background; `--status` says where it is.
* `scripts/build.sh` — compile one file or the whole package, reported in plain English. It also
  answers to a `.tex` path, because Tutor-Board's `board export --build` calls
  `scripts/build.sh <file.tex>` on any repository that has one and does not know this is a Lean
  package.
* `scripts/status.sh` — which exercises are proved and which still hold a `sorry`, in manifest
  order.
* `scripts/new-exercise.sh` — scaffold a new exercise and append it to `exercises.tsv`.
* `slurm_jobs/build_mathlib.sbatch` — the full Mathlib build as a Slurm batch job.

A `sorry` is a warning, not an error, so "it built" and "it is proved" are different claims —
`status.sh` reports the second.

## VS Code

The Lean 4 extension gives the Infoview — the live goal state as the cursor moves through a
proof. That panel is the entire experience; working without it is proving blindfolded. It finds
the toolchain through `elan` automatically once the workspace is opened at this directory.

## Source conventions

Imports precede module docstrings. Open the `IntermediateField` scope when using its
adjoin notation. Avoid collisions with Mathlib's root names; the exercises use primed
names where needed. Shared lemmas belong in `LeanTP/` after two exercises need them.

Keep Lean and Mathlib versions aligned: compiled Mathlib artifacts require the exact
Lean version in `lean-toolchain`. `lake-manifest.json` pins dependency commits.

## Tutoring

Use Atlas's board for lessons and write-ups. See `../../board/README.md` for access and
`../../board/TEACHING.md` for the teaching workflow. `RULES.md` sets this subject's rules;
`TUTOR.md` holds the current lesson state.
