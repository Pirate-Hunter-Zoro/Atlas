"""The local tone check: was each syllable of a Mandarin take the tone it was
meant to be? Standard library only. A PROTOTYPE, and every result says so.

    f0           YIN pitch per 10 ms frame (0 where unvoiced), at 8 kHz
    smooth       a median over the voiced neighbours, then octave jumps
                 repaired against the local median
    semitones    each voiced frame against the speaker's own median
    syllables    from whisper's word timings when they count out right, else
                 the voiced runs merged (or split) to the target count
    classify     each syllable's contour against T1-T4 and the neutral tone;
                 a low-confidence call is `unknown`, never a guess
    dtw          the whole contour against the TTS reference's, when there is one
    word_diff    what was said against what was meant, word by word

The prototype found six voiced runs in four syllables, which is why runs are
merged to the count rather than trusted. A tone is `T1`..`T4`, `neutral` or
`unknown`; `target` is the written tone and `expect` the one actually spoken
after third-tone and 不 sandhi.
"""

import difflib
import math
import operator
import re
import unicodedata

from tutorboard.speech import audio

RATE = 8000
HOP = 0.010
WINDOW = 0.032
FMIN, FMAX = 70.0, 420.0
THRESHOLD = 0.15
# With no dip under THRESHOLD, the deepest dip under this still counts.
LOOSE = 0.35
# Below this share of the loudest frame's RMS a frame is silence.
QUIET = 0.08
# Frames bridged inside a run, and the shortest run kept.
GAP_FRAMES = 2
MIN_RUN = 4
# A call below this is `unknown`.
SURE = 0.3

LABEL = "local tone check, a prototype"

# Each tone's contour in semitones from the speaker's median, at five points.
TEMPLATES = {
    "T1": [2.5, 2.5, 2.5, 2.5, 2.5],
    "T2": [-1.0, -0.5, 0.5, 2.0, 3.5],
    "T3": [-2.0, -3.5, -4.5, -4.0, -2.5],
    "T4": [4.0, 3.0, 1.0, -1.5, -4.0],
    "neutral": [0.0, -0.5, -1.0, -1.5, -2.0],
}

TONE_MARKS = {
    "ā": ("a", 1), "á": ("a", 2), "ǎ": ("a", 3), "à": ("a", 4),
    "ē": ("e", 1), "é": ("e", 2), "ě": ("e", 3), "è": ("e", 4),
    "ī": ("i", 1), "í": ("i", 2), "ǐ": ("i", 3), "ì": ("i", 4),
    "ō": ("o", 1), "ó": ("o", 2), "ǒ": ("o", 3), "ò": ("o", 4),
    "ū": ("u", 1), "ú": ("u", 2), "ǔ": ("u", 3), "ù": ("u", 4),
    "ǖ": ("ü", 1), "ǘ": ("ü", 2), "ǚ": ("ü", 3), "ǜ": ("ü", 4),
}


# ---------------------------------------------------------------------------
# pinyin: what was meant
# ---------------------------------------------------------------------------
def _tone_name(n):
    return {1: "T1", 2: "T2", 3: "T3", 4: "T4", 5: "neutral", 0: "neutral"}.get(n)


def targets(pinyin):
    """`[{syllable, target, expect}]` for `ni3 hao3` or `nǐ hǎo`: the written
    tone, and the one spoken once third-tone and 不 sandhi are applied."""
    out = []
    said = str(pinyin or "").lower()
    toned = bool(re.search(r"[1-5]", said) or any(c in TONE_MARKS for c in said))
    for token in re.split(r"[\s',.;:!?，。、！？-]+", said):
        if not token:
            continue
        for m in re.finditer(r"([a-zü:vāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]+)([0-5])?", token):
            syl, tone = "", None
            for ch in m.group(1):
                if ch in TONE_MARKS:
                    base, tone = TONE_MARKS[ch]
                    syl += base
                else:
                    syl += ch
            if m.group(2):
                tone = int(m.group(2))
            syl = syl.replace("u:", "ü").replace("v", "ü")
            if tone is None and toned:
                tone = 5          # untoned among toned syllables: neutral
            out.append({"syllable": syl, "target": _tone_name(tone)})
    for s in out:
        s["expect"] = s["target"]
    # Third tone before third tone is spoken as a second.
    for i in range(len(out) - 1):
        if out[i]["target"] == "T3" and out[i + 1]["target"] == "T3":
            out[i]["expect"] = "T2"
    # 不 before a fourth tone is spoken as a second.
    for i in range(len(out) - 1):
        if out[i]["syllable"] == "bu" and out[i]["target"] == "T4" \
                and out[i + 1]["target"] == "T4":
            out[i]["expect"] = "T2"
    return out


