import Mathlib
import LeanTP

/-!
# InvUnique

Inverses in a group are unique.

Multiply both sides on the left by a⁻¹ and use associativity. Doing this by hand
once, before discovering that Mathlib has it, is the exercise.
-/

theorem inv_unique' {G : Type*} [Group G] {a b : G} (h : a * b = 1) :
    b = a⁻¹ := by
  -- ===== PROOF: inv_unique' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: inv_unique' =====
