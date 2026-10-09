#!/usr/bin/env python3
"""The teaching method ships with the board, and the board does what it says.

`board/TEACHING.md` is read in place by every turn from the Atlas root. This
suite guards behaviour, not wording:

- the document's shape: its length, that every link inside it lands on a
  heading, that every `board` command it names exists, and that every section
  code names is a heading;
- what a turn is actually handed: which of the `tutorboard.sense` blocks each
  kind of turn gets, and how often;
- the commands those blocks name: `board write --over`, `board step`, `--help`.

A rule's wording is checked only where a real session turned on it. This file
and test/tokens.py hold at most 30 such literal phrases between them, the
retired-feature list included; count before adding one.
"""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

loader = importlib.machinery.SourceFileLoader("boardcli", os.path.join(ROOT, "bin", "board"))
spec = importlib.util.spec_from_loader("boardcli", loader)
boardcli = importlib.util.module_from_spec(spec)
loader.exec_module(boardcli)
from tutorboard import brief as brief_mod                     # noqa: E402
from tutorboard import sense                                  # noqa: E402
from tutorboard.course.repo import Repo                       # noqa: E402
from tutorboard.runner import prompts                         # noqa: E402
from tutorboard.agents import recipes                         # noqa: E402
from tutorboard.runner import turn as runturn                 # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def flat(said):
    """Whitespace folded and case dropped: what must agree is the rule, not how
    a paragraph happened to be filled."""
    return " ".join(str(said or "").lower().split())


METHOD = os.path.join(ROOT, "TEACHING.md")
check("the method ships with the board", os.path.isfile(METHOD))
text = open(METHOD, encoding="utf-8").read() if os.path.isfile(METHOD) else ""
FLAT = flat(text)
check("the brief names it where it is, from the Atlas root a turn runs in",
      brief_mod.METHOD == "board/TEACHING.md")

# ---------------------------------------------------------------------------
# THE DOCUMENT'S SHAPE
# ---------------------------------------------------------------------------
LINES = text.count("\n")
check("it is at most 600 lines (%d)" % LINES, 0 < LINES <= 600)

HEADINGS = [re.sub(r"^#+\s*", "", line).strip()
            for line in text.splitlines() if line.startswith("#")]


