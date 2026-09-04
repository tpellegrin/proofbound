"""The architecture corpus must stay internally consistent as it is split and moved.

Proofbound's architecture is deliberately several documents so a bounded task can read only
what applies to it. That is only safe if references resolve and every canonical identifier
has exactly one home — a principle dropped or duplicated during a file move is a real
architectural regression, and reviewing prose does not reliably catch it.

This is a documentation test. It asserts nothing about runtime behavior.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_docs_refs.py"
CORPUS = ROOT / "docs" / "architecture" / "proofbound"


class ArchitectureCorpusTest(unittest.TestCase):
    maxDiff = None

    def test_reference_checker_reports_a_consistent_corpus(self):
        cp = subprocess.run([sys.executable, str(CHECKER)], text=True,
                            capture_output=True, check=False)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_the_entry_point_exists_and_routes(self):
        readme = CORPUS / "README.md"
        self.assertTrue(readme.is_file(), "the architecture corpus needs an entry point")
        text = readme.read_text(encoding="utf-8")
        for doc in ("core-model.md", "execution-and-review.md", "artifacts-and-provenance.md",
                    "long-running-autonomy.md", "context-economy.md"):
            self.assertIn(doc, text, f"entry point does not route to {doc}")

    def test_every_corpus_document_is_reachable_from_the_entry_point(self):
        """An orphaned normative document is one nobody will find, so nobody will obey."""
        readme = CORPUS / "README.md"
        text = readme.read_text(encoding="utf-8")
        for doc in sorted(CORPUS.rglob("*.md")):
            if doc == readme:
                continue
            rel = doc.relative_to(CORPUS).as_posix()
            self.assertIn(rel, text, f"{rel} is not linked from the entry point")

    def test_the_entry_point_stays_thin(self):
        """It routes; it does not summarize. A fat index becomes a second authority."""
        size = len((CORPUS / "README.md").read_bytes())
        self.assertLess(size, 16_000, "entry point is growing into a duplicate of the corpus")

    def test_no_normative_document_grows_past_the_ingestion_budget(self):
        """The split exists to bound what one bounded task must read.

        Historical evidence under evidence/ is exempt: it is read on demand, never as a
        precondition for doing work.
        """
        for doc in sorted(CORPUS.glob("*.md")):
            with self.subTest(doc=doc.name):
                self.assertLess(len(doc.read_bytes()), 40_000,
                                f"{doc.name} is too large to be read selectively; split it")

    def test_the_superseded_rfc_path_is_a_redirect_not_a_second_authority(self):
        old = ROOT / "docs" / "architecture" / "specification-reflection-harness.md"
        if not old.exists():
            self.skipTest("redirect stub removed")
        self.assertLess(len(old.read_bytes()), 1_000, "redirect stub is accumulating content")
        self.assertIn("proofbound/README.md", old.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
