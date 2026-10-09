#!/usr/bin/env python3
"""A subject's contract, handoff, plans and threads become RULES.md and TUTOR.md.

    migrate-memory.py <subject>... [--draft [--force]] [--atlas ROOT]
    migrate-memory.py --all [--draft [--force]] [--atlas ROOT]

<subject> is `courses/<Name>` or `projects/<Name>`. --all takes every subject
that still holds one of SOURCES.

--draft   Write a first RULES.md and TUTOR.md from the sources, where none
          exists (--force overwrites). RULES.md gets the bold lead of each
          "rules that do not bend" bullet and a data fence's refusal list;
          TUTOR.md gets the four sections, the owner's DIRECTION.md under
          "Now", every open threads.json task as a `- [ ]` line and every
          open decision as a bullet. A draft is raw material: it is cut and
          rewritten by hand, against the sources, before it is committed.
(default) Check the files that are there, and exit 1 on any failure:
          - TUTOR.md has exactly the four sections, in order, and at most
            `memo.WORDS` words; RULES.md at most RULES_WORDS.
          - Every open threads.json task appears on a `- [ ]` line of
            TUTOR.md: its whole text, or the fragment CONDENSED records for
            it where the task was shortened or merged to fit the cap.
          - Every open decision (a null `rule`) appears in "Open decisions",
            the same way.
          - A subject whose AI_INSTRUCTIONS.md has a data fence has a
            RULES.md that names `phi/`.
          - Neither file names a retired command or file (RETIRED).

The sources are read only here, and T30c deleted them; the check still
reads the RULES.md and TUTOR.md that are there. Stdlib only.
"""

import argparse
import json
import os
import re
import sys

BOARD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BOARD)

from tutorboard import memo, subjects                      # noqa: E402

ATLAS = os.path.dirname(BOARD)

RULES_WORDS = 300

# What T30c retires, by name, at the subject's root (the TODO files under
# planning/).
SOURCES = ["AI_INSTRUCTIONS.md", "HANDOFF.md", "DIRECTION.md", "PLAN.md",
           "PROGRESS.md", "threads.json", "planning/PSYCH-ASR_TODO.txt",
           "planning/LOCAL-LLM_TODO.txt"]

# Machinery that no longer exists. A memory file naming it sends a turn
# after something it cannot find.
RETIRED = [r"\bboard thread\b", r"\bboard note\b", r"\bboard hold\b",
           r"\bboard coach\b", r"\bboard handoff\b", r"\bboard direction\b",
           r"\blive/", r"\bNEXT\.md\b", r"\bAI_INSTRUCTIONS\.md\b",
           r"\bDIRECTION\.md\b", r"\bPROGRESS\.md\b", r"\bPLAN\.md\b"]

