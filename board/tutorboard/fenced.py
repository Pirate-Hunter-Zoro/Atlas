"""fenced.py -- the directories nothing in this tool may look inside, by name.

ONE LIST, BECAUSE TWO LISTS DRIFT. `research/PSYCH-ASR/phi/` is session content:
the recordings, the turn tables, the joined transcripts. 308 MB of identifiable
therapy audio in a directory in this repository, fenced from the assistant by
`ai-config/policy/phi.py`, which matches the directory NAME.

The name has to be refused in every place that walks a workspace and hands what
it found to something else. `manuscript.py` refused it and `course/reading.py`
did not, so the manuscript factory could not be pointed at that tree while the
document drawer offered `phi/stage1/Audio Transcription.pdf` under the id
`audio-transcription`, rendered it to PNGs, and wrote its address into a tutor's
prompt beside an instruction to open and read a page. Both modules were right
about the rule. Only one of them knew it.

So the rule lives here and every module that needs it reads it from here.

**Matched on the directory NAME, at any depth.** Not on a prefix, not on a
depth, and not on a size floor happening to exclude what is inside it: those are
all true by accident today and none of them is the rule. `phi/stage1/x.pdf` and
`a/b/c/phi/x.pdf` are the same refusal.

The failure mode this guards is silent and one-way. A document that reaches a
tutor has been read; a directory that reaches a manuscript factory has been
mined. Neither can be taken back afterwards, which is why the check is cheap,
central, and belt-and-braces over whatever allowlist sits in front of it.

Standard library only, like everything else. Nothing here touches the
filesystem -- it is a question about a path, and it is asked of paths that have
not been opened yet.
"""


# AND NEVER THESE, WHATEVER ELSE CHANGES.
#
# `phi` is the session content. `data`, `raw` and `audio` are what feeds it and
# what comes out of it. `stage1` and `stage2` are the pipeline's own working
# directories, which hold both. `inbox` is where something arrives before
# anybody has decided what it is.
#
# `test/writing_up.py` fails the suite if this stops holding for a manuscript
# job, and `test/plan.py` if it stops holding for a document.
NEVER = ("phi", "data", "inbox", "stage1", "stage2", "raw", "audio")

# Where a workspace keeps output worth showing or citing.
#
# AN ALLOWLIST, AND IT MUST STAY ONE. This is what a manuscript job is permitted
# to mine and what the figure drawer is permitted to walk, chosen on somebody's
# behalf. A blocklist here -- "everything except the obvious ones" -- would hand
# over whatever a workspace happens to grow next.
RESULT_DIRS = ("results", "figures", "tables", "artifacts", "analysis")


def refused(path):
    """Is any part of this path a directory nothing may be pointed at?

    Backslashes are normalised first, because a path that came out of a file
    somebody wrote is a path in whatever notation they wrote it in.
    """
    parts = [x.lower() for x in str(path or "").replace("\\", "/").split("/")]
    return any(x in NEVER for x in parts)
