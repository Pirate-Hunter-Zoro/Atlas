import Mathlib
import LeanTP

/-!
# SubsetTrans

Subset inclusion is transitive.

Unfold what `s ⊆ t` means — a ∀ statement about membership — and this becomes
trivial. The habit of unfolding a definition before panicking is the lesson.
-/

theorem subset_trans' {α : Type*} {s t u : Set α} (h₁ : s ⊆ t) (h₂ : t ⊆ u) :
    s ⊆ u := by
  -- ===== PROOF: subset_trans' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: subset_trans' =====
