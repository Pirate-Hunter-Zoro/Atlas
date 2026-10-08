import Mathlib
import LeanTP

/-!
# CharTwo

In characteristic two, every element is its own additive inverse.

Rewrite a + a as 2 * a first. This is the fact that quietly breaks half the
formulas in Galois theory — discriminants, quadratic formulas, separability —
which is why Garling keeps carving out char K = 2 as a special case.
-/

theorem add_self_eq_zero_char_two {K : Type*} [Field K] (h2 : (2 : K) = 0)
    (a : K) : a + a = 0 := by
  -- ===== PROOF: add_self_eq_zero_char_two =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: add_self_eq_zero_char_two =====
