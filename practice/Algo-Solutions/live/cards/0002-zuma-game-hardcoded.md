---
kind: lesson
title: The unfinished one is Zuma Game
---

I scanned all 88 problem packages. Every one has a test beside it; none is an empty directory or a missing solver. Exactly one is unfinished, and it is not subtle:

**`leetcode/findminstep/` — LeetCode 488, Zuma Game.**

`findminstep.go:31–52` is a wall of hardcoded answers. Seven specific `board`/`hand` pairs are matched by string equality and returned as constants, *before* the real solver at line 56 is ever reached. Your own comments are still in there — `// I think -1?` above a `return 2`, seven times over. That is a submission that got accepted by memorising the judge, not a solution.

`removeGroups` at line 118 also still carries its `// TODO`.

The four cases in `findminstep_test.go` are different inputs entirely, so the local test suite has never seen any of the seven. The hack is invisible to `go test`.

Yes to the rest of what you asked — tracking what is done, picking the next problem, shipping the repo. I am writing the tracking document and the contract change now, while you read this. That is paperwork, not your homework.

## Your move

One change, two files, `leetcode/findminstep/`:

1. **Delete `findminstep.go:31–52` entirely.** The whole `if`/`else if` chain. `findMinStep` should begin at the hand-alphabetising step.
2. **Move those seven inputs into `findminstep_test.go`'s table**, appended after the four that are there, each with the number the deleted branch was returning as its expected output.

You will know it worked when `go test` on that package **fails** — and tells us exactly which of the seven the real algorithm gets wrong. A clean pass would mean the hack was never needed. Either result is information.

Tap *ready to check* and I will run it.
