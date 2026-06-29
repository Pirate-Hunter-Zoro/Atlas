# LeetCode Solutions (Go)

## Overview

This repository contains a structured collection of Go solutions for LeetCode algorithmic problems. It is designed with modularity in mind, separating reusable core data structures and mathematical helper functions from the actual problem-solving logic.

## Project Structure

### Core Solutions

* **`solution.go`**: Contains the primary algorithmic logic for the currently targeted LeetCode problem.
* **`solution_test.go`**: Contains the testing suite to verify the logic in `solution.go` against expected edge cases and standard inputs.

### Data Structures (`/datastructures`)

A library of custom data structures frequently required for optimal algorithmic performance:

* **Disjoint Set (Union-Find)**: `dijsointset.go` (Note: Pending rename to `disjointset.go`)
* **Heap / Priority Queue**: `heap.go`
* **Linked List**: `linkedlist.go`, `listnode.go`
* **Tree**: `treenode.go`
* **Trie (Prefix Tree)**: `trie.go`

### Mathematical Helpers (`/helpermath`)

A collection of mathematical utility functions used to simplify complex numeric problems:

* **Combinatorics**: `combination.go`
* **Modulo Arithmetic**: `modulo.go`
* **Primes (Sieve/Checking)**: `primes.go`

## Getting Started

### Prerequisites

* Go (Version 1.25.0 or higher)

### Running Tests

To execute the test suite for the current solution, navigate to the root directory and run the following command:

```bash
go test -v
```

## Debugging on the SSH Compute Node

When working over SSH on the Laureate compute node, the VS Code Go debugger (Delve) needs two things configured in `.vscode/launch.json`, or breakpoints silently fail to bind. Note that `.vscode/` is gitignored, so a fresh clone of this repo will not have these settings — recreate them.

### 1. Path substitution (the recurring "breakpoints never bind" fix)

The home directory is a symlink: `/home/librad.laureateinstitute.org/mferguson` resolves to `/mnt/dell_storage/homefolders/librad.laureateinstitute.org/mferguson`. VS Code typically opens the workspace via the `/home/...` path, but the compiled test binary embeds the real `/mnt/dell_storage/...` path. Delve can't match the two on its own, so breakpoints never bind.

The fix is a `substitutePath` mapping `from` the `/home/...` workspace path `to` the `/mnt/dell_storage/...` resolved path. **This mapping has to be set in two different places, because the two ways of launching the debugger read it from two different files:**

* **`.vscode/launch.json`** — used only by the **Run and Debug** panel (the play-button configurations). The mapping goes in the configuration's `substitutePath` array.
* **`.vscode/settings.json`** — used by the **Testing** sidebar (the flask/beaker icon) and the inline "debug test" CodeLens. These ignore `launch.json` entirely and read the mapping from `go.delveConfig.substitutePath`.

If you debug from the flask sidebar and breakpoints don't bind, the cause is almost always that the mapping exists in `launch.json` but is missing from `settings.json`. This was the step lost on re-clone and the one that is easy to miss.

### 2. The `-test.run` filter must match the function under the breakpoint

The launch config runs a single test via `-test.run <TestName>`. If that test does not call the function holding your breakpoint, the debugger runs cleanly but never reaches the line — it looks identical to a "broken debugger." Whenever you switch to a new LeetCode problem, update the test name in the `args` array to the test that actually exercises that function (e.g. `TestNumberOfPaths` for `numberOfPaths`).

If breakpoints stop working again, check these two things in this order before assuming the debugger itself is broken.
