"""`board build <file>`: the one builder for every document Atlas makes.

    .tex   pdflatex, beside the source. Beamer or article, detected from the
           document class. Twice, and a third time when the log says "Rerun".
    .md    pandoc, to .docx and also to .pdf when the PDF engine exists.

Output lands beside the source. Nothing else in board/ runs a compiler.

THE MARKDOWN HALF IS A COPY of Paper-Writer's converter
(`paperwriter/stages/building.py`, its figure gate, its `config` lookups and
`pdf_fit.lua`), copied rather than imported so the board does not depend on a
project. A document built here must be the document Paper-Writer would build:
the same flags, the same reference .docx, the same resource path.

Pandoc reports a figure it could not find as a warning and exits 0, so every
built .docx is opened and its images counted. A lost figure always fails the
build. A figure that will not sit on the page warns, and fails with `strict`.

Cluster-safe Python (3.7): `board` imports this.
"""

import os
import re
import shutil
import subprocess
import time
import zipfile

from pathlib import Path

from . import paths, tex

# ---------------------------------------------------------------------------
# Where a document lives
# ---------------------------------------------------------------------------

# A subject is a directory directly under one of these.
SUBJECT_PARENTS = ("courses", "projects")


def repo_top(path):
    """The nearest directory at or above `path` holding `.git`, else None."""
    d = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path))
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def subject_of(path):
    """The subject a file belongs to: a directory directly under `courses/`,
    `projects/`, ... Falling back to the nearest directory holding
    `tutorboard.json`, then to the file's own directory."""
    here = os.path.dirname(os.path.abspath(path))
    d = here
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            break
        if os.path.basename(parent) in SUBJECT_PARENTS:
            return d
        d = parent
    d = here
    while True:
        if os.path.isfile(os.path.join(d, "tutorboard.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return here
        d = parent


# ---------------------------------------------------------------------------
# LaTeX
# ---------------------------------------------------------------------------

TEX_TIMEOUT = 180

# What pdflatex writes beside a document, removed after a good build. `.bbl`
# is not here: it can be a hand-supplied file, and nothing here runs bibtex.
SCRATCH = (".aux", ".log", ".out", ".toc", ".nav", ".snm", ".vrb", ".lof",
           ".lot", ".fls", ".fdb_latexmk", ".synctex.gz")

NO_TEX = ("No LaTeX on this machine: pdflatex is in none of the places a TeX "
          "gets installed (`board doctor` lists them). Nothing is wrong with "
          "the document -- the source is written and safe, and it will "
          "typeset on a machine that has one.")

_CLASS_RE = re.compile(r"\\documentclass\s*(?:\[[^\]]*\])?\s*\{\s*([^}\s]+)\s*\}")


def document_class(path):
    """The `\\documentclass` a .tex names, or None. Comments are skipped."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    text = re.sub(r"(?<!\\)%.*", "", text)
    m = _CLASS_RE.search(text)
    return m.group(1) if m else None


def tex_kind(path):
    """'beamer' for a deck, 'article' for anything else."""
    return "beamer" if document_class(path) == "beamer" else "article"


def tex_env_for(source):
    """TeX on PATH, and TEXINPUTS holding the subject's `latex/` (where
    `coursemacros.sty` lives) and the board's `tex/`, the subject first."""
    extra = [os.path.join(subject_of(source), "latex"),
             os.path.join(paths.TOOL, "tex")]
    return tex.tex_env([d for d in extra if os.path.isdir(d)])


def _tex_errors(log_text):
    """The error lines of a LaTeX log, each with the lines up to its `l.NN`."""
    lines = log_text.splitlines()
    out = []
    for i, ln in enumerate(lines):
        if not ln.startswith("!"):
            continue
        out.append(ln)
        for nxt in lines[i + 1:i + 8]:
            out.append(nxt)
            if re.match(r"^l\.\d+", nxt):
                break
    return "\n".join(out)


def build_tex(source, keep_aux=False):
    """Compile one .tex beside itself. Returns the result dict of `build`."""
    src = os.path.abspath(source)
    here, name = os.path.split(src)
    stem = os.path.splitext(src)[0]
    pdf = stem + ".pdf"
    kind = tex_kind(src)
    env = tex_env_for(src)
    exe = shutil.which("pdflatex", path=env.get("PATH", ""))
    if not exe:
        return _result(False, [], NO_TEX, kind)

    started = time.time()
    runs, code, printed = 0, 0, ""
    while True:
        runs += 1
        try:
            p = subprocess.run(
                [exe, "-interaction=nonstopmode", "-halt-on-error", name],
                cwd=here, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=TEX_TIMEOUT)
        except subprocess.TimeoutExpired:
            return _result(False, [], "pdflatex ran past %d s on %s"
                           % (TEX_TIMEOUT, name), kind)
        code = p.returncode
        printed = p.stdout.decode("utf-8", "replace")
        if code != 0 or runs >= 3:
            break
        if runs == 2 and "Rerun" not in _read(stem + ".log"):
            break

    if code != 0 or not os.path.isfile(pdf) or os.path.getmtime(pdf) < started - 1:
        detail = _tex_errors(_read(stem + ".log")) or printed.strip()[-1200:]
        return _result(False, [], "FAILED to compile %s\n%s" % (name, detail), kind)

    keep = (".aux",) if keep_aux else ()
    for ext in SCRATCH:
        f = stem + ext
        if ext not in keep and os.path.isfile(f) and os.path.getmtime(f) >= started - 1:
            os.remove(f)
    return _result(True, [pdf], "built %s (%s, %d pdflatex run%s)"
                   % (os.path.basename(pdf), kind, runs, "" if runs == 1 else "s"),
                   kind)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Markdown: Paper-Writer's converter, copied. `config` first.
# ---------------------------------------------------------------------------

PDF_FIT = Path(__file__).with_name("build") / "pdf_fit.lua"

# Pandoc is often installed off PATH (conda, RStudio Server, Quarto). An
# explicit PAPER_PANDOC_BIN always wins.
_PANDOC_CANDIDATES = (
    "/opt/apps/easybuild/software/Anaconda3/2025.06-0/bin/pandoc",
    "/usr/lib/rstudio-server/bin/pandoc/pandoc",
    "/usr/lib/rstudio/bin/pandoc/pandoc",
    "/opt/quarto/bin/tools/pandoc",
    "/usr/local/bin/pandoc",
)


def pandoc_bin():
    explicit = os.environ.get("PAPER_PANDOC_BIN", "").strip()
    if explicit:
        return explicit
    found = shutil.which("pandoc")
    if found:
        return found
    for candidate in _PANDOC_CANDIDATES:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    for root in (os.environ.get("CONDA_PREFIX"), os.environ.get("CONDA_EXE")):
        if not root:
            continue
        base = Path(root)
        base = base.parent.parent if base.is_file() else base
        candidate = base / "bin" / "pandoc"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return "pandoc"


# pdflatex refuses a Unicode minus, so the engine is xelatex; and xelatex's
# default face has no subscripts or Greek, so the face is named. DejaVu comes
# from the root Brewfile.
def pdf_engine():
    return os.environ.get("PAPER_PDF_ENGINE", "xelatex").strip() or "xelatex"


def pdf_mainfont():
    return os.environ.get("PAPER_PDF_MAINFONT", "DejaVu Sans").strip()


def pdf_monofont():
    return os.environ.get("PAPER_PDF_MONOFONT", "DejaVu Sans Mono").strip()


# --- the figure gate (paperwriter/gates/figures.py) --------------------------

_GATE_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]*)\)(?:\{([^}]*)\})?")
_WIDTH_RE = re.compile(r"width=([0-9.]+)in")
# Word's default cell margin, 0.08in a side, on a two-column figure table.
CELL_PADDING_IN = 0.32
# US Letter with 1.25in margins, when the reference document cannot be measured.
DEFAULT_TEXT_WIDTH_IN = 6.0


