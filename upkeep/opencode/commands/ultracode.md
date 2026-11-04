---
description: Take on a large coding task by orchestrating subagents with workflow scripts
---
Task: $ARGUMENTS

Work as an orchestrator, not a solo coder. Your context is for planning and judgement; subagents do the reading and the edits.

1. Understand the task and the code just enough to split it: at most five tool calls of your own (a listing, a README, a grep), then write the plan with `todowrite`. Reading the code in depth is the survey phase's job, not yours; a sixth read of your own means you are solo coding.
2. Write a `workflow` script for each fan-out stage. Typical shape:
   - `phase("survey")`: `parallel` agents, each mapping one area, returning JSON through a `schema` (files, functions, risks).
   - `phase("build")`: one agent per independent change, each told exactly which files it owns. Use worktrees (`worktree_create`, agent `cwd`) when changes could collide.
   - `phase("verify")`: agents run the tests and review the diffs against the plan with `schema` verdicts.
   Return a compact summary object from the script. Keep prompts self-contained: a subagent sees only its prompt.
3. Start the workflow (background is the default) and end your turn. When the `<workflow>` message arrives, read the result, decide, and run the next stage. On a failure, fix the script and rerun with `resume_run_id` so finished agents are not repeated.
4. Finish by running the tests yourself, committing if the user asked for it, and reporting in a few lines what changed and what is left.
