# Lean-Theorem-Proving

> **AI assistants: read [`AI_INSTRUCTIONS.md`](./AI_INSTRUCTIONS.md) in full before doing
> anything.** It is the operating contract for this repository and it is model-agnostic —
> Claude, Codex, DeepSeek/open-code, Cursor, a local model, all the same. Nothing auto-loads
> it, so read it the moment you are pointed at this README.

Learning to prove theorems in **Lean 4** with **Mathlib**, one exercise at a time. Organised the
same way as `Algo-Solutions`: every exercise is a self-contained unit with its statement in a doc
comment and its verification sitting right beside it — except that in Lean the proof *is* the
test. A file that compiles without `sorry` is a passing test. A file with `sorry` in it is a
failing one, and the compiler will say so.

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
├── LeanTP/                       shared library — the analogue of helpermath/
│   ├── Basic.lean                    reusable lemmas, once they earn it
│   └── Tactics.lean                  tactic shorthands, once they earn it
├── Exercises.lean                index module (Lake globs the real files)
├── LeanTP.lean                   shared library root
├── exercises.tsv                 order of study — the manifest
├── lakefile.toml                 package config; requires Mathlib
├── lean-toolchain                pinned Lean version (must match Mathlib's)
├── scripts/
│   ├── new-exercise.sh               scaffold a new exercise + manifest row
│   ├── status.sh                     which exercises are proved, which still sorry
│   └── build.sh                      build and report in plain English
├── slurm_jobs/
│   └── build_mathlib.sbatch          full Mathlib build as a batch job (92 cores)
└── references/                   papers, textbook excerpts, notes
```

Mapping to Algo-Solutions, since that is the shape you already know:

| Algo-Solutions | here |
|---|---|
| one package per problem | one `.lean` file per exercise |
| solver + doc comment | theorem statement + module docstring |
| `_test.go` table-driven test | the proof itself — `sorry` means failing |
| `leetcode/` vs `codeforces/` | topic directories, no platform split |
| `helpermath/`, `datastructures/` | `LeanTP/Basic.lean`, `LeanTP/Tactics.lean` |
| `go.mod` / `go.work` | `lakefile.toml` / `lean-toolchain` |
| `go test ./...` | `lake build` |

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

## Prerequisites

* `elan` (installed), which manages the Lean toolchain — the pinned version is in
  `lean-toolchain` and must match the version Mathlib was built against.
* A compiled Mathlib — **already done**, and sitting in `.lake/`. The prebuilt cache is
  unreachable from this cluster (see the tooling section), so it was compiled from source under
  Slurm instead: a one-time cost of a few hours that persists. It only needs repeating if Mathlib
  or the toolchain is bumped, and the assistant handles it when it does.

## Building

Handled by the assistant, never by you.

* `scripts/build.sh` — compile one file or the whole package, reported in plain English.
* `scripts/status.sh` — which exercises are proved and which still hold a `sorry`, in manifest
  order.
* `scripts/new-exercise.sh` — scaffold a new exercise and append it to `exercises.tsv`.
* `slurm_jobs/build_mathlib.sbatch` — the full Mathlib build as a batch job. See "Building under
  Slurm" below.

A `sorry` is a warning, not an error, so "it built" and "it is proved" are different claims —
`status.sh` reports the second.

## VS Code

The Lean 4 extension gives the Infoview — the live goal state as the cursor moves through a
proof. That panel is the entire experience; working without it is proving blindfolded. It finds
the toolchain through `elan` automatically once the workspace is opened at this directory.

## Tooling — what we used and how we got it

Set up on the Laureate compute node `compute301` (RHEL 9, x86-64, 96 cores, 1 TB RAM), entirely
in the home directory, no root.

### Lean toolchain

`elan` was already installed at `~/.elan` — it is Lean's version manager, the equivalent of
`rustup`, and it picks the compiler version per project by reading `lean-toolchain`.

The pinned version is **`leanprover/lean4:v4.34.0-rc2`**, and it was not chosen — it was copied
from Mathlib's own `lean-toolchain` after the dependency resolved. That matters: Mathlib's
compiled artifacts are only valid for the exact Lean version they were built against, so the
project toolchain must track Mathlib's, not the other way round.

### Mathlib

Declared in `lakefile.toml` as a Reservoir dependency (scope `leanprover-community`), which is
the modern form and avoids hard-coding a git URL. `lake update` resolved nine packages —
mathlib, batteries, aesop, Qq, proofwidgets, importGraph, LeanSearchClient, plausible, Cli — and
wrote `lake-manifest.json`, which pins every one of them to an exact commit.

### The cache is unreachable from this node — Mathlib is built from source

Normally you never compile Mathlib. Its CI publishes prebuilt `.olean` artifacts and
`lake exe cache get` downloads them, turning hours of compilation into a few minutes of
transfer.

**That does not work here.** The cache lives on Azure Blob Storage at
`lakecache.blob.core.windows.net`, and this node's egress filtering permits the TCP connection
but drops the TLS handshake: `curl` connects to port 443, sends its Client Hello, and the server
never replies. `cache get` therefore hangs forever on the handshake rather than failing — it sat
for eighteen minutes having fetched exactly zero artifacts, which reads like a slow download and
is not one.

Diagnostic, if this recurs: `curl -sv https://lakecache.blob.core.windows.net/` shows
`Connected to ...` followed by `TLS handshake, Client hello (1)` and then silence. DNS resolves
fine; GitHub and `releases.lean-lang.org` are both reachable. The block is specific to Azure
Blob Storage.

So Mathlib is **compiled from source** instead. On 96 cores that is a one-time cost measured in
tens of minutes rather than the afternoon it would take on a laptop, and it needs nobody's
permission. The artifacts land in `.lake/` and persist; it only repeats when Mathlib is bumped.

If the block is ever lifted, fetching the cache becomes the faster path again and nothing else
about the project changes.

### Mistakes worth not repeating

**Docstring above the imports.** The first generated batch of exercise files put the module
docstring above the imports. Lean requires `import` lines to come first, before any other command
— including a `/-! ... -/` docstring — so every Mathlib-importing file failed with *invalid
'import' command, it must be used in the beginning of the file*. A side effect worth noticing:
because the imports were invalid, Mathlib was never requested, so the build "finished" in seconds
and looked like a success at a glance.

**Heredoc generation.** Those files were generated through a shell heredoc, which turned the
intended newlines into literal backslash-n characters inside docstrings and multi-line
statements. The generator now lives in a Python file rather than inline in a shell command.

**A scoped notation used without opening its scope.** `E02_AdjoinRoot` failed with *expected
token* pointing at the `⟮` in `F⟮α⟯`. That notation is declared `scoped` in the
`IntermediateField` namespace, so it does not exist as syntax until the scope is opened — and a
notation that does not exist is a parse error, not a name error, which is why the message names
no identifier. `import Mathlib` brings the declaration in; it does not bring the notation into
scope. The file now opens the scope explicitly. Worth remembering because Mathlib scopes a great
deal of its nicest notation this way.

**A name collision with Mathlib's root namespace.** `E01_UniqueIdentity` failed with *`unique_one`
has already been declared* — Mathlib owns that name at the root level, for an unrelated fact about
a `Unique` type carrying a `One`. Because `import Mathlib` imports everything, every root-level
name in the library is taken. The exercise is now `unique_one'`, following the convention
`and_comm'` and `or_comm'` already use here: when Mathlib owns the obvious name, prime it.

**`set -e` swallowing the status report.** The Slurm script ran `lake build` under `set -e`, so a
build that failed on any exercise aborted the script before `scripts/status.sh` at the end could
run — losing the status report precisely on the runs where it was most wanted. The script now
captures the build's exit code, always reports, and exits with that code so a genuine failure is
still reported as FAILED.

### Editor

The Lean 4 VS Code extension provides the Infoview, which shows the goal state at the cursor as
you move through a proof. It locates the toolchain through `elan` automatically when the
workspace is opened at this directory. Working without it is proving blindfolded.

## Git — and the one deliberate ignore exception

Nothing is committed automatically and no remote is configured.

`.gitignore` here ignores **`.lake/`** and **`build/`**, and otherwise matches the deliberately
minimal ignore set used across these repositories (`__pycache__`, `node_modules/`, OS cruft).
The `.lake/` entry is an explicit, agreed exception to the "ignore nothing extra" rule, for three
reasons:

1. **Size.** A fully built Mathlib is roughly 5–6 GB of `.olean` files. GitHub rejects any single
   file over 100 MB and struggles past about 1 GB per repository.
2. **They are version-locked binaries.** An `.olean` is loadable only by the exact Lean version
   that produced it, against the exact Mathlib commit it came from. Bump `lean-toolchain` or
   update Mathlib and every one is dead weight.
3. **They are fully regenerable from what *is* committed.** `lean-toolchain` pins the compiler
   and `lake-manifest.json` pins all nine packages to exact commits. Those two files reproduce
   this build on any machine. The artifacts are output, not source.

To move a built `.lake` to another machine, copy the directory out of band — not through git.

## Where things stand

*Written 24 August 2026, updated 25 August 2026. Update this section as it changes; it is the
handoff note.*

**Done:**

- Repository structure complete: 26 exercises across ten topic directories, `exercises.tsv`
  manifest, shared `LeanTP` library, scaffold/build/status scripts, Slurm job.
- Toolchain resolved and pinned: `leanprover/lean4:v4.34.0-rc2`, copied from Mathlib's own pin.
- `lake update` complete — nine packages resolved, `lake-manifest.json` written.
- **Mathlib is compiled.** All 8,787 modules built from source under Slurm. The artifacts live in
  `.lake/` and persist; they only need rebuilding when Mathlib or the toolchain is bumped. A
  rebuild now replays the cache and re-elaborates only what changed, so the whole package
  round-trips in minutes rather than hours.
- **All 26 theorem statements elaborate.** `lake build` completes with exit status 0, zero
  `error:` lines, empty stderr, and exactly 26 `declaration uses 'sorry'` warnings — one per
  exercise. Every statement is type-correct and every proof obligation is real.

**Not yet true, and important:**

- **Nothing is proved.** `scripts/status.sh` reports *0 proved, 26 open*. A verified statement is
  a starting line, not progress past it — this is exactly the "it built" versus "it is proved"
  distinction the last section of this file insists on.
- Nothing has been committed and no remote exists.

Two statements had to be fixed to get here, and neither was wrong in the way this note previously
predicted. `E01_TowerLaw`'s `IsScalarTower` formulation of the tower law was correct as written
and needed no change, and `E02_AdjoinRoot`'s statement matched Mathlib's
`IntermediateField.adjoin.finrank` exactly. The real failures were a scoped notation used without
opening its scope and a name collision with Mathlib's root namespace — both recorded under
"Mistakes worth not repeating" above.

**The immediate next step** is to start proving. Exercise 01 is the entry point, and the tree
builds clean, so this is also the first sensible moment to consider an initial commit.

## Building under Slurm

`slurm_jobs/build_mathlib.sbatch` compiles Mathlib and then the exercises. Submit it from the
repository root; it requests 92 cores on `c3_short` (the partition's `MaxCPUsPerNode` is 92 —
asking for the node's full 96 is rejected with "Requested node configuration is not available").

Progress and results land in `slurm_jobs/build_mathlib_out.txt`, and the job always finishes by
running `scripts/status.sh`, so the exercise status is at the bottom of that log even when the
build itself failed.

That log is **truncated on every submission**. If a run is worth keeping — the cold Mathlib build
especially — copy it aside before resubmitting; `build_mathlib_out.full-mathlib.txt` and
`build_mathlib_out.64core.txt` are previous runs preserved that way.

The build is **incremental** — cancelling and resubmitting resumes from the artifacts already in
`.lake/` rather than starting over, so the job is safe to resubmit at any time. The artifacts are
also portable across nodes of this cluster: a build started on `compute301` replayed cleanly on
`compute304`.

Rough timings observed on this cluster:

- **Cold build:** the first ~1,400 modules go by in minutes because they are small foundational
  files, then throughput drops sharply to roughly 30–50 modules per minute as individual files
  start taking 100+ seconds each. Budget two to four hours, not the twenty minutes the early
  progress suggests.
- **Warm rebuild after editing two exercises:** about thirteen minutes. Almost none of that is
  compilation — Lake walks all 8,811 targets replaying cached results, then elaborates only the
  changed files, each of which must load the whole of Mathlib first and takes eight to nine
  minutes on its own.

The 92 cores parallelise *across* files, never within one. Editing a single exercise therefore
costs roughly the same wall-clock as editing five, and asking for more cores does not speed up
one file.

## Reading the build output

Three outcomes, and they are not the same thing:

- **`error:`** — the statement is wrong and must be fixed. This is the assistant's job, since the
  statement is the assistant's work.
- **`declaration uses 'sorry'`** *(a warning)* — the statement is correct and the proof is
  missing. This is the expected state of every exercise until you prove it.
- **Silence** — proved.

"It built" and "it is proved" are therefore different claims. `scripts/status.sh` reports the
second by checking each file for a remaining `sorry`; never substitute the first for it.
