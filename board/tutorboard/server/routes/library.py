"""The library: every document this workspace has written, and feedback on one.

A surface, not a sitting: nothing here writes cards or session state, so a
correction to a deck never interrupts somebody mid-proof. A note lands beside
its document and wakes a turn that is not the lesson's.

    GET  /library.json              everything `course/library.py` found
    GET  /library/results.json      everything this workspace PRODUCED, grouped
                                    by the directory it came out of -- or a
                                    sentence saying why there is nothing
    GET  /library/table/<id>        one table, read back as rows or as text,
                                    because a page cannot open a file
    POST /artifact                  a deck or a paper `{make, about?}`, from the
                                    session's Make menu or a subject's row on
                                    the start screen: the doc.json first, then
                                    a `[writeup]` turn that writes and builds it
    POST /writeup/seen              one finished ask waved off the board's strip
    GET  /library/stamp             one hash of where every document is and
                                    when it last changed, cheap enough to ask
                                    every few seconds
    GET  /library/view/<id>         the pages of one, drawn by the renderer the
                                    board already has
    GET  /library/marked/<id>/<name> a marked copy `POST /annotate/burn` kept
                                    beside one's PDF, as an attachment
    GET  /library/note/<id>/<name>  one round of feedback, read back -- which is
                                    where the turn wrote what it changed
    GET  /library/ledger/<id>       every round's requests, what was done about
                                    each, and where each sits on the pages now
    GET  /library/evidence/<id>/<note>/<file>
                                    one crop or page picture a request keeps
    POST /library/ledger/preview    how the panel's words and ink would split
                                    into requests, before anything is sent
    POST /library/ledger/state      one request accepted, or reopened with why
    POST /library/feedback          one round of feedback, written where the
                                    document is, and then acted on -- in words,
                                    in ink, or in both
    POST /doc/delete                one artifact `{subject, id}`, after a
                                    second tap: to the trash with its ink, and
                                    its tracked files out in one commit
    GET  /materials.json            the files under the subject's materials/
    POST /material/delete           one material `{subject, name}`, after a
                                    second tap: to the trash with its ink

Subject routes are served under `/s/<id>/` for the session's own subject, or
unprefixed with `?subject=<id>` from the library page (`handler.UNPREFIXED`);
/writeup/seen is session-only. An ask for another subject's tutor goes
through `registry.runner_route`, which picks the session.

The constraint: an id, never a path. Ids are matched against discovery
(`library.find`), note names against `library.notes`, and `/artifact` takes
no path at all. Feedback is never just filed: writing a note dispatches a
`[revise]` turn in the same request. `rework` (an overhaul) needs a purpose
sentence and a committed source, because git is its only undo.
"""

import json
import os
import re
import time
from urllib.parse import unquote

from . import NOT_MINE
from . import writing
from .. import registry
from ...runner import service as runner
from ... import (artifacts, briefs, fenced, leaving, paths, sense, subjects,
                 writeups)
from ...course import burn
from ...course import ledger
from ...course import library
from ...lesson import turns


