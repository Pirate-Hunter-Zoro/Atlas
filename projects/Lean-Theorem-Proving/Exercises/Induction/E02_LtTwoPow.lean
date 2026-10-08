import Mathlib
import LeanTP

/-!
# LtTwoPow

Every natural is smaller than its own power of two.

Straightforward induction, but the successor step needs a small inequality
argument rather than pure rewriting. A good first taste of induction where the
step is not just algebra.
-/

theorem lt_two_pow' (n : ℕ) : n < 2 ^ n := by
  -- ===== PROOF: lt_two_pow' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: lt_two_pow' =====
