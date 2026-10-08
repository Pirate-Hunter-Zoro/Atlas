/-!
# NotForall

Negating a universal gives an existential counterexample.

One direction is constructive; the other is not, and needs classical reasoning.
Identify which is which before reaching for a tactic.
-/

theorem not_forall' {α : Type} (p : α → Prop) :
    ¬(∀ x, p x) ↔ ∃ x, ¬ p x := by
  -- ===== PROOF: not_forall' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: not_forall' =====