def _widths_on(line):
    return [(target.strip(), _declared_width(attrs))
            for target, attrs in _GATE_IMAGE_RE.findall(line)]


def _declared_width(attrs):
    match = _WIDTH_RE.search(attrs or "")
    return float(match.group(1)) if match else None


def _figure_check(text, name, text_width_in=DEFAULT_TEXT_WIDTH_IN):
    """Every figure-layout problem in one document: an image with no width
    (pandoc imports it at full page width) and a row of panels wider than the
    page (Word shrinks the columns until labels and panels stop lining up)."""
    problems = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        images = _widths_on(line)
        if not images:
            continue
        for target, width in images:
            if width is None:
                problems.append(
                    f"{name}:{lineno}: figure has no width= attribute, so it is "
                    f"imported at full page width: {target}")
        declared = [w for _, w in images if w is not None]
        if len(declared) != len(images):
            continue
        budget = text_width_in - (CELL_PADDING_IN if len(images) > 1 else 0.0)
        total = sum(declared)
        if total > budget + 1e-9:
            problems.append(
                f"{name}:{lineno}: figure row is {total:.2f}in wide but only "
                f"{budget:.2f}in fits ({len(images)} panel(s))")
    return problems


# --- the converter (paperwriter/stages/building.py) --------------------------

