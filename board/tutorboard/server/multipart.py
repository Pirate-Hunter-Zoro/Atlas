"""Reading an upload, without a library, straight to disk.

`save_parts` reads a multipart/form-data body off the socket a chunk at a
time and writes each file part into a folder as it arrives, so a 150 MB PDF
costs the server one chunk of memory, not 150 MB. Each part is written to a
hidden `.part-*` file, and every one is renamed only once the closing
boundary has been read: a body cut off half way leaves nothing in the folder.

The body is capped at `MAX_UPLOAD` (1 GB) by its Content-Length, which the
caller checks before reading a byte. Every other route keeps
`Handler.MAX_BODY`.
"""

import os
import posixpath
import re
import tempfile

# The largest upload body taken, multipart framing included.
MAX_UPLOAD = 1 << 30
CHUNK = 1 << 16
# A part's headers are a few lines; more than this is not a form.
MAX_HEAD = 16 * 1024


class Broken(ValueError):
    """The body is not the multipart form it says it is, or it ended early."""


SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name):
    name = posixpath.basename((name or "").replace("\\", "/"))
    name = SAFE_NAME.sub("-", name).strip("-.") or "drop"
    return name[:120]


def _filename(raw):
    """The `filename` of one part's header block, or None for a plain field."""
    for line in raw.decode("utf-8", "replace").split("\r\n"):
        k, _, v = line.partition(":")
        if k.strip().lower() == "content-disposition":
            m = re.search(r'filename="([^"]*)"', v)
            return m.group(1) if m else None
    return None


class _Body(object):
    """The request body as a buffer refilled from the socket, never read past
    Content-Length."""

    def __init__(self, rfile, length, chunk):
        self.rfile = rfile
        self.left = length
        self.chunk = chunk
        # A leading CRLF, so the first boundary line matches the same
        # delimiter as every later one.
        self.buf = b"\r\n"

    def more(self):
        """One more chunk onto the buffer; False at the end of the body."""
        if self.left <= 0:
            return False
        got = self.rfile.read(min(self.chunk, self.left))
        if not got:
            raise Broken("the body ended %d bytes early" % self.left)
        self.left -= len(got)
        self.buf += got
        return True


def save_parts(rfile, length, boundary, folder, name_for, chunk=CHUNK):
    """Write every file part of the body into `folder`.

    `name_for(index, filename)` gives the path a whole part is renamed to;
    it is asked only after the closing boundary. Returns `[(filename as sent,
    path written, size)]`. Raises `Broken` for a body that is not a whole
    form and `OSError` when the disk refuses; either way nothing is left in
    `folder`.
    """
    if not boundary:
        raise Broken("no boundary")
    delim = b"\r\n--" + boundary
    keep = len(delim) - 1
    body = _Body(rfile, length, chunk)
    parts = []                                  # [(tmp path, filename, size)]
    out = None
    try:
        # The preamble, up to the first boundary.
        while True:
            at = body.buf.find(delim)
            if at >= 0:
                body.buf = body.buf[at + len(delim):]
                break
            body.buf = body.buf[-keep:]
            if not body.more():
                raise Broken("no boundary in the body")
        while True:
            # After a boundary: `--` ends the form, a line break starts a part.
            while len(body.buf) < 2 and body.more():
                pass
            if body.buf[:2] == b"--":
                break
            while body.buf.find(b"\r\n") < 0:
                if len(body.buf) > MAX_HEAD or not body.more():
                    raise Broken("a boundary line that does not end")
            line, _, body.buf = body.buf.partition(b"\r\n")
            if line.strip(b" \t"):
                raise Broken("junk after a boundary")
            while True:
                if body.buf.startswith(b"\r\n"):
                    head, body.buf = b"", body.buf[2:]
                    break
                end = body.buf.find(b"\r\n\r\n")
                if end >= 0:
                    head, body.buf = body.buf[:end], body.buf[end + 4:]
                    break
                if len(body.buf) > MAX_HEAD or not body.more():
                    raise Broken("a part's headers do not end")
            filename = _filename(head)
            if filename:
                fd, tmp = tempfile.mkstemp(prefix=".part-", dir=folder)
                out = os.fdopen(fd, "wb")
                parts.append([tmp, filename, 0])
            while True:
                at = body.buf.find(delim)
                if at >= 0:
                    data, body.buf = body.buf[:at], body.buf[at + len(delim):]
                elif len(body.buf) > keep:
                    data, body.buf = body.buf[:-keep], body.buf[-keep:]
                else:
                    data = b""
                if out is not None and data:
                    out.write(data)
                    parts[-1][2] += len(data)
                if at >= 0:
                    break
                if not body.more():
                    raise Broken("the body ended inside a part")
            if out is not None:
                out.close()
                out = None
        saved = []
        for index, (tmp, filename, size) in enumerate(parts):
            final = name_for(index, filename)
            os.rename(tmp, final)
            parts[index][0] = None
            saved.append((filename, final, size))
        return saved
    except BaseException:
        if out is not None:
            out.close()
        for tmp, _f, _s in parts:
            if tmp:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        raise
