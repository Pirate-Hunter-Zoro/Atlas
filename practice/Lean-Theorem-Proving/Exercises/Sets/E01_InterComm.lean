import Mathlib
import LeanTP

/-!
# InterComm

Intersection is commutative.

Sets in Mathlib are predicates in disguise: `Set α` unfolds to `α → Prop`. Two
sets are equal when they have the same members, which is what `Set.ext` says.
This exercise is `and_comm'` wearing a costume — notice that.
-/

theorem inter_comm' {α : Type*} (s t : Set α) : s ∩ t = t ∩ s := by
  -- ===== PROOF: inter_comm' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: inter_comm' =====
