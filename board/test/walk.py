#!/usr/bin/env python3
"""A walkthrough: a lesson about machinery that already exists.

Every other sitting on this board ends in the student producing something new.
In a working project most of what has to be understood was written months ago,
and a tutor with nowhere to put that does the only thing it can -- there is a
card in PSYCH-ASR that proves it, invented arithmetic on fictional numbers in a
repository whose owner wanted an algorithm on disk explained to him.

So: the scope is a file in this repository, checked before it reaches
anything. What is guarded here is that nothing invented reaches the filesystem
or the prompt, and that who writes the code is the session's mode alone.
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
# A walkthrough is a method the tutor picks in teach mode, not a sitting kind: a
# state still saying `session: walk` reads as a lecture.
try:
    json.dump({"name": "PSYCH-ASR"},
              open(os.path.join(proj, "tutorboard.json"), "w"))
    r = course_repo.Repo(proj)
    st = r.state()
    st.update({"session": "walk",
               "walk": ["psych_asr/evaluate/grade.py::grade"]})
    json.dump(st, open(r.state_path, "w"))
    line = sense.session_sense(r)
    check("a legacy walk sitting reads as a lecture in teach mode",
          "WALKTHROUGH SITTING" not in line and "IN TEACH MODE" in line
          and "a walkthrough of code that already exists" in line)
finally:
    pass

# --- the mode is the session's, and tutorboard.json says nothing about it ------
teach_repo = tempfile.mkdtemp(prefix="tutor-walk-teach-")
do_repo = tempfile.mkdtemp(prefix="tutor-walk-do-")
try:
    json.dump({"name": "PSYCH-ASR"},
              open(os.path.join(teach_repo, "tutorboard.json"), "w"))
    json.dump({"name": "TRD-EHR", "stance": "do"},
              open(os.path.join(do_repo, "tutorboard.json"), "w"))
    write(teach_repo, "psych_asr/grid.py", "def sweep():\n" + BODY + "\n")
    write(do_repo, "pipeline/confound.py", "def overlap():\n" + BODY + "\n")

    rd = course_repo.Repo(do_repo)
    st = rd.state()
    st.update({"session": "lecture", "chapter": "the propensity model"})
    json.dump(st, open(rd.state_path, "w"))
    line = sense.session_sense(rd)
    check("a tutorboard.json stance of do is ignored: the session teaches",
          "IN TEACH MODE" in line and "IN DO MODE" not in line)

    rt = course_repo.Repo(teach_repo)
    st = rt.state()
    st.update({"session": "lecture", "chapter": "the grid sweep", "mode": "do"})
    json.dump(st, open(rt.state_path, "w"))
    line = sense.session_sense(rt)
    check("a session in do mode is told to write the code",
          "IN DO MODE" in line and "you write the code yourself" in line)
    line = brief.briefing(rt, sense)
    check("the briefing names the mode", "mode: do" in line)
    st.pop("mode")
    json.dump(st, open(rt.state_path, "w"))
    line = brief.briefing(rt, sense)
    check("and teach when the session says nothing", "mode: teach" in line)
    check("a workspace that names no check gets no check line",
          "\ncheck: " not in line)
    json.dump({"name": "PSYCH-ASR", "check": "uv run --extra test python -m pytest tests -q"},
              open(os.path.join(teach_repo, "tutorboard.json"), "w"))
    line = brief.briefing(rt, sense)
    check("the briefing names the workspace's check, to run before a push",
          "check: uv run --extra test python -m pytest tests -q" in line
          and "before a push" in line)
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

        status, _ = post("/session", {
            "session": "walk", "over": ["psych_asr.evaluate.grade.grade"]})
        check("the board no longer opens a walkthrough sitting", status == 400)
        check("and the lesson it would have interrupted is untouched",
              not archive.list_archive(repo))
        status, _ = post("/session", {"session": "lecture", "stance": "do"})
        check("a stance sent with a sitting is ignored",
              status == 200 and not repo.state().get("stance")
              and "IN DO MODE" not in sense.session_sense(repo))
    finally:
        httpd.shutdown()
finally:
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(proj, ignore_errors=True)

# ---------------------------------------------------------------------------
# A VENDOR TREE IS WALKABLE, AND IS STILL NOT A WORKSPACE
# ---------------------------------------------------------------------------
# The vendor family is skipped because nothing in it is the person's to be
# GRADED on. The ask
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

    walk_repo = course_repo.Repo(ws)

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
        check("a walkthrough is no longer a sitting the board opens, over a "
              "tree or not", status == 400)
        check("and nothing was written into the tree",
              not os.path.isdir(os.path.join(tree_root, "live")))

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

# --- the fence: no code walker looks inside a directory in fenced.NEVER -------
from tutorboard import fenced                                # noqa: E402
from tutorboard.course import symbols                        # noqa: E402

fence = tempfile.mkdtemp(prefix="tutor-walk-fence-")
try:
    for rel in ("pkg/ok.py", "stage1/run.py", "raw/x.py", "phi/y.py",
                "PHI/z.py", "pkg/Audio/w.py"):
        write(fence, rel, "def f():\n" + BODY + "\n    return 1\n")
    walk._cache.clear()
    check("in_fence matches any lower-cased component, and nothing else",
          fenced.in_fence("a/Stage1/x.py") and fenced.in_fence("phi")
          and fenced.in_fence("a\\raw\\b.py")
          and not fenced.in_fence("pkg/ok.py") and not fenced.in_fence("raw.py")
          and not fenced.in_fence(""))
    check("walk.units lists only the file outside every fence",
          [u["path"] for u in walk.units(fence)] == ["pkg/ok.py"])
    typed = ["stage1/run.py::f", "stage1/run.py", "stage1.run.f", "phi/y.py",
             "raw/x.py::f", "PHI/z.py"]
    chosen, unknown = walk.resolve(fence, typed)
    check("walk.resolve refuses a typed path through the fence",
          chosen == [] and unknown == typed)
    chosen, unknown = walk.resolve(fence, ["pkg/ok.py::f"])
    check("and still resolves the path beside it",
          [u["name"] for u in chosen] == ["pkg/ok.py::f"] and unknown == [])
    check("symbols.of opens no fenced file, even when handed one",
          symbols.of(fence, "phi/y.py")["defines"] == []
          and symbols.of(fence, "stage1/run.py")["defines"] == []
          and symbols.of(fence, "pkg/ok.py")["defines"] != []
          and symbols.exact(fence, "raw/x.py") is False)
finally:
    walk._cache.clear()
    shutil.rmtree(fence, ignore_errors=True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    sys.exit(1)
print("a walkthrough is held over machinery that exists, and a stance is a sitting's")
