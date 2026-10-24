"""WAV in the standard library, everything else through a converter.

Every listener reads WAV PCM, 16 kHz, mono, 16-bit (`to_wav16k`); every phrase
the board plays is AAC in m4a (`to_m4a`), which Safari plays from a Blob.
`afconvert` ships with macOS and reads m4a, mp4, caf and WAV; WebM and Ogg,
which a browser without `audio/mp4` records, need `ffmpeg`. Neither present is
`Unconvertible`, in words, never a crash.
"""

import array
import os
import shutil
import subprocess
import sys
import tempfile
import wave

RATE = 16000

# Azure's short-audio REST endpoint takes at most this much.
MAX_SECONDS = 30

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


def wav_shape(path):
    """`(rate, channels, bits, seconds)` of a WAV, or None for anything else."""
    try:
        with wave.open(path, "rb") as w:
            return (w.getframerate(), w.getnchannels(), w.getsampwidth() * 8,
                    w.getnframes() / float(w.getframerate() or 1))
    except (wave.Error, EOFError, OSError):
        return None


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


def to_wav16k(src, dst, limit=MAX_SECONDS):
    """`src` as WAV PCM 16 kHz mono 16-bit at `dst`, at most `limit` seconds.
    A WAV of that shape is copied; anything else goes through `afconvert`, or
    `ffmpeg` for WebM and Ogg."""
    shape = wav_shape(src)
    if shape and shape[:3] == (RATE, 1, 16):
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)
    else:
        tool = converter_for(src)
        if not tool:
            raise Unconvertible(
                "%s needs %s to be read, and it is not installed here (brew "
                "install ffmpeg)" % (os.path.basename(src),
                                     "ffmpeg" if src.lower().endswith(NEEDS_FFMPEG)
                                     else "afconvert or ffmpeg"))
        if tool == "afconvert":
            _run(["afconvert", src, "-o", dst, "-f", "WAVE", "-d", "LEI16@%d" % RATE,
                  "-c", "1"])
        else:
            _run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src,
                  "-ar", str(RATE), "-ac", "1", "-c:a", "pcm_s16le", "-f", "wav", dst])
        if not wav_shape(dst):
            raise Unconvertible("%s converted to nothing readable" % src)
    if limit and seconds(dst) > limit:
        trim(dst, limit)
    return dst


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
