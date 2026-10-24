"""WAV in the standard library, everything else through a converter.

Every listener reads WAV PCM, 16 kHz, mono, 16-bit (`to_wav16k`); every phrase
the board plays is AAC in m4a (`to_m4a`), which Safari plays from a Blob.
`afconvert` ships with macOS and reads m4a, mp4, caf and WAV; WebM and Ogg,
which a browser without `audio/mp4` records, need `ffmpeg`. Neither present is
`Unconvertible`, in words, never a crash.
"""

import array
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

RATE = 16000

# Azure's short-audio REST endpoint takes at most this much.
MAX_SECONDS = 30
# What a converter may write past MAX_SECONDS before the WAV is trimmed.
MARGIN = 2

# What afconvert cannot read.
NEEDS_FFMPEG = (".webm", ".ogg", ".oga", ".opus", ".mkv")

TIMEOUT = 60


class Unconvertible(Exception):
    """This audio could not be turned into what was asked; the message says why."""


def read_wav(path):
    """`(samples, rate)`: mono floats in [-1, 1]. 8-, 16- and 32-bit PCM;
    channels are averaged."""
    with wave.open(path, "rb") as w:
        rate, width, chans = w.getframerate(), w.getsampwidth(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    if width == 2:
        data = array.array("h")
        data.frombytes(raw[:len(raw) - len(raw) % 2])
        scale = 32768.0
    elif width == 4:
        data = array.array("i")
        data.frombytes(raw[:len(raw) - len(raw) % 4])
        scale = 2147483648.0
    elif width == 1:
        data = array.array("h", [b - 128 for b in raw])
        scale = 128.0
    else:
        raise Unconvertible("%s is %d-bit PCM, which is not read here"
                            % (path, width * 8))
    if sys.byteorder == "big" and width > 1:
        data.byteswap()
    if chans > 1:
        data = [sum(data[i:i + chans]) / float(chans)
                for i in range(0, len(data) - chans + 1, chans)]
    return [v / scale for v in data], rate


def write_wav(path, samples, rate=RATE):
    """Mono 16-bit PCM, clipped."""
    data = array.array("h", [max(-32767, min(32767, int(round(v * 32767))))
                             for v in samples])
    if sys.byteorder == "big":
        data.byteswap()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())
    return path


