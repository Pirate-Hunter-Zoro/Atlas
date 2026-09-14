import Mathlib
import LeanTP

/-!
# SubgroupInter

An element in two subgroups lies in their intersection.

Mathlib writes the intersection of subgroups as a lattice meet, ⊓, not ∩ — the
subgroups of a group form a lattice, and that is the notation that comes with
it. Getting used to lattice notation now saves pain in the Galois exercises.
-/

theorem subgroup_inter_mem {G : Type*} [Group G] (H K : Subgroup G) (x : G)
    (hH : x ∈ H) (hK : x ∈ K) : x ∈ H ⊓ K := by
  -- ===== PROOF: subgroup_inter_mem =====
  -- TODO(mferguson): your proof goes here. Delete the `sorry` when you replace it.
  sorry
  -- ===== END PROOF: subgroup_inter_mem =====
