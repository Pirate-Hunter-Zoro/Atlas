# Algo Solutions

## Where things are

- One package per problem under leetcode/, each with its solver, a doc comment with the problem link, and a table-driven test. 87 are solved.
- datastructures/ holds union-find, heap, linked list, tree and trie, and no range-query structure. helpermath/ holds the modular helpers; answers accumulate under leetcode.MOD.
- findminstep (Zuma) has literal board/hand branches at findminstep.go:31-46 that short-circuit seven judge cases. They are deliberate.

## Now

In flight: leetcode/totalbeauty/, Sum of Beautiful Subsequences. totalbeauty.go:20 is still `return 0`, and the build is broken: helpermath and algo-solutions/leetcode are imported unused. The test is correct: [1,2,3] gives 10, [4,6] gives 12.

Card 0013 (in the imported session) answers their aside on beating O(n²): position is free under a left-to-right sweep, so the inner loop is a prefix sum over the value axis with a point update. It sets them hand-running a value-indexed table S[1..8] on [6,2,8,4]. Expect S to end [0,1,0,2,0,1,0,3], with I unchanged at 1,1,3,2.

Then, in order: Fenwick or O(n²), their choice; coordinate compression, since values reach 1e5; leetcode.MOD; the sum of g·E(g). Go last.

This student answers in full on the slate with their own justification and puts their real doubt in a bubbled aside at the foot. Answer the aside first. They correct you and are right. Paperwork is yours. go test and python3 are refused in a headless turn, so checks are by hand.

Backlog, for when a problem lands and the next is not chosen:
- [ ] totalbeauty's test uses snake_case expected_outputs, and its solver's line 21 is space-indented.
- [ ] leetcode/diffwaystocompute/ has no doc comment and no link (LC 241, Different Ways to Add Parentheses), and uses op_map, the repository's one snake_case name.
- [ ] leetcode/catmousegame/ has no problem link (LC 913, Cat and Mouse).
- [ ] leetcode/maximumjumps/ links over http, not https.
- [ ] ChooseCalculator's caches are not keyed by modulus. Fine while everything shares leetcode.MOD.

## Open decisions

- Fenwick tree or O(n²) for totalbeauty: theirs to choose.
- The next problem. Thick: every kind of DP, grids, graphs. Thin: segment and Fenwick trees, string algorithms proper (KMP, Z-function, suffix structures), sweep-line, max-flow, randomised methods. Best is one that forces a new entry in datastructures/, such as a segment tree.

## Done recently

Do not re-teach:
- The E/A reformulation. A(g) counts increasing subsequences with every element divisible by g, E(g) those with GCD exactly g, and A(g) is the sum of E(m) over multiples m ≤ max(nums). They justified it (a subsequence has one GCD) and inverted it unprompted: E(n) = A(n) minus the sum of E(i) over multiples i > n, filled with g descending.
- Order-dependence: order never moves a subsequence between buckets, only changes the counts, so nums cannot be sorted for the 2^k − 1 shortcut.
- The per-position DP: on [6,2,8,4] they got I = 1,1,3,2 and A(2) = 7, and stated I(i) = 1 + the sum of I(j) over j < i with nums[j] < nums[i] without being asked.
- Wrong once: they enumerated four subsequences of [2,4,6] instead of seven and thought A and E the same. Partial enumeration, fixed in one turn.
