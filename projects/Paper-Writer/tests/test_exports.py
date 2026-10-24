"""A manuscript builds on a tree with no `results/`, from the cluster's exports.

The Mac holds `exports/results/...`, copied there by the relay at the path the
figure has under `results/` on the cluster. A manuscript names `../results/...`
on both machines, and the builder reads the export where `results/` lacks it.
"""

import os
import shutil
import struct
import tempfile
import unittest
import zlib
import zipfile
from pathlib import Path

import support                                                      # noqa: F401
from paperwriter import config                                      # noqa: E402
from paperwriter.stages import building                             # noqa: E402


def png(path):
    """A real 8x8 PNG, enough for pandoc to embed."""
    def chunk(kind, data):
        body = kind + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xffffffff))
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * 8 for _ in range(8))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw))
                     + chunk(b"IEND", b""))


MANUSCRIPT = ("# Results\n\n"
              "![The sweep.](../results/knn/sweep.png){width=3in}\n\n"
              "![Beside it.](figs/local.png){width=3in}\n")


class ExportedFigureTests(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.ws, True)
        self.paper = self.ws / "paper1"
        self.paper.mkdir()
        self.source = self.paper / "manuscript.md"
        self.source.write_text(MANUSCRIPT, encoding="utf-8")
        png(self.paper / "figs" / "local.png")

    def dirs(self):
        return [str(self.paper), str(self.ws)]

    def test_a_missing_results_figure_is_read_from_exports(self):
        png(self.ws / "exports" / "results" / "knn" / "sweep.png")
        found = building.exported_figures(MANUSCRIPT, self.dirs())
        self.assertEqual(found, {"../results/knn/sweep.png": str(
            self.ws / "exports" / "results" / "knn" / "sweep.png")})

    def test_a_figure_results_holds_is_left_alone(self):
        png(self.ws / "results" / "knn" / "sweep.png")
        png(self.ws / "exports" / "results" / "knn" / "sweep.png")
        self.assertEqual(building.exported_figures(MANUSCRIPT, self.dirs()), {})

    def test_nothing_exported_is_nothing_put_in(self):
        self.assertEqual(building.exported_figures(MANUSCRIPT, self.dirs()), {})
        argv, text = building._pandoc_input(self.source, os.pathsep.join(self.dirs()))
        self.assertEqual((argv, text), ([str(self.source)], None))

    def test_the_source_is_never_rewritten(self):
        png(self.ws / "exports" / "results" / "knn" / "sweep.png")
        argv, text = building._pandoc_input(self.source, os.pathsep.join(self.dirs()))
        self.assertEqual(argv, [])
        self.assertIn(str(self.ws / "exports" / "results" / "knn" / "sweep.png"), text)
        self.assertIn("{width=3in}", text)
        self.assertIn("](figs/local.png)", text)
        self.assertEqual(self.source.read_text(encoding="utf-8"), MANUSCRIPT)

    @unittest.skipUnless(config.PANDOC_BIN and shutil.which(config.PANDOC_BIN)
                         or os.path.isfile(config.PANDOC_BIN or ""),
                         "no pandoc on this machine")
    def test_a_manuscript_compiles_on_a_tree_with_no_results(self):
        png(self.ws / "exports" / "results" / "knn" / "sweep.png")
        self.assertFalse((self.ws / "results").exists())
        built = building.convert_one(self.source, "docx",
                                     resource_roots=(self.ws,))
        self.assertIsNotNone(built)
        self.assertEqual(building.figures_lost(self.source, built), 0)
        with zipfile.ZipFile(built) as archive:
            media = [n for n in archive.namelist() if n.startswith("word/media/")]
        self.assertEqual(len(media), 2)

    @unittest.skipUnless(config.PANDOC_BIN and shutil.which(config.PANDOC_BIN)
                         or os.path.isfile(config.PANDOC_BIN or ""),
                         "no pandoc on this machine")
    def test_and_with_neither_the_figure_is_lost_and_counted(self):
        built = building.convert_one(self.source, "docx",
                                     resource_roots=(self.ws,))
        self.assertEqual(building.figures_lost(self.source, built), 1)


if __name__ == "__main__":
    unittest.main()