# Open tasks and open decisions that were shortened or merged to keep
# TUTOR.md under its cap: subject -> {source text: the fragment TUTOR.md
# carries}. Everything not listed appears whole.
CONDENSED = {
    "projects/TRD-EHR": {
        # knn-across-embedders
        "Learn: why ROC AUC against k has its shape: the random arm at 1/2, "
        "k = 1, the climb in log k, the right edge, and why every best k is "
        "optimistic":
            "why ROC AUC against k has its shape",
        "Bring the new figures to the Mac (owner marks each PNG aggregate) "
        "or build on the cluster, then rebuild parts/ and run "
        "scripts/rebuild-packet.sh --strict. Every .docx and .pdf predates "
        "the 2026-10-05 text":
            "Bring the new figures to the Mac",
        "Once the owner marks cross_embedder_retrieval.csv aggregate and it "
        "crosses, confirm the dimension counts (253, 271, 1,626, 236) and "
        "best k exactly against it; Figure 6 already agrees to marker "
        "precision":
            "confirm the dimension counts (253, 271, 1,626, 236)",
        # reviewer-findings
        "Ask Martin whether the corresponding author moves to him "
        "(2026-09-29 ink round, item 1)":
            "corresponding author (2026-09-29 ink round, item 1)",
        "Martin accepts or reverts items 2-14 of the 2026-09-29 ink round, "
        "each a rewrite of his sentences":
            "Martin accepts or reverts items 2-14",
        "Ask Martin about the title, which now names retrieval and "
        "propagates to the cover letter and checklist":
            "the title, which now names retrieval",
        "Ask Martin whether Limitations stays. If it goes, its two unique "
        "sentences move to Methods and to Implications and future "
        "directions":
            "whether Limitations stays",
        "Ask Martin whether the similarity judge stays in reserve or returns "
        "as a supplement section":
            "whether the similarity judge stays in reserve",
        "Ask Martin the Discussion's take-home: parity with the published "
        "literature, or parity between the two representations":
            "the Discussion's take-home",
        "Ask Martin whether the sparsity sentence (385 of 4,096 dimensions) "
        "gets a clause, since a re-render selects a dense fit of equal "
        "discrimination":
            "the sparsity sentence (385 of 4,096 dimensions)",
        "Once his text is settled, deterministic to algorithmic in 18 "
        "places, rewriting the manuscript.md naming rule in the same edit":
            "deterministic to algorithmic in 18 places",
        "Once his text is settled, patient to participant (about 261 "
        "places), never in the title, the verbatim narratives or quoted "
        "prior work":
            "patient to participant (about 261 places)",
        "Once his text is settled, trained classifier to machine learning "
        "model only where it is generic; where it contrasts with the "
        "neighbour predictor say the fitted models":
            "trained classifier to machine learning model",
        "Ask Martin whether S12.1 quotes the bootstrap intervals for "
        "sensitivity, specificity and likelihood ratios (job 2120643), and "
        "tell him Table S4's retrieval rows now use Figure S5's equal-count "
        "bins":
            "whether S12.1 quotes the bootstrap intervals",
        # consistency-pass
        "Clarity pass on our sections, one per turn, starting with "
        "Discrimination and Calibration. Numbers are frozen and diffed "
        "before and after; the owner reads each one before the next":
            "Clarity pass on our sections, one per turn",
        "Make scripts/rebuild-packet.sh resolve the sections' "
        "../results/*.png from exports/results/, so the packet builds on "
        "this Mac with every panel":
            "resolve the sections' ../results/*.png from exports/results/",
        "S7 mismatch: the redraw split bge-small into 14,437/28,142 with "
        "nested silhouette 0.70; supplement Tables S5-S6 say 14,438/28,141 "
        "and 0.69. Re-run the clustering with a fixed seed through board "
        "job, printing the nested subgroup sizes as REL":
            "S7 mismatch",
        "Re-run the paper reviewer over the new KNN section and answer what "
        "it finds":
            "Re-run the paper reviewer over the new KNN section",
        "Check every TRIPOD+AI row against the current sections after the "
        "KNN section":
            "Check every TRIPOD+AI row against the current sections",
        "Check that every number, figure, table and S-section reference "
        "agrees across the four documents":
            "agrees across the four documents",
        "Rebuild the packet with scripts/rebuild-packet.sh --strict and "
        "check that no panel moved":
            "check that no panel moved",
        # suicidality-window
        "Give suicidality_flag an explicit window, the way psych_utilization "
        "takes one, or state the precondition in its docstring":
            "Give suicidality_flag an explicit window",
        # estimand-identification
        "Learn: the target trial at the index anchor, its treatment, "
        "eligibility, time zero and outcome":
            "the target trial at the index anchor",
        "Learn: gradeable against ungradeable predictions, and why the arm "
        "actually received is the only performance evidence":
            "gradeable against ungradeable predictions",
        "Learn: conditional independence, and why confounding by indication "
        "survives adjustment for measured covariates":
            "why confounding by indication survives adjustment",
        "Learn: why the 0.10/0.90 trim changes the estimand to the overlap "
        "population":
            "why the 0.10/0.90 trim changes the estimand",
        "Learn: the four-rung robustness ladder, and what each rung can and "
        "cannot rule out":
            "the four-rung robustness ladder",
        # counterfactual-pipeline
        "Build: pull the per-arm calibration bin table out of "
        "grade_arm_models into its own function, and have run_one.py "
        "persist it per arm":
            "per-arm calibration bin table out of grade_arm_models",
        "Build: one folder per contrast carrying the SMD table, the E-value "
        "and its benchmark table, and the negative-control result beside "
        "what is there now":
            "one folder per contrast",
        # balance-smd, overlap-positivity, e-value, negative-control
        "Coach: the owner writes the SMD per covariate from "
        "balance_frame.csv, as mean difference over pooled SD":
            "the SMD per covariate from balance_frame.csv",
        "Coach: the owner decides how a multi-level categorical field "
        "becomes balance rows":
            "multi-level categorical field becomes balance rows",
        "Coach: the owner writes the overlap coefficient, the integrated "
        "minimum of the two arm-conditional e(x) densities":
            "the overlap coefficient",
        "Coach: the owner writes the E-value on the point estimate and on "
        "the CI limit nearest the null":
            "the E-value on the point estimate",
        "Coach: the owner writes both risk-ratio arrows for every measured "
        "covariate, the benchmark the E-value is read against":
            "both risk-ratio arrows for every measured covariate",
        "Coach: the owner chooses the negative-control outcome and argues "
        "why it qualifies":
            "chooses the negative-control outcome",
        "Build: extract that outcome's label from the raw diagnosis tables, "
        "as a second binary label the pipeline can re-run against":
            "label from the raw diagnosis tables",
        # open decisions
        "Where the sensitivity-label decline's reason goes: Limitations or "
        "the covering note":
            "sensitivity-label decline's reason",
        "A window parameter, or a stated precondition":
            "a window parameter or a stated precondition",
        "The symmetric 0.10/0.90 band, or a rule that adapts to arm "
        "prevalence":
            "The symmetric 0.10/0.90 band",
        "Further balance measures (variance ratios, a distributional "
        "distance)":
            "Further balance measures",
    },
    "projects/PSYCH-ASR": {
        "Add a duration check to the 1a seam: check_segment_contract takes "
        "the audio duration and fails a typist whose last segment ends far "
        "short of it":
            "Add a duration check to the 1a seam",
        "Canary transcribes only the first 17.8 s of a session. Chunked "
        "inference would fix it, if canary is worth that work":
            "Canary transcribes only the first 17.8 s",
        "Build the reference RTTM: re-align the reference transcript's "
        "words to the audio and write measured word times. The job reads "
        "the reference locally and prints counts only":
            "Build the reference RTTM",
        "Then compare two aligners on the same words: the large wav2vec2 "
        "bundle, or one built for forced alignment, against the current one":
            "compare two aligners on the same words",
        "Build: widen run_typist_bakeoff.sh's driver to two aligners, 8 runs "
        "of 1a beside 5 of 1b, and join every cell that lands. Every "
        "grid-aware caller passes --stem":
            "widen run_typist_bakeoff.sh's driver to two aligners",
        "The owner's own: listen to the recording beside its diarized "
        "transcript":
            "listen to the recording beside its diarized transcript",
        "Is canary-1b-flash worth chunked inference, given parakeet already "
        "covers the NVIDIA design":
            "Is canary-1b-flash worth chunked inference",
        "How an arm is measured against the reference transcript":
            "How an arm is measured against the reference",
    },
    "projects/libr-local-llm": {
        "Walltime: both sbatch files default to 8 h. Decide whether a "
        "longer-lived server is wanted on c3; ollama-up takes an hours "
        "argument for shorter ones":
            "whether a longer-lived ollama server is wanted on c3",
        "Raise coder's webfetch from ask to allow, leave websearch at ask "
        "and the top-level deny alone; opencode agent list must show every "
        "other agent still at deny":
            "Raise coder's webfetch from ask to allow",
        "Build the vllm path for PSYCH-ASR Stage 3c, fleet milestone M0/M1: "
        "scrub SLURM_* before any srun or sbatch, and expect a multi-minute "
        "cold load":
            "Build the vllm path for PSYCH-ASR Stage 3c",
        "Learn: the PHI fence, and why coli-code's session root ends in a "
        "directory named phi":
            "why coli-code's session root ends in a directory named phi",
        "Learn: the three layers of the PHI boundary, and why the clinical "
        "model never runs through opencode":
            "the three layers of the PHI boundary",
        "Learn: what names_phi checks before a push or a save, and what only "
        "a hosted turn's judgement can catch":
            "what names_phi checks before a push or a save",
        "Learn: the cluster's partitions and nodes, the A40s, the 1 TB node, "
        "and why NVLink being inactive favours replicas over shards":
            "the cluster's partitions and nodes",
        "Learn: the measured rates, 51 tok/s per user on one A40 for the 30B "
        "helper against 3.2-4.4 tok/s for the 744B model":
            "the measured rates",
        "Build the deck once the owner has had the learn sittings on the PHI "
        "path and the hardware":
            "Build the deck",
        "Whether MTP is forced off; one A/B on a warm server settles it":
            "Whether MTP is forced off",
    },
}


