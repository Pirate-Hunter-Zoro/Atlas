---
description: Returns JSON matching a schema. Used by workflow scripts for schema output.
mode: subagent
hidden: true
model: deepseek/deepseek-flash
variant: nothink
permission:
  doom_loop: allow
  external_directory: allow
  edit: deny
  write: deny
  apply_patch: deny
  task: deny
---
Answer with exactly the data the request asks for, in the requested structure. No commentary.
