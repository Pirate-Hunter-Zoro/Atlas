#!/usr/bin/env python3
"""A walkthrough: a lesson about machinery that already exists.

Every other sitting on this board ends in the student producing something new.
In a working project most of what has to be understood was written months ago,
and a tutor with nowhere to put that does the only thing it can -- there is a
card in PSYCH-ASR that proves it, invented arithmetic on fictional numbers in a
repository whose owner wanted an algorithm on disk explained to him.

So: the scope is a file in this repository, it is checked before it reaches
anything, and the tutor is told to trace rather than to write. What is guarded
here is the same as everywhere else -- that nothing invented reaches the
filesystem or the prompt -- plus the one thing that is new, which is that the
stance may now belong to the sitting rather than to the repository, and a stance
that overrode the written one must never outlive the sitting that chose it.
"""

import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tutorboard.course import walk            # noqa: E402
from tutorboard.course import config          # noqa: E402
from tutorboard import brief, sense           # noqa: E402
from tutorboard.course import repo as course_repo   # noqa: E402
from tutorboard.lesson import archive         # noqa: E402
from tutorboard.server import handler, hub, tikz    # noqa: E402
from http.server import ThreadingHTTPServer   # noqa: E402

fails = []


def check(name, cond):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name)


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# A file has to be big enough to be worth a sitting; `MIN_BYTES` is the floor and
# every fixture here clears it without anybody having to count characters.
BODY = "\n".join("    # a line of it that is long enough to be real" for _ in range(8))

