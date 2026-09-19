// A document that lies is worse than one that is missing, because a missing
// one sends somebody to the code and a lying one does not.
//
// WHY THIS IS A FLEET AND NOT A SESSION. The checkable surface is about eight
// thousand lines of core documentation plus twenty-three workspace files, and
// the check is not reading them — it is reading each claim and then going to
// the code it names. That is one context per surface, and they do not need to
// talk to each other. Five readers, each with its own surface and its own
// copy of the rules.
//
// WHY EVERY FINDING IS THEN ATTACKED. A model asked to find stale prose will
// find stale prose, and most of what it brings back is wording it would have
// chosen differently. Each candidate goes to a second agent whose ONLY job is
// to show the document was right all along, told to default to refuted when
// unsure. What survives that is a fact, and the count of what did not is
// returned too, because a filter nobody can see is a filter nobody trusts.
//
// READ-ONLY, DELIBERATELY. The agents do not edit. The documents are in the
// owner's voice and the corrections are one turn's work once the facts are in
// hand; a fleet rewriting prose in parallel produces five registers and a
// merge conflict. `courses/Galois-Theory` may also have a live session in it.

export const meta = {
  name: 'stale-docs-audit',
  description: 'Find documentation claims in Atlas that the shipped code contradicts, then adversarially verify each',
  whenToUse: 'HANDOFF item 3. Run from a keyboard session; report findings, then fix them by hand in one pass.',
  phases: [
    { title: 'Audit', detail: 'one reader per documentation surface, checking each claim against the code' },
    { title: 'Verify', detail: 'a skeptic tries to show each claimed staleness is actually still true' },
  ],
}

const ROOT = '/mnt/dell_storage/homefolders/librad.laureateinstitute.org/mferguson/Atlas'

const FINDING_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          doc_file: { type: 'string', description: 'repo-relative path of the documentation file' },
          doc_line: { type: 'integer', description: '1-indexed line where the false claim sits' },
          claim: { type: 'string', description: 'the claim, quoted from the doc, trimmed to one sentence' },
          truth: { type: 'string', description: 'what the code actually does now, in one sentence' },
          evidence: { type: 'string', description: 'code path:line that proves it, or the command run and its output' },
        },
        required: ['doc_file', 'doc_line', 'claim', 'truth', 'evidence'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean', description: 'true if the documentation claim is in fact still accurate, so the finding is wrong' },
    why: { type: 'string', description: 'one sentence, citing the file:line you checked' },
  },
  required: ['refuted', 'why'],
}

const RULES = `
You are auditing documentation in the Atlas repository at ${ROOT}.

THE ONE QUESTION: does this document assert something about the CODE, the
COMMANDS, the FILE LAYOUT or the MEASURED NUMBERS that is FALSE as the tree
stands right now? Read the document, then go and read the code it is talking
about, and check. Cite the code.

REPORT ONLY FALSEHOODS OF FACT. A claim is a finding when a reader who believed
it would do the wrong thing: a named function, flag, file, command, env var or
path that does not exist or does not behave as described; a "nothing does X
yet" / "still to be decided" / "not built" statement about something that has
since been built; a number contradicted by a number elsewhere in the tree.

NOT findings, and do not report them: prose style, tone, length, missing
documentation, things you would word differently, opinions about design,
anything you merely suspect without having read the code, or a future plan that
is honestly labelled as a plan. A sentence that reads oddly is not a finding.
Silence is a correct answer — an empty findings list is far better than a
padded one.

DO NOT EDIT ANYTHING. No Write, no Edit, no git commit, no git checkout, no
file mutation of any kind. This is a read-only audit. Read-only git commands
(log, show, diff, ls-files, grep) are fine.

A live session may be working in courses/Galois-Theory. Read it if your surface
covers it; never write there.
`

