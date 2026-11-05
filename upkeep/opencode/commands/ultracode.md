---
description: Take on a large coding task by orchestrating subagents with workflow scripts
model: deepseek/deepseek-v4-pro
---
Task: $ARGUMENTS

Work as an orchestrator, not a solo coder. Your context is for planning and judgement; subagents do the reading and the edits.

1. Understand the task just enough to split it: at most five tool calls of your own (a listing, a README, a grep), then write the plan with `todowrite`. Reading the code in depth is the survey phase's job; a sixth read of your own means you are solo coding.
2. The plan holds, before any build:
   - each requirement restated as the check the owner would run;
   - the owner's own examples: the real sessions, files, endpoints or clones the request is about;
   - Done when: checks naming at least one of those real artifacts, run read-only, as well as fixtures;
   - the threat model: every string from a model or user that reaches a file, an evaluated config or a command, and how each is validated or escaped.
3. Write a `workflow` script for each stage:
   - `phase("survey")`: `parallel` agents with `readonly: true`, each mapping one area, returning JSON through a `schema`.
   - `phase("build")`: one agent per independent change, each told exactly which files it owns. Use worktrees (`worktree_create`, agent `cwd`) when changes could collide.
   - `phase("verify")`: `agent: "verifier"` with `think: true`. Its brief is the owner's request verbatim, the Done-when list and the threat model, never the builder's summary. It returns a `verdict`.
   - Every fix runs through `verify_until_pass(fixStage, verifyStage, {max: 3})`, with `agent: "fixer"` briefed on the failing verdicts and the files it owns.
   Keep prompts self-contained: a subagent sees only its prompt. Return a compact summary object that carries the final verdicts.
4. Start the workflow (background is the default) and end your turn. When the `<workflow>` message arrives, read the result, decide, and run the next stage. On a script failure, fix the script and rerun with `resume_run_id` so finished agents are not repeated.
5. A standing `fail` blocks the commit. Fix and re-verify, or stop and put the failing verdict to the owner. Then run the tests yourself, and commit named paths if the user asked for it.
6. Follow the owner's global instructions, `~/.config/opencode/AGENTS.md` (the same file as `~/.claude/CLAUDE.md`). The report is at most 6 lines: what changed, what was verified against which real artifact, every failed or skipped check, and any `fail` you shipped over, quoted word for word.
