"""What is in this image, for an assistant that cannot see one.

`board see <path>` prints a description of a PNG, a JPEG or a page of a PDF:
a subcommand every agent already has, so no tool protocol is needed. Where
the image goes is a recipe's `vision` block (an endpoint, or a command
running a sighted assistant already installed): the running agent's first,
then `vision_agent`. Every request carries a code drawn only in the image,
and an answer that cannot say it back is refused, because a confident
paragraph about an unseen page is the failure that must not happen.

The constraint: a fenced path is refused before a byte is read, because this
sends files to a hosted provider and no pre-tool hook sees a board command.
"""

import base64
import json
import mimetypes
import os
import random
import re
import shutil
import struct
import subprocess
import tempfile
import urllib.error
import urllib.request
import zlib

from . import fenced, keys


# The default question: read back a page of handwriting a tutor must mark.
DEFAULT_ASK = (
    "Transcribe everything written or printed in this image, in reading order, "
    "and keep the layout of it -- line breaks, columns, what is crossed out. "
    "Mathematics as LaTeX. Then, in two or three sentences, say what the page "
    "IS: a worked solution, a problem sheet, a diagram, a photograph of a "
    "board. Do not solve anything and do not correct anything; report what is "
    "on the page."
)

# Wide enough for small handwriting, narrow enough for one data URL per page.
PAGE_WIDTH = 1600

TIMEOUT = 180

# The types every OpenAI-format endpoint accepts; a fifth is a 400.
IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".gif")

# Variables that point a binary at another provider. A command route runs
# without them, because inside a turn the running recipe set them and the
# route would reach that recipe's provider again instead of the local
# binary. `vision.env` is applied after the scrub; None unsets.
ROUTING = ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY",
           "ANTHROPIC_MODEL", "ANTHROPIC_SMALL_FAST_MODEL",
           "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
           "ANTHROPIC_DEFAULT_HAIKU_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL",
           "OPENAI_BASE_URL", "OPENAI_API_KEY")

# What a provider substitutes, with HTTP 200, when the image did not arrive
# (DeepSeek maps unknown models to text-only).
PLACEHOLDERS = ("[Unsupported Image]", "[Unsupported Document]")


class Refused(Exception):
    """This path is not one this command may open, and the reason is the message."""


def registry():
    """`recipes.listing()`, or {} when it cannot be built."""
    from .agents import recipes
    try:
        return recipes.listing() or {}
    except Exception:                                        # noqa: BLE001
        return {}


def route(agent=None, table=None):
    """Where an image goes, as `(settings, why-there-is-none)`.

    The running agent's own recipe first, then `vision_agent`, so `board see`
    reports the route that really answers. A stood-down host is skipped: an
    endpoint route when the stand-down names its host or none, never a
    command route by name alone, since commands scrub `ROUTING`. An in-fence
    recipe is never a route (only it reads phi), nor one marked `sighted:
    false`.
    """
    from .net import egress
    table = registry() if table is None else table
    agents = {a.get("name"): a for a in (table.get("agents") or [])}
    tried, dark, blind = [], [], []
    for name in (agent, table.get("vision_agent"), table.get("default")):
        if not name or name in tried:
            continue
        tried.append(name)
        if (agents.get(name) or {}).get("private"):
            dark.append("'%s' is an in-fence model and never a vision route"
                        % name)
            continue
        got = (agents.get(name) or {}).get("vision")
        if not got or not (got.get("endpoint") or got.get("cmd")):
            continue
        if got.get("sighted") is False:
            blind.append("'%s' says its model cannot take an image" % name)
            continue
        stood = egress.stood_down(name)
        here = route_host(got)
        if stood and here and stood["host"] in (here, ""):
            dark.append("'%s' is stood down (%s)"
                        % (name, stood["host"] and
                           "%s does not answer from this machine" % stood["host"]
                           or stood["why"]))
            continue
        return dict(got, agent=name), None
    if dark or blind:
        return None, ("no vision route on this machine can be used: %s. "
                      "A sighted assistant can open the file itself."
                      % "; ".join(dark + blind))
    return None, ("no assistant on this machine names a vision route. Put a "
                  "`vision` block -- an endpoint or a command, and a model -- "
                  "on a recipe in the config, or name one in `vision_agent`.")