def get(h, repo, path):
    if path == "/library.json":
        return h.send_json(with_deck(library.status(repo), repo))

    if path == "/materials.json":
        found = subjects.find(repo.root, registry.base_of(repo))
        if not found:
            return h.send_json({"ok": False, "error": "this session is bound to "
                                "no subject, so it has no materials"}, status=404)
        # A library PDF carries its id `doc` for the drawer's reader.
        ids = library.ident_map(found["root"])
        listed = subjects.materials(found["root"])
        for m in listed:
            ident = ids.get(os.path.realpath(os.path.join(
                found["root"], subjects.MATERIALS, *m["name"].split("/"))))
            if ident and m["name"].lower().endswith(".pdf"):
                m["doc"] = ident
        return h.send_json({"ok": True, "subject": found["id"],
                            "materials": listed})

    # Stats only: polled every few seconds; `/library.json` is the expensive
    # answer, fetched when this changes.
    if path == "/library/stamp":
        try:
            return h.send_json(library.stamp(repo.root))
        except Exception as exc:                             # noqa: BLE001
            # A 500 would paint "the board is not answering" over a walk fault.
            return h.send_json({"ok": False, "error": str(exc)})

    # Its own fetch: a different tree and walk from `/library.json`.
    if path == "/library/results.json":
        try:
            return h.send_json(library.browse_results(repo))
        except Exception as exc:                             # noqa: BLE001
            # As for `/library/stamp`.
            return h.send_json({"ok": False, "error": str(exc)})

    # One table read back as rows, because a downloaded CSV is lost on an iPad.
    # An id, never a path (`library.result_table`).
    if path.startswith("/library/table/"):
        got = library.result_table(repo.root, unquote(path[len("/library/table/"):]))
        return h.send_json(got, status=200 if got.get("ok") else 404)

    # A marked copy as an attachment for Files; id and name matched on disk
    # (`burn.marked_file`).
    if path.startswith("/library/marked/"):
        rest = path[len("/library/marked/"):].split("/", 1)
        found = burn.marked_file(repo, rest[0] if rest else "",
                                 unquote(rest[1]) if len(rest) > 1 else "")
        if not found:
            return h.send_json({"ok": False, "error": "no such copy"},
                               status=404)
        return h.send_file(found, download=os.path.basename(found))

    if path.startswith("/library/view/"):
        # The lesson's own rasteriser, cache and page addresses.
        return h.send_json(library.pages(repo, path[len("/library/view/"):]))

    # One round's text, including the turn's `## What was changed`.
    if path.startswith("/library/note/"):
        rest = path[len("/library/note/"):].split("/", 1)
        doc = library.find(repo.root, rest[0] if rest else "")
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        got = library.note_text(repo.root, doc,
                                unquote(rest[1]) if len(rest) > 1 else "")
        return h.send_json(got, status=200 if got.get("ok") else 404)

    # Each request, its answer, and its place on the build on disk.
    if path.startswith("/library/ledger/"):
        # Either name: the board's document drawer asks by its own (`find_any`).
        doc = library.find_any(repo.root, unquote(path[len("/library/ledger/"):]))
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        try:
            return h.send_json(ledger.view(repo, doc))
        except Exception as exc:                             # noqa: BLE001
            return h.send_json({"ok": False, "error": str(exc)[-300:]})

    # A request's picture: id, round and file name matched on disk
    # (`ledger.evidence`), never joined.
    if path.startswith("/library/evidence/"):
        rest = path[len("/library/evidence/"):].split("/")
        doc = library.find(repo.root, rest[0]) if len(rest) == 3 else None
        found = (ledger.evidence(repo.root, doc, unquote(rest[1]), unquote(rest[2]))
                 if doc else "")
        if not found:
            return h.send_json({"ok": False, "error": "no such picture"},
                               status=404)
        return h.send_file(found)

    return NOT_MINE