def _format_flags(fmt, reference):
    """The pandoc flags that depend on what is being built. A .docx takes the
    reference document's styles; a PDF takes pdf_fit.lua, the engine and the
    faces."""
    if fmt == "docx":
        return ["--reference-doc", str(reference)] if reference else []
    if fmt != "pdf":
        return []
    out = ["--lua-filter", str(PDF_FIT)]
    engine = pdf_engine()
    if engine:
        out += ["--pdf-engine", engine]
    for name, value in (("mainfont", pdf_mainfont()),
                        ("monofont", pdf_monofont())):
        if value:
            out += ["-V", f"{name}={value}"]
    return out


def _format_timeout(fmt):
    """A .docx is one pass; a PDF is a TeX run over many pages, more than once."""
    return 900 if fmt == "pdf" else 300


# `![alt](target)`, bare or in angle brackets. Reference-style images are not
# matched: a check that guesses is a check nobody can act on.
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*(<[^>]*>|[^)\s]+)")
_IMAGE_SRC_RE = re.compile(r"(!\[[^\]]*\]\(\s*)(<[^>]*>|[^)\s]+)")
_REMOTE_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//|^data:", re.IGNORECASE)


def _image_targets(text):
    """Every distinct local image a document refers to, in order. Distinct,
    because pandoc embeds one copy of a file referenced twice."""
    seen, out = set(), []
    for raw in _IMAGE_RE.findall(text):
        target = raw.strip("<>").strip()
        if not target or _REMOTE_RE.match(target) or target in seen:
            continue
        seen.add(target)
        out.append(target)
    return out


def _media_count(docx):
    """How many image files a .docx actually carries. -1 if it cannot be read."""
    try:
        with zipfile.ZipFile(docx) as archive:
            return sum(1 for name in archive.namelist()
                       if name.startswith("word/media/"))
    except (OSError, zipfile.BadZipFile):
        return -1


