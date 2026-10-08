/-!
# ForallAnd

A universal quantifier distributes over conjunction.

Both directions are constructive. Introducing a ∀ is `intro`; using one is
function application.
-/

theorem forall_and' {α : Type} (p q : α → Prop) :
    (∀ x, p x ∧ q x) ↔ (∀ x, p x) ∧ (∀ x, q x) := by
  -- ===== PROOF: forall_and' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: forall_and' =====
