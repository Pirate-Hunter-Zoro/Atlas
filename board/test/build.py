#!/usr/bin/env python3
"""`board build <file>`: one builder, output beside the source.

A beamer deck and an article (with the subject's own `latex/coursemacros.sty`)
through pdflatex; a Markdown document with figures in a sibling directory
through pandoc to a .docx that carries every figure it names. A figure that
did not arrive fails the build, a figure that will not sit on the page fails
it under --strict, and a missing pandoc or PDF engine is named.
"""

import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tutorboard import build, tex  # noqa: E402

BOARD = os.path.join(ROOT, "bin", "board")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("ok   " + name)
    else:
        fails.append(name)
        print("FAIL " + name + (("\n     " + detail.replace("\n", "\n     "))
                                if detail else ""))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def png(path, shade):
    """A real 8x8 grey PNG; pandoc and pdflatex both refuse a fake one."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    def chunk(kind, data):
        body = kind + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xffffffff))
    raw = b"".join(b"\x00" + bytes([shade]) * 8 for _ in range(8))
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n"
                 + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 0, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(raw))
                 + chunk(b"IEND", b""))


def media(docx):
    with zipfile.ZipFile(docx) as z:
        return sorted(n for n in z.namelist() if n.startswith("word/media/"))


def cli(*args, **kw):
    env = dict(os.environ)
    env.update(kw.get("env") or {})
    p = subprocess.run([sys.executable, BOARD, "build"] + list(args),
                       cwd=kw.get("cwd"), env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=600)
    return p.returncode, p.stdout.decode("utf-8", "replace")


HAVE_TEX = tex.have_tex()
HAVE_PANDOC = bool(shutil.which(build.pandoc_bin()))

DECK = r"""\documentclass[aspectratio=169]{beamer}
\title{A deck}
\begin{document}
\begin{frame}\titlepage\end{frame}
\begin{frame}{One}\tableofcontents Content.\end{frame}
\end{document}
"""

ARTICLE = r"""%% \documentclass{beamer} in a comment is not the class
\documentclass{article}
\usepackage{coursemacros}
\begin{document}
\section{One}\label{s:one}
The space $\Topo$ is compact; see Section~\ref{s:one}.
\end{document}
"""

MACROS = r"""\ProvidesPackage{coursemacros}
\newcommand{\Topo}{\mathcal{T}}
"""

tmp = tempfile.mkdtemp(prefix="tutor-build-")
try:
    atlas = os.path.join(tmp, "Atlas")
    os.makedirs(os.path.join(atlas, ".git"))      # the repository top

    # ---- detection and the environment, with no compiler ------------------
    subj = os.path.join(atlas, "courses", "Topology")
    deck = os.path.join(subj, "docs", "deck", "deck.tex")
    art = os.path.join(subj, "chapters", "ch01", "homework", "ch01-homework.tex")
    write(deck, DECK)
    write(art, ARTICLE)
    write(os.path.join(subj, "latex", "coursemacros.sty"), MACROS)
    check("a beamer document is a deck", build.tex_kind(deck) == "beamer")
    check("and anything else an article, even with beamer in a comment",
          build.tex_kind(art) == "article")
    check("the subject is the directory under courses/",
          build.subject_of(art) == subj)
    inputs = build.tex_env_for(art)["TEXINPUTS"].split(os.pathsep)
    check("TEXINPUTS holds the subject's latex/ and then the board's tex/",
          inputs[:2] == [os.path.join(subj, "latex"), os.path.join(ROOT, "tex")],
          repr(inputs))

    # ---- .tex ---------------------------------------------------------------
    if not HAVE_TEX:
        print("skip the .tex builds: no LaTeX on this machine")
        rec = build.build(deck)
        check("with no LaTeX the failure says so by name",
              not rec["ok"] and "pdflatex" in rec["detail"])
    else:
        write(os.path.join(subj, "docs", "deck", "deck.bbl"), "kept")
        rec = build.build(deck)
        stem = os.path.splitext(deck)[0]
        check("a beamer deck builds beside its source",
              rec["ok"] and rec["built"] == [stem + ".pdf"]
              and os.path.isfile(stem + ".pdf"), rec["detail"])
        check("and says it is a deck", rec["kind"] == "beamer"
              and "beamer" in rec["detail"])
        left = sorted(os.listdir(os.path.dirname(deck)))
        check("its scratch files go on success, and a file it did not write stays",
              left == ["deck.bbl", "deck.pdf", "deck.tex"], repr(left))

        rec = build.build(art)
        stem = os.path.splitext(art)[0]
        check("an article using the subject's coursemacros builds",
              rec["ok"] and os.path.isfile(stem + ".pdf")
              and rec["kind"] == "article", rec["detail"])
        check("twice at least, so references settle", "2 pdflatex runs" in rec["detail"]
              or "3 pdflatex runs" in rec["detail"], rec["detail"])

        rec = build.build(art, keep_aux=True)
        check("--keep-aux keeps the .aux and nothing else",
              rec["ok"] and os.path.isfile(stem + ".aux")
              and not os.path.exists(stem + ".log"))

        write(art, ARTICLE.replace(r"\end{document}", "\\nosuchmacro\n\\end{document}"))
        rec = build.build(art)
        check("a LaTeX error fails and names the error and its line",
              not rec["ok"] and "Undefined control sequence" in rec["detail"]
              and "l." in rec["detail"], rec["detail"])
        check("and the log stays to read", os.path.isfile(stem + ".log"))

        code, out = cli(os.path.relpath(deck, subj), cwd=subj)
        check("`board build` takes a path relative to where it is run",
              code == 0 and out.strip().endswith("deck.pdf"), out)

    # ---- .md ----------------------------------------------------------------
    proj = os.path.join(atlas, "projects", "Paper")
    md = os.path.join(proj, "paper", "manuscript.md")
    png(os.path.join(proj, "figs", "a.png"), 40)
    png(os.path.join(proj, "figs", "b.png"), 200)
    write(md, "# Results\n\n"
              "![](../figs/a.png){width=3in}\n\n"
              "Text.\n\n"
              "![](../figs/b.png){width=2in} ![](../figs/a.png){width=2in}\n")
    if not HAVE_PANDOC:
        print("skip the .md builds: no pandoc on this machine")
    else:
        rec = build.build(md, formats=["docx"])
        docx = os.path.splitext(md)[0] + ".docx"
        check("a .md with figures in a sibling directory builds a .docx beside it",
              rec["ok"] and rec["built"] == [docx], rec["detail"])
        check("whose image count equals its distinct image references",
              len(media(docx)) == len(build._image_targets(open(md).read())) == 2,
              repr(media(docx)))

        sec = os.path.join(proj, "paper", "parts", "results.md")
        write(sec, "![](../figs/a.png){width=3in}\n")
        rec = build.build(sec, formats=["docx"])
        check("a section's paper-relative figure resolves from a directory above it",
              rec["ok"] and len(media(os.path.splitext(sec)[0] + ".docx")) == 1,
              rec["detail"])

        png(os.path.join(proj, "exports", "results", "c.png"), 120)
        exp = os.path.join(proj, "paper", "exported.md")
        write(exp, "![](../results/c.png){width=3in}\n")
        rec = build.build(exp, formats=["docx"])
        out = os.path.splitext(exp)[0] + ".docx"
        with zipfile.ZipFile(out) as z:
            body = z.read("word/document.xml").decode("utf-8")
        check("a figure under results/ is found at its exports/ copy",
              rec["ok"] and len(media(out)) == 1, rec["detail"])
        check("and the .docx names it relative to the document, never by an "
              "absolute path", tmp not in body
              and "../exports/results/c.png" in body)

        lost = os.path.join(proj, "paper", "lost.md")
        write(lost, "![](../figs/missing.png){width=3in}\n")
        rec = build.build(lost, formats=["docx"])
        check("a figure that did not reach the .docx fails the build",
              not rec["ok"] and "did not reach" in rec["detail"], rec["detail"])

        wide = os.path.join(proj, "paper", "wide.md")
        write(wide, "![](../figs/a.png)\n")
        rec = build.build(wide, formats=["docx"])
        check("a figure with no width warns", rec["ok"]
              and "no width= attribute" in rec["detail"], rec["detail"])
        rec = build.build(wide, formats=["docx"], strict=True)
        check("and fails under --strict", not rec["ok"])

        # The styles: formats/ found from the source upward.
        fmts = os.path.join(proj, "formats")
        os.makedirs(fmts)
        with open(os.path.join(fmts, "journal.docx"), "wb") as fh:
            fh.write(subprocess.run([build.pandoc_bin(), "--print-default-data-file",
                                     "reference.docx"],
                                    stdout=subprocess.PIPE).stdout)
        ref, err = build.reference_docx_for(md)
        check("the reference .docx is the one in formats/ above the source",
              ref == os.path.join(fmts, "journal.docx") and err is None)
        rec = build.build(md, formats=["docx"])
        check("and the build names it", rec["ok"] and "journal.docx" in rec["detail"])
        shutil.copy(os.path.join(fmts, "journal.docx"), os.path.join(fmts, "other.docx"))
        rec = build.build(md, formats=["docx"])
        check("two in formats/ is an error, not a guess",
              not rec["ok"] and "more than one reference document" in rec["detail"])
        os.remove(os.path.join(fmts, "other.docx"))

        code, out = cli(md, "--format", "docx", "--strict")
        check("`board build x.md --format docx --strict` exits 0 on a clean document",
              code == 0 and out.strip().endswith("manuscript.docx"), out)
        code, out = cli(lost, "--format", "docx")
        check("and 1 on a lost figure", code == 1, out)

        if build.pdf_engine_found() and HAVE_TEX:
            rec = build.build(md, formats=["pdf"])
            check("a .pdf builds through the PDF engine and pdf_fit.lua",
                  rec["ok"] and os.path.isfile(os.path.splitext(md)[0] + ".pdf"),
                  rec["detail"])

    code, out = cli(md, "--format", "docx",
                    env={"PAPER_PANDOC_BIN": os.path.join(tmp, "no-pandoc")})
    check("a missing pandoc is named", code == 1 and "pandoc did not run" in out, out)
    code, out = cli(md, "--format", "pdf",
                    env={"PAPER_PDF_ENGINE": "no-such-engine"})
    check("a missing PDF engine is named",
          code == 1 and "no-such-engine" in out, out)
    code, out = cli(os.path.join(tmp, "notes.txt"))
    check("a file that is not there is refused", code == 1, out)
    write(os.path.join(tmp, "notes.txt"), "x")
    code, out = cli(os.path.join(tmp, "notes.txt"))
    check("and so is one that is neither .tex nor .md",
          code == 1 and ".tex or a .md" in out, out)
    code, out = cli()
    check("no file is a usage error", code == 2, out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
print("%d FAILURES" % len(fails) if fails
      else "one builder, and what it builds is beside what it was built from")
sys.exit(1 if fails else 0)