def _norm(text):
    return " ".join(str(text or "").split())


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def threads(root):
    """(open task texts, open decision questions) from threads.json."""
    raw = _read(os.path.join(root, "threads.json"))
    if raw is None:
        return [], []
    data = json.loads(raw)
    tasks, open_decisions = [], []
    for th in data.get("threads", []):
        if th.get("closed"):
            continue
        for t in th.get("tasks", []):
            if not t.get("done"):
                tasks.append(_norm(t.get("text")))
        for d in th.get("decisions", []):
            if not d.get("rule"):
                open_decisions.append(_norm(d.get("q")))
    return tasks, open_decisions


def sections(text):
    """[(level-2 heading, body)] of a markdown file, in order."""
    out, name, body = [], None, []
    for line in (text or "").splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m and not line.startswith("###"):
            if name is not None:
                out.append((name, "\n".join(body)))
            name, body = m.group(1), []
        elif name is not None:
            body.append(line)
    if name is not None:
        out.append((name, "\n".join(body)))
    return out


def _fragment(subject, text):
    return _norm(CONDENSED.get(subject, {}).get(text, text))


def _has(haystack_lines, fragment):
    want = fragment.lower()
    return any(want in _norm(line).lower() for line in haystack_lines)


def _fenced(root):
    """Whether the subject's contract has a data-fence section."""
    text = _read(os.path.join(root, "AI_INSTRUCTIONS.md")) or ""
    return bool(re.search(r"^## The data fence", text, re.M))


