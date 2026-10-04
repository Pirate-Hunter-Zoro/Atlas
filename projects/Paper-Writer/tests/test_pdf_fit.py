"""A PDF's tables, code blocks and paths stay inside the page.

`stages/pdf_fit.lua` is passed to pandoc for a PDF and never for a .docx. These
run the filter through pandoc's LaTeX writer, which is what the PDF is typeset
from, and read the LaTeX: a TeX run would make the suite need TeX Live.
"""

import shutil
import subprocess
import unittest

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


def latex(markdown):
    out = subprocess.run(
        ["pandoc", "--from", "markdown", "--to", "latex", "--standalone",
         "--lua-filter", str(building.PDF_FIT)],
        input=markdown, capture_output=True, text=True, check=True)
    return out.stdout


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
