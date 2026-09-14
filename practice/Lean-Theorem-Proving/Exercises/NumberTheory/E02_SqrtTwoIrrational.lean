import Mathlib
import LeanTP

/-!
# SqrtTwoIrrational

There is no rational whose square is 2.

The classical proof. The work is in getting a rational into lowest terms and
deriving the contradiction from `even_of_even_sq` applied twice. Mathlib has
machinery for numerators and denominators being coprime — find it rather than
rebuilding it.
-/

theorem sqrt_two_irrational : ¬ ∃ q : ℚ, q ^ 2 = 2 := by
  -- ===== PROOF: sqrt_two_irrational =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: sqrt_two_irrational =====
