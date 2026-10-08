import Mathlib
import LeanTP

/-!
# UniqueIdentity

A left identity in a monoid is *the* identity.

One line, if you pick the right instantiation of h. This is the first exercise
where the structure comes from a typeclass instance rather than from a
hypothesis you were handed — get comfortable with where `1` and `*` come from.

Primed, because Mathlib already owns the root-level name `unique_one` (a fact
about a `Unique` type with a `One`, which is a different statement entirely).
-/

theorem unique_one' {M : Type*} [Monoid M] (e : M) (h : ∀ a : M, e * a = a) :
    e = 1 := by
  -- ===== PROOF: unique_one' =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: unique_one' =====
