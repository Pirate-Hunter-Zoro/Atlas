# PSYCH-ASR rules

## The data fence

- Never read anything under phi/: the whole directory, by its name, whatever is put there. Never rename it; a renamed directory is unfenced.
- Never read a legacy data/ tree, a recording (.wav .m4a .mp3 .flac .mp4 .mov), or a pipeline artifact that carries speech (.rttm .aligned.json .diarized.json .transcript.txt). Never run an entry point that prints transcript spans.
- A read is anything that puts the bytes in front of you: cat, grep, a one-liner, a subagent. The hook is not the rule; never route around it.
- Open on purpose: filenames, sizes and timestamps; slurm_jobs/logs/; numbers-only siblings; all source. To learn the shape of fenced data, write a module that prints counts and run it.
- Every artifact that carries session content gets a numbers-only sibling. The owner eyeballs a new summary shape once before any guard allows it.
- The one exception, a model running on LIBR hardware, is ai-config/policy/LOCAL-MODELS.md. If you cannot say for certain that what you read stays on the node, refuse.
- On-prem only: no audio, transcript, feature or model call leaves the node. Anything driving a model over session content has no tool-calling surface.
- Never write a participant id (the BL### codes) into a tracked file, a commit message or output. Write BL### or <stem>.
- The check and every report carry only aggregate RELAY: lines.

## The work

- The reference transcript is the annotator's. Do not rebuild it, and do not write anything that repairs a transcript from the error log.
- Before writing anything that scores, compares or ranks arms, stop and ask the owner.
- No published DER is compared with ours: only numbers measured here, at one stated collar.