def slug(heading):
    """The anchor a Markdown renderer gives a heading."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def is_heading(name):
    name = flat(name)
    return any(flat(h) == name or flat(h).startswith(name) for h in HEADINGS)


ANCHORS = {slug(h) for h in HEADINGS}
links = re.findall(r"\]\(#([^)]+)\)", text)
check("it links inside itself (%d links)" % len(links), len(links) >= 5)
broken = [a for a in links if a not in ANCHORS]
check("and every such link lands on a heading%s"
      % (": " + ", ".join(broken) if broken else ""), not broken)

named = sorted(set(re.findall(r"`board ([a-z][a-z-]*)", text)))
missing = [c for c in named if c not in boardcli.COMMANDS]
check("every `board` command it names is one (%d named)%s"
      % (len(named), ": " + ", ".join(missing) if missing else ""),
      len(named) >= 10 and not missing)

# EVERY SECTION CODE NAMES IS A HEADING. A turn handed "TEACHING.md says the
# same under `X`" goes looking for X, so X has to be there. Read off every
# string a turn can be handed: the sense blocks, the brief's and the prompts.
handed = [v for m in (sense, brief_mod, prompts) for v in vars(m).values()
          if isinstance(v, str)]
handed += list(sense.SIGNAL_SENSE.values())
_prompts = os.path.join(ROOT, "tutorboard", "runner", "prompts")
handed += [open(os.path.join(_prompts, f), encoding="utf-8").read()
           for f in sorted(os.listdir(_prompts))]
quoted = sorted(set(q for h in handed for q in re.findall(
    r"TEACHING\.md[^`]{0,60}?(?:under|section) `([^`]+)`",
    " ".join(h.split()))))
check("code names sections of it (%s)" % "; ".join(quoted), bool(quoted))
for q in quoted:
    check("and %r is a heading" % q, is_heading(q))
# The methods a teach turn picks from, each a section of its own.
for q in ("Homework", "A test review", "A walkthrough", "Coaching",
          "A session coding at the cluster", "A deck or a paper"):
    check("the method %r is a heading" % q, is_heading(q))

# Retired features stay out of it.
for word in (r"\bthreads?\b", r"\bmaps?\b", r"famil", r"DIRECTION\.md",
             r"\baim", r"stance", r"NEXT[.]md", r"board\s+note", r"board\s+hold"):
    check("it never mentions %s" % word,
          not re.search(word, text, re.IGNORECASE))

# ---------------------------------------------------------------------------
# THE RULES A REAL SESSION TURNED ON
# ---------------------------------------------------------------------------
for phrase, why in [
    # A model handed a chapter and told to teach writes a lecture.
    ("exercises, all the way down", "a lesson is exercises and nothing else"),
    # "I've got a board to write on and have to scroll up to see the question."
    ("Then ask it again", "a posing card closes by restating the question"),
    # A skipped homework problem is deferred, not dropped.
    ("not now", "a skipped assigned problem is still owed"),
    ("ladder comes after the break", "a review asks cold and ladders from a break"),
    # "the tutor embellished my work a lot with its own prose"
    ("Nothing goes in that they did not write",
     "the write-up carries their argument and nothing added to it"),
    # "Two words to add when you write it up."
    ("never tells them to write anything up",
     "no card hands the write-up back to the student"),
    # "I'm not sure any coding happened."
    ("Never hand back a plan", "a plan handed back is not the work"),
]:
    check("the method states: " + why, flat(phrase) in FLAT)

# Two places, one rule: the document a tutor opens, and the block a woken turn
# is handed. A rule fixed in one and left in the other is the failure here.
for phrase, block, why in [
    ("mathematics in a card is tex, not ascii", sense.PLAIN_SENSE,
     "every card's mathematics is TeX"),
    ("fix the module that produces it and run it again", sense.RULE_SENSE,
     "fix the rule, never its output"),
]:
    check("TEACHING.md and the turn agree: " + why,
          phrase in FLAT and phrase in flat(block))

# ---------------------------------------------------------------------------
# WHAT A TURN IS HANDED
# ---------------------------------------------------------------------------
_prompt_text = "".join(handed)
check("the prompts point at the method where it is",
      brief_mod.METHOD in _prompt_text)

# A doing turn gets a longer clock: one ran 56 minutes, the next was killed at 15.
_cfg = recipes.load_config()
_clock = tempfile.mkdtemp(prefix="tutor-clock-")
try:
    os.makedirs(os.path.join(_clock, "live"))

    def _sitting(**kw):
        with open(os.path.join(_clock, "live", "state.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(kw, fh)

    _sitting(session="lecture")
    teach_for = runturn.turn_timeout(_cfg, _clock)
    _sitting(session="lecture", mode="do")
    build_for = runturn.turn_timeout(_cfg, _clock)
    _sitting(session="lecture")
    make_for = runturn.turn_timeout(_cfg, _clock, signal="writeup")
    check("a do-mode turn gets longer than a teaching turn, at least 40 minutes",
          build_for > teach_for and build_for >= 2400)
    check("a turn that writes a document gets the same", make_for == build_for)
    _sitting(session="make", makes="paper", aim="build", stance="do")
    check("a legacy session that says make, build or do is taught",
          runturn.turn_timeout(_cfg, _clock) == teach_for == 900)
finally:
    shutil.rmtree(_clock, ignore_errors=True)

# A document asked for from a session: the line carries the make method whole,
# names the file where it is given, and takes the evening as its scope only
# where nobody named one.
for makes in ("paper", "slides"):
    line = sense.writeup_sense(makes)
    kind = "slides" if makes == "slides" else "paper"
    check("a %s ask carries the make method whole" % makes,
          sense.MAKE_SENSE in line and line.count(sense.RULE_SENSE) == 1)
    check("and the evening as its scope where nobody named one (%s)" % makes,
          sense.WRITEUP_EVENING in line)
    named_line = sense.writeup_sense(makes, "the serve harness", "docs/x/x.tex")
    check("and what they named where they named it (%s)" % makes,
          "the serve harness" in named_line
          and sense.WRITEUP_EVENING not in named_line)
    check("and the file it writes and builds (%s)" % makes,
          (sense.FILE_SENSE[kind] + sense.DOC_BUILD_SENSE)
          % {"source": "docs/x/x.tex"} in named_line)
check("a deck and a paper are different asks",
      sense.writeup_sense("paper") != sense.writeup_sense("slides"))

home = tempfile.mkdtemp(prefix="tutor-doing-")
try:
    root = os.path.join(home, "Course")
    os.makedirs(root)
    with open(os.path.join(root, "tutorboard.json"), "w", encoding="utf-8") as fh:
        fh.write('{"name": "Course"}')
    repo = Repo(root)

    def state(**kw):
        st = {"course": "Course", "session": "lecture"}
        st.update(kw)
        with open(repo.state_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)

    RULE, MEASURE = sense.RULE_SENSE, sense.MEASURE_SENSE

    state(mode="do")
    _do = sense.session_sense(repo)
    check("a do-mode turn is handed the doing order, the rule and the measure, "
          "once each", sense.DOING_SENSE in _do and sense.DO_SENSE in _do
          and _do.count(RULE) == 1 and _do.count(MEASURE) == 1)
    check("and no write-up rule, since it poses no questions",
          sense.WRITEUP_SENSE not in _do)
    for kw, why in ((dict(mode="teach"), "teach mode"),
                    (dict(aim="build"), "a legacy aim of build"),
                    (dict(stance="do"), "a legacy stance of do"),
                    (dict(session="make", makes="paper"), "a legacy make")):
        state(**kw)
        said = sense.session_sense(repo)
        check("a turn in %s is taught: the method, the write-up and how to "
              "write, and no doing order" % why,
              sense.METHOD_SENSE in said and sense.WRITEUP_SENSE in said
              and sense.TEACH_SENSE in said and sense.PLAIN_SENSE in said
              and sense.DOING_SENSE not in said and RULE not in said
              and said.count(MEASURE) == 1)

    # The turns that never run `board brief`: their inbox line is the whole of
    # what they read, so the rule and the measure ride in it, once.
    for line, why in (
            (sense.ship_sense("colibri", "repair the transcript"), "a ship"),
            (sense.writeup_sense("paper", "the serve harness"), "a write-up"),
            (sense.revise_sense("docs/a/a.tex", "docs/a/feedback.md"),
             "a revision"),
            (sense.rework_sense("docs/a/a.tex", "docs/a/feedback.md",
                                "for the meeting"), "an overhaul"),
            (sense.handover_sense("0004")
             + sense.session_sense(repo, doing=True), "a handed-over step")):
        check("%s carries the rule and the measure, once each" % why,
              line.count(RULE) == 1 and line.count(MEASURE) == 1)

    # A MISSION replaces the session: it has its job, so it is not handed the
    # method for teaching an exercise or the write-up.
    state(session="lecture")

    def _brief():
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            boardcli.cmd_brief(boardcli.course_repo.Repo(root), [])
        return out.getvalue()

    _cold = _brief()
    check("a teaching subject with no mission is briefed as a lesson",
          sense.METHOD_SENSE in _cold and RULE not in _cold
          and sense.MISSION_SENSE not in _cold)
    missions = os.path.join(root, "live", "missions")
    os.makedirs(missions, exist_ok=True)

    def _mission(ended=""):
        with open(os.path.join(missions, "0007.json"), "w", encoding="utf-8") as fh:
            json.dump({"id": "0007", "task": "repair the transcript",
                       "agent": "colibri", "at": time.time(), "ship": False,
                       "host": "", "card_at": 0.0, "ceiling": 0.0,
                       "ended": ended, "ended_at": time.time() if ended else 0.0,
                       "reason": "", "looked": 0.0, "shipped": 0.0}, fh)

    _mission()
    check("a live mission is what `missions.running` reports",
          boardcli.missions.running(root))
    _sent = _brief()
    check("the same subject briefs a mission as a doing turn, not a lesson",
          sense.MISSION_SENSE in _sent and sense.DOING_SENSE in _sent
          and sense.METHOD_SENSE not in _sent
          and sense.WRITEUP_SENSE not in _sent)
    _woken = (prompts.HEADLESS_FIRST_PROMPT
              % {"inbox": "repair the transcript", "handoff": ""}) + _sent
    check("and once across the inbox line and the brief together",
          _woken.count(RULE) == 1 and _woken.count(MEASURE) == 1
          and _woken.count(sense.DOING_SENSE) == 1)

    def _step(*args, body=""):
        out = io.StringIO()
        old, sys.stdin = sys.stdin, io.StringIO(body)
        try:
            with contextlib.redirect_stdout(out):
                code = boardcli.cmd_step(boardcli.course_repo.Repo(root), list(args))
        finally:
            sys.stdin = old
        return code, out.getvalue()

    _code, _said = _step(body="rebuilt the reference: 74 rows, 6 disagree")
    check("`board step` lands the line on the running mission",
          _code == 0 and "0007" in _said
          and [s["said"] for s in boardcli.progress.read(root, "0007")]
          == ["rebuilt the reference: 74 rows, 6 disagree"])
    _code, _said = _step("--show")
    check("`board step --show` reads the trail back", _code == 0 and "74 rows" in _said)
    check("and the brief carries it", "74 rows" in _brief())
    os.remove(os.path.join(missions, "0007.json"))
    boardcli.progress.drop(root, "0007")
    _code, _said = _step(body="nobody is waiting on this")
    check("a step with no mission running is refused", _code == 1)
    _mission(ended="done")
    check("an ended mission leaves the subject teaching again",
          sense.MISSION_SENSE not in _brief())
    shutil.rmtree(missions, ignore_errors=True)
    state(session="lecture")

    # ONE CARD, OPENED WITH A SENTENCE AND FINISHED WITH THE REPORT.
    def write(args, body):
        out = io.StringIO()
        old_stdin, sys.stdin = sys.stdin, io.StringIO(body)
        try:
            with contextlib.redirect_stdout(out):
                code = boardcli.cmd_write(boardcli.course_repo.Repo(root), args)
        finally:
            sys.stdin = old_stdin
        return code, out.getvalue().strip()

    code, flagged = write(["lesson", "--title", "Opening: verify the call path"],
                          "one sentence.")
    check("a --title is read as the title rather than written into it",
          code == 0 and "title: Opening: verify the call path"
          in open(flagged, encoding="utf-8").read()
          and os.path.basename(flagged) == "0001-opening-verify-the-call-path.md")
    code, odd = write(["lesson", "--nonsense", "real name"], "x")
    check("an option nobody implemented is dropped, not printed on the board",
          code == 0 and "--nonsense" not in open(odd, encoding="utf-8").read())
    for name in os.listdir(repo.cards):
        os.remove(os.path.join(repo.cards, name))

    code, first = write(["lesson", "starting"], "I am about to split it in two.")
    check("a doing turn puts one sentence up at once",
          code == 0 and os.path.basename(first).startswith("0001-"))
    code, again = write(["--over", os.path.basename(first), "lesson", "the seam is cut"],
                        "Done. Split it into two functions and ran the tests.")
    check("and writes the report over it: one card, its place kept, renamed",
          code == 0 and "Split it into two functions"
          in open(again, encoding="utf-8").read()
          and len([n for n in os.listdir(repo.cards) if n.endswith(".md")]) == 1
          and os.path.basename(again).startswith("0001-")
          and "the-seam-is-cut" in os.path.basename(again))
    code, _said = write(["--over", "../../../etc/passwd", "lesson", "no"], "x")
    check("a card outside this board is refused rather than written over",
          code == 1)

    # Asking what a command does must not do it.
    before = sorted(os.listdir(repo.cards))
    out = io.StringIO()
    old_stdin, sys.stdin = sys.stdin, io.StringIO("")
    try:
        with contextlib.redirect_stdout(out):
            code = boardcli.main(["write", "--help", "--repo", root])
    finally:
        sys.stdin = old_stdin
    check("`board write --help` prints its help and writes no card",
          code == 0 and "--over" in out.getvalue()
          and sorted(os.listdir(repo.cards)) == before)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = boardcli.main(["memo", "--help", "--repo", root])
    check("and every command answers --help the same way",
          code == 0 and "board memo" in out.getvalue())
finally:
    shutil.rmtree(home, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails else "the method ships with the board")
sys.exit(1 if fails else 0)
