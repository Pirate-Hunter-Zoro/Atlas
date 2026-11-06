---
description: Take on a large coding task by orchestrating subagents with workflow scripts
model: deepseek/deepseek-v4-pro
---
Task: $ARGUMENTS

Work as an orchestrator, not a solo coder. Your context is for planning and judgement; subagents do the reading and the edits.

1. Understand the task just enough to split it: at most five read calls of your own (a listing, a README, a grep), then write the plan with `todowrite`, two steps or more. The plugin refuses a sixth read before that plan. Reading the code in depth is the survey phase's job.
   Build in a worktree, never in the checkout you were started in: `worktree_create` one for the task (under `~/Developer/Atlas-wt/<item>` for Atlas), point every builder and fixer at it with `cwd`, and merge it back only after the final verify passes. The checkout you started in may be serving the owner live. The plugin refuses a file write in any repository's main checkout from this session and every agent it starts.
2. The plan holds, before any build:
   - each requirement restated as the check the owner would run;
   - the owner's own examples, by name: the session ids, file paths, URLs or clones the request is about. A survey agent finds them read-only (a live endpoint such as the board's `/sessions.json`, the repository's `sessions/`); list what it found.
   - When the request describes something already broken ("when I resume them, it goes to..."), those existing records are the acceptance test. The survey lists every record of that kind, not a sample: say how it found them (the field or title that marks them) and how many there are. A fix that works only for data created after it ships, or for some of those records, has not done the task: backfill or derive what each old record lacks, and the check runs over all of them.
   - Done when: checks naming at least one of those real artifacts, run read-only, as well as fixtures;
   - the threat model: every string from a model or user that reaches a file, an evaluated config or a command, and how each is validated or escaped.
3. Write a `workflow` script for each stage:
   - `phase("survey")`: `parallel` agents with `readonly: true`, each mapping one area, returning JSON through a `schema`.
   - `phase("build")`: one agent per independent change, each told exactly which files it owns. Use worktrees (`worktree_create`, agent `cwd`) when changes could collide.
   - Then `verify_until_pass(fixStage, verifyStage, {max: 3})`. Its `verifyStage` starts fresh `agent: "verifier"` agents with `think: true` and a `schema` holding a `verdict` field, and returns what they returned. Each verifier's brief is the owner's request verbatim, the Done-when list, the real artifacts by name and the threat model, never the builder's summary. A verifier checks those real artifacts read-only against the built code; a verdict whose evidence is only fixtures or tests is a `fail`. Its `fixStage` gets the failing verdicts and starts `agent: "fixer"`, briefed on those verdicts and the files it owns. Every fix is re-verified this way; never fix outside it.
   Keep prompts self-contained: a subagent sees only its prompt. Return a compact summary object that carries the final verdicts.
4. Start the workflow (background is the default) and end your turn. When the `<workflow>` message arrives, read the result, decide, and run the next stage. Read a subagent's session with `session_read`. On a script failure, fix the script and rerun with `resume_run_id` so finished agents are not repeated.
5. A standing `fail` blocks the commit: the plugin refuses `git commit`, `merge`, `push` and other shipping commands until a later verify passes or the owner says "ship over it". Fix and re-verify, or stop and put the failing verdict to the owner. Then run the tests yourself, and commit named paths if the user asked for it.
   Merge each worktree's branch with `git merge <branch>` from the main checkout: the plugin then removes that worktree when it is clean, deletes the branch, and removes the parent directory, such as `~/Developer/Atlas-wt`, when it is empty. Remove one you abandon with `worktree_remove`. Never leave a worktree behind.
6. Follow the owner's global instructions (`~/.config/opencode/AGENTS.md`, or `~/.claude/CLAUDE.md` where it is missing). The report is at most 6 lines: what changed, what was verified against which real artifact, every failed or skipped check, and any `fail` you shipped over, quoted word for word.
