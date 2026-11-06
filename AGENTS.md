# AGENTS.md

Rules for any assistant working in Atlas. The rest is in [README.md](README.md),
[HANDOFF.md](HANDOFF.md) and [board/README.md](board/README.md). A board tutor turn follows
[board/TEACHING.md](board/TEACHING.md).

- **The repository is public.** A pushed commit is published and kept forever. Never commit a
  key, a session, a material or a machine's own path.
- **Commit named paths only,** with `bash board/scripts/save-and-push.sh "message" -- <paths>`
  (a tutor turn uses `board push "message" -- <paths>`). Never `git add -A`, `git add .` or
  `git commit -a`, because the main checkout carries the owner's uncommitted work. Never
  `git stash` or force-push.
- **Edit `board/` only in a worktree** under `~/Developer/Atlas-wt/<item>`. The main checkout,
  `~/Developer/Atlas`, serves the iPad live, so a half-finished edit there breaks a lesson in
  progress.
- **Remove a worktree as soon as it is merged or abandoned,** in any repository:
  `git worktree remove <path>`, delete its branch, and remove the parent directory
  (`~/Developer/Atlas-wt`) once it is empty. upkeep also removes merged, clean worktrees idle
  for 24 hours; remove yours at once rather than leave them for it.
  Delete the scratch files and directories you made (clones, copies, test data, logs) as soon
  as the work is done with them.
- **Run `python3 board/test/run.py` and leave it green before merging board code.** Merge only
  when every `sessions/*/agent.json` has `turn_pid` null or absent and the owner is not
  mid-lesson.
- **Never read a credential,** not even to check that it exists:
  `~/.local/share/opencode/auth.json`, `keys.env` and any `*.env`, `~/.config/api-keys/`,
  `rclone.conf` and `~/.config/rclone`, `~/.config/media-syncer`, `backup-private/`, SSH keys,
  and plists that hold keys. upkeep's `key_sync` places the DeepSeek key; nothing else needs
  to see it.
- **DeepSeek through OpenCode is the AI.** Its one spec is `board/tutorboard/agents/recipes.py`.
  Add no provider, no fallback chain and no other assistant.
- **Take a repository root from `git rev-parse --show-toplevel`.** Never count `dirname`s.
