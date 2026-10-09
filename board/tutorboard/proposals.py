"""A mark on a meeting slide becomes a PROPOSED direction, in one workspace.

    "My mentors, seeing this presentation, will give me suggestions on new
     directions to take -- THAT'S what these annotations will serve as -- the
     agent should use them to decide which new directions we will take after
     the meeting's feedback."

THE DECK IS THE MEETINGS SUBJECT'S (`briefs.deck`), so every page of it maps
to projects/Meetings and a mark on any slide is input for the Meetings tutor,
which knows every project the deck is about.

**THIS IS NOT FEEDBACK AND IT DOES NOT GO THROUGH `/library/feedback`.** That
route writes a feedback file and wakes a `[revise]` turn, which would spend a
turn polishing the slides -- correcting a throwaway communication tool while
throwing away the only thing the marks actually said. The owner's sentence is
the specification and it is unambiguous: *"NOT to give feedback on them in
terms of the presentation."*

**PROPOSED, NEVER APPLIED, and that is the other half.** `direction.write` and
`POST /direction` already do the right four things for a direction somebody has
decided on: write it at the root, open a new sitting which ARCHIVES the lesson,
forget the last turn's note, and REPLACE the assistant. Two of those are
destructive. Doing them unattended to five workspaces because somebody drew on
five slides is the worst outcome available here, so what lands is ONE CARD per
marked workspace saying what it would change -- which is also where
`news.elsewhere` will tell them it landed. The person taps it.

Standard library only, like everything else.
"""

import json
import os
import shutil
import time

from . import atlas, briefs, sense
from .lesson import turns

# Where the picture of each marked slide is kept: beside the deck, ignored,
# so it goes to the trash with the deck it was drawn on.
MARKS = "marks"


def marks_dir(base):
    return os.path.join(briefs.deck_dir(base) or os.path.join(base, ".none"), MARKS)


def by_workspace(repo, rec):
    """`{workspace id: [(page, key)]}` for every marked slide of this deck.

    A mark on PAGE 1 belongs to nobody -- that is the title slide, and it is
    about the whole repository. It is left out here rather than attached to the
    first workspace in the deck, which is the kind of guess that sends a
    mentor's suggestion into a project they never mentioned.
    """
    from .server.routes import writing                 # local: avoids a cycle

    pages = (rec or {}).get("pages") or {}
    out = {}
    for key in briefs.ink_keys(repo):
        found = writing.ann_doc_page(key)
        if not found:
            continue
        ws = pages.get(str(found[1]))
        if not ws:
            continue
        out.setdefault(ws, []).append((found[1], key))
    for ws in out:
        out[ws].sort()
    return out


def _picture(repo, base, page, key):
    """The saved picture of one page's ink, copied beside the deck.

    Returns the repository-relative path, or "" when the viewer saved no
    picture -- which happens when the marks were autosaved by a build of the
    page that never finished drawing. The turn is told that rather than handed
    a path to nothing.
    """
    from .server.routes import writing                 # local: avoids a cycle

    src = writing.ann_path(repo, key, ".png")
    if not os.path.isfile(src):
        return ""
    where = marks_dir(base)
    try:
        os.makedirs(where, exist_ok=True)
        target = os.path.join(where, "p%d.png" % page)
        shutil.copyfile(src, target)
    except OSError:
        return ""
    return os.path.relpath(target, base).replace(os.sep, "/")


def _sent(repo, keys):
    """Record that these marks have gone somewhere, next to the marks.

    The same flag `/annotate/save` sets and the library sets, for the same
    reason: without it a reload cannot tell ink that was delivered from ink
    that was only autosaved, and yesterday's marks demand a decision every
    time anything is sent.
    """
    from .server.routes import writing                 # local: avoids a cycle

    for key in keys:
        path = writing.ann_path(repo, key)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                got = json.load(fh)
            got["sent"] = True
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(got, fh)
        except (OSError, ValueError):
            continue