def text_width_in(reference_docx):
    """The printable width of the reference document's page, in inches."""
    if not reference_docx:
        return DEFAULT_TEXT_WIDTH_IN
    try:
        with zipfile.ZipFile(Path(reference_docx)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", "ignore")
        width = int(re.search(r'<w:pgSz\b[^>]*\bw:w="(\d+)"', xml).group(1))
        margins = re.search(r"<w:pgMar\b[^>]*>", xml).group(0)
        left = int(re.search(r'w:left="(\d+)"', margins).group(1))
        right = int(re.search(r'w:right="(\d+)"', margins).group(1))
        return (width - left - right) / 1440.0          # twips to inches
    except (OSError, AttributeError, ValueError, KeyError, zipfile.BadZipFile):
        return DEFAULT_TEXT_WIDTH_IN


def figures_lost(source, built, reference_docx=None):
    """How many of a document's figures did not reach the built .docx, counted
    from the result. None when there is nothing to check. The reference
    document's own images are subtracted."""
    if built is None or built.suffix.lower() != ".docx":
        return None
    try:
        referenced = len(_image_targets(source.read_text(encoding="utf-8")))
    except OSError:
        return None
    if not referenced:
        return None
    embedded = _media_count(built)
    if embedded < 0:
        return None
    if reference_docx:
        template = _media_count(Path(reference_docx))
        if template > 0:
            embedded -= template
    return max(0, referenced - embedded)


def figure_layout_problems(source, reference_docx=None):
    """Every way this document's figures will land on the page wrong."""
    try:
        text = source.read_text(encoding="utf-8")
    except OSError:
        return []
    return _figure_check(text, source.name, text_width_in(reference_docx))


def exported_figures(text, resource_dirs):
    """`{target: path}` for each figure named under a `results/` that lacks it,
    where the copy under `exports/results/` has it. A machine without the
    cluster's `results/` holds only what the relay exported."""
    out = {}
    for target in _image_targets(text):
        named = [target] if os.path.isabs(target) else [
            os.path.join(d, target) for d in resource_dirs if d]
        if any(os.path.exists(p) for p in named):
            continue
        for p in named:
            parts = os.path.normpath(p).split(os.sep)
            twins = [os.sep.join(parts[:i] + ["exports"] + parts[i:])
                     for i in range(len(parts) - 1, -1, -1)
                     if parts[i] == "results"]
            hit = next((t for t in twins if os.path.isfile(t)), None)
            if hit:
                out[target] = hit
                break
    return out


def _pandoc_input(source, resource):
    """`(argv, stdin)`: the source as pandoc's argument, or its text with each
    exported figure's path put in, on stdin. Nothing is written beside it."""
    try:
        text = source.read_text(encoding="utf-8")
    except OSError:
        return [str(source)], None
    found = exported_figures(text, resource.split(os.pathsep))
    if not found:
        return [str(source)], None

    # Relative to the document, which is first on the resource path: an
    # absolute path would go into the .docx as the image's description, and
    # every built document is public.
    def put(m):
        target = m.group(2).strip("<>").strip()
        path = found.get(target)
        if not path:
            return m.group(0)
        if os.path.isabs(path):
            path = os.path.relpath(path, str(source.parent))
        return m.group(1) + ("<%s>" % path if " " in path else path)

    return [], _IMAGE_SRC_RE.sub(put, text)


def _resource_path(source, extra_roots):
    """Where pandoc looks for a figure, nearest first: the document's own
    directory, then the caller's roots."""
    seen, out = set(), []
    for root in (source.parent,) + tuple(extra_roots):
        text = str(root)
        if text not in seen:
            seen.add(text)
            out.append(text)
    return os.pathsep.join(out)


def convert_one(source, fmt, reference_docx=None, resource_roots=(), log_fn=None):
    """Convert one Markdown document to one format, beside its source. Returns
    the path, or None when pandoc did not produce it. A document that lost
    figures still returns its path, and says so."""
    if not source.exists():
        return None
    out_path = source.with_suffix("." + fmt)
    resource = _resource_path(source, tuple(resource_roots))
    given, text = _pandoc_input(source, resource)
    command = [pandoc_bin()] + given + ["-o", str(out_path),
                                        "--from", "markdown", "--standalone",
                                        "--resource-path", resource]
    command += _format_flags(fmt, reference_docx)

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True,
                                input=text, env=tex.tex_env(),
                                timeout=_format_timeout(fmt))
    except (OSError, subprocess.SubprocessError) as exc:
        if log_fn:
            log_fn(f"could not run pandoc on {source.name} ({exc}).")
        return None
    if result.returncode != 0 or not out_path.exists():
        if log_fn:
            log_fn(f"pandoc failed on {source.name} ({result.returncode}): "
                   f"{(result.stderr or '').strip()[:300]}")
        return None
    if log_fn:
        log_fn(f"built {out_path.name} ({out_path.stat().st_size:,} bytes)")
    lost = figures_lost(source, out_path, reference_docx=reference_docx)
    if lost and log_fn:
        referenced = len(_image_targets(source.read_text(encoding="utf-8")))
        log_fn(f"{lost} of {referenced} figure(s) in {source.name} did not reach "
               f"{out_path.name}. Their paths do not resolve from the document's "
               f"directory or any directory above it in the repository.")
    if log_fn:
        for problem in figure_layout_problems(source, reference_docx):
            log_fn(problem)
    return out_path


# --- what rebuild-docs.sh decided around the converter -----------------------