def han(text):
    """The CJK characters of `text`, one a syllable."""
    return [c for c in str(text or "") if unicodedata.category(c) == "Lo"
            and ("CJK" in unicodedata.name(c, ""))]


# ---------------------------------------------------------------------------
# pitch
# ---------------------------------------------------------------------------
def downsample(samples, rate, to=RATE):
    """To `to` Hz by averaging each block (a box filter, enough for pitch)."""
    if rate == to:
        return list(samples)
    step = rate / float(to)
    if step < 1:
        raise ValueError("cannot upsample %d Hz to %d" % (rate, to))
    out, n = [], len(samples)
    i = 0.0
    while i + step <= n:
        a, b = int(i), int(i + step)
        block = samples[a:b] or [samples[a]]
        out.append(sum(block) / len(block))
        i += step
    return out


def f0(samples, rate):
    """`(f0 per frame, rms per frame)`: YIN pitch in Hz (0 where unvoiced)."""
    x = downsample(samples, rate)
    w = int(WINDOW * RATE)
    hop = int(HOP * RATE)
    tmin, tmax = int(RATE / FMAX), int(RATE / FMIN) + 1
    cs = [0.0]
    for v in x:
        cs.append(cs[-1] + v * v)
    frames = []
    starts = list(range(0, max(0, len(x) - w - tmax), hop))
    rms = [math.sqrt((cs[i + w] - cs[i]) / w) for i in starts]
    loud = max(rms) if rms else 0.0
    for n, i in enumerate(starts):
        if loud <= 0 or rms[n] < QUIET * loud:
            frames.append(0.0)
            continue
        seg = x[i:i + w]
        e0 = cs[i + w] - cs[i]
        d = [0.0] * (tmax + 1)
        for tau in range(1, tmax + 1):
            et = cs[i + tau + w] - cs[i + tau]
            d[tau] = e0 + et - 2.0 * sum(map(operator.mul, seg, x[i + tau:i + tau + w]))
        running, cmnd = 0.0, [1.0] * (tmax + 1)
        for tau in range(1, tmax + 1):
            running += d[tau]
            cmnd[tau] = d[tau] * tau / running if running > 0 else 1.0
        tau = None
        for t in range(tmin, tmax):
            if cmnd[t] < THRESHOLD:
                while t + 1 < tmax and cmnd[t + 1] < cmnd[t]:
                    t += 1
                tau = t
                break
        if tau is None:
            # No dip under the threshold: the deepest one, if it is clear
            # enough to be voicing at all (breathy or creaky speech).
            t = min(range(tmin, tmax), key=lambda j: cmnd[j])
            if cmnd[t] >= LOOSE:
                frames.append(0.0)
                continue
            tau = t
        # Parabolic interpolation around the dip.
        a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1] if tau + 1 <= tmax else cmnd[tau]
        den = a - 2 * b + c
        shift = 0.5 * (a - c) / den if den else 0.0
        frames.append(RATE / (tau + max(-1.0, min(1.0, shift))))
    return frames, rms


def _median(vals):
    vals = sorted(vals)
    if not vals:
        return 0.0
    m = len(vals) // 2
    return vals[m] if len(vals) % 2 else (vals[m - 1] + vals[m]) / 2.0


