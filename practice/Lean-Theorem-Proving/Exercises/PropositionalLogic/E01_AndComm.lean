/-!
# AndComm

Conjunction is commutative.

The first proof anyone writes in Lean. Both directions are separate obligations;
`constructor` splits an iff into them.
-/

theorem and_comm' (p q : Prop) : p ∧ q ↔ q ∧ p := by
  -- ===== PROOF: and_comm' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: and_comm' =====