# --- what a repository can be walked through ---------------------------------
# Discovered, never registered, exactly as chapters and problem sets are.
proj = tempfile.mkdtemp(prefix="tutor-walk-proj-")
prose = tempfile.mkdtemp(prefix="tutor-walk-prose-")
try:
    write(proj, "psych_asr/__init__.py", "from . import evaluate\n" + BODY)
    write(proj, "psych_asr/config.py", "SETTING = 1\n" + BODY)
    write(proj, "psych_asr/evaluate/__init__.py", "\n" + BODY)
    write(proj, "psych_asr/evaluate/grade.py",
          "import re\n\n\ndef grade(reference, candidate):\n" + BODY + "\n\n\nclass Finding:\n    pass\n")
    write(proj, "psych_asr/transcript/corrections.py",
          "def apply_corrections(turns, log):\n" + BODY + "\n")
    write(proj, "scripts/run.sh", "#!/usr/bin/env bash\nset -eu\n" + BODY + "\n")
    write(proj, "README.md", "# a project\n" + BODY)
    write(proj, "notes.txt", "not machinery\n" + BODY)
    write(proj, "psych_asr/tiny.py", "x = 1\n")
    # A SHEBANG IS AS GOOD A DECLARATION AS A SUFFIX, and `SOURCE` keyed on the
    # suffix alone -- so the entire surface of colibrì, which is `bin/coli`,
    # `bin/coli-up`, `bin/coli-ask` and `bin/coli-code`, was invisible. A
    # walkthrough of that workspace offered six files and not one of them was
    # the one anybody would ask for.
    write(proj, "bin/coli-up",
          "#!/usr/bin/env bash\nset -eu\nwarm() {\n" + BODY + "\n}\n")
    write(proj, "bin/coli-ask", "#!/bin/bash\n" + BODY + "\n")
    write(proj, "bin/tally", "#!/usr/bin/env python3\ndef tally(rows):\n" + BODY + "\n")
    # And a file that declared nothing at all is not machinery. A licence, a
    # lock file and a data dump all have no suffix either.
    write(proj, "LICENSE", "All rights reserved.\n" + BODY)
    write(proj, "README", "# prose with no suffix\n" + BODY)
    for d in ("live", "node_modules", "__pycache__", "results", "data", ".git"):
        os.makedirs(os.path.join(proj, d), exist_ok=True)
        write(proj, os.path.join(d, "buried.py"), "def buried():\n" + BODY + "\n")

    names = [u["name"] for u in walk.units(proj)]
    check("a project offers its own source files",
          "psych_asr/evaluate/grade.py" in names
          and "psych_asr/transcript/corrections.py" in names)
    check("and shell scripts, because a pipeline is taught by its job script too",
          "scripts/run.sh" in names)
    check("and a script with a #! line and no suffix at all, which is what a "
          "driver command is",
          "bin/coli-up" in names and "bin/coli-ask" in names
          and "bin/tally" in names)
    # A README is read by reading it. A walkthrough over one is a lecture with
    # extra steps, and offering it buries the files that do something.
    check("but never prose", not [n for n in names if n.endswith((".md", ".txt"))])
    check("and never a file that declared nothing -- no suffix and no shebang",
          "LICENSE" not in names and "README" not in names)
    # The symbol check has to know which language a shebang stands in for, or a
    # function named inside a suffixless script is a name it cannot verify --
    # and an unverifiable name is one `resolve` refuses to carry.
    chosen, _ = walk.resolve(proj, ["bin/coli-up::warm"])
    check("a function inside a #! bash script is found the way one in a .sh is",
          [u["name"] for u in chosen] == ["bin/coli-up::warm"])
    chosen, _ = walk.resolve(proj, ["bin/tally::tally"])
    check("and one inside a #! python script too",
          [u["name"] for u in chosen] == ["bin/tally::tally"])
    check("while a name such a script does not define is still refused",
          walk.resolve(proj, ["bin/coli-up::missing"])[1] == ["bin/coli-up::missing"])
    check("and never build output, dependencies, data or the board's own live/",
          not [n for n in names if n.split("/")[0]
               in ("live", "node_modules", "__pycache__", "results", "data", ".git")])
    check("an __init__.py is a namespace, not machinery, and is not offered",
          not [n for n in names if n.endswith("__init__.py")])
    check("and neither is a file with nothing in it",
          "psych_asr/tiny.py" not in names)
    check("each one says which directory it is in, so a list of a hundred can be read",
          all(u["dir"] for u in walk.units(proj))
          and {u["dir"] for u in walk.units(proj)}
          >= {"psych_asr", "psych_asr/evaluate", "scripts"})
    check("and they come back in the repository's own order, not the order os.walk found them",
          names == sorted(names, key=lambda n: (os.path.dirname(n), n)))

    write(prose, "README.md", "# all narrative, no machinery\n" + BODY)
    check("a repository with no source says so rather than inventing something",
          walk.units(prose) == [] and walk.status(prose, {}) is None
          and walk.kind(prose) == "")

    # --- a name from a request is checked, never trusted ----------------------
    # A person names machinery the way their language names it, and the last
    # component of a dotted name is as likely to be the function as the module.
    chosen, unknown = walk.resolve(proj, ["psych_asr/evaluate/grade.py"])
    check("a file can be named by its path",
          [u["name"] for u in chosen] == ["psych_asr/evaluate/grade.py"])
    chosen, _ = walk.resolve(proj, ["psych_asr.evaluate.grade"])
    check("or as a module, the way the language names it",
          [u["name"] for u in chosen] == ["psych_asr/evaluate/grade.py"])
    chosen, _ = walk.resolve(proj, ["psych_asr.evaluate.grade.grade"])
    check("or as a definition inside one, which is where a walkthrough starts",
          [u["name"] for u in chosen] == ["psych_asr/evaluate/grade.py::grade"]
          and chosen[0]["symbol"] == "grade")
    chosen, _ = walk.resolve(proj, ["psych_asr.evaluate.grade.Finding"])
    check("a class is a definition too", chosen and chosen[0]["symbol"] == "Finding")
    # The whole point of checking: a walkthrough announced over a function that
    # is not there sends the tutor looking, and it will find something else and
    # teach that instead.
    check("a name the file does not define is refused rather than carried",
          walk.resolve(proj, ["psych_asr.evaluate.grade.missing"])[1]
          == ["psych_asr.evaluate.grade.missing"])
    check("and so is a file this repository does not have",
          walk.resolve(proj, ["psych_asr/evaluate/nothing.py"])[1]
          == ["psych_asr/evaluate/nothing.py"])
    check("a bare filename works where the repository has only one of them",
          [u["name"] for u in walk.resolve(proj, ["corrections.py"])[0]]
          == ["psych_asr/transcript/corrections.py"])
    write(proj, "scripts/config.py", "OTHER = 2\n" + BODY)
    walk._cache.clear()
    check("and resolves to nothing where it would have to guess between two",
          walk.resolve(proj, ["config.py"])[1] == ["config.py"])
    check("naming the same file twice walks it once",
          len(walk.resolve(proj, ["psych_asr.evaluate.grade",
                                  "psych_asr/evaluate/grade.py"])[0]) == 1)
    check("a file and one definition inside it are two different scopes",
          len(walk.resolve(proj, ["psych_asr.evaluate.grade",
                                  "psych_asr.evaluate.grade.grade"])[0]) == 2)

    # --- the scope is re-resolved on the way out, never echoed back -----------
    state = {"walk": ["psych_asr/evaluate/grade.py::grade",
                      "psych_asr/gone.py"]}
    check("a scope naming something deleted since drops it",
          [u["name"] for u in walk.scope(proj, state)]
          == ["psych_asr/evaluate/grade.py::grade"])

    check("a short scope is named in the sitting label",
          walk.sitting_label(walk.resolve(proj, ["psych_asr.evaluate.grade.grade"])[0])
          == "Walkthrough — grade")
    check("and a long one is counted instead of listed",
          walk.sitting_label([{"short": "a"}] * 5) == "Walkthrough — 5 files")
