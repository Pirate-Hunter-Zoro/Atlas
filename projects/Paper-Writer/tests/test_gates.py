"""The gates. Pure arithmetic over strings and dicts, so these tests need no fixtures
beyond the strings themselves.

This is the largest test module in the project on purpose. The gates are the only thing
standing between a confidently wrong model and a published manuscript, and every one of
them is cheap enough to test exhaustively.
"""

import os                                                          # noqa: E402
import tempfile                                                    # noqa: E402
import zipfile                                                     # noqa: E402
import support                                                      # noqa: F401
from unittest import mock                                           # noqa: E402
import unittest                                                     # noqa: E402

from pathlib import Path                                          # noqa: E402
from paperwriter import config                                    # noqa: E402
from paperwriter.stages import building                           # noqa: E402
from paperwriter.gates import figures                              # noqa: E402
from paperwriter.gates import (citations, crossrefs, claims, coverage, ladder, venue,
                               procedures,
                               repetition,  # noqa: E402
                               length, numbers, paragraphs, polarity, prose,
                               readability, sentences, structure,
                               terminology, venue)


class ProseSplittingTests(unittest.TestCase):
    """Everything else counts what this module splits, so it has to be right."""

    def test_abbreviations_do_not_end_a_sentence(self):
        text = ("Smith et al. reported a similar gap. We used pandas vs. polars for "
                "the join. See Fig. 3 for the curve.")
        self.assertEqual(len(prose.sentences(text)), 3)

    def test_initials_do_not_end_a_sentence(self):
        self.assertEqual(len(prose.sentences("J. R. Smith ran the analysis. It held.")),
                         2)

    def test_decimals_do_not_end_a_sentence(self):
        self.assertEqual(len(prose.sentences("The AUC was 0.74 on the split. It held.")),
                         2)

    def test_a_sentence_ending_in_a_decimal_still_ends(self):
        """A results section reports figures at the ends of sentences. Gluing those to
        the sentence after is how such a section measures as long, welded prose when it
        is nothing of the kind."""
        self.assertEqual(
            prose.sentences("The range runs to 0.657. Discrimination is modest."),
            ["The range runs to 0.657.", "Discrimination is modest."])

    def test_a_bare_integer_and_a_stop_is_still_a_list_marker(self):
        self.assertEqual(len(prose.sentences("1. First item here. 2. Second one.")), 2)

    def test_headings_and_tables_are_not_prose(self):
        text = "# Results\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nThe model did better."
        self.assertEqual(prose.sentences(text), ["The model did better."])

    def test_a_list_item_starts_a_new_sentence(self):
        """A bulleted list is the standard repair for a sentence carrying six things,
        and its stem ends in a colon. Without this boundary the stem and every bullet
        merge into one enormous sentence, so the gate reports the repair as worse than
        the defect it fixes."""
        text = "A patient needed all three of:\n\n- one thing;\n- two thing;\n- three.\n"
        found = prose.sentences(text)
        self.assertEqual(len(found), 4, found)
        self.assertEqual(found[0], "A patient needed all three of:")

    def test_a_caption_ending_in_emphasis_still_closes(self):
        """A figure or table caption is written `***Table 3.** ... *` and ends in `.*`.
        Without emphasis as a closer the caption never terminates and swallows the
        paragraph beneath it, which on a supplement is most of the apparent long
        sentences."""
        text = "***Table 3.** The counts by group.*\n\nThe model did better here.\n"
        self.assertEqual(prose.sentences(text),
                         ["***Table 3.** The counts by group.*",
                          "The model did better here."])

    def test_a_cross_reference_ends_its_sentence(self):
        """"Table 2." at the end of a sentence is a reference, not a list marker.
        Reading it as a marker glued the sentence to the next one, so a paragraph of
        three ordinary sentences measured as one run-on and the long-sentence share
        was driven by the paper's own cross-references."""
        text = ("The values are tabulated in Table 2. A paired bootstrap followed. "
                "The ablation is Figure 9. It reproduced across encoders.")
        self.assertEqual(len(prose.sentences(text)), 4)

    def test_a_bare_numeral_is_still_a_list_marker(self):
        text = "A patient needed all of:\n\n1. one thing.\n2. another thing.\n"
        self.assertEqual(len(prose.sentences(text)), 3)

    def test_a_display_equation_is_not_prose(self):
        """Counting one produces a paragraph with no topic sentence on every
        derivation, and a sentence made of LaTeX.

        The stem and its continuation stay one sentence, which is correct: "The
        estimator is: [equation] where a is the sum" is one sentence in mathematical
        writing, and the equation is simply not words."""
        text = "The estimator is:\n\n$$\\hat{P} = \\frac{a}{b},$$\n\nwhere a is the sum.\n"
        self.assertEqual(prose.sentences(text), ["The estimator is: where a is the sum."])
        self.assertNotIn("frac", prose.strip_structure(text))

    def test_an_image_line_is_not_prose(self):
        """A results path is not a dozen words of writing."""
        text = "Before it.\n\n![](../results/a/very/long/path/to/figure_name.png)\n\nAfter."
        self.assertEqual(prose.sentences(text), ["Before it.", "After."])

    def test_a_blockquote_is_not_the_author_s_prose(self):
        """Quoted material — a verbatim model output, a reviewer's comment, an example
        narrative. The author cannot repair a sentence they did not write, and a
        supplement quoting a 170-word generated narrative would otherwise measure as
        though it contained a 170-word sentence."""
        text = "The example follows.\n\n> A very long quoted line goes here.\n\nIt ends."
        self.assertEqual(prose.sentences(text),
                         ["The example follows.", "It ends."])

    def test_fenced_code_is_not_prose(self):
        text = "Before it.\n\n```\nx = 1. y = 2. z = 3.\n```\n\nAfter it."
        self.assertEqual(len(prose.sentences(text)), 2)

    def test_a_hard_wrapped_sentence_is_one_sentence(self):
        text = "The embedded\nrepresentation did\nbetter than the other one."
        self.assertEqual(len(prose.sentences(text)), 1)

    def test_the_anchor_keeps_the_line_breaks(self):
        """A repair anchor is matched character for character against the draft, so a
        tidied sentence is an anchor that silently never applies."""
        text = "The embedded\nrepresentation did better."
        spans = prose.sentence_spans(text)
        self.assertEqual(spans[0][2], text)
        self.assertEqual(spans[0][3], "The embedded representation did better.")

    def test_list_items_are_separate_paragraphs(self):
        text = "Intro line.\n\n- first item\n- second item\n\nOutro line."
        self.assertEqual(len(prose.paragraphs(text)), 4)

    def test_collapse_pattern_crosses_a_line_break(self):
        pattern = prose.collapse_pattern("treatment-resistant depression")
        self.assertTrue(pattern.search("we studied treatment-resistant\ndepression here"))

    def test_collapse_pattern_will_not_match_inside_a_word(self):
        self.assertIsNone(prose.collapse_pattern("rule-based").search("non-rule-based"))

    def test_stripping_structure_preserves_every_offset(self):
        """Blanked, not deleted. An anchor drawn from stripped text has to be a
        substring of the original, or the repair it belongs to never applies."""
        text = "# Results\n\n| a | b |\n\nThe model did better.\n"
        stripped = prose.strip_structure(text)
        self.assertEqual(len(stripped), len(text))
        at = stripped.index("The model")
        self.assertEqual(text[at:at + 21], "The model did better.")

    def test_a_heading_does_not_join_the_paragraph_below_it(self):
        """A heading carries no terminator. Delete the line and it glues onto the
        first sentence beneath it — which on a real manuscript produced one 133-word
        sentence that was a title block plus everything after it."""
        text = "# Title page\n\nThe first real sentence. And a second one.\n"
        found = prose.sentences(text)
        self.assertEqual(found, ["The first real sentence.", "And a second one."])


class SentenceGateTests(unittest.TestCase):
    """The one-read rule, measured."""

    LONG = ("The embedded representation, which was produced by a pretrained encoder "
            "applied to the narrative sections of each record and then pooled across "
            "the whole of the encounter window rather than a fixed lookback, "
            "discriminated the outcome more sharply than the typed feature vector "
            "did, although the difference was smaller in the youngest subgroup and "
            "may possibly reflect sampling rather than any real signal.")

    def test_a_long_welded_sentence_fails(self):
        report = sentences.score(self.LONG)
        self.assertFalse(report.passed)
        self.assertTrue(any("35 words" in r for r in report.reasons))

    def test_the_hard_ceiling_fires_on_one_sentence(self):
        report = sentences.score(self.LONG)
        self.assertEqual(len(report.over_hard_max), 1)

    def test_stacked_hedges_are_counted(self):
        report = sentences.score(self.LONG)
        self.assertEqual(len(report.stacked_hedges), 1)

    def test_a_list_semicolon_is_punctuation_not_a_weld(self):
        """Semicolons end the items of an enumeration by convention. Counting them
        pushes a writer away from the list that fixes a long sentence."""
        text = ("The domains were three:\n\n- depression severity;\n"
                "- psychiatric comorbidity;\n- health-care utilisation.\n")
        self.assertEqual(sentences.score(text).semicolons_per_kword, 0.0)

    def test_semicolons_are_rationed_and_the_ration_only_advises(self):
        """The count is reported. It does not fail the section: a published
        manuscript this project measures itself against runs three times the ceiling
        in ordinary clause-joining prose, and no shared ceiling exists to retune to.
        The defect the ration was aiming at is caught by the mid band."""
        text = " ".join(["The model did better; the gap was small."] * 6)
        report = sentences.score(text)
        self.assertTrue(any("semicolon" in a for a in report.advisories))
        self.assertFalse(any("semicolon" in r for r in report.reasons))

    def test_a_caption_semicolon_is_a_label_not_a_weld(self):
        """"(held-out test set; primary Qwen3-Embedding-8B encoder)" and "(A) history
        length; (B) gap; (C) count" accounted for every semicolon the ration refused
        in one Results section. The convention is the journal's, and the only repair
        available to a writer is to damage the caption."""
        text = (support.CLEAN_PROSE + "\n\n"
                "***Figure 2.** Discrimination by representation and classifier "
                "(held-out test set, n = 8,516; primary Qwen3-Embedding-8B encoder). "
                "(A) pre-index history length; (B) MDD-to-index gap; (C) encounter "
                "count.*\n")
        self.assertEqual(sentences.score(text).semicolons_per_kword, 0.0)

    def test_a_semicolon_inside_a_parenthesis_separates_items(self):
        """A parenthetical is already a subordinate aside, so a semicolon in one
        cannot be welding two independent clauses."""
        text = ("The penalty left 385 of 4,096 dimensions with nonzero weight, and 179 "
                "carried 80% of the magnitude (236 carried 90%; Figure 7). Fewer than "
                "5% of the dimensions account for the fit. The checks agree.")
        self.assertEqual(sentences.score(text).semicolons_per_kword, 0.0)

    def test_a_caption_is_still_measured_for_everything_else(self):
        """Only the weld budget forgives a caption. A caption a reader cannot parse is
        a real defect."""
        long_caption = ("***Figure 9.** " + "word " * 60 + "end.*")
        self.assertTrue(sentences.score(long_caption).long_sentences)

    def test_a_numeric_range_is_not_a_dash_weld(self):
        """A dash between two numbers is a range, not a second claim. Counting
        confidence intervals as welds measured the density of the results rather
        than of the prose, and no amount of rewriting could bring a Results
        section under the ration."""
        text = ("Discrimination reached 0.657 (95% CI 0.643-0.672) against 0.649 "
                "(0.634-0.664). The band spanned 0.645-0.657 across encoders. "
                "Index dates spanned 2016-2024 and the deltas ran -0.024 to -0.028.")
        text = text.replace("-0.672", "\u20130.672").replace("-0.664", "\u20130.664")
        text = text.replace("0.645-0.657", "0.645\u20130.657")
        text = text.replace("2016-2024", "2016\u20132024")
        report = sentences.score(text)
        self.assertEqual(report.emdashes_per_kword, 0.0)
        self.assertEqual(report.welded, [])

    def test_a_clause_joining_dash_is_still_a_weld(self):
        """The ration exists for asides. Excluding ranges must not excuse those."""
        text = " ".join(["The gap held \u2014 nobody expected that \u2014 across sites."] * 5)
        report = sentences.score(text)
        self.assertGreater(report.emdashes_per_kword, 2)
        self.assertFalse(report.passed)
        self.assertTrue(any("em-dash" in r for r in report.reasons))

    def test_a_tight_compound_dash_is_not_a_weld(self):
        """"precision\u2013recall" and "nearest\u2013farthest" are single terms made of two
        coordinate words. Counting them asked the writer to rename the analysis."""
        text = " ".join(["A nearest\u2013farthest fusion improved the precision\u2013recall "
                         "curve for every anchor\u2013neighbor pair we drew."] * 5)
        report = sentences.score(text)
        self.assertEqual(report.emdashes_per_kword, 0.0)

    def test_a_spaced_en_dash_is_still_a_weld(self):
        """Spacing is what separates the aside from the compound, and the aside is
        the whole reason the ration exists."""
        text = " ".join(["The gap held \u2013 nobody expected that \u2013 across sites."] * 5)
        self.assertGreater(sentences.score(text).emdashes_per_kword, 2)

    def test_empty_openers_are_named(self):
        text = ("It is worth noting that the gap was small. The cohort held. "
                "Importantly, the split was redrawn once. Nothing else moved.")
        report = sentences.score(text)
        phrases = {p for _s, p in report.empty_openers}
        self.assertEqual(phrases, {"it is worth noting", "importantly"})

    def test_uniform_length_fails_even_when_every_sentence_is_fine(self):
        """The one gate that fires on prose which is individually correct. Every
        sentence the same length is the loudest tell that nobody read it aloud."""
        text = " ".join(["The cohort held its shape across every one of the splits."]
                        * 8)
        report = sentences.score(text)
        self.assertFalse(report.passed)
        self.assertTrue(any("nearly the same length" in r for r in report.reasons))

    def test_good_prose_passes(self):
        self.assertTrue(sentences.score(support.CLEAN_PROSE).passed,
                        sentences.score(support.CLEAN_PROSE).reasons)

    def test_worst_offenders_are_ranked_by_how_badly_they_break_the_rule(self):
        text = (self.LONG + " " + "A short one. "
                + "This sentence runs on for a while and lists covariates such as age "
                  "and sex and site and year and season and payer and region and "
                  "index month without doing anything else at all with them.")
        worst = sentences.worst_offenders(sentences.score(text), count=2)
        self.assertIn(self.LONG, worst[0])

    def test_an_empty_section_fails_rather_than_scoring_zero(self):
        self.assertFalse(sentences.score("").passed)


class LocalDensityTests(unittest.TestCase):
    """A section average hides the paragraph that earns it."""

    # Verbatim, from the Methods of a manuscript this harness produced and shipped.
    # Four sentences, mean 27.2, inside a section that passed at 20.8.
    DENSE = ("The 2 representations were derived from the same temporal slice and from "
             "the same selected fields, but they do not render an identical inventory "
             "of them: 11 of 30 source fields are asymmetric, and 10 of those 11 "
             "favour the narrative. Head-to-head performance comparisons therefore "
             "estimate the performance of the complete representation pipelines rather "
             "than the isolated effect of data format. The field-level crosswalk, row "
             "by row with each field's encoding on both sides, is Supplement S10; it "
             "is the evidence for the scope statement above and not only a limitation. "
             "The full encoding rules are described in Supplement M5 and two example "
             "narratives are reproduced in Supplement S5.")

    def test_a_dense_paragraph_is_reported(self):
        report = sentences.score(self.DENSE)
        self.assertTrue(report.dense_paragraphs)
        self.assertGreater(report.dense_paragraphs[0][1],
                           config.PARAGRAPH_MEAN_WORDS_MAX)

    def test_a_dense_paragraph_survives_a_passing_section(self):
        """The defect this check exists for. A real Methods section passed at a mean
        of 20.8 while carrying a paragraph at 27.2, because nineteen easy sentences
        paid for four hard ones."""
        section = "\n\n".join([support.CLEAN_PROSE] * 3 + [self.DENSE])
        report = sentences.score(section)
        self.assertLessEqual(report.mean, config.SENTENCE_MEAN_WORDS_MAX)
        self.assertTrue(report.dense_paragraphs)
        self.assertFalse(report.passed)
        self.assertTrue(any("does not read the average" in r for r in report.reasons))

    def test_clean_prose_has_no_dense_paragraph(self):
        self.assertEqual(sentences.score(support.CLEAN_PROSE).dense_paragraphs, [])

    def test_two_sentences_are_not_a_measurement(self):
        """One legitimate 40-word list of covariates plus a short sentence averages
        over the ceiling and means nothing."""
        text = ("Covariates comprised age, sex, race, ethnicity, preferred language, "
                "marital status, religion, smoking status, body mass index, systolic "
                "pressure, diastolic pressure, encounter count, prior trial counts and "
                "the nine social-determinant flags recorded in the window. All were "
                "measured before the index date.")
        self.assertEqual(sentences.score(text).dense_paragraphs, [])

    def test_the_dense_opener_is_quotable_for_the_editor(self):
        report = sentences.score(self.DENSE)
        opener = report.dense_paragraphs[0][0]
        self.assertIn(opener, self.DENSE)
        self.assertIn(opener, sentences.worst_offenders(report))


class AnticipatoryRebuttalTests(unittest.TestCase):
    """The paper arguing with a reviewer who has not spoken yet."""

    def test_the_defensive_clause_is_caught(self):
        text = ("The crosswalk is in the supplement. It is the evidence for the scope "
                "statement above and not only a limitation. The rules follow.")
        report = sentences.score(text)
        self.assertTrue(report.anticipatory)
        self.assertFalse(report.passed)

    def test_a_scope_caveat_is_not_a_rebuttal(self):
        """Bounding what a result means is what a Discussion is for. An early version
        of this list refused it, which teaches the writer to overclaim."""
        text = ("Cohort proportions describe this enriched sample. They should not be "
                "interpreted as health-system prevalence estimates. The denominator "
                "differs.")
        self.assertEqual(sentences.score(text).anticipatory, [])

    def test_a_real_contrast_is_not_a_rebuttal(self):
        text = ("The farthest-neighbor predictor is not merely poor but informatively "
                "poor. Its errors are structured. That structure is the finding.")
        self.assertEqual(sentences.score(text).anticipatory, [])


class TalliedComparisonTests(unittest.TestCase):
    """A count of comparisons whose dimension is never stated."""

    def test_a_tally_with_no_axis_is_refused(self):
        text = ("Eleven fields are asymmetric and ten of them favour the narrative. "
                "The rest match. That bounds the claim.")
        report = sentences.score(text)
        self.assertEqual([v for _, v in report.undefined_comparisons], ["favour"])
        self.assertTrue(any("on what axis" in r for r in report.reasons))

    def test_naming_the_axis_clears_it(self):
        text = ("Eleven fields are asymmetric and ten of them favour the narrative in "
                "granularity. The rest match. That bounds the claim.")
        self.assertEqual(sentences.score(text).undefined_comparisons, [])

    def test_a_plain_comparison_is_not_a_tally(self):
        """"The embedding did not beat the feature vector" is a claim whose axis the
        section around it has fixed. Refusing it was the first version of this check
        and it refused correct prose."""
        text = ("The embedding did not beat the feature vector. The gap was small. "
                "Retrieval works, and loses.")
        self.assertEqual(sentences.score(text).undefined_comparisons, [])

    def test_a_threshold_comparison_names_its_own_axis(self):
        text = ("All ten contrasts include zero. None of them exceeds 0.05. The "
                "conclusion holds across strata.")
        self.assertEqual(sentences.score(text).undefined_comparisons, [])