def post(h, repo, path):
    if path == "/library/feedback":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        ident = str(payload.get("document") or "").strip()
        text = payload.get("text") or ""
        ask = library.clean_ask(payload.get("ask"))
        purpose = payload.get("purpose") or ""
        try:
            page = int(payload.get("page") or 0)
        except (TypeError, ValueError):
            page = 0
        merge = _pages(payload.get("merge"))
        doc = library.find(repo.root, ident)
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        # A piece is corrected through its whole, by that document's machinery.
        whole = (library.find(repo.root, doc.get("whole") or "")
                 if doc.get("piece") else None)
        if doc.get("piece") and ask == "rework":
            return h.send_json({"ok": False, "ask": "rework", "error": (
                "%s is one section of %s, cut from it, so an overhaul of it "
                "alone is lost on the next cut. Overhaul the whole document "
                "instead. Nothing has been written."
                % (doc["title"], (whole or {}).get("title") or "a larger document"))},
                status=409)
        if ask == "rework":
            stop = rework_refused(repo, doc)
            if stop:
                # Nothing is written when this refuses: an unstarted overhaul's
                # note would read as in force.
                return h.send_json({"ok": False, "ask": "rework",
                                    "error": stop}, status=409)
        rec = library.write_note(repo, ident, text, page=page, ask=ask,
                                 purpose=purpose, hand_over=False, merge=merge)
        if not rec.get("ok"):
            return h.send_json(rec, status=400)
        keys = rec.pop("keys", [])
        carry = rec.pop("carry", [])
        rec.update(_revise(h, repo, whole or doc, rec["rel"], ask=ask,
                           purpose=rec.get("purpose") or "",
                           ledger_rel=rec.get("ledger") or "",
                           ids=rec.get("ids") or []))
        # Ink (and reopened requests) count as delivered only once the
        # revision was asked, so a failed ask leaves them for the retry.
        if rec.get("asked"):
            library.hand_over(repo, keys)
            ledger.carry(repo.root, doc, carry, rec.get("note") or "")
        elif rec.get("path"):
            # Nothing answers this round: it counts nowhere, and the retry
            # files the same ink and requests again.
            ledger.mark_unsent(rec["path"], rec.get("detail") or "")
        return h.send_json(rec)

    # How words and ink would split into requests, before sending. Writes
    # nothing.
    if path == "/library/ledger/preview":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        doc = library.find(repo.root, str(payload.get("document") or "").strip())
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        try:
            page = int(payload.get("page") or 0)
        except (TypeError, ValueError):
            page = 0
        found = library.carried(repo, doc, library.marks(repo, doc))
        items = ledger.preview(repo, found, payload.get("text") or "", page=page,
                               merge=_pages(payload.get("merge")),
                               round_no=ledger.next_round(repo.root, doc),
                               reopen=ledger.reopened(repo.root, doc))
        return h.send_json({"ok": True, "items": items})

    # A reopened request costs a line of why and rides the next round under
    # its id.
    if path == "/library/ledger/state":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        doc = library.find(repo.root, str(payload.get("document") or "").strip())
        if not doc:
            return h.send_json({"ok": False, "error": "no such document"},
                               status=404)
        got = ledger.set_state(repo.root, doc, str(payload.get("note") or ""),
                               str(payload.get("id") or ""),
                               payload.get("state"), payload.get("why") or "")
        library.forget()
        return h.send_json(got, status=200 if got.get("ok") else 400)

    if path == "/artifact":
        return _artifact(h, repo)

    if path == "/material/delete":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        if not isinstance(payload, dict):
            payload = {}
        got, code = delete_material(repo, str(payload.get("subject") or "").strip(),
                                    str(payload.get("name") or ""))
        if got.get("ok"):
            h.hub.worker.dirty.set()
        return h.send_json(got, status=code)

    if path == "/doc/delete":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        if not isinstance(payload, dict):
            payload = {}
        got, code = delete_doc(repo, str(payload.get("subject") or "").strip(),
                               str(payload.get("id") or "").strip().lower())
        if got.get("ok"):
            h.hub.worker.dirty.set()
        return h.send_json(got, status=code)

    if path == "/writeup/seen":
        try:
            payload = json.loads(h.read_body().decode("utf-8") or "{}")
        except Exception:
            return h.send_json({"ok": False, "error": "bad json"}, status=400)
        # A `writing` ask cannot be waved away (`writeups.seen` refuses it).
        got = writeups.seen(repo, str(payload.get("id") or ""))
        h.hub.worker.dirty.set()
        return h.send_json({"ok": bool(got)})

    return NOT_MINE


# What the Make menu sends, and what each is called in a record.
MAKES = {"deck": "slides", "paper": "paper"}


def _artifact(h, repo):
    """`POST /artifact {make: "deck"|"paper", about?}`: a deck or a paper.

    Changes no mode and writes no card. The server writes
    `<subject>/docs/<slug>/doc.json` first, choosing slug and path, then
    queues a `[writeup]` turn naming that source and `board build`. Under
    `/s/<id>/` the scope is the session's own (an unbound session is
    refused); unprefixed, `?subject=<id>` picks via `registry.runner_route`
    and `about` is required.
    """
    try:
        payload = json.loads(h.read_body().decode("utf-8") or "{}")
    except Exception:
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    if not isinstance(payload, dict):
        return h.send_json({"ok": False, "error": "bad json"}, status=400)
    make = str(payload.get("make") or "").strip().lower()
    if make not in MAKES:
        return h.send_json({"ok": False, "error": "make is deck or paper"},
                           status=400)
    about = str(payload.get("about") or "").strip()[:writeups.ABOUT_CHARS]
    if getattr(repo, "stored", False) and not (repo.state() or {}).get("subject"):
        # An unbound session's root is the Atlas root: nothing to put it in.
        return h.send_json({"ok": False, "error": "this session is not bound to a "
                            "course or project: bind it first"}, status=409)
    sessionless = registry.is_sessionless(repo)
    if sessionless and not about:
        return h.send_json({"ok": False, "error": "say what it is about"},
                           status=400)
    got = _dispatch_writeup(h, repo, None, MAKES[make], about)
    if not isinstance(got, dict):
        return got
    art = got.get("artifact") or {}
    return h.send_json({"ok": True, "id": got["id"], "make": make,
                        "about": about, "state": "writing",
                        "doc": art.get("id") or "", "source": art.get("source") or "",
                        "session": got.get("session"),
                        "subject": art.get("subject") or ""})


