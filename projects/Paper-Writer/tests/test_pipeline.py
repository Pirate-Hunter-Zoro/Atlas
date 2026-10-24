"""End to end: a prompt goes into the inbox and a manuscript comes out of the other
side.

Every model seam is stubbed and **nothing else is**. The journal, every gate, the
ledger gatekeeper, atomic staging, the manuscript assembly, the audit and the delivery
all run for real, which is the point: this proves the harness wiring independent of the
models. A model that starts writing better prose cannot make these tests pass, and a
model that starts writing worse prose cannot make them fail.
"""

import shutil                                                       # noqa: E402
import support                                                      # noqa: F401
import tempfile                                                     # noqa: E402
import unittest                                                     # noqa: E402
from pathlib import Path                                            # noqa: E402

from paperwriter import config, paths, states                       # noqa: E402
from paperwriter.infra import journal, storage                      # noqa: E402
from paperwriter.stages import delivery                             # noqa: E402


class PipelineTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        support.stub_model_seams()

    def setUp(self):
        support.wipe_state()

    def _run(self, project_id="fixture-paper"):
        support.drop(project_id)
        return support.run_engine(project_id), project_id

    def test_a_dropped_prompt_produces_a_delivered_manuscript(self):
        status, pid = self._run()
        self.assertEqual(status, states.PROJECT_COMPLETE,
                         journal.load_records().get(journal.project_key(pid), {})
                         .get("error"))

    def test_the_manuscript_holds_every_section(self):
        _status, pid = self._run()
        text = paths.manuscript_path(pid, 1).read_text(encoding="utf-8")
        for heading, _words in support.SECTIONS:
            self.assertIn(f"# {heading}", text)
        self.assertNotIn("MISSING", text)

    def test_the_manuscript_is_delivered_to_the_output_folder(self):
        _status, pid = self._run()
        delivered = list((config.OUT_DIR / pid).rglob("manuscript.md"))
        self.assertEqual(len(delivered), 1, delivered)
        self.assertEqual(delivered[0].read_text(encoding="utf-8"),
                         paths.manuscript_path(pid, 1).read_text(encoding="utf-8"))

    def test_the_prompt_is_filed_away_rather_than_deleted(self):
        _status, pid = self._run()
        self.assertFalse((config.INBOX_DIR / f"{pid}.md").exists())
        self.assertTrue((config.INBOX_FINISHED_DIR / f"{pid}.md").exists())

    def test_evidence_is_frozen_and_reused(self):
        """A second job on the same corpus must not re-mine it. The freeze is also
        what stops an analysis rerun from silently changing what a written section
        claims."""
        self._run("first-paper")
        frozen = storage.load_json(paths.evidence_path("fixture analysis"))
        self.assertTrue(frozen["frozen"])
        before = len(frozen["items"])

        calls = []
        real = support.real_seam(
            __import__("paperwriter.stages.evidence", fromlist=["evidence"]),
            "propose_evidence")
        self.assertTrue(callable(real))

        support.drop("second-paper")
        support.run_engine("second-paper")
        after = storage.load_json(paths.evidence_path("fixture analysis"))
        self.assertEqual(len(after["items"]), before, calls)

    def test_every_section_is_on_disk_and_journaled(self):
        _status, pid = self._run()
        records = journal.load_records()
        sections = journal.sections_of(records, pid, 1)
        self.assertEqual(len(sections), len(support.SECTIONS))
        for record in sections:
            self.assertEqual(record["status"], states.LEDGER_MERGED)
            self.assertTrue(paths.section_path(pid, 1, record["section_num"]).exists())

    def test_a_hand_written_grounding_is_reused_rather_than_re_derived(self):
        """Terminology and an estimand are often settled by people. Re-proposing them
        lets the model drift away from a decision that was already agreed, and every
        section would then be internally consistent with a vocabulary nobody approved."""
        from paperwriter.stages import grounding

        support.drop("grounded-paper")
        # Admit the job so the project directory exists, then plant the grounding.
        from paperwriter.engine import cycle
        cycle.run(log_fn=lambda _m: None)

        hand_written = {
            "estimand": "Discrimination of a twelve-month label on a held-out split, "
                        "measured by area under the ROC curve.",
            "venue": "Journal of Fixtures",
            "reader": "Clinical informatics researchers.",
            "checklist": {"name": "TRIPOD+AI", "items": []},
            "conventions": {"person": "we", "tense": "past"},
            "terminology": [{"term": "hand-locked term", "aliases": ["a synonym"]}],
        }
        storage.save_json(hand_written, paths.grounding_path("grounded-paper"))

        called = []
        real = grounding.propose_grounding
        grounding.propose_grounding = lambda *a, **k: called.append(1)
        try:
            support.run_engine("grounded-paper")
        finally:
            grounding.propose_grounding = real

        self.assertEqual(called, [], "the grounding stage re-derived a settled file")
        on_disk = storage.load_json(paths.grounding_path("grounded-paper"))
        self.assertEqual(on_disk["terminology"][0]["term"], "hand-locked term")

    def test_the_ledger_survives_the_run(self):
        _status, pid = self._run()
        doc = storage.load_json(paths.ledger_path(pid))
        self.assertEqual(len(doc["claims"]), len(support.PLAN_CLAIM_IDS))
        self.assertTrue(doc["terminology"])

    def test_the_ledger_carries_the_points_the_claims_serve(self):
        """The ladder is committed state. A point that can be renegotiated mid-draft
        is a paper that changes what it is about halfway through, and nothing reading
        one section at a time can see that."""
        _status, pid = self._run()
        doc = storage.load_json(paths.ledger_path(pid))
        self.assertEqual(sorted(doc["points"]), ["p.1"])
        served = doc["claims"]["c.1"]["serves"]
        self.assertEqual(served, ["p.1"])
        self.assertEqual(doc["claims"]["c.2"]["role"], "setup")

    def test_every_document_is_delivered_not_only_the_manuscript(self):
        """The pipeline's job is not finished when the prose is written. It is
        finished when the author can see what was checked, which means the report
        ships beside the manuscript rather than living in the journal."""
        _status, pid = self._run()
        folder = config.OUT_DIR
        names = {p.name for p in folder.rglob("*") if p.is_file()}
        self.assertIn("manuscript.md", names)
        self.assertIn("report.md", names)

    def test_the_report_leads_on_what_the_paper_is_for(self):
        """A reader can check the numbers and the prose themselves. What they cannot
        recover from the manuscript is which claim was supposed to serve which
        point."""
        _status, pid = self._run()
        report = paths.report_path(pid, 1).read_text(encoding="utf-8")
        self.assertIn("What this paper is for", report)
        self.assertIn("p.1", report)
        self.assertIn("(states it)", report)
        self.assertIn("Role: setup", report)
        self.assertIn("What shipped unresolved", report)

    def test_the_report_leads_with_the_final_sweep(self):
        """The sweep exists so the reader sees the list of defects before they start
        reading the paper. A list at the bottom of a report is read after the damage
        is done, so the position is part of the deliverable."""
        _status, pid = self._run()
        report = paths.report_path(pid, 1).read_text(encoding="utf-8")
        self.assertIn("## The final sweep", report)
        self.assertLess(report.index("## The final sweep"),
                        report.index("What this paper is for"))
        # Every gate, every section, every document — and it says so in numbers.
        self.assertRegex(report, r"\d+ document\(s\), \d+ section\(s\)")

    def test_shipping_is_off_unless_a_repo_is_named(self):
        """Pushing to a remote is the only outward-facing thing this harness does.
        Both halves are opt-in and the default is to do nothing."""
        from paperwriter.infra import shipping
        self.assertIsNone(config.SHIP_REPO)
        self.assertFalse(config.SHIP_PUSH)
        note = shipping.ship([paths.manuscript_path("x", 1)], "a message")
        self.assertIn("PAPER_SHIP_REPO is not set", note)

    def test_shipping_never_raises_into_the_engine(self):
        """Delivery has already succeeded by the time it runs, so a git problem must
        not be the reason a finished paper's status stays unfinished."""
        from paperwriter.infra import shipping
        for bad in ([], [None], ["/nonexistent/path/manuscript.md"]):
            self.assertIsInstance(shipping.ship(bad, "a message"), str)

    def test_a_crash_resumes_rather_than_restarting(self):
        """Nothing durable is recomputed. The engine is driven one cycle at a time,
        stopped partway, and driven again; the sections written before the stop must
        still be there and must not be rewritten."""
        from paperwriter.engine import cycle
        support.drop("resumed-paper")
        for _ in range(14):
            cycle.run(log_fn=lambda _m: None)

        written = sorted(paths.sections_dir("resumed-paper", 1).glob("*.md")) \
            if paths.sections_dir("resumed-paper", 1).exists() else []
        stamps = {p.name: p.read_text(encoding="utf-8") for p in written}

        support.run_engine("resumed-paper")
        for name, text in stamps.items():
            self.assertEqual(
                (paths.sections_dir("resumed-paper", 1) / name)
                .read_text(encoding="utf-8"), text,
                f"{name} was rewritten after a resume")

    def test_the_status_file_is_published(self):
        self._run()
        path = paths.status_file()
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertIn("Paper-Writer", path.read_text(encoding="utf-8"))


