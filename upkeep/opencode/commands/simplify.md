---
description: Simplify the changed code (reuse, dead code, needless complexity) and apply the fixes
---
Simplify the changed code: $ARGUMENTS

With no target, use the uncommitted diff (`git diff HEAD`). Look for duplicated logic that existing helpers already cover, dead or unreachable code, needless indirection, over-general abstractions, and slow patterns with an obvious faster equivalent. Behaviour must not change. Apply each fix, run the relevant tests, and report in a few lines what you changed. Do not hunt for bugs; that is /review.
