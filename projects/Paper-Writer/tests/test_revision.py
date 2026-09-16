"""A job that names a document it is correcting edits that document, and only it.

The board's library page writes what somebody said is wrong with a delivered
manuscript into a file beside it and drops a job here naming both. Until this path
existed that job was admitted as a fresh paper: it re-mined the evidence, re-fixed
the terminology, re-planned the manuscript from the claims list and wrote a new one —
which is how a correction becomes a different paper.

What is guarded here is that it does not. The three deciding stages are skipped, the
delivered sections come back off disk as they were written, the outline gate never
runs on a document that already exists, and the author's words lead every editorial
pass.

Every model seam is stubbed, as everywhere else in this suite. The import is a parse
and the brief is a quotation, so the whole revision path is deterministic — which is
the reason it can be tested at all.
"""

import support                                                      # noqa: F401
import unittest                                                     # noqa: E402
from pathlib import Path                                            # noqa: E402
import shutil                                                       # noqa: E402
import tempfile                                                     # noqa: E402

from paperwriter import config, jobspec, paths, states               # noqa: E402
from paperwriter.gates import length                                 # noqa: E402
from paperwriter.infra import journal, storage                       # noqa: E402
from paperwriter.stages import outlining, review, revision           # noqa: E402


DELIVERED = """---
title: "Fixture Paper"
author:
  - "A Writer"
---

# Abstract

The embedded representation separated the two outcome groups more sharply than the
feature representation did. Area under the curve reached 0.7429 on the held-out
split. The gap held under a second draw of the split.

# Methods

Both representations were scored on one frozen split of 8516 patients, so the
comparison is paired. The source extract held 42579 patients before the eligibility
filters ran. Most of the loss came from the diagnosis window rather than from missing
data.

# Data availability

The extract is not public.
"""

FEEDBACK = """# Feedback on Fixture Paper

- document: `manuscripts/fixture-paper.md`
- about page 2

Section 2 says the split is paired and never says what the pairing buys. Say it.
"""


def _job(document, feedback="", workspace="", venue="Journal of Fixtures. 4000 word "
                                                    "limit."):
    """A filled template naming a document to correct."""
    return f"""# Fixture Paper

## Evidence

fixture analysis

## Claims

- Something the planner would happily turn into a whole new paper.

## Venue

{venue}

## Reporting checklist

TRIPOD+AI

## Scope

1 paper.

## Revision

document: {document}
{f"feedback: {feedback}" if feedback else ""}
{f"workspace: {workspace}" if workspace else ""}

## Anything the harness cannot work out

Nothing.
"""


class ReadingTheSection(unittest.TestCase):
    """`## Revision` is read, and its absence is what makes a job a new paper."""

    def test_a_new_papers_job_names_no_revision(self):
        self.assertEqual(jobspec.revision(support.PROMPT), {})

    def test_the_fields_are_read(self):
        spec = jobspec.revision(_job("manuscripts/m.md", "manuscripts/f.md", "/w"))
        self.assertEqual(spec["document"], "manuscripts/m.md")
        self.assertEqual(spec["feedback"], "manuscripts/f.md")
        self.assertEqual(spec["workspace"], "/w")

    def test_a_path_keeps_its_trailing_punctuation(self):
        """The prose cleaner strips `-` and `_` from both ends of a list item, and a
        workspace at `/data/psych-asr_` is then a workspace that does not exist."""
        spec = jobspec.revision(_job("m.md", workspace="/data/psych-asr_"))
        self.assertEqual(spec["workspace"], "/data/psych-asr_")

    def test_a_revision_naming_nothing_is_not_one(self):
        """Read as an ordinary job rather than guessed at."""
        self.assertEqual(jobspec.revision("# P\n\n## Revision\n\nfix it please\n"), {})

    def test_the_templates_own_example_is_not_read_as_a_job(self):
        """PROMPT_TEMPLATE.md illustrates the section inside an HTML comment, and a
        parser that looks through comments reads the illustration as a document."""
        template = Path(__file__).resolve().parent.parent / "PROMPT_TEMPLATE.md"
        if not template.exists():                       # pragma: no cover
            self.skipTest("no template in this checkout")
        self.assertEqual(jobspec.revision(template.read_text(encoding="utf-8")), {})