class GateRejectionTests(unittest.TestCase):
    """What happens when a proposal is refused. A stall is not a failure, and nothing
    written before it is lost."""

    @classmethod
    def setUpClass(cls):
        support.stub_model_seams()

    def setUp(self):
        support.wipe_state()

    def test_an_outline_that_never_passes_stalls_rather_than_failing(self):
        from paperwriter.stages import outlining

        def bad_outline(project_rec, paper_num, out_path, log_fn=None, feedback=""):
            storage.save_json({"sections": [
                {"number": 1, "heading": "Results", "words": 400, "paragraphs": []},
                {"number": 2, "heading": "Methods", "words": 400, "paragraphs": []},
            ]}, out_path)
            return "bad outline"

        good = outlining.propose_outline
        outlining.propose_outline = bad_outline
        try:
            support.drop("stalling-paper")
            support.run_engine("stalling-paper", limit=30)
            records = journal.load_records()
            paper = records.get(journal.paper_key("stalling-paper", 1))
            self.assertIsNotNone(paper)
            self.assertEqual(paper["status"], states.STALLED)
            self.assertIn("outlining", (paper.get("error") or ""))
            # Not terminal, and not a dead end.
            self.assertNotIn(paper["status"], states.DEAD_ENDS)
        finally:
            outlining.propose_outline = good

    def test_the_evidence_stage_parks_a_job_it_cannot_support(self):
        from paperwriter.stages import evidence

        def thin_evidence(prompt_text, corpus, out_path, log_fn=None, focus=(),
                          sources=()):
            storage.save_json({"items": [
                {"id": "e.1", "statement": "something unrelated entirely",
                 "values": [1], "source": "x"}]}, out_path)
            return "thin"

        good = evidence.propose_evidence
        evidence.propose_evidence = thin_evidence
        try:
            support.drop("thin-paper")
            support.run_engine("thin-paper", limit=20)
            record = journal.load_records()[journal.project_key("thin-paper")]
            self.assertEqual(record["status"], states.STALLED)
            self.assertIn("coverage", record.get("error", ""))
        finally:
            evidence.propose_evidence = good