def smooth(track, k=5):
    """A median over each voiced frame's voiced neighbours, then octave jumps
    repaired: a frame more than ~0.75 octave off its neighbourhood's median is
    halved or doubled back onto it."""
    half = k // 2
    out = list(track)
    for i, v in enumerate(track):
        if v > 0:
            near = [u for u in track[max(0, i - half):i + half + 1] if u > 0]
            out[i] = _median(near)
    for _ in range(2):
        fixed = list(out)
        for i, v in enumerate(out):
            if v <= 0:
                continue
            near = [u for u in out[max(0, i - 10):i + 11] if u > 0]
            ref = _median(near)
            if ref <= 0:
                continue
            r = math.log(v / ref, 2)
            if r > 0.75:
                fixed[i] = v / 2.0
            elif r < -0.75:
                fixed[i] = v * 2.0
        out = fixed
    return out


def semitones(track):
    """Each voiced frame in semitones from the speaker's median; None unvoiced."""
    m = _median([v for v in track if v > 0])
    if m <= 0:
        return [None] * len(track)
    return [12.0 * math.log(v / m, 2) if v > 0 else None for v in track]


# ---------------------------------------------------------------------------
# syllables
# ---------------------------------------------------------------------------
def voiced_runs(track):
    """`[[start, end)]` frame spans of voicing, gaps of GAP_FRAMES bridged and
    runs shorter than MIN_RUN dropped."""
    runs, start, gap = [], None, 0
    for i, v in enumerate(list(track) + [0] * (GAP_FRAMES + 1)):
        if v > 0:
            if start is None:
                start = i
            gap = 0
            end = i + 1
        elif start is not None:
            gap += 1
            if gap > GAP_FRAMES:
                if end - start >= MIN_RUN:
                    runs.append([start, end])
                start, gap = None, 0
    return runs