# ---------------------------------------------------------------------------
# The witness code: proof that whatever answered actually looked
# ---------------------------------------------------------------------------
# The witness code. A route can answer without looking (text-only model,
# denied file read, dropped block) and still exit 0, so every request carries
# six digits drawn only in the image; an answer that cannot repeat them is
# refused. Drawn here in the standard library so the check never silently
# depends on TeX or poppler.
GLYPHS = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
}

# Generous: a model may open with a sentence before the code line.
WITNESS_WINDOW = 600

# Tells the model what to do when it cannot see: an invented code is worse
# than a refusal.
WITNESS_ASK = (
    "\n\nThe FIRST image is a strip carrying a six-digit code and nothing "
    "else. Read that code off the strip and make the first line of your answer "
    "exactly `CODE: <the digits>`. Then answer the question above about the "
    "remaining image or images, and do not describe the strip itself. If you "
    "cannot see the images at all, say that plainly instead of guessing: an "
    "invented code is worse than no answer."
)


def _code():
    """Six digits nobody could guess, grouped so they are read back cleanly."""
    return "%03d-%03d" % (random.randint(0, 999), random.randint(0, 999))


def _png(path, width, height, rows):
    """An 8-bit greyscale PNG, written by hand. `rows` is one bytearray a line."""
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag, data):
        body = tag + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xffffffff))

    head = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head)
                 + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    return path


def _token_png(code, path, scale=18, pad=48):
    """The code, black on white, larger than any handwriting on the page."""
    glyphs = [GLYPHS[c] for c in code if c in GLYPHS]
    cells = max(1, len(glyphs) * 6 - 1)     # five wide, one of gap, none trailing
    width = pad * 2 + cells * scale
    height = pad * 2 + 7 * scale
    rows = [bytearray(b"\xff" * width) for _ in range(height)]
    for n, glyph in enumerate(glyphs):
        left = pad + n * 6 * scale
        for y, line in enumerate(glyph):
            for x, bit in enumerate(line):
                if bit != "1":
                    continue
                start = left + x * scale
                for dy in range(scale):
                    rows[pad + y * scale + dy][start:start + scale] = b"\x00" * scale
    return _png(path, width, height, rows)


def blind_answer(said):
    """The provider's own words for "the image never arrived", or None."""
    low = (said or "").lower()
    for mark in PLACEHOLDERS:
        if mark.lower() in low:
            return mark
    return None


def witnessed(said, code):
    """Did this answer carry the code that was only ever in the image?"""
    want = re.sub(r"\D", "", code or "")
    if not want:
        return True
    return want in re.sub(r"\D", "", (said or "")[:WITNESS_WINDOW])


def without_code(said):
    """The answer with the leading `CODE:` line removed; only that line."""
    lines = (said or "").splitlines()
    while lines and (not lines[0].strip()
                     or re.match(r"^\s*[`*]*\s*CODE\b\s*[:\-]", lines[0], re.I)):
        gone = lines.pop(0)
        if gone.strip():
            break
    return "\n".join(lines).strip() or (said or "").strip()


def _command_env(settings):
    """The environment a command route runs with: this one minus `ROUTING`,
    then the recipe's own `vision.env`."""
    env = dict(os.environ)
    for name in ROUTING:
        env.pop(name, None)
    for name, value in (settings.get("env") or {}).items():
        if value is None:
            env.pop(str(name), None)
        else:
            env[str(name)] = str(value)
    return env


def route_host(got):
    """The hostname this route opens, or "" for one that runs a command."""
    if not (got or {}).get("endpoint"):
        return ""
    from urllib.parse import urlsplit
    try:
        return urlsplit(got["endpoint"]).hostname or ""
    except ValueError:
        return ""


def _data_url(path):
    kind = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (
            kind, base64.b64encode(fh.read()).decode("ascii"))


