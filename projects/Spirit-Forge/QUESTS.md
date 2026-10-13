# Spirit Forge quests

Choose the next quest from what the owner wants to play and needs to learn. These are
expansion directions, not folders to generate now. Keep only one quest active in `TUTOR.md`.
May 2027 is a readiness checkpoint, not a finish line or a promise to finish every branch.

## First playable loop

**Sparring spirit.** One fighter, one enemy, one action, and a terminal result. The owner
chooses what the action does, describes valid states, and builds a deterministic transition
in Rust. Learn basic types, functions, ownership, errors, and a focused test through that
behavior. Finish with a playable win or loss and rejection of an invalid action.

**A real duel.** Add turn order, energy, and a small choice of techniques. Arrays, maps,
queues, enums, and state machines now have jobs. Explain ties, defeat, and resource limits.
Use explicit inputs and repeatable randomness so a failing encounter can be replayed.

**A visible arena.** Build a Flutter screen for the same duel. Learn Dart classes and
composition, widget layout, state transitions, input, animation, and accessible feedback.
Begin with a deliberately small presentation prototype. Add the Rust API before claiming
the client plays the real simulation. Deliver one action from UI through server to outcome.

## Mechanics that earn algorithms

- **Realm routes:** grids and adjacency lists, BFS, weighted paths, heaps, then A*. Make
  movement costs visible; compare a simple correct route finder against an optimization.
- **Technique chains:** strings, stacks, parsing, trees, and tries for readable player-authored
  combos. Introduce a small command grammar only when literal actions become limiting.
- **Forge choices:** constrained equipment selection and resource allocation. Derive dynamic
  programming states and recurrences by hand; compare against exhaustive search on tiny cases.
- **Rival tactics:** recursion, backtracking, minimax, pruning, and memoization through enemies
  that choose moves. Make the search budget and resulting difficulty visible.
- **Guild links:** connected components, union-find, dependency DAGs, and topological ordering
  for alliances and technique prerequisites. Require a mechanic before adding a structure.
- **Uncertain realms:** probability, expected value, combinatorics, and simulation for loot
  and risk. Distinguish a calculated guarantee from an empirical estimate.
- **Battle analysis:** prefix sums, range queries, and spatial indexing when replay history
  or collision queries create a measurable need. Benchmark before replacing a simple design.

Every algorithm quest includes a tiny hand trace, the owner's implementation, meaningful
edge cases, a complexity explanation, and an observable effect in the game. Optimizations
must preserve behavior against a simple reference where feasible.

## Grow the software around the game

**Save a journey.** Design identities, schemas, relationships, queries, migrations, transactions,
and recovery from an interrupted save. Add an export the owner can inspect and restore.

**Serve a guild.** Develop versioned APIs, validation, structured errors, configuration, logs,
and integration tests. Add authentication and authorization when multiple players exist.
Keep secrets outside Git. Explain browser origins and threats using the actual endpoints.

**Ship a reproducible realm.** Coach dependency pinning, Git branches and reviews, formatting,
linting, CI, and an OCI image run with Podman. Learn ports, volumes, health checks, non-root
execution, and backup restoration. A fresh local environment must run the current game.
Public hosting stays optional; the coach checks costs before proposing it.

**Make it survive trouble.** Replays, profiling, cancellation, concurrent requests, idempotency,
rate limits, observability, and failure recovery. Add co-op only after the owner understands
who owns state, ordering, and synchronization. Use measured bottlenecks to justify changes.

## Keep it personal

Possible branches include a realm editor, tournament brackets, a mathematical spell language,
procedural dungeons, asynchronous rivals, or an accessible story mode. Choose one at a time.
Do not build microservices, orchestration clusters, or an account system merely to name tools.

At the May 2027 checkpoint, have the owner demo a playable slice, explain one algorithm and
one design tradeoff, diagnose a seeded bug, and describe how it is tested and packaged.
The coach writes the resulting project explanation from demonstrated work. Future quests
follow curiosity and gaps revealed in real engineering work.
