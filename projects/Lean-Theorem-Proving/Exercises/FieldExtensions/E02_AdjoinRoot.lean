import Mathlib
import LeanTP

/-!
# AdjoinRoot

The degree of a simple extension is the degree of the minimal polynomial.

Garling's Theorem 4.4. Notation: `F⟮α⟯` uses Mathlib's special angle brackets
for adjoining an element, not ordinary parentheses, and `minpoly F α` is the
minimal polynomial.

Again, Mathlib has this. Locating it and reading how the statement is phrased is
the exercise; a Galois final project would need this shape of statement
constantly.

The `F⟮α⟯` notation is *scoped* to the `IntermediateField` namespace, so it does
not exist until that scope is opened — hence the `open scoped` line below.
-/

open scoped IntermediateField

theorem adjoin_simple_degree {F : Type*} [Field F] {E : Type*} [Field E]
    [Algebra F E] (α : E) (h : IsIntegral F α) :
    Module.finrank F F⟮α⟯ = (minpoly F α).natDegree := by
  -- ===== PROOF: adjoin_simple_degree =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: adjoin_simple_degree =====
