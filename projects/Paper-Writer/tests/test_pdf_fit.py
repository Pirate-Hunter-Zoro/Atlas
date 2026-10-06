"""A PDF's tables, figures, code blocks and paths stay inside the page.

`stages/pdf_fit.lua` is passed to pandoc for a PDF and never for a .docx. These
run the filter through pandoc's LaTeX writer, which is what the PDF is typeset
from, and read the LaTeX. One also builds a PDF, and skips that half where
xelatex is not installed, so the suite does not need TeX Live.
"""

import re
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

import support                                                      # noqa: F401
from paperwriter.stages import building                             # noqa: E402

WIDE = """\
  Parent cluster (n)               Splits into (n / n)                                     Driving token   Token present, sub 1 / sub 2   Split silhouette (top level = 0.48)
  -------------------------------- ------------------------------------------------------- --------------- ------------------------------ -------------------------------------
  A: no "episode" token (14,438)   recurrent + severity (11,425) / unspecified (3,013)      recurrent       0.98 / 0.00                    0.69
"""

NARROW = """\
  a   b
  --- ---
  1   2
"""

NARRATIVE = """\
Before.

    SOCIAL_ANXIETY: Absent | OCD: Absent | ANXIETY: Present | ADJUSTMENT_DISORDER: Absent | PTSD: Absent

After.
"""


# A pipe table with a line longer than pandoc's 72 columns takes its widths
# from the dashes, and these give "Representation" a tenth of the line.
GIVEN = """\
| **Representation** | **Classifier** | **ROC AUC (95% CI)** | **AUPRC (95% CI)** | **Brier score (95% CI)** |
| ---------- | ------------------- | ---------------------- | ---------------------- | ---------------------- |
| EMBEDDED | Logistic regression | 0.657 (0.643--0.672) | 0.302 (0.281--0.325) | 0.137 (0.132--0.142) |
"""

# The same kind of table with dashes that already hold every word.
GIVEN_ROOMY = """\
| **Group** | **Value** |
| ---------------------------------------- | ---------------------------------------- |
| A label that is long enough to pass the seventy-two column mark | 1 |
"""

CELLS = """\
  **Source field**     **Encoding**                     **Narrative**
  -------------------- -------------------------------- -----------------------------------------
  Benzodiazepine days  pre_anchor_history_days, float   BMI: N \\\\\\| BP (mean): S/D, or Missing
  Race                 White/Caucasian, N/A             Psych inpatient days: N \\| ED psych visits: N
"""

PANELS = """\
Text before.

A bge-small-en-v1.5

![](a.png){width=4.5in}

B bge-en-icl

![](b.png){width=4.5in}

***Figure 5.** Retrieval by neighborhood size.*

After.
"""

CAPTIONED_TABLE = """\
***Table 2.** Discrimination in the test patients.*

""" + GIVEN


def latex(markdown, cwd=None, resource=None):
    command = ["pandoc", "--from", "markdown", "--to", "latex", "--standalone",
               "--lua-filter", str(building.PDF_FIT)]
    if resource:
        command += ["--resource-path", str(resource)]
    out = subprocess.run(command, input=markdown, capture_output=True,
                         text=True, check=True, cwd=cwd)
    return out.stdout


def png(path, width, height):
    """A blank grey PNG of `width` by `height` pixels, written with zlib alone."""
    def chunk(kind, data):
        body = kind + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))
    rows = b"".join(b"\x00" + b"\x80" * width for _ in range(height))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b""))


# A panel label, a tall image and its caption: the label and the image are
# boxed together and the image is narrowed to leave room for both texts.
TALL_PANEL = """\
Text before.

A bge-small-en-v1.5

![](figs/tall.png){width=5.6in}

Figure S11. Subgroup discrimination.

After.
"""


