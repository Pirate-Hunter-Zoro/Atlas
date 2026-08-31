---
kind: question
title: Keeping it. But the permission is not what pins the compiling here
---

**Kept.** `homework/*/build/` stays tracked, the PDF stays on GitHub. Nothing to
undo.

One thing in the reason does not hold, and it is worth having straight because
you will lean on it later.

The permission is an edit to `.claude/settings.local.json`, and I have just
checked how it reached here: **it is not tracked by git.** `.claude/` has never
been added — it is not ignored either, simply never committed — so the file did
not arrive through the remote. It is local to this machine, dated 18:46.

That cuts against the conclusion rather than for it. The allow list is a
property of *a clone*, not of the repository, so it designates nothing. What the
compute node is permitted to do is decided by the node's own copy of that file,
which I cannot see from here and which no push will ever change.

Nor is the choice always somebody's to make. A save compiles the write-up when
the `.tex` is newer than the `.pdf` — that is deliberate, so a pushed document is
never behind its source. So the node recompiles the moment anyone edits the
`.tex` there and saves, without deciding to. And this repository's `.gitignore`
says outright that build products and compiled PDFs are all tracked, so that
build gets committed.

So "we will only ever compile here" is a habit, and habits are not what stopped
the bleeding. What stopped it is the merge step in the push script: it now
integrates the other side and resolves a `build/` collision to whichever machine
just built. Keeping the artifacts tracked is fine **because** of that fix, not
because contention has become impossible.

---

**Your move.** The sheet is done, compiled and pushed. Nothing is outstanding.

From the handoff: you improvised the law of total probability and Bayes on
Ross 39 before either had a name, and conditioned twice unprompted on 41. That
is most of a chapter you have not formally been taught.

Start on conditional probability properly — independence and the multiplication
rule — or stop here for tonight?
