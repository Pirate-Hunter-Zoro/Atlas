#!/usr/bin/env python3
"""The deck loop: a deck read in the library, inked, revised, and kept at End,
which leaves the round on disk and out of the commit.

    python3 test/deck_loop.py

A temp Atlas holds one project shaped like `projects/libr-local-llm`: a beamer
deck placed in `docs/` with `docs/doc.json` beside it (asked by nobody), its
PDF tracked despite the root's PDF rule, a `*.json` ignore with the negations
that keep a document's record, and the real root .gitignore's feedback rule,
which keeps every round on disk and out of git.

  * "Say what's wrong" from the library page routes a `[revise]` to the open
    session bound to the project, and puts that session on the deck's
    doc.json, once however many rounds; asked from inside a session, that
    session goes on it. An overhaul of the committed deck is a `[rework]`,
    refused once the source has changes nothing committed.
  * End of that session settles every round on disk, then commits the
    revised .tex, the rebuilt tracked PDF, doc.json and TUTOR.md, and
    leaves nothing of the deck modified. Every round -- note, ledger, round
    directory -- stays on disk and out of the commit. The owner's edits,
    drafts and rounds on other documents in that `docs/` stay out too. What the overhaul pulls into the deck beside it
    (an image, a sub-file and what that pulls in) is committed with it; a
    file named only in a LaTeX comment is not. A PDF a failed build deleted
    is committed as deleted.
  * End settles a `docs/<slug>/` deck whose slug a walked document already
    holds as its library id (`DESIGN.md` beside a "Design" deck).
  * A document placed in place outside `docs/` with a round on disk: End
    commits its source and doc.json with TUTOR.md, and the round stays out.
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
from tutorboard.course import ledger, library                       # noqa: E402
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

# The root's rules for sessions and built PDFs, the real root's feedback-round
# rules, and the project's `*.json` with the negations a document's record
# needs.
with open(os.path.join(os.path.dirname(BOARD_DIR), ".gitignore"),
          encoding="utf-8") as _fh:
    ROUND_RULES = [l.strip() for l in _fh
                   if "/feedback/" in l and not l.lstrip().startswith("#")]
ROOT_IGNORE = ("/sessions/\n/projects/*/docs/**/*.pdf\n*.log\n*.aux\n"
               + "".join(r + "\n" for r in ROUND_RULES))
LAB_IGNORE = "*.json\n!/tutorboard.json\n!/docs/doc.json\n!/docs/*/doc.json\n"

try:
    lab = os.path.join(base, "projects", "Lab")
    docs = os.path.join(lab, "docs")
    write(os.path.join(base, ".gitignore"), ROOT_IGNORE)
    write(os.path.join(lab, ".gitignore"), LAB_IGNORE)
    write(os.path.join(lab, "tutorboard.json"),
          json.dumps({"name": "Lab"}))
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
    check("the fixture carries the real root's feedback-round rules",
          len(ROUND_RULES) >= 2, ROUND_RULES)
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
                                      "Colibri and why it runs locally",
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
    signal = turn.turn_signal(out)
    check("the session's inbox wakes a [rework] turn naming the source",
          signal == "rework" and "docs/fleet.tex" in out, out)

    # The turn: the deck rewritten and rebuilt, every request answered. The
    # overhaul adds files of its own beside it: an image and a sub-file that
    # pulls in another image from a folder of its own. A map it commented out
    # is the owner's draft, not the deck's.
    write(os.path.join(docs, "fleet.tex"), DECK.replace(
        "One frame.", "Colibri.\\includegraphics[width=4cm]{colibri-map}"
        "\n%\\includegraphics{old-map.png}\n\\input{frames}"))
    write(os.path.join(docs, "colibri-map.png"), b"\x89PNG map")
    write(os.path.join(docs, "old-map.png"), b"\x89PNG old")
    write(os.path.join(docs, "frames.tex"),
          "\\graphicspath{{figs/}}\n\\begin{frame}\\includegraphics{arch}"
          "\\end{frame}\n")
    write(os.path.join(docs, "figs", "arch.png"), b"\x89PNG arch")
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
    write(os.path.join(lab, "TUTOR.md"), "# Where things are\n\nThe deck.\n")
    shown = ledger.summary(lab, doc)
    head = git("rev-parse", "HEAD").stdout.strip()
    rec, ok, said = sessions.end(sid, base=base)
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    check("End makes one commit", ok and git(
        "rev-list", "--count", "%s..HEAD" % head).stdout.strip() == "1", said)
    for want in ("projects/Lab/docs/fleet.tex", "projects/Lab/docs/fleet.pdf",
                 "projects/Lab/docs/doc.json",
                 "projects/Lab/docs/colibri-map.png",
                 "projects/Lab/docs/frames.tex",
                 "projects/Lab/docs/figs/arch.png",
                 "projects/Lab/TUTOR.md"):
        check("End commits %s" % want, want in files, files)
    check("End leaves every round out of the commit: no note, ledger or "
          "round directory", not any("/feedback/" in f for f in files), files)
    round_dir = note_path[:-3]
    check("and on disk, settled: the note's account, the ledgers, the "
          "round's requests, after-copy and caches",
          "## What was changed" in open(note_path, encoding="utf-8").read()
          and os.path.isfile(led)
          and os.path.isfile(os.path.join(lab, *note2["ledger"].split("/")))
          and os.path.isfile(os.path.join(round_dir, "items.json"))
          and os.path.isfile(os.path.join(round_dir, "after.tex"))
          and os.path.isfile(os.path.join(round_dir, "checked.json")),
          sorted(os.listdir(round_dir)) if os.path.isdir(round_dir) else None)
    library.forget()
    after = library.status(page)
    row = [d for d in after["documents"] if d.get("stem") == "fleet"]
    check("and the library still shows every round, read from disk",
          shown["rounds"] == 4 and ledger.summary(lab, doc) == shown
          and row and row[0].get("ledger") == shown,
          (shown, ledger.summary(lab, doc), row and row[0].get("ledger")))
    check("and git cannot see any of it",
          git("ls-files", "--", "projects/Lab/docs/feedback").stdout == ""
          and git("status", "--porcelain", "--",
                  "projects/Lab/docs/feedback").stdout == "")
    left = git("status", "--porcelain", "--", "projects/Lab/docs").stdout
    theirs = ("projects/Lab/docs/egress.md", "projects/Lab/docs/draft-private.md",
              "projects/Lab/docs/old-map.png")
    deck_left = [l for l in left.splitlines()
                 if not any(t in l for t in theirs)]
    check("nothing of the deck under docs/ is left modified or untracked after "
          "End, the rebuilt PDF included", deck_left == [], left)
    check("End commits only the deck's own files from the docs/ it shares: "
          "not the owner's edit to another document, nor an untracked draft, "
          "nor that document's round",
          not any(f.startswith(t) for f in files for t in theirs)
          and not any("/feedback/egress-" in f for f in files), files)
    check("and those stay as the owner left them, the commented-out map too",
          " M projects/Lab/docs/egress.md" in left
          and "?? projects/Lab/docs/draft-private.md" in left
          and "?? projects/Lab/docs/old-map.png" in left, left)

    # ---- a revise whose last build failed: the PDF is gone ------------------
    # pdflatex with -halt-on-error deletes the tracked PDF it could not
    # rebuild; End commits that deletion rather than leave it in the tree.
    write(os.path.join(docs, "fleet.tex"), DECK.replace("One frame.", "Broken."))
    os.remove(os.path.join(docs, "fleet.pdf"))
    head = git("rev-parse", "HEAD").stdout.strip()
    rec, ok, said = sessions.end(other, base=base)
    files = git("show", "--name-status", "--pretty=format:", "HEAD").stdout
    left = git("status", "--porcelain", "--", "projects/Lab/docs/fleet.pdf",
               "projects/Lab/docs/fleet.tex").stdout
    check("End after a failed build commits the deleted PDF with the source",
          ok and "D\tprojects/Lab/docs/fleet.pdf" in files
          and "M\tprojects/Lab/docs/fleet.tex" in files and left == "",
          (said, files, left))

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
    note4_path = os.path.join(lab, *note4["rel"].split("/"))
    check("End settles that deck's round, not the walked document's: its "
          "account and after-copy are on disk",
          ok and "## What was changed" in open(
              note4_path, encoding="utf-8").read()
          and os.path.isfile(os.path.join(note4_path[:-3], "after.tex")),
          (said, note4["rel"]))
    check("and End commits the deck it owns, none of its round",
          "projects/Lab/docs/design/design.tex" in files
          and not any("/feedback/" in f for f in files), files)
    library.forget()
    library.status(page)
    left = git("status", "--porcelain", "--", "projects/Lab/docs/design",
               "projects/Lab/DESIGN.md").stdout
    check("and the next library read leaves nothing of it to commit",
          left.strip() == "", left)

    # ---- a document placed in place, outside docs/, with a round ------------
    # End names only what `git add` takes: never an ignored round path, which
    # would fail the add and commit nothing, TUTOR.md included. A project of
    # its own, with no `*.json` rule, so its doc.json is trackable.
    talk = os.path.join(base, "projects", "Talk")
    talks = os.path.join(talk, "talks")
    write(os.path.join(talk, "tutorboard.json"),
          json.dumps({"name": "Talk"}))
    write(os.path.join(talk, "TUTOR.md"), "# Where things are\n")
    write(os.path.join(talks, "intro.md"), "# Intro\n\nOne slide.\n")
    git("add", "-A", "projects/Talk")
    git("commit", "-q", "-m", "talk")
    sid4 = registry.open_bound(base, "projects/Talk", "Intro talk")
    artifacts.place(talks, "intro.md", "Intro", session=sid4)
    library.forget()
    intro = [d for d in library.documents(talk) if d["stem"] == "intro"]
    check("a document placed in place outside docs/ is a library document "
          "with its record", intro and intro[0].get("artifact") == "talks",
          [(d["id"], d.get("artifact")) for d in library.documents(talk)])
    note5 = library.write_note(sessions.repo(sid4, base), intro[0]["id"],
                               "Say who it is for.", hand_over=False)
    note5_path = os.path.join(talk, *note5.get("rel", "x").split("/"))
    check("its round is filed in talks/feedback/ and ignored",
          note5.get("ok") and note5["rel"].startswith("talks/feedback/intro-")
          and git("check-ignore", "-q", "projects/Talk/" + note5["rel"])
          .returncode == 0, note5)
    art = [a for a in artifacts.for_session(talk, sid4) if a["rel"] == "talks"]
    check("`artifacts.kept` names no round path, so End never hands git an "
          "ignored one", art and not any(
              os.sep + "feedback" in p for p in artifacts.kept(art[0])),
          art and artifacts.kept(art[0]))
    write(os.path.join(talks, "intro.md"), "# Intro\n\nFor the lab.\n")
    write(os.path.join(talk, "TUTOR.md"), "# Where things are\n\nThe talk.\n")
    head = git("rev-parse", "HEAD").stdout.strip()
    rec, ok, said = sessions.end(sid4, base=base)
    files = git("show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
    check("End commits it: its source, its doc.json and TUTOR.md, in one commit",
          ok and git("rev-list", "--count", "%s..HEAD" % head).stdout.strip()
          == "1" and {"projects/Talk/talks/intro.md",
                      "projects/Talk/talks/doc.json",
                      "projects/Talk/TUTOR.md"} <= set(files), (said, files))
    check("and its round stays on disk and out of the commit",
          os.path.isfile(note5_path)
          and not any("/feedback/" in f for f in files), files)
    check("leaving nothing of the project to commit",
          git("status", "--porcelain", "--", "projects/Talk").stdout == "",
          git("status", "--porcelain", "--", "projects/Talk").stdout)

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