finally:
    shutil.rmtree(prose, ignore_errors=True)

# --- what the tutor is actually told ------------------------------------------
try:
    json.dump({"name": "PSYCH-ASR"},
              open(os.path.join(proj, "tutorboard.json"), "w"))
    r = course_repo.Repo(proj)
    st = r.state()
    st.update({"session": "walk",
               "walk": ["psych_asr/evaluate/grade.py::grade"]})
    json.dump(st, open(r.state_path, "w"))

    line = sense.session_sense(r)
    check("the tutor is told this is a walkthrough", "WALKTHROUGH SITTING" in line)
    check("and what it is over, named in the prompt rather than left to be found",
          "psych_asr/evaluate/grade.py::grade" in line)
    check("and that nothing is being built", "NOTHING IS BEING BUILT HERE" in line)
    check("and not to assign a change or write code into a card",
          "Do not assign a change" in line and "do not write code into a card" in line)
    check("and that the scope is not its to widen", "not yours to widen" in line)
    # The failure this sitting exists to replace: a tour of the file, top to
    # bottom, read on a tablet and understood by nobody.
    check("the exercise is a hand trace, not an explanation",
          "hand trace" in line and "they carry it one step" in line)
    check("on one invented instance carried the whole way through",
          "ONE INSTANCE FOR THE WHOLE SITTING" in line and "INVENTED" in line)
    check("with a plain name before the identifier",
          "PLAIN NAMES BEFORE IDENTIFIERS" in line)
    check("and an excerpt rather than the file",
          "smallest excerpt" in line and "never the file" in line)
    check("the recap comes last, which is the word dump it replaces",
          "ONLY WHEN THE TRACE IS DONE" in line and "Last, never first" in line)
    check("and it still points at the method rather than restating it",
          "live/TEACHING.md" in line)
    check("and produces no document, like a review",
          "do not compile" in line and "no write-up" in line)
    # A lecture chooses a manageable few pieces of work. A walkthrough does not
    # choose anything: the student named it.
    check("and is not told to pick a manageable few, which is a lecture behaviour",
          "manageable few" not in line)

    st["walk"] = []
    json.dump(st, open(r.state_path, "w"))
    line = sense.session_sense(r)
    check("a walkthrough with nothing named asks rather than choosing",
          "Ask in your first card" in line and "do not choose it yourself" in line)
    check("and does not go looking for a candidate",
          "Do not survey the repository" in line)
finally:
    pass

