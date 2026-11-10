# Longtable quests

Choose the next quest from what the owner wants to play and needs to learn. These are
expansion directions, not folders to generate now. Keep only one quest active in `TUTOR.md`.
May 2027 is a readiness checkpoint, not a finish line or a promise to finish every branch.

The order to May 2027: First roll, The sheet, The table, The map, The vault, Warden and the
compendium, Prove the rules, Forge a static table, then Ship the table. What slips first:
Lean's optional proofs, the amd64 run, then `warden check`. The sections below group quests
by theme; this line sets the order.

## First playable loop

**First roll.** One fighter, one enemy, one action, and a terminal result. The owner chooses
what the action does, describes valid states, and builds a deterministic transition in Rust.
Learn basic types, functions, ownership, errors, and a focused test through that behavior.
Finish with a playable hit or miss and rejection of an invalid action. Add advantage and
disadvantage once the plain roll works, and keep every roll reproducible from a seed.

**The sheet.** Give the fighter the numbers a real sheet has: abilities, modifiers,
proficiency, armour class, hit points, conditions, rests, and a first spell slot. Rust structs,
enums, traits, and ordered maps now have jobs. Explain which values are derived and which are
stored, and why a condition is a set rather than a counter. Finish when a short rest, a long
rest, and one condition all change the state correctly, with tests.

**The table.** Build the minimal v1 server and the first Flutter client. One device hosts the
table and shows a join code; a second device joins from the browser and sees the same roll
log. Use a versioned HTTP/JSON boundary and a WebSocket for live events. The Rust server owns
the state and rejects an action it did not authorise. Learn Dart classes, widgets, state and
input. From the first screen, target the iPad in Safari: safe-area insets, both orientations,
fingertip-sized controls, no hover-only state, and a reconnect after the device sleeps.
Deliver one roll from one screen to the other through the server.

**The map.** Add the battle map in Flutter: a grid or hex board, tokens, drag to move, pinch
to zoom, fog of war, a range ruler, and area-of-effect templates. The Rust server validates
movement and distance so the client cannot cheat. Learn canvas drawing, gesture handling,
hit-testing, and line of sight (a grid traversal or BFS). Keep the map at 60 frames per second
on the iPad and test a crowded board, not a toy one.

## Grow the software around the table

**The vault.** Design identities, schemas, relationships, queries, migrations, transactions,
and recovery from an interrupted save. Store campaigns, characters, encounters and the action
log in SQLite compiled from its own C source inside the Rust build, so the table carries C
code that later needs a cross compiler. Add an export the owner can inspect and restore.

**Warden and the compendium.** Write warden in Zig: a small static tool that backs up,
restores and checks a save while the server is stopped or hung, and probes the server's
health. Declare the few SQLite C functions it needs by hand and build SQLite's source with
`build.zig`. In the same language, write the content compiler that turns SRD source into one
compact binary the Rust server and the Flutter client both load. Learn slices, allocators,
error unions, `defer`, and the C ABI through tools the table depends on. Finish with a drill:
delete the save, restore it, and play on.

**Forge a static table.** Cross-compile the server and warden from the Mac to static Linux
binaries for arm64 and amd64. Zig compiles SQLite's C and links against musl for both. Explain
target triples, libc, and static linking from each binary's own headers, not from a green
build.

**Ship the table.** Coach dependency pinning, Git branches and reviews, formatting, linting,
and a local Kubernetes cluster. Package the server, warden and web client in one image built
from scratch, for arm64 and amd64 under one manifest, with no emulation in the build. Write
the Containerfile and the manifests: a StatefulSet with a PersistentVolumeClaim for saves, a
Service, readiness and liveness probes through `warden probe`, resource requests and limits,
and a numeric non-root user. Learn the ports, the volume, and the Linux VM behind a local k3s
or kind cluster. The cluster replays the golden traces with identical digests, and a restore
drill brings a deleted save back. A fresh local cluster must run the current table.

**Make it survive trouble.** Replays, profiling, cancellation, concurrent requests,
idempotency, rate limits, observability, and failure recovery. Add a second client device to
the same table only after the owner understands who owns state, ordering, and synchronisation.
Use measured bottlenecks to justify changes. Measure musl's allocator under concurrent tables
before blaming it; replace it only for a measured gain.

## Prove the rules

**The oracle.** Write the step function as a pure Lean definition. A rejected action leaves
the state unchanged, and hit points, slots and conditions stay in bounds. The Lean package
reads the rolls from a versioned trace and never re-implements the PRNG.

**Replay judge.** `lake exe oracle` replays Rust's traces and stops at the first divergence.

**Every fight ends.** A decreasing measure shows that no fight runs forever. After the May
2027 checkpoint unless time remains.

**Proven optimizations.** The encounter-budget tool equals brute force on tiny cases, the
line-of-sight check is shortest, and union-find agrees with naive condition grouping.
Plausible falsifies first, if it needs no Mathlib; proptest mirrors each. After the May 2027
checkpoint unless time remains.

## Mechanics that earn algorithms

- **Initiative and turns:** arrays, queues, a heap, stable ordering, and tie-breaking rules
  the owner can explain and reproduce.
- **Movement and sight:** grids and adjacency lists, BFS, weighted paths, heaps, then A*.
  Make movement costs visible; compare a simple correct route finder against an optimisation.
- **Encounter budget:** constrained selection and resource allocation. Derive dynamic
  programming states and recurrences by hand; compare against exhaustive search on tiny cases.
- **Conditions and effects:** sets, dependency graphs, union-find, and topological ordering
  for effects that stack, expire, or depend on one another.
- **Dice probability:** probability, expected value, combinatorics, and simulation for damage
  and risk. Distinguish a calculated guarantee from an empirical estimate.
- **Session analysis:** prefix sums, range queries, and spatial indexing when the action log
  or collision queries create a measurable need. Benchmark before replacing a simple design.

Every algorithm quest includes a tiny hand trace, the owner's implementation, meaningful edge
cases, a complexity explanation, and an observable effect at the table. Optimisations must
preserve behavior against a simple reference where feasible, stated, and preferably proved in
Lean.

## Keep it personal

Possible branches include a homebrew monster builder, tournament brackets, a procedural
dungeon, a shared campaign chronicle, asynchronous play between sessions, or an accessible
story mode. Choose one at a time. Do not build microservices, orchestration clusters, or an
account system merely to name tools; the cluster exists because a table has to ship.

At the May 2027 checkpoint, have the owner demo a playable slice, explain one algorithm and
one design tradeoff, diagnose a seeded bug, and describe how it is tested and packaged.
Diagnose the seeded bug from the first diverging step of its trace.
The coach writes the resulting project explanation from demonstrated work. Future quests
follow curiosity and gaps revealed in real engineering work.
