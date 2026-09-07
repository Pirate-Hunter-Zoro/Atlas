<!-- chapter: Ch 03 — Rings -->
# HANDOFF

**Ch 03, Rings (Garling) — homework.** Assigned in order: **3.1, 3.2, 3.3, 3.8,
3.10, 3.11, 3.12, 3.14, 3.15, 3.17, 3.25, 3.26.** Sheet:
`handwritten/20260902-exercise-list.png`.

**Tooling.** `scripts/build.sh` fails silently on the Mac (forces a Linux
TinyTeX path) — use `board hw build`. Last build OK, 2 pages, 0 warnings.
`board hw file` drops pages in `chapters/ch03-rings/homework/handwritten/`,
which is *not* the chapter's record; copy them to
`chapters/ch03-rings/handwritten/` as `YYYYMMDD-<problem>-attemptN-<what>.png`.

## Where it got to

**3.1** done and transcribed. **3.2, 3.3** skipped ("I have lost patience") —
regions empty, still owed, come back at the end unremarked.

**3.8** — homomorphism (both halves), epimorphism for finite K, and
non-injectivity for general finite K all done and transcribed. Only the
**infinite case** is left, and it has taken four postings. **Skipped
2026-09-06** on the re-pose (card 0057). Homework skip = *not now*: it is still
owed, region still partial, come back to it once the rest of the sheet is done —
unremarked.

**3.10** — statement now transcribed into the `.tex`. Card 0058 posed it and
laddered rung one: multiply (2x+1)(3x+1) in ℤ₆[x] (expect 5x+1, degree 1 — the
degree drops because 2·3 = 0). Unanswered.

## Right — do not re-teach

A polynomial is not its function. cₘ = Σ_{i+j=m} aᵢbⱼ. The indicator δ over 𝔽₂,
𝔽₃, 𝔽₅. The general epimorphism f = Σ_k h(k)δ_k, unaided. The general kernel
element ∏_{k∈K} δ_k, unaided. The reduction: Φ(g−f) = M − M = 0, so h = g−f ∈
ker Φ. Why ∏δ_k dies over infinite K — infinitely many factors is not a
polynomial. The degree ceiling, via x(x−1)(x−2)(x−3): no non-zero cubic has four
roots.

## The misunderstanding

They treated "h has finite degree n" as a hypothesis someone had to grant, not
as the definition of K[x]. Asked outright: *"Since when has degree been limited?"*
Card 0056 answered it — eventually-zero coefficients, K[[x]] is the other thing,
degree is unbounded across K[x] but finite for each element — and posed a check:
A = 1+x+x²+⋯ versus B = x¹⁰⁰⁰⁰⁰⁰, which is in ℚ[x] and what degree. **They
skipped it** (2026-09-06). Skip means *I have this*: treat finite degree as
settled, do not re-ask it, do not remark on the skip.

## Next

Read the ℤ₆ product. Then rung two — the same product over ℤ (or any integral
domain): leading coefficients multiply and cannot vanish, so degrees add. Then
re-pose 3.10 in full. Expected answer: units of R[x] are the units of R (constants);
in ℤ₄[x], 1+2x is a unit, since (1+2x)² = 1+4x+4x² = 1.

**Still owed on 3.8:** the infinite case, skipped. Both halves — monomorphism
(h ≠ 0 in ker Φ has finite degree n, at most n roots, yet all of infinite K are
roots) and not epimorphism (δ_c is not a polynomial over infinite K). Bring it
back when the rest of the sheet is done. **If the monomorphism half does not
close on the next posting, name the contradiction outright — no fifth rung.**

Also still owed: **3.2, 3.3** (skipped 2026-09-02), then 3.11, 3.12, 3.14,
3.15, 3.17, 3.25, 3.26 — statements still `\todo`.

## This student

Concrete lands, general does not — but general lands straight off two concrete
instances. **"I'm stuck" is unreliable: read the working above it.** Twice they
wrote the correct step and declared themselves stuck, because the answer arrived
as a rhetorical question they did not recognise as their own. Pencilled questions
get answered first, in their own card, never as `wrong` — and their questions are
usually the real gap, better than their attempts. They double-tap Send. When a
piece is right, say so in two lines and move.