# --- a stance belongs to a sitting, not only to a repository ------------------
# One word in tutorboard.json could only ever answer for the whole repository,
# and a project has both kinds of work in it: plumbing its owner wants written,
# and the one algorithm they need to understand. Both answers, one repository.
teach_repo = tempfile.mkdtemp(prefix="tutor-walk-teach-")
do_repo = tempfile.mkdtemp(prefix="tutor-walk-do-")
try:
    json.dump({"name": "PSYCH-ASR"},
              open(os.path.join(teach_repo, "tutorboard.json"), "w"))
    json.dump({"name": "TRD-EHR", "stance": "do"},
              open(os.path.join(do_repo, "tutorboard.json"), "w"))
    write(teach_repo, "psych_asr/grid.py", "def sweep():\n" + BODY + "\n")
    write(do_repo, "pipeline/confound.py", "def overlap():\n" + BODY + "\n")

    check("a sitting that says nothing runs under the repository's own answer",
          config.stance_for(teach_repo, {}) == "teach"
          and config.stance_for(do_repo, {}) == "do")
    check("and a sitting that names one runs under that instead",
          config.stance_for(teach_repo, {"stance": "do"}) == "do"
          and config.stance_for(do_repo, {"stance": "teach"}) == "teach")
    check("a word that is not a stance is not one",
          config.stance_for(teach_repo, {"stance": "maybe"}) == "teach"
          and config.clean_stance("maybe") is None)

    rt = course_repo.Repo(teach_repo)
    st = rt.state()
    st.update({"session": "lecture", "chapter": "the grid sweep", "stance": "do"})
    json.dump(st, open(rt.state_path, "w"))
    line = sense.session_sense(rt)
    check("a doing sitting in a teaching repository is told to write the code",
          "STANCE IS DO" in line and "you write the code yourself" in line)
    # The one mistake here the next card cannot undo is writing the code for
    # somebody who wanted to learn it. An override that leaks into the handoff
    # becomes the repository's answer without anybody deciding it.
    check("and told that it is this sitting's and ends with it",
          "CHOSEN FOR THIS SITTING" in line
          and "Do not write it into HANDOFF.md" in line)

    rd = course_repo.Repo(do_repo)
    st = rd.state()
    st.update({"session": "lecture", "chapter": "the propensity model",
               "stance": "teach"})
    json.dump(st, open(rd.state_path, "w"))
    line = sense.session_sense(rd)
    check("a teaching sitting in a doing repository puts the withholding back",
          "THIS SITTING'S IS TEACH" in line and "they write the code, you do not" in line)
    check("and says the repository's own answer is unchanged",
          "the repository's own answer is unchanged" in line)

    # A walkthrough and a review read rather than write, so a repository that
    # wants its code written does not get it written into one of these.
    st.update({"session": "walk", "walk": ["pipeline/confound.py"],
               "stance": None})
    st.pop("stance")
    json.dump(st, open(rd.state_path, "w"))
    line = sense.session_sense(rd)
    check("a doing repository's walkthrough is still a walkthrough",
          "WALKTHROUGH SITTING" in line and "STANCE IS DO" not in line)

    # The briefing is where a cold turn finds out, and a turn that cannot see
    # that the stance was chosen for the evening will write it down as standing.
    st = rt.state()
    line = brief.briefing(rt, sense)
    check("the briefing names the sitting's stance and the repository's when they differ",
          "stance: do" in line and "tutorboard.json says teach" in line)
    st.pop("stance")
    json.dump(st, open(rt.state_path, "w"))
    line = brief.briefing(rt, sense)
    check("and names it once when they agree",
          "stance: teach" in line and "tutorboard.json says" not in line)
finally:
    shutil.rmtree(teach_repo, ignore_errors=True)
    shutil.rmtree(do_repo, ignore_errors=True)

