# Algo-Solutions

> **AI assistants: read [`AI_INSTRUCTIONS.md`](./AI_INSTRUCTIONS.md) in full before doing
> anything.** It is the operating contract for this repository and it is model-agnostic —
> Claude, Codex, DeepSeek/open-code, Cursor, a local model, all the same. Nothing auto-loads
> it, so read it the moment you are pointed at this README.

**LeetCode** solutions in Go, built so that adding a new problem is a drop-in operation. Reusable data structures, math helpers, and a shared test runner are factored out of the problem code, and every problem lives in its own package with its implementation and test side by side.

## Layout

```
Algo-Solutions/                 (Go module root)
├── leetcode/                    package leetcode — shared MOD + GlobalCalculator
│   ├── supereggdrop/            one package per problem
│   │   ├── supereggdrop.go          the solver(s) + doc comment
│   │   └── supereggdrop_test.go     table-driven test
│   ├── maximalrectangle/ …
│   └── … (88 problem packages)
├── testutil/                    RunTestHelper — the shared table-driven runner
├── helpermath/                  combinatorics, modular arithmetic, primes
├── datastructures/              union-find, heap, linked list, tree, trie
├── references/                  problem writeups (gitignored)
├── go.mod                       module algo-solutions
└── go.work
```

## How a problem is structured

Every problem is a library function, never a standalone program. The problem package exports nothing special: the solver is an unexported function (plus any recursive or helper companions in the same file), and the test drives it directly. Nothing reads stdin, so no problem ever needs fake input piped through it.

Tests are uniform: a table of inputs and expected outputs run through `testutil.RunTestHelper`, a generic helper that applies the solver to each input and compares against the expected result.

## Shared packages

* **`testutil`** — `RunTestHelper`, the generic table-driven comparator used by every test.
* **`helpermath`** — modular arithmetic (`ModAdd`/`ModSub`/`ModMul`/`ModPow`, each taking an explicit modulus), the memoized `ChooseCalculator` for binomial coefficients (plain and modular), and prime/sieve utilities.
* **`datastructures`** — union-find (disjoint set), heap / priority queue, linked list, binary tree, and trie.

The root `leetcode` package also holds two shared values: `MOD` (the `10⁹ + 7` modulus) and `GlobalCalculator` (a process-wide `ChooseCalculator`). Solution packages that need modular combinatorics import `leetcode` and pass `leetcode.MOD` into the math helpers.

> Caveat: `ChooseCalculator`'s caches are not keyed by modulus, so a single instance is bound to one modulus. That is fine while everything here shares `leetcode.MOD`; revisit it before sharing one calculator across different moduli.

## Conventions

* **Directory and package names** are lowercase with no separators (`numberofstablearrays`), matching Go's guidance against underscores and mixedCaps in package names. Each problem directory's name equals its package name.
* **File names** are lowercase-concatenated to match their package (`supereggdrop.go`, and `supereggdrop_test.go` for the test), keeping the required `_test.go` suffix.
* **Identifiers** are camelCase; there is no snake_case anywhere in the code.
* **Problem descriptions** live in a doc comment above the solver and render math with Unicode sub/superscripts (`aᵢ`, `10⁹`) rather than LaTeX-style `a_i` / `10^9`.

## Adding a problem

Create `leetcode/<problemname>/`, put the solver and its doc comment in one file and a `_test.go` beside it in the same package, and drive the solver through `testutil.RunTestHelper`.

## Running the tests

Tests run through Go's standard `go test` tooling; pointing it at the module root exercises every package. Inside VS Code, the **Testing** view (the flask/beaker icon) discovers and runs each package's tests individually, which is the day-to-day path.

## Prerequisites

* Go 1.24 or newer (generics and integer `range` are both used). On the Mac that is
  `brew install go`; the module targets 1.24 and a newer toolchain builds it unchanged.

Nothing else. There is no build step, no code generation, and no dependency outside the standard
library — `go test ./...` from the module root is the whole of it.

## Debugging over SSH (Delve on the Laureate compute node)

*This whole section is about the cluster. On the Mac the workspace path and the compiled test
binary's path are the same string, so breakpoints bind with no configuration and none of the
below applies.*

Breakpoints depend on one piece of configuration, and it is easy to lose on a fresh clone because `.vscode/` is gitignored — recreate it if breakpoints stop binding.

**The symlink problem.** The home directory `/home/librad.laureateinstitute.org/mferguson` is a symlink to `/mnt/dell_storage/homefolders/librad.laureateinstitute.org/mferguson`. VS Code opens the workspace through the `/home/...` path, but the compiled test binary embeds the real `/mnt/dell_storage/...` path. Delve cannot reconcile the two on its own, so breakpoints never bind.

**The fix.** A Delve path-substitution mapping that translates the `/home/...` workspace path to the resolved `/mnt/dell_storage/...` path. Because problems are run from the **Testing** sidebar (and the inline "debug test" CodeLens), the mapping belongs in the `go.delveConfig.substitutePath` setting inside `.vscode/settings.json` — that is the file those entry points read. A prefix mapping there covers every problem package underneath it. If breakpoints fail to bind, check that mapping first, before suspecting the debugger itself.

## The live board

Lessons are not read in the terminal. The assistant runs `board start` from this repository and
tells you which address to open. This machine gets a `127.0.0.1` one; the iPad, which is not on
the institute network, reaches the same board over **Tailscale**. All of them show the same page
at the same time.

On the iPad, open it once in Safari and use Share → **Add to Home Screen**. After that it is an
app with its own icon, no browser chrome, and a long-press shortcut straight to the slate.

Everything the assistant teaches appears there as typeset mathematics the moment it is written:
real LaTeX, real subgroup lattices and commutative diagrams, no refresh and no compile step. You
answer in the terminal, in the box at the bottom of the board, or by hand: the ✎ button opens a
slate you write on with the Apple Pencil. Tap send and the assistant opens the page and reads
your handwriting — no exporting, no airdropping, no retyping a proof you already wrote. Turn on
*live* and it sees each page as you pause. Photos and PDFs dropped anywhere on the board work
too.

With the board on the iPad and the slate for your working, a whole session can happen without
touching the keyboard.

You never run a board command. The tool is `~/Tutor-Board`; its README explains the rest.
