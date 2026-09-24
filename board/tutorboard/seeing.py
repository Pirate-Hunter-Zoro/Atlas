"""What is in this image, for an assistant that cannot see one.

`board see <path>` prints a description of a PNG, a JPEG or a page of a PDF.

WHY A BOARD SUBCOMMAND AND NOT A TOOL PROTOCOL. A subcommand is the one
interface every agent in the registry already has -- `board brief`, `board
recap`, `board write` -- so this needs no MCP, no adapter and no per-vendor
plumbing, and a new provider inherits it by existing. It is also the honest
fallback for the local model, which is the assistant that most needs it and the
one no hosted vision route may ever be handed a fenced file from.

WHERE THE IMAGE GOES IS A RECIPE FIELD, NOT A CONSTANT. A `vision` block on an
agent names either an endpoint, a model and a key, or a COMMAND to run on the
file -- a sighted assistant that is already installed needs no second provider
and no second key. The running agent's own recipe is asked first, and
`vision_agent` at the top of the config answers for the case where the agent
running the sitting has no eyes. Both come out of `tutor --agents --json`, which
is the registry, so there is no second table.

AND AN ANSWER IS NOT BELIEVED BECAUSE IT ARRIVED. The one failure this path
must not have is a confident paragraph about a page nobody looked at -- a route
whose model is text-only, a harness that dropped the image, a file-reading tool
that was denied. Every request therefore carries a code that is in the IMAGE and
nowhere in the prompt, and an answer that cannot say it back is refused. See
`_code`, `_token_png` and `blind_answer`.

AND IT REFUSES A FENCED PATH BEFORE IT READS A BYTE. This sends a file to a
hosted provider, which is exactly what `ai-config/policy/phi.py` exists to stop
-- and a board subcommand does not go through any assistant's pre-tool hook. So
the check is here, first, by name, with the reason. Getting this wrong grows the
tool a documented route for sending session content to a third party.

Standard library only: `urllib.request`, a base64 data URL, no dependency.
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


# What the model is asked, when the caller asks nothing in particular. Written
# for the one thing this is for: a page of somebody's handwriting that a tutor
# has to read back and mark.
DEFAULT_ASK = (
    "Transcribe everything written or printed in this image, in reading order, "
    "and keep the layout of it -- line breaks, columns, what is crossed out. "
    "Mathematics as LaTeX. Then, in two or three sentences, say what the page "
    "IS: a worked solution, a problem sheet, a diagram, a photograph of a "
    "board. Do not solve anything and do not correct anything; report what is "
    "on the page."
)

# Poppler renders at this many pixels across. Wide enough that small handwriting
# survives, narrow enough that a base64 data URL of one page is not a megabyte
# of request body per page.
PAGE_WIDTH = 1600

TIMEOUT = 180

# The four an OpenAI-format endpoint accepts, plus jpg for the same type under
# its other extension. A fifth added here is a 400 from every hosted route.
IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".gif")

# THE VARIABLES A RECIPE USES TO POINT A BINARY SOMEWHERE ELSE, and the reason
# a command route has to be run without them. `board see` is run by the tutor's
# own Bash tool, inside a turn whose environment the RUNNING recipe wrote -- so
# in a DeepSeek sitting `ANTHROPIC_BASE_URL` is inherited, and claude's vision
# route, whose whole premise is "the binary that is installed here anyway", is
# not Claude at all. It is the provider that just went dark, reached a second
# time through a second door.
#
# Measured on this machine, the same PNG both ways: 14.4 s and a correct
# transcription in a clean environment; 180 s and `\`claude\` did not answer
# within 180 s` with those variables exported. That is the whole of the
# handwriting fallback for a DeepSeek sitting, and it is why this list is a
# constant here rather than a habit somewhere.
#
# A recipe overrides it: `env` on the `vision` block is applied after the scrub,
# and a value of None unsets. So the rule lives beside the command it is about.
ROUTING = ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY",
           "ANTHROPIC_MODEL", "ANTHROPIC_SMALL_FAST_MODEL",
           "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
           "ANTHROPIC_DEFAULT_HAIKU_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL",
           "OPENAI_BASE_URL", "OPENAI_API_KEY")

# WHAT A PROVIDER SAYS WHEN THE IMAGE DID NOT ARRIVE, in its own words, with
# HTTP 200 and a normal result object. DeepSeek's endpoint maps an unrecognised
# model name onto its text-only model and substitutes this for the image block
# rather than failing; the same string turns up in the model's own reasoning
# ("the message includes '[Unsupported Image]'"). Cheapest possible detector for
# the most expensive possible failure.
PLACEHOLDERS = ("[Unsupported Image]", "[Unsupported Document]")


class Refused(Exception):
    """This path is not one this command may open, and the reason is the message."""


def registry():
    """`tutor --agents --json`, parsed, or {}. One subprocess, and it is fine.

    This is a command a person or an assistant runs occasionally, not a poll:
    `assistants.listing` caches it for the hub because the hub asks four times
    a second, and nothing here does.
    """
    from .server import spawn
    code, out = spawn.tutor_cli(["--agents", "--json"], timeout=30)
    if code != 0:
        return {}
    try:
        return json.loads(out.strip().splitlines()[-1]) or {}
    except (ValueError, IndexError):
        return {}


def route(agent=None, table=None):
    """Where an image goes, as `(settings, why-there-is-none)`.

    The running agent's own recipe first, then `vision_agent`. A recipe with
    eyes of its own is still asked FIRST rather than skipped: `board see` is
    also how a person checks the route, and answering from somebody else's
    recipe when this one names its own would be a lie about what happens.

    A ROUTE THROUGH A PROVIDER THAT IS STOOD DOWN IS NOT A ROUTE. The same
    hostname that drops a tutor's turns drops its vision request, and the
    stand-down a failed turn already wrote is the evidence -- so the next name
    on the list answers instead, and where none can, the refusal says which
    host went dark rather than sending a page at it to find out again.

    BUT THE STAND-DOWN IS ABOUT A HOST, NOT ABOUT A NAME, and that distinction
    is what makes the climb-down work at all. A command route no longer opens
    the provider's hostname -- `ROUTING` is scrubbed out of its environment --
    so an agent whose TURNS are stood down still has working eyes on the binary
    that is installed here, and skipping them on the strength of the name would
    answer "every vision route on this machine is stood down" with one sitting
    on the path. An ENDPOINT route is skipped when the stand-down names its own
    host, and also when the stand-down names no host at all: that is
    `mark_failing`, a recipe whose requests are being refused for a reason the
    network is innocent of -- a renamed model, a rejected key -- and this route
    carries the same recipe's key to the same provider.

    AND A ROUTE THAT SAYS IT CANNOT SEE IS NEVER HANDED A PAGE. `sighted: false`
    on a `vision` block is a fact about the model behind it, and an answer from
    a blind route is indistinguishable from a transcription -- which is the one
    outcome this whole file exists to prevent.
    """
    from .net import egress
    table = registry() if table is None else table
    agents = {a.get("name"): a for a in (table.get("agents") or [])}
    tried, dark, blind = [], [], []
    for name in (agent, table.get("vision_agent"), table.get("default")):
        if not name or name in tried:
            continue
        tried.append(name)
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
# A VISION ROUTE THAT ANSWERS WITHOUT LOOKING IS INDISTINGUISHABLE FROM ONE THAT
# READ THE PAGE, and that is the failure this board can least afford: the tutor
# writes a card off the answer, marks working it never saw, and nothing anywhere
# exits non-zero. It has three separate causes and one shape. The endpoint's
# model is text-only and the provider swaps `[Unsupported Image]` in for the
# image. The command route's file-reading tool is absent or denied, and the
# model answers from the filename -- reproduced here, exit 0, non-empty stdout,
# "I can't transcribe it -- this session has no file-reading tool". Or the
# harness in between simply drops the block.
#
# So every request carries a strip with six digits on it that are in the IMAGE
# and in nothing else: not in the prompt, not in a filename, not derivable. An
# answer that cannot say them back did not see the page, whatever else it says,
# and is refused. `board eyes` is the same instrument run by hand for a person;
# this is it run on every call, for a program.
#
# Drawn here rather than rendered, because the alternatives are worse than the
# fifty lines: TeX is not on every machine, poppler is not either, and a route
# that silently stops being checked is the thing being guarded against. Standard
# library, one zlib call, no dependency -- which is the same promise the rest of
# this file makes.
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

# How far into the answer the code is looked for. Generous: a model that opens
# with a sentence of its own before the line it was asked for has still read the
# strip, and refusing that would be this guard failing the honest case.
WITNESS_WINDOW = 600

# What the model is told about the strip. Deliberately says what to do when it
# CANNOT see -- an invented code is the one answer worse than a refusal, and a
# model told to guess is a model that guesses.
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
    """The code, in black on white, big enough that no model has to squint.

    Eighteen pixels a cell puts each digit at 90 x 126, which is larger than any
    handwriting on a slate page and is the point: the strip must never be the
    hard part of the image.
    """
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
    """The answer with the `CODE:` line taken off the front.

    The code is plumbing and the card is written from what is left, so it does
    not belong in the description. Only the front, and only the one line: a
    transcription that legitimately contains the word is not touched.
    """
    lines = (said or "").splitlines()
    while lines and (not lines[0].strip()
                     or re.match(r"^\s*[`*]*\s*CODE\b\s*[:\-]", lines[0], re.I)):
        gone = lines.pop(0)
        if gone.strip():
            break
    return "\n".join(lines).strip() or (said or "").strip()


def _command_env(settings):
    """The environment a command route runs with: this one, minus the routing.

    See `ROUTING`. The recipe's own `vision.env` is applied on top, so a route
    that genuinely wants one of those variables says so where the command is.
    """
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
    """The image files to send: the file itself, or a PDF's pages rendered.

    A temporary directory comes back with them and is the caller's to remove --
    returned rather than cleaned up here, because the files have to outlive this
    call by exactly as long as it takes to read them.
    """
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
    """The answer, PROVED to have been written by something that looked.

    A code strip goes in front of the page and the code has to come back. It is
    six digits, drawn here, in the image and nowhere else -- so an answer
    carrying it read the image, and an answer without it did not, whatever it
    says about the page. Both outcomes are then loud: this raises, `cmd_see`
    prints the reason and exits non-zero, and no card is written off a paragraph
    about nothing. See the note above `GLYPHS` for the three ways that happens.

    `_answer` is the two spellings underneath, because a vision route is a
    recipe field and recipes are not all endpoints. `cmd` runs a sighted
    assistant that is already installed and hands it the file; `endpoint` is one
    HTTP request in the OpenAI chat-completions shape -- not an agent loop and
    not a conversation, which is why it is `/v1/chat/completions` rather than
    the Anthropic-format endpoint the same recipe drives a whole tutor through.
    """
    code = _code()
    box = tempfile.mkdtemp(prefix="board-see-code-")
    try:
        strip = _token_png(code, os.path.join(box, "code-strip.png"))
        said = _answer(settings, [strip] + list(images), prompt + WITNESS_ASK)
    finally:
        shutil.rmtree(box, ignore_errors=True)
    # AND NOW THE TWO WAYS AN ANSWER CAN BE A LIE, in the order they are cheap
    # to tell apart. The provider saying so in its own words comes first,
    # because its message names the cause; a missing code only says that
    # whatever answered did not look.
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
        # AND THE FINDING IS WRITTEN DOWN, so the next page is not sent at a
        # host that has just refused a connection. This is the same stand-down a
        # failed turn writes, on the same record and per agent, which is what
        # makes `route` able to pass over this recipe and answer from another.
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
    """A sighted assistant that is already installed, run once on these files.

    WHY A COMMAND IS A VISION ROUTE AT ALL. The models that teach here can see;
    what a hosted `/chat/completions` route buys is a SECOND provider, a second
    key and a model name that goes stale, for a job the binary on the path does
    already. So a recipe may name a command instead of an endpoint, and the
    fallback route on a machine is then whatever assistant it teaches with.

    RUN IN THE IMAGE'S OWN DIRECTORY, AND THE FILE ASKED FOR BY NAME. A headless
    turn has nobody to approve reading a path outside its working directory, and
    a refused read does not fail -- the model answers from the filename and
    sounds certain, which is the one outcome worse than an error. Every rendered
    page of a PDF lands in one temporary directory, so one directory always
    covers them.

    ONE DIRECTORY, MADE HERE, HOLDING EXACTLY WHAT IS BEING ASKED ABOUT. The
    code strip and the page do not start out as neighbours -- the strip is drawn
    into a temporary directory and a slate page lives in the workspace -- and
    "the files in this directory" is only an instruction if it is true. So they
    are copied together, which is what `pages` already does for every page of a
    PDF. The fence ran in `describe`, long before this, so nothing reaches here
    that was not already allowed to leave.

    AND IT RUNS WITHOUT THE ROUTING VARIABLES. See `ROUTING`: inside a turn the
    running recipe wrote the environment, and inheriting it points this command
    at the provider whose eyes are being fallen back FROM.

    The answer is stdout. `{prompt}` in the command is the question with the
    filenames in it; nothing is put on the command line that is not already a
    path on this machine.
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

    THE FENCE IS THE FIRST THING AND NOT THE SECOND. Nothing is opened, nothing
    is rendered and nothing leaves the machine for a path inside one -- see
    `fenced.refused_in`, which is the workspace-relative rule, and the note
    there for why it is that one rather than the any-depth `refused`: the slate
    pages this command exists to read live in the board's own `live/inbox/`.
    """
    path = os.path.abspath(os.path.expanduser(str(path or "")))
    hit = (fenced.refused_in(root, path) if root else fenced.refused(path))
    if hit:
        raise Refused(
            "%s is inside `%s/`, which is fenced -- and `board see` sends a "
            "file to a hosted provider. Nothing in there may leave this "
            "machine. The local model reads it where it sits; see the "
            "`private` recipe in `tutor --agents`." % (path, hit))
    if not os.path.isfile(path):
        raise Refused("there is no file at %s" % path)
    # Resolved once, here, rather than on each pass below: `route` asks
    # `tutor --agents --json` when it is handed nothing, and the retry must not
    # buy a second subprocess to answer a question that has not changed.
    table = registry() if table is None else table
    settings, why = route(agent, table)
    if not settings:
        raise Refused(why)
    images, box = pages(path, page)
    try:
        # AND THE ROUTE IS RE-ASKED ONCE WHEN THE FIRST ONE FAILS, because the
        # attempt that just failed is what WRITES the evidence the next choice
        # is made on: `ask` marks a provider unreachable when its endpoint
        # refuses a connection, and that record is only consulted by a `route`
        # call that happens afterwards. Resolved before the attempt and never
        # again, the first `board see` of a DeepSeek sitting always failed with
        # "api.deepseek.com could not be reached" and the tutor had no reason to
        # believe a second try would differ -- so it did not make one.
        #
        # Once, and only onto a DIFFERENT route. `route` walks its own candidate
        # list, so the name it returns after the stand-down is the next one
        # down; the same name back means nothing moved and the first refusal is
        # the honest answer.
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
