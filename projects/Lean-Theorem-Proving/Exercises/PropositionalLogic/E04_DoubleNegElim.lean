/-!
# DoubleNegElim

Double negation elimination.

This one is *not* constructively provable, unlike the three before it. You need
classical reasoning — `Classical.byContradiction` or `by_cases`. Understanding
exactly why the constructive proof fails is the point of the exercise.
-/

theorem double_neg_elim (p : Prop) : ¬¬p → p := by
  -- ===== PROOF: double_neg_elim =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: double_neg_elim =====