def pages(path, page=None, width=PAGE_WIDTH):
    """The image files to send: the file itself, or a PDF's pages rendered,
    with a temporary directory that is the caller's to remove."""
    low = path.lower()
    if low.endswith(IMAGES):
        return [path], None
    if not low.endswith(".pdf"):
        raise Refused("%s is neither an image nor a PDF; `board see` reads "
                      "%s and .pdf" % (path, ", ".join(IMAGES)))
    from .course import paper
    env = paper.raster_env()
    tool = paper.renderer(env)
    if not tool:
        raise Refused("this machine has no page renderer -- pdftoppm, "
                      "pdftocairo or Ghostscript -- so a PDF cannot be turned "
                      "into something to look at. An image works.")
    box = tempfile.mkdtemp(prefix="board-see-")
    first = int(page or 1)
    name = tool[0]
    prefix = os.path.join(box, "page")
    if name in ("pdftoppm", "pdftocairo"):
        cmd = [name, "-png", "-scale-to-x", str(width), "-scale-to-y", "-1",
               "-f", str(first), "-l", str(first), path, prefix]
    else:
        cmd = ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
               "-sDEVICE=png16m", "-r%d" % max(72, int(width / 8.27)),
               "-dFirstPage=%d" % first, "-dLastPage=%d" % first,
               "-sOutputFile=%s-%%d.png" % prefix, path]
    subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=300)
    got = sorted(os.path.join(box, f) for f in os.listdir(box)
                 if f.lower().endswith(".png"))
    if not got:
        raise Refused("page %d of %s did not render; is the page there?"
                      % (first, path))
    return got, box


def ask(settings, images, prompt):
    """The answer, proved to come from something that looked: a code strip
    goes in front and must come back, else this raises and `cmd_see` exits
    non-zero. `_answer` does one request: `cmd` runs an installed sighted
    assistant on the file; `endpoint` is one OpenAI chat-completions call.
    """
    code = _code()
    box = tempfile.mkdtemp(prefix="board-see-code-")
    try:
        strip = _token_png(code, os.path.join(box, "code-strip.png"))
        said = _answer(settings, [strip] + list(images), prompt + WITNESS_ASK)
    finally:
        shutil.rmtree(box, ignore_errors=True)
    # The provider's own "no image" words first, since they name the cause.
    placeholder = blind_answer(said)
    if placeholder:
        raise Refused(
            "the route through %s answered with `%s`: the model behind it does "
            "not take image input, so the page was never read. Pin a model that "
            "does, or give the recipe's `vision` block a route that can see."
            % (settings.get("model") or settings.get("agent") or "this recipe",
               placeholder))
    if not witnessed(said, code):
        raise Refused(
            "the route through %s answered without the code that was printed "
            "on the image, so it did not read the page -- whatever it said "
            "about it. Nothing was written from this. What it did say, in case "
            "it explains itself: %s"
            % (settings.get("agent") or settings.get("model") or "this recipe",
               said[:300].replace("\n", " ") or "(nothing)"))
    return without_code(said)


