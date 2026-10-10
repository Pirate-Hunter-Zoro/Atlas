import Mathlib
import LeanTP

/-!
# TypeclassInference

Unfolding the successor case of monoid exponentiation.

The point is not the mathematics, it is learning to find the Mathlib lemma that
already says this, and to recognise when a goal is true by definition.
-/

theorem monoid_pow_succ {M : Type*} [Monoid M] (a : M) (n : ℕ) :
    a ^ (n + 1) = a ^ n * a := by
  -- ===== PROOF: monoid_pow_succ =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: monoid_pow_succ =====