class VagueThresholdTests(unittest.TestCase):
    """A threshold invoked by name and never given a value."""

    def test_a_threshold_with_no_value_is_refused(self):
        text = ("The embedded representation runs below the conventional "
                "events-per-variable threshold on three of the four encoders. "
                "The feature vector clears it. That bounds what the embedded arm "
                "can be asked to do.")
        report = sentences.score(text)
        self.assertTrue(report.vague_thresholds)
        self.assertTrue(any("Below what" in r for r in report.reasons))

    def test_numbers_elsewhere_in_the_sentence_do_not_excuse_it(self):
        """The version that accepted any digit anywhere passed the sentence it was
        written for. Those numbers are the measurements being compared, which is what
        makes the missing bar invisible."""
        text = ("The embedded representation runs below the conventional "
                "events-per-variable threshold on three of the four encoders (EPV "
                "1.5 to 2.3), whereas the feature-vector model exceeds it at 65. "
                "That is a property of dimensionality. It bounds the arm.")
        self.assertTrue(sentences.score(text).vague_thresholds)

    def test_stating_the_value_clears_it(self):
        text = ("Only the smallest encoder exceeds the conventional threshold of 10 "
                "events per variable. The rest fall below. That is by construction.")
        self.assertEqual(sentences.score(text).vague_thresholds, [])

    def test_a_threshold_named_before_its_value_also_clears(self):
        text = ("The 10-events-per-variable conventional threshold is met by one "
                "encoder only. The rest fall below. That is by construction.")
        self.assertEqual(sentences.score(text).vague_thresholds, [])


class ForecastTests(unittest.TestCase):
    """A prediction the paper cannot support, standing where a finding should be."""

    def test_a_bare_forecast_is_refused(self):
        text = ("The encoder accepts a bounded input. That constraint is a property "
                "of the tooling and is likely to move. The question stands.")
        report = sentences.score(text)
        self.assertEqual([p for _, p in report.forecasts], ["is likely to move"])
        self.assertTrue(any("only wait" in r for r in report.reasons))

    def test_a_recommendation_is_not_a_forecast(self):
        """A reader can act on "future work should test X" and can only wait for
        "X will improve". The first is what a Discussion is for."""
        text = ("The encoder accepts a bounded input. Future work should test whether "
                "a longer context changes the result. The question stands.")
        self.assertEqual(sentences.score(text).forecasts, [])

    def test_a_cited_forecast_is_somebody_else_s_on_the_record(self):
        """And the citation may sit in the sentence before, which is how a citation
        attaches in ordinary prose."""
        text = ("Context length has grown steadily across model generations [12]. It "
                "will likely improve further. The constraint is not conceptual.")
        self.assertEqual(sentences.score(text).forecasts, [])

    def test_the_capability_idiom_is_caught_too(self):
        text = ("The gap is wide today. As models improve the gap will narrow. "
                "Nothing here settles it.")
        self.assertTrue(sentences.score(text).forecasts)

    def test_a_conditional_about_this_study_is_not_a_forecast(self):
        text = ("Discrimination could improve with richer care-process variables. "
                "That is a data question. It is not tested here.")
        self.assertEqual(sentences.score(text).forecasts, [])


class DoubledWordTests(unittest.TestCase):
    """A hard wrap hides this from every reader and from no machine."""

    def test_a_repeated_word_is_caught(self):
        text = ("All ten contrasts include zero and none exceeds 0.012 ROC ROC AUC. "
                "The gap held. Nothing changed.")
        report = sentences.score(text)
        self.assertEqual([w for _, w in report.doubled], ["ROC"])
        self.assertFalse(report.passed)

    def test_a_word_english_really_doubles_is_left_alone(self):
        text = ("The cohort had had one prior trial. That was the floor. It held "
                "across arms.")
        self.assertEqual(sentences.score(text).doubled, [])

    def test_it_survives_a_line_break(self):
        """Which is the only reason it shipped three times in one manuscript."""
        text = "The gap was 0.005 ROC\nROC AUC. It held. Nothing changed."
        self.assertTrue(sentences.score(text).doubled)


class SplitHedgeTests(unittest.TestCase):
    """The stacked hedge again, moved behind a full stop where the per-sentence
    check cannot see it."""

    def test_retracting_a_claim_never_made_is_refused(self):
        text = ("This pattern is consistent with a decision boundary captured by a "
                "regularized linear model. It does not establish that the latent "
                "structure is intrinsically linear. The point stands.")
        report = sentences.score(text)
        self.assertEqual([c for _, c in report.split_hedges], ["consistent with"])
        self.assertTrue(any("never made" in r for r in report.reasons))

    def test_a_scope_statement_after_a_firm_claim_is_honest(self):
        """"It does not establish X" is the right sentence when the paper actually
        claimed something. It is only noise after a hedge."""
        text = ("The embedding reorganizes the available signal. It does not "
                "establish that narrative adds information. That bound is stated in "
                "Limitations.")
        self.assertEqual(sentences.score(text).split_hedges, [])


class WordyRatioTests(unittest.TestCase):
    """A figure written as a word is how a quantity gets past the numbers gate."""

    def test_a_ratio_with_no_number_is_refused(self):
        text = ("The interval is roughly a third the width of the marginal ones. That "
                "matters. It reflects precision rather than power.")
        report = sentences.score(text)
        self.assertEqual([p for _, p in report.wordy_ratios], ["a third the"])
        self.assertTrue(any("still a quantity" in r for r in report.reasons))

    def test_an_unquantified_magnitude_comparison_is_the_same_defect(self):
        """Sat one paragraph below +0.028 against -0.013 to -0.022, which is not
        comparable by any reading."""
        text = ("The two effects are of comparable magnitude and opposite sign. That "
                "is why it lands on a null. Nothing else explains it.")
        self.assertTrue(sentences.score(text).wordy_ratios)

    def test_writing_the_figures_clears_it(self):
        """The gate is not against the phrase. It is against the phrase standing
        alone, with nothing the numbers gate can check."""
        text = ("The paired interval is 0.022 wide against marginal intervals of "
                "0.029 and 0.030, roughly three quarters the width. That is "
                "precision. It is not power.")
        self.assertEqual(sentences.score(text).wordy_ratios, [])

    def test_a_sequence_is_not_a_magnitude(self):
        """"Ordered in the same order as Table 4" was this check's one false
        positive on a real supplement."""
        text = ("Each row is a run. The six permutation specifications are listed in "
                "the same order as Table 4. The baseline is on top.")
        self.assertEqual(sentences.score(text).wordy_ratios, [])


class EquivalenceOverclaimTests(unittest.TestCase):
    """A word that asserts more than the statistics can support.

    Written from a manuscript whose Methods said "no equivalence or noninferiority
    margin was prespecified", whose Limitations was headed "Absence of an advantage is
    not equivalence", and which called the result "parity" sixteen times in between."""

    DISCLAIMER = "No equivalence or noninferiority margin was prespecified. "

    def test_the_word_is_refused_when_the_paper_disclaims_the_test(self):
        found = sentences.equivalence_overclaim(
            self.DISCLAIMER + "The result supports parity rather than superiority. "
            "The two representations are equivalent on this outcome.")
        self.assertEqual([w for _, w in found], ["parity", "equivalent"])

    def test_the_word_is_allowed_when_the_margin_was_set(self):
        """A paper that prespecified a margin is entitled to every word in the list."""
        found = sentences.equivalence_overclaim(
            "An equivalence margin of 0.02 ROC AUC was prespecified. The result "
            "supports parity rather than superiority. Both intervals fall inside it.")
        self.assertEqual(found, [])

    def test_refusing_the_word_is_not_claiming_it(self):
        """"Absence of an advantage is not equivalence" is the correct sentence.
        A gate that refuses it demands the paper stop saying the true thing."""
        found = sentences.equivalence_overclaim(
            self.DISCLAIMER + "Absence of an advantage is not equivalence. It is not "
            "that the two representations are equivalent.")
        self.assertEqual(found, [])

    def test_an_honest_null_is_not_an_equivalence_claim(self):
        found = sentences.equivalence_overclaim(
            self.DISCLAIMER + "The embedding did not outperform the feature vector. "
            "The interval includes zero and the two tie on this cohort.")
        self.assertEqual(found, [])

    def test_the_adverb_does_not_slip_past(self):
        """"The models perform equivalently across sexes" is the claim, and a
        word-boundary match on "equivalent" does not see it."""
        found = sentences.equivalence_overclaim(
            self.DISCLAIMER + "The models perform equivalently across sexes. All ten "
            "contrasts include zero.")
        self.assertEqual([w for _, w in found], ["equivalently"])

    def test_a_restatement_connective_is_not_a_claim(self):
        """"Equivalently, ..." means "put another way". It was the false positive the
        adverb widening bought."""
        found = sentences.equivalence_overclaim(
            self.DISCLAIMER + "Equivalently, the outcome required at least 2 "
            "post-index antidepressant changes. The window was fixed.")
        self.assertEqual(found, [])

    def test_it_is_a_whole_document_check(self):
        """The licence lives in the Methods and the claim lives in the Discussion.
        Neither section can see the defect from inside itself."""
        discussion_only = ("The result supports parity rather than superiority. "
                           "Both read the same content. That is the finding.")
        self.assertEqual(sentences.equivalence_overclaim(discussion_only), [])
        self.assertTrue(sentences.equivalence_overclaim(
            self.DISCLAIMER + discussion_only))


class UnreportedAnalysisTests(unittest.TestCase):
    """Report it or do not mention it. There is no third option."""

    def test_an_analysis_described_and_then_withheld_is_refused(self):
        text = ("Two further weightings derived from a clinical-similarity score were "
                "also evaluated. They added no discrimination and are reported "
                "separately, available from the corresponding author. The rest "
                "follows.")
        report = sentences.score(text)
        self.assertTrue(report.unreported)
        self.assertTrue(any("mailing address" in r for r in report.reasons))

    def test_data_not_shown_is_the_same_defect(self):
        text = ("Sensitivity analyses using an alternative outcome window gave the "
                "same ordering (data not shown). The gap held. Nothing changed.")
        self.assertTrue(sentences.score(text).unreported)

    def test_a_code_availability_statement_is_required_not_refused(self):
        """Journals ask for this sentence. A gate that refuses it is a gate that
        makes the paper worse."""
        text = ("The cohort was assembled from one health system. Analysis code is "
                "available from the corresponding author. Nothing else was used.")
        self.assertEqual(sentences.score(text).unreported, [])

    def test_a_data_availability_statement_is_not_refused_either(self):
        text = ("The extract held 42,579 patients. Data are available on request, "
                "subject to institutional review. The split was fixed in advance.")
        self.assertEqual(sentences.score(text).unreported, [])

    def test_the_sentence_is_quoted_for_the_editor(self):
        text = ("A re-run with the two largest asymmetries closed leaves the contrast "
                "a null. That analysis is available from the corresponding author. It "
                "bounds the claim.")
        report = sentences.score(text)
        self.assertIn(report.unreported[0][0], sentences.worst_offenders(report))


class SignpostEndingTests(unittest.TestCase):
    """A cross-reference is support, exactly as a citation is."""

    def test_a_paragraph_ending_on_a_signpost_has_no_conclusion(self):
        text = ("The two representations differ in their field inventory. Eleven of "
                "thirty are asymmetric. The full encoding rules are described in "
                "Supplement M5 and two example narratives are reproduced in "
                "Supplement S5.")
        self.assertIn("no concluding sentence",
                      {d.kind for d in paragraphs.check(text).defects})

    def test_a_cross_reference_as_the_predicate_is_a_signpost(self):
        text = ("The crosswalk settles the question. Every row traces to a chosen "
                "field. The field-level crosswalk, row by row, is Supplement S10.")
        self.assertIn("no concluding sentence",
                      {d.kind for d in paragraphs.check(text).defects})

    def test_an_attached_pointer_is_not_a_signpost(self):
        """"as shown in Figure 3" hangs off a sentence that states its finding. That
        one word is the difference between a signpost and an attachment."""
        text = ("Discrimination was flat across the four encoders. The spread was "
                "0.012. The band held in every stratum, as shown in Figure 3.")
        self.assertNotIn("no concluding sentence",
                         {d.kind for d in paragraphs.check(text).defects})

    def test_a_parenthetical_table_reference_is_not_a_signpost(self):
        text = ("The cohort lost 3,105 patients at the diagnosis filter. Most of the "
                "rest were missing an index date. Attrition therefore concentrates in "
                "one step (Table 2).")
        self.assertNotIn("no concluding sentence",
                         {d.kind for d in paragraphs.check(text).defects})


class TerminologyDriftTests(unittest.TestCase):
    """The synonym nobody thought to ban."""

    LOCK = [{"term": "feature representation", "aliases": ["rule-based approach"]}]

    TEXT = ("# Methods\n\nThe feature representation assigned explicit columns. The "
            "feature matrix was assembled first. Every row of the feature matrix "
            "carried one patient. The feature-vector model exceeded the threshold, "
            "and the feature-vector arm was fitted with regularisation.\n")

    def test_an_undeclared_second_name_is_drift(self):
        report = terminology.check_manuscript(self.TEXT, self.LOCK)
        found = {d.found for d in report.defects if d.kind == "drift"}
        self.assertIn("feature matrix", found)
        self.assertIn("feature vector", found)
        self.assertFalse(report.passed)

    def test_a_single_use_is_ordinary_english(self):
        text = "# Methods\n\nThe feature representation used columns. The feature " \
               "matrix was assembled once.\n"
        report = terminology.check_manuscript(text, self.LOCK)
        self.assertEqual([d for d in report.defects if d.kind == "drift"], [])

    def test_drift_does_not_run_at_section_scope(self):
        """A phrase used once in each of four sections is a name, and no section can
        see that from inside itself. The same split the abbreviation rules make."""
        report = terminology.check(self.TEXT, self.LOCK)
        self.assertEqual([d for d in report.defects if d.kind == "drift"], [])

    def test_a_declared_alias_belongs_to_the_alias_rule(self):
        lock = [{"term": "feature representation",
                 "aliases": ["feature matrix"]}]
        report = terminology.check_manuscript(self.TEXT, lock)
        kinds = {d.kind for d in report.defects if d.found == "feature matrix"}
        self.assertEqual(kinds, {"alias"})

    def test_a_non_naming_head_is_not_drift(self):
        """"Feature selection" shares the modifier and names no thing."""
        text = ("# Methods\n\nThe feature representation used columns. Feature "
                "selection ran first. Feature selection used the training fold "
                "alone.\n")
        report = terminology.check_manuscript(text, self.LOCK)
        self.assertEqual([d for d in report.defects if d.kind == "drift"], [])


class WeldRationTests(unittest.TestCase):
    """The semicolon and dash rations, and the notation they must not punish."""

    def test_a_semicolon_inside_a_parenthesis_is_a_label(self):
        text = ("Discrimination held across encoders (held-out test set; primary "
                "Qwen3-Embedding-8B encoder). Nothing moved by more than 0.012 in "
                "either direction across the four. The band is narrow.")
        self.assertEqual(sentences.score(text).semicolons_per_kword, 0.0)

    def test_a_hard_wrapped_parenthesis_is_still_a_parenthesis(self):
        """Drafted prose arrives hard-wrapped, so a parenthetical two thirds of the
        way along a line is split across two of them. Excluding the newline switched
        the exemption off for exactly those, and one wrapped pointer pair scored a
        supplement section at 2.5 per thousand words with no repair available but to
        damage the cross-reference."""
        text = ("The crosswalk bounds the null, and the main text states the bound in\n"
                "its own voice (Methods, *Predictors and patient representations*;\n"
                "Discussion, *Principal findings*). Every row traces to a field that\n"
                "predictor selection chose. Neither arm was handed a raw record.")
        self.assertEqual(sentences.score(text).semicolons_per_kword, 0.0)

    def test_a_semicolon_welding_two_clauses_is_still_counted(self):
        text = ("The split is the frozen one every evaluation uses; nothing was refit "
                "to produce this table. The distributions are unchanged. Both halves "
                "inherit the same sampling frame.")
        self.assertGreater(sentences.score(text).semicolons_per_kword, 0.0)


class MeanLengthFloorTests(unittest.TestCase):
    """The floor catches prose that has gone clipped. A caption's length is set by
    convention, so counting captions makes a section of tables unfixable."""

    def test_captions_do_not_drag_the_floor_down(self):
        text = (
            "The representation comprises fifty-nine source fields, three of which "
            "were dropped at load time for missingness. Quantitative and boolean "
            "fields map one-to-one onto model columns. The eight categorical fields "
            "are one-hot encoded, and five of them carry an additional level for "
            "patients with no recorded value.\n\n"
            "***Table A1.** Quantitative predictors (15).*\n\n"
            "***Table A2.** Boolean predictors (36).*\n\n"
            "***Table A3.** Categorical predictors (8).*\n\n"
            "***Table A4.** One-hot levels (41).*\n")
        report = sentences.score(text)
        self.assertTrue(report.passed, report.reasons)

    def test_genuinely_clipped_prose_still_fails_the_floor(self):
        text = ("The model was fit. It scored well. The split was stratified. "
                "Nothing was refit. The result held. Calibration was fine.")
        report = sentences.score(text)
        self.assertFalse(report.passed)
        self.assertTrue(any("the floor is" in r for r in report.reasons))


class ParagraphGateTests(unittest.TestCase):

    def test_a_paragraph_opening_on_a_citation_has_no_topic_sentence(self):
        text = ("[12] reported a similar gap in a comparable cohort. Our estimate was "
                "close to theirs. The difference was not material.")
        report = paragraphs.check(text)
        self.assertIn("no topic sentence", {d.kind for d in report.defects})

    def test_a_paragraph_opening_on_a_number_has_no_topic_sentence(self):
        text = ("42579 patients entered the extract before filtering. Most of the loss "
                "came from the diagnosis window. The rest was missing data.")
        self.assertIn("no topic sentence",
                      {d.kind for d in paragraphs.check(text).defects})

    def test_a_hinge_opener_is_a_continuation(self):
        text = ("However, the gap narrowed in the youngest group. The interval was "
                "wide. Nothing about it changes the headline.")
        self.assertIn("hinge opener", {d.kind for d in paragraphs.check(text).defects})

    def test_a_buried_claim_is_flagged(self):
        text = ("Because the cohort was assembled retrospectively from a single health "
                "system, the estimate may not transfer. The case mix differs. That "
                "limits what it settles.")
        self.assertIn("buried claim", {d.kind for d in paragraphs.check(text).defects})

    def test_a_short_subordinate_opener_is_not_a_buried_claim(self):
        text = ("If so, the estimate is biased downward. The direction is known. The "
                "size is not.")
        self.assertNotIn("buried claim",
                         {d.kind for d in paragraphs.check(text).defects})

    def test_a_one_sentence_paragraph_is_too_short(self):
        """A single sentence cannot be a claim plus anything, and this is exactly how
        one appears after a compression pass: a fact left floating."""
        self.assertIn("too short",
                      {d.kind for d in paragraphs.check("The model did better.").defects})

    def test_two_sentences_is_a_claim_and_what_follows(self):
        """The floor was three until a real manuscript was read against it. Three
        refused eight paragraphs and was wrong about seven: an attrition statement, a
        lead-in before bolded subsections, a claim and its consequence, and the compact
        findings a Conclusions section is made of."""
        text = ("The domains the embedding relies on are the same domains that carry "
                "the largest feature-vector weights. That convergence is the mechanism "
                "behind the null in Table 2.")
        self.assertNotIn("too short",
                         {d.kind for d in paragraphs.check(text).defects})

    def test_the_gate_blocks_on_a_share_not_on_one_defect(self):
        """A single mis-shaped paragraph in a long section is not a failing section.
        A gate that fires on every section is a gate nobody reads."""
        good = support.CLEAN_PROSE
        text = good + "\n\nHowever, one paragraph opens badly.\n\n" + good
        report = paragraphs.check(text)
        self.assertTrue(report.defects)
        self.assertTrue(report.passed, report.reasons)

    def test_a_list_stem_is_not_a_paragraph(self):
        """A block ending in a colon points at what comes next; its support is the
        list beneath it. Judging it as an unsupported paragraph would make the gate
        call the repair for a long sentence a defect."""
        text = "The domains were three:\n\n- one;\n- two;\n- three.\n"
        report = paragraphs.check(text)
        self.assertEqual(report.checked, 0)
        self.assertTrue(report.passed)

    def test_a_caption_is_not_a_paragraph(self):
        """A caption has no topic sentence and no concluding sentence by design, and is
        routinely one or two sentences. Judging it against paragraph shape produces a
        defect on every figure in a supplement."""
        text = "***Table S3.** Counts by group. Lower is better.*\n"
        self.assertEqual(paragraphs.check(text).checked, 0)
        self.assertEqual(paragraphs.check("**(A) Nearest retrieval**\n").checked, 0)

    def test_a_caption_s_sentences_are_still_measured(self):
        """Only shape is exempt. A caption a reader cannot parse is a real defect."""
        long_caption = "***Table 1.** " + " ".join(["word"] * 60) + ".*"
        self.assertFalse(sentences.score(long_caption).passed)

    def test_exempt_sections_are_not_checked(self):
        report = paragraphs.check("One sentence only.", section_name="Abstract")
        self.assertTrue(report.passed)
        self.assertEqual(report.checked, 0)

    def test_list_items_are_exempt(self):
        text = "- first bullet\n- second bullet\n- third bullet"
        report = paragraphs.check(text)
        self.assertEqual(report.checked, 0)

    def test_good_prose_passes(self):
        self.assertTrue(paragraphs.check(support.CLEAN_PROSE).passed)


