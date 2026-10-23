# Spirit Forge quests

Choose the next quest from what the owner wants to play and needs to learn. These are
expansion directions, not folders to generate now. Keep only one quest active in `TUTOR.md`.
May 2027 is a readiness checkpoint, not a finish line or a promise to finish every branch.

The order to May 2027: Sparring spirit, A real duel, Prove the rules, one algorithm quest
of the owner's choice, Save a journey, Realm warden, A visible arena (web, with the minimal
v1 server), Forge a static spirit, then Ship a reproducible realm. What slips first: Lean's
optional proofs, the amd64 run, then `warden check`. The sections below group quests by
theme; this line sets the order.

## First playable loop

**Sparring spirit.** One fighter, one enemy, one action, and a terminal result. The owner
chooses what the action does, describes valid states, and builds a deterministic transition
in Rust. Learn basic types, functions, ownership, errors, and a focused test through that
behavior. Finish with a playable win or loss and rejection of an invalid action.

**A real duel.** Add turn order, energy, and a small choice of techniques. Arrays, maps,
queues, enums, and state machines now have jobs. Explain ties, defeat, and resource limits.
Use explicit inputs and repeatable randomness so a failing encounter can be replayed.
Write the random generator yourself from a published algorithm and check it against its
reference values, because a library generator may change its stream between versions.
Each encounter writes a versioned JSON-lines trace of the seed, every action and roll, and
a digest of the state after each step. Keep the rules in integers and ordered collections
so a trace replays identically on any machine.

**A visible arena.** Build a Flutter web screen for the same duel; phone and tablet targets
wait until one is chosen. Learn Dart classes and composition, widget layout, state
transitions, input, animation, and accessible feedback. Begin with a deliberately small
presentation prototype. Add the Rust API before claiming the client plays the real
simulation. Deliver one action from UI through server to outcome. The Rust server serves
the built client, so one binary carries the playable game.

## Prove the rules

**Oracle of the duel.** Write the step function as a pure Lean definition. A rejected action
leaves the state unchanged, and HP and energy stay in bounds.

**Replay judge.** `lake exe oracle` replays Rust's traces and stops at the first divergence.

**Every duel ends.** A decreasing measure shows that no duel runs forever. After the May 2027
checkpoint unless time remains.

**Proven optimizations.** DP forge equals brute force, BFS is shortest, and union-find agrees
with naive connectivity. Plausible falsifies first, if it needs no Mathlib; proptest mirrors
each. After the May 2027 checkpoint unless time remains.

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
must preserve behavior against a simple reference where feasible, stated, and preferably
proved, in Lean.

## Grow the software around the game

**Save a journey.** Design identities, schemas, relationships, queries, migrations, transactions,
and recovery from an interrupted save. Add an export the owner can inspect and restore.
Store saves in SQLite compiled from its own C source inside the Rust build, so the realm
carries C code that later needs a cross compiler.

**Realm warden.** Write warden in Zig: a small static tool that backs up, restores, and
checks a save while the game is stopped or hung. Declare the few SQLite C functions it needs
by hand and build SQLite's source with build.zig. Learn slices, allocators, error unions,
defer, and the C ABI through a tool the realm depends on. Finish with a drill: delete the
save, restore it, and play on.

**Serve a guild.** Develop versioned APIs, validation, structured errors, configuration, logs,
and integration tests. Add authentication and authorization when multiple players exist.
Keep secrets outside Git. Explain browser origins and threats using the actual endpoints.

**Forge a static spirit.** Cross-compile the server and warden from the Mac to static Linux
binaries for arm64 and amd64. Zig compiles SQLite's C and links against musl for both.
Explain target triples, libc, and static linking from each binary's own headers, not from a
green build.

**Ship a reproducible realm.** Coach dependency pinning, Git branches and reviews, formatting,
linting, CI, and an OCI image run with Podman. Package the server, warden, and web client in
one image built from scratch, for arm64 and amd64 under one manifest, with no emulation in
the build. Learn ports, a named save volume, a numeric non-root user, a warden health probe,
memory limits, and the Linux VM behind Podman. The image replays the golden traces with
identical digests, and a restore drill brings a deleted save back. A fresh local environment
must run the current game.
Public hosting stays optional; the coach checks costs before proposing it.

**Make it survive trouble.** Replays, profiling, cancellation, concurrent requests, idempotency,
rate limits, observability, and failure recovery. Add co-op only after the owner understands
who owns state, ordering, and synchronization. Use measured bottlenecks to justify changes.
Measure musl's allocator under concurrent duels before blaming it; replace it only for a
measured gain.

## Keep it personal

Possible branches include a realm editor, tournament brackets, a mathematical spell language,
procedural dungeons, asynchronous rivals, or an accessible story mode. Choose one at a time.
Do not build microservices, orchestration clusters, or an account system merely to name tools.

At the May 2027 checkpoint, have the owner demo a playable slice, explain one algorithm and
one design tradeoff, diagnose a seeded bug, and describe how it is tested and packaged.
Diagnose the seeded bug from the first diverging step of its trace.
The coach writes the resulting project explanation from demonstrated work. Future quests
follow curiosity and gaps revealed in real engineering work.
