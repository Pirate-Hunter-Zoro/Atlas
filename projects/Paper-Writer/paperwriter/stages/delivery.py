"""Delivery. Copy the finished manuscript and its builds into the output folder,
using stage-then-atomic-rename so a sync client never begins uploading a partial file.

Sub-organisation is `<project>/<paper>/<file>`. Delivery is idempotent: a target
already present with identical content makes this a verified no-op rather than a
redundant copy — verify before commit, at the very last boundary.

The Markdown manuscript is delivered alongside every built format, always. It is the
source, it is the thing an author edits, and it is the one artifact that exists even
when pandoc does not.

**And a second copy goes where the job said to put it.** `config.OUT_DIR` is one
directory for one harness, and one harness serves every workspace that drops a job, so
the out-directory cannot be each asking workspace's own. A job carrying `## Delivery`
names an absolute directory in the workspace that asked — see `jobspec.landing` — and
every artifact is placed there as well, keeping whatever subtree it has under
`OUT_DIR`.

**The landing is the paper's own directory, and naming it is the job's business.**
Nothing is appended here. A workspace writes more than one paper and two of them would
both be `manuscript.md` in one folder, so the asking side names the folder — which is
also what lets a REVISION land exactly over the document it corrects rather than beside
it under a slug of a title that has since changed. `manuscript.landing_for` on the
board is the whole of that decision.

That second copy is what makes a delivered paper a document like any other: the board
lists what is in the asking workspace, marks it as the factory's to revise, and can
hand the feedback back. A paper that exists only under `OUT_DIR` is a paper nobody can
find from the workspace it was written for.

**The landing never raises.** By the time it runs the paper is delivered and the work
is safe. A landing that is relative, or that cannot be written, is reported as a note
and the paper stays DELIVERED — the same rule a missing pandoc and a failed `git push`
already get.
"""

import os
from pathlib import Path

from .. import config, jobspec, paths
from ..infra import storage


def deliver_one(source, dest):
    """Deliver one file atomically. Returns the destination path."""
    if storage.already_delivered(source, dest):
        return dest                                     # verified no-op

    # Stage a copy on the destination volume, prove it is byte-identical, then rename
    # into place, so no partial file is ever visible to a sync client.
    staged = storage.staging_dir_for(dest.parent) / source.name
    storage.atomic_write_bytes(source.read_bytes(), staged)
    if storage.sha256_file(staged) != storage.sha256_file(source):
        raise RuntimeError(f"delivery: staged copy of {source.name} does not match "
                           f"its source")
    storage.atomic_place(staged, dest)
    return dest


def landing_dir(project_rec):
    """The absolute directory this job asked to be delivered into, or "".

    Read off the job and nowhere else. Absent is the ordinary case for a job
    dropped by hand, and it is not a defect: that paper lands under `OUT_DIR`
    and always did.
    """
    said = jobspec.landing((project_rec or {}).get("prompt_text") or "")
    if not said:
        return ""
    return os.path.expanduser(said)


def deliver(project_rec, paper_num, artifacts, project_name=None, paper_name=None,
            log_fn=None):
    """Deliver a finished paper's artifacts.

    Returns `(paths, note)` — every path written, the `OUT_DIR` copies first, and
    one sentence about the landing for the record to carry.
    """
    project_name = paths.slug(project_name or project_rec["project_id"])
    paper_name = paths.slug(paper_name or f"paper-{paper_num}")
    folder = config.OUT_DIR / project_name / paper_name

    # Delivered paths keep whatever subtree they had under the paper root, so
    # `sections/manuscript/04-methods.docx` arrives as that and not as a flat
    # `04-methods.docx` beside three other files with the same name from three other
    # documents.
    root = paths.paper_root(project_rec["project_id"], paper_num)
    delivered, relative = [], []
    for source in artifacts:
        if source is None or not source.exists():
            continue
        try:
            rel = source.resolve().relative_to(root.resolve())
        except (ValueError, OSError):
            rel = Path(source.name)
        delivered.append(deliver_one(source, folder / rel))
        relative.append((source, rel))

    landed, note = _land(project_rec, relative, log_fn=log_fn)
    return delivered + landed, note


def _land(project_rec, relative, log_fn=None):
    """The second copy, in the workspace that asked. Returns `(paths, note)`.

    NEVER RAISES. The paper is already delivered by the time this runs, and a
    directory somebody has since moved must not be the reason a finished paper's
    status stays unfinished.
    """
    said = landing_dir(project_rec)
    if not said:
        return [], ("the job named no landing, so the delivered copy is under "
                    "OUT_DIR only.")
    if not os.path.isabs(said):
        return [], (f"the job's landing `{said}` is not an absolute path, so there is "
                    f"no root to resolve it against; nothing was placed there.")
    if not relative:
        return [], "nothing was delivered, so nothing was placed in the landing."

    where = Path(said)
    out = []
    try:
        where.mkdir(parents=True, exist_ok=True)
        for source, rel in relative:
            out.append(deliver_one(source, where / rel))
    except (OSError, RuntimeError) as exc:
        note = (f"delivered, but the landing {where} could not be written: {exc}. "
                f"The paper is under OUT_DIR; copy it across by hand.")
        if log_fn:
            log_fn(f"delivery: {note}")
        return out, note

    note = f"{len(out)} file(s) also placed in {where}."
    if log_fn:
        log_fn(f"delivery: {note}")
    return out, note