class ParagraphShapeExemptionTests(unittest.TestCase):
    """The blocks that are not paragraphs, and the section where a closing pointer is
    the conclusion rather than a substitute for one."""

    def test_a_standalone_bold_label_is_not_a_paragraph(self):
        """"**TRD-positive example.**" above a fenced narrative names what follows. It
        has no claim and no support and is one sentence long by construction. A
        supplement reproducing two example narratives reported three too-short
        paragraphs out of six, on two labels and a horizontal rule."""
        text = ("The renderer walks a fixed template over the selected fields. Every "
                "patient reaches the encoder through the same constant form.\n\n"
                "**TRD-positive example.**\n\n"
                "---\n\n"
                "**TRD-negative example.**\n")
        report = paragraphs.check(text)
        self.assertEqual([d.kind for d in report.defects], [])
        self.assertTrue(report.passed)

    def test_a_run_in_heading_with_prose_after_it_is_still_a_paragraph(self):
        """The label rule is narrow on purpose: the WHOLE block has to be emphasis."""
        text = "**Strata.** [12] chose six families.\n"
        report = paragraphs.check(text)
        self.assertEqual(report.checked, 1)
        self.assertTrue(report.defects)

    def test_a_methods_paragraph_may_close_on_a_pointer(self):
        """A methods paragraph's job is to specify a procedure, and when the fuller
        specification lives in a supplement the pointer IS the rest of that
        paragraph's content. Pointed at a real Methods section the rule refused eight
        of twenty-one paragraphs and all eight were correct as written."""
        text = ("The index date was the earliest antidepressant prescription recorded "
                "on or after the first documented depression diagnosis. Each patient "
                "contributed one index date. Full index-selection rules are given in "
                "Supplement M2.")
        self.assertNotIn("no concluding sentence",
                         {d.kind for d in paragraphs.check(
                             text, section_name="Methods").defects})
        self.assertNotIn("no concluding sentence",
                         {d.kind for d in paragraphs.check(
                             text, section_name="Supplement M2. Index selection"
                         ).defects})

    def test_a_results_paragraph_may_not(self):
        text = ("Discrimination was modest in every configuration. The best model "
                "reached a ROC AUC of 0.657. The full stratified results are in "
                "Supplement S7.")
        self.assertIn("no concluding sentence",
                      {d.kind for d in paragraphs.check(
                          text, section_name="Results").defects})


class NumberGateTests(unittest.TestCase):

    EVIDENCE = {"items": [
        {"id": "e.1", "statement": "AUC", "values": [0.7429]},
        {"id": "e.2", "statement": "n", "values": [8516]},
    ]}

    def test_a_number_in_the_ledger_passes(self):
        self.assertTrue(numbers.check("The AUC was 0.7429 here.", self.EVIDENCE).passed)

    def test_a_rounded_restatement_is_the_same_number(self):
        self.assertTrue(numbers.check("The AUC was 0.74 here.", self.EVIDENCE).passed)

    def test_a_plausible_wrong_number_is_caught(self):
        """The failure this gate exists for. 0.75 is not 0.7429 and no amount of
        fluency makes it one."""
        report = numbers.check("The AUC was 0.75 here.", self.EVIDENCE)
        self.assertFalse(report.passed)
        self.assertEqual([u.raw for u in report.unsupported], ["0.75"])

    def test_a_percentage_matches_its_proportion(self):
        self.assertTrue(numbers.check("Accuracy reached 74.29%.", self.EVIDENCE).passed)

    def test_a_thousands_separator_is_the_same_number(self):
        self.assertTrue(numbers.check("We analysed 8,516 records.",
                                      self.EVIDENCE).passed)

    def test_years_are_not_findings(self):
        self.assertTrue(numbers.check("The extract covers 2019 to 2024.",
                                      self.EVIDENCE).passed)

    def test_structural_references_are_not_findings(self):
        self.assertTrue(numbers.check("See Table 3 and Figure 7 for the curves.",
                                      self.EVIDENCE).passed)

    def test_citation_markers_are_not_findings(self):
        self.assertTrue(numbers.check("A prior study found the same [27].",
                                      self.EVIDENCE).passed)

    def test_an_empty_ledger_disables_the_gate(self):
        """A first draft written before the evidence stage has run must not be
        rejected for every figure in it."""
        self.assertTrue(numbers.check("The AUC was 0.99.", {"items": []}).passed)

    def test_also_allow_exempts_a_quotable_non_finding(self):
        evidence = dict(self.EVIDENCE, also_allow=[32])
        self.assertTrue(numbers.check("We used 32 quantile bins.", evidence).passed)

    def test_rounding_is_judged_at_the_precision_the_prose_used(self):
        """A flat relative tolerance gets small effect sizes wrong in the direction
        that matters: 0.74 against 0.7429 passes while 0.008 against 0.007939 fails,
        because the same rounding is a larger fraction of a smaller number. Every
        legitimately rounded effect size in a manuscript is small."""
        evidence = {"items": [{"id": "e.1", "statement": "delta",
                               "values": [0.007939069768552076]}]}
        self.assertTrue(numbers.check("The gap was +0.008.", evidence).passed)
        self.assertFalse(numbers.check("The gap was +0.009.", evidence).passed)

    def test_a_sentence_final_number_is_checked(self):
        """It was not, for a while, and nothing said so. The trailing lookahead
        rejected a match followed by a full stop, so every figure that ended a
        sentence went unchecked — and the gate reported the section clean."""
        report = numbers.check("Discrimination reached 0.9999.", self.EVIDENCE)
        self.assertFalse(report.passed)
        self.assertEqual([u.raw for u in report.unsupported], ["0.9999"])

    def test_the_closing_bound_of_an_interval_is_checked(self):
        """Same lookahead, same silence: a number followed by ")" was skipped, so the
        upper bound of every confidence interval in the manuscript went unread."""
        report = numbers.check("AUC 0.7429 (95% CI 0.7100-0.9999).", self.EVIDENCE)
        self.assertIn("0.9999", [u.raw for u in report.unsupported])

    def test_a_version_string_is_still_not_a_finding(self):
        self.assertTrue(numbers.check("We used version 1.2.3 of it.",
                                      self.EVIDENCE).passed)

    def test_clinical_codes_are_not_findings(self):
        """A Methods section lists dozens of ICD codes and not one is a measurement.
        The keyword sits several words back from most of them, so adjacency is the
        wrong test."""
        text = ("Depression comprised ICD-9 codes 296.2, 296.3, 300.4, and 311 or "
                "ICD-10 codes F32 and F33.")
        report = numbers.check(text, self.EVIDENCE)
        self.assertTrue(report.passed, [u.raw for u in report.unsupported])

    def test_a_finding_after_a_code_list_is_still_checked(self):
        """The exemption stops at the sentence boundary, or a results sentence
        following a Methods sentence would inherit it."""
        text = ("Depression comprised ICD-9 codes 296.2 and 311. Discrimination "
                "reached 0.9999.")
        self.assertFalse(numbers.check(text, self.EVIDENCE).passed)

    def test_an_orcid_is_not_a_finding(self):
        text = "Mikey Ferguson 0009-0005-1365-5609 wrote this sentence down."
        self.assertTrue(numbers.check(text, self.EVIDENCE).passed,
                        [u.raw for u in numbers.check(text, self.EVIDENCE).unsupported])

    def test_numbers_in_a_heading_or_a_comment_are_not_findings(self):
        text = ("# Table 4 results for 9999 patients\n\n"
                "<!-- TRIPOD+AI item 7777 -->\n\n"
                "The AUC was 0.7429 on the split.\n")
        self.assertTrue(numbers.check(text, self.EVIDENCE).passed,
                        [u.raw for u in numbers.check(text, self.EVIDENCE).unsupported])

    def test_the_anchor_is_the_sentence_verbatim(self):
        text = "The cohort held.\nThe AUC was\n0.75 on the split.\n"
        report = numbers.check(text, self.EVIDENCE)
        anchor = report.unsupported[0].sentence
        self.assertEqual(text.count(anchor), 1)
        self.assertIn("\n", anchor)


class BibliographicNumberTests(unittest.TestCase):
    """A Vancouver entry is a dense block of numbers and not one is a result."""

    EVIDENCE = {"items": [{"id": "e.1", "statement": "ROC AUC", "values": [0.657]}]}

    def test_a_reference_list_is_not_scanned(self):
        text = ("# Results\n\nThe best model reached 0.657.\n\n"
                "# References\n\n"
                "1. Al-Harbi KS. Treatment-resistant depression. Patient Prefer "
                "Adherence. 2012;6:369-388. doi:10.2147/PPA.S29716.\n")
        report = numbers.check(text, self.EVIDENCE)
        self.assertTrue(report.passed, [u.raw for u in report.unsupported])

    def test_the_abstract_is_still_scanned(self):
        """The abstract is exempt from paragraph shape and is the LAST place a number
        should go unchecked. Rounding 0.712 to 0.71 there while the results say 0.712
        is the defect this gate exists for."""
        text = "# Abstract\n\nThe model reached a ROC AUC of 0.883.\n"
        report = numbers.check(text, self.EVIDENCE)
        self.assertFalse(report.passed)
        self.assertIn("0.883", [u.raw for u in report.unsupported])


class TerminologyGateTests(unittest.TestCase):

    LOCK = [
        {"term": "feature representation",
         "aliases": ["rule-based approach", "rule-based"]},
        {"term": "TRD", "first_use": "treatment-resistant depression"},
    ]

    def test_a_forbidden_alias_is_a_violation(self):
        report = terminology.check("The rule-based approach did worse.", self.LOCK)
        self.assertFalse(report.passed)
        self.assertEqual(report.defects[0].kind, "alias")

    def test_nested_aliases_are_reported_once(self):
        """A lock forbidding both 'rule-based' and 'rule-based approach' must not ask
        for two repairs on one span — the second could never apply."""
        report = terminology.check("The rule-based approach did worse.", self.LOCK)
        self.assertEqual(len(report.defects), 1)

    def test_an_alias_inside_a_quotation_is_allowed(self):
        report = terminology.check('The reviewer wrote "the rule-based approach is '
                                   'unclear" in their note.', self.LOCK)
        self.assertTrue(report.passed)

    def test_an_undefined_abbreviation_is_caught(self):
        report = terminology.check_manuscript("Patients with TRD were included.",
                                              self.LOCK)
        self.assertIn("undefined-abbreviation", {d.kind for d in report.defects})

    def test_an_expansion_across_a_line_break_still_counts(self):
        """Drafted prose arrives hard-wrapped. A gate that misses the expansion
        reports a defect the editor cannot repair, because nothing is wrong."""
        report = terminology.check_manuscript(
            "Patients with treatment-resistant\ndepression (TRD) were included.",
            self.LOCK)
        self.assertTrue(report.passed, [d.detail for d in report.defects])

    def test_expanding_twice_is_a_defect(self):
        report = terminology.check_manuscript(
            "Treatment-resistant depression (TRD) is common. We studied "
            "treatment-resistant depression again.", self.LOCK)
        self.assertIn("redefined", {d.kind for d in report.defects})

    def test_first_use_is_not_checked_at_section_scope(self):
        """Which section holds an abbreviation's first appearance cannot be known from
        inside one section. Demanding the expansion in every section is exactly the
        expanded-twice defect the same gate punishes, so the two rules contradict each
        other and a writer told to satisfy both oscillates."""
        section = "Patients with TRD were included in the analysis here."
        self.assertTrue(terminology.check(section, self.LOCK).passed)
        self.assertFalse(terminology.check_manuscript(section, self.LOCK).passed)

    def test_an_alias_still_blocks_at_section_scope(self):
        """A forbidden synonym is a defect wherever it appears."""
        self.assertFalse(
            terminology.check("The rule-based approach did worse.", self.LOCK).passed)

    def test_an_abbreviation_inside_its_own_term_is_not_an_alias(self):
        """The common case, not an edge case: an abbreviation is usually a substring of
        the term it abbreviates. A lock preferring "ROC AUC" over a bare "AUC" would
        otherwise flag every correct use, and the repair would replace "AUC" inside
        "ROC AUC" with "ROC AUC"."""
        lock = [{"term": "ROC AUC", "aliases": ["AUC", "AUROC"]}]
        self.assertTrue(terminology.check("Discrimination reached ROC AUC 0.65.",
                                          lock).passed)
        self.assertFalse(terminology.check("Discrimination reached AUC 0.65.",
                                           lock).passed)

    def test_an_abstract_may_expand_an_abbreviation_the_body_expands_again(self):
        """An abstract is read detached from its paper, so journals expect it to
        expand its own abbreviations and the body to expand them again. A first-use
        check spanning both reports every correctly written manuscript as having
        defined everything twice."""
        manuscript = (
            "# Abstract\n\nTreatment-resistant depression (TRD) is common.\n\n"
            "# Introduction\n\nTreatment-resistant depression (TRD) is common. "
            "TRD is the outcome here.\n")
        self.assertTrue(terminology.check_manuscript(manuscript, self.LOCK).passed,
                        [d.detail for d in
                         terminology.check_manuscript(manuscript, self.LOCK).defects])

    def test_expanding_twice_inside_the_body_is_still_a_defect(self):
        manuscript = ("# Introduction\n\nTreatment-resistant depression (TRD) is "
                      "common.\n\n# Discussion\n\nTreatment-resistant depression "
                      "recurs often.\n")
        self.assertFalse(terminology.check_manuscript(manuscript, self.LOCK).passed)

    def test_an_alias_in_the_abstract_is_still_a_defect(self):
        """Aliases are checked everywhere. A forbidden synonym in an abstract is a
        defect in the part of the paper most people read."""
        manuscript = "# Abstract\n\nThe rule-based approach did worse.\n"
        self.assertFalse(terminology.check_manuscript(manuscript, self.LOCK).passed)

    def test_an_alias_in_a_reference_title_is_not_a_second_name(self):
        """You cannot rename somebody else's paper. Two entries whose published titles
        are "Treatment resistant depression in electronic health records: definitions
        matter" flagged against a lock forbidding "resistant depression", and the only
        repair on offer was to misquote a citation."""
        lock = [{"term": "TRD", "aliases": ["resistant depression"],
                 "first_use": "treatment-resistant depression"}]
        manuscript = ("# Results\n\nTreatment-resistant depression (TRD) was "
                      "assigned on the switch count.\n\n"
                      "# References\n\n"
                      "1. Iveson MH. Treatment resistant depression in electronic "
                      "health records: definitions matter. BMC Psychiatry. 2026.\n")
        self.assertTrue(terminology.check_manuscript(manuscript, lock).passed)

    def test_an_alias_inside_the_term_s_own_expansion_is_not_a_second_name(self):
        """A lock that abbreviates "treatment-resistant depression" to "TRD" and
        forbids "resistant depression" flagged every correct first use, because the
        approved phrase contains the forbidden one."""
        lock = [{"term": "TRD", "aliases": ["resistant depression"],
                 "first_use": "treatment-resistant depression"}]
        text = "Patients with treatment-resistant depression (TRD) were included."
        self.assertEqual(
            [d.kind for d in terminology.check(text, lock).defects], [])

    def test_an_alias_in_the_body_is_still_a_second_name(self):
        lock = [{"term": "TRD", "aliases": ["resistant depression"],
                 "first_use": "treatment-resistant depression"}]
        text = "Patients with resistant depression were switched more often."
        self.assertFalse(terminology.check(text, lock).passed)

    def test_also_called_declares_an_approved_variant(self):
        """`aliases` forbids and `also_called` permits, and both are needed. A real
        naming rule reads "the FEATURE representation (feature vector, typed feature
        vector, feature-vector XGBoost)": three approved names for one arm,
        deliberately. Drift reported all thirty-one uses and offered "declare it as a
        separate locked term", which would assert two arms where there is one."""
        entry = {"term": "feature representation",
                 "aliases": ["feature matrix"],
                 "also_called": ["feature vector"]}
        text = ("The feature vector was built from coded fields. The feature vector "
                "carried ninety-two columns. Nothing else entered it.")
        self.assertTrue(terminology.check_manuscript(text, [entry]).passed)

    def test_an_undeclared_variant_is_still_drift(self):
        entry = {"term": "feature representation", "also_called": ["feature vector"]}
        text = ("The feature pipeline was built from coded fields. The feature "
                "pipeline carried ninety-two columns. Nothing else entered it.")
        report = terminology.check_manuscript(text, [entry])
        self.assertIn("drift", {d.kind for d in report.defects})

    def test_an_empty_lock_disables_the_gate(self):
        self.assertTrue(terminology.check("Anything at all.", []).passed)


class CitationGateTests(unittest.TestCase):

    def test_an_unresolved_marker_fails(self):
        report = citations.check("A prior study found this [27].", {"1": {}, "2": {}})
        self.assertFalse(report.passed)
        self.assertEqual(report.unresolved, ["27"])

    def test_a_numeric_range_expands(self):
        keys, _styles = citations.keys_used("Several studies agree [3-5].")
        self.assertEqual(keys, {"3", "4", "5"})

    def test_an_interval_is_not_a_citation(self):
        """Reference numbering starts at 1, so `[0, 1]` is the unit interval. Any paper
        that mentions a probability writes it, and reading it as a citation invents an
        unresolved reference 0."""
        keys, _styles = citations.keys_used("α was chosen from a grid on [0, 1].")
        self.assertEqual(keys, set())
        self.assertTrue(citations.check("a value in [0, 1] here.", {"1": {}}).passed)

    def test_a_borrowed_claim_with_no_source_is_flagged(self):
        report = citations.check("Prior studies have shown the same pattern.", {})
        self.assertEqual(len(report.missing), 1)

    def test_a_claim_about_this_paper_needs_no_source(self):
        report = citations.check("We found the same pattern in this study.", {})
        self.assertEqual(report.missing, [])

    def test_a_borrowed_claim_with_a_marker_is_fine(self):
        report = citations.check("Prior studies have shown the same pattern [1].",
                                 {"1": {}})
        self.assertEqual(report.missing, [])

    def test_mixing_two_styles_is_a_defect(self):
        report = citations.check("One source says so [1]. Another (Smith, 2024) "
                                 "disagrees.", {"1": {}})
        self.assertTrue(any("mixes" in r for r in report.reasons))

    def test_uncited_references_only_block_at_manuscript_level(self):
        """A reference cited only in the Discussion is not uncited when the Methods is
        being gated."""
        section = citations.check("Nothing cited here at all.", {"1": {}})
        self.assertEqual(section.uncited, [])
        whole = citations.check_manuscript("Nothing cited here at all.", {"1": {}})
        self.assertEqual(whole.uncited, ["1"])
        self.assertFalse(whole.passed)