def send(repo, base=None):
    """One proposal turn per marked workspace. The whole of the route's work.

    Returns `{ok, sent: [...], skipped: [...], detail}`. `sent` is one record
    per workspace that was woken; `skipped` is one per marked page that could
    not be routed, each saying why in a sentence -- a mark that goes nowhere
    with nothing said about it is a suggestion somebody believes was delivered.
    """
    base = base or atlas.root() or repo.root
    rec = briefs.deck(base)
    if not rec or not rec.get("has_pdf"):
        return {"ok": False, "sent": [], "skipped": [],
                "detail": "there is no deck to have marked up."}

    found = by_workspace(repo, rec)
    if not found:
        return {"ok": False, "sent": [], "skipped": [],
                "detail": ("Nothing is marked on a slide about a workspace. "
                           "The title slide is about all of them, so a mark "
                           "there has nowhere to go -- draw on the frame for "
                           "the project you mean.")}

    from .server import registry                       # local: avoids a cycle

    names = rec.get("names") or {}
    known = dict((w["id"], w["root"]) for w in atlas.workspaces(base))
    deck_rel = os.path.relpath(rec["pdf"], base).replace(os.sep, "/")

    sent, skipped = [], []
    for ws_id in sorted(found):
        root = known.get(ws_id)
        if not root:
            # The deck named a workspace that is not in the tree any more. Said
            # out loud rather than dropped: the mark is on the glass and the
            # person will believe it went.
            skipped.append({"workspace": ws_id,
                            "why": "%s is not a workspace in this repository "
                                   "any more, so its marks went nowhere."
                                   % ws_id})
            continue

        pages = [p for p, _ in found[ws_id]]
        keys = [k for _, k in found[ws_id]]
        images = []
        for page, key in found[ws_id]:
            shot = _picture(repo, base, page, key)
            if shot:
                images.append((page, shot))

        line = "[direction] " + sense.direction_mark_sense(
            deck_rel, pages, images, since=rec.get("since") or "")
        record = {
            "kind": "text", "answers": None,
            # THEIRS, because it is: they drew it. A transcript over there that
            # opens with the answer reads as an assistant that decided to
            # rethink the project on its own.
            "from": "student", "text": line,
            # NOT the `direction` signal. That one is read by the board as "the
            # lesson is being archived and the tutor replaced", and none of
            # that is happening here -- this turn writes one card and stops.
            "signal": None, "read": False,
        }
        # INTO THAT WORKSPACE'S SESSION, which `runner_route` picks; it wakes
        # its tutor too.
        try:
            got = registry.runner_route(ws_id, record, base=base, turn=True,
                                        ask="a direction from the meeting")
        except (LookupError, OSError) as exc:
            skipped.append({"workspace": ws_id,
                            "why": "nothing could be asked in %s: %s"
                                   % (ws_id, exc)})
            continue
        tid = got["id"]

        _sent(repo, keys)
        sent.append({"workspace": ws_id,
                     "name": names.get(ws_id) or ws_id,
                     "pages": pages, "turn": tid,
                     "images": [img for _, img in images]})

    if not sent:
        return {"ok": False, "sent": [], "skipped": skipped,
                "detail": "None of the marks could be routed."}

    return {"ok": True, "sent": sent, "skipped": skipped,
            "detail": ("%d workspace%s %s been asked to propose a new "
                       "direction. Nothing has been changed anywhere: each one "
                       "writes a card saying what it would do, and it is yours "
                       "to take or leave."
                       % (len(sent), "" if len(sent) == 1 else "s",
                          "has" if len(sent) == 1 else "have"))}


# Where the picture of a document page marked as a direction is kept, under the
# workspace's own `live/`. Not beside the document: `writeups/` is tracked and
# this repository is public, and the picture is of a slide whose figures are
# kept out of it on purpose. Not in `live/annotations/` either, where the
# direction ink and its picture are removed the moment the turn is written --
# and this picture must outlast that until the turn that reads it has run.
DIRECTIONS = "directions"


