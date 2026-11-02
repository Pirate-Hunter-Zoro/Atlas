"""What is in this image, in words.

`board see <path>` prints a description of a PNG, a JPEG or a page of a PDF:
a subcommand the agent already has, so no tool protocol is needed. The image
goes to the DeepSeek recipe's `vision` block, one OpenAI-format
chat-completions call. Every request carries a code drawn only in the image,
and an answer that cannot say it back is refused, because a confident
paragraph about an unseen page is the failure that must not happen.
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

from . import keys


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

# What DeepSeek substitutes, with HTTP 200, when the image did not arrive
# (it maps unknown models to text-only).
PLACEHOLDERS = ("[Unsupported Image]", "[Unsupported Document]")


class Refused(Exception):
    """This path is not one this command may open, and the reason is the message."""


def route():
    """Where an image goes: the DeepSeek recipe's `vision` block."""
    from .agents import recipes
    return dict(recipes.spec()["vision"], agent=recipes.NAME)


# ---------------------------------------------------------------------------
# The witness code: proof that whatever answered actually looked
# ---------------------------------------------------------------------------
# The witness code. A route can answer without looking (a text-only model,
# a dropped image block) and still answer 200, so every request carries
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
    """DeepSeek's own words for "the image never arrived", or None."""
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


def route_host(got):
    """The hostname this route opens, or ""."""
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
    non-zero. `_answer` does the one chat-completions call.
    """
    code = _code()
    box = tempfile.mkdtemp(prefix="board-see-code-")
    try:
        strip = _token_png(code, os.path.join(box, "code-strip.png"))
        said = _answer(settings, [strip] + list(images), prompt + WITNESS_ASK)
    finally:
        shutil.rmtree(box, ignore_errors=True)
    # DeepSeek's own "no image" words first, since they name the cause.
    placeholder = blind_answer(said)
    if placeholder:
        raise Refused(
            "%s answered with `%s`: the model does not take image input, so "
            "the page was never read. `vision.model` in agents/recipes.py "
            "names the model." % (settings.get("model") or "DeepSeek",
                                  placeholder))
    if not witnessed(said, code):
        raise Refused(
            "%s answered without the code that was printed on the image, so "
            "it did not read the page -- whatever it said about it. Nothing "
            "was written from this. What it did say, in case it explains "
            "itself: %s"
            % (settings.get("model") or "DeepSeek",
               said[:300].replace("\n", " ") or "(nothing)"))
    return without_code(said)


def _answer(settings, images, prompt):
    """One request. The text it gave back, or raises Refused."""
    need = settings.get("needs_key")
    key = keys.get(need) if need else None
    if need and not key:
        from . import paths
        raise Refused("%s is not in %s or %s, so there is nothing to "
                      "authenticate with. One `%s=...` line in the first is "
                      "the whole of the setup.%s"
                      % (need, keys.store(), paths.DEEPSEEK_KEY, need,
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
        # The board says DeepSeek does not answer from here until a turn
        # goes through.
        from .net import egress
        egress.mark_unreachable(route_host(settings))
        raise Refused("%s could not be reached: %s"
                      % (settings["endpoint"], exc))
    try:
        said = got["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise Refused("the answer had no text in it: %s"
                      % json.dumps(got)[:400])
    return (said or "").strip()


def describe(path, page=None, prompt=None):
    """What is in this file, as text, and the route that read it. Raises
    `Refused` with the reason."""
    path = os.path.abspath(os.path.expanduser(str(path or "")))
    if not os.path.isfile(path):
        raise Refused("there is no file at %s" % path)
    settings = route()
    images, box = pages(path, page)
    try:
        return ask(settings, images, prompt or DEFAULT_ASK), settings
    finally:
        if box:
            shutil.rmtree(box, ignore_errors=True)