def merge_to(runs, n, rms=None):
    """The runs made `n`: the closest neighbours merged while there are too
    many, the longest split at its quietest middle frame while too few."""
    runs = [list(r) for r in runs]
    while len(runs) > n > 0:
        gaps = [(runs[i + 1][0] - runs[i][1],
                 runs[i + 1][1] - runs[i][0], i) for i in range(len(runs) - 1)]
        _g, _l, i = min(gaps)
        runs[i:i + 2] = [[runs[i][0], runs[i + 1][1]]]
    while 0 < len(runs) < n:
        i = max(range(len(runs)), key=lambda j: runs[j][1] - runs[j][0])
        a, b = runs[i]
        if b - a < 2 * MIN_RUN:
            break
        lo, hi = a + (b - a) // 5, b - (b - a) // 5
        cut = (min(range(lo, hi), key=lambda j: rms[j]) if rms and hi > lo
               and hi <= len(rms) else (a + b) // 2)
        cut = max(a + MIN_RUN, min(b - MIN_RUN, cut))
        runs[i:i + 1] = [[a, cut], [cut, b]]
    return runs


def from_words(words, n):
    """Frame spans from whisper's word timings, one per character of a
    multi-character word, or None when they do not count out to `n`."""
    spans = []
    for w in words or []:
        try:
            start, end = float(w.get("start")), float(w.get("end"))
        except (TypeError, ValueError):
            return None
        k = len(han(w.get("text"))) or 1
        step = (end - start) / k
        for j in range(k):
            spans.append([int(round((start + j * step) / HOP)),
                          int(round((start + (j + 1) * step) / HOP))])
    return spans if len(spans) == n and all(b > a for a, b in spans) else None


# ---------------------------------------------------------------------------
# a syllable's tone
# ---------------------------------------------------------------------------
def _five(points):
    """A contour resampled to five means."""
    out = []
    for k in range(5):
        a = int(len(points) * k / 5.0)
        b = max(a + 1, int(len(points) * (k + 1) / 5.0))
        part = points[a:b]
        out.append(sum(part) / len(part))
    return out


def _distance(c, t):
    mc, mt = sum(c) / 5.0, sum(t) / 5.0
    shape = math.sqrt(sum(((a - mc) - (b - mt)) ** 2 for a, b in zip(c, t)) / 5.0)
    # The level counts for less than the shape: in a short phrase the
    # speaker's median sits between its tones.
    return shape + 0.3 * abs(mc - mt)


def classify(st, span, short=False):
    """`(tone, confidence, contour)` for frames `span` of the semitone track.
    `short`: the syllable is brief enough to be a neutral tone."""
    a, b = span
    cut = max(0, (b - a) // 10)
    points = [v for v in st[a + cut:b - cut] if v is not None]
    if len(points) < MIN_RUN:
        return "unknown", 0.0, []
    c = _five(points)
    names = [k for k in TEMPLATES if k != "neutral" or short]
    ranked = sorted((_distance(c, TEMPLATES[k]), k) for k in names)
    (d1, best), (d2, _second) = ranked[0], ranked[1]
    sure = (d2 - d1) / d2 if d2 > 0 else 0.0
    if d1 > 1.5:
        sure *= max(0.0, 1.0 - (d1 - 1.5) / 3.0)
    sure = max(0.0, min(1.0, sure))
    return (best if sure >= SURE else "unknown"), round(sure, 2), \
        [round(v, 2) for v in c]


# ---------------------------------------------------------------------------
# the whole take against the reference
# ---------------------------------------------------------------------------
def dtw(a, b, cap=120):
    """The mean absolute semitone gap along the best alignment of two
    contours (voiced frames only), each thinned to at most `cap` points."""
    a = [v for v in a if v is not None]
    b = [v for v in b if v is not None]
    if not a or not b:
        return None
    a = a[::max(1, len(a) // cap)]
    b = b[::max(1, len(b) // cap)]
    inf = float("inf")
    prev = [0.0] + [inf] * len(b)
    steps = [0] + [0] * len(b)
    for x in a:
        cur, cur_steps = [inf] * (len(b) + 1), [0] * (len(b) + 1)
        for j, y in enumerate(b, 1):
            choices = ((prev[j - 1], steps[j - 1]), (prev[j], steps[j]),
                       (cur[j - 1], cur_steps[j - 1]))
            best, n = min(choices)
            cur[j] = best + abs(x - y)
            cur_steps[j] = n + 1
        prev, steps = cur, cur_steps
    return prev[-1] / max(1, steps[-1])


def contour(path):
    """The semitone track of a WAV."""
    samples, rate = audio.read_wav(path)
    track, _rms = f0(samples, rate)
    return semitones(smooth(track))


# ---------------------------------------------------------------------------
# words
# ---------------------------------------------------------------------------
def _tokens(text, lang):
    if str(lang or "").lower().startswith(("zh", "ja", "yue")):
        return [c for c in str(text or "")
                if unicodedata.category(c)[0] in "LN"]
    return re.findall(r"[^\W_]+(?:'[^\W_]+)?", str(text or "").lower())


def word_diff(ref, heard, lang):
    """`[{op, target, heard}]`, op one of equal, wrong, missing, extra."""
    a, b = _tokens(ref, lang), _tokens(heard, lang)
    out = []
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out += [{"op": "equal", "target": x, "heard": x} for x in a[i1:i2]]
        elif op == "delete":
            out += [{"op": "missing", "target": x, "heard": ""} for x in a[i1:i2]]
        elif op == "insert":
            out += [{"op": "extra", "target": "", "heard": y} for y in b[j1:j2]]
        else:
            ta, hb = a[i1:i2], b[j1:j2]
            for k in range(max(len(ta), len(hb))):
                t = ta[k] if k < len(ta) else ""
                h = hb[k] if k < len(hb) else ""
                out.append({"op": "wrong" if t and h else "missing" if t else "extra",
                            "target": t, "heard": h})
    return out


def _syllable_texts(ref, lang, n, aims):
    chars = han(ref) if str(lang).lower().startswith("zh") else []
    if len(chars) == n:
        return chars
    return [t["syllable"] for t in aims] if len(aims) == n else [""] * n


def unheard(ref, lang, pinyin=None):
    """The result for a take in which nothing was heard."""
    aims = targets(pinyin)
    n = len(aims) or len(han(ref))
    texts = _syllable_texts(ref, lang, n, aims)
    return {"verdict": "nothing was heard", "score": None,
            "syllables": [{"syllable": texts[i],
                           "pinyin": aims[i]["syllable"] if i < len(aims) else "",
                           "target": aims[i]["target"] if i < len(aims) else None,
                           "expect": aims[i]["expect"] if i < len(aims) else None,
                           "heard": "unknown", "confidence": 0.0}
                          for i in range(n)],
            "words": word_diff(ref, "", lang), "prototype": True, "label": LABEL}


def assess(wav, ref, lang, pinyin=None, words=None, heard=None, reference=None):
    """Judge the take at `wav` against `ref` (and `pinyin`, for the tones).

    `words`: whisper's `[{text, start, end}]`; `heard`: the transcript;
    `reference`: a WAV of the same phrase from TTS, for the DTW distance.
    Only Mandarin has its tones checked; other languages get the word diff.
    """
    samples, rate = audio.read_wav(wav)
    secs = len(samples) / float(rate or 1)
    diff = word_diff(ref, heard, lang) if heard is not None else []
    off = [w for w in diff if w["op"] != "equal"]
    said_words = ("heard different words (%s)" % ", ".join(
        "'%s' for '%s'" % (w["heard"], w["target"]) if w["op"] == "wrong"
        else "'%s' missing" % w["target"] if w["op"] == "missing"
        else "'%s' extra" % w["heard"] for w in off[:3])) if off else ""
    if not str(lang).lower().startswith("zh"):
        return {"verdict": said_words or ("every word as written" if heard is not None
                                          else "no transcript to compare"),
                "score": None, "syllables": [], "words": diff, "contour": None,
                "prototype": True, "label": LABEL, "seconds": secs,
                "tones": "only Mandarin tones are checked here"}

    aims = targets(pinyin)
    n = len(aims) or len(han(ref))
    track, rms = f0(samples, rate)
    track = smooth(track)
    st = semitones(track)
    runs = voiced_runs(track)
    spans = from_words(words, n) if n else None
    how = "whisper timings"
    if spans is None:
        spans = merge_to(runs, n, rms) if n else runs
        how = "voiced runs"
    if not n:
        n = len(spans)
    texts = _syllable_texts(ref, lang, n, aims)
    lengths = sorted(b - a for a, b in spans) or [0]
    typical = lengths[len(lengths) // 2]
    out = []
    for i in range(n):
        span = spans[i] if i < len(spans) else None
        aim = aims[i] if i < len(aims) else {"syllable": "", "target": None,
                                             "expect": None}
        if span is None:
            tone, sure, shape = "unknown", 0.0, []
        else:
            tone, sure, shape = classify(st, span,
                                         short=(span[1] - span[0]) < 0.6 * typical)
        out.append({"syllable": texts[i] if i < len(texts) else "",
                    "pinyin": aim["syllable"], "target": aim["target"],
                    "expect": aim["expect"], "heard": tone, "confidence": sure,
                    "start": round(span[0] * HOP, 2) if span else None,
                    "end": round(span[1] * HOP, 2) if span else None,
                    "contour": shape})

    known = [s for s in out if s["heard"] != "unknown" and s["expect"]]
    wrong = [s for s in known if s["heard"] != s["expect"]]
    unsure = [s for s in out if s["heard"] == "unknown"]
    if not out:
        tones_said = "no syllable could be found"
    elif not aims:
        tones_said = "tones heard: %s (no pinyin was given to check them against)" % (
            " ".join(s["heard"] for s in out))
    elif wrong:
        tones_said = "tone off on %s" % ", ".join(
            "%s (heard %s, wanted %s)" % (s["syllable"] or s["pinyin"], s["heard"],
                                          s["expect"]) for s in wrong[:3])
    elif len(unsure) == len(out):
        tones_said = "tones unknown: the pitch could not be read"
    elif unsure:
        tones_said = "tones right where they could be read (%d of %d unsure)" % (
            len(unsure), len(out))
    else:
        tones_said = "every tone right"
    score = (round(100.0 * (len(known) - len(wrong)) / len(known))
             if known else None)
    shape = None
    if reference:
        try:
            gap = dtw(st, contour(reference))
        except (OSError, EOFError, ValueError, audio.Unconvertible):
            gap = None
        if gap is not None:
            shape = {"dtw": round(gap, 2),
                     "similarity": round(math.exp(-gap / 3.0), 2)}
    verdict = "; ".join(x for x in (said_words, tones_said) if x)
    return {"verdict": "%s (%s)" % (verdict, LABEL), "score": score,
            "syllables": out, "words": diff, "contour": shape,
            "segmented_by": how, "voiced_runs": len(runs),
            "prototype": True, "label": LABEL, "seconds": secs}