def _data_chunk(path):
    """`(offset, declared size, file size)` of a RIFF WAV's data chunk, or
    None. A streamed WAV (OpenAI's) declares 0xFFFFFFFF, so the declared size
    is never trusted past the end of the file."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            head = fh.read(12)
            if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
                return None
            at = 12
            while at + 8 <= size:
                fh.seek(at)
                chunk = fh.read(8)
                n = struct.unpack("<I", chunk[4:8])[0]
                if chunk[:4] == b"data":
                    return at + 8, n, size
                at += 8 + n + (n & 1)
    except OSError:
        return None
    return None


def mend_wav(path):
    """Write a WAV's true RIFF and data sizes over ones that run past the end
    of the file (a stream's 0xFFFFFFFF). True when it changed anything."""
    got = _data_chunk(path)
    if not got:
        return False
    offset, declared, size = got
    actual = size - offset
    if declared <= actual:
        return False
    with open(path, "r+b") as fh:
        fh.seek(4)
        fh.write(struct.pack("<I", size - 8))
        fh.seek(offset - 4)
        fh.write(struct.pack("<I", actual))
    return True


def wav_shape(path):
    """`(rate, channels, bits, seconds)` of a WAV, or None for anything else.
    The seconds are what the file holds, whatever its header declares."""
    try:
        with wave.open(path, "rb") as w:
            rate, chans, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
            frames = w.getnframes()
    except (wave.Error, EOFError, OSError):
        return None
    got = _data_chunk(path)
    if got and chans and width:
        frames = min(frames, (got[2] - got[0]) // (chans * width))
    return rate, chans, width * 8, frames / float(rate or 1)


def seconds(path):
    got = wav_shape(path)
    return got[3] if got else 0.0


def _run(argv):
    try:
        done = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=TIMEOUT)
    except FileNotFoundError:
        raise Unconvertible("`%s` is not on the path here" % argv[0])
    except subprocess.TimeoutExpired:
        raise Unconvertible("`%s` took more than %d s" % (argv[0], TIMEOUT))
    if done.returncode != 0:
        raise Unconvertible("`%s` exited %d: %s" % (
            argv[0], done.returncode,
            (done.stdout or b"").decode("utf-8", "replace").strip()[-300:]))


def converter_for(src):
    """The program that reads `src`: `afconvert`, `ffmpeg`, or None."""
    low = src.lower()
    if low.endswith(NEEDS_FFMPEG):
        return "ffmpeg" if shutil.which("ffmpeg") else None
    if shutil.which("afconvert"):
        return "afconvert"
    return "ffmpeg" if shutil.which("ffmpeg") else None


def duration(src):
    """`src`'s length in seconds as `afinfo` estimates it, or None."""
    if not shutil.which("afinfo"):
        return None
    try:
        done = subprocess.run(["afinfo", src], stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(rb"estimated duration:\s*([0-9.]+)", done.stdout or b"")
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


def to_wav16k(src, dst, limit=MAX_SECONDS):
    """`src` as WAV PCM 16 kHz mono 16-bit at `dst`, at most `limit` seconds.
    A WAV of that shape is copied; anything else goes through `afconvert`, or
    `ffmpeg` for WebM and Ogg. A converter never writes much more than
    `limit`: ffmpeg stops at `limit` + MARGIN, and a source `afinfo` says is
    longer goes through ffmpeg instead, or is refused. `dst` is written whole
    or not at all: a conversion that fails or times out leaves nothing."""
    fd, tmp = tempfile.mkstemp(prefix=".wav16k-", suffix=".wav",
                               dir=os.path.dirname(os.path.abspath(dst)))
    os.close(fd)
    try:
        _to_wav16k(src, tmp, limit)
        if limit and seconds(tmp) > limit:
            trim(tmp, limit)
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return dst


def _to_wav16k(src, dst, limit):
    shape = wav_shape(src)
    if shape and shape[:3] == (RATE, 1, 16):
        shutil.copyfile(src, dst)
        return
    tool = converter_for(src)
    if not tool:
        raise Unconvertible(
            "%s needs %s to be read, and it is not installed here (brew "
            "install ffmpeg)" % (os.path.basename(src),
                                 "ffmpeg" if src.lower().endswith(NEEDS_FFMPEG)
                                 else "afconvert or ffmpeg"))
    if tool == "afconvert" and limit:
        # afconvert cannot stop early: a source longer than the limit, or one
        # whose length cannot be told, goes through ffmpeg or not at all.
        secs = duration(src)
        if secs is None or secs > limit + MARGIN:
            if not shutil.which("ffmpeg"):
                raise Unconvertible(
                    "%s is %s, over the %d s a take may be, and only ffmpeg "
                    "(not installed here) can cut it short" % (
                        os.path.basename(src),
                        "of a length afinfo cannot tell" if secs is None
                        else "%.0f s long" % secs, limit))
            tool = "ffmpeg"
    if tool == "afconvert":
        _run(["afconvert", src, "-o", dst, "-f", "WAVE", "-d", "LEI16@%d" % RATE,
              "-c", "1"])
    else:
        _run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src]
             + (["-t", "%d" % (limit + MARGIN)] if limit else [])
             + ["-ar", str(RATE), "-ac", "1", "-c:a", "pcm_s16le", "-f", "wav", dst])
    if not wav_shape(dst):
        raise Unconvertible("%s converted to nothing readable" % src)


def trim(path, limit=MAX_SECONDS):
    """Cut a WAV to its first `limit` seconds, in place."""
    with wave.open(path, "rb") as w:
        params = w.getparams()
        raw = w.readframes(int(limit * w.getframerate()))
    tmp = path + ".trim"
    with wave.open(tmp, "wb") as w:
        w.setparams(params)
        w.writeframes(raw)
    os.replace(tmp, path)


def to_m4a(src, dst):
    """`src` (anything the converter reads) as AAC in m4a at `dst`, written
    whole or not at all."""
    tool = converter_for(src)
    if not tool:
        raise Unconvertible("no afconvert or ffmpeg here to make an m4a")
    fd, tmp = tempfile.mkstemp(prefix=".m4a-", suffix=".m4a",
                               dir=os.path.dirname(os.path.abspath(dst)))
    os.close(fd)
    try:
        if tool == "afconvert":
            _run(["afconvert", src, "-o", tmp, "-f", "m4af", "-d", "aac"])
        else:
            _run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src,
                  "-c:a", "aac", "-b:a", "96k", "-f", "mp4", tmp])
        if not os.path.getsize(tmp):
            raise Unconvertible("the converter wrote an empty m4a")
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return dst
