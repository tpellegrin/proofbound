"""The architecture corpus must stay internally consistent as it is split and moved.

Proofbound's architecture is deliberately several documents so a bounded task can read only
what applies to it. That is only safe if references resolve and every canonical identifier
has exactly one home — a principle dropped or duplicated during a file move is a real
architectural regression, and reviewing prose does not reliably catch it.

This is a documentation test. It asserts nothing about runtime behavior.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
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
        """An orphaned document is one nobody will find, so nobody will obey it.

        Reachability, not membership of the entry point's own text. The earlier rule required every
        corpus path to appear *directly* in the router, which kept documents findable and also made
        the router grow by one row per historical file forever — so recording a new run meant first
        compressing the router's prose. A route through the evidence index is a real route.
        """
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_docs_refs

        reachable, routes = check_docs_refs.reachable_from_entry_point()
        for doc in sorted(CORPUS.rglob("*.md")):
            with self.subTest(doc=doc.relative_to(CORPUS).as_posix()):
                self.assertIn(doc.resolve(), reachable)
        # The property is worth nothing if everything happens to be one hop away: assert that the
        # two-hop route this restructure introduced is genuinely exercised.
        index = (CORPUS / "evidence" / "README.md").resolve()
        via_index = [d for d, route in routes.items() if len(route) > 2 and index in route]
        self.assertTrue(via_index, "no document is reached through the evidence index")

    def test_reachability_fails_for_an_orphan_and_terminates_on_cycles(self):
        """The check must actually discriminate, and must not hang on a cross-linked corpus.

        Built as a disposable corpus rather than by mutating the real one: a test that edits the
        documents it checks can leave the repository broken when it fails.
        """
        sys.path.insert(0, str(ROOT / "scripts"))
        import check_docs_refs

        with tempfile.TemporaryDirectory() as raw:
            corpus = Path(raw) / "proofbound"
            (corpus / "evidence").mkdir(parents=True)
            # a -> b -> a is a cycle; the index is two hops; the orphan is linked by nobody.
            (corpus / "README.md").write_text("# Entry\n[a](a.md)\n[index](evidence/README.md)\n")
            (corpus / "a.md").write_text("# A\n[back](README.md)\n[b](b.md)\n")
            (corpus / "b.md").write_text("# B\n[a](a.md)\n")
            (corpus / "evidence" / "README.md").write_text("# Index\n[old](old.md)\n")
            (corpus / "evidence" / "old.md").write_text("# Old\n")
            (corpus / "orphan.md").write_text("# Orphan\n")

            original = check_docs_refs.CORPUS
            check_docs_refs.CORPUS = corpus
            try:
                failures: list[str] = []
                checked = check_docs_refs.check_reachability(failures)
            finally:
                check_docs_refs.CORPUS = original

        self.assertEqual(checked, 6)
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("orphan.md", failures[0])

    def test_the_routing_table_states_measured_costs(self):
        """A stale reading budget is worse than none, because it is quoted in decisions.

        The figures drifted to roughly half the truth — route A displayed ~28 KB against 46,937
        actual bytes — because they were maintained by hand. They are derived now.
        """
        cp = subprocess.run([sys.executable, str(ROOT / "scripts" / "docs_route_cost.py"), "--check"],
                            text=True, capture_output=True, check=False)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_a_new_evidence_document_needs_no_change_to_the_router(self):
        """The property this restructure exists to provide, asserted directly.

        Adding history used to cost a row in a byte-capped router, which is why the previous
        milestone spent its last hour compressing prose to fit one link.
        """
        index = CORPUS / "evidence" / "README.md"
        self.assertTrue(index.is_file(), "the evidence index is the router's single history link")
        entry = (CORPUS / "README.md").read_text(encoding="utf-8")
        listed = {m for m in re.findall(r"evidence/([a-z0-9-]+\.md)", entry)}
        on_disk = {d.name for d in (CORPUS / "evidence").glob("*.md")} - {"README.md"}
        # Routes F and G name two documents directly and that is fine; the rest must not be needed.
        self.assertLessEqual(len(listed - {"README.md"}), 2,
                             f"the router names {len(listed)} evidence documents; it should name the index")
        self.assertGreater(len(on_disk - listed), 5,
                           "most evidence must be reached through the index, or nothing was gained")

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
