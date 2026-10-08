import Mathlib
import LeanTP

/-!
# UnionDistribInter

Union distributes over intersection.

After `ext`, this reduces to a propositional tautology. Whether you finish it by
hand or let a decision procedure close it is your call, but do it by hand once.
-/

theorem union_distrib_inter' {α : Type*} (s t u : Set α) :
    s ∪ (t ∩ u) = (s ∪ t) ∩ (s ∪ u) := by
  -- ===== PROOF: union_distrib_inter' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: union_distrib_inter' =====
