import Mathlib
import LeanTP

/-!
# NoZeroDivisors

A field has no zero divisors.

Case on whether a is zero. If it is not, it has an inverse — that is the whole
content of being a field, and the entire proof.
-/

theorem mul_eq_zero' {K : Type*} [Field K] {a b : K} (h : a * b = 0) :
    a = 0 ∨ b = 0 := by
  -- ===== PROOF: mul_eq_zero' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: mul_eq_zero' =====
