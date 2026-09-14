/-!
# Contrapositive

The contrapositive of an implication follows from it.

Remember what ¬p unfolds to: p → False. Once you see that, this is function
composition and nothing more. This direction needs no classical logic.
-/

theorem contrapositive (p q : Prop) : (p → q) → (¬q → ¬p) := by
  -- ===== PROOF: contrapositive =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: contrapositive =====
