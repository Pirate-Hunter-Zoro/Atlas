<!-- chapter: Ch 03 — Rings -->
# HANDOFF

**Ch 03, Rings (Garling) — homework.** Assigned: **3.1, 3.2, 3.3, 3.8, 3.10,
3.11, 3.12, 3.14, 3.15, 3.17, 3.25, 3.26.** Sheet:
`handwritten/20260902-exercise-list.png` (numbers only, not statements).

**Tooling.** `scripts/build.sh` fails silently on the Mac — use `board hw
build`. Statements live in `reading/ch03.txt` under the section-end
**Exercises** headings; grep the number. File pages to
`chapters/ch03-rings/handwritten/`. **Open the PNGs** — an ordinary image read
works; `board eyes <path>` is the fallback. Never ask this student to type
mathematics.

## Where it got to

**7 of 12 written up** (`board hw`): 3.1, 3.3, 3.8, 3.10, 3.11, 3.12, 3.14.
Document compiles, 5 pages, 0 warnings.

Still owed: **3.2** (skipped twice — *not now*, not never; come back unremarked
once the sheet is clear; they were most of the way through it on 2026-09-02 and
stalled on clearing denominators for an arbitrary α ∈ F[x]). **3.8** infinite-K
monomorphism half. **3.15, 3.17, 3.25, 3.26.** **3.11**'s divisibility
contrapositive never says "contrary to assumption, so a is prime" — noted in a
comment there.

## Right — do not re-teach

3.12 whole (φ multiplicative was *supplied*, not proved by them; irreducible vs
prime settled). 3.3 whole, including that a domain's powers stay nonzero, and
cancellation at general exponents. 3.14 both directions. deg(fg) = deg f + deg
g. Units of R[x] and of ℤ₄[x]. a ∈ (c) ⟺ c | a, and (c) = R ⟺ c a unit.

## The pattern, and it is the whole of what to watch

**The architecture is sound; the last clause is not.** Four times now: *non-zero*
absent from all of 3.3; *proper* and *not a unit* absent from all of 3.14; the
last line landing in R instead of (a); "(c) can't be a unit" where the theorem
is about c. When a definition is a conjunction they prove the interesting
conjunct and drop the side condition. Ask for the missing one by name, one at a
time — they fix it in a minute or two, unaided, every time.

Also: they mis-enumerate m² + 5n² style lists (three times). Check any such list
by hand.

## Next

**3.15, posed in full on card 0112, statement transcribed.** Cold, no ladder,
**first half only** — a is a root of f iff f ∈ (x − a) — because 3.15 is
literally the two-part ask they half-answer. Route: divide by x − a
(**Theorem 3.7**, `reading/ch03.txt:452`; Garling never calls it the division
algorithm), r = 0 or deg r < 1 so r is constant, evaluate at a to get r = f(a).
The one rung worth building if they stall is *deg r < 1 makes r a constant*.

## This student

Concrete lands. General lands only off **two instances that disagree** — one
gets promoted to a theorem. Ask **one** thing per card; the second is dropped.
They revise one page in place, often **write over** earlier work (keep the old
page, the proof may span two) and often fix the wrong end — say which end.
**They will skip pure algebra grind mid-page and are right to** — grant it, take
the computation over, but check the line they asked you to assume. Pencilled
questions get answered first, in their own card. **"I'm stuck" with a page
attached is unreliable** — read the working; with no page it is real. Their | and
∤ look identical; their set notation runs loose. Read intent, do not spend a
turn on it.