# --- the sitting itself, through the real handler -----------------------------
tmp = tempfile.mkdtemp(prefix="tutor-walk-")
try:
    json.dump({"name": "PSYCH-ASR"},
              open(os.path.join(tmp, "tutorboard.json"), "w"))
    write(tmp, "psych_asr/evaluate/grade.py",
          "def grade(reference, candidate):\n" + BODY + "\n")
    write(tmp, "psych_asr/transcript/corrections.py",
          "def apply_corrections(turns, log):\n" + BODY + "\n")
    walk._cache.clear()
    repo = course_repo.Repo(tmp)
    open(os.path.join(repo.cards, "0001-mid-lesson.md"), "w",
         encoding="utf-8").write("---\nkind: lesson\ntitle: A card\n---\n\nx\n")

    worker = tikz.TikzWorker(repo)
    worker.start()
    board = hub.Hub(repo, worker)
    board.payload = json.dumps(board.build())

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
    httpd.daemon_threads = True
    httpd.repo = repo
    httpd.hub = board
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    BASE = "http://127.0.0.1:%d" % port

    def post(path, body):
        req = urllib.request.Request(BASE + path, method="POST",
                                     data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    try:
        payload = board.build()
        check("the board is told what can be walked through before any walkthrough exists",
              payload.get("walk") and len(payload["walk"]["units"]) == 2)
        check("and that nothing is being walked through yet",
              payload["walk"]["scope"] == [])

        status, body = post("/session", {
            "session": "walk", "over": ["psych_asr.evaluate.grade.grade"]})
        check("a walkthrough can be opened from the board",
              status == 200 and body.get("ok"))
        st = repo.state()
        check("the badge will read walk", st.get("session") == "walk")
        check("and the scope is recorded as the file and the definition in it",
              st.get("walk") == ["psych_asr/evaluate/grade.py::grade"])
        check("the sitting is labelled with what it covers",
              "Walkthrough" in (st.get("chapter") or ""))
        # Opening one is starting a different lesson, so what is being left is
        # filed whole rather than written over -- the same rule as a review.
        check("and the lesson it interrupted was filed, not overwritten",
              len(archive.list_archive(repo)) == 1)

        status, body = post("/session", {"session": "walk", "over": ["nope.py"]})
        check("a file this repository does not have is refused by name",
              status == 400 and body.get("unknown") == ["nope.py"])
        status, _ = post("/session", {"session": "walk", "over": []})
        check("and a walkthrough over nothing is refused rather than opened",
              status == 400)
        check("a refused walkthrough leaves the sitting it was in alone",
              repo.state().get("walk") == ["psych_asr/evaluate/grade.py::grade"])

        # A stance chosen on the board belongs to the sitting being opened, and
        # the way back to the repository's own answer is to open one without
        # choosing -- which is what tapping `lecture` does.
        status, _ = post("/session", {"session": "lecture", "stance": "do"})
        check("a stance chosen on the board reaches the sitting",
              repo.state().get("stance") == "do")
        check("and opening that sitting cleared the walkthrough's scope",
              not repo.state().get("walk"))
        check("and the tutor is told to write the code",
              "STANCE IS DO" in sense.session_sense(repo))
        status, _ = post("/session", {"session": "lecture"})
        check("opening the next sitting without one gives the repository back",
              not repo.state().get("stance")
              and "STANCE IS DO" not in sense.session_sense(repo))
        status, _ = post("/session", {"session": "lecture", "stance": "sideways"})
        check("a stance that is not one is dropped rather than failing the request",
              status == 200 and not repo.state().get("stance"))
    finally:
        httpd.shutdown()
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(proj, ignore_errors=True)

# ---------------------------------------------------------------------------
# A VENDOR TREE IS WALKABLE, AND IS STILL NOT A WORKSPACE
# ---------------------------------------------------------------------------
# `atlas.json` made one claim out of two: the vendor family was skipped, and the
# reason given was that nothing in it is the person's to be GRADED on. The ask
# was about TRACING -- *"who knows when we'll want to explore external tools in
# the same way... That's the best way to dive into how Colibri works"* -- and
# under the merged rule that was impossible for a reason about homework.
#
# So there are two lists, and what is guarded here is that they stay two. The
# failure to catch is either direction: a tree that cannot be read, or a tree
# that something eventually offers a sitting in.
from tutorboard import atlas                                # noqa: E402
from tutorboard.course import map as mapping                 # noqa: E402

home = tempfile.mkdtemp(prefix="tutor-walk-atlas-")
was = os.environ.get("TUTORBOARD_COURSES")
try:
    with open(os.path.join(home, "atlas.json"), "w", encoding="utf-8") as fh:
        json.dump({"families": [
            {"id": "research", "name": "Research", "blurb": "Papers."},
            {"id": "vendor", "name": "Vendor", "blurb": "Pulled, not written.",
             "vendor": True},
        ]}, fh)
    write(home, "research/PSYCH-ASR/tutorboard.json", '{"name": "PSYCH-ASR"}')
    write(home, "research/PSYCH-ASR/psych_asr/grade.py",
          "def grade(a, b):\n" + BODY + "\n")
    # Somebody else's repository, at a commit. No `tutorboard.json`, no `live/`,
    # nothing that has ever said it wants to be taught in.
    write(home, "vendor/colibri/src/engine.c",
          "int warm(void) {\n" + BODY + "\n}\n")
    write(home, "vendor/colibri/bin/coli-up",
          "#!/usr/bin/env bash\nwarm() {\n" + BODY + "\n}\n")
    write(home, "vendor/colibri/README.md", "# colibri\n" + BODY)
    # AND THE TRAP IN THE OTHER DIRECTION. A vendor tree carrying the marker
    # that makes a directory a workspace is still not one: the family decides,
    # and a file inside somebody else's repository is not this side's promise.
    write(home, "vendor/pretender/tutorboard.json", '{"name": "Pretender"}')
    write(home, "vendor/pretender/thing.py", "def thing():\n" + BODY + "\n")
    os.makedirs(os.path.join(home, "vendor", "unpulled"), exist_ok=True)

    os.environ["TUTORBOARD_COURSES"] = home
    atlas.forget()
    walk._cache.clear()
    mapping._cache.clear()

    ids = [w["id"] for w in atlas.workspaces()]
    trees = {t["id"]: t for t in atlas.trees()}
    check("a vendor tree is not a workspace, and the family is still skipped",
          ids == ["research/PSYCH-ASR"])
    check("and a marker file inside somebody else's repository does not make "
          "one -- the family decides, not a file in the tree",
          "vendor/pretender" not in ids)
    check("but the trees are listed, which is the half that was missing",
          sorted(trees) == ["vendor/colibri", "vendor/pretender"])
    check("a submodule nobody has pulled is an empty directory, not a tree",
          "vendor/unpulled" not in trees)
    check("and a tree comes back shaped like a workspace, so a caller that "
          "wants a name and a root does not care which list it came from",
          set(["id", "family", "family_name", "dir", "root"])
          <= set(trees["vendor/colibri"]))

    # WALKABLE. The same walk, over a root nobody is graded on.
    names = [u["name"] for u in walk.units(trees["vendor/colibri"]["root"])]
    check("a vendor tree's source is walkable: tracing is not grading",
          "src/engine.c" in names and "bin/coli-up" in names)
    check("and its prose is refused there for the same reason it is anywhere",
          "README.md" not in names)
    chosen, unknown = walk.resolve(trees["vendor/colibri"]["root"],
                                   ["bin/coli-up::warm"])
    check("and a symbol inside it is carried once the file really defines it",
          [u["name"] for u in chosen] == ["bin/coli-up::warm"] and not unknown)

    # DIAGRAMMABLE. `map.shape` takes a root and does not ask whose it is.
    drawn = mapping.shape(trees["vendor/colibri"]["root"])
    check("and a vendor tree has a diagram, which is what it is there for",
          drawn and sorted(n["name"] for n in drawn["nodes"]) == ["bin", "src"])

    # A NAME FROM A REQUEST IS LOOKED UP, NEVER CONSTRUCTED. Same rule as
    # `atlas.find`, `walk.resolve` and `reading.find`: a miss is a miss.
    check("a tree is found by the name discovery gave it",
          (atlas.find_tree("vendor/colibri") or {})["id"] == "vendor/colibri")
    check("and by its bare directory name, which is how everything else is spelt",
          (atlas.find_tree("colibri") or {})["id"] == "vendor/colibri")
    for made_up in ("../../etc/passwd", "vendor", "vendor/nothing", "", None,
                    "research/PSYCH-ASR"):
        check("a tree name that matches nothing resolves to nothing: %r"
              % (made_up,), atlas.find_tree(made_up) is None)
    check("and a workspace is not reachable through the tree door either",
          atlas.find("vendor/colibri") is None)

    # -----------------------------------------------------------------------
    # AND THE SITTING ITSELF, WHICH IS THE HALF THAT WAS MISSING
    # -----------------------------------------------------------------------
    # *"A `trace` sitting over `vendor/colibri` is exactly the right shape and
    # it is currently impossible."* It was impossible because a walkthrough's
    # scope is resolved against the root of the workspace the board is SERVING,
    # and no vendor tree is under one of those.
    #
    # The expensive answer was to let a sitting be held over a foreign root, at
    # which point `Repo.root` stops being the single answer to "where are we".
    # This is the other one: the sitting is held in the workspace that is
    # READING the tree, and the tree is named IN THE SCOPE. So what has to be
    # true is one thing said three ways -- the scope reaches out, the sitting
    # does not, and the tree is never written to.
    ws = os.path.join(home, "research", "PSYCH-ASR")

    chosen, unknown = walk.resolve_any(
        ws, ["psych_asr/grade.py", "@vendor/colibri/bin/coli-up::warm"])
    check("a scope can name this workspace's own source and a vendor tree's "
          "in one list, which is what a trace held here over somebody else's "
          "code actually is",
          not unknown and [u["name"] for u in chosen]
          == ["psych_asr/grade.py", "@vendor/colibri/bin/coli-up::warm"])
    check("and the foreign one says which repository it is in, so whatever "
          "opens the file knows where to look",
          chosen[1]["tree"] == "vendor/colibri"
          and chosen[1]["root"] == trees["vendor/colibri"]["root"]
          and chosen[1]["path"] == "bin/coli-up"
          and not chosen[0].get("tree"))
    check("while the workspace's own resolver is untouched and still refuses "
          "a marked name, because one root is all it answers for",
          walk.resolve(ws, ["@vendor/colibri/bin/coli-up"])[1]
          == ["@vendor/colibri/bin/coli-up"])

    # A NAME FROM A REQUEST IS LOOKED UP, NEVER CONSTRUCTED -- on both halves of
    # it. The marker is not a licence to reach anywhere: the tree is found in
    # what `atlas.trees()` listed, and the rest is found in what that tree's own
    # walk listed.
    for made_up in ("@vendor/nothing/x.py", "@vendor/colibri/nope.py",
                    "@vendor/colibri/bin/coli-up::missing",
                    "@vendor/colibri/README.md", "@vendor/colibri",
                    "@research/PSYCH-ASR/psych_asr/grade.py",
                    "@vendor/../../etc/passwd", "@"):
        check("a scope that matches nothing is refused by name: %r" % (made_up,),
              walk.resolve_any(ws, [made_up])[1] == [made_up])

    st = {"walk": ["@vendor/colibri/bin/coli-up::warm"]}
    check("the scope is re-resolved on the way out, the way a local one is",
          [u["name"] for u in walk.scope(ws, st)]
          == ["@vendor/colibri/bin/coli-up::warm"])
    check("and the badge says whose code it is -- a label reading warm alone "
          "would not",
          walk.sitting_label(walk.scope(ws, st)) == "Walkthrough — colibri/warm")

    # WHAT THE TUTOR IS TOLD, and the one thing it could get badly wrong.
    walk_repo = course_repo.Repo(ws)
    live_st = walk_repo.state()
    live_st.update({"session": "walk",
                    "walk": ["@vendor/colibri/bin/coli-up::warm"]})
    json.dump(live_st, open(walk_repo.state_path, "w"))
    line = sense.session_sense(walk_repo)
    check("the tutor is told this is somebody else's code",
          "NOT THIS REPOSITORY'S CODE" in line and "vendor/colibri" in line)
    check("and that a defect found in it is not work to be done",
          "change nothing in it" in line and "not to be" not in line
          and "do not write a patch" in line)
    check("and which workspace the sitting belongs to, because that is where "
          "the cards are filed",
          "The sitting is PSYCH-ASR's" in line)
    live_st["walk"] = ["psych_asr/grade.py"]
    json.dump(live_st, open(walk_repo.state_path, "w"))
    check("and a sitting over this repository's own source is told none of it",
          "NOT THIS REPOSITORY'S CODE" not in sense.session_sense(walk_repo))

    # THE TREE IS NEVER WRITTEN TO. Not by opening the sitting, not by drawing
    # it, not by anything: it is somebody else's repository at a commit.
    def _shape_of(root):
        out = []
        for here, dirs, files in os.walk(root):
            for name in sorted(files):
                path = os.path.join(here, name)
                out.append((os.path.relpath(path, root),
                            os.path.getsize(path), os.stat(path).st_mtime))
        return sorted(out)

    tree_root = trees["vendor/colibri"]["root"]
    before = _shape_of(tree_root)

    # --- through the real handler -------------------------------------------
    worker = tikz.TikzWorker(walk_repo)
    worker.start()
    board = hub.Hub(walk_repo, worker)
    board.payload = json.dumps(board.build())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler.Handler)
    httpd.daemon_threads = True
    httpd.repo = walk_repo
    httpd.hub = board
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    BASE = "http://127.0.0.1:%d" % port

    def post(path, body):
        req = urllib.request.Request(BASE + path, method="POST",
                                     data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def get(path):
        try:
            with urllib.request.urlopen(BASE + path, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    try:
        status, body = post("/session", {
            "session": "walk", "over": ["@vendor/colibri/bin/coli-up::warm"]})
        check("a trace over a vendor tree opens, which is the whole of this item",
              status == 200 and body.get("ok"))
        opened = walk_repo.state()
        check("and it is a sitting in the workspace that is reading the tree, "
              "not a board in somebody else's repository",
              opened.get("session") == "walk"
              and opened.get("walk") == ["@vendor/colibri/bin/coli-up::warm"]
              and not os.path.isdir(os.path.join(tree_root, "live")))
        check("the sitting's own files are this workspace's",
              os.path.isdir(os.path.join(ws, "live", "cards")))
        status, body = post("/session", {
            "session": "walk", "over": ["@vendor/nothing/x.py"]})
        check("a tree this repository does not pull is refused by name",
              status == 400 and body.get("unknown") == ["@vendor/nothing/x.py"])

        # THE DIAGRAM OF A TREE NEEDS A SURFACE, and it is the board's own map
        # rather than a second renderer: `map.inside` already answers with a
        # picture that is not the workspace's, and a foreign repository is
        # exactly that shape.
        status, drawn = get("/map/tree/vendor/colibri")
        check("a tree has a picture, on the surface that already draws one",
              status == 200 and drawn.get("ok")
              and sorted(n["name"] for n in drawn["nodes"]) == ["bin", "src"])
        check("and the picture says whose it is, so a scope taken off it is "
              "spelt with the tree in it",
              drawn.get("tree") == "vendor/colibri"
              and drawn.get("depth") == "tree")
        check("and says the rule where somebody is looking at it",
              "pulled and not written here" in (drawn.get("why") or ""))
        check("nothing on it is working, next or done: none of it is work this "
              "side has taken on",
              all(n["status"] == "unknown" for n in drawn["nodes"])
              and not [n for n in drawn["nodes"] if n["steps"]])
        status, deeper = get("/map/tree/vendor/colibri/inside/bin")
        check("a box of it opens the way a box of this repository does",
              status == 200 and deeper.get("tree") == "vendor/colibri"
              and [n["name"] for n in deeper["nodes"]] == ["coli-up"])
        for missed in ("/map/tree/vendor/nothing",
                       "/map/tree/research/PSYCH-ASR",
                       "/map/tree/vendor/colibri/inside/nowhere"):
            check("a name that matches nothing is a 404 rather than a picture: "
                  "%s" % missed, get(missed)[0] == 404)
    finally:
        httpd.shutdown()

    check("and after all of it the tree is byte for byte what it was: it is "
          "read, drawn and traced, and never written to",
          _shape_of(tree_root) == before)
finally:
    if was is None:
        os.environ.pop("TUTORBOARD_COURSES", None)
    else:
        os.environ["TUTORBOARD_COURSES"] = was
    atlas.forget()
    walk._cache.clear()
    mapping._cache.clear()
    shutil.rmtree(home, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a walkthrough is held over machinery that exists, and a stance is a sitting's")
