# upkeep/opencode: the OpenCode parity layer

Gives DeepSeek inside OpenCode (1.19.5) the long-running harness tools: wakeups, cron, background shells, monitors, background agents, forks, workflow scripts, worktrees, notifications.

`python3 upkeep/opencode/install.py [--dry-run] [--home DIR]` installs it into `~/.config/opencode`. Exit status is the number of problems. `upkeep.py run` calls it; it is idempotent. Tests: `python3 -m unittest upkeep/opencode/test_install.py`.

| File | Installed as | Role |
| --- | --- | --- |
| `plugins/parity.ts` | `~/.config/opencode/plugins/` | Every tool. It must export only `ParityPlugin`, because OpenCode calls every exported function as a plugin |
| `agents/*.md`, `commands/*.md` | same names | `worker`, `deep`, `reviewer`, `structured`; `/loop`, `/ultracode`, `/review`, `/simplify` |
| `capabilities.md` | `~/.config/opencode/capabilities.md` | Listed in `instructions`. Names tools only, no vendor |
| `config.json` | merged into `opencode.jsonc` | The managed keys. Never copy it into the config dir: OpenCode loads a `config.json` there as config |
| `package.json` | merged into `~/.config/opencode/package.json` | Pins `@opencode-ai/plugin` and `sdk` to the opencode version; bump both with opencode |
| `env` | read by `shell.zsh` | Feature flags. Never `OPENCODE_EXPERIMENTAL=1`: it turns on the unstable code mode |
| `launchd/com.mikeyferguson.opencode-serve.plist` | `~/Library/LaunchAgents/` (by upkeep.py, `@HOME@` filled) | The persistent server on 127.0.0.1:4096. Its env block must equal `env` (a test checks) |
| `shell.zsh` | sourced from the upkeep block in `~/.zprofile` | Exports `env`; `oc` and `ocrun` attach to the server with `--dir "$PWD"`, or run a local opencode when it is down |
| `coder` | `~/bin/coder` | Same attach-or-fallback; keeps the line `exec opencode --auto` the doctor looks for |

The config merge parses JSONC and keeps every unmanaged key. A file that does not parse is reported and left alone. A commented original is saved once as `opencode.jsonc.before-upkeep`, because the rewrite drops comments. The merge deletes the `openrouter`, `groq` and `cloudflare` provider blocks, and drops `plugin` entries for files under `plugin/` or `plugins/`, which load automatically. Skills under `~/.claude/skills` and `~/.agents/skills` (any directory holding `SKILL.md`) are copied into `~/.config/opencode/skills`. Nothing is ever deleted.

## How the plugin works

- Every job reports by posting a message into the session that started it (`client.session.promptAsync`). The model ends its turn and is woken by `<task>`, `<monitor>`, `<wakeup>`, `<cron>`, `<bg_shell>` or `<workflow>`. This needs a live opencode process, so use the server (`oc`, `coder`). A plain `opencode run` exits and loses them.
- State lives in `$PARITY_STATE_DIR`, else `~/.local/state/opencode/parity/`: `jobs.json`, `shells/<id>.log`, `workflows/<run>/{script.js,journal.jsonl,log.txt,result.json}` and `parity.log`. On load the plugin re-arms the saved jobs. Overdue wakeups fire with `late_by`. Monitors are restarted. Background shells are detached, so their exit code file is still seen. Interrupted workflows are announced with their `resume_run_id`.
- A workflow `agent()` with a `schema` sends `format: json_schema` with `variant: "nothink"`, because DeepSeek rejects that tool choice while thinking. `think: true` asks for JSON in text instead and checks it. Opencode 1.19.5 cannot list a user message that carried a schema, so the plugin reads only the newest messages, and the TUI may fail to open such a child session.
- Built-in `task` with `background: true` (flag `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`) is the normal background subagent. `agent_spawn` covers worktrees and other models, and stands in if the flag goes away.
