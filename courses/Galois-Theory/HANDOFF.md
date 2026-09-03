<!-- chapter: Ch 03 — Rings -->
# HANDOFF

**Ch 03, Rings (Garling) — homework.** Assigned in order: **3.1, 3.2, 3.3, 3.8,
3.10, 3.11, 3.12, 3.14, 3.15, 3.17, 3.25, 3.26.** Sheet:
`handwritten/20260902-exercise-list.png`. Skeleton laid; build clean via
`bash scripts/build.sh <tex>`. `board recap` and `board next` work; other
subcommands fail.

## Where it got to

**3.1** — done, transcribed as written.

**3.2, 3.3** — skipped after seventeen revisions and *"I have lost patience."*
Skip means *not now*: regions empty, come back after the sheet, unremarked on.
Owed on surjectivity: dα ∈ R[x], φ(γ) = α/β, dβ ≠ 0, and injectivity.

**3.8** — homomorphism clause finished, both halves, transcribed. Now mid-ladder
on the epimorphism for finite K, all of it correct so far.

## Right — do not re-teach

Clearing denominators by the product; a polynomial is not its function;
(Φ(f))(k) ∈ K while Φ(f) ∈ K^K; x²+x ∈ ker Φ over 𝔽₂; cₘ = Σ_{i+j=m} aᵢbⱼ;
both halves of the 3.8 homomorphism proof; f = 1+x hits 0↦1, 1↦0 over 𝔽₂;
(x−1)(x−2) evaluated over all 𝔽₃ (2, 0, 0); scaling it to the indicator
δ = 2p (1, 0, 0); subtraction in a ring is a + (−b) — they asked, they have it.

## Wrong, and what it was

They wrote fg's coefficients as aᵢbᵢ, index by index, as if multiplication
behaved like addition. Arithmetic fixed the idea but the proof line did not
move: asked twice, they drew cₘ in the margin and left the proof untouched.
Writing the formula *somewhere* felt like using it. Naming the exact line to
cross out is what worked.

## Next

Card 0046 is unanswered and is the thing to read first: given δ₀ = 2(x−1)(x−2),
δ₁ = 2x(x−2), δ₂ = 2x(x−1) tabulated with their values, assemble f with
Φ(f) = h for h = (0↦2, 1↦0, 2↦1). Expect f = 2δ₀ + δ₂, the δ₁ term dropping
out, with values 2, 0, 1. **The idea is the sum** — at each k only one term
survives — and it is deliberately not stated on the card. Let them find it,
then name it, because that sum *is* the epimorphism.

Then generalise: δ_c(x) = (∏_{a≠c}(x−a))·(∏_{a≠c}(c−a))⁻¹ and f = Σ_c h(c)δ_c.
Then non-injectivity for finite K (∏_{c∈K}(x−c) is nonzero and in the kernel),
then the infinite case. Still owed on 3.8: the closing "as k was arbitrary"
line for the product half.

## This student

Concrete lands, general does not. Pencilled questions get answered first, in
their own card, never as a wrong answer — they ask good ones (why subtraction
is legal in a ring). Asked twice with no attempt → stop withholding, name the
target line. One half of an identity per turn. Hand them the drudgery half
(the second and third indicator) and keep the new idea for the question. They
double-tap Send — hash against the previous revision before reading a page as
new. Their ∘ for the product is set as juxtaposition in the .tex; leave it.
When a piece is right, say so in two lines and move.
