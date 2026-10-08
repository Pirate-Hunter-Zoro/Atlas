import Mathlib
import LeanTP

/-!
# SumRange

The Gauss sum, stated without division so it lives entirely in ℕ.

Induction on n. `Finset.sum_range_succ` peels the last term off the sum; after
that it is arithmetic. Stating it as 2 * sum avoids natural-number division,
which truncates and would make the statement harder than the mathematics.
-/

theorem two_mul_sum_range (n : ℕ) :
    2 * ∑ i ∈ Finset.range (n + 1), i = n * (n + 1) := by
  -- ===== PROOF: two_mul_sum_range =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: two_mul_sum_range =====