const SURFACES = [
  {
    key: 'board-readme',
    prompt: `${RULES}

YOUR SURFACE: ${ROOT}/board/README.md — the board's architecture document, and
the longest file in the audit. Check its claims against the code in
${ROOT}/board/ (bin/board, bin/tutor, tutorboard/**, web/**, scripts/**,
test/**).

It is long, so sample with judgement rather than reading every line equally:
prioritise sections that name a function, a module, a command, a flag, a file
path or an env var, since those are the checkable ones. Confirm each named
thing exists with that name and does what the sentence says.`,
  },
  {
    key: 'handoff-settled',
    prompt: `${RULES}

YOUR SURFACE: the "Settled, so nobody re-derives it" section of
${ROOT}/HANDOFF.md, from its heading to the end of the file. Every bullet there
asserts that some rule is SHIPPED and true now. Take the bullets that name
concrete machinery — a function, a file, a test, a flag, a threshold — and
verify each against ${ROOT}/board/. A bullet claiming something is shipped when
the code does not do it is the highest-value finding in this whole audit.

Also check the "Before anything" section near the top: the suite count it
states, the paths it names, and the scripts it tells people to run.`,
  },
  {
    key: 'libr',
    prompt: `${RULES}

YOUR SURFACE: ${ROOT}/projects/libr-local-llm/ — README.md, P0-STATUS.md,
FLEET-BUILD.md, DESIGN.md, AI_INSTRUCTIONS.md and HANDOFF.md. Check them
against bin/* (coli, coli-up, coli-code, coli-ask, coli-down, coli-build,
coli-adopt), the sbatch scripts, and any python under that directory.

Two known drifts have already been corrected in some files and may survive in
others, so report every place either is still stated the old way. First, the
MTP/speculation question: the measured answer is that speculation at draft=1
COSTS about 10 percent on this box and the served configuration leaves it off,
so any file still calling it an open question is wrong. Second, the accidental
pip tree at ~/.local/lib/python3.12: it is deleted and the directory is gone,
so any sentence telling somebody to delete it, or quoting its size as something
still on disk, is wrong.

Also look for internal contradictions: the same number or the same rule stated
two different ways in two of these files.`,
  },
  {
    key: 'workspaces',
    prompt: `${RULES}

YOUR SURFACE: the per-workspace documents —
${ROOT}/courses/Galois-Theory/{README,AI_INSTRUCTIONS,DIRECTION}.md,
${ROOT}/courses/Probability/{README,AI_INSTRUCTIONS}.md,
${ROOT}/research/PSYCH-ASR/{README,AI_INSTRUCTIONS,DIRECTION}.md,
${ROOT}/research/TRD-EHR/{README,AI_INSTRUCTIONS}.md.

These describe how a tutor works in that workspace, which board commands exist,
where files go, and what is tracked. Check them against ${ROOT}/board/ and
against each workspace's own tree and .gitignore.

A known drift to check in every one of them: these files used to describe the
board as a separate clone at ~/Tutor-Board, and it now lives at ${ROOT}/board.
Any file still pointing at the old location is a finding. Likewise any file
describing its workspace as its own git remote when it is a directory inside
the Atlas repository.

Also verify what each file says about what is and is not tracked in git,
against the real .gitignore files and git ls-files. Getting that wrong in a
PUBLIC repository is the one mistake here with a consequence outside the tree.`,
  },
  {
    key: 'paper-writer',
    prompt: `${RULES}

YOUR SURFACE: ${ROOT}/projects/Paper-Writer/ — README.md, AI_INSTRUCTIONS.md,
PROMPT_TEMPLATE.md and any other markdown in there. Check them against that
project's python package and its tests.

Its 517 tests pass, so the code is the source of truth: where a document and
the code disagree, the document is the finding. Check the entry points, the
module names, the config keys and the directory layout it describes. Also check
anything it says about how the board calls it, against ${ROOT}/board/tutorboard/.`,
  },
]

phase('Audit')
log(`auditing ${SURFACES.length} documentation surfaces against the code`)

const VERIFY_CAP = 12
let verified = 0
let dropped = 0

const results = await pipeline(
  SURFACES,
  s => agent(s.prompt, { label: `audit:${s.key}`, phase: 'Audit', schema: FINDING_SCHEMA }),
  (found, surface) => {
    const list = (found && found.findings) || []
    const take = []
    for (const f of list) {
      if (verified < VERIFY_CAP) { verified++; take.push(f) } else { dropped++ }
    }
    if (!take.length) return []
    return parallel(take.map(f => () =>
      agent(`${RULES}

A previous auditor claims this documentation sentence is FALSE. Your job is to
REFUTE that claim — to show the document is in fact still accurate. Go and read
the code yourself; do not take the auditor's evidence on trust.

  document:  ${f.doc_file}:${f.doc_line}
  it says:   ${f.claim}
  auditor says the truth is: ${f.truth}
  auditor's evidence: ${f.evidence}

Set refuted=true if the document is accurate as written, or if the auditor's
evidence does not actually support the claim, or if this is a matter of wording
rather than of fact. Set refuted=false ONLY if you independently confirmed the
document is wrong and can cite where. Default to refuted=true when uncertain: a
false alarm that reaches the owner costs more than a missed nit.`,
        { label: `verify:${f.doc_file.split('/').pop()}:${f.doc_line}`, phase: 'Verify', schema: VERDICT_SCHEMA })
        .then(v => ({ ...f, surface: surface.key, verdict: v }))
    ))
  }
)

if (dropped) {
  log(`NOT VERIFIED: ${dropped} further findings exceeded the ${VERIFY_CAP} verification cap and are not in this result`)
}

const all = results.flat().filter(Boolean)
const confirmed = all.filter(f => f.verdict && f.verdict.refuted === false)
const rejected = all.filter(f => f.verdict && f.verdict.refuted === true)

log(`${all.length} candidates, ${confirmed.length} survived refutation, ${rejected.length} refuted`)

return {
  confirmed,
  rejected_count: rejected.length,
  rejected_summary: rejected.map(f => `${f.doc_file}:${f.doc_line} — ${f.verdict.why}`),
  unverified_dropped: dropped,
}
