import Mathlib
import LeanTP

/-!
# InvInv

The inverse of an inverse is the original element.

Follows immediately from uniqueness of inverses — reuse `inv_unique'` rather
than starting over, and notice that reusing your own earlier lemma is exactly
what `LeanTP/Basic.lean` is for once a lemma proves itself worth keeping.
-/

theorem inv_inv' {G : Type*} [Group G] (a : G) : (a⁻¹)⁻¹ = a := by
  -- ===== PROOF: inv_inv' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: inv_inv' =====
