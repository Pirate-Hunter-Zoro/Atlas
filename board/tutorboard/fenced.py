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

Standard library only, like everything else. `refused` does not touch the
filesystem -- it is a question about a path, and it is asked of paths that have
not been opened yet. `holds` is the same question asked of a WORKSPACE, and that
one is a directory listing, because whether a workspace has a fence in it is a
fact about what is on disk.
"""

import os
import time


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


# ---------------------------------------------------------------------------
# Does this WORKSPACE hold a fence, and is that sayable before a tap
# ---------------------------------------------------------------------------
# The question above is asked of a path that is about to be handed to something.
# This one is asked of a whole workspace, before anything has been chosen: *does
# this box hold content only one assistant may read?* Nothing answered it, so the
# chooser offered a hosted model in a fenced workspace exactly as it does in a
# course, and the only thing between that tap and a hosted model reaching for
# session content was a hook the person cannot see.
#
# ONE LEVEL DEEP, AND THAT IS THE RULE RATHER THAN A SHORTCUT. `refused` matches
# the name at any depth because it is guarding a file that is about to be opened.
# This is labelling a workspace on a chooser, and a fence is a top-level
# directory of the workspace that holds it. Walking the whole tree to label a row
# would put a `data/` directory six levels down inside somebody's vendored
# dependency on the front door, which is a warning that is true and means
# nothing.
#
# Cached, because the hub asks this on every build -- four times a second -- and
# `machines.workspaces` asks it once per workspace per poll. A fence appearing is
# a `mkdir`, not an event.
SEEN_TTL = 60.0
_SEEN = {}


def holds(root):
    """The fenced directories this workspace actually has, as a sorted tuple.

    Empty means no fence, which is the answer for every workspace but one today.
    A root that cannot be listed is not a workspace with a fence -- it is a
    directory that is not there, and saying "fenced" about it would be a warning
    nobody can act on.
    """
    root = str(root or "")
    if not root:
        return ()
    now = time.time()
    hit = _SEEN.get(root)
    if hit and now - hit[0] < SEEN_TTL:
        return hit[1]
    try:
        found = tuple(sorted(
            n for n in os.listdir(root)
            if n.lower() in NEVER and os.path.isdir(os.path.join(root, n))))
    except OSError:
        found = ()
    _SEEN[root] = (now, found)
    return found


def forget():
    """Drop the cache. For a test, and for a walk that has just made one."""
    _SEEN.clear()