def _dispatch_writeup(h, repo, match, makes, about, line=None, prepare=None,
                      ask=None):
    """Ask for a document in the workspace `match` names (or this one), and
    return `{id, rec, root}` or the refusal already sent. `prepare(target,
    id)` runs once the ask is allowed and before it is recorded (the meeting
    deck writes its brief there); a dict it returns may name `doc_dir`.
    """
    got, err = dispatch(repo, match, makes, about, line=line, prepare=prepare,
                        ask=ask)
    if err:
        return h.send_json(err[0], status=err[1])
    if got.get("woke"):
        h.note("nothing was reading the board; starting a tutor to write it")
    h.hub.worker.dirty.set()
    return got


class _Refusal(Exception):
    """A write-up refused once its target was known: `(payload, status)`."""

    def __init__(self, payload, status):
        Exception.__init__(self, payload.get("error") or "")
        self.payload, self.status = payload, status


def dispatch(repo, match, makes, about, line=None, prepare=None, ask=None):
    """`_dispatch_writeup` without a request: `({id, rec, root, woke}, None)`
    or `(None, (payload, status))`. The CLI and the front door share it.

    Only an ask for the session's own subject goes to its own tutor; others
    go through `registry.runner_route`. Nothing is written until the target
    is known, so a refusal leaves nothing behind.
    """
    made = {}

    def ready(target, wid):
        """Make what the ask needs in `target`, and return the inbox text."""
        doc_dir, text = None, line
        if line is None and prepare is None:
            # A plain ask makes its artifact first, so the turn is told the
            # exact file, from the Atlas root.
            try:
                art = artifacts.create(
                    target.root,
                    about[:80] or ("Slides" if makes == "slides" else "Paper"),
                    session=target.live if target.stored else None,
                    ext=".tex" if makes == "slides" else ".md")
            except (ValueError, OSError) as exc:
                raise _Refusal({"ok": False, "error": "no document could be made "
                                "here: %s" % exc}, 409)
            doc_dir = art["rel"]
            top = os.path.realpath(target.atlas or registry.base_of(repo))

            def rel(p):
                # From the Atlas root; a workspace outside it is named whole.
                p = os.path.realpath(p)
                said = os.path.relpath(p, top)
                return p if said.startswith("..") else said.replace(os.sep, "/")
            src = rel(art["path"])
            made["artifact"] = {"id": art["id"], "source": src,
                                "subject": rel(target.root)}
            text = "[writeup] " + sense.writeup_sense(makes, about, source=src)
        if prepare:
            try:
                got = prepare(target, wid)
            except Exception as exc:                         # noqa: BLE001
                raise _Refusal({"ok": False,
                                "error": "nothing could be prepared: %s" % exc}, 500)
            if isinstance(got, dict) and got.get("doc_dir"):
                doc_dir = got["doc_dir"]
        made["rec"] = writeups.ask(target, wid, makes, about,
                                   agent="",
                                   doc_dir=doc_dir,
                                   session=(os.path.basename(target.live)
                                            if target.stored else None))
        return {"text": text or ("[writeup] " + sense.writeup_sense(makes, about))}

    record = {"rev": 0, "kind": "text", "answers": None, "from": "student",
              "signal": "writeup", "read": False}
    if match or registry.is_sessionless(repo):
        subject = match["id"] if match else registry.subject_of(repo)
        try:
            got = registry.runner_route(
                subject, record, base=registry.base_of(repo), before=ready,
                ask=ask or ("a deck" if makes == "slides" else "a paper"))
        except LookupError:
            return None, ({"ok": False, "error": "no such subject"}, 404)
        except _Refusal as no:
            return None, (no.payload, no.status)
        except OSError as exc:
            return None, ({"ok": False,
                           "error": "nothing could be asked: %s" % exc}, 500)
        return {"id": got["id"], "rec": made["rec"], "root": got["repo"].root,
                "session": got["session"], "woke": False,
                "artifact": made.get("artifact")}, None

    # An id from the lesson's turn series; not written into `turns.jsonl`.
    wid = turns.next_turn_id(repo)
    try:
        record.update(ready(repo, wid))
    except _Refusal as no:
        return None, (no.payload, no.status)
    record.update(id=wid, t=time.time(), iso=time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        with open(repo.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        return None, ({"ok": False,
                       "error": "nothing could be asked: %s" % exc}, 500)
    # Queued on the runner, the same as `/say` and `_revise`.
    woke = bool(runner.wake(repo))
    return {"id": wid, "rec": made["rec"], "root": repo.root, "woke": woke,
            "session": os.path.basename(repo.live) if repo.stored else None,
            "artifact": made.get("artifact")}, None


SUBJECT_ID = re.compile(r"\A(?:courses|projects|research|practice)/[A-Za-z0-9._-]+\Z")


def delete_doc(repo, subject, ident):
    """`POST /doc/delete`: `(payload, status)`. An id and a subject id, never
    a path: the subject is this board's or matches `subjects.find`, the
    document matches the library. A fenced name is 403 before any lookup.
    """
    served = (subjects.find(repo.root) or {}).get("id") or ""
    if fenced.refused(subject) or fenced.refused("%s/%s" % (artifacts.DOCS, ident)):
        return {"ok": False, "error": "that is under a fence"}, 403
    if not subject or subject == served:
        root = repo.root
    elif SUBJECT_ID.match(subject):
        found = subjects.find(subject)
        if not found or found["id"] != subject:
            return {"ok": False, "error": "no such subject"}, 404
        root = found["root"]
    else:
        return {"ok": False, "error": "no such subject"}, 404
    if not ident or not writing.ANN_DOC.match("doc/%s/p1" % ident):
        return {"ok": False, "error": "no such document"}, 404
    library.forget()
    doc = library.find(root, ident)
    if not doc or not doc.get("artifact"):
        return {"ok": False, "error": (
            "no such document" if not doc else
            "%s has no doc.json, so it is not the board's to delete"
            % doc["title"])}, 404
    if fenced.refused(doc["artifact"]):
        return {"ok": False, "error": "that is under a fence"}, 403
    from ... import sessions                        # local: a cycle through artifacts
    ink = [os.path.join(root, sessions.INK)]
    if paths.same_dir(root, repo.root):
        ink.append(repo.notes)
    got = artifacts.delete(root, os.path.join(root, *doc["artifact"].split("/")),
                           idents=library.mark_idents(root, doc), ink_dirs=ink)
    library.forget()
    if got.get("fenced"):
        return {"ok": False, "error": got["said"]}, 403
    got.pop("trash", None)
    return dict(got, id=doc["id"], title=doc["title"]), (200 if got["ok"] else 500)


def delete_material(repo, subject, name):
    """`POST /material/delete`: `(payload, status)`. A subject id and a name
    `subjects.materials` listed; fenced names 403 first. File and ink go to
    the trash; an ignored file makes no commit.
    """
    served = subjects.find(repo.root, registry.base_of(repo))
    if fenced.refused(subject) or fenced.refused(name):
        return {"ok": False, "error": "that is under a fence"}, 403
    if not subject or (served and subject == served["id"]):
        found = served
    elif SUBJECT_ID.match(subject):
        found = subjects.find(subject, registry.base_of(repo))
        if found and found["id"] != subject:
            found = None
    else:
        found = None
    if not found:
        return {"ok": False, "error": "no such subject"}, 404
    library.forget()
    rel = "%s/%s" % (subjects.MATERIALS, name)
    doc = next((d for d in library.documents(found["root"])
                if d.get("group") == "material" and d.get("rel") == rel), None)
    idents = library.mark_idents(found["root"], doc) if doc else []
    try:
        _where, said = subjects.delete_material(found["root"], name, idents)
    except subjects.Refused as exc:
        status = 404 if str(exc).startswith("no material") else 500
        return {"ok": False, "error": str(exc)}, status
    library.forget()
    return {"ok": True, "subject": found["id"], "name": name, "said": said}, 200


def _pages(got):
    """Page numbers off a request, or []. Anything that is not one is dropped."""
    if not isinstance(got, list):
        return []
    out = []
    for x in got[:200]:
        try:
            n = int(x)
        except (TypeError, ValueError):
            continue
        if n > 0:
            out.append(n)
    return out


def _strings(payload, key):
    """A list of strings off a request, or []. Nothing else from it is read."""
    got = payload.get(key)
    if not isinstance(got, list):
        return []
    return [str(x) for x in got if isinstance(x, (str, int))][:500]


def ask_meeting(repo, base, since_ts, human, want=None):
    """Ask for the meeting deck: `({id, host, where, dir, record}, None)` or
    `(None, (payload, status))`. The brief is `briefs.blocks_for` the period
    and subjects; `briefs.replace` runs in `prepare`, so a refusal leaves the
    last deck standing.
    """
    blocks, every, why = briefs.blocks_for(base, want, since_ts)
    if why:
        return None, ({"ok": False, "detail": why}, 400)
    if not blocks:
        return None, ({"ok": False, "detail": (
            "Nothing landed in %s in %s, so there is nothing to present. "
            "Choose a longer period." % (human, ", ".join(
                s["id"] for s in every) or "any subject"))}, 400)
    if not briefs.meetings_root(base):
        return None, ({"ok": False, "detail": (
            "%s is missing; `board bind %s --create --phi yes` makes it"
            % (briefs.MEETINGS, briefs.MEETINGS))}, 409)
    period = briefs.period_text(since_ts)
    rel = briefs.deck_rel()
    about = ("the meeting deck for %s, briefed in %s/%s"
             % (period, rel, briefs.BRIEF_MD))[:writeups.ABOUT_CHARS]
    line = "[writeup] " + sense.writeup_sense("slides", sense.meeting_about(
        rel, period, "%s/%s" % (briefs.MEETINGS, rel)))
    made = {}

    def prepare(target, wid):
        made["rec"] = briefs.replace(
            base, blocks, since_ts, human,
            session=os.path.basename(target.live) if target.stored else None,
            ink=briefs.ink_dirs(base, repo))
        return made["rec"]

    got, err = dispatch(repo, {"id": briefs.MEETINGS}, "slides", about, line=line,
                        prepare=prepare, ask="the meeting deck")
    if err:
        payload = dict(err[0])
        payload.setdefault("detail", payload.get("error") or "")
        return None, (payload, err[1])
    brief = made.get("rec", {}).get("brief") or {}
    return {"id": got["id"], "host": briefs.MEETINGS, "where": "Meetings",
            "dir": "%s/%s" % (briefs.MEETINGS, rel), "record": brief,
            "woke": got.get("woke"), "session": got.get("session")}, None


def meeting_deck(h, repo, base, since_ts, human, want=None):
    """`POST /meeting`: the meeting deck asked for, and the sheet told it is
    being written. The sheet then watches the Meetings library (`with_deck`)."""
    got, err = ask_meeting(repo, base, since_ts, human, want=want)
    if err:
        return h.send_json(err[0], status=err[1])
    h.hub.worker.dirty.set()
    rec = got["record"]
    return h.send_json({
        "ok": True, "id": got["id"], "name": "meeting", "state": "being written",
        "host": got["host"], "where": got["where"], "dir": got["dir"],
        "session": got.get("session"),
        "workspaces": rec.get("subjects") or [],
        "names": rec.get("names") or {}, "since": human,
        "period": rec.get("period") or "",
        "detail": ("The assistant is writing it in Meetings. It takes several "
                   "minutes, and this sheet says when it is ready. It replaces "
                   "the deck before it.")})


def with_deck(payload, repo):
    """The Meetings library's payload with the meeting deck's record on its
    row as `meeting` (`briefs.deck`); other subjects pass through."""
    if registry.subject_of(repo) != briefs.MEETINGS:
        return payload
    try:
        rec = briefs.deck(registry.base_of(repo) or subjects.root())
    except Exception:                                        # noqa: BLE001
        rec = None
    rel = briefs.deck_rel()
    for doc in payload.get("documents") or []:
        if doc.get("artifact") == rel:
            doc["meeting"] = rec
    payload["meeting"] = rec
    return payload


def rework_refused(repo, doc):
    """Why this document may not be overhauled from here, or "".

    The source must be committed, because git is an overhaul's only undo. The
    board refuses rather than commit on somebody's behalf: a half-finished
    edit is a worse undo than none.
    """
    src = doc.get("source") or ""
    if not src:
        return ("%s has no source in this repository -- there is only a built "
                "file -- so there is nothing to rework."
                % doc["title"])
    if leaving.uncommitted(repo.root, src):
        # Name the board's save tap, not `git commit`: the laptop stays shut.
        return ("`%s` has changes nothing has committed, and an overhaul "
                "replaces the whole document: git is the only undo it has. Tap "
                "⤓ save on the board to commit it as it stands, then ask again "
                "-- the overhaul is one diff after that. Nothing has been "
                "written." % src)
    return ""


def _revise(h, repo, doc, note_rel, ask="revise", purpose="", ledger_rel="",
            ids=()):
    """Ask for the revision: a `[revise]` (or `[rework]`) line and a turn woken
    on it. The turn runs fresh and writes no card (`HEADLESS_REVISE_PROMPT`).
    The line names the source and, for a deck, its brief; `ledger_rel` and
    `ids` are the requests to answer. `ask` sets the signal, prompt and clock
    (`turn_plan`, `doing_now`).
    """
    brief = ""
    if library.from_sittings(repo.root, doc):
        brief = "%s/%s" % (doc["dir"], library.DECK_BRIEF)
    if ask == "rework":
        line = "[rework] " + sense.rework_sense(doc.get("source") or doc["rel"],
                                                note_rel, purpose, brief=brief,
                                                ledger=ledger_rel, ids=ids,
                                                source=doc.get("source") or "")
    else:
        line = "[revise] " + sense.revise_sense(doc["rel"], note_rel,
                                                brief=brief, ledger=ledger_rel,
                                                ids=ids,
                                                source=doc.get("source") or "")
    record = {
        "rev": 0, "kind": "text", "answers": None,
        "t": time.time(),
        "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "student", "text": line, "signal": ask, "read": False,
    }
    if registry.is_sessionless(repo):
        # From the library page: `runner_route` picks the session.
        try:
            got = registry.runner_route(registry.subject_of(repo), record,
                                        base=registry.base_of(repo),
                                        ask="%s %s" % (ask, doc.get("title") or ""))
        except (LookupError, OSError) as exc:
            return {"revise": "board", "asked": False,
                    "detail": "the note is written but nothing could be asked: %s"
                              % exc}
        h.hub.worker.dirty.set()
        return {"revise": "board", "asked": True, "session": got["session"],
                "detail": ("The tutor has been asked to %s it, in the newest "
                           "session on this subject." % ask)}
    # An id from the lesson's turn series; not written into `turns.jsonl`,
    # which is the lesson's.
    record["id"] = turns.next_turn_id(repo)
    try:
        with open(repo.messages_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        return {"revise": "board", "asked": False,
                "detail": "the note is written but nothing could be asked: %s" % exc}
    runner.wake(repo)
    h.hub.worker.dirty.set()
    return {"revise": "board", "asked": True,
            "detail": ("The tutor has been asked to rework it, and an overhaul "
                       "takes longer than a correction. That turn is not part "
                       "of the lesson: it writes no card and leaves the sitting "
                       "on the board alone."
                       if ask == "rework" else
                       "The tutor has been asked to revise it. That turn is not "
                       "part of the lesson: it writes no card and leaves the "
                       "sitting on the board alone.")}
