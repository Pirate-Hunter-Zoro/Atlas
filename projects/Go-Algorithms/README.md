# Go Algorithms

Classical data structures and algorithms, implemented in Go by hand, each with a
correctness argument, a cost analysis, and tests that scale. The mathematical companion to
Spirit Forge.

Only coaching documents and Atlas metadata exist. There is no code or `go.mod` yet.

- `RULES.md`: the coaching contract, loaded by Atlas, and the design of the test system.
- `QUESTS.md`: the topics, their default order, and which one uses which.
- `TUTOR.md`: current lesson state, maintained through `board memo`.
- `AGENTS.md`: entry point for assistants outside the board.

Start a teach session on this subject: “Coach me through Go Algorithms. Read the rules
and current memory. Begin with the first unfinished topic, one step at a time.”

## Toolchain

Go from Homebrew, declared in this subject's `Brewfile`; `scripts/setup.sh` installs it and
runs `go mod download` once `go.mod` exists. The standard library covers everything,
including tests, fuzzing, and benchmarks. Nothing else is installed.