class PolarityGateTests(unittest.TestCase):
    """One thing asserted and then denied, on the same noun.

    A Methods section said in bold that both representations were built from the same
    curated field inventory, and twenty-five lines later that the two do not receive an
    identical field inventory. Both were true of different senses of "inventory", and
    neither sentence said which. Every other gate passed it."""

    ASSERTED = ("Both representations were built from the same curated field "
                "inventory, and neither was built from a raw record.")
    DENIED = ("FEATURE and EMBEDDED do not receive an identical field inventory, so a "
              "head-to-head comparison estimates two whole pipelines.")

    def _doc(self, sections):
        return "\n\n".join(f"# {name}\n\n{body}\n" for name, body in sections)

    def test_the_pair_that_motivated_the_gate(self):
        report = polarity.check(self._doc([("Methods", self.ASSERTED + " " +
                                            self.DENIED)]))
        self.assertFalse(report.passed)
        self.assertEqual([c.noun for c in report.clashes], ["inventory"])

    def test_the_modifiers_are_discarded_so_the_two_phrasings_key_together(self):
        """"the same curated field inventory" and "an identical field inventory" are
        one claim about one noun. Keying on the phrase is how the pair escapes."""
        report = polarity.check(self._doc([
            ("Methods", self.ASSERTED),
            ("Discussion", "The two arms do not share an identical inventory."),
        ]))
        self.assertEqual([c.noun for c in report.clashes], ["inventory"])

    def test_sameness_asserted_and_never_denied_is_a_paper_doing_its_job(self):
        doc = self._doc([("Methods", self.ASSERTED),
                         ("Results", "Both arms scored the same patients.")])
        self.assertTrue(polarity.check(doc).passed)

    def test_polarity_is_read_at_the_clause_not_the_sentence(self):
        """"built from the same inventory, and neither was built from a raw record" is
        one assertion. The negator governs the clause after the comma."""
        self.assertTrue(polarity.check(self._doc([("Methods", self.ASSERTED)])).passed)

    def test_a_conditional_is_neither_side_of_a_contradiction(self):
        """The supplement section that introduces the crosswalk says the comparison
        holds to the extent that both encodings carry the same information, and the
        table under it is the paper checking that. Counting the conditional as an
        assertion reported the section as contradicting its own opening line."""
        doc = self._doc([
            ("Supplement S8", "It is only a comparison of encodings to the extent "
                              "that both encodings carry the same information. "
                              "Asymmetric marks a row where the two representations "
                              "do not receive the same information."),
        ])
        self.assertTrue(polarity.check(doc).passed)

    def test_an_of_phrase_keys_on_the_thing_not_the_container(self):
        """"the same set of values" is a claim about values and "an identical set of
        rendered fields" is a claim about fields. Keying both on "set" made two
        unrelated sentences a pair."""
        doc = self._doc([
            ("Methods", "The permutation retains the same set of values."),
            ("Supplement", "The two arms do not render an identical set of fields."),
        ])
        self.assertTrue(polarity.check(doc).passed)

    def test_an_empty_head_names_no_respect(self):
        """"the same thing" and "not the same way" collide every sentence in a paper
        and identify nothing."""
        doc = self._doc([
            ("Methods", "Both arms do the same thing."),
            ("Discussion", "They do not do it the same way."),
        ])
        self.assertTrue(polarity.check(doc).passed)

    def test_a_plural_and_a_singular_are_one_noun(self):
        doc = self._doc([
            ("Methods", "Both arms received the same fields."),
            ("Discussion", "The two arms were not given an identical field."),
        ])
        self.assertEqual([c.noun for c in polarity.check(doc).clashes], ["field"])

    def test_the_reason_names_both_sections(self):
        report = polarity.check(self._doc([("Methods", self.ASSERTED),
                                           ("Discussion", self.DENIED)]))
        reason = report.reasons[0]
        self.assertIn("Methods", reason)
        self.assertIn("Discussion", reason)

    def test_the_abstract_restates_the_paper_and_is_not_counted_twice(self):
        doc = self._doc([("Abstract", self.ASSERTED), ("Methods", self.ASSERTED)])
        self.assertEqual(polarity.check(doc).checked, 1)


class RepetitionGateTests(unittest.TestCase):
    """A point the paper makes over and over, section after section.

    One manuscript said in five places that both representations were built from the
    same hand-picked inventory. Every instance was true and relevant. The sixth was cut
    only because a person noticed."""

    POINT = ("Predictor selection ran once, before either representation existed, and "
             "both arms then encoded that same chosen inventory of fields.")

    def _doc(self, sections):
        return "\n\n".join(f"# {name}\n\n{body}\n" for name, body in sections)

    def test_a_point_in_three_sections_is_reported(self):
        doc = self._doc([
            ("Introduction", self.POINT),
            ("Methods", "Predictor selection happened once, before either "
                        "representation existed, and both arms encoded that chosen "
                        "inventory of fields."),
            ("Discussion", "Predictor selection ran once before either representation "
                           "existed, and both arms encoded the same chosen inventory "
                           "of fields."),
        ])
        report = repetition.check(doc)
        self.assertFalse(report.passed)
        self.assertEqual(len(report.echoes), 1)
        self.assertEqual(len(report.echoes[0].sections), 3)

    def test_two_sections_is_a_discussion_doing_its_job(self):
        doc = self._doc([
            ("Results", self.POINT),
            ("Discussion", "Predictor selection ran once, before either "
                           "representation existed, and both arms then encoded that "
                           "same chosen inventory of fields."),
        ])
        self.assertTrue(repetition.check(doc).passed)

    def test_the_abstract_is_supposed_to_restate_the_paper(self):
        """A conclusions section that introduced new material would be the defect."""
        doc = self._doc([
            ("Abstract", self.POINT),
            ("Introduction", self.POINT),
            ("Methods", self.POINT),
        ])
        self.assertEqual(len(repetition.check(doc).echoes), 0)

    def test_a_conclusions_section_restating_the_paper_is_the_section_working(self):
        """A different list from the paragraph gate's: a conclusions section is prose
        and its SHAPE is still checked. Only its echoes are forgiven."""
        doc = self._doc([
            ("Introduction", self.POINT),
            ("Discussion", "Predictor selection happened once, before either "
                           "representation existed, and both arms encoded that chosen "
                           "inventory of fields."),
            ("Conclusions", "Predictor selection ran once before either "
                            "representation existed, and both arms encoded the same "
                            "chosen inventory of fields."),
        ])
        self.assertTrue(repetition.check(doc).passed)

    def test_captions_share_boilerplate_by_design(self):
        """Three clusters of perfectly correct captions, on the first run."""
        cap = ("***Table {n}.** Discrimination of the four classifiers on each "
               "representation (held-out test set). 95% CIs are bootstrap percentile "
               "intervals.*")
        doc = self._doc([("Model discrimination", cap.format(n=2)),
                         ("Model calibration", cap.format(n=3)),
                         ("Robustness across encoders", cap.format(n=5))])
        self.assertTrue(repetition.check(doc).passed)

    def test_two_sections_on_different_topics_do_not_match(self):
        doc = self._doc([
            ("Introduction", self.POINT),
            ("Methods", "Discrimination was summarised with ROC AUC and calibration "
                        "with slope and intercept on the held-out patients."),
            ("Discussion", "The cohort came from one community health system and "
                           "skews middle-aged, which bounds transportability."),
        ])
        self.assertTrue(repetition.check(doc).passed)

    def test_the_report_names_the_sections_a_person_must_open(self):
        doc = self._doc([
            ("Introduction", self.POINT),
            ("Methods", "Predictor selection happened once, before either "
                        "representation existed, and both arms encoded that chosen "
                        "inventory of fields."),
            ("Discussion", "Predictor selection ran once before either representation "
                           "existed, and both arms encoded the same chosen inventory "
                           "of fields."),
        ])
        reason = repetition.check(doc).reasons[0]
        for name in ("Introduction", "Methods", "Discussion"):
            self.assertIn(name, reason)


class ProcedureSpecificationTests(unittest.TestCase):
    """Naming a procedure is not specifying it."""

    def test_a_correction_without_its_error_rate_is_refused(self):
        text = ("P values were adjusted across the entire reported set by "
                "Benjamini-Hochberg. The adjusted value is what we interpret. Two "
                "hundred forty contrasts were computed.")
        report = procedures.check(text)
        self.assertFalse(report.passed)
        self.assertEqual([d.procedure for d in report.defects], ["Benjamini-Hochberg"])

    def test_a_contrast_count_is_not_an_error_rate(self):
        """The numbers around a multiplicity correction are mostly not its
        parameter, which is the whole precision of the check."""
        text = "Two hundred 240 contrasts were adjusted by Benjamini-Hochberg."
        self.assertFalse(procedures.check(text).passed)

    def test_stating_the_rate_clears_it(self):
        text = ("P values were adjusted by Benjamini-Hochberg, controlling the false "
                "discovery rate at 5%. The adjusted value is what we interpret.")
        self.assertTrue(procedures.check(text).passed)

    def test_a_bootstrap_without_its_resample_count_is_refused(self):
        text = ("Confidence intervals were estimated by resampling test-set patients "
                "with replacement. The 2.5th and 97.5th percentiles of the bootstrap "
                "distribution form the 95% confidence interval.")
        self.assertEqual([d.procedure for d in procedures.check(text).defects],
                         ["bootstrap"])

    def test_ninety_five_percent_is_not_a_resample_count(self):
        """It sits beside every bootstrap interval in every paper ever written."""
        text = "Bootstrap percentile 95% confidence intervals are reported throughout."
        self.assertFalse(procedures.check(text).passed)

    def test_stating_the_resample_count_clears_it(self):
        text = ("Intervals come from 1,000 nonparametric bootstrap resamples of the "
                "test-set patients. Percentiles form the 95% interval.")
        self.assertTrue(procedures.check(text).passed)

    def test_the_parameter_may_be_stated_in_the_supplement(self):
        """A manuscript and its supplement are one submission, and a paper should not
        restate a resample count in every caption that mentions a bootstrap."""
        man = "Bootstrap percentile 95% confidence intervals are reported throughout."
        sup = "Intervals come from 1,000 bootstrap resamples drawn with replacement."
        self.assertTrue(procedures.check(man, sup).passed)

    def test_a_procedure_the_paper_never_names_is_not_reported(self):
        report = procedures.check("The model reached a ROC AUC of 0.657 on the test "
                                  "set. Nothing was refit. That is the headline.")
        self.assertEqual(report.defects, [])


class CrossrefGateTests(unittest.TestCase):
    """Pointers the paper makes to itself.

    Three supplement sections were cut from one manuscript in an afternoon. Each
    removal renumbered everything below it, one pass ran twice by mistake, and the
    Methods ended up pointing at the subgroup analysis instead of the crosswalk. Every
    gate passed, because a pointer is the one defect that cannot be seen from inside
    the section that makes it."""

    SUP = ("# Supplement S1. First\n\n***Table S1.** One.*\n\n"
           "# Supplement S2. Second\n\n***Table S2.** Two.*\n\n"
           "***Figure S1.** A picture.*\n")

    def test_a_pointer_to_nothing_is_refused(self):
        man = "The crosswalk is Supplement S7. It settles the question. Read it."
        report = crossrefs.check(man, self.SUP)
        self.assertFalse(report.passed)
        self.assertIn("Supplement S7", {d.label for d in report.defects})

    def test_a_pointer_that_resolves_passes(self):
        man = "The crosswalk is Supplement S2. It settles the question. Read it."
        self.assertTrue(crossrefs.check(man, self.SUP).passed)

    def test_a_gap_in_the_numbering_is_a_missing_item(self):
        """What an excision leaves behind. A reader counts a lost section."""
        sup = self.SUP + "\n# Supplement S4. Fourth\n\nBody text here.\n"
        report = crossrefs.check("The paper is short.", sup)
        self.assertFalse(report.passed)
        self.assertTrue(any(d.kind == "gap" for d in report.defects))

    def test_main_text_and_supplement_are_separate_sequences(self):
        """"Table 2" and "Table S2" are two different objects."""
        man = "***Table 1.** Main.*\n\nThe result is in Table 1 and Table S2."
        self.assertTrue(crossrefs.check(man, self.SUP).passed)

    def test_a_range_names_every_item_in_it(self):
        man = "Those are given in Tables S1-S3."
        report = crossrefs.check(man, self.SUP)
        self.assertIn("Table S3", {d.label for d in report.defects})

    def test_a_kind_with_no_captions_is_not_this_gate_s_business(self):
        """A manuscript with no figure captions at all is being assembled, not
        broken. Firing on it means firing on every section drafted in isolation."""
        self.assertTrue(crossrefs.check("See Figure 4 for the curve.", "").passed)

    def test_the_defect_carries_the_sentence_to_repair(self):
        man = "The crosswalk is Supplement S7. It settles the question. Read it."
        defect = crossrefs.check(man, self.SUP).defects[0]
        self.assertIn("Supplement S7", defect.sentence)


class LengthGateTests(unittest.TestCase):

    def test_over_budget_blocks_and_says_to_cut_a_claim(self):
        report = length.check(1400, budget=1000)
        self.assertFalse(report.passed)
        self.assertIn("Cut, do not compress", report.reason)

    def test_under_budget_blocks_and_says_to_support_a_claim(self):
        report = length.check(400, budget=1000)
        self.assertFalse(report.passed)
        self.assertIn("dropped a claim", report.reason)

    def test_inside_the_band_passes(self):
        for words in (620, 1000, 1140):
            self.assertTrue(length.check(words, budget=1000).passed, words)

    def test_with_no_budget_the_floor_and_the_absolute_ceiling_apply(self):
        self.assertTrue(length.check(1_000).passed)
        self.assertFalse(length.check(10).passed)
        self.assertFalse(length.check(100_000).passed)


class ResultsDensityTests(unittest.TestCase):
    """How many words a Results section spends per number it reports."""

    DENSE = ("Embedded logistic regression reached 0.657 (0.643 to 0.672) and XGBoost "
             "0.649 (0.634 to 0.664). The paired difference was 0.008, on an interval "
             "from -0.003 to 0.019. The lowest configuration reached 0.623 and the "
             "highest 0.657. Tuning grids did not differ between representations.")

    PADDED = ("The two representations behaved in a way that rewards careful reading, "
              "and the pattern that emerges is worth setting out at some length before "
              "the figures are given. What the comparison shows, taken as a whole, is "
              "that neither representation established itself over the other in any "
              "way that a reader should regard as decisive. The reader should keep in "
              "mind that the classifiers were tuned identically throughout. Taken "
              "together these considerations frame everything that follows in this "
              "section, and the single figure worth carrying away is 0.008.")

    def test_a_reporting_section_is_quiet(self):
        report = length.density(self.DENSE, "Model discrimination")
        self.assertEqual(report.warnings, [])
        self.assertLess(report.ratio, config.RESULTS_WORDS_PER_NUMBER_WARN)

    def test_a_section_that_talks_about_its_results_warns(self):
        report = length.density(self.PADDED, "Model discrimination")
        self.assertTrue(report.warnings)
        self.assertTrue(any("talking about the results" in w for w in report.warnings))

    def test_it_warns_and_never_blocks(self):
        """A section that names its predictors rather than measuring them reads this
        way and is right to. Blocking would tell it to invent numbers."""
        self.assertTrue(length.density(self.PADDED, "Model discrimination").passed)

    def test_captions_are_not_reporting_prose(self):
        text = self.DENSE + ("\n\n***Figure 2.** Discrimination by representation and "
                             "classifier, held-out test set, n = 8,516.*\n")
        self.assertEqual(length.density(text, "Model discrimination").numbers,
                         length.density(self.DENSE, "Model discrimination").numbers)

    def test_a_non_results_phase_is_not_measured(self):
        self.assertEqual(length.density(self.PADDED, "Study design").words, 0)

    def test_an_explicit_phase_beats_the_heading(self):
        """"Principal findings" is a Discussion subsection whose heading names no
        phase, so the heading alone cannot tell it from a results subsection."""
        self.assertEqual(
            length.density(self.PADDED, "Principal findings", phase="discussion").words,
            0)

    def test_a_short_section_is_not_a_measurement(self):
        self.assertEqual(length.density("The rate was 17.5%.", "Participant flow").ratio,
                         0.0)


class ReadabilityGateTests(unittest.TestCase):

    def test_syllable_counting_handles_the_silent_e(self):
        self.assertEqual(readability.count_syllables("make"), 1)
        self.assertEqual(readability.count_syllables("table"), 2)

    def test_an_empty_draft_fails(self):
        self.assertFalse(readability.score("").passed)

    def test_a_methods_section_is_measured_but_not_banded(self):
        """Both numbers are dominated by syllables per word, and in a methods section
        the syllable count is the subject matter. Measured on a real manuscript the
        gate refused the main Methods and eight of thirteen Supplementary Methods, at
        reading ease 5 to 19 against a floor of 20, and all nine were correct. The
        lowest was a predictor-selection section at -1.0, which is a list of clinical
        domains and cannot be raised without renaming the analysis."""
        text = ("Domains included depression characteristics, psychiatric and "
                "substance-use comorbidity, medical comorbidity, prior antidepressant "
                "exposure and medication burden, prescribing constraints, health care "
                "utilization, and sociodemographic and social-determinant variables.")
        banded = readability.score(text)
        self.assertFalse(banded.passed)
        for name in ("Methods", "Supplement M4. Predictor selection"):
            report = readability.score(text, section_name=name)
            self.assertTrue(report.passed, name)
            # Still measured, so the record shows what it scored.
            self.assertEqual(report.flesch_ease, banded.flesch_ease)

    def test_a_results_section_is_still_banded(self):
        """What is left is the sections where the vocabulary is a choice."""
        text = ("Domains included depression characteristics, psychiatric and "
                "substance-use comorbidity, medical comorbidity, prior antidepressant "
                "exposure and medication burden, prescribing constraints, health care "
                "utilization, and sociodemographic and social-determinant variables.")
        self.assertFalse(readability.score(text, section_name="Results").passed)

    def test_academic_prose_sits_in_the_band(self):
        report = readability.score(support.CLEAN_PROSE)
        self.assertGreaterEqual(report.fk_grade, 0)
        self.assertEqual(report.words, len(prose.words(support.CLEAN_PROSE)))


class CoverageGateTests(unittest.TestCase):

    EVIDENCE = {"items": [
        {"id": "e.1", "statement": "held-out AUC was 0.7429", "source": "x"},
        {"id": "e.2", "statement": "the cohort held 8516 patients", "source": "x"},
    ]}

    def test_declared_ids_are_the_exact_path(self):
        report = coverage.check(self.EVIDENCE,
                                [{"claim": "anything", "evidence": ["e.1"]}])
        self.assertTrue(report.passed)

    def test_a_declared_id_that_does_not_exist_is_uncovered(self):
        report = coverage.check(self.EVIDENCE,
                                [{"claim": "anything", "evidence": ["e.9"]}])
        self.assertFalse(report.passed)

    def test_naming_falls_back_to_identifying_words(self):
        """A claim need not quote the evidence: every identifying word appearing
        somewhere is enough. Demanding the claim's exact phrasing penalises evidence
        for using the abbreviation the paper itself locked."""
        report = coverage.check(self.EVIDENCE, ["patients in the cohort"])
        self.assertTrue(report.passed)

    def test_a_claim_about_nothing_in_the_evidence_is_uncovered(self):
        report = coverage.check(self.EVIDENCE, ["genotype interaction effects"])
        self.assertFalse(report.passed)
        self.assertEqual(report.missing, ["genotype interaction effects"])

    def test_no_claims_means_full_coverage(self):
        self.assertTrue(coverage.check(self.EVIDENCE, []).passed)


class ArgumentGateTests(unittest.TestCase):

    def _claims(self, **overrides):
        base = [
            {"id": "c.1", "claim": "text beats features", "kind": "comparative",
             "evidence": ["e.1"], "headline": True},
            {"id": "c.2", "claim": "the split is large enough", "kind": "descriptive",
             "evidence": ["e.2"]},
            {"id": "c.3", "claim": "discrimination is not benefit",
             "kind": "limitation", "evidence": ["e.1"]},
            {"id": "c.4", "claim": "a threshold must be chosen", "kind": "implication",
             "evidence": ["e.1"]},
        ]
        for cid, patch in overrides.items():
            for claim in base:
                if claim["id"] == cid.replace("_", "."):
                    claim.update(patch)
        return base

    IDS = {"e.1", "e.2"}

    def test_a_well_formed_map_passes(self):
        report = claims.check(self._claims(), evidence_ids=self.IDS)
        self.assertTrue(report.passed, report.errors)

    def test_a_claim_with_no_evidence_is_refused(self):
        report = claims.check(self._claims(c_2={"evidence": []}),
                              evidence_ids=self.IDS)
        self.assertFalse(report.passed)
        self.assertTrue(any("rests on no evidence" in e for e in report.errors))

    def test_two_headline_claims_is_two_papers(self):
        report = claims.check(self._claims(c_2={"headline": True}),
                              evidence_ids=self.IDS)
        self.assertFalse(report.passed)
        self.assertTrue(any("headline" in e for e in report.errors))

    def test_no_headline_claim_is_refused(self):
        report = claims.check(self._claims(c_1={"headline": False}),
                              evidence_ids=self.IDS)
        self.assertFalse(report.passed)

    def test_a_map_with_no_limitation_is_refused(self):
        report = claims.check(self._claims(c_3={"kind": "descriptive"}),
                              evidence_ids=self.IDS)
        self.assertFalse(report.passed)
        self.assertTrue(any("limitation" in e for e in report.errors))

    def test_the_same_claim_twice_is_refused(self):
        doubled = self._claims() + [
            {"id": "c.5", "claim": "the text beats the features", "kind": "comparative",
             "evidence": ["e.1"]}]
        report = claims.check(doubled, evidence_ids=self.IDS)
        self.assertFalse(report.passed)
        self.assertTrue(any("say the same thing" in e for e in report.errors))

    def test_unused_evidence_is_a_warning_not_a_failure(self):
        report = claims.check(self._claims(), evidence_ids={"e.1", "e.2", "e.9"})
        self.assertTrue(report.passed)
        self.assertTrue(any("e.9" in w for w in report.warnings))


