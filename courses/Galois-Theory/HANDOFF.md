<!-- chapter: Ch 03 — Rings -->
# HANDOFF

**Ch 03, Rings (Garling) — homework.** Assigned in order: **3.1, 3.2, 3.3, 3.8,
3.10, 3.11, 3.12, 3.14, 3.15, 3.17, 3.25, 3.26.** Sheet:
`handwritten/20260902-exercise-list.png`.

**Building:** `scripts/build.sh` fails silently on the Mac — it forces a Linux
TinyTeX path. Use **`board hw build`**; it works, as do `board recap` and
`board next`. Last build: OK, 2 pages, 0 warnings.

**Filing:** `board hw file` drops pages into
`chapters/ch03-rings/homework/handwritten/`, which is *not* where this chapter's
record lives. The canonical folder is `chapters/ch03-rings/handwritten/`, named
`YYYYMMDD-<problem>-attemptN-<what>.png`; copy the page there yourself and let
board keep its own copy.

## Where it got to

**3.1** done and transcribed. **3.2, 3.3** skipped ("I have lost patience") —
regions empty, still owed, come back at the end of the sheet unremarked.

**3.8** — homomorphism (both halves), the epimorphism for finite K, and
non-injectivity for general finite K all done and transcribed. Only the
**infinite case** is left. Card 0051 posed it (monomorphism half only); they
came back stuck, with a strategy question rather than an attempt (rev 21). Card
0052 answered it and posed the concrete ℚ rung; they got it (degree 5, all the
(x−k) factors). Card 0053 re-posed the monomorphism half in full; rev 22 came
back with the reduction done (0 = M−M = Φ(g−f), so h = g−f ∈ ker Φ) and the
right reason ∏δ_k dies over infinite K — infinitely many factors is not a
polynomial — but stuck again on forcing h = 0. Card 0054 names the reason and
posed a degree-bound non-example; rev 23 answered it correctly — x(x−1)(x−2)(x−3),
degree 4, cannot be shaved because there are no zero divisors — but wrote "I'm
stuck" under it and asked "how can we not have at least degree 4?", not seeing
that the question *is* the answer. Card 0055 reads it back to them and re-poses
the monomorphism half a third time. They came back not with an attempt but with
the real question: *"Since when has degree been limited? Do g and f have finite
degree?"* Card 0056 answers it — finite degree is the definition of K[x],
eventually-zero coefficient sequences, K[[x]] is the thing that allows
infinitely many — and poses a classification check (A = 1+x+x²+⋯ versus
B = x¹⁰⁰⁰⁰⁰⁰). Unanswered.

## Right — do not re-teach

A polynomial is not its function. cₘ = Σ_{i+j=m} aᵢbⱼ. Clearing denominators by
the product. x²+x ∈ ker Φ over 𝔽₂. The indicator δ built by hand over 𝔽₂, 𝔽₃ and
unprompted over 𝔽₅. **The general epimorphism, whole and unaided:** f = Σ_k
h(k)δ_k evaluated at an arbitrary k₁, collapsing to h(k₁)·1. **The general
kernel element, whole and unaided, off one 𝔽₂ instance:** f = ∏_{k∈K} δ_k — not
the expected ∏(x−c), but correct.

## Wrong

Nothing marked wrong this sitting. One dead end they proposed themselves and
asked about (rev 21): to prove injectivity for infinite K, compare f and g
coefficient by coefficient and contradict a mismatched one. No contradiction is
reachable from a single slot. Card 0052 named the reduction instead — Φ is a
homomorphism, so Φ(f−g) = 0 and f−g ∈ ker Φ, and injectivity is ker Φ = {0}.
They had used that criterion in the finite case but did not reach for it here.

Earlier: fg's coefficients written aᵢbᵢ index by index, as if multiplication
behaved like addition.

## Owed, and recorded in the .tex

Above the 03.8 region: no general definition of δ_c anywhere in their work (only
𝔽₂, 𝔽₃, 𝔽₅ instances); no "the sum is finite because K is"; the collapse shown
but not justified; the arbitrariness lines for the product half and for k₁; for
the general kernel element, no line evaluating it at an arbitrary c and no line
saying f ≠ 0 (needs K[x] to have no zero divisors). Flagged to them, none
supplied by me.

## Next

**Card 0056 — the finite-degree check.** Expect: B only, degree 1000000; A is
not a polynomial. Then re-pose the monomorphism half a fourth time. Expect: h ≠
0 has some *finite* degree n, yet every one of infinitely many k ∈ K is a root,
so h has more than n roots. Contradiction, h = 0, f = g, Φ injective. Every
piece is on their own pages now — the kernel reduction (rev 22), the degree
ceiling (rev 23), finite degree (card 0056). **If the fourth posing does not
close it, stop withholding and name the contradiction outright.** No fifth rung.

The finite-degree question was the genuine gap all along, and it was worth the
three stalls to surface it: they had been treating "h has finite degree n" as an
extra hypothesis somebody had to grant, not as the definition of K[x]. Nothing
in the earlier cards had said so, because nothing had needed to.

**The diagnosed misunderstanding, and it is the useful thing here:** they owned
the degree fact only in the constructive direction — given roots, build the
polynomial, degree at least this much — and never as a *bound*: given the
degree, no more roots than that. Card 0054's non-example fixed it. Note the
separate failure mode it exposed, which matters more for next time: **they
reached the right conclusion and labelled it "I'm stuck."** They do not trust a
result that arrives as a rhetorical question. When a page says stuck, read the
mathematics above it before believing the word.

Then the epimorphism half: over an infinite field δ_c is not a polynomial at
all, by the same finite-roots fact, so Φ misses it and is not onto. That
finishes 3.8.

After that: 3.10, whose statement is still `\todo`. Lay the statement in when
you reach it. 3.2 and 3.3 remain owed with empty regions — come back to them at
the end of the sheet, unremarked.

## This student

Concrete lands, general does not — but general lands *straight off* two concrete
instances, so: make them do it twice in numbers, then ask for it in letters.
Pencilled questions get answered first, in their own card, never as `wrong`.
**"I'm stuck" is not reliable — check the work above it.** Twice now they have
written the correct step and declared themselves stuck under it, because the
answer arrived as a question they did not recognise as rhetorical.
They double-tap Send — a resent page with one added mark is a stall, not an
attempt. They run ahead of the ladder; read that as a skip and re-aim. Asked
twice with no attempt, stop withholding and name the line. When a piece is
right, say so in two lines and move.