def check(atlas, subject):
    """The failures for one subject, as sentences; [] when it passes."""
    root = os.path.join(atlas, subject)
    fails = []
    tutor = _read(os.path.join(root, memo.TUTOR))
    rules = _read(os.path.join(root, memo.RULES))
    if tutor is None:
        return ["%s: no TUTOR.md" % subject]
    n = memo.word_count(tutor)
    if n > memo.WORDS:
        fails.append("%s: TUTOR.md is %d words, over %d"
                     % (subject, n, memo.WORDS))
    have = [name for name, _ in sections(tutor)]
    if have != list(memo.SECTIONS):
        fails.append("%s: TUTOR.md sections are %r, not %r"
                     % (subject, have, list(memo.SECTIONS)))
    if rules is not None and memo.word_count(rules) > RULES_WORDS:
        fails.append("%s: RULES.md is %d words, over %d"
                     % (subject, memo.word_count(rules), RULES_WORDS))
    tasks, open_decisions = threads(root)
    boxes = [line for line in tutor.splitlines()
             if line.lstrip().startswith("- [ ]")]
    for t in tasks:
        if not _has(boxes, _fragment(subject, t)):
            fails.append("%s: open task missing from TUTOR.md: %s"
                         % (subject, t))
    body = dict(sections(tutor)).get("Open decisions", "")
    bullets = [line for line in body.splitlines()
               if line.lstrip().startswith("- ")]
    for q in open_decisions:
        if not _has(bullets, _fragment(subject, q)):
            fails.append("%s: open decision missing from TUTOR.md: %s"
                         % (subject, q))
    if _fenced(root) and "phi/" not in (rules or ""):
        fails.append("%s: the contract has a data fence and RULES.md does "
                     "not carry it" % subject)
    for name, text in (("TUTOR.md", tutor), ("RULES.md", rules or "")):
        for pat in RETIRED:
            m = re.search(pat, text)
            if m:
                fails.append("%s: %s names retired %r"
                             % (subject, name, m.group(0)))
    return fails


