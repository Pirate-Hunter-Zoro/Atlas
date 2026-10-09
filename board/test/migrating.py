#!/usr/bin/env python3
"""migrate-artifacts.py: existing documents become artifacts, their ink follows.

    python3 test/migrating.py

A temp Atlas with its own git repository, shaped like the real one at the
paths the script names: TRD-EHR's homework sets and sittings deck, its two
paper trees, PSYCH-ASR's and libr-local-llm's hand-made `docs/`, and two
courses' sets. Ink is seeded under each document's old library id.

  * --plan names every move, untrack, doc.json and key rename, and changes
    nothing on disk or in git.
  * --apply-tree moves the TRD-EHR trees into `docs/<slug>/` with doc.json,
    untracks their `.out` and built PDF, places doc.json in every hand-made
    tree and course set, and writes the key map.
  * --apply-ink renames the `.ink/` files by the map: the stroke count is
    unchanged, each moved document shows its old ink through the library,
    and a second run renames nothing.
  * The 2026-09-29 round on the manuscript still opens, `placed-*.json`
    byte for byte.
  * --rebuild builds every course writeup and the moved set beside its source
    (skipped where there is no pdflatex).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
SCRIPT = os.path.join(BOARD_DIR, "scripts", "migrate-artifacts.py")
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


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-migrating-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-migrating-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)

from tutorboard import artifacts, build, sessions                     # noqa: E402
from tutorboard.course import ledger, library                         # noqa: E402
from tutorboard.course import repo as course_repo                     # noqa: E402
from tutorboard.server.routes import writing                          # noqa: E402

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=base, env=ENV,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True).stdout.strip()


def run(*args):
    p = subprocess.run([sys.executable, SCRIPT] + list(args), cwd=base, env=ENV,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    return p.returncode, p.stdout


def snapshot():
    """Every path under the Atlas with its size and mtime, and git's view."""
    out = []
    for here, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != ".git"]
        for n in files:
            p = os.path.join(here, n)
            st = os.lstat(p)
            out.append((os.path.relpath(p, base), st.st_size, st.st_mtime_ns))
    return sorted(out), git("status", "--porcelain"), git("rev-parse", "HEAD")


ARTICLE = ("\\documentclass[11pt]{article}\n\\title{%s}\n\\begin{document}\n"
           "\\maketitle\nText.\n\\end{document}\n")
BEAMER = ("\\documentclass{beamer}\n\\title{%s}\n\\begin{document}\n"
          "\\begin{frame}{One}Slide.\\end{frame}\n\\end{document}\n")
PDF = b"%PDF-1.4\n% a fixture\n" + b"x" * 30000
PLACED = json.dumps({"ann": "doc/paper1-trd-prediction-manuscript/p1",
                     "box": [0.1, 0.2, 0.3, 0.4]}, indent=2) + "\n"

trd = os.path.join(base, "projects", "TRD-EHR")
psych = os.path.join(base, "projects", "PSYCH-ASR")
llm = os.path.join(base, "projects", "libr-local-llm")
galois = os.path.join(base, "courses", "Galois-Theory")
prob = os.path.join(base, "courses", "Probability")
map_path = os.path.join(base, "artifact-moves.json")

