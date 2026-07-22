# algo-solutions

Competitive-programming solutions in Go, spanning **LeetCode** and **Codeforces**, built so that adding a new problem on either platform is a drop-in operation. Reusable data structures, math helpers, and a shared test runner are factored out of the problem code, and every problem lives in its own package with its implementation and test side by side.

## Layout

```
algo-solutions/                 (Go module root)
├── leetcode/                    package leetcode — shared MOD + GlobalCalculator
│   ├── supereggdrop/            one package per problem
│   │   ├── supereggdrop.go          the solver(s) + doc comment
│   │   └── supereggdrop_test.go     table-driven test
│   ├── maximalrectangle/ …
│   └── … (84 problem packages)
├── codeforces/                  package codeforces — shared fast-input Reader
│   └── mochaandstars/           one package per problem (package main)
│       ├── main.go                  thin stdin/stdout wrapper
│       ├── mochaandstars.go         the pure solver
│       └── mochaandstars_test.go    table-driven test of the solver
├── testutil/                    RunTestHelper — the shared table-driven runner
├── helpermath/                  combinatorics, modular arithmetic, primes
├── datastructures/              union-find, heap, linked list, tree, trie
├── references/                  problem writeups (gitignored)
├── go.mod                       module algo-solutions
└── go.work
```

## The two platforms

**LeetCode** problems are library functions. Each problem package exports nothing special: the solver is an unexported function (plus any recursive/helper companions in the same file), and the test drives it directly.

**Codeforces** problems are standalone programs (`package main`) that read stdin and write stdout. Each is split into a **thin `main`** that only handles I/O and a **pure solver** function that takes already-parsed inputs and returns the answer. The test targets the pure solver, so no problem ever needs fake stdin piped through it.

Both platforms test the same way: a table of inputs and expected outputs run through `testutil.RunTestHelper`, a generic helper that applies the solver to each input and compares against the expected result.

## Shared packages

* **`testutil`** — `RunTestHelper`, the generic table-driven comparator used by every test on both platforms.
* **`helpermath`** — modular arithmetic (`ModAdd`/`ModSub`/`ModMul`/`ModPow`, each taking an explicit modulus), the memoized `ChooseCalculator` for binomial coefficients (plain and modular), and prime/sieve utilities.
* **`datastructures`** — union-find (disjoint set), heap / priority queue, linked list, binary tree, and trie.

The LeetCode side also keeps two shared values in its root `leetcode` package: `MOD` (the `10⁹ + 7` modulus) and `GlobalCalculator` (a process-wide `ChooseCalculator`). Solution packages that need modular combinatorics import `leetcode` and pass `leetcode.MOD` into the math helpers.

> Caveat: `ChooseCalculator`'s caches are not keyed by modulus, so a single instance is bound to one modulus. That is fine for the LeetCode `MOD`; revisit it before sharing one calculator across different moduli.

## Conventions

* **Directory and package names** are lowercase with no separators (`numberofstablearrays`), matching Go's guidance against underscores and mixedCaps in package names. Each problem directory's name equals its package name.
* **File names** are lowercase-concatenated to match their package (`supereggdrop.go`, and `supereggdrop_test.go` for the test), keeping the required `_test.go` suffix.
* **Identifiers** are camelCase; there is no snake_case anywhere in the code.
* **Problem descriptions** live in a doc comment above the solver and render math with Unicode sub/superscripts (`aᵢ`, `10⁹`) rather than LaTeX-style `a_i` / `10^9`.

## Adding a problem

* **LeetCode**: create `leetcode/<problemname>/`, put the solver and its doc comment in one file and a `_test.go` beside it in the same package, and drive the solver through `testutil.RunTestHelper`.
* **Codeforces**: create `codeforces/<problemname>/` as `package main` with a `main` that reads input via `codeforces.NewReader` over standard input, a pure solver in its own file, and a `_test.go` that tests the solver directly.

## Running the tests

Tests run through Go's standard `go test` tooling; pointing it at the module root exercises every package on both platforms. Inside VS Code, the **Testing** view (the flask/beaker icon) discovers and runs each package's tests individually, which is the day-to-day path.

## Prerequisites

* Go 1.24 or newer (generics and integer `range` are both used).

## Debugging over SSH (Delve on the Laureate compute node)

Breakpoints depend on one piece of configuration, and it is easy to lose on a fresh clone because `.vscode/` is gitignored — recreate it if breakpoints stop binding.

**The symlink problem.** The home directory `/home/librad.laureateinstitute.org/mferguson` is a symlink to `/mnt/dell_storage/homefolders/librad.laureateinstitute.org/mferguson`. VS Code opens the workspace through the `/home/...` path, but the compiled test binary embeds the real `/mnt/dell_storage/...` path. Delve cannot reconcile the two on its own, so breakpoints never bind.

**The fix.** A Delve path-substitution mapping that translates the `/home/...` workspace path to the resolved `/mnt/dell_storage/...` path. Because problems are run from the **Testing** sidebar (and the inline "debug test" CodeLens), the mapping belongs in the `go.delveConfig.substitutePath` setting inside `.vscode/settings.json` — that is the file those entry points read. A prefix mapping there covers every problem package underneath it. If breakpoints fail to bind, check that mapping first, before suspecting the debugger itself.