class UnnamedPointerTests(unittest.TestCase):
    """A pointer with no identifier is not a pointer any resolver can follow, so
    nothing was looking for it."""

    MAN = ("# Results\n\n"
           "***Table 1.** Selected cohort characteristics by TRD status. %s*\n\n"
           "| Characteristic | Overall |\n| --- | ---: |\n| Age | 55 |\n")

    def test_a_pointer_that_names_nothing_is_refused(self):
        """"Full table in supporting material" appeared in a finished manuscript. No
        such document existed, the caption's own sentence above it said "Table 1 gives
        every selected characteristic", and every gate passed."""
        report = crossrefs.check(self.MAN % "Full table in supporting material.")
        self.assertFalse(report.passed)
        self.assertIn("unnamed", {d.kind for d in report.defects})

    def test_a_pointer_that_names_its_target_passes(self):
        man = (self.MAN % "The stratified version is in Supplement S7."
               + "\n# Supplement S7. Subgroups\n\nRows.\n")
        self.assertNotIn("unnamed",
                         {d.kind for d in crossrefs.check(man).defects})

    def test_a_supplement_pointer_with_a_bracketed_table_passes(self):
        man = self.MAN % "The crosswalk is in the supplement (Table S9)."
        self.assertNotIn("unnamed",
                         {d.kind for d in crossrefs.check(man).defects})

    def test_a_numbered_appendix_is_named(self):
        man = self.MAN % "The complete inventory is in Appendix 1."
        self.assertNotIn("unnamed",
                         {d.kind for d in crossrefs.check(man).defects})


class ReferenceOrderTests(unittest.TestCase):
    """Vancouver numbers by order of first appearance. Every marker resolves, every
    entry is cited, the list is contiguous, and it is still wrong."""

    REFS = {str(n): {} for n in range(1, 5)}

    def test_markers_out_of_first_appearance_order_are_refused(self):
        text = ("# Introduction\n\nOthers looked at this [3]. So did others [1]. "
                "And more [2]. And one more [4].\n")
        report = citations.check_manuscript(text, self.REFS)
        self.assertFalse(report.passed)
        self.assertEqual(report.misordered, (1, 3, 1))

    def test_markers_in_order_pass(self):
        text = ("# Introduction\n\nOthers looked at this [1]. Two agree [2,3]. "
                "One more [4].\n")
        report = citations.check_manuscript(text, self.REFS)
        self.assertIsNone(report.misordered)
        self.assertTrue(report.passed, report.reasons)

    def test_a_group_contributes_its_numbers_in_ascending_order(self):
        """A marker naming several references reaches them in the order they are
        printed inside it, so [1-3] is 1 then 2 then 3."""
        self.assertEqual(
            citations.first_appearance_order("First [1-3]. Then [4]."),
            [1, 2, 3, 4])

    def test_a_manuscript_with_no_numeric_markers_is_not_judged(self):
        self.assertIsNone(citations.out_of_order("No markers here at all."))


class VenueGateTests(unittest.TestCase):
    """The journal's own rules. Every other gate asks whether the manuscript is good;
    this one asks whether the file will be accepted, which an editorial assistant
    settles in ninety seconds and which no other gate here can see."""

    GOOD = (
        "# Title page\n\n**Title.** A Study\n\n"
        "# Abstract\n\n"
        # Sentences rather than a run of tokens: the gate reads the abstract's
        # shape now, and a 40-word block with no full stop in it is a 40-word
        # sentence.
        "**Background.** " + "Word word word word. " * 10 + "\n\n"
        "**Objective.** " + "Word word word word. " * 7 + "\n\n"
        "**Methods.** " + "Word word word word. " * 8 + "\n\n"
        "**Results.** " + "Word word word word. " * 9 + "\n\n"
        "**Conclusions.** " + "Word word word word. " * 5 + "\n\n"
        "**Keywords.** one; two; three; four; five; six\n\n"
        "# Introduction\n\nThe question is open. Nobody has answered it.\n\n"
        "# Methods\n\nThe cohort was assembled from records. Nothing was refit.\n\n"
        "# Results\n\nThe model discriminated modestly. Calibration was adequate.\n\n"
        "# Discussion\n\nThe finding is a null. It bounds one comparison only.\n\n"
        "# Ethical Considerations\n\nSecondary analysis of existing records.\n\n"
        "# Acknowledgments\n\nNone.\n\n"
        "# Funding\n\nNone.\n\n"
        "# Conflicts of Interest\n\nNone declared.\n\n"
        "# Data Availability\n\nOn request.\n\n"
        "# Authors' Contributions\n\nMF did the work.\n\n"
        "# Protocol and Registration\n\nNot registered.\n\n"
        "# Abbreviations\n\nTRD: treatment-resistant depression.\n\n"
        "# Multimedia Appendix 1\n\nThe supplement.\n\n"
        "# References\n\n1. Someone. A paper. Journal. 2024.\n"
    )

    def test_a_compliant_manuscript_passes(self):
        report = venue.check(self.GOOD, "JMIR Mental Health")
        self.assertTrue(report.passed, report.errors)

    def test_a_heading_marker_inside_a_line_is_refused(self):
        """One absent newline left "...documented in Supplement S8. # Methods" at the
        end of an Introduction paragraph. Pandoc printed the four characters as body
        text, the built .docx had no Methods heading anywhere, and every gate passed
        because the section boundary the gates are handed had stopped existing."""
        text = self.GOOD.replace(
            "records. Nothing was refit.\n\n# Results",
            "records. Nothing was refit. # Results")
        report = venue.check(text, "JMIR")
        self.assertFalse(report.passed)
        self.assertTrue(any("instead of opening" in e for e in report.errors),
                        report.errors)

    def test_a_missing_imrad_heading_is_refused(self):
        report = venue.check(self.GOOD.replace("# Results\n", "# Outcomes\n"), "JMIR")
        self.assertFalse(report.passed)
        self.assertTrue(any("no `Results` heading" in e for e in report.errors),
                        report.errors)

    def test_an_unprofiled_venue_does_not_pass_silently(self):
        """Writing to a journal nobody has profiled is ordinary. Being told the
        manuscript is compliant against rules nobody checked is how an 810-word
        abstract survived two redrafts."""
        report = venue.check(self.GOOD, "Journal of Made Up Things")
        self.assertFalse(report.passed)
        self.assertTrue(any("no venue profile" in e for e in report.errors))

    def test_no_venue_at_all_does_not_pass_silently(self):
        self.assertFalse(venue.check(self.GOOD, "").passed)

    def test_an_over_length_abstract_is_refused(self):
        text = self.GOOD.replace("**Methods.** " + "Word word word word. " * 8,
                                 "**Methods.** " + "Word word word word. " * 100)
        report = venue.check(text, "JMIR")
        self.assertFalse(report.passed)
        self.assertTrue(any("against this venue's ceiling" in e
                            for e in report.errors))

    def test_the_venue_labels_are_not_charged_to_the_author(self):
        """The structured headings are the venue's own form. Counting them against
        the author's allowance is charging them for the boilerplate."""
        report = venue.check(self.GOOD, "JMIR")
        self.assertNotIn("Background", str(report.stats))
        self.assertLess(report.stats["abstract_words"], 450)

    def test_a_missing_structured_heading_is_refused(self):
        report = venue.check(self.GOOD.replace("**Objective.**", "**Aim.**"), "JMIR")
        self.assertFalse(report.passed)
        self.assertTrue(any("no `Objective` heading" in e for e in report.errors))

    def test_a_missing_mandatory_section_is_refused(self):
        report = venue.check(self.GOOD.replace("# Abbreviations", "# Notes"),
                             "JMIR")
        self.assertFalse(report.passed)
        self.assertTrue(any("`Abbreviations` heading" in e for e in report.errors))

    def test_a_url_in_the_body_is_refused(self):
        """The commonest way to break this is a Methods section naming its own code
        repository, which reads as good practice and is not what the venue asked."""
        text = self.GOOD.replace("Nothing was refit.",
                                 "Code is at https://github.com/x/y.")
        report = venue.check(text, "JMIR")
        self.assertFalse(report.passed)
        self.assertTrue(any("URL(s) in the body" in e for e in report.errors))

    def test_a_url_in_the_reference_list_is_fine(self):
        text = self.GOOD.replace("1. Someone. A paper. Journal. 2024.",
                                 "1. Someone. A paper. https://example.org/x")
        self.assertTrue(venue.check(text, "JMIR").passed)

    def test_too_few_keywords_is_refused(self):
        report = venue.check(self.GOOD.replace(
            "one; two; three; four; five; six", "one; two"), "JMIR")
        self.assertFalse(report.passed)
        self.assertTrue(any("keyword" in e for e in report.errors))

    def test_an_advisory_limit_warns_and_says_what_it_costs(self):
        """A venue that recommends a length and charges above it has not set a
        ceiling. Blocking there refuses legitimate manuscripts; saying nothing lets
        the author find out at invoice."""
        long_body = self.GOOD.replace("The cohort was assembled from records.",
                                      "The cohort was assembled. " * 6000)
        report = venue.check(long_body, "JMIR")
        self.assertTrue(report.passed, report.errors)
        self.assertTrue(any("fees" in w for w in report.warnings))

    def test_a_profile_that_has_not_decided_a_key_is_refused(self):
        """A key that is absent is a requirement nobody looked up. `None` records
        that the venue states no limit; missing records that nobody checked."""
        from paperwriter import venues
        half = {k: v for k, v in venues.JMIR.items() if k != "references_max"}
        report = venue.check(self.GOOD, "JMIR", profile=half)
        self.assertFalse(report.passed)
        self.assertTrue(any("does not decide" in e for e in report.errors))

    def test_a_stale_profile_is_reported_rather_than_trusted(self):
        from datetime import date, timedelta
        from paperwriter import venues
        old = dict(venues.JMIR)
        report = venue.check(self.GOOD, "JMIR", profile=old,
                             today=old["checked"] + timedelta(days=900))
        self.assertTrue(report.passed, report.errors)
        self.assertTrue(any("re-read it before submitting" in w
                            for w in report.warnings))


class TitleLengthTests(unittest.TestCase):
    """A title nobody can read is a paper nobody opens."""

    HEAD = ("# Title page\n\n**Title.** {title}\n\n**Short title.** {short}\n\n"
            "**Authors.** A B.\n")

    def _check(self, title, short):
        return venue.check(self.HEAD.format(title=title, short=short), "JMIR")

    def test_an_overlong_title_is_refused_when_the_venue_states_no_limit(self):
        """Most venues state no character limit, which meant nothing checked a title
        at all. This one ran 34 words with every word of it accurate."""
        long_title = ("Typed Feature Vectors, Generalized Pretrained Transformer "
                      "Embeddings of Deterministic Patient Narratives, and "
                      "Nearest-Neighbor Retrieval for Predicting a "
                      "Treatment-Switch-Defined Electronic Health Record Proxy for "
                      "Treatment-Resistant Depression: Retrospective Cohort Study")
        errors = self._check(long_title, "Short One").errors
        self.assertTrue(any("words against a ceiling" in e for e in errors))

    def test_a_title_that_names_the_finding_and_the_design_passes(self):
        title = ("Narrative Embeddings Do Not Outperform Typed Features for a "
                 "Treatment-Switch Proxy of Treatment-Resistant Depression: "
                 "Retrospective Cohort Study")
        errors = self._check(title, "Embeddings and Typed Features for TRD "
                                    "Prediction").errors
        self.assertEqual([e for e in errors if "title" in e.lower()], [])

    def test_a_short_title_is_a_running_head(self):
        """The constraint is the page margin, not taste."""
        errors = self._check("A Short Title", "Curated EHR Representations and "
                             "Patient Retrieval for Predicting a Treatment-Switch "
                             "Proxy for Treatment-Resistant Depression").errors
        self.assertTrue(any("running head" in e for e in errors))

    def test_the_measurements_are_reported_either_way(self):
        stats = self._check("A B C", "D E").stats
        self.assertEqual(stats["title_words"], 3)
        self.assertEqual(stats["short_title_chars"], 3)


class SupportLadderTests(unittest.TestCase):
    """The ladder: points <- claims <- evidence. The rung this gate owns is the top
    one, and the failure it was written from is a manuscript where every other gate
    passed and a reader still could not say what the paper claimed."""

    POINTS = [
        {"id": "p.1", "point": "The embedding does not outperform the feature vector "
                               "on this outcome."},
        {"id": "p.2", "point": "Retrieval over that embedding loses to a model fitted "
                               "on it."},
    ]

    def _claims(self, **overrides):
        base = [
            {"id": "c.1", "claim": "the two representations tie",
             "kind": "comparative", "serves": ["p.1"], "headline": True},
            {"id": "c.2", "claim": "the tie holds across four encoders",
             "kind": "descriptive", "serves": ["p.1"]},
            {"id": "c.3", "claim": "nearest retrieval beats random retrieval",
             "kind": "descriptive", "serves": ["p.2"], "headline": True},
            {"id": "c.4", "claim": "retrieval falls short of the trained model",
             "kind": "comparative", "serves": ["p.2"]},
            {"id": "c.5", "claim": "the cohort is one community health system",
             "kind": "descriptive", "role": "setup"},
        ]
        for cid, patch in overrides.items():
            for claim in base:
                if claim["id"] == cid.replace("_", "."):
                    claim.update(patch)
        return base

    def test_a_well_formed_ladder_passes(self):
        report = ladder.check(self.POINTS, self._claims())
        self.assertTrue(report.passed, report.errors)

    def test_no_points_is_a_list_of_findings(self):
        report = ladder.check([], self._claims())
        self.assertFalse(report.passed)
        self.assertTrue(any("declares no points" in e for e in report.errors))

    def test_too_many_points_is_several_papers(self):
        points = self.POINTS + [
            {"id": f"p.{i}", "point": f"a {i}th thing the paper is also about here"}
            for i in range(3, 6)]
        claims = self._claims() + [
            {"id": f"c.1{i}", "claim": f"support {i}", "kind": "descriptive",
             "serves": [f"p.{i}"], "headline": True} for i in range(3, 6)
        ] + [
            {"id": f"c.2{i}", "claim": f"more support {i}", "kind": "descriptive",
             "serves": [f"p.{i}"]} for i in range(3, 6)]
        report = ladder.check(points, claims)
        self.assertFalse(report.passed)
        self.assertTrue(any("the ceiling is" in e for e in report.errors))

    def test_a_point_that_is_a_topic_is_refused(self):
        points = [dict(self.POINTS[0], point="representation comparison"),
                  self.POINTS[1]]
        report = ladder.check(points, self._claims())
        self.assertFalse(report.passed)
        self.assertTrue(any("topic, not a point" in e for e in report.errors))

    def test_a_claim_serving_nothing_is_refused(self):
        report = ladder.check(self.POINTS, self._claims(c_2={"serves": []}))
        self.assertFalse(report.passed)
        self.assertTrue(any("serves no point and declares no role" in e
                            for e in report.errors))

    def test_a_claim_cannot_both_serve_and_have_a_role(self):
        report = ladder.check(self.POINTS, self._claims(c_2={"role": "setup"}))
        self.assertFalse(report.passed)
        self.assertTrue(any("both serves" in e for e in report.errors))

    def test_an_unknown_role_is_refused_and_names_the_valid_ones(self):
        report = ladder.check(self.POINTS,
                               self._claims(c_5={"role": "validity"}))
        self.assertFalse(report.passed)
        self.assertTrue(any("no role for a validity check" in e
                            for e in report.errors))

    def test_a_claim_serving_a_point_that_does_not_exist_is_refused(self):
        report = ladder.check(self.POINTS, self._claims(c_2={"serves": ["p.9"]}))
        self.assertFalse(report.passed)
        self.assertTrue(any("does not declare" in e for e in report.errors))

    def test_a_point_carried_by_one_claim_is_that_claim(self):
        report = ladder.check(self.POINTS, self._claims(c_2={"serves": ["p.2"]}))
        self.assertFalse(report.passed)
        self.assertTrue(any("is served by 1 claim" in e for e in report.errors))

    def test_a_point_supported_only_by_caveats_is_not_a_finding(self):
        claims = self._claims(c_3={"kind": "limitation"},
                              c_4={"kind": "limitation"})
        report = ladder.check(self.POINTS, claims)
        self.assertFalse(report.passed)
        self.assertTrue(any("only by limitation claims" in e
                            for e in report.errors))

    def test_every_point_has_one_claim_that_states_it(self):
        report = ladder.check(self.POINTS, self._claims(c_3={"headline": False}))
        self.assertFalse(report.passed)
        self.assertTrue(any("no claim marked `headline`" in e
                            for e in report.errors))

    def test_two_claims_cannot_both_state_one_point(self):
        report = ladder.check(self.POINTS, self._claims(c_2={"headline": True}))
        self.assertFalse(report.passed)
        self.assertTrue(any("claims marked `headline`" in e
                            for e in report.errors))

    def test_the_role_allowance_is_bounded(self):
        """An unbounded exemption turns the ladder into decoration, and `setup` is the
        easiest label in the world to reach for."""
        claims = self._claims()
        claims += [{"id": f"c.1{i}", "claim": f"more background {i}",
                    "kind": "descriptive", "role": "setup"} for i in range(4)]
        report = ladder.check(self.POINTS, claims)
        self.assertFalse(report.passed)
        self.assertTrue(any("the ladder is" in e for e in report.errors))


class SupportLadderBudgetTests(unittest.TestCase):
    """The word-budget half. A graph check asks whether every claim has a parent,
    which a writer satisfies by attaching claims loosely; length cannot be argued
    with, and it is the half that catches a complete and irrelevant section."""

    POINTS = [{"id": "p.1", "point": "The embedding does not outperform the feature "
                                     "vector on this outcome."}]
    CLAIMS = [
        {"id": "c.1", "claim": "the two tie", "kind": "comparative",
         "serves": ["p.1"], "headline": True},
        {"id": "c.2", "claim": "the tie holds across encoders", "kind": "descriptive",
         "serves": ["p.1"]},
        {"id": "c.9", "claim": "the judge rubric was mislabelled",
         "kind": "descriptive", "role": "reporting"},
    ]

    def _outline(self, aside_words):
        return {"sections": [
            {"number": 1, "heading": "Introduction", "words": 400, "claims": []},
            {"number": 2, "heading": "Results", "words": 1000, "claims": ["c.1", "c.2"]},
            {"number": 3, "heading": "A similarity judge nobody needed",
             "words": aside_words, "claims": ["c.9"]},
            {"number": 4, "heading": "References", "words": 300, "claims": []},
        ]}

    def test_a_small_aside_passes(self):
        report = ladder.check(self.POINTS, self.CLAIMS, outline=self._outline(120))
        self.assertTrue(report.passed, report.errors)

    def test_a_section_serving_nothing_is_refused_on_length(self):
        report = ladder.check(self.POINTS, self.CLAIMS, outline=self._outline(900))
        self.assertFalse(report.passed)
        self.assertTrue(any("serve no point" in e for e in report.errors))
        self.assertTrue(any("A similarity judge nobody needed" in e
                            for e in report.errors))

    def test_the_share_is_warned_about_before_it_blocks(self):
        report = ladder.check(self.POINTS, self.CLAIMS, outline=self._outline(250))
        self.assertTrue(report.passed, report.errors)
        self.assertTrue(any("grows quietly" in w for w in report.warnings))

    def test_a_section_with_no_claims_is_structural_not_unladdered(self):
        """An Introduction that sets up every point without asserting one is the
        ordinary case. Counting its words as serving nothing fires on every paper."""
        outline = self._outline(120)
        outline["sections"][0]["words"] = 4000        # an enormous claim-free section
        report = ladder.check(self.POINTS, self.CLAIMS, outline=outline)
        self.assertTrue(report.passed, report.errors)