class TakingTheDocumentApart(unittest.TestCase):

    def test_front_matter_gives_the_title_and_the_authors(self):
        title, authors = revision.front_matter(DELIVERED)
        self.assertEqual(title, "Fixture Paper")
        self.assertEqual(authors, ["A Writer"])

    def test_it_splits_on_the_headings_the_builder_wrote(self):
        parts = revision.split_document(DELIVERED)
        self.assertEqual([h for h, _b in parts],
                         ["Abstract", "Methods", "Data availability"])
        self.assertIn("0.7429", parts[0][1])
        self.assertNotIn("#", parts[0][1])

    def test_prose_above_the_first_heading_is_refused_rather_than_dropped(self):
        with self.assertRaises(RuntimeError) as caught:
            revision.split_document("A stray sentence.\n\n# Abstract\n\nText.\n")
        self.assertIn("first heading", str(caught.exception))

    def test_a_document_with_no_headings_is_refused(self):
        with self.assertRaises(RuntimeError):
            revision.split_document("Just prose, no headings at all.\n")


class DeliveredSectionsAreNotRebudgeted(unittest.TestCase):
    """The length gate's absolute floor is about a section being written. A section
    that was delivered is not being written."""

    def test_a_short_delivered_section_passes(self):
        self.assertFalse(length.check(40, budget=40).passed)
        self.assertTrue(length.check(40, budget=40, absolute=0).passed)

    def test_and_the_band_around_it_still_holds(self):
        self.assertFalse(length.check(4000, budget=40, absolute=0).passed)

    def test_an_ordinary_section_keeps_the_floor(self):
        self.assertFalse(length.check(40, budget=400).passed)


