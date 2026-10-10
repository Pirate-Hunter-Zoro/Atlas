"""What a model thought, and what it said.

Providers often leave a model's deliberation in `content` (`<think>` tags,
harmony channels, bracket markers, or plain prose). On a board the card is
the lesson, pushed and committed with no undo, so nothing trusts a model to
have kept its thinking to itself: the tutor strips it off the wire and
`board write` strips it again for agents this repository does not know.
"""

import re


REASONING_TAGS = ("think", "thinking", "thought", "thoughts", "reason",
                  "reasoning", "reflection", "scratchpad", "analysis",
                  "internal", "monologue")

_TAGS = "|".join(REASONING_TAGS)

# A whole block; the backreference stops `<think>...</see>` swallowing a card.
_PAIRED = re.compile(r"<\s*(%s)\b[^>]*>.*?<\s*/\s*\1\s*>" % _TAGS,
                     re.DOTALL | re.IGNORECASE)
# An unclosed open: thinking hit the token ceiling; all after the tag is thought.
_UNCLOSED = re.compile(r"<\s*(?:%s)\b[^>]*>.*\Z" % _TAGS, re.DOTALL | re.IGNORECASE)
# A close with no open (the provider stripped the opening tag).
_ORPHAN_CLOSE = re.compile(r"^.*<\s*/\s*(?:%s)\s*>" % _TAGS, re.DOTALL | re.IGNORECASE)
# The bracket form, for the models that write markers rather than tags.
_BRACKETED = re.compile(r"\[\s*(%s)\s*\].*?\[\s*/\s*\1\s*\]" % _TAGS,
                        re.DOTALL | re.IGNORECASE)

# OpenAI harmony (gpt-oss): only the `final` channel is for the reader.
_HARMONY_FINAL = re.compile(r"<\|channel\|>\s*final\s*<\|message\|>", re.IGNORECASE)
_HARMONY_OTHER = re.compile(
    r"<\|channel\|>\s*(?:analysis|commentary|critic)[^<]*<\|message\|>"
    r".*?(?=<\|(?:start|end|return|channel)\|>|\Z)", re.DOTALL | re.IGNORECASE)
_HARMONY_TOKEN = re.compile(r"<\|[a-z_]+\|>", re.IGNORECASE)


def _starts_with_reasoning(text):
    """Does this reply open with thinking? The only question the second gate
    may ask: a lesson may mention `<think>` mid-sentence."""
    head = (text or "").lstrip()
    if not head:
        return False
    for rx in (_PAIRED, _UNCLOSED, _BRACKETED):
        m = rx.match(head)
        if m:
            return True
    return bool(_HARMONY_FINAL.match(head) or _HARMONY_OTHER.match(head)
                or head.startswith("<|"))


def strip_reasoning(text, leading_only=False):
    """The answer with the model's private working taken out. `leading_only`
    strips only an opening block, for text that may be a deliberate lesson.
    "" means it was all thinking: retry rather than write an empty card."""
    t = text or ""
    if not t.strip():
        return ""
    if leading_only and not _starts_with_reasoning(t):
        return t

    if _HARMONY_FINAL.search(t):
        t = t[_HARMONY_FINAL.search(t).end():]
        for stop in ("<|return|>", "<|end|>"):
            if stop in t:
                t = t.split(stop)[0]
    else:
        t = _HARMONY_OTHER.sub("", t)
    t = _HARMONY_TOKEN.sub("", t)

    t = _PAIRED.sub("", t)
    t = _BRACKETED.sub("", t)
    # Order matters: pairs first, then orphan closes, then unclosed opens.
    if _ORPHAN_CLOSE.search(t):
        t = _ORPHAN_CLOSE.sub("", t, count=1)
    t = _UNCLOSED.sub("", t)
    return t.strip()


# ---------------------------------------------------------------------------
# thinking with no tag on it
# ---------------------------------------------------------------------------
# Untagged thinking is told by voice: a card is addressed to the student;
# deliberation talks about them in the third person and argues with itself.
# The bar is high (one decisive signal, or two suggestive ones), because
# refusing a real card mid-lesson is its own damage.
_REASONING_STRONG = (
    re.compile(r"\bthe student\b", re.IGNORECASE),
    re.compile(r"^\s*(?:okay|ok|alright|right|so)[,.]?\s+(?:so\s+)?"
               r"(?:the|i|let|we)\b", re.IGNORECASE),
    re.compile(r"^\s*(?:i (?:need to|should|will|must|have to)\b"
               r"|let me\b|let's (?:see|think)\b|first,? i\b"
               r"|i'?m going to (?:read|look|check|think)\b)", re.IGNORECASE),
    # "my previous reply", not "my card": tutors refer to their cards normally.
    re.compile(r"\bmy (?:previous|last|earlier) (?:reply|response|answer|card|turn)\b",
               re.IGNORECASE),
)
_REASONING_HINTS = (
    re.compile(r"\b(?:hmm|wait)\b[,.]", re.IGNORECASE),
    re.compile(r"\blet me (?:think|re-?read|check|reconsider|work)\b", re.IGNORECASE),
    re.compile(r"\bactually,? (?:i|the|it|this)\b", re.IGNORECASE),
    re.compile(r"\b(?:looking|thinking) (?:more )?(?:carefully|about it)\b",
               re.IGNORECASE),
    re.compile(r"\bcard\s+\d{3,4}\b", re.IGNORECASE),
    re.compile(r"\bthey (?:were asked|answered|wrote|said|are asking)\b",
               re.IGNORECASE),
    re.compile(r"\bthe (?:question|card) (?:asked|was asking|is asking)\b",
               re.IGNORECASE),
    re.compile(r"\bso (?:this|that) is (?:incorrect|correct|wrong|right)\b",
               re.IGNORECASE),
)


_ADDRESSES = re.compile(r"\b(?:you|your|yours|you'?re|you'?ll|you'?ve)\b",
                        re.IGNORECASE)


def reads_as_reasoning(text):
    """Is this a model deliberating rather than a card written to the student?
    Nothing can be stripped, so the caller refuses: retry on the wire, write
    nothing at `board write`."""
    t = (text or "").strip()
    if len(t) < 200:
        return False           # too short to be a monologue, and cheap to be wrong about
    # Address to a reader is the discriminator, over the whole text, so a
    # lesson about reasoning models passes.
    if _ADDRESSES.search(t):
        return False
    head = t[:1200]
    for rx in _REASONING_STRONG:
        if rx.search(head):
            return True
    hits = sum(1 for rx in _REASONING_HINTS if rx.search(head))
    return hits >= 2


# Shown in place of a monologue card that reached disk another way (an agent
# writing `live/cards/` itself), by every reader: never silence, so nobody
# waits on a turn that did not land.
THINKING_NOTICE = ("*The tutor's own working ended up here instead of a lesson, "
                   "so it is not shown. Ask again — the next turn will be a "
                   "card.*")


def card_body(body):
    """A card body as it should be read, whoever wrote the file."""
    return THINKING_NOTICE if reads_as_reasoning(body) else body
