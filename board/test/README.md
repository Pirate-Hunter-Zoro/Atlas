# Test ownership

Board suites use synthetic subjects. Never read a named real project's files as fixtures.
Repository-wide guards enumerate subjects with `subjects.all` rather than a name list.

Project-specific integration checks live in that subject's `tests/board/*.py`. The full
`python3 board/test/run.py` discovers them automatically and runs each from its subject root.
Each entry point exits nonzero on failure and locates its own files relative to itself.
Prefix private helper filenames with an underscore. Do not import runnable suites as helpers.

Use a full relative path to select a project suite when filenames overlap. Board helpers
are declared in `run.py` and must have a suite that uses them. `independence.py` checks
subject discovery and runs the board's subject-handling regressions in a subject-free tree.
