import Mathlib
import LeanTP

/-!
# SubsetPreimageImage

A set is contained in the preimage of its image.

The reverse inclusion needs injectivity — think about why before you start, and
find the counterexample that kills it in general. Notation: `f '' s` is the
image of s, and `f ⁻¹' t` is the preimage of t.
-/

theorem subset_preimage_image {α β : Type*} (f : α → β) (s : Set α) :
    s ⊆ f ⁻¹' (f '' s) := by
  -- ===== PROOF: subset_preimage_image =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: subset_preimage_image =====
