---
description: Review the current diff (or a path, branch or commit) for correctness bugs
subtask: true
agent: reviewer
---
Review for correctness bugs: $ARGUMENTS

With no target, review the uncommitted diff (`git diff HEAD`); a branch name means `git diff main...<branch>`. Read surrounding code as needed. Report only defects that break behaviour: file and line, what goes wrong, and a concrete input or state that triggers it, most severe first. No style notes. If nothing survives scrutiny, say so in one line.