def _answer(settings, images, prompt):
    """One route, one request. The text it gave back, or raises Refused."""
    if settings.get("cmd"):
        return _ask_command(settings, images, prompt)
    need = settings.get("needs_key")
    key = keys.get(need) if need else None
    if need and not key:
        raise Refused("%s is not in %s, so there is nothing to authenticate "
                      "with. One `%s=...` line in that file is the whole of "
                      "the setup.%s"
                      % (need, keys.store(), need,
                         ("\n" + keys.why_not()) if keys.why_not() else ""))
    content = [{"type": "text", "text": prompt}]
    for img in images:
        content.append({"type": "image_url",
                        "image_url": {"url": _data_url(img)}})
    body = json.dumps({
        "model": settings.get("model"),
        "messages": [{"role": "user", "content": content}],
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        settings["endpoint"], data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer %s" % key} if key
        else {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            got = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise Refused("%s answered %s: %s" % (settings["endpoint"],
                                              exc.code, detail.strip()))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        # Record the stand-down, so `route` answers from another recipe next.
        from .net import egress
        from urllib.parse import urlsplit
        host = urlsplit(settings["endpoint"]).hostname or ""
        if settings.get("agent") and egress.egress_ok():
            egress.mark_unreachable(settings["agent"], host)
        raise Refused("%s could not be reached: %s"
                      % (settings["endpoint"], exc))
    try:
        said = got["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise Refused("the answer had no text in it: %s"
                      % json.dumps(got)[:400])
    return (said or "").strip()


def _ask_command(settings, images, prompt):
    """An installed sighted assistant, run once on these files.

    Run in one temporary directory holding exactly the strip and the pages,
    with the files asked for by name, because a headless turn cannot approve
    reads elsewhere and a refused read answers from the filename. Run without
    `ROUTING`. The fence already ran in `describe`. The answer is stdout.
    """
    box = tempfile.mkdtemp(prefix="board-see-ask-")
    try:
        return _run_command(settings, _staged(images, box), prompt)
    finally:
        shutil.rmtree(box, ignore_errors=True)


def _staged(images, box):
    """The same images, side by side in `box`, with their names kept distinct."""
    out = []
    for n, path in enumerate(images):
        name = os.path.basename(path)
        if name in [os.path.basename(p) for p in out]:
            name = "%02d-%s" % (n, name)
        landed = os.path.join(box, name)
        shutil.copyfile(path, landed)
        out.append(landed)
    return out


def _run_command(settings, images, prompt):
    box = os.path.dirname(os.path.abspath(images[0])) or "."
    names = ", ".join(os.path.basename(p) for p in images)
    said = ("%s\n\nThe image is the file %s in this directory. Read it and "
            "answer about what is in it. Do not answer from the filename."
            % (prompt, names) if len(images) == 1 else
            "%s\n\nThe images are the files %s in this directory, in that "
            "order. Read them and answer about what is in them. Do not answer "
            "from the filenames." % (prompt, names))
    cmd = [a.replace("{prompt}", said) for a in settings["cmd"]]
    try:
        done = subprocess.run(cmd, cwd=box, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=_command_env(settings), timeout=TIMEOUT)
    except FileNotFoundError:
        raise Refused("`%s` is not on the path here, and it is the vision route "
                      "this machine names" % cmd[0])
    except subprocess.TimeoutExpired:
        raise Refused("`%s` did not answer within %d s" % (cmd[0], TIMEOUT))
    except OSError as exc:
        raise Refused("`%s` could not be run: %s" % (cmd[0], exc))
    out = (done.stdout or b"").decode("utf-8", "replace").strip()
    if done.returncode != 0 or not out:
        why = (done.stderr or b"").decode("utf-8", "replace").strip()[:400]
        raise Refused("`%s` exited %d and said nothing about the page%s"
                      % (cmd[0], done.returncode, (": " + why) if why else ""))
    return out


def describe(path, page=None, prompt=None, agent=None, table=None, root=None):
    """What is in this file, as text. Raises `Refused` with the reason.

    The fence comes first, before anything is opened (`fenced.refused_in`,
    the workspace-relative rule, since slate pages live in `live/inbox/`).
    """
    path = os.path.abspath(os.path.expanduser(str(path or "")))
    hit = (fenced.refused_in(root, path) if root else fenced.refused(path))
    if hit:
        raise Refused(
            "%s is inside `%s/`, which is fenced -- and `board see` sends a "
            "file to a hosted provider. Nothing in there may leave this "
            "machine. The local model reads it where it sits; see the "
            "`private` recipe in agents/recipes.py." % (path, hit))
    if not os.path.isfile(path):
        raise Refused("there is no file at %s" % path)
    # Resolved once: `route` may build the provider table in a subprocess.
    table = registry() if table is None else table
    settings, why = route(agent, table)
    if not settings:
        raise Refused(why)
    images, box = pages(path, page)
    try:
        # On failure, re-ask the route once: the failed attempt wrote the
        # stand-down the next choice depends on. Only onto a different route;
        # the same one back means the first refusal stands.
        tried, said = [], []
        while True:
            try:
                return ask(settings, images, prompt or DEFAULT_ASK), settings
            except Refused as gone:
                tried.append(settings.get("agent"))
                said.append("%s: %s" % (settings.get("agent") or "the route", gone))
                settings, _ = route(agent, table)
                if not settings or settings.get("agent") in tried:
                    raise Refused(" -- and then ".join(said)) if len(said) > 1 \
                        else gone
    finally:
        if box:
            for f in os.listdir(box):
                try:
                    os.remove(os.path.join(box, f))
                except OSError:
                    pass
            try:
                os.rmdir(box)
            except OSError:
                pass
