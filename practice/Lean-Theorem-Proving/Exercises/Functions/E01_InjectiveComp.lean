import Mathlib
import LeanTP

/-!
# InjectiveComp

A composition of injections is an injection.

`Function.Injective f` unfolds to: for all a b, f a = f b → a = b. Apply the two
hypotheses in the right order and it falls out.
-/

theorem injective_comp {α β γ : Type*} {f : α → β} {g : β → γ}
    (hf : Function.Injective f) (hg : Function.Injective g) :
    Function.Injective (g ∘ f) := by
  -- ===== PROOF: injective_comp =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: injective_comp =====