class ClaimWordCeilingTests(unittest.TestCase):
    """The budget from the other side: material attached to something, then written
    until it outweighs the claim it belongs to."""

    POINTS = [{"id": "p.1", "point": "The embedding does not outperform the feature "
                                     "vector on this outcome."}]

    def _claims(self, aside_kind="descriptive"):
        return [
            {"id": "c.1", "claim": "the two tie", "kind": "comparative",
             "serves": ["p.1"], "headline": True},
            {"id": "c.2", "claim": "the tie holds across encoders",
             "kind": "descriptive", "serves": ["p.1"]},
            {"id": "c.3", "claim": "the ablation localises the signal",
             "kind": "mechanistic", "serves": ["p.1"]},
            {"id": "c.4", "claim": "retrieval is informative, not competitive",
             "kind": "comparative", "serves": ["p.1"]},
            {"id": "c.5", "claim": "the cohort is single-site", "kind": "descriptive",
             "role": "setup"},
            {"id": "c.6", "claim": "fusing the inverted farthest signal does not help",
             "kind": aside_kind, "serves": ["p.1"]},
        ]

    def _outline(self, fusion_words):
        return {"sections": [
            {"number": 1, "heading": "Introduction", "words": 400, "claims": []},
            {"number": 2, "heading": "Results", "words": 2400,
             "claims": ["c.1", "c.2", "c.3", "c.4"]},
            {"number": 3, "heading": "Cohort", "words": 600, "claims": ["c.5"]},
            {"number": 4, "heading": "Nearest-farthest retrieval fusion",
             "words": fusion_words, "claims": ["c.6"]},
            {"number": 5, "heading": "References", "words": 300, "claims": []},
        ]}

    def test_a_proportionate_strand_is_silent(self):
        report = ladder.check(self.POINTS, self._claims(),
                              outline=self._outline(300))
        self.assertTrue(report.passed, report.errors)
        self.assertEqual([w for w in report.warnings if "soft ceiling" in w], [])

    def test_an_overgrown_strand_is_warned_about_not_refused(self):
        """Word share is a proxy, and a proxy that stalls a run is a proxy somebody
        raises until it stops firing."""
        report = ladder.check(self.POINTS, self._claims(),
                              outline=self._outline(1900))
        self.assertTrue(report.passed, report.errors)
        self.assertTrue(any("soft ceiling" in w for w in report.warnings))
        self.assertTrue(any("'c.6'" in w for w in report.warnings))

    def test_a_limitation_written_at_the_length_of_a_finding_is_refused(self):
        report = ladder.check(self.POINTS, self._claims(aside_kind="limitation"),
                              outline=self._outline(1900))
        self.assertFalse(report.passed)
        self.assertTrue(any("reads as a finding" in e for e in report.errors))

    def test_a_ceiling_an_even_split_cannot_meet_does_not_fire(self):
        """A two-claim paper puts half of itself on each claim by construction.
        Refusing that is refusing arithmetic."""
        points = self.POINTS
        claims = [
            {"id": "c.1", "claim": "the two tie", "kind": "comparative",
             "serves": ["p.1"], "headline": True},
            {"id": "c.2", "claim": "a caveat", "kind": "limitation",
             "serves": ["p.1"]},
        ]
        outline = {"sections": [
            {"number": 1, "heading": "Results", "words": 1000, "claims": ["c.1"]},
            {"number": 2, "heading": "Limitations", "words": 1000, "claims": ["c.2"]},
        ]}
        report = ladder.check(points, claims, outline=outline)
        self.assertEqual([e for e in report.errors if "reads as a finding" in e], [])

    def test_the_attribution_is_reported_for_a_person_to_check(self):
        report = ladder.check(self.POINTS, self._claims(),
                              outline=self._outline(1900))
        self.assertEqual(report.stats["claim_words"]["c.6"], 1900)
        self.assertEqual(report.stats["claim_words"]["c.1"], 600)


class SupportLadderMigrationTests(unittest.TestCase):
    """A claim map written before the ladder existed marks one claim `headline`,
    declares no points, and gives no claim a `serves`. Refusing those would strand
    state that is otherwise fine, so both halves of the migration travel together."""

    LEGACY = [
        {"id": "c.1", "claim": "the embedded representation discriminates better",
         "kind": "comparative", "headline": True},
        {"id": "c.2", "claim": "the split is large enough to estimate the gap",
         "kind": "descriptive"},
        {"id": "c.3", "claim": "discrimination is not benefit", "kind": "limitation"},
    ]

    def test_a_pre_ladder_map_migrates_to_one_point(self):
        points, claims = ladder.migrated([], self.LEGACY)
        self.assertEqual([p["id"] for p in points], ["p.1"])
        self.assertEqual(points[0]["derived_from"], "c.1")
        self.assertTrue(all(c["serves"] == ["p.1"] for c in claims))
        self.assertTrue(ladder.check(points, claims).passed)

    def test_a_derived_point_is_not_measured_as_prose(self):
        """It inherits its wording from the claim it came from, so measuring its
        length measures that claim against a rule it never had to meet."""
        terse = [{"id": "c.1", "claim": "text wins", "kind": "comparative",
                  "headline": True},
                 {"id": "c.2", "claim": "twice over", "kind": "descriptive"}]
        points, claims = ladder.migrated([], terse)
        self.assertTrue(ladder.check(points, claims).passed)

    def test_declared_points_are_not_filled_in(self):
        """Under declared points a claim with no `serves` skipped a field that
        exists, which is a different thing from a map that predates it."""
        points = [{"id": "p.1", "point": "a thing this paper is genuinely about"}]
        _p, claims = ladder.migrated(points, self.LEGACY)
        self.assertFalse(any(c.get("serves") for c in claims))
        self.assertFalse(ladder.check(points, claims).passed)

    def test_a_map_with_no_headline_does_not_migrate_silently(self):
        points, _claims = ladder.migrated([], [dict(self.LEGACY[1])])
        self.assertEqual(points, [])


class OutlineParagraphLadderTests(unittest.TestCase):
    """The rung below the ladder: a section can carry three claims, plan nine
    paragraphs that touch two of them, and simply not make the third."""

    def _outline(self, paragraphs):
        return {"sections": [{
            "number": 1, "heading": "Results", "words": 600,
            "claims": ["c.1", "c.2"], "evidence": [],
            "paragraphs": paragraphs}]}

    def test_a_paragraph_advancing_a_claim_passes(self):
        outline = self._outline([
            {"topic": "The two representations discriminated alike.",
             "supports": ["c.1"]},
            {"topic": "That tie held across every encoder tested.",
             "supports": ["c.2"]},
        ])
        self.assertTrue(structure.check(outline).passed)

    def test_a_claim_no_paragraph_makes_is_refused(self):
        outline = self._outline([
            {"topic": "The two representations discriminated alike.",
             "supports": ["c.1"]},
            {"topic": "The interval was narrower than the marginal ones.",
             "supports": ["c.1"]},
        ])
        report = structure.check(outline)
        self.assertFalse(report.passed)
        self.assertTrue(any("no paragraph advances" in e for e in report.errors))

    def test_a_paragraph_cannot_advance_another_sections_claim(self):
        outline = self._outline([
            {"topic": "The two representations discriminated alike.",
             "supports": ["c.1"]},
            {"topic": "That tie held across every encoder tested.",
             "supports": ["c.2", "c.7"]},
        ])
        report = structure.check(outline)
        self.assertFalse(report.passed)
        self.assertTrue(any("which this section does not carry" in e
                            for e in report.errors))

    def test_a_section_of_transitions_has_no_argument_in_it(self):
        outline = self._outline([
            {"topic": "This paragraph sets the scene for what follows.",
             "role": "transition"},
            {"topic": "This paragraph also sets the scene for what follows.",
             "role": "transition"},
            {"topic": "The two representations discriminated alike.",
             "supports": ["c.1", "c.2"]},
        ])
        report = structure.check(outline)
        self.assertFalse(report.passed)
        self.assertTrue(any("no argument in it" in e for e in report.errors))

    def test_a_claimless_section_is_structural(self):
        outline = {"sections": [{
            "number": 1, "heading": "Declarations", "words": 200, "claims": [],
            "evidence": [], "paragraphs": [
                {"topic": "The funder had no role in the analysis."},
                {"topic": "The authors declare no competing interests."},
            ]}]}
        self.assertTrue(structure.check(outline).passed)


class OutlineStructureTests(unittest.TestCase):

    def _section(self, number, heading, words=500, claims_=(), paragraphs_=None):
        return {
            "number": number, "heading": heading, "words": words,
            "claims": list(claims_), "evidence": [],
            "paragraphs": paragraphs_ if paragraphs_ is not None else [
                {"topic": "This paragraph makes a claim about the cohort."},
                {"topic": "This paragraph makes a claim about the model."},
            ]}

    def _outline(self, headings=("Introduction", "Methods", "Results", "Discussion")):
        return {"sections": [self._section(i, h)
                             for i, h in enumerate(headings, start=1)]}

    def test_a_well_formed_outline_passes(self):
        self.assertTrue(structure.check(self._outline()).passed)

    def test_results_before_methods_is_refused(self):
        outline = self._outline(("Introduction", "Results", "Methods", "Discussion"))
        report = structure.check(outline)
        self.assertFalse(report.passed)
        self.assertTrue(any("belongs before it" in e for e in report.errors))

    def test_a_duplicate_heading_is_refused(self):
        outline = self._outline(("Methods", "Methods"))
        self.assertFalse(structure.check(outline).passed)

    def test_budgets_over_the_venue_limit_are_refused(self):
        report = structure.check(self._outline(), word_limit=1000)
        self.assertFalse(report.passed)
        self.assertTrue(any("Cut a claim" in e for e in report.errors))

    def test_a_paragraph_with_no_topic_sentence_is_refused(self):
        outline = self._outline()
        outline["sections"][0]["paragraphs"] = [{"topic": ""}]
        report = structure.check(outline)
        self.assertFalse(report.passed)
        self.assertTrue(any("no topic sentence" in e for e in report.errors))

    def test_a_topic_label_is_not_a_topic_sentence(self):
        outline = self._outline()
        outline["sections"][0]["paragraphs"] = [{"topic": "cohort characteristics"}]
        report = structure.check(outline)
        self.assertFalse(report.passed)
        self.assertTrue(any("label, not a claim" in e for e in report.errors))

    def test_a_section_with_no_paragraph_plan_is_refused(self):
        outline = self._outline()
        outline["sections"][0]["paragraphs"] = []
        self.assertFalse(structure.check(outline).passed)

    def test_a_claim_placed_twice_is_refused(self):
        outline = self._outline(("Methods", "Results"))
        outline["sections"][0]["claims"] = ["c.1"]
        outline["sections"][1]["claims"] = ["c.1"]
        report = structure.check(outline, argument_claims=[
            {"id": "c.1", "claim": "x"}])
        self.assertFalse(report.passed)
        self.assertTrue(any("already placed" in e for e in report.errors))

    def test_a_claim_the_map_does_not_hold_is_refused(self):
        outline = self._outline(("Results",))
        outline["sections"][0]["claims"] = ["c.9"]
        report = structure.check(outline, argument_claims=[
            {"id": "c.1", "claim": "x"}])
        self.assertFalse(report.passed)

    def test_an_unplaced_claim_is_refused(self):
        outline = self._outline(("Results",))
        report = structure.check(outline, argument_claims=[
            {"id": "c.1", "claim": "x"}])
        self.assertFalse(report.passed)
        self.assertTrue(any("no section makes it" in e for e in report.errors))

    def test_front_matter_and_back_matter_sort_correctly(self):
        self.assertEqual(structure.phase_of("Abstract"), "front")
        self.assertEqual(structure.phase_of("Statistical analysis"), "methods")
        self.assertEqual(structure.phase_of("Declarations"), "back")
        self.assertEqual(structure.phase_of("Something Else"), "")


class PandocResolutionTests(unittest.TestCase):
    """Pandoc is usually installed and usually not on PATH.

    Conversion is optional, so a pandoc the harness cannot find does not fail a run —
    it leaves an old .docx beside a new .md, which is worse than missing because
    nothing announces it."""

    def test_an_explicit_setting_wins_and_is_not_second_guessed(self):
        with mock.patch.dict(os.environ, {"PAPER_PANDOC_BIN": "/nowhere/pandoc"}):
            self.assertEqual(config._find_pandoc(), "/nowhere/pandoc")

    def test_path_is_used_when_pandoc_is_on_it(self):
        with mock.patch.dict(os.environ, {"PAPER_PANDOC_BIN": ""}), \
             mock.patch("shutil.which", return_value="/usr/bin/pandoc"):
            self.assertEqual(config._find_pandoc(), "/usr/bin/pandoc")

    def test_a_known_location_is_found_when_path_has_nothing(self):
        """The conda case: condabin/ is on PATH and bin/ is not."""
        with mock.patch.dict(os.environ, {"PAPER_PANDOC_BIN": ""}, clear=False), \
             mock.patch("shutil.which", return_value=None), \
             mock.patch.object(config, "_PANDOC_CANDIDATES", ("/opt/conda/bin/pandoc",)), \
             mock.patch("os.path.isfile", lambda p: p == "/opt/conda/bin/pandoc"), \
             mock.patch("os.access", lambda p, m: p == "/opt/conda/bin/pandoc"):
            self.assertEqual(config._find_pandoc(), "/opt/conda/bin/pandoc")

    def test_the_bare_name_is_the_last_resort_not_the_default(self):
        """It still fails, but it fails loudly instead of skipping conversion."""
        with mock.patch.dict(os.environ, {"PAPER_PANDOC_BIN": "",
                                          "CONDA_PREFIX": "", "CONDA_EXE": ""}), \
             mock.patch("shutil.which", return_value=None), \
             mock.patch.object(config, "_PANDOC_CANDIDATES", ()):
            self.assertEqual(config._find_pandoc(), "pandoc")


class ResourcePathTests(unittest.TestCase):
    """Where pandoc looks for a figure, and why the document's own directory is not
    enough.

    A split part inherits the whole document's figure paths verbatim, and those were
    written relative to the paper. Get this wrong and pandoc warns on stderr, exits 0,
    and writes a .docx with every figure missing — indistinguishable downstream from a
    section that never had one."""

    def test_the_documents_own_directory_comes_first(self):
        path = building._resource_path(Path("/paper/parts/manuscript/05-results.md"),
                                       (Path("/paper"),))
        self.assertEqual(path.split(os.pathsep)[0], "/paper/parts/manuscript")

    def test_the_roots_the_caller_named_follow_it(self):
        path = building._resource_path(Path("/paper/parts/manuscript/05-results.md"),
                                       (Path("/paper"), Path("/repo")))
        self.assertEqual(path.split(os.pathsep), ["/paper/parts/manuscript",
                                                  "/paper", "/repo"])

    def test_a_root_that_is_already_the_documents_own_directory_is_not_repeated(self):
        """The manuscript sits AT the paper root, so the caller's root and the
        document's directory are the same path. Twice on the resource path is not
        wrong, only noise, and noise in a command line is how a real difference
        stops being visible."""
        path = building._resource_path(Path("/paper/manuscript.md"), (Path("/paper"),))
        self.assertEqual(path, "/paper")

    def test_naming_no_roots_is_the_old_behaviour(self):
        self.assertEqual(building._resource_path(Path("/paper/manuscript.md"), ()),
                         "/paper")


class LostFigureTests(unittest.TestCase):
    """Pandoc reports a figure it could not find as a warning and exits 0.

    So a document converts successfully, is written, is a plausible size, and is
    missing its evidence. The check counts what is in the built file rather than
    believing what the tool said about it."""

    def _docx(self, media, extra=("word/document.xml",)):
        """A .docx carrying `media` images. Enough of one for a count."""
        path = Path(tempfile.mkdtemp()) / "built.docx"
        with zipfile.ZipFile(path, "w") as archive:
            for name in extra:
                archive.writestr(name, "<x/>")
            for i in range(media):
                archive.writestr(f"word/media/image{i}.png", b"x")
        return path

    def _md(self, text):
        path = Path(tempfile.mkdtemp()) / "doc.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_every_figure_arriving_is_no_loss(self):
        source = self._md("![](a.png)\n\n![](b.png)\n")
        self.assertEqual(building.figures_lost(source, self._docx(2)), 0)

    def test_a_figure_that_did_not_arrive_is_counted(self):
        """The real failure: twenty referenced, none embedded, exit status 0."""
        source = self._md("\n".join(f"![](../results/f{i}.png)" for i in range(20)))
        self.assertEqual(building.figures_lost(source, self._docx(0)), 20)

    def test_the_same_file_twice_is_one_figure(self):
        """Pandoc embeds one copy, so counting references would read as a loss."""
        source = self._md("![](a.png)\n\n![](a.png)\n")
        self.assertEqual(building.figures_lost(source, self._docx(1)), 0)

    def test_a_remote_image_is_not_the_resource_paths_problem(self):
        source = self._md("![](https://example.org/a.png)\n\n![](b.png)\n")
        self.assertEqual(building._image_targets(source.read_text()), ["b.png"])

    def test_a_template_carrying_a_logo_cannot_cover_for_a_lost_figure(self):
        """Three logos in the reference doc would otherwise hide three lost
        figures, and the document would look complete at exactly the wrong count."""
        source = self._md("\n".join(f"![](f{i}.png)" for i in range(3)))
        template = self._docx(3)
        self.assertEqual(building.figures_lost(source, self._docx(3),
                                               reference_docx=template), 3)

    def test_a_document_with_no_figures_has_nothing_to_check(self):
        self.assertIsNone(building.figures_lost(self._md("# Methods\n"),
                                                self._docx(0)))

    def test_a_format_that_cannot_be_opened_is_not_guessed_at(self):
        source = self._md("![](a.png)\n")
        self.assertIsNone(building.figures_lost(source, Path("/tmp/out.pdf")))

    def test_an_image_target_in_angle_brackets_is_read(self):
        self.assertEqual(building._image_targets("![](<a file.png>)"), ["a file.png"])

    def test_pandoc_attributes_are_not_part_of_the_target(self):
        self.assertEqual(building._image_targets("![](a.png){width=6in}"), ["a.png"])


class FigureLayoutTests(unittest.TestCase):
    """The two ways a figure that is present still ruins the page.

    Both were learned from a real manuscript whose panels stopped lining up with the
    labels above them, and neither is visible in the Markdown."""

    WIDE = 6.0                                  # the JMIR template's printable width

    def test_a_figure_with_no_width_is_imported_at_full_page_width(self):
        problems = figures.check("![](a.png)", "x.md", self.WIDE)
        self.assertEqual(len(problems), 1)
        self.assertIn("no width=", problems[0])

    def test_a_captioned_figure_with_no_width_is_caught_too(self):
        """A caption changes nothing: an unsized image is a full-page import either
        way, so the pattern must not require the alt text to be empty."""
        self.assertEqual(len(figures.check("![Figure 1](a.png)", "x.md", self.WIDE)), 1)

    def test_a_single_figure_at_the_printable_width_fits(self):
        self.assertEqual(figures.check("![](a.png){width=6in}", "x.md", self.WIDE), [])

    def test_a_single_figure_wider_than_the_page_does_not(self):
        problems = figures.check("![](a.png){width=6.5in}", "x.md", self.WIDE)
        self.assertEqual(len(problems), 1)
        self.assertIn("6.50in wide but only 6.00in fits", problems[0])

    def test_two_panels_on_one_line_pay_for_the_cell_padding(self):
        """5.68in of budget, not 6.00: Word spends 0.08in a side on cell margins,
        and a row that overflows is shrunk rather than refused — which is how the
        panels stop lining up with the labels above them."""
        self.assertEqual(figures.check("![](a.png){width=2.8in} ![](b.png){width=2.8in}",
                                       "x.md", self.WIDE), [])
        problems = figures.check("![](a.png){width=3.2in} ![](b.png){width=3.2in}",
                                 "x.md", self.WIDE)
        self.assertEqual(len(problems), 1)
        self.assertIn("2 panel(s)", problems[0])

    def test_an_unsized_panel_is_reported_once_and_the_row_sum_is_not_guessed(self):
        """The sum of the panels that DO declare a width is not the row's width, so
        reporting it as one would be a second, invented finding."""
        problems = figures.check("![](a.png){width=2.8in} ![](b.png)", "x.md", self.WIDE)
        self.assertEqual(len(problems), 1)
        self.assertIn("no width=", problems[0])

    def test_a_line_on_its_own_is_a_row_and_two_lines_are_not(self):
        """The two-column table puts side-by-side panels on one line. Stacked figures
        are separate rows and each gets the full width."""
        self.assertEqual(figures.check("![](a.png){width=5in}\n![](b.png){width=5in}",
                                       "x.md", self.WIDE), [])

    def test_prose_with_no_figures_is_not_a_finding(self):
        self.assertEqual(figures.check("Below the threshold of 10.", "x.md", self.WIDE),
                         [])

    def test_the_line_number_is_the_line_a_person_has_to_open(self):
        problems = figures.check("a\n\nb\n![](x.png)", "doc.md", self.WIDE)
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("doc.md:4:"))