try:
    git("init", "-q")
    write(os.path.join(base, ".gitignore"), "/sessions/\n**/.ink/\n*.out\n"
          "/projects/*/docs/**/*.pdf\n/courses/**/*.pdf\n")
    write(os.path.join(trd, "homework", "knn-ksweep", "knn-ksweep.tex"),
          ARTICLE % "The KNN neighbour-count sweep")
    write(os.path.join(trd, "homework", "knn-ksweep", "knn-ksweep.pdf"), PDF)
    write(os.path.join(trd, "homework", "knn-ksweep", "handwritten",
                       "knn-ksweep-1.png"), b"\x89PNG fixture")
    write(os.path.join(trd, "homework", "retrieval-and-subgroups",
                       "retrieval-and-subgroups.tex"), ARTICLE % "Retrieval")
    deck = os.path.join(trd, "writeups", "deck-260925-0942")
    write(os.path.join(deck, "deck-260925-0942.tex"), BEAMER % "Predicting TRD")
    write(os.path.join(deck, "deck-260925-0942.out"), "")
    write(os.path.join(deck, ".gitignore"), "figures/\n*.pdf\n_brief.*\n")
    write(os.path.join(deck, "feedback", "2026-09-25-v1.md"), "# Feedback\n")
    p1 = os.path.join(trd, "paper1-trd-prediction")
    write(os.path.join(p1, "manuscript.md"), "# Predicting TRD\n\nText.\n")
    write(os.path.join(p1, "manuscript.pdf"), PDF)
    write(os.path.join(p1, "cover_letter.md"), "# Cover letter\n")
    rnd = os.path.join(p1, "feedback", "manuscript-2026-09-29-v1")
    write(rnd + ".md", "# Feedback on Predicting TRD\n")
    write(os.path.join(rnd, "placed-ce5b4dff5e1839e9.json"), PLACED)
    write(os.path.join(rnd, "items.json"), PLACED)
    write(os.path.join(trd, "paper2-counterfactual", "PAPER2_OUTLINE.md"),
          "# PAPER 2 -- PROJECT OUTLINE\n")
    write(os.path.join(trd, "phi", "secret-notes.tex"), ARTICLE % "PHI")
    write(os.path.join(psych, "docs", "stage1_pipeline_walkthrough.tex"),
          ARTICLE % "Stage 1")
    write(os.path.join(llm, "docs", "fleet_walkthrough.tex"), ARTICLE % "Fleet")
    write(os.path.join(llm, "docs", "deepseek-egress.md"), "# Egress\n")
    write(os.path.join(galois, "chapters", "ch07-splitting-fields", "homework",
                       "ch07-homework.tex"), ARTICLE % "Ch 7")
    write(os.path.join(galois, "chapters", "ch07-splitting-fields", "notes",
                       "ch07-notes.tex"), ARTICLE % "Ch 7 notes")
    write(os.path.join(prob, "homework", "hw02", "hw02.tex"), ARTICLE % "HW 2")
    write(os.path.join(prob, "homework", "hw02", "superseded-edition-10.tex"),
          ARTICLE % "HW 2, tenth edition")
    git("add", "-A")
    # Tracked before `*.out` was ignored, as the real one is.
    git("add", "-f", os.path.join(deck, "deck-260925-0942.out"))
    git("commit", "-qm", "fixture")

    # Ink on each document under the id the library gives it now, written
    # the way a bound session's reader saves it.
    sid = "20261008-090000"
    sess = os.path.join(base, "sessions", sid)
    write(os.path.join(sess, "session.json"),
          json.dumps({"id": sid, "subject": "projects/TRD-EHR"}))
    repo = course_repo.Repo(trd, session=sess, create=False)
    old = dict((d["rel"], d["id"]) for d in library.documents(trd))
    seeded = {
        "homework/knn-ksweep/knn-ksweep.pdf": 3,
        "homework/retrieval-and-subgroups/retrieval-and-subgroups.tex": 2,
        "writeups/deck-260925-0942/deck-260925-0942.tex": 5,
        "paper1-trd-prediction/manuscript.pdf": 1,
    }
    old_ids = {}
    for rel, n in seeded.items():
        ident = old[rel]
        old_ids[rel] = ident
        for page in (1, 2):
            key = "doc/%s/p%d" % (ident, page)
            write(writing.ann_path(repo, key),
                  json.dumps({"card": key, "strokes": [{"p": [[0, 0], [1, 1]]}] * n,
                              "sent": False}))
            write(writing.png_path(repo, key), b"\x89PNG ink")
        write(writing.gone_path(repo, "doc/%s/p1" % ident),
              json.dumps({"card": "doc/%s/p1" % ident, "strokes": [{"p": []}]}))
    ink_dir = os.path.join(trd, sessions.INK)
    strokes_before = sum(len(json.load(open(os.path.join(ink_dir, n)))["strokes"])
                         for n in os.listdir(ink_dir) if n.endswith(".json"))

    # ------------------------------------------------------------- --plan
    before = snapshot()
    code, out = run("--plan", "--atlas", base, "--map", map_path)
    check("--plan exits 0", code == 0, out)
    for line in ("move    projects/TRD-EHR/homework/knn-ksweep -> docs/knn-ksweep",
                 "move    projects/TRD-EHR/homework/retrieval-and-subgroups -> "
                 "docs/retrieval-and-subgroups",
                 "move    projects/TRD-EHR/writeups/deck-260925-0942 -> "
                 "docs/deck-260925-0942",
                 "untrack projects/TRD-EHR/homework/knn-ksweep/knn-ksweep.pdf",
                 "untrack projects/TRD-EHR/writeups/deck-260925-0942/"
                 "deck-260925-0942.out",
                 "place   projects/PSYCH-ASR/docs/doc.json",
                 "place   projects/libr-local-llm/docs/doc.json",
                 "place   projects/TRD-EHR/paper1-trd-prediction/doc.json",
                 "place   projects/TRD-EHR/paper2-counterfactual/doc.json",
                 "place   courses/Galois-Theory/chapters/ch07-splitting-fields/"
                 "homework/doc.json",
                 "place   courses/Probability/homework/hw02/doc.json  (source hw02.tex)",
                 "ink     projects/TRD-EHR: doc/%s/p* -> doc/knn-ksweep/p*"
                 % old_ids["homework/knn-ksweep/knn-ksweep.pdf"],
                 "ink     projects/TRD-EHR: doc/%s/p* -> doc/deck-260925-0942/p*"
                 % old_ids["writeups/deck-260925-0942/deck-260925-0942.tex"]):
        check("--plan lists: " + line.split("  (")[0], line in out, out)
    check("--plan renames no key whose id holds (the manuscript's)",
          old_ids["paper1-trd-prediction/manuscript.pdf"] not in out)
    check("--plan never names a fenced path", "phi" not in out.replace("PHI", ""), out)
    check("--plan changes nothing on disk or in git", snapshot() == before)
    check("--plan writes no map", not os.path.exists(map_path))

    # ------------------------------------------------------- --apply-tree
    code, out = run("--apply-tree", "--atlas", base, "--map", map_path)
    check("--apply-tree exits 0", code == 0, out)
    git("commit", "-qm", "apply-tree")
    files = set(git("ls-files").splitlines())
    check("the sets and the deck are tracked under docs/<slug>/",
          {"projects/TRD-EHR/docs/knn-ksweep/knn-ksweep.tex",
           "projects/TRD-EHR/docs/knn-ksweep/handwritten/knn-ksweep-1.png",
           "projects/TRD-EHR/docs/knn-ksweep/doc.json",
           "projects/TRD-EHR/docs/deck-260925-0942/deck-260925-0942.tex",
           "projects/TRD-EHR/docs/deck-260925-0942/feedback/2026-09-25-v1.md",
           "projects/TRD-EHR/docs/deck-260925-0942/.gitignore"} <= files, files)
    check("nothing is left under homework/ or writeups/",
          not [f for f in files if "/homework/" in f and "TRD-EHR" in f
               or "/writeups/" in f])
    check("the built PDF and the .out are untracked",
          not [f for f in files if f.endswith((".out", "knn-ksweep.pdf"))])
    log = git("log", "-1", "--name-status", "-M")
    check("git sees the moves as renames",
          "R100\tprojects/TRD-EHR/homework/knn-ksweep/knn-ksweep.tex" in log, log)
    rec = artifacts.read(os.path.join(trd, "docs", "knn-ksweep"))
    check("the moved set's doc.json names its source and title, asked by nobody",
          rec == {"title": "The KNN neighbour-count sweep",
                  "source": "knn-ksweep.tex", "sessions": [], "asked_at": None},
          rec)
    for d in (os.path.join(psych, "docs"), os.path.join(llm, "docs"),
              os.path.join(p1), os.path.join(trd, "paper2-counterfactual"),
              os.path.join(galois, "chapters", "ch07-splitting-fields", "homework"),
              os.path.join(prob, "homework", "hw02")):
        check("doc.json is placed in %s" % os.path.relpath(d, base),
              os.path.relpath(os.path.join(d, "doc.json"), base) in files)
    check("hw02's doc.json names the set named after it",
          artifacts.read(os.path.join(prob, "homework", "hw02"))["source"] == "hw02.tex")
    psych_arts = artifacts.list(psych)
    check("a doc.json in a hand-made docs/ is listed as that subject's artifact",
          [a["source"] for a in psych_arts] == ["stage1_pipeline_walkthrough.tex"]
          and psych_arts[0]["id"] == "docs-stage1-pipeline-walkthrough", psych_arts)
    library.forget()
    ids = dict((d["id"], d) for d in library.documents(llm))
    check("the other document in that docs/ keeps its legacy id",
          ids.get("docs-deepseek-egress", {}).get("group") == "legacy", sorted(ids))
    moves = json.load(open(map_path))
    check("the map records the three key renames and the set to rebuild",
          sorted((r["from"], r["to"]) for r in moves["ink"]) == sorted(
              [(old_ids["homework/knn-ksweep/knn-ksweep.pdf"], "knn-ksweep"),
               (old_ids["homework/retrieval-and-subgroups/retrieval-and-subgroups"
                        ".tex"], "retrieval-and-subgroups"),
               (old_ids["writeups/deck-260925-0942/deck-260925-0942.tex"],
                "deck-260925-0942")])
          and moves["rebuild"] == ["projects/TRD-EHR/docs/knn-ksweep/knn-ksweep.tex"],
          moves)
    code, out = run("--plan", "--atlas", base, "--map", map_path)
    check("a second --plan has no move and no key left",
          code == 0 and "0 moves" in out and "0 ink keys" in out, out)

    # -------------------------------------------------------- --apply-ink
    library.forget()
    gone_before = [d for d in library.documents(trd)
                   if d["id"] in ("knn-ksweep", "deck-260925-0942")
                   and library.ink(repo, d)]
    check("before --apply-ink the moved documents show no ink", not gone_before)
    code, out = run("--apply-ink", base, "--map", map_path)
    check("--apply-ink exits 0", code == 0, out)
    strokes_after = sum(len(json.load(open(os.path.join(ink_dir, n)))["strokes"])
                        for n in os.listdir(ink_dir) if n.endswith(".json"))
    check("the stroke count is unchanged (%d)" % strokes_after,
          strokes_after == strokes_before and strokes_before == 2 * (3 + 2 + 5 + 1))
    library.forget()
    docs = dict((d["id"], d) for d in library.documents(trd))
    for ident, rel in (("knn-ksweep", "homework/knn-ksweep/knn-ksweep.pdf"),
                       ("retrieval-and-subgroups", "homework/retrieval-and-subgroups/"
                        "retrieval-and-subgroups.tex"),
                       ("deck-260925-0942", "writeups/deck-260925-0942/"
                        "deck-260925-0942.tex")):
        got = library.ink(repo, docs[ident]) if ident in docs else {}
        n = seeded[rel]
        check("%s shows its old ink through the library" % ident,
              sorted(got) == ["doc/%s/p1" % ident, "doc/%s/p2" % ident]
              and all(len(v) == n for v in got.values()), got)
        check("and its pictures and burial moved with it",
              os.path.isfile(writing.png_path(repo, "doc/%s/p2" % ident))
              and writing.gone_of(repo, "doc/%s/p1" % ident))
    left = [n for n in os.listdir(ink_dir) if any(
        n.startswith("doc-" + old_ids[r][:20]) for r in seeded
        if "paper1" not in r)]
    check("no file is left under an old id", not left, left)
    man = docs.get(old_ids["paper1-trd-prediction/manuscript.pdf"])
    check("the manuscript, whose id held, keeps its ink",
          man and len(library.ink(repo, man)) == 2)
    code, out = run("--apply-ink", base, "--map", map_path)
    check("a second --apply-ink renames nothing",
          code == 0 and "0 file(s) renamed" in out, out)

    # ---------------------------------------------- the 2026-09-29 round
    check("the manuscript is a placed artifact with its old id",
          man and man["group"] == "artifact"
          and man["id"] == "paper1-trd-prediction-manuscript")
    check("its 2026-09-29 round is still listed",
          man and [n["name"] for n in library.notes(trd, man)]
          == ["manuscript-2026-09-29-v1.md"])
    check("and its ledger directory opens", man is not None and ledger.rounds(trd, man) is not None)
    with open(os.path.join(rnd, "placed-ce5b4dff5e1839e9.json")) as fh:
        check("placed-ce5b4dff5e1839e9.json is byte for byte what it was",
              fh.read() == PLACED)

    # ---------------------------------------------------------- --rebuild
    tex = build.tex_env_for(os.path.join(galois, "x.tex"))
    if not shutil.which("pdflatex", path=tex.get("PATH", "")):
        print("skip --rebuild: no pdflatex here")
    else:
        code, out = run("--rebuild", base, "--map", map_path)
        check("--rebuild exits 0", code == 0, out)
        for src in ("courses/Galois-Theory/chapters/ch07-splitting-fields/homework/"
                    "ch07-homework.tex",
                    "courses/Galois-Theory/chapters/ch07-splitting-fields/notes/"
                    "ch07-notes.tex",
                    "courses/Probability/homework/hw02/superseded-edition-10.tex",
                    "projects/TRD-EHR/docs/knn-ksweep/knn-ksweep.tex"):
            check("--rebuild leaves a PDF beside %s" % src,
                  os.path.isfile(os.path.join(base, src[:-4] + ".pdf")))
        check("and builds nothing outside the courses but the map's list",
              not os.path.isfile(os.path.join(psych, "docs",
                                              "stage1_pipeline_walkthrough.pdf")))
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("documents moved, their ink followed")
