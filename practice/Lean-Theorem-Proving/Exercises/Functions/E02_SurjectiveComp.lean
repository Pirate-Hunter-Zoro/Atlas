import Mathlib
import LeanTP

/-!
# SurjectiveComp

A composition of surjections is a surjection.

Surjectivity gives you an existential to destructure and then rebuild. Watch the
direction: you are handed a target in γ and must produce a source in α.
-/

theorem surjective_comp {α β γ : Type*} {f : α → β} {g : β → γ}
    (hf : Function.Surjective f) (hg : Function.Surjective g) :
    Function.Surjective (g ∘ f) := by
  -- ===== PROOF: surjective_comp =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: surjective_comp =====