class TextWidthTests(unittest.TestCase):
    """The page the figures have to fit on, measured from the venue's own template."""

    def test_no_template_is_us_letter_at_inch_and_a_quarter_margins(self):
        self.assertEqual(building.text_width_in(None), 6.0)

    def test_a_template_that_is_not_a_docx_falls_back_rather_than_raising(self):
        """Declining to check is worse than checking against a conventional page."""
        junk = Path(tempfile.mkdtemp()) / "not.docx"
        junk.write_bytes(b"this is not a zip")
        self.assertEqual(building.text_width_in(junk), 6.0)

    def test_the_page_is_measured_in_twips_and_returned_in_inches(self):
        """12240 twips wide, 1800 a side: 8.5in less 2.5in of margin."""
        path = Path(tempfile.mkdtemp()) / "ref.docx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml",
                             '<w:body><w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
                             '<w:pgMar w:top="1440" w:right="1800" w:bottom="1440" '
                             'w:left="1800"/></w:sectPr></w:body>')
        self.assertEqual(building.text_width_in(path), 6.0)


class BuildResourceDirTests(unittest.TestCase):
    """The knob that exists because the `..` is doing the work.

    A manuscript's `![](../results/roc.png)` needs a directory whose SIBLING is the
    results folder. Naming the results folder itself does not help, which is why this
    is a setting and not a search."""

    def test_nothing_configured_is_an_empty_tuple_not_a_path_to_nowhere(self):
        with mock.patch.dict(os.environ, {"PAPER_BUILD_RESOURCE_DIRS": ""}):
            self.assertEqual(
                tuple(Path(d).expanduser() for d in "".split(os.pathsep) if d.strip()),
                ())
        self.assertEqual(config.BUILD_RESOURCE_DIRS, ())

    def test_the_configured_directories_land_after_the_documents_own(self):
        path = building._resource_path(Path("/paper/manuscript.md"),
                                       (Path("/journey/paper1"),))
        self.assertEqual(path.split(os.pathsep), ["/paper", "/journey/paper1"])


class PandocTableTests(unittest.TestCase):
    """A table is not prose whichever of the three ways it is written. Pipe-ruled is
    what this project's builder emits; dash-ruled and raw HTML are what
    `pandoc -f docx` emits, and `-f docx` is how a reviewer's revision comes back."""

    def test_a_dash_ruled_simple_table_is_not_prose(self):
        text = ("The cohort is described below. Nothing was refit.\n\n"
                "  Group      Patients   Rate\n"
                "  --------- ---------- ------\n"
                "  Positive        7455  17.5%\n"
                "  Negative       35124  82.5%\n\n"
                "The split is the frozen one. Both halves inherit the frame.\n")
        self.assertEqual(len(prose.paragraphs(text)), 2)
        self.assertNotIn("Positive", prose.strip_structure(text))

    def test_a_raw_html_table_is_not_prose(self):
        """Pandoc falls back to literal `<table>` for a merged cell. One unblanked
        block measured as a single 293-word paragraph and carried a correct section
        over every length rule in this project."""
        text = ("The characteristics follow. They are unremarkable.\n\n"
                "<table>\n<thead>\n<tr>\n<th>Group</th>\n<th>N</th>\n</tr>\n"
                "</thead>\n<tbody>\n<tr>\n<td>Positive</td>\n<td>7455</td>\n"
                "</tr>\n</tbody>\n</table>\n\n"
                "Discrimination was modest. Calibration was adequate.\n")
        self.assertEqual(len(prose.paragraphs(text)), 2)
        self.assertNotIn("Positive", prose.strip_structure(text))

    def test_a_thematic_break_is_not_a_table_ruler(self):
        """A ruler is two or more runs of hyphens. One run is a horizontal rule, and
        blanking the paragraphs around it would delete prose."""
        text = "The claim holds.\n\n---\n\nAnd the next one follows from it."
        self.assertIn("claim holds", prose.strip_structure(text))
        self.assertIn("next one follows", prose.strip_structure(text))

    def test_an_unemphasised_caption_is_still_a_caption(self):
        """Word holds a caption's styling outside its text, so pandoc writes
        `Table 1. ...` with no emphasis. Requiring emphasis measured seven captions
        in a returned manuscript as one-sentence paragraphs."""
        self.assertTrue(paragraphs._is_caption(
            "Table 1. Selected cohort characteristics by TRD proxy status."))
        self.assertTrue(paragraphs._is_caption("Figure 2. Discrimination by encoder."))

    def test_a_cross_reference_in_prose_is_not_a_caption(self):
        """The stop after the number is what separates them; both read "Table 2" on
        the page."""
        self.assertFalse(paragraphs._is_caption(
            "Table 2 gives every selected characteristic and its standardized "
            "difference."))


class SectionPrefixMatchTests(unittest.TestCase):
    """An exemption keyed on equality exempts nothing, because a heading carries what
    the venue calls the section rather than what the list calls it."""

    def test_a_numbered_appendix_heading_matches_its_tag(self):
        self.assertTrue(prose.section_matches("Multimedia Appendix 1",
                                              ("multimedia appendix",)))

    def test_an_unrelated_heading_does_not(self):
        self.assertFalse(prose.section_matches("Methods", ("multimedia appendix",)))

    def test_venue_named_back_matter_is_exempt_from_paragraph_shape(self):
        """A manuscript that writes its back matter the way the venue asks carries
        nine short headings. Without the exemption every one of them draws findings
        from gates that have no business reading them."""
        for heading in ("Conflicts of Interest", "Data Availability",
                        "Authors' Contributions", "Multimedia Appendix 1"):
            self.assertEqual(paragraphs.check("None declared.", heading).checked, 0,
                             heading)


class ParagraphWordCeilingTests(unittest.TestCase):
    """A paragraph's sentence count and its word count are different failures. Nine
    short sentences is two claims; so is one 155-word block of five long ones, and
    the sentence ceiling has never fired on either manuscript measured here."""

    SHORT = ("The embedding did not beat the feature vector. "
             "Embedded logistic regression reached 0.657 and XGBoost reached 0.649. "
             "The paired interval crosses zero.")

    def _paragraph(self, words):
        """One paragraph of about `words` words, in five sentences — inside the
        sentence-count band, so the only rule left is the word ceiling."""
        each = words // 5
        return " ".join(["Word " + " ".join(["word"] * (each - 1)) + "."] * 5)

    def test_a_paragraph_inside_the_ceiling_passes(self):
        report = paragraphs.check(self._paragraph(config.PARAGRAPH_MAX_WORDS - 10),
                                  "Results")
        self.assertEqual([d.kind for d in report.defects], [])

    def test_a_paragraph_over_the_ceiling_is_reported_but_not_counted(self):
        """It is a length rule wearing a shape rule's clothes.

        Komorowski's published Nature Medicine methods supplement runs 10% of its
        paragraphs past this ceiling, with a maximum of 204 words. Counting those
        toward the shape share spends two thirds of the allowance before a real
        defect is found, so the defect is reported and the share ignores it."""
        report = paragraphs.check(self._paragraph(config.PARAGRAPH_MAX_WORDS + 20),
                                  "Results")
        self.assertIn(paragraphs.LONG_IN_WORDS, {d.kind for d in report.defects})
        self.assertIn("grew rather than one that welded",
                      report.defects[0].detail)
        self.assertEqual(0.0, report.share)

    def test_the_ceiling_is_120_words(self):
        """The lowest cap a published rewrite clears completely in both its
        documents: its longest paragraphs are 113 and 111 words. The draft it
        replaced runs 15 of 87 manuscript paragraphs over it, topping out at 155."""
        self.assertEqual(config.PARAGRAPH_MAX_WORDS, 120)

    def test_the_short_paragraph_the_ceiling_must_not_touch(self):
        self.assertTrue(paragraphs.check(self.SHORT, "Results").passed)


class ParagraphShareDenominatorTests(unittest.TestCase):
    """A share needs a denominator. "1 of 1 paragraphs are mis-shaped (100%)" on a
    twenty-word back-matter section is a blocking finding about nothing, and every
    defect kind added to this gate makes the arithmetic worse."""

    ONE_BAD = "However, the estimate moved. It moved by 0.004."

    def test_one_paragraph_does_not_block_a_section(self):
        report = paragraphs.check(self.ONE_BAD, "Validity checks")
        self.assertTrue(report.passed)
        self.assertTrue(report.defects)      # still reported, just not a verdict

    def test_the_same_defect_blocks_once_there_is_a_denominator(self):
        good = ("The split is the frozen one. Nothing was refit to produce it.\n\n"
                "Discrimination was modest. It held across encoders.\n\n"
                "Calibration was adequate. The intercept was near zero.\n\n"
                "Retrieval lost to the fitted model. The gap was 0.02.\n\n")
        report = paragraphs.check(good + self.ONE_BAD, "Validity checks")
        self.assertFalse(report.passed)
        self.assertIn("5 paragraphs are mis-shaped", report.reasons[0])

    def test_the_floor_is_five_paragraphs(self):
        self.assertEqual(config.PARAGRAPH_DEFECT_MIN_PARAGRAPHS, 5)


class RoadmapOpenerTests(unittest.TestCase):
    """A section that opens by describing its own running order spends the first
    thing a reader reads on what the table of contents already told them. It is one
    paragraph of twenty-four in the section where it was found — invisible under any
    share ceiling, and the first thing on the page — so it is a section reason."""

    def test_a_section_opening_on_its_own_running_order_is_refused(self):
        text = ("The results are reported in the order of the two objectives. "
                "Participant flow and cohort composition come first, then "
                "discrimination.\n\n"
                "Of 501,718 patients, 42,579 met eligibility criteria. "
                "7,455 (17.5%) met the proxy definition.")
        report = paragraphs.check(text, "Results")
        self.assertFalse(report.passed)
        self.assertIn("opens on a roadmap", report.reasons[0])

    def test_a_section_describing_itself_is_refused(self):
        text = ("This section reports the within-subgroup prevalence of the "
                "outcome. The strata are the ones named in the Methods.")
        report = paragraphs.check(text, "S9 Subgroup outcome prevalence")
        self.assertFalse(report.passed)
        self.assertIn("opens on a roadmap", report.reasons[0])

    def test_here_we_report_is_an_introduction_s_purpose_statement(self):
        """The standard close of an Introduction, and not a roadmap. Refusing it
        would be the gate fighting the one place the construction belongs."""
        text = ("Here we report a comparison of two representations on one cohort. "
                "Neither was tuned after the split was frozen.")
        self.assertTrue(paragraphs.check(text, "Introduction").passed)

    def test_a_section_opening_on_a_measurement_passes(self):
        text = ("Of 501,718 patients in the extract, 42,579 met eligibility "
                "criteria and 7,455 (17.5%) met the TRD proxy definition. "
                "Median age was 55 years.")
        self.assertTrue(paragraphs.check(text, "Results").passed)

    def test_a_roadmap_phrase_further_down_is_not_this_defect(self):
        """Only the first paragraph is asked. A pointer in the middle of a Methods
        section is a signpost, which is a different rule and a milder one."""
        text = ("The cohort was assembled from records. Nothing was refit.\n\n"
                "The remainder of this section gives the encoder settings. "
                "They are unchanged from the protocol.")
        self.assertTrue(paragraphs.check(text, "Methods").passed)


class ResultsTopicSentenceTests(unittest.TestCase):
    """When a Results paragraph's claim IS a number, the claim and the number belong
    in the same sentence. It advises: a short report whose findings are qualitative
    scores badly here and is legitimate."""

    BARE = ("The embedding did not outperform the feature vector.\n"
            "Embedded logistic regression achieved 0.657 (0.643 to 0.672) and "
            "XGBoost led the feature-vector models at 0.649 (0.634 to 0.664).\n\n"
            "Retrieval lost to the fitted model.\n"
            "Nearest retrieval reached 0.612 against 0.649 for XGBoost, a gap of "
            "0.037 (0.021 to 0.052).\n\n"
            "Calibration was adequate on both arms.\n"
            "The Brier score was 0.131 on the embedded arm and 0.129 on the "
            "feature-vector arm, with intercepts of 0.02 and 0.01.")

    CARRIED = ("Embedded logistic regression had the highest ROC AUC, 0.657 "
               "(95% CI 0.643 to 0.672), followed by feature-vector XGBoost at "
               "0.649 (95% CI 0.634 to 0.664). Their paired difference was 0.008 "
               "(95% CI -0.003 to 0.019).\n\n"
               "Nearest retrieval reached 0.612, below the 0.649 of the fitted "
               "model. The gap was 0.037 (0.021 to 0.052).\n\n"
               "Brier scores were 0.131 and 0.129 across the two arms. Calibration "
               "intercepts were 0.02 and 0.01.")

    def test_a_bare_claim_opener_is_reported(self):
        report = paragraphs.check(self.BARE, "Results")
        self.assertTrue(report.advisories)
        self.assertIn("carrying a reported figure", report.advisories[0])

    def test_it_advises_and_does_not_block(self):
        self.assertTrue(paragraphs.check(self.BARE, "Results").passed)

    def test_an_opener_that_carries_its_figure_passes(self):
        report = paragraphs.check(self.CARRIED, "Results")
        self.assertEqual(report.advisories, [])
        self.assertGreaterEqual(report.results_topic_share,
                                config.RESULTS_TOPIC_FIGURE_SHARE_MIN)

    def test_the_floor_is_half(self):
        """Not 0.8. A published supplement's own S-sections run 0 to 50% on the same
        measure, which is why the rule is scoped to the manuscript's Results heading
        and nowhere else."""
        self.assertEqual(config.RESULTS_TOPIC_FIGURE_SHARE_MIN, 0.50)

    def test_a_section_that_is_not_reporting_figures_is_skipped(self):
        """A Results section that names its predictors rather than measuring them
        reports in words and is correct."""
        text = ("The model leaned on psychiatric history. Suicidality, insomnia and "
                "substance use carried most of the weight.\n\n"
                "Medication burden mattered less. Prior exposure mattered least.\n\n"
                "Sociodemographic fields contributed little. None of them was "
                "dropped.")
        report = paragraphs.check(text, "Results")
        self.assertIsNone(report.results_topic_share)
        self.assertEqual(report.advisories, [])

    def test_a_supplement_section_called_results_is_not_swept_in(self):
        report = paragraphs.check(self.BARE, "Results", manuscript=False)
        self.assertEqual(report.advisories, [])


class MidBandSentenceTests(unittest.TestCase):
    """The middle of the length distribution, where a heavy text and a readable one
    actually separate. Above 35 words two manuscripts of one paper are
    indistinguishable; between 25 and 35 they run three to one."""

    def _document(self, long_share):
        """A hundred sentences, `long_share` of them past the mid threshold."""
        long_one = "Word " + " ".join(["word"] * 28) + "."
        short_one = "The model did better on the held-out split."
        n_long = int(round(100 * long_share))
        body = " ".join([long_one] * n_long + [short_one] * (100 - n_long))
        return [("Results", sentences.score(body))]

    def test_a_document_inside_the_ceiling_passes(self):
        self.assertTrue(sentences.mid_tail(self._document(0.06)).passed)

    def test_a_document_over_the_ceiling_is_refused(self):
        report = sentences.mid_tail(self._document(0.19))
        self.assertFalse(report.passed)
        self.assertIn("past 25 words", report.reasons[0])

    def test_the_thresholds_are_25_words_and_15_percent(self):
        """25 is where plain-language and medical-writing guidance converge, and it
        is the 35-word rule one band down. 15% clears a published manuscript by a
        factor of two and a half (5.6% and 6.6%) and refuses both documents of the
        draft it replaced (18.9% and 17.4%)."""
        self.assertEqual(config.SENTENCE_MID_WORDS, 25)
        self.assertEqual(config.SENTENCE_MID_SHARE_MAX, 0.15)

    def test_an_exempt_section_contributes_nothing(self):
        reports = [("Abstract", sentences.score("x " * 60, section_name="Abstract"))]
        self.assertEqual(sentences.mid_tail(reports).sentences, 0)

    def test_the_worst_section_rides_along_without_being_the_failure(self):
        light = ("Results", sentences.score(
            " ".join(["The model did better."] * 40)))
        heavy = ("Methods", sentences.score(
            " ".join(["Word " + " ".join(["word"] * 28) + "."] * 6)))
        report = sentences.mid_tail([light, heavy])
        self.assertEqual(report.worst_section, "Methods")
        self.assertTrue(report.passed)


class SelfGradingTests(unittest.TestCase):
    """The paper handing down the verdict a reviewer is there to reach. The sibling
    of the anticipatory rebuttal: one argues the case for the defence, the other
    writes the judgment."""

    def test_a_design_graded_by_its_own_paper_is_refused(self):
        report = sentences.score(
            "The temporal design is a real strength. Every model was fit on "
            "records that predate the index prescription.")
        self.assertFalse(report.passed)
        self.assertTrue(any("grade the paper's own work" in r
                            for r in report.reasons), report.reasons)

    def test_telling_the_reader_which_comparison_to_believe_is_refused(self):
        report = sentences.score(
            "Both scored the same held-out patients, so the paired comparison is "
            "the one that counts. The interval crosses zero.")
        self.assertFalse(report.passed)

    def test_telling_the_reader_to_be_reassured_is_refused(self):
        report = sentences.score(
            "Retrieval beat chance on every encoder. That is reassuring for face "
            "validity and nothing more.")
        self.assertFalse(report.passed)

    def test_reporting_the_same_design_passes(self):
        """The rule is the verdict, not the interpretation. A Discussion saying what
        a result means is doing its job."""
        report = sentences.score(
            "Every model was fit on records that predate the index prescription, so "
            "no feature in either representation can encode the outcome it is asked "
            "to predict. Nearest retrieval discriminated above chance on all four "
            "encoders, and lost to the fitted model on every one of them. The "
            "finding bounds one comparison on one cohort and no more than that.")
        self.assertTrue(report.passed, report.reasons)


class EquivalenceComparativeTests(unittest.TestCase):
    """Equivalence smuggled in as a comparative. The precondition, the disavowal
    escape and the severity are the ones already here; the list had a hole."""

    METHODS = ("No equivalence or noninferiority margin was prespecified. "
               "The comparison is descriptive.")

    def test_neither_is_better_than_the_other_is_an_equivalence_claim(self):
        text = (self.METHODS + " Neither representation is better than the other. "
                "The interval runs from -0.003 to 0.019.")
        hits = sentences.equivalence_overclaim(text)
        self.assertTrue(hits)
        self.assertIn("neither representation is better than", hits[0][1])

    def test_matched_but_did_not_exceed_is_an_equivalence_claim(self):
        text = (self.METHODS + " Embedding matched, but did not exceed, a feature "
                "vector built from the same fields.")
        self.assertTrue(sentences.equivalence_overclaim(text))

    def test_a_paper_refusing_the_word_is_not_refused(self):
        """"These quantities are distinguished because they are not
        interchangeable" is a published manuscript saying the careful thing."""
        text = (self.METHODS + " These quantities are distinguished because they "
                "are not interchangeable.")
        self.assertEqual(sentences.equivalence_overclaim(text), [])

    def test_a_plain_negative_result_is_not_an_equivalence_claim(self):
        text = (self.METHODS + " The embedding did not outperform the feature "
                "vector. The paired difference was 0.008.")
        self.assertEqual(sentences.equivalence_overclaim(text), [])

    def test_without_the_disclaimer_the_check_stays_silent(self):
        self.assertEqual(sentences.equivalence_overclaim(
            "Neither representation is better than the other."), [])


