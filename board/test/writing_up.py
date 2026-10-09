#!/usr/bin/env python3
"""`board writeup`: every agreed answer in any teach session, typeset and built.

    python3 test/writing_up.py

Everything runs in a temp Atlas (`TUTORBOARD_COURSES`) with its own git
repository and a temp trash. Nothing touches the real `sessions/`.

  * An unbound session refuses; bound to a libr-local-llm copy, two answers
    make `docs/<session-slug>/writeup.tex` from the one template and a
    writeup.pdf holding both. The doc.json lists the session, the sent page is
    filed into handwritten/, and a fenced code block is set verbatim.
  * A Galois copy whose session names chapter 7 writes into
    `chapters/ch07-.../homework/ch07-homework.tex` in place, region by region,
    with doc.json written beside it; `board writeup status` reports it,
    and End commits the set.
  * A build failure is in the payload the board's banner paints, LaTeX error
    and all.
  * An Algo-Solutions teach brief names `board writeup`; a do brief carries no
    write-up rule.
  * The old scaffold is gone: one template, no course templates.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DIR = os.path.dirname(HERE)
ATLAS = os.path.dirname(BOARD_DIR)
BOARD = os.path.join(BOARD_DIR, "bin", "board")
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


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


base = os.path.realpath(tempfile.mkdtemp(prefix="tutor-writeup-"))
trash = os.path.realpath(tempfile.mkdtemp(prefix="tutor-writeup-trash-"))
os.environ["TUTORBOARD_COURSES"] = base
os.environ["TUTORBOARD_TRASH"] = trash
os.environ.pop("TUTORBOARD_SESSION", None)
os.environ.pop("TUTORBOARD_TURN", None)
ENV = dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
os.environ.update(ENV)

from tutorboard import artifacts, brief, sense, sessions, tex     # noqa: E402
from tutorboard.course import homework                            # noqa: E402

HAVE_TEX = tex.have_tex()
HAVE_TEXT = bool(shutil.which("pdftotext"))


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=base, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True).stdout.strip()


def board(args, session=None, stdin=""):
    env = dict(os.environ)
    env.pop("TUTORBOARD_SESSION", None)
    if session:
        env["TUTORBOARD_SESSION"] = session
    p = subprocess.run([sys.executable, BOARD] + list(args), cwd=base, env=env,
                       input=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, timeout=300)
    return p.returncode, p.stdout


def pdf_text(pdf):
    if not HAVE_TEXT:
        return ""
    return subprocess.run(["pdftotext", pdf, "-"], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, universal_newlines=True).stdout


def subject_dir(slug):
    """Where a subject lives in this checkout: its parent and directory."""
    for parent in ("courses", "projects"):
        d = os.path.join(ATLAS, parent, slug)
        if os.path.isdir(d):
            return parent, d
    return None, None


def sent_page(session_dir, tid, data=b"\x89PNG\r\n\x1a\nfake"):
    """A page the student sent: answers/<tid>-r1.png and its turn."""
    write(os.path.join(session_dir, "answers", tid + "-r1.png"), data)
    with open(os.path.join(session_dir, "turns.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": tid, "rev": 1, "kind": "ink", "t": 1.0,
                             "png": "/answers/%s-r1.png" % tid}) + "\n")


try:
    git("init", "-q", "-b", "main")
    write(os.path.join(base, ".gitignore"),
          "/sessions/\n.ink/\nlive/\n*.pdf\n*.aux\n*.log\n")

    # --- the fixtures: copies of three real subjects -------------------------
    _, llm_src = subject_dir("libr-local-llm")
    llm = os.path.join(base, "projects", "libr-local-llm")
    write(os.path.join(llm, "tutorboard.json"),
          read(os.path.join(llm_src, "tutorboard.json")))

    _, gal_src = subject_dir("Galois-Theory")
    gal = os.path.join(base, "courses", "Galois-Theory")
    ch07 = glob.glob(os.path.join(gal_src, "chapters", "ch07-*"))[0]
    ch07_rel = os.path.relpath(ch07, gal_src)
    shutil.copytree(os.path.join(gal_src, "latex"), os.path.join(gal, "latex"))
    shutil.copyfile(os.path.join(gal_src, "chapters.tsv"), os.path.join(gal, "chapters.tsv"))
    shutil.copyfile(os.path.join(gal_src, "tutorboard.json"),
                    os.path.join(gal, "tutorboard.json"))
    hw_src = os.path.join(ch07, "homework", "ch07-homework.tex")
    hw_tex = os.path.join(gal, ch07_rel, "homework", "ch07-homework.tex")
    write(hw_tex, read(hw_src))
    # A second set, so the session's title is what picks ch07.
    write(os.path.join(gal, "chapters", "ch05-tests", "homework", "ch05-homework.tex"),
          read(hw_src))

    algo_parent, algo_src = subject_dir("Algo-Solutions")
    algo = os.path.join(base, algo_parent or "projects", "Algo-Solutions")
    write(os.path.join(algo, "tutorboard.json"),
          read(os.path.join(algo_src, "tutorboard.json")) if algo_src
          else '{"name": "Algo Solutions", "phi": false}')
    git("add", "-A")
    git("commit", "-q", "-m", "fixture")

    # --- one template, and nothing else ---------------------------------------
    check("board/tex/writeup.tex.in is the one template",
          os.path.isfile(homework.TEMPLATE)
          and not hasattr(homework, "SCAFFOLD") and not hasattr(homework, "PLAIN_PREAMBLE")
          and not hasattr(homework, "scaffold"))
    check("no course keeps templates of its own",
          not glob.glob(os.path.join(ATLAS, "courses", "*", "latex", "templates")))
    body = homework.render("A & B_1", "Me")
    check("render fills the title and author, escaped",
          "\\title{A \\& B\\_1}" in body and "\\author{Me}" in body and "@@" not in body)
    check("and uses coursemacros only where the subject has them",
          "\\IfFileExists{coursemacros.sty}{\\usepackage{coursemacros}}" in body)

    # --- an unbound session refuses ------------------------------------------
    s1 = sessions.new("Colibri warmth", base=base)
    d1 = sessions.path(s1["id"], base)
    code, out = board(["writeup", "add", "1"], d1, "Q\n---\nA\n")
    check("an unbound session refuses, and says to bind first",
          code != 0 and "board bind" in out and not os.path.isdir(os.path.join(llm, "docs")),
          out)

    # --- libr-local-llm: two answers, one writeup.pdf ------------------------
    sessions.bind(s1["id"], "projects/libr-local-llm", base=base)
    sent_page(d1, "t0001")
    code, out = board(["writeup", "add", "warm-pool"], d1,
                      "Why is the warm pool two jobs?\n---\n"
                      "Because two generations \\emph{overlap}: $n = 2$.\n"
                      "```python\ndef warm(n):\n\treturn [spawn(i) for i in range(n)]  # 100% & $x_1\n```\n")
    wdir = os.path.join(llm, "docs", "colibri-warmth")
    wtex = os.path.join(wdir, "writeup.tex")
    check("the first add makes docs/<session-slug>/writeup.tex",
          os.path.isfile(wtex) and "started docs/colibri-warmth/writeup.tex" in out, out)
    doc = artifacts.read(wdir) or {}
    check("its doc.json names writeup.tex and lists the session",
          doc.get("source") == "writeup.tex" and doc.get("sessions") == [s1["id"]], doc)
    rec = sessions.get(s1["id"], base)
    check("session.json's writeup is that source",
          rec["writeup"] == "projects/libr-local-llm/docs/colibri-warmth/writeup.tex", rec)
    check("the sent page is filed into handwritten/",
          os.path.isfile(os.path.join(wdir, "handwritten", "colibri-warmth-warm-pool.png")))
    text = read(wtex)
    check("the code block is set verbatim, its tab expanded, nothing escaped",
          "\\begin{verbatim}\ndef warm(n):\n    return [spawn(i) for i in range(n)]"
          "  # 100% & $x_1\n\\end{verbatim}" in text, text)
    check("and no shell-escape package is anywhere", "minted" not in text)

    code, out = board(["writeup", "add", "fit"], d1,
                      "Which tier fits the H100?\n---\nTier one, by $80 > 70$ GB.\n")
    pdf = os.path.join(wdir, "writeup.pdf")
    words = pdf_text(pdf)
    check("two answers produce a writeup.pdf with both",
          not HAVE_TEX or (code == 0 and os.path.isfile(pdf)
                           and (not HAVE_TEXT or ("warm pool two jobs" in words
                                                  and "Which tier fits" in words
                                                  and "def warm(n)" in words))),
          out + words[:400])
    check("the write-up reads done once built",
          not HAVE_TEX or artifacts.status(wdir) == "done", artifacts.status(wdir))
    code, out = board(["writeup", "add", "fit"], d1, "---\nTier one: $80 > 70$.\n")
    check("a second add on one label rewrites its region, nothing appended",
          "rewrote fit" in out and read(wtex).count("% ===== SOLUTION fit =====") == 1
          and "80 > 70$." in read(wtex), out)
    code, out = board(["writeup", "status"], d1)
    check("board writeup status names the write-up and what is written",
          code == 0 and "colibri-warmth" in out and "2 of 2 written up" in out, out)
    code, out = board(["writeup", "add", "../x"], d1, "---\nA\n")
    check("a label that is not a label is refused", code != 0 and "label" in out, out)

    # --- a build failure reaches the board's banner --------------------------
    code, out = board(["writeup", "add", "broken"], d1,
                      "A broken one\n---\n\\undefinedmacrohere\n")
    check("a failed build exits non-zero and prints the LaTeX error",
          not HAVE_TEX or (code != 0 and "BUILD FAILED" in out
                           and "Undefined control sequence" in out), out)
    from tutorboard.server import hub, tikz                        # noqa: E402
    repo = sessions.repo(s1["id"], base)
    data = hub.Hub(repo, tikz.TikzWorker(repo)).build()
    banner = (data.get("hw") or {}).get("build") or {}
    check("the payload carries the failure the banner paints, with its reason",
          not HAVE_TEX or (data.get("hw", {}).get("name") == "colibri-warmth"
                           and banner.get("ok") is False
                           and "Undefined control sequence" in banner.get("detail", "")),
          banner)
    code, out = board(["writeup", "add", "broken"], d1, "---\nFixed.\n")
    data = hub.Hub(repo, tikz.TikzWorker(repo)).build()
    check("and fixing it clears it",
          not HAVE_TEX or ((data.get("hw") or {}).get("build") or {}).get("ok") is True,
          out)

    # --- Galois: the course's own set, in place -------------------------------
    s2 = sessions.new("Ch 7 homework", base=base)
    d2 = sessions.path(s2["id"], base)
    sessions.bind(s2["id"], "courses/Galois-Theory", base=base)
    sent_page(d2, "t0001")
    before = read(hw_tex)
    code, out = board(["writeup", "add", "14"], d2,
                      "A statement the sheet already has.\n---\n"
                      "Since $3^2 = 2$ and $3^3 = 6$ modulo $7$, $3$ is a primitive root.\n")
    after = read(hw_tex)
    region = after[after.index("% ===== SOLUTION 14 ====="):
                   after.index("% ===== END SOLUTION 14 =====")]
    check("a Galois copy still writes into chapters/ch07-.../homework/ch07-homework.tex",
          code == 0 and "3$ is a primitive root" in region
          and "wrote 14 in %s/homework/ch07-homework.tex" % ch07_rel in out, out)
    check("in place: the statement the sheet has is kept, and nothing is appended",
          after.count("\\begin{problem}{14}") == 1 and "already has" not in after
          and len(after.splitlines()) == len(before.splitlines()))
    check("no docs/ write-up was made for a session on a set",
          not os.path.isdir(os.path.join(gal, "docs")))
    hw_dir = os.path.dirname(hw_tex)
    placed = artifacts.read(hw_dir) or {}
    check("doc.json is written in place, listing the session",
          placed.get("source") == "ch07-homework.tex"
          and placed.get("sessions") == [s2["id"]], placed)
    listed = [a for a in artifacts.list(gal) if a["dir"] == hw_dir]
    check("and it is listed as an in-place artifact",
          len(listed) == 1 and not listed[0]["own"], listed)
    check("the page is filed beside the set",
          os.path.isfile(os.path.join(hw_dir, "handwritten", "ch07-14.png")))
    code, out = board(["writeup", "status"], d2)
    check("board writeup status reports the set",
          code == 0 and "ch07" in out and "14     written up" in out, out)
    rec, ok, said = sessions.end(s2["id"], base=base)
    shown = git("show", "--stat", "--format=%s", "HEAD")
    check("End commits the set the session wrote into",
          ok and "ch07-homework.tex" in shown and "doc.json" in shown, said + shown)

    # --- the brief -------------------------------------------------------------
    s3 = sessions.new("Two pointers", base=base)
    sessions.bind(s3["id"], "%s/Algo-Solutions" % (algo_parent or "projects"), base=base)
    taught = brief.briefing(sessions.repo(s3["id"], base), sense)
    check("an Algo-Solutions teach brief names board writeup",
          "board writeup add <label>" in taught and "writeup: none yet" in taught)
    from tutorboard import mode as session_mode                    # noqa: E402
    session_mode.set_mode(sessions.repo(s3["id"], base), "do", "test")
    done = brief.briefing(sessions.repo(s3["id"], base), sense)
    check("a do brief carries no write-up rule",
          "mode: do" in done and sense.WRITEUP_SENSE not in done)
    walk = brief.briefing(sessions.repo(s1["id"], base), sense)
    check("and a teach session with a write-up has its debt on the brief",
          "writeup: colibri-warmth (docs/colibri-warmth/writeup.tex) -- 3 of 3 written up"
          in walk, [l for l in walk.splitlines() if l.startswith("writeup")])
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(trash, ignore_errors=True)

print()
if fails:
    print("%d FAILURES" % len(fails))
    sys.exit(1)
print("an agreed answer in any session is written up and built")
