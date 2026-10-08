# Plan

The worksheet *Automorphisms, Irreducibility and Splitting Fields*, problems
7--12, uploaded 2026-09-22 as
`live/inbox/uploads/20260922-150639-01-Open-folder-Galois-Theory-2.png`
(problems 7--9) and `-00-Open-folder-Galois-Theory.png` (problems 10--12).
Chapter 6 is skipped; `DIRECTION.md` is the authority for that.

Four of the six are in scope: **7, 8, 9, 10**. Problems 11 (finite subgroups of
$K^\times$ are cyclic) and 12 (finite fields as splitting fields) are the
finite-field pair, need none of the four, and get their own sheet when worked.

## Order of work

Book order, which is also the dependency order.

1. **7** --- an automorphism sends a root of $f \in F[x]$ to a root of $f$;
   $\sigma$ is determined by its values on generators; hence
   $\operatorname{Aut}(\mathbb{Q}(\zeta_n)/\mathbb{Q})$ injects into
   $(\mathbb{Z}/n\mathbb{Z})^\times$ and has order at most $\varphi(n)$.
2. **8** --- conjugate roots give a unique isomorphism $F(\alpha) \to F(\beta)$;
   $\Phi_p$ is irreducible over $\mathbb{Q}$; the injection of 7(c) is onto for
   $n = p$.
3. **9** --- the whole machine on $x^4+1$ and $\zeta_8$: degree 4, the three
   quadratic factorisations, $K = \mathbb{Q}(i,\sqrt2)$, and the three
   order-2 automorphisms with their fixed fields.
4. **10** --- the splitting field of $x^3-2$ is $\mathbb{Q}(\sqrt[3]{2},\zeta_3)$
   of degree 6, the general $x^n - a$, and $\operatorname{Aut}(E/\mathbb{Q})$
   inside $S_3$.

## Write-up

One file:
`homework/worksheet-automorphisms-splitting-fields/worksheet-automorphisms-splitting-fields.tex`.
`board hw use worksheet-automorphisms-splitting-fields` pins a sitting to it.
All fourteen lettered parts of 7--10 are transcribed with empty solution
regions, labelled `7(a)` through `10(d)` in the sheet's order; the file builds
to 2 pages with 0 warnings.

A solution region is filled in the same turn the answer is agreed, not at the
end of the sitting. The student's own argument goes in, in their steps.
`board hw file <label>` puts the handwriting beside it and `board hw build`
compiles the set. `board hw status` reads the `% ===== SOLUTION <label> =====`
markers: one problem environment per label, each opener matched by its closer,
or the report is wrong.

## What is closed

Chapter 6 is out of scope. `chapters/ch06-ruler-and-compass-constructions/`
holds four transcribed statements with empty regions and is left as it stands.
The earlier sheet under `homework/worksheet-field-extensions/` (problems 1--6,
which this one references) is a separate set and is not in scope.
