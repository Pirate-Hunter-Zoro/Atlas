#!/usr/bin/env python3
"""The deck loop: a deck read in the library, inked, revised, and kept at End.

    python3 test/deck_loop.py

A temp Atlas holds one project shaped like `projects/libr-local-llm`: a beamer
deck placed in `docs/` with `docs/doc.json` beside it (asked by nobody), its
PDF tracked despite the root's PDF rule, and a `*.json` ignore with the
negations that keep a document's record and its feedback (the ledger,
`items.json` and `states.json`).

  * "Say what's wrong" from the library page routes a `[revise]` to the open
    session bound to the project, and puts that session on the deck's
    doc.json, once however many rounds; asked from inside a session, that
    session goes on it. An overhaul of the committed deck is a `[rework]`,
    refused once the source has changes nothing committed.
  * End of that session settles every round, then commits the revised
    .tex, the rebuilt tracked PDF, doc.json and every round's note, ledger
    and round directory, and leaves nothing of the deck modified. The
    round's caches (`checked.json`, `placed-*.json`) stay ignored. The
    owner's edits, drafts and rounds on other documents in that `docs/`
    stay out of the commit.
  * End settles a `docs/<slug>/` deck whose slug a walked document already
    holds as its library id (`DESIGN.md` beside a "Design" deck).
  * A revision, overhaul or write-up turn is handed the recap of the session
    it runs in, and its prompt sends it to `board see` for the ink and
    holds a deck to a build with no box warnings.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
sys.path.insert(0, BOARD_DIR)

fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n       " + str(detail)) if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if isinstance(text, bytes) else "w") as fh:
        fh.write(text)


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-deckloop-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-deckloop-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)

from tutorboard import artifacts, brief, sessions                   # noqa: E402
from tutorboard.course import library                               # noqa: E402
from tutorboard.lesson import inbox                                 # noqa: E402
from tutorboard.runner import prompts, turn                         # noqa: E402
from tutorboard.runner import service as runner_service             # noqa: E402
from tutorboard.server import registry                              # noqa: E402
from tutorboard.server.routes import library as library_route       # noqa: E402

runner_service.wake = lambda r: True


def git(*args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    env.pop("TUTORBOARD_TURN", None)
    return subprocess.run(["git"] + list(args), cwd=base, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


class _H(object):
    def __init__(self):
        self.hub = type("Hub", (), {"worker": type(
            "W", (), {"dirty": threading.Event()})()})()

    def note(self, _msg):
        pass


DECK = r"""\documentclass{beamer}
\title{A Private AI Assistant}
\begin{document}
\begin{frame}{Where it runs}One frame.\end{frame}
\end{document}
"""

# The root's rules for sessions and built PDFs, and the project's `*.json`
# with the negations a document's record and its feedback need.
ROOT_IGNORE = "/sessions/\n/projects/*/docs/**/*.pdf\n*.log\n*.aux\n"
LAB_IGNORE = ("*.json\n!/tutorboard.json\n!/docs/doc.json\n!/docs/*/doc.json\n"
              "!/docs/**/feedback/*.ledger.json\n"
              "!/docs/**/feedback/*/items.json\n"
              "!/docs/**/feedback/*/states.json\n")

try:
    lab = os.path.join(base, "projects", "Lab")
    docs = os.path.join(lab, "docs")
    write(os.path.join(base, ".gitignore"), ROOT_IGNORE)
    write(os.path.join(lab, ".gitignore"), LAB_IGNORE)
    write(os.path.join(lab, "tutorboard.json"),
          json.dumps({"name": "Lab", "phi": False}))
    write(os.path.join(lab, "TUTOR.md"), "# Where things are\n")
    write(os.path.join(docs, "doc.json"), json.dumps(
        {"title": "A Private AI Assistant", "source": "fleet.tex",
         "sessions": [], "asked_at": None}, indent=2) + "\n")
    write(os.path.join(docs, "fleet.tex"), DECK)
    write(os.path.join(docs, "fleet.pdf"), b"%PDF-1.4 first\n" + b"x" * 4000)
    write(os.path.join(docs, "egress.md"), "# Not the deck\n")
    git("init", "-q")
    git("add", "-A")
    git("add", "-f", "projects/Lab/docs/fleet.pdf")
    git("commit", "-q", "-m", "fixture")
    check("the fixture deck's PDF is tracked despite the root's PDF rule",
          "projects/Lab/docs/fleet.pdf" in git("ls-files").stdout)

    # ---- the lesson's session, and the library page ------------------------
    sid = registry.open_bound(base, "projects/Lab", "Colibri")
    page = registry.sessionless(lab, base)
    library.forget()
    doc = [d for d in library.documents(lab) if d["stem"] == "fleet"][0]
    check("a deck placed in docs/ with docs/doc.json is a library document "
          "with its record", doc.get("artifact") == "docs"
          and doc["source"] == "docs/fleet.tex", doc)
    check("an overhaul of it is allowed while its source is committed",
          library_route.rework_refused(page, doc) == "")

    # ---- round 1: an overhaul from the library page --------------------------
    note = library.write_note(page, doc["id"], "Say what Colibri is first.",
                              ask="rework",
                              purpose="a twenty-minute talk for the lab on "
                                      "Colibri and why it is safe with PHI",
                              hand_over=False)
    check("an overhaul's note is filed in docs/feedback/ under the deck's stem",
          note.get("ok") and note["rel"].startswith("docs/feedback/fleet-")
          and note.get("ledger", "").endswith(".ledger.json"), note)
    asked = library_route._revise(_H(), page, doc, note["rel"], ask="rework",
                                  purpose=note["purpose"],
                                  ledger_rel=note["ledger"], ids=note["ids"])
    check("from the library page it goes to the open session on the project",
          asked.get("asked") is True and asked.get("session") == sid, asked)
    rec = read_json(os.path.join(docs, "doc.json"))
    check("and that session is now on the deck's doc.json",
          rec.get("sessions") == [sid], rec)
    check("and nothing else in doc.json changed",
          rec.get("title") == "A Private AI Assistant"
          and rec.get("source") == "fleet.tex" and rec.get("asked_at") is None,
          rec)
    srepo = sessions.repo(sid, base)
    out, _taken = inbox.take(srepo)
    signal, _ = turn.woken_for(lab, out, srepo.messages_path)
    check("the session's inbox wakes a [rework] turn naming the source",
          signal == "rework" and "docs/fleet.tex" in out, out)

    # The turn: the deck rewritten and rebuilt, every request answered.
    write(os.path.join(docs, "fleet.tex"), DECK.replace("One frame.", "Colibri."))
    write(os.path.join(docs, "fleet.pdf"), b"%PDF-1.4 second\n" + b"y" * 4000)
    led = os.path.join(lab, *note["ledger"].split("/"))
    got = read_json(led)
    got["answers"] = {i: {"disposition": "done", "did": "said it first",
                          "new": "Colibri."} for i in note["ids"]}
    write(led, json.dumps(got))
    check("once the source has changes nothing committed, another overhaul is "
          "refused", "changes nothing has committed"
          in library_route.rework_refused(page, doc))

    # ---- round 2: a correction, asked twice --------------------------------
    for text in ("Frame 1 runs over.", "Name the egress block."):
        note2 = library.write_note(page, doc["id"], text, hand_over=False)
        library_route._revise(_H(), page, doc, note2["rel"],
                              ledger_rel=note2["ledger"], ids=note2["ids"])
    rec = read_json(os.path.join(docs, "doc.json"))
    check("a second and third round from the same session list it once",
          rec.get("sessions") == [sid], rec)
    out, _taken = inbox.take(srepo)
    check("and each is a [revise] for that session",
          out.count("[revise]") == 2, out)

    # ---- asked from inside another session ----------------------------------
    other = registry.open_bound(base, "projects/Lab", "Elsewhere")
    orepo = sessions.repo(other, base)
    note3 = library.write_note(orepo, doc["id"], "One more.", hand_over=False)
    asked = library_route._revise(_H(), orepo, doc, note3["rel"],
                                  ledger_rel=note3["ledger"], ids=note3["ids"])
    rec = read_json(os.path.join(docs, "doc.json"))
    check("asked from inside a session, that session goes on doc.json too",
          asked.get("asked") is True and rec.get("sessions") == [sid, other],
          rec)

    # ---- End ---------------------------------------------------------------
    # The owner's own work beside the deck in docs/: an edit to a tracked
    # document, an untracked draft, and a round of feedback on that document.
    write(os.path.join(docs, "egress.md"), "# Not the deck\n\nThe owner's edit.\n")
    write(os.path.join(docs, "draft-private.md"), "# Not for any commit\n")
    egress = [d for d in library.documents(lab) if d["stem"] == "egress"][0]
    note_e = library.write_note(page, egress["id"], "Not the deck's round.",
                                hand_over=False)
    check("a round on the other document in docs/ is filed under its stem",
          note_e.get("ok") and note_e["rel"].startswith("docs/feedback/egress-"),
          note_e)
    note_path = os.path.join(lab, *note["rel"].split("/"))
    check("the answered round has no account under its note before End",
          "## What was changed" not in open(note_path, encoding="utf-8").read())
    head = git("rev-parse", "HEAD").stdout.strip()
    rec, ok, said = sessions.end(sid, base=base)
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    check("End makes one commit", ok and git(
        "rev-list", "--count", "%s..HEAD" % head).stdout.strip() == "1", said)
    for want in ("projects/Lab/docs/fleet.tex", "projects/Lab/docs/fleet.pdf",
                 "projects/Lab/docs/doc.json",
                 "projects/Lab/" + note["rel"],
                 "projects/Lab/" + note["ledger"],
                 "projects/Lab/" + note2["ledger"]):
        check("End commits %s" % want, want in files, files)
    round_files = [f for f in files if f.startswith(
        "projects/Lab/" + note["rel"][:-3] + "/")]
    check("and the round's own directory, its requests with it",
          any(f.endswith("/items.json") for f in round_files), round_files)
    check("End settles the round first, so the account and the after-copy are "
          "in the commit rather than written after it",
          "## What was changed" in git("show", "HEAD:projects/Lab/"
                                       + note["rel"]).stdout
          and any(f.endswith("/after.tex") for f in round_files), round_files)
    check("while the round's caches stay out of git",
          not any(f.endswith("/checked.json") for f in round_files)
          and os.path.isfile(os.path.join(note_path[:-3], "checked.json")),
          round_files)
    left = git("status", "--porcelain", "--", "projects/Lab/docs").stdout
    theirs = ("projects/Lab/docs/egress.md", "projects/Lab/docs/draft-private.md",
              "projects/Lab/docs/feedback/egress-")
    deck_left = [l for l in left.splitlines()
                 if not any(t in l for t in theirs)]
    check("nothing of the deck under docs/ is left modified or untracked after "
          "End, the rebuilt PDF included", deck_left == [], left)
    check("End commits only the deck's own files from the docs/ it shares: "
          "not the owner's edit to another document, nor an untracked draft, "
          "nor that document's round",
          not any(f.startswith(t) for f in files for t in theirs), files)
    check("and those stay as the owner left them",
          " M projects/Lab/docs/egress.md" in left
          and "?? projects/Lab/docs/draft-private.md" in left, left)

    # ---- End settles a docs/<slug>/ deck whose slug a walked document took --
    write(os.path.join(lab, "DESIGN.md"), "# Design\n\nHow the lab is laid out.\n")
    git("add", "-A", "projects/Lab/DESIGN.md")
    git("commit", "-q", "-m", "design")
    sid3 = registry.open_bound(base, "projects/Lab", "Design talk")
    made = artifacts.create(lab, "Design", session=sid3, ext=".tex", base=base)
    design = made["dir"]
    write(os.path.join(design, "design.tex"), DECK)
    write(os.path.join(design, "design.pdf"), b"%PDF-1.4 first\n" + b"z" * 4000)
    library.forget()
    listed = library.documents(lab)
    deck3 = [d for d in listed if d.get("artifact") == "docs/design"]
    walked = [d for d in listed if d["stem"] == "DESIGN"]
    check("a 'Design' deck beside a root DESIGN.md: the walked file has the "
          "slug as its id, so the deck has another",
          made["id"] == "design" and deck3 and walked
          and walked[0]["id"] == "design" and deck3[0]["id"] != "design",
          [(d["id"], d.get("artifact"), d["stem"]) for d in listed])
    deck3 = deck3[0]
    note4 = library.write_note(page, deck3["id"], "Frame 1 is too dense.",
                               hand_over=False)
    write(os.path.join(design, "design.tex"), DECK.replace("One frame.", "Less."))
    write(os.path.join(design, "design.pdf"), b"%PDF-1.4 second\n" + b"w" * 4000)
    led4 = os.path.join(lab, *note4["ledger"].split("/"))
    got = read_json(led4)
    got["answers"] = {i: {"disposition": "done", "did": "cut it",
                          "new": "Less."} for i in note4["ids"]}
    write(led4, json.dumps(got))
    rec, ok, said = sessions.end(sid3, base=base)
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    check("End settles that deck's round, not the walked document's: its "
          "account and after-copy are in the commit",
          ok and "## What was changed" in git(
              "show", "HEAD:projects/Lab/" + note4["rel"]).stdout
          and any(f.startswith("projects/Lab/" + note4["rel"][:-3] + "/")
                  and f.endswith("/after.tex") for f in files), (said, files))
    library.forget()
    library.status(page)
    left = git("status", "--porcelain", "--", "projects/Lab/docs/design",
               "projects/Lab/DESIGN.md").stdout
    check("and the next library read leaves nothing of it to commit",
          left.strip() == "", left)

    # ---- what the turn is handed --------------------------------------------
    for sig in ("revise", "rework", "writeup"):
        check("a %s turn is handed the recap and not the brief" % sig,
              turn.context_plan(sig) == (False, True))
    check("a lesson turn still gets both", turn.context_plan("") == (True, True))
    write(os.path.join(srepo.cards, "0001-colibri.md"),
          "---\nkind: lesson\ntitle: Where Colibri runs\n---\nOn a GPU node.\n")
    handed = brief.turn_context(srepo, "revise", brief=False)
    check("the recap it is handed is that session's lesson",
          "THE RECAP" in handed and "THE BRIEF" not in handed
          and "Where Colibri runs" in handed, handed[:600])
    for name, said in (("a revision", prompts.HEADLESS_REVISE_PROMPT),
                       ("an overhaul", prompts.HEADLESS_REWORK_PROMPT)):
        check("%s is told to run `board see` on the ink" % name,
              "`board see <path>`" in said and "every image" in said)
        check("and that the recap above is the session it was asked from",
              "recap above" in said)
    for name, said in (("a revision", prompts.HEADLESS_REVISE_PROMPT),
                       ("an overhaul", prompts.HEADLESS_REWORK_PROMPT),
                       ("a write-up", prompts.HEADLESS_WRITEUP_PROMPT)):
        check("%s holds a deck to a build with no box warnings" % name,
              "Overfull or Underfull box" in said
              and "Fix every one" in said)
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("a deck is inked, revised and kept, and each turn knows the lesson")
