import Mathlib
import LeanTP

/-!
# TowerLaw

The tower law: degrees multiply up a tower of finite extensions.

Garling's Theorem 4.3, and the workhorse of the whole course. In Mathlib the
degree [L:K] is `Module.finrank K L`, and the tower relationship between three
algebras is carried by the `IsScalarTower` instance rather than by an equation.

Mathlib proves this already. Find the lemma, and read its proof — the point of
this exercise is learning to search Mathlib for a result you already know under
a different name, which is most of what using it consists of.
-/

theorem tower_law (F K L : Type*) [Field F] [Field K] [Field L]
    [Algebra F K] [Algebra K L] [Algebra F L] [IsScalarTower F K L]
    [FiniteDimensional F K] [FiniteDimensional K L] :
    Module.finrank F K * Module.finrank K L = Module.finrank F L := by
  -- ===== PROOF: tower_law =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: tower_law =====
