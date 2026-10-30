# Go Algorithms topics

Choose the next topic from what the owner wants to learn and what a later topic needs. These
are directions, not folders to generate now. Keep one topic active in `TUTOR.md`.

Default order: the dynamic array, lists and queues, sorting, binary search and selection,
the binary heap, ordered maps, hashing, union-find, graphs, then the owner's choice. Each
topic names the test stage it introduces, from `RULES.md`, and what it is later used by.

## Foundations

**Dynamic array.** Append, doubling, and shrinking without thrashing. Prove amortized O(1)
append with the potential method, then measure it. Introduces table cases (stage 1) and
the first doubling table (stage 7).

**Lists, stacks, and queues.** A singly and a doubly linked list, a stack, and a ring-buffer
deque. The slice is the oracle. Introduces oracles and seeded generators (stage 2). The
queue later carries BFS, and the stack carries iterative DFS.

**Sorting.** Insertion, merge, quicksort (randomized, then three-way partition), and
counting and radix sort. Argue stability, and prove the Ω(n log n) comparison bound by
decision tree. Introduces the shared sort suite (stage 3) and differential fuzzing against
`slices.Sort` (stage 5). Kruskal later uses it.

**Binary search and selection.** Lower and upper bound with stated invariants. Then
quickselect, and median of medians with its recurrence solved by hand. Sorting is the oracle.

**Binary heap.** Sift up and down, linear-time heapify with its sum derived, heapsort, and a
d-ary variant. Then an indexed heap with decrease-key. Introduces invariant checkers
(stage 4). Dijkstra and Prim later use it.

## Ordered and hashed maps

**Ordered maps.** A plain BST, then AVL, a left-leaning red-black tree, a skip list, and a
B-tree. All of them pass one map suite, with height bounds proved for the balanced ones.
Introduces suites at scale and in-order iteration with `iter.Seq2`.

**Hash tables.** Separate chaining, then linear probing and Robin Hood probing. Derive the
expected probe counts, and measure them against the load factor. Universal hashing comes
with its collision probability. The map suite from Ordered maps runs here too, unordered.

**Bloom filter.** Derive the false-positive rate, then measure it against the formula.

**Union-find.** Union by rank and path compression, with naive connectivity as the oracle.
The inverse-Ackermann bound is stated, and the simpler O(log* n) bound is proved. Kruskal
later uses it.

## Graphs

Adjacency lists first, with an adjacency matrix where a topic is clearer with one. Graph
cases live as golden files (stage 6).

- **Traversal:** BFS on the owner's queue, iterative DFS on the owner's stack, topological
  sort, and strongly connected components by Tarjan or Kosaraju.
- **Shortest paths:** Dijkstra on the owner's indexed heap, Bellman-Ford with negative-cycle
  detection, and Floyd-Warshall. All three check each other on small random graphs.
- **Spanning trees:** Kruskal on the owner's sort and union-find, and Prim on the heap. The
  cut property is proved first.
- **Flow:** Edmonds-Karp, with max-flow min-cut checked on small graphs.

## Range queries

Prefix sums, a Fenwick tree, a segment tree with lazy propagation, and a sparse table.
Naive scans are the oracle, and the Fenwick and segment trees check each other.

## Strings

A trie, the KMP prefix function, the Z-algorithm, and Rabin-Karp with its collision
probability. Then a suffix array. Aho-Corasick is built on the owner's trie and queue.
Naive matching is the oracle throughout.

## Dynamic programming

LCS, edit distance, 0/1 knapsack, LIS (quadratic, then patience sorting with the owner's
binary search), and matrix-chain order. The owner derives each state and recurrence by hand.
Brute force on tiny inputs is the oracle, and reconstructing the solution is part of the topic.

## Number theory

GCD and extended Euclid with proofs, modular exponentiation, the sieve of Eratosthenes, and
Miller-Rabin with the deterministic bases for 64-bit integers. `math/big` is the oracle.

## Randomized structures

A treap, reservoir sampling, and the expected-depth analysis of randomized BSTs. These are
checked against the map suite, with a fixed seed.

## Readiness

At the May 2027 checkpoint, the owner picks three topics they did not just finish. For each,
they trace it by hand, argue correctness and cost, and walk through the tests that guard it.
They also diagnose a seeded bug from the first failing suite case or fuzz input. The coach
writes the resulting summary from demonstrated work.