def reference_docx_for(source, explicit=None):
    """`(path or None, error or None)`: `--reference-doc`, then
    PAPER_REFERENCE_DOCX, then exactly one .docx in a `formats/` directory
    found from the source upward to the top of its repository. Two candidates
    is an error: a manuscript built against the wrong journal's styles is a
    plausible document nobody notices."""
    chosen = explicit or os.environ.get("PAPER_REFERENCE_DOCX", "").strip()
    if chosen:
        chosen = os.path.expanduser(chosen)
        if not os.path.isfile(chosen):
            return None, "no such reference document: %s" % chosen
        return chosen, None
    d = os.path.dirname(os.path.abspath(source))
    ceiling = repo_top(d) or "/"
    while True:
        formats = os.path.join(d, "formats")
        if os.path.isdir(formats):
            found = sorted(os.path.join(formats, f) for f in os.listdir(formats)
                           if f.endswith(".docx")
                           and os.path.isfile(os.path.join(formats, f)))
            if len(found) == 1:
                return found[0], None
            if len(found) > 1:
                return None, ("more than one reference document in %s: %s. Name "
                              "the one you want with --reference-doc."
                              % (formats, ", ".join(os.path.basename(f) for f in found)))
        parent = os.path.dirname(d)
        if d == ceiling or parent == d:
            return None, None
        d = parent


def resource_roots_for(source):
    """Each directory above the source, up to the top of its repository: a
    section carries the whole document's figure paths, written relative to
    the paper."""
    here = os.path.dirname(os.path.abspath(source))
    stop = repo_top(here)
    if not stop:
        return ()
    roots, walk = [], here
    while walk != stop:
        walk = os.path.dirname(walk)
        roots.append(walk)
    return tuple(roots)


def pdf_engine_found():
    """The PDF engine's path, or None."""
    return shutil.which(pdf_engine(), path=tex.tex_env().get("PATH", ""))


def build_md(source, formats=None, strict=False, reference_docx=None):
    """Convert one .md beside itself. Returns the result dict of `build`."""
    src = Path(os.path.abspath(source))
    lines = []
    say = lines.append

    pandoc = pandoc_bin()
    try:
        ok = subprocess.run([pandoc, "--version"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        return _result(False, [], "pandoc did not run: %s. Set PAPER_PANDOC_BIN "
                       "to the one you want, or put pandoc on PATH." % pandoc, "md")

    reference, err = reference_docx_for(src, reference_docx)
    if err:
        return _result(False, [], err, "md")

    if formats:
        wanted = list(formats)
    else:
        wanted = ["docx"]
        if pdf_engine_found():
            wanted.append("pdf")
        else:
            say("no .pdf: the PDF engine %s is not installed (PAPER_PDF_ENGINE "
                "names another)" % pdf_engine())
    if "pdf" in wanted and not pdf_engine_found():
        return _result(False, [], "cannot build a .pdf: the PDF engine %s is not "
                       "installed (PAPER_PDF_ENGINE names another)" % pdf_engine(),
                       "md")

    say("template: %s" % (reference or "(none; building unstyled)"))
    built, failed = [], False
    roots = resource_roots_for(src)
    for fmt in wanted:
        out = convert_one(src, fmt, reference_docx=reference,
                          resource_roots=roots, log_fn=say)
        if out is None:
            failed = True
            continue
        built.append(str(out))
        if figures_lost(src, out, reference_docx=reference):
            failed = True
        if strict and figure_layout_problems(src, reference):
            say("--strict: a figure will not sit on the page")
            failed = True
    return _result(not failed, built, "\n".join(lines), "md")


# ---------------------------------------------------------------------------
# The one entry
# ---------------------------------------------------------------------------

def _result(ok, built, detail, kind):
    return {"ok": bool(ok), "built": list(built), "detail": detail, "kind": kind}


def build(source, formats=None, strict=False, reference_docx=None, keep_aux=False):
    """Build one document beside itself.

    Returns {"ok", "built": [paths], "detail": what to show, "kind"}: kind is
    'beamer' or 'article' for a .tex and 'md' for Markdown. `formats` and
    `strict` apply to Markdown; `keep_aux` keeps a .tex build's `.aux`.
    """
    if not os.path.isfile(source):
        return _result(False, [], "no such file: %s" % source, None)
    ext = os.path.splitext(source)[1].lower()
    if ext == ".tex":
        return build_tex(source, keep_aux=keep_aux)
    if ext == ".md":
        return build_md(source, formats=formats, strict=strict,
                        reference_docx=reference_docx)
    return _result(False, [], "board build takes a .tex or a .md, not %s" % source,
                   None)
