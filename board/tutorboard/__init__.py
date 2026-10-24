"""Tutor-Board: a live board for tutoring sessions, organised by what a thing
is about.

    paths, machine, tex         what this machine knows about itself
    net/                        the tailnet, and whether a turn can get out
    limits, reasoning, plain    what a model said and what it may not say
    sessions, subjects          the session store and courses/projects
    course/                     a subject's config, documents and homework
    lesson/                     what is on the board: cards, turns, the slate
    server/                     the HTTP board and its routes
    runner/                     the turns: one fresh provider process each
    sync, code                  the Mac's git sync and coding sessions

Standard library only, everywhere.
"""

__all__ = []