class RevisingEndToEnd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        support.stub_model_seams()

    def setUp(self):
        support.wipe_state()
        self.workspace = Path(tempfile.mkdtemp(prefix="paperwriter-test-ws-"))
        self.addCleanup(shutil.rmtree, self.workspace, ignore_errors=True)
        (self.workspace / "manuscripts" / "feedback").mkdir(parents=True)
        self.document = self.workspace / "manuscripts" / "fixture-paper.md"
        self.document.write_text(DELIVERED, encoding="utf-8")
        self.feedback = (self.workspace / "manuscripts" / "feedback"
                         / "fixture-paper-2026-09-16-v1.md")
        self.feedback.write_text(FEEDBACK, encoding="utf-8")

    def _run(self, pid="fixture-revision", **kwargs):
        support.drop(pid, prompt=_job(
            "manuscripts/fixture-paper.md",
            feedback="manuscripts/feedback/fixture-paper-2026-09-16-v1.md",
            workspace=str(self.workspace), **kwargs))
        return support.run_engine(pid), pid

    def test_it_completes(self):
        status, pid = self._run()
        self.assertEqual(status, states.PROJECT_COMPLETE,
                         journal.load_records().get(journal.project_key(pid), {})
                         .get("error"))

    def test_nothing_is_gathered_grounded_or_planned_by_a_model(self):
        """The three stages that decide what the paper IS are skipped. Their
        artifacts are the evidence of that: a revision has no frozen evidence and no
        grounding, and its plan is the one this path derived."""
        _status, pid = self._run()
        self.assertFalse(paths.evidence_path("fixture analysis").exists())
        self.assertFalse(paths.grounding_path(pid).exists())
        plan = storage.load_json(paths.plan_path(pid), {})
        self.assertEqual(plan.get("claims"), [])
        self.assertEqual(plan["revision"]["named"], "manuscripts/fixture-paper.md")

    def test_the_outline_gate_never_runs(self):
        """It asks whether a proposed plan is a well-formed manuscript, which is a
        question about a document that does not exist yet."""
        calls = []
        real = outlining.propose_outline

        def spy(*args, **kwargs):
            calls.append(args)
            return real(*args, **kwargs)

        outlining.propose_outline = spy
        self.addCleanup(setattr, outlining, "propose_outline", real)
        self._run()
        self.assertEqual(calls, [])

    def test_the_delivered_sections_come_back_as_they_were_written(self):
        _status, pid = self._run()
        outline = storage.load_json(paths.outline_path(pid, 1), {})
        self.assertEqual([s["heading"] for s in outline["sections"]],
                         ["Abstract", "Methods", "Data availability"])
        self.assertTrue(all(s["delivered"] for s in outline["sections"]))
        first = paths.section_path(pid, 1, 1).read_text(encoding="utf-8")
        self.assertIn("0.7429", first)

    def test_the_manuscript_is_the_document_again_not_a_new_one(self):
        _status, pid = self._run()
        text = paths.manuscript_path(pid, 1).read_text(encoding="utf-8")
        for heading in ("# Abstract", "# Methods", "# Data availability"):
            self.assertIn(heading, text)
        self.assertIn("The extract is not public.", text)
        self.assertNotIn(support.CLEAN_PROSE.split(".")[0], text)
        self.assertIn('title: "Fixture Paper"', text)
        self.assertIn("A Writer", text)

    def test_it_is_delivered(self):
        _status, pid = self._run()
        delivered = list((config.OUT_DIR / pid).rglob("manuscript.md"))
        self.assertEqual(len(delivered), 1, delivered)

    def test_every_section_is_swept_with_the_authors_words_leading(self):
        """The feedback is what the editor reads first, on every section and every
        sweep — not a defect a gate found."""
        seen = []

        def capture(project_rec, paper_num, section_num, prose, truth, gate_brief,
                    pass_num, log_fn=None):
            seen.append((section_num, gate_brief))
            return {"issues": [], "structural": []}

        real = review.model_review
        review.model_review = capture
        self.addCleanup(setattr, review, "model_review", real)
        self._run()
        # Every section, and section 3 twice: a forty-word statement fails the
        # sentence and paragraph gates on its own, so the sweep gives it the second
        # round `revising.flagged` owes anything that yielded blocking findings.
        self.assertEqual(sorted(set(n for n, _b in seen)), [1, 2, 3])
        for _n, brief in seen:
            self.assertIn("THIS IS A REVISION", brief)
            self.assertIn("what the pairing buys", brief)
            self.assertLess(brief.index("THIS IS A REVISION"), 200)

    def test_a_document_that_is_not_there_stalls_with_a_usable_error(self):
        support.drop("missing-doc", prompt=_job("manuscripts/nowhere.md",
                                                workspace=str(self.workspace)))
        status = support.run_engine("missing-doc", limit=6)
        self.assertEqual(status, states.STALLED)
        record = journal.load_records()[journal.project_key("missing-doc")]
        self.assertIn("no such file", record["error"])
        self.assertIn("workspace:", record["error"])

    def test_a_built_format_is_refused_rather_than_edited(self):
        (self.workspace / "manuscripts" / "fixture-paper.docx").write_bytes(b"PK\x03")
        support.drop("docx-revision", prompt=_job(
            "manuscripts/fixture-paper.docx", workspace=str(self.workspace)))
        status = support.run_engine("docx-revision", limit=6)
        self.assertEqual(status, states.STALLED)
        record = journal.load_records()[journal.project_key("docx-revision")]
        self.assertIn("Name the .md", record["error"])

    def test_an_ordinary_job_is_unaffected(self):
        """The whole pipeline still runs for a job with no Revision section."""
        support.drop("ordinary")
        self.assertEqual(support.run_engine("ordinary"), states.PROJECT_COMPLETE)
        self.assertTrue(paths.grounding_path("ordinary").exists())


if __name__ == "__main__":                                    # pragma: no cover
    unittest.main()