# --- drafts -----------------------------------------------------------------

def _rule_leads(contract):
    """The bold lead of each bullet under "The rules that do not bend"."""
    m = re.search(r"^### The rules that do not bend\n(.*?)(?=^## |\Z)",
                  contract, re.M | re.S)
    if not m:
        return []
    return [_norm(x) for x in re.findall(r"^- \*\*(.+?)\*\*", m.group(1),
                                         re.M)]


def _fence_list(contract):
    """The refusal bullets of a data-fence section, first line each."""
    m = re.search(r"^## The data fence.*?\n(.*?)(?=^### |^## )",
                  contract, re.M | re.S)
    if not m:
        return []
    return [_norm(x) for x in re.findall(r"^- (.+)$", m.group(1), re.M)]


def draft(atlas, subject, force=False):
    """Write the drafts that are missing (all of them with `force`)."""
    root = os.path.join(atlas, subject)
    contract = _read(os.path.join(root, "AI_INSTRUCTIONS.md")) or ""
    wrote = []
    rules_path = os.path.join(root, memo.RULES)
    leads = _rule_leads(contract) + _fence_list(contract)
    if leads and (force or not os.path.exists(rules_path)):
        with open(rules_path, "w", encoding="utf-8") as fh:
            fh.write("# Rules\n\n" + "".join("- %s\n" % x for x in leads))
        wrote.append(rules_path)
    tutor_path = os.path.join(root, memo.TUTOR)
    if force or not os.path.exists(tutor_path):
        name = os.path.basename(subject)
        text = subjects._tutor_md(name)
        direction = _read(os.path.join(root, "DIRECTION.md"))
        tasks, open_decisions = threads(root)
        now = []
        if direction:
            now.append("Owner's direction: " + _norm(
                re.sub(r"<!--.*?-->", "", direction)))
        now += ["- [ ] %s" % t for t in tasks]
        text = memo.replace_section(text, "Now", "\n".join(now))
        text = memo.replace_section(
            text, "Open decisions",
            "\n".join("- %s" % q for q in open_decisions))
        with open(tutor_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        wrote.append(tutor_path)
    return wrote


def holders(atlas):
    """Every subject that still holds one of SOURCES."""
    out = []
    for kind in ("courses", "projects"):
        base = os.path.join(atlas, kind)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            root = os.path.join(base, name)
            if any(os.path.exists(os.path.join(root, s)) for s in SOURCES):
                out.append("%s/%s" % (kind, name))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("subject", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--atlas", default=ATLAS)
    args = ap.parse_args(argv)
    atlas = os.path.abspath(args.atlas)
    todo = holders(atlas) if args.all else args.subject
    if args.all and not todo:
        print("no subject holds any of the old files: nothing to migrate")
        return 0
    if not todo:
        ap.error("name a subject, or --all")
    if args.draft:
        for s in todo:
            for path in draft(atlas, s, force=args.force):
                print("wrote %s" % os.path.relpath(path, atlas))
        return 0
    fails = []
    for s in todo:
        mine = check(atlas, s)
        fails += mine
        root = os.path.join(atlas, s)
        print("%-32s %s  TUTOR.md %d words, RULES.md %s" % (
            s, "FAIL" if mine else "ok",
            memo.word_count(_read(os.path.join(root, memo.TUTOR)) or ""),
            ("%d words" % memo.word_count(_read(os.path.join(root, memo.RULES))))
            if os.path.exists(os.path.join(root, memo.RULES)) else "none"))
    for f in fails:
        print("  " + f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
