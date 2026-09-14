<!-- chapter: Next change in the LeetCode Go repository -->
`PROGRESS.md` is the plan; `AI_INSTRUCTIONS.md` §12 is the cycle.

## In flight

**`leetcode/totalbeauty/`** — Sum of Beautiful Subsequences. `totalbeauty.go:20` is still
`return 0`, and the build is broken: `helpermath` and `algo-solutions/leetcode` imported
unused. The test is correct — `[1,2,3]`→10, `[4,6]`→12.

## Done, do not re-teach

- **The `E`/`A` reformulation, entirely.** `A(g)` = increasing subsequences with every element
  divisible by `g`; `E(g)` = those with GCD exactly `g`; `A(g) = Σ E(m)` over multiples
  `m ≤ max(nums)`. They justified it themselves — a subsequence has only one GCD — and inverted
  it unprompted: `E(n) = A(n) − Σ E(i)` over multiples `i > n`. Fill order is `g` descending.
- **Order-dependence.** Worked a shuffled list by hand and concluded, their words, that order
  never moves a subsequence between buckets, only changes the counts. So `nums` cannot be
  sorted for the `2^k − 1` shortcut.
- **The per-position DP.** On `[6,2,8,4]` they got `I = 1,1,3,2`, `A(2) = 7`, and drew the
  dependency arrows — that is `I(i) = 1 + Σ I(j)` for `j < i`, `nums[j] < nums[i]`, stated
  without being asked.

## Wrong, once

Early on they enumerated four subsequences of `[2,4,6]` instead of seven and concluded `A` and
`E` were the same thing. Partial enumeration, not bad reasoning. Fixed in one turn.

## The open question

Card 0013. They asked, in a bubbled aside, how to beat `O(n²)`. The card says position is free
under a left-to-right sweep, so the inner loop is a prefix sum over the **value** axis with a
point update, and sets them hand-running a value-indexed table `S[1..8]` on `[6,2,8,4]`.
Expect `S` ending `[0,1,0,2,0,1,0,3]`, `I` unchanged at `1,1,3,2`.

Then Fenwick versus `O(n²)` is theirs to choose; then compression, values reach `1e5`; then
`leetcode.MOD`; then `Σ g·E(g)`. Go last.

## This student

Answers in full on the slate with their own justification, and puts their real doubt in a
bubbled aside at the foot. Answer the aside first. They correct you and are right; Zuma's
hardcoded branches are deliberate. Paperwork is yours. `go test` and `python3` are refused
headless, so checks are by hand.
