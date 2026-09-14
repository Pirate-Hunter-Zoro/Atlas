---
kind: question
title: The empty body is totalBeauty
---

Wrong package last time. Zuma is yours and done; I read a stale comment as an open question. The TODO and the `// I think -1?` lines are coming out.

The empty one is **`leetcode/totalbeauty/totalbeauty.go:20`** — *Sum of Beautiful Subsequences*. `totalBeauty` takes `nums []int` and its entire body is `return 0`.

It does not compile, either. Lines 4–5 import `helpermath` and `leetcode` and neither name is used anywhere in the file, which Go rejects outright. Those two imports are the note-to-self: the answer is summed under `leetcode.MOD` with the modular helpers.

The test beside it is already right. `[1,2,3]` → 10, `[4,6]` → 12. I checked both by hand against the statement, so when the package compiles those two numbers are the target.

## The shape of the thing

Counting subsequences whose GCD is **exactly** $g$ is painful. Counting the ones where every element is **divisible by** $g$ is not — that is a plain increasing-subsequence count over the sub-array of multiples of $g$.

Before you write anything, get the relationship between those two counts straight, because the whole solution turns on it.

## Your move

Take $\texttt{nums} = [2, 4, 6]$. By hand, on the slate or typed:

**How many strictly increasing subsequences have every element divisible by 2, and how many have GCD exactly 2?**

Non-empty subsequences only. I want both numbers and I want to know why they differ — the gap is the part that becomes code.
