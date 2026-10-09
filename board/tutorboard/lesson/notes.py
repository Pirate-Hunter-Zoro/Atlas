"""Typed messages, in both directions, and the drafts behind them.
"""

import json
import os
import re


def load_messages(repo, limit=60):
    out = []
    try:
        with open(repo.messages_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out[-limit:]


# Work in the inbox that no turn has taken, and since when: an unread line
# (`read` is set when a turn takes it), timed from the message's own stamp so
# it survives reloads and restarts.
def waiting(repo, limit=400):
    """The oldest thing in the inbox nobody has picked up, and how many there are."""
    oldest, count, signal = None, 0, ""
    for rec in load_messages(repo, limit=limit):
        # Read, or a line that wakes nothing (a bind, a mode change): nothing
        # is waiting on either.
        if rec.get("read") or rec.get("wake") is False:
            continue
        count += 1
        try:
            at = float(rec.get("t") or 0)
        except (TypeError, ValueError):
            continue
        if at and (oldest is None or at < oldest):
            oldest = at
            # What is waiting, so an expected wait is not reported as a stall.
            signal = (rec.get("signal") or "")
    if not count:
        return None
    return {"since": oldest, "count": count, "signal": signal}


def stroke_sig(s):
    """One stroke as a hashable value: every field but the `_` caches, numbers
    as floats, so a browser echo compares equal."""
    def freeze(x):
        if isinstance(x, bool):
            return x
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, (list, tuple)):
            return tuple(freeze(v) for v in x)
        if isinstance(x, dict):
            return tuple(sorted((str(k), freeze(v)) for k, v in x.items()
                                if not str(k).startswith("_")))
        return x
    return freeze(s) if isinstance(s, dict) else None


def ink_records(repo):
    """Every annotation record of `repo`, each read from where its key's ink
    lives (`course.repo.ink_dir`): cards from the session, document pages
    from the subject's `.ink/` when the session is bound."""
    from ..course import repo as course_repo        # local: light
    out = []
    for where, name in course_repo.ink_records(repo):
        try:
            with open(os.path.join(where, name), "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(rec, dict) or not rec.get("card"):
            continue
        if course_repo.ink_dir(repo, rec["card"]) != where:
            continue
        out.append(rec)
    return out


def load_notes_sent(repo):
    """Which cards' marks have already been handed to the tutor; separate from
    `load_notes`, whose shape is a contract with `Annotate.load`."""
    out = {}
    for rec in ink_records(repo):
        if rec.get("card"):
            out[rec["card"]] = bool(rec.get("sent"))
    return out


def load_notes_builds(repo):
    """`{key: {digest, at, pages}}`: the build each library-drawn page's marks
    were drawn on."""
    out = {}
    for rec in ink_records(repo):
        if rec.get("card") and isinstance(rec.get("build"), dict):
            out[rec["card"]] = rec["build"]
    return out


def load_notes(repo):
    """Every card's annotations, so a reload does not lose what was marked up."""
    out = {}
    for rec in ink_records(repo):
        if rec.get("card"):
            out[rec["card"]] = rec.get("strokes") or []
    return out


def load_text_drafts(repo):
    """Typed answers in progress, keyed by the question they answer."""
    out = {}
    try:
        names = sorted(os.listdir(repo.text))
    except OSError:
        return out
    for name in names:
        if not name.endswith(".txt"):
            continue
        qid = name[:-4]
        if not re.match(r"^\d{1,4}$", qid):
            continue
        try:
            with open(os.path.join(repo.text, name), "r", encoding="utf-8") as fh:
                out[qid] = fh.read()
        except OSError:
            continue
    return out


# Uncommitted-work badge, cached: `git status` is too slow to poll.


# A card's ink file is named by the card's id (`writing.ann_file`).
CARD_INK = re.compile(r"\A\d{1,4}\Z")
DOC_KEY = "doc/"


def card_ink(repo, ids):
    """`(notes, sent)` for the cards in `ids` and every non-document key, read
    from the session's ink directory; document ink comes with its pages."""
    ids = set(int(i) for i in ids or () if str(i).isdigit())
    marks, sent = {}, {}
    try:
        names = sorted(os.listdir(repo.notes))
    except OSError:
        return marks, sent
    for name in names:
        if not name.endswith(".json"):
            continue
        stem = name[:-5]
        if CARD_INK.match(stem) and int(stem) not in ids:
            continue
        try:
            with open(os.path.join(repo.notes, name), "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        key = rec.get("card") if isinstance(rec, dict) else None
        if not key or str(key).startswith(DOC_KEY):
            continue
        marks[key] = rec.get("strokes") or []
        sent[key] = bool(rec.get("sent"))
    return marks, sent


def doc_ink(repo, ident):
    """`(notes, sent)` for the pages of one document, keyed `doc/<ident>/p<n>`,
    from wherever `repo` keeps document ink."""
    want = DOC_KEY + str(ident or "") + "/"
    marks, sent = {}, {}
    for rec in ink_records(repo):
        key = str(rec.get("card") or "")
        if key.startswith(want):
            marks[key] = rec.get("strokes") or []
            sent[key] = bool(rec.get("sent"))
    return marks, sent
