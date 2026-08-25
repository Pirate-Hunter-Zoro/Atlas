/-!
# ExistsOr

An existential quantifier distributes over disjunction.

Contrast this with the ∀/∧ case: the analogous statement for ∃ and ∧ is FALSE.
Work out a counterexample before you start, so you know which structure is
carrying the proof.
-/

theorem exists_or' {α : Type} (p q : α → Prop) :
    (∃ x, p x ∨ q x) ↔ (∃ x, p x) ∨ (∃ x, q x) := by
  -- ===== PROOF: exists_or' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: exists_or' =====