def from_document(repo, doc, page=0, words="", pictured=None):
    """This workspace's own document, marked as a DIRECTION.

    The library's directions mode. The same proposal the meeting deck makes --
    one `[direction]` turn in this workspace, one card, nothing applied until
    ⟳ rethink is tapped -- but routed by the reader's choice rather than by
    which frame the ink is on, because every page of a workspace's own
    document is about that workspace.

    DIRECTION INK ONLY: the strokes the reader drew with its toggle on
    *directions* (`dir: 1`). Fix ink on the same page is left for the next
    note. `page` names one page; without it, every page carrying direction
    ink goes. Once the turn is written those strokes and their picture come
    off the page (`library.strip_kind`), because the turn has its own copy of
    the picture under `live/directions/` -- so every direction stroke on disk
    is one not yet sent, and none ever rides a revision of the slides.

    ONLY A PAGE PICTURED FOR THIS SEND IS SENT. The strokes are coordinates
    and the turn reads the picture, so a page goes only when its `.dir.png`
    exists and, where `pictured` is given (`{key: direction strokes when the
    picture was taken}`, the reader's own list), it is in it with the count
    still on disk. Any other page (its image had not decoded, or its marks
    changed since) keeps its direction ink on disk, is named in the turn as
    having no picture, and comes back in `kept` for the reader to send again.
    Marks with no picture at all and no words are refused, and nothing is
    written. `pictured=None` trusts every picture on disk (callers in Python).
    Returns `{ok, turn, pages, kept, stripped, images, detail}`: `pages` sent,
    `kept` the pages left on disk, `stripped` the keys whose direction ink
    came off.
    """
    from .course import library                        # local: avoids a cycle
    from .server import spawn                          # local: avoids a cycle

    try:
        page = int(page or 0)
    except (TypeError, ValueError):
        page = 0
    words = (words or "").strip()
    marked = library.marks(repo, doc, kind="dir")
    chosen = [m for m in marked if m["page"] == page] if page else marked
    if not chosen and not (page and words):
        return {"ok": False,
                "error": ("there is nothing marked to send -- draw the "
                          "direction on a page, or say what it is")}
    pages = sorted(set(m["page"] for m in chosen)) or [page]

    from .server import registry                       # local: avoids a cycle
    # A sessionless Repo (the library page) has no session to keep the
    # pictures in: they go beside the subject's document ink.
    away = registry.is_sessionless(repo)
    stamp = time.strftime("%y%m%d-%H%M%S")
    where = (os.path.join(repo.doc_ink, DIRECTIONS) if away
             else os.path.join(os.path.dirname(repo.notes), DIRECTIONS))
    images = []
    going = []
    for m in chosen:
        if not m["png"]:
            continue
        if pictured is not None and pictured.get(m["key"]) != m["strokes"]:
            continue
        src = os.path.join(repo.root, *m["png"].split("/"))
        try:
            os.makedirs(where, exist_ok=True)
            target = os.path.join(where, "%s-p%d-%s.png"
                                  % (doc["id"], m["page"], stamp))
            shutil.copyfile(src, target)
        except OSError:
            continue
        going.append(m)
        images.append((m["page"],
                       os.path.relpath(target, repo.root).replace(os.sep, "/")))
    sent_keys = set(m["key"] for m in going)
    kept = sorted(set(m["page"] for m in chosen if m["key"] not in sent_keys))
    if chosen and not going and not words:
        return {"ok": False, "kept": kept,
                "error": ("no picture of the direction marks reached the board, "
                          "so nothing was sent -- send again")}

    line = "[direction] " + sense.doc_direction_sense(
        doc["rel"], pages, images, words, missing=kept)
    record = {
        "kind": "text", "answers": None, "t": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        # Theirs, and not the `direction` signal -- for the reasons `send`
        # gives: nothing is archived and nobody is replaced by this turn.
        "from": "student", "text": line, "signal": None, "read": False,
    }
    if away:
        # From outside any session: the subject's tutor, through the one
        # route there is to it, which picks the session and wakes it.
        try:
            tid = registry.runner_route(
                registry.subject_of(repo), record, base=registry.base_of(repo),
                turn=True, ask="a direction for %s" % doc.get("title"))["id"]
        except (LookupError, OSError) as exc:
            return {"ok": False, "error": "nothing could be asked: %s" % exc}
    else:
        tid = turns.next_turn_id(repo)
        record.update(id=tid, rev=turns.turn_revision(repo, tid))
        turns.write_turn(repo, record)
        try:
            with open(repo.messages_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError as exc:
            return {"ok": False, "error": "nothing could be asked: %s" % exc}

    stripped = []
    for m in going:
        library.strip_kind(repo, m["key"], "dir")
        stripped.append(m["key"])
    if not away:
        spawn.wake_tutor(repo)
    sent = sorted(set(m["page"] for m in going)) if chosen else pages
    said = ("page %d" % sent[0]) if len(sent) == 1 \
        else "pages " + ", ".join(str(p) for p in sent)
    detail = ("Your marks on %s went as a proposed direction. The tutor writes "
              "one card on this workspace's board saying what it would change; "
              "nothing changes until you tap ⟳ rethink there." % said) \
        if sent else "Your words went as a proposed direction."
    return {"ok": True, "turn": tid, "pages": sent, "kept": kept,
            "stripped": stripped, "images": [img for _, img in images],
            "detail": detail}
