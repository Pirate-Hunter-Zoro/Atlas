import Mathlib
import LeanTP

/-!
# EvenOfEvenSq

If n² is even then n is even.

The contrapositive is easier: assume n is odd, write n = 2k + 1, and expand.
This lemma is the engine of the irrationality proof in the next exercise.
-/

theorem even_of_even_sq {n : ℤ} (h : Even (n ^ 2)) : Even n := by
  -- ===== PROOF: even_of_even_sq =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: even_of_even_sq =====