class AbsoluteSectionCeilingTests(unittest.TestCase):
    """A budget is whatever the planner wrote, so a plan that budgets 2,700 words for
    Results passes at 2,767 and the gate has checked the planner against themselves."""

    def test_a_section_over_the_absolute_ceiling_is_refused_with_no_budget(self):
        report = length.check(config.SECTION_MAX_WORDS + 1, section_name="Results")
        self.assertFalse(report.passed)
        self.assertIn("absolute ceiling", report.reason)

    def test_a_generous_budget_does_not_license_it(self):
        report = length.check(2_767, budget=2_700, section_name="Results")
        self.assertFalse(report.passed)
        self.assertIn("absolute ceiling", report.reason)

    def test_the_repair_is_relocation_and_not_compression(self):
        report = length.check(2_767, section_name="Results")
        self.assertIn("Do not compress", report.reason)
        self.assertIn("supplement", report.reason)

    def test_the_ceiling_is_1800_words_at_top_level_scope(self):
        """`stages.sweep.sections` splits on H1 and an outline section IS an H1, so
        this is a whole Methods. A published manuscript's Methods measures 1,133
        words at that scope; the draft it replaced runs 2,047, 2,496 and 2,767."""
        self.assertEqual(config.SECTION_MAX_WORDS, 1800)
        self.assertTrue(length.check(1_133, section_name="Methods").passed)


class SectionFloorTests(unittest.TestCase):
    """The floor does not merely report a short section: `stages.drafting` re-prompts
    the model for continuation prose until the draft clears it, so a wrong floor is
    an instruction to pad."""

    def test_the_floor_is_fifty_words(self):
        """150 refused eight sections of a published manuscript, including a 55-word
        Conclusions that is the right length at 55 words."""
        self.assertEqual(config.SECTION_MIN_WORDS, 50)
        self.assertTrue(length.check(55, section_name="Conclusions").passed)

    def test_a_declaration_has_no_floor(self):
        for heading in ("Conflicts of Interest", "Data Availability",
                        "Funding", "Protocol and Registration", "Acknowledgments"):
            self.assertEqual(length.floor_for(heading), 0, heading)
            self.assertTrue(length.check(2, section_name=heading).passed, heading)

    def test_a_section_that_argues_keeps_its_floor(self):
        self.assertEqual(length.floor_for("Results"), config.SECTION_MIN_WORDS)
        self.assertFalse(length.check(10, section_name="Results").passed)

    def test_an_explicit_absolute_still_wins(self):
        self.assertEqual(length.floor_for("Results", absolute=0), 0)


class ReadingEaseTests(unittest.TestCase):
    """Reading ease is computed, reported and never gated. It is dominated by
    syllables per word, and in a clinical paper that is subject matter."""

    DENSE = ("Multimodal representational heterogeneity necessitates methodological "
             "standardization. Operationalization of comorbidity classification "
             "presupposes nosological consistency. Discriminative performance "
             "differentials remain inconclusive.")

    def test_a_low_reading_ease_is_reported_and_not_refused(self):
        report = readability.score(self.DENSE, section_name="Discussion")
        self.assertLess(report.flesch_ease, 20.0)
        self.assertFalse(any("reading ease" in r for r in report.reasons),
                         report.reasons)

    def test_there_is_no_reading_ease_floor_to_re_tighten(self):
        self.assertFalse(hasattr(config, "READABILITY_FLESCH_EASE_MIN"))

    def test_the_fk_ceiling_survives_at_eighteen(self):
        """It catches what the sentence gate does not: long words in long sentences
        at once. A published manuscript peaks at 17.2 in its Discussion."""
        self.assertEqual(config.READABILITY_FK_GRADE_MAX, 18.0)


class VenueHeadingTests(unittest.TestCase):
    """A bold lead-in inside a Declarations block is not a section a copyeditor, a
    submission portal, or a reader scanning for the data-availability statement can
    find."""

    def _declarations_style(self):
        text = VenueGateTests.GOOD
        for heading in ("Ethical Considerations", "Acknowledgments", "Funding",
                        "Conflicts of Interest", "Data Availability",
                        "Authors' Contributions"):
            text = text.replace(f"# {heading}\n", f"**{heading}.**\n")
        return text

    def test_a_bold_lead_in_does_not_satisfy_a_required_section(self):
        report = venue.check(self._declarations_style(), "JMIR")
        self.assertFalse(report.passed)
        self.assertTrue(any("`Data Availability` heading" in e
                            for e in report.errors), report.errors)

    def test_an_unbolded_keywords_line_still_counts(self):
        """The bold markup is this project's builder's, not the venue's. Matching on
        it turned seven present keywords into zero on a manuscript written in Word."""
        text = VenueGateTests.GOOD.replace(
            "**Keywords.** one; two; three; four; five; six",
            "Keywords: one, two, three, four, five, six")
        report = venue.check(text, "JMIR")
        self.assertEqual(report.stats["keywords"], 6)
        self.assertTrue(report.passed, report.errors)

    def test_an_unsourced_requirement_warns_rather_than_blocks(self):
        text = VenueGateTests.GOOD.replace("# Protocol and Registration\n", "")
        report = venue.check(text, "JMIR")
        self.assertTrue(report.passed, report.errors)
        self.assertTrue(any("Protocol and Registration" in w
                            for w in report.warnings))


class AbstractShapeTests(unittest.TestCase):
    """Every prose gate exempts the abstract, so nothing measured the one section a
    reader meets detached from the paper."""

    def _with_abstract(self, methods, results):
        return VenueGateTests.GOOD.replace(
            "**Methods.** " + "Word word word word. " * 8, "**Methods.** " + methods
        ).replace(
            "**Results.** " + "Word word word word. " * 9, "**Results.** " + results)

    def test_a_long_abstract_sentence_is_reported_and_does_not_refuse(self):
        """Measured on two abstracts of one paper, so it says so and stands aside.

        Chekroud 2016 in Lancet Psychiatry opens its Methods label with a 51-word
        sentence. A ceiling that refuses that is a ceiling calibrated on n=2."""
        long_one = " ".join(["word"] * 38) + "."
        report = venue.check(self._with_abstract(long_one, "Short result here."),
                             "JMIR")
        self.assertTrue(any("abstract sentence" in w for w in report.warnings),
                        report.warnings)
        self.assertFalse(any("abstract sentence" in e for e in report.errors),
                         report.errors)

    def test_the_abstract_sentence_ceiling_is_35_words(self):
        """A published rewrite's longest abstract sentence is 32 words; the draft it
        replaced runs to 38, with three more between 34 and 37."""
        self.assertEqual(config.ABSTRACT_SENTENCE_MAX_WORDS, 35)
        report = venue.check(
            self._with_abstract("Word " + " ".join(["word"] * 31) + ".",
                                "Short result here now."), "JMIR")
        self.assertFalse(any("abstract sentence" in e for e in report.errors),
                         report.errors)

    def test_methods_outrunning_results_warns(self):
        report = venue.check(
            self._with_abstract("Word word word word. " * 9,
                                "Word word word word. " * 4), "JMIR")
        self.assertTrue(any("on Methods against" in w for w in report.warnings),
                        report.warnings)
        self.assertTrue(report.passed, report.errors)

    def test_a_results_heavy_abstract_passes(self):
        report = venue.check(
            self._with_abstract("Word word word word. " * 5,
                                "Word word word word. " * 9), "JMIR")
        self.assertEqual(report.warnings, [])
        self.assertLess(report.stats["abstract_methods_results_ratio"],
                        config.ABSTRACT_METHODS_RESULTS_RATIO_MAX)

    def test_the_ratio_ceiling_is_1_point_2(self):
        self.assertEqual(config.ABSTRACT_METHODS_RESULTS_RATIO_MAX, 1.2)


class PandocCrossrefTests(unittest.TestCase):
    """A reviewer's revision arrives as `pandoc -f docx` output, so the shapes it
    writes are the normal case rather than an edge one."""

    SUP = ("# M1 Source Data and Sampling\n\nThe extract is one health system.\n\n"
           "# S1 Neighbor Prediction\n\nRetrieval lost to the fitted model.\n\n"
           "Table S1. Expanded cohort characteristics.\n\n"
           "Figure S1. Discrimination by encoder.\n")

    def test_a_bare_pandoc_caption_defines_a_table(self):
        report = crossrefs.check("See Table S1 for the rest.", self.SUP)
        self.assertEqual(report.defined.get("Table S"), [1])
        self.assertTrue(report.passed, report.reasons)

    def test_a_venue_style_section_heading_defines_a_section(self):
        report = crossrefs.check("The sampling frame is Supplement M1.", self.SUP)
        self.assertEqual(report.defined.get("Supplement M"), [1])
        self.assertTrue(report.passed, report.reasons)

    def test_a_multimedia_appendix_pointer_resolves(self):
        report = crossrefs.check(
            "Expanded characteristics are in Multimedia Appendix 1, section S1.",
            self.SUP)
        self.assertEqual(report.referenced.get("Supplement S"), [1])
        self.assertTrue(report.passed, report.reasons)

    def test_a_multimedia_appendix_table_pointer_reaches_the_table_resolver(self):
        report = crossrefs.check(
            "The rest appear in Multimedia Appendix 1, Table S1.", self.SUP)
        self.assertEqual(report.referenced.get("Table S"), [1])
        self.assertTrue(report.passed, report.reasons)

    def test_a_packet_that_points_at_an_empty_index_is_reported(self):
        """The worse failure: `passed=True` with `defined={}` on a returned
        manuscript, which is a gate reporting green after checking nothing."""
        report = crossrefs.check(
            "The rest are in Multimedia Appendix 1, Table S15 and Table S16.",
            "# S1 Something\n\nNo captions at all here.\n", whole_packet=True)
        self.assertFalse(report.passed)
        self.assertTrue(any("resolve against nothing" in r for r in report.reasons),
                        report.reasons)

    def test_a_section_drafted_in_isolation_is_still_not_this_gate_s_business(self):
        self.assertTrue(crossrefs.check("See Figure 4 for the curve.", "").passed)


# A manuscript drawn from the published rewrite this project's newest rules were
# measured against: its own headings, its own back-matter shape, its own paragraphs,
# verbatim. Every sentence here was written by somebody else and accepted.
#
# It is the sharpest test available and it is free. A rule that refuses this text is
# a wrong rule, whatever it is defensible as in the abstract, and the two failure
# modes these checks exist to avoid — encoding one author's tics, and shipping a gate
# the reference text cannot pass — are both caught here rather than in production.
REFERENCE_MANUSCRIPT = """# Abstract

**Background:** Electronic health records (EHRs) have been shown to support
prediction of subsequent antidepressant switching, an imperfect proxy for
treatment-resistant depression (TRD).

**Objective:** We compared structured feature vectors with pretrained embeddings of
rule-based patient narratives for predicting a treatment-switching proxy for TRD at
the index antidepressant prescription.

**Methods:** This retrospective study included 42,579 patients with depression from
one community health system. The outcome required at least 3 distinct antidepressant
treatments, including the index agent, within 365 days.

**Results:** The outcome occurred in 7,455 patients (17.5%). Embedded logistic
regression had the highest ROC AUC, 0.657 (95% CI 0.643 to 0.672), followed by
feature-vector XGBoost at 0.649 (95% CI 0.634 to 0.664). Their paired difference was
0.008 (95% CI -0.003 to 0.019). Nearest-neighbor retrieval did not improve on the
trained classifiers.

**Conclusions:** Narrative embeddings did not demonstrate superior discrimination
over the strongest structured feature model for this treatment-switching proxy.

Keywords: treatment-resistant depression, electronic health records, prediction,
embeddings, machine learning, retrieval, proxy outcomes

# Introduction

Electronic health records (EHRs) offer longitudinal information on diagnoses,
prescribing, and health care use. They rarely establish why a medication was changed
or whether an adequate trial failed. Consequently, EHR studies often define TRD
through treatment sequences. These definitions identify observable care trajectories,
and changes in the rules alter both outcome frequency and cohort composition. A model
predicting repeated switching therefore requires a more limited interpretation than
one predicting symptom-confirmed treatment resistance.

General-purpose text encoders provide one way to represent an EHR without training a
large clinical foundation model. Structured fields can be converted into a patient
narrative and then encoded as a numerical embedding for prediction. The practical
question is whether this additional processing improves on a transparent feature
vector. A narrative created from the same structured records adds no new measurement,
although the encoding may organize existing information differently.

# Methods

We conducted a retrospective cohort study using a frozen, deidentified Epic EHR
extract from one community health system. The extract contained 501,718 patients and
included diagnoses, encounters, medications, procedures, and laboratory data. Patients
with a problem-list depression flag were retained, together with a random sample
without that flag. The resulting sample was enriched for depression and does not
represent health-system prevalence.

Eligible patients met the study's coded depression definition, had no bipolar or
schizophrenia-spectrum diagnosis, and had an antidepressant index prescription on or
after a documented depression diagnosis. The depression code set included major
depressive disorder (MDD), dysthymia, and unspecified depression. The final cohort
included 42,579 patients, and the eligibility cascade appears in Multimedia Appendix
1, section M2.

## Ethical Considerations

The study used a deidentified secondary extract and was reviewed under an approved
protocol. No patient contact occurred and no identifiers were retained.

# Results

Of 501,718 patients in the extract, 42,579 met eligibility criteria and 7,455 (17.5%)
met the TRD proxy definition. Median age was 55 years (IQR 38 to 70), 72.5% were
female, and 80.0% were recorded as White. Outcome-positive patients more often had
coded suicidality, severe depression, anxiety, insomnia, and substance use disorders.

Training and test characteristics were closely balanced, at a maximum absolute
standardized mean difference of 0.036. Weak negative correlations linked the outcome
to history length, encounter count, and time from diagnosis to the index
prescription. These descriptive checks do not exclude effects of observation or care
access.

Embedded logistic regression had the highest ROC AUC, 0.657 (95% CI 0.643 to 0.672),
followed by feature-vector XGBoost at 0.649 (95% CI 0.634 to 0.664). Their paired
difference was 0.008 (95% CI -0.003 to 0.019). This post hoc comparison did not
demonstrate superior discrimination for embeddings.

Nearest-neighbor retrieval reached a ROC AUC of 0.612 across the four encoders,
below every trained classifier. Weighting neighbors by distance did not close the
gap. Retrieval therefore carries signal without competing with a fitted model.

# Discussion

We asked whether pretrained narrative embeddings improve prediction of a
treatment-switching proxy for TRD beyond structured feature vectors. In this cohort,
they did not demonstrate superior discrimination over the strongest feature-vector
model. The leading models achieved ROC AUCs of 0.657 and 0.649, with a paired
difference of 0.008 (95% CI -0.003 to 0.019). This finding supports structured
features as a practical benchmark, and it does not establish equivalence or isolate
the effect of encoding identical information.

The choice of classifier changed the result. Embeddings improved logistic regression
but reduced discrimination for each tree ensemble, and logistic regression led the
embedded models across all encoders. This pattern is consistent with regularized
linear models accommodating distributed embedding information under the tested
settings. Differences in dimensionality, regularization, and tuning may also
contribute.

## Limitations

The main limitation is the target. A treatment-switching proxy identifies an
observable care trajectory rather than a symptom-confirmed failure of adequate
trials. Patients switch for tolerability, cost, and access, and none of those is
treatment resistance. The cohort is one community health system, so transportability
is unestablished.

## Conclusions

Narrative embeddings did not improve discrimination over structured features for
this proxy. Progress toward clinical use requires better validation of the outcome.

# Acknowledgments

None.

# Funding

No external funding supported this work.

# Conflicts of Interest

None declared.

# Data Availability

The extract cannot be shared under the data use agreement.

# Authors' Contributions

MF designed the study and ran the analysis.

# Protocol and Registration

The study was not registered.

# Abbreviations

EHR: electronic health record. TRD: treatment-resistant depression.

# Multimedia Appendix 1

Supplementary methods and results.

# References

1. Someone. A paper. Journal. 2024.
"""


class ReferenceManuscriptTests(unittest.TestCase):
    """The acceptance test: the checks added for compression, register and venue fit,
    run over a manuscript somebody else wrote and a journal accepted.

    Scoped to those checks on purpose. The reference text does carry two defects
    against rules that predate this work — one stacked hedge and one empty opener in
    thirteen thousand words — and those are real, they are not grounds to relax a
    zero-tolerance rule, and they are not what this test is about."""

    def _sections(self):
        out, name, body = [], "", []
        for line in REFERENCE_MANUSCRIPT.splitlines():
            if line.startswith("# "):
                if name:
                    out.append((name, "\n".join(body)))
                name, body = line[2:].strip(), []
            else:
                body.append(line)
        out.append((name, "\n".join(body)))
        return [(h, b) for h, b in out if prose.sentences(b)]

    def test_no_paragraph_is_over_the_word_ceiling(self):
        for heading, body in self._sections():
            for defect in paragraphs.check(body, heading).defects:
                self.assertNotEqual(defect.kind, "too long",
                                    f"{heading}: {defect.detail}")

    def test_no_section_opens_on_a_roadmap(self):
        for heading, body in self._sections():
            for reason in paragraphs.check(body, heading).reasons:
                self.assertNotIn("roadmap", reason, heading)

    def test_the_results_openers_carry_their_figures(self):
        body = dict(self._sections())["Results"]
        report = paragraphs.check(body, "Results")
        self.assertEqual(report.advisories, [], report.advisories)
        self.assertGreaterEqual(report.results_topic_share,
                                config.RESULTS_TOPIC_FIGURE_SHARE_MIN)

    def test_no_section_blocks_on_paragraph_shape(self):
        for heading, body in self._sections():
            report = paragraphs.check(body, heading)
            self.assertTrue(report.passed, f"{heading}: {report.reasons}")

    def test_the_document_clears_the_mid_band(self):
        measured = [(h, sentences.score(b, section_name=h))
                    for h, b in self._sections()]
        report = sentences.mid_tail(measured)
        self.assertTrue(report.passed, report.reasons)
        self.assertLess(report.share, config.SENTENCE_MID_SHARE_MAX)

    def test_no_sentence_grades_the_paper(self):
        for heading, body in self._sections():
            self.assertEqual(sentences.score(body, section_name=heading).self_grading,
                             [], heading)

    def test_no_section_breaks_the_absolute_word_ceiling_or_the_floor(self):
        for heading, body in self._sections():
            words = prose.word_count(prose.strip_structure(body))
            report = length.check(words, section_name=heading)
            self.assertTrue(report.passed, f"{heading} ({words} words): "
                                           f"{report.reason}")

    def test_no_section_breaks_the_readability_band(self):
        for heading, body in self._sections():
            report = readability.score(body, section_name=heading)
            self.assertTrue(report.passed, f"{heading}: {report.reasons}")

    def test_the_paper_claims_no_equivalence_it_did_not_test(self):
        self.assertEqual(sentences.equivalence_overclaim(REFERENCE_MANUSCRIPT), [])

    def test_the_venue_gate_finds_only_what_is_really_wrong(self):
        """Every required section is a heading in the venue's own wording, the
        keyword line is unbolded and still counts, and the abstract's shape holds."""
        report = venue.check(REFERENCE_MANUSCRIPT, "JMIR")
        self.assertTrue(report.passed, report.errors)
        self.assertEqual(report.stats["keywords"], 7)
        self.assertLess(report.stats["abstract_methods_results_ratio"],
                        config.ABSTRACT_METHODS_RESULTS_RATIO_MAX)

    def test_its_appendix_pointers_resolve(self):
        supplement = ("# M1 Source Data and Sampling\n\nOne health system.\n\n"
                      "# M2 Eligibility and Temporal Design\n\nThe cascade.\n")
        report = crossrefs.check(REFERENCE_MANUSCRIPT, supplement,
                                 whole_packet=True)
        self.assertTrue(report.passed, report.reasons)
        self.assertEqual(report.referenced.get("Supplement M"), [2])


class ConfigBandTests(unittest.TestCase):
    """The thresholds are the contract. A change to one of these is a change to what
    the harness will publish, so it should break a test and be argued about."""

    def test_the_sentence_band_is_academic(self):
        self.assertGreater(config.SENTENCE_MEAN_WORDS_MAX,
                           config.SENTENCE_MEAN_WORDS_MIN)
        self.assertLessEqual(config.SENTENCE_MEAN_WORDS_MAX, 24)

    def test_the_hard_ceiling_is_above_the_long_threshold(self):
        self.assertGreater(config.SENTENCE_HARD_MAX_WORDS, config.SENTENCE_LONG_WORDS)

    def test_the_paragraph_band_admits_a_real_paragraph(self):
        self.assertLessEqual(config.PARAGRAPH_MIN_SENTENCES, 3)
        self.assertGreaterEqual(config.PARAGRAPH_MAX_SENTENCES, 7)


if __name__ == "__main__":
    unittest.main()
