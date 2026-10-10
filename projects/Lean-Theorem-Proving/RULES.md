# Lean Theorem Proving rules

- You write the statement; the owner writes the proof. You produce the docstring, the imports and the signature, stated correctly and elaborating cleanly, and a marked proof region holding nothing but sorry, between `-- ===== PROOF: <name> =====` and `-- ===== END PROOF: <name> =====`.
- In teach mode never put a proof term or a tactic inside a marked region: not a first tactic, not a skeleton, not a commented-out sketch.
- Never delete or renumber a marker pair. If a statement is wrong, fix the statement and leave the region alone.
- A proof the owner wrote is theirs. Review it, say whether it is right and point at the step that breaks; never rewrite it.
- In do mode, and only for a proof the owner names, you may fill a region. Say which ones you filled.
- Name tactics and Mathlib lemmas in prose and say what each leaves behind; never assemble them into a script to paste. Teach the search (exact?, apply?, rw?, loogle); never run it for them and hand back a one-line proof.
- Building is yours. Report which exercises compile, which still contain sorry and which fail for a real reason: "it built" is not "it is proved". Fetch the Mathlib cache; never compile Mathlib from source.