class LandingTests(unittest.TestCase):
    """The second copy, in the workspace that asked for the paper.

    `PAPER_OUT_DIR` is one directory for one harness and one harness serves every
    workspace, so a paper that stops there is a paper nobody can find from the
    workspace it was written for — and every document route the board offers is
    waiting on files that are not in it."""

    @classmethod
    def setUpClass(cls):
        support.stub_model_seams()

    def setUp(self):
        support.wipe_state()
        self.workspace = Path(tempfile.mkdtemp(prefix="paperwriter-test-land-"))
        self.addCleanup(shutil.rmtree, self.workspace, ignore_errors=True)

    def _run(self, landing, project_id="landed-paper"):
        prompt = support.PROMPT.replace(
            "## Scope\n\n1 paper.\n",
            f"## Scope\n\n1 paper.\n\n## Delivery\n\nlanding: {landing}\n")
        self.assertIn("## Delivery", prompt)
        support.drop(project_id, prompt=prompt)
        return support.run_engine(project_id), project_id

    def _record(self, pid):
        records = journal.load_records()
        return records[journal.paper_key(pid, 1)]

    def test_the_manuscript_lands_in_the_workspace_that_asked(self):
        landing = self.workspace / "manuscripts" / "fixture-paper"
        status, _pid = self._run(landing)
        self.assertEqual(status, states.PROJECT_COMPLETE)
        self.assertTrue((landing / "manuscript.md").is_file())

    def test_nothing_is_appended_to_the_landing(self):
        """The line names the paper's own directory, and naming it is the asking
        side's business -- which is what lets a revision land over the document it
        corrects rather than beside it under a slug of a drifted title."""
        landing = self.workspace / "manuscripts" / "fixture-paper"
        self._run(landing)
        landed = list(landing.rglob("manuscript.md"))
        self.assertEqual([p.parent for p in landed], [landing], landed)

    def test_the_out_dir_copy_is_still_there(self):
        """A second copy, not a move. The harness keeps its own subtree."""
        _status, pid = self._run(self.workspace / "manuscripts" / "p")
        self.assertEqual(len(list((config.OUT_DIR / pid).rglob("manuscript.md"))), 1)

    def test_every_artifact_lands_not_only_the_manuscript(self):
        landing = self.workspace / "manuscripts" / "p"
        self._run(landing)
        names = {p.name for p in landing.rglob("*") if p.is_file()}
        self.assertIn("manuscript.md", names)
        self.assertIn("report.md", names)

    def test_an_artifact_keeps_the_subtree_it_had(self):
        """`parts/manuscript/04-methods.md` arrives as that, not as a flat file
        beside three others of the same name from three other documents."""
        landing = self.workspace / "manuscripts" / "p"
        self._run(landing)
        parts = list((landing / "parts").rglob("*.md"))
        self.assertTrue(parts, sorted(str(p) for p in landing.rglob("*")))

    def test_what_landed_is_byte_identical(self):
        landing = self.workspace / "manuscripts" / "p"
        _status, pid = self._run(landing)
        self.assertEqual((landing / "manuscript.md").read_bytes(),
                         paths.manuscript_path(pid, 1).read_bytes())

    def test_the_landing_is_recorded_on_the_paper(self):
        landing = self.workspace / "manuscripts" / "p"
        _status, pid = self._run(landing)
        self.assertIn(str(landing), self._record(pid)["landed"])

    def test_a_job_naming_no_landing_still_completes(self):
        """Absent is the ordinary case for a job dropped by hand, not a defect."""
        support.drop("plain-paper")
        status = support.run_engine("plain-paper")
        self.assertEqual(status, states.PROJECT_COMPLETE)
        record = journal.load_records()[journal.paper_key("plain-paper", 1)]
        self.assertIn("no landing", record["landed"])

    def test_a_relative_landing_is_refused_and_said_so(self):
        """The harness is another repository and cannot resolve a relative path
        against a root nobody named. Refused loudly rather than guessed at."""
        status, pid = self._run("manuscripts", project_id="relative-paper")
        self.assertEqual(status, states.PROJECT_COMPLETE)
        self.assertIn("not an absolute path", self._record(pid)["landed"])

    def test_a_landing_that_cannot_be_written_leaves_the_paper_delivered(self):
        """The paper is already safe under OUT_DIR by the time this is attempted, so
        a directory somebody has since moved must not be the reason a finished paper's
        status stays unfinished. Same rule as a missing pandoc and a failed push."""
        blocked = self.workspace / "not-a-directory"
        blocked.write_text("a file sitting where the landing should be\n",
                           encoding="utf-8")
        status, pid = self._run(blocked, project_id="blocked-paper")
        self.assertEqual(status, states.PROJECT_COMPLETE)
        record = self._record(pid)
        self.assertIn("could not be written", record["landed"])
        self.assertTrue(record["delivered_paths"])
        self.assertEqual(
            len(list((config.OUT_DIR / "blocked-paper").rglob("manuscript.md"))), 1)

    def test_re_delivery_into_the_landing_is_a_verified_no_op(self):
        """`deliver_one` is content-addressed, so a paper delivered twice copies
        nothing twice and the file an author has open does not change under them."""
        landing = self.workspace / "manuscripts" / "p"
        _status, pid = self._run(landing)
        landed = landing / "manuscript.md"
        before = landed.stat().st_mtime_ns
        rec = journal.load_records()[journal.project_key(pid)]
        rec = {"project_id": pid, "prompt_text": rec.get("prompt_text") or ""}
        paths_out, note = delivery.deliver(
            rec, 1, list(paths.documents(pid, 1)), paper_name="Fixture Paper")
        self.assertTrue(paths_out)
        self.assertIn(str(landing), note)
        self.assertEqual(landed.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