@unittest.skipUnless(shutil.which("pandoc"), "pandoc is not installed")
class PdfFit(unittest.TestCase):

    def test_pdf_only(self):
        self.assertIn(str(building.PDF_FIT), building._format_flags("pdf", None))
        self.assertNotIn(str(building.PDF_FIT),
                         " ".join(building._format_flags("docx", None)))

    def test_wide_table_gets_widths_and_a_smaller_face(self):
        tex = latex(WIDE)
        self.assertIn(r"\begingroup\footnotesize", tex)
        self.assertIn(r"\linewidth", tex)      # p{...\linewidth} columns wrap
        self.assertNotIn("@{}llll", tex)

    def test_narrow_table_is_left_alone(self):
        tex = latex(NARROW)
        self.assertNotIn(r"\begingroup", tex)
        self.assertIn("@{}ll@{}", tex)

    def test_given_widths_too_narrow_for_a_word_are_recomputed(self):
        tex = latex(GIVEN)
        widths = [float(x) for x in
                  re.findall(r"\\real\{([\d.]+)\}", tex)]
        self.assertEqual(len(widths), 5)
        # The dashes gave Representation 0.105; a bold "Representation"
        # needs about a fifth of a footnotesize line.
        self.assertGreater(widths[0], 0.2)
        self.assertRegex(tex, r"\\begingroup\\(small|footnotesize)")

    def test_given_widths_that_hold_every_word_are_kept(self):
        tex = latex(GIVEN_ROOMY)
        self.assertNotIn(r"\begingroup", tex)
        self.assertIn(r"\real{0.5000}", tex)

    def test_identifiers_in_cells_break_after_underscores(self):
        tex = latex(CELLS)
        self.assertIn(r"pre\_\allowbreak{}anchor\_\allowbreak{}history", tex)

    def test_a_literal_backslash_and_pipe_in_a_cell_is_kept(self):
        # The source asked for a backslash and a pipe, and gets both.
        tex = latex(CELLS)
        self.assertRegex(tex, r"N \\textbackslash\{?\}?\s*\\textbar\{\} BP")
        self.assertRegex(tex, r"days: N\s+\\textbar\{\} ED")

    def test_slash_breaks_only_between_words(self):
        tex = latex(CELLS)
        self.assertIn(r"White/\allowbreak{}Caucasian", tex)
        self.assertIn("S/D", tex)
        self.assertIn("N/A", tex)
        self.assertNotIn(r"S/\allowbreak", tex)
        self.assertNotIn(r"N/\allowbreak", tex)

    def test_panel_label_is_boxed_with_its_image(self):
        tex = latex(PANELS)
        def boxed(label, image):
            return (r"\\begin\{minipage\}\{\\linewidth\}\s*" + label
                    + r"\s*(\\smallskip\s*)?[^\n]*includegraphics[^\n]*\{"
                    + image + r"\}[^\n]*\s*\\end\{minipage\}")
        self.assertRegex(tex, boxed("A bge-small-en-v1.5", r"a\.png"))
        self.assertRegex(tex, boxed("B bge-en-icl", r"b\.png"))
        # The caption after the last panel may not be broken from it.
        self.assertRegex(tex, r"\\end\{minipage\}\\par\s*\\nopagebreak\s*"
                              r"\\emph\{\\textbf\{Figure 5\.\}")
        self.assertNotIn("needspace", tex)

    def test_image_kept_with_text_leaves_room_for_it(self):
        # An image as tall as the page, held to its caption, has nowhere to
        # break, and TeX ships empty pages until it runs out of numbers. One
        # three times as tall as it is wide, 5.6in across, is 16.8in tall.
        with tempfile.TemporaryDirectory() as tmp:
            png(Path(tmp) / "a.png", 60, 180)
            tex = latex("![](a.png){width=5.6in}\n\n"
                        "Figure S11. Subgroup discrimination.\n", cwd=tmp)
        width = float(re.search(
            r"\\includegraphics\[width=([\d.]+)in[^\]]*\]\{a\.png\}", tex).group(1))
        # The page is 550pt (7.61in) tall; three widths must fit under it.
        self.assertLess(width * 3, 550 / 72.27)
        self.assertGreater(width * 3, 6.5)
        self.assertIn(r"\usepackage{graphicx}", tex)
        self.assertRegex(tex, r"a\.png\}\s*\\nopagebreak\s*Figure S11\.")

    def test_short_image_keeps_its_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            png(Path(tmp) / "a.png", 200, 100)
            tex = latex("![](a.png){width=5in}\n\n"
                        "Figure S11. Subgroup discrimination.\n", cwd=tmp)
        self.assertRegex(tex, r"\\includegraphics\[width=5in[^\]]*\]\{a\.png\}")

    def test_boxed_image_resolves_through_the_resource_path(self):
        # The figure is found only through --resource-path, from a directory
        # that is neither the document's nor the figure's. The Image must reach
        # pandoc's writer as an Image, which copies the file where TeX runs; a
        # raw \includegraphics names a path TeX cannot find.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            png(root / "paper" / "figs" / "tall.png", 60, 180)
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            tex = latex(TALL_PANEL, cwd=elsewhere, resource=root / "paper")
            self.assertRegex(
                tex, r"\\begin\{minipage\}\{\\linewidth\}\s*A bge-small-en-v1\.5\s*"
                     r"(\\smallskip\s*)?\\includegraphics\[width=[\d.]+in[^\]]*\]"
                     r"\{figs/tall\.png\}\s*\\end\{minipage\}")
            if not shutil.which("xelatex"):
                self.skipTest("xelatex is not installed")
            pdf = root / "out.pdf"
            run = subprocess.run(
                ["pandoc", "--from", "markdown", "--standalone",
                 "--lua-filter", str(building.PDF_FIT), "--pdf-engine", "xelatex",
                 "--resource-path", str(root / "paper"), "-o", str(pdf)],
                input=TALL_PANEL, capture_output=True, text=True, cwd=elsewhere,
                timeout=300)
            self.assertEqual(run.returncode, 0, run.stderr[-2000:])
            self.assertNotIn("Could not fetch", run.stderr)
            if shutil.which("pdfimages"):
                listed = subprocess.run(["pdfimages", "-list", str(pdf)],
                                        capture_output=True, text=True,
                                        check=True).stdout.splitlines()
                self.assertEqual(len(listed) - 2, 1, "\n".join(listed))

    def test_caption_after_an_image_is_not_boxed_with_the_next(self):
        tex = latex("![](a.png){width=4in}\n\n"
                    "Figure S3. Continued on the next page.\n\n"
                    "![](b.png){width=4in}\n")
        self.assertNotIn("minipage", tex)

    def test_table_caption_asks_for_room_for_the_table(self):
        tex = latex(CAPTIONED_TABLE)
        self.assertIn(r"\usepackage{needspace}", tex)
        self.assertRegex(tex, r"\\Needspace\{\d+\\baselineskip\}\s*"
                              r"\\emph\{\\textbf\{Table 2\.\}")

    def test_prose_is_not_boxed(self):
        tex = latex("A sentence that happens to start with a capital.\n\n"
                    "Another paragraph.\n")
        self.assertNotIn("minipage", tex)
        self.assertNotIn("nopagebreak", tex)

    def test_code_block_wraps_and_loads_fvextra(self):
        tex = latex(NARRATIVE)
        self.assertIn(r"\begin{Verbatim}[breaklines,breakanywhere]", tex)
        self.assertIn(r"\usepackage{fvextra}", tex)
        self.assertIn("ADJUSTMENT_DISORDER", tex)  # literal, not escaped

    def test_no_code_block_no_fvextra(self):
        # fvextra loads lineno, which breaks a longtable with tall rows.
        self.assertNotIn("fvextra", latex(WIDE))

    def test_long_paths_may_break(self):
        tex = latex("Built by `scripts/data_loading/feature_vector.py` and "
                    "scripts/pipeline/neighbors/narrative_audit.py.\n")
        self.assertIn(r"data\_\allowbreak{}loading/\allowbreak{}", tex)
        self.assertIn(r"pipeline/\allowbreak{}neighbors/\allowbreak{}", tex)
        # Prose does not break at a dot, so the full stop stays on its line.
        self.assertIn(r"narrative\_\allowbreak{}audit.py.", tex)


if __name__ == "__main__":
    unittest.main()
