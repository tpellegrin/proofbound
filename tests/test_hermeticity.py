"""Whether the evidence a treatment withholds is reachable anyway.

An arm whose prepared workspace deliberately contained no implementation source ran one ordinary
search of the host, found a copy left by a materialisation from a previous day, and read all four of
the module's files. The workspace was exactly as designed and the treatment had already failed.

So the experiment now has two conditions, and this file tests the second one: before execution, no
unintended alternative copy of the controlled evidence — nor of the oracle, the reference solution,
prior samples or earlier results — is reachable under the roots the scan actually looks at.

**This is experimental hermeticity, not system security.** Nothing here claims process isolation, a
kernel boundary, or resistance to an agent that is trying to escape. It claims that ordinary
engineering tools do not find a second copy of what is being controlled, and it reports which roots
it looked at so that absence is never claimed over a machine.

Nothing here invokes a model.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _hermetic     # noqa: E402
import _lineage      # noqa: E402
import _mlr          # noqa: E402

MODULE = _mlr.FIXTURE / "runtime" / "objectstore"


def controlled():
    return _hermetic.Sensitive(
        _hermetic.CONTROLLED_EVIDENCE,
        stems=[p.name for p in sorted(MODULE.glob("*.py"))],
        digests=[_mlr.digest_file(p) for p in sorted(MODULE.glob("*.py"))],
        marks=_lineage.source_fingerprint(MODULE))


class Sandbox:
    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-hermetic-test-"))
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


class ScanTest(unittest.TestCase):
    maxDiff = None

    def scan(self, root, sensitive=None, **kw):
        return _hermetic.scan([root], [sensitive or controlled()], **kw)

    def test_an_empty_environment_is_clean(self):
        with Sandbox() as box:
            report = self.scan(box.tmp)
            self.assertEqual(report["status"], _hermetic.CLEAN)
            self.assertEqual(report["findings"], [])

    def test_a_copy_of_the_controlled_source_is_found(self):
        """The failure that invalidated a field qualification, as a deterministic case."""
        with Sandbox() as box:
            stale = box.tmp / "leftover" / "workspace" / "third_party" / "objectstore"
            stale.mkdir(parents=True)
            shutil.copy(MODULE / "_store.py", stale / "_store.py")
            report = self.scan(box.tmp)
            self.assertEqual(report["status"], _hermetic.CONTAMINATED)
            self.assertEqual(len(report["findings"]), 1)
            self.assertIn("byte-identical", report["findings"][0]["basis"])

    def test_a_modified_copy_is_still_found_by_its_fingerprint(self):
        """A leak does not have to be byte-perfect to be a leak."""
        with Sandbox() as box:
            text = (MODULE / "_store.py").read_text(encoding="utf-8")
            (box.tmp / "_store.py").write_text("# a comment someone added\n" + text,
                                               encoding="utf-8")
            report = self.scan(box.tmp)
            self.assertEqual(report["status"], _hermetic.CONTAMINATED)
            self.assertIn("distinctive lines", report["findings"][0]["basis"])

    def test_a_similarly_named_but_unrelated_file_is_not_a_finding(self):
        """§83 E. Identity confirms; a name only decides where to look."""
        with Sandbox() as box:
            (box.tmp / "_store.py").write_text("def unrelated():\n    return 'nothing to do with it'\n",
                                               encoding="utf-8")
            report = self.scan(box.tmp)
            self.assertEqual(report["status"], _hermetic.CLEAN)

    def test_a_symlinked_file_is_followed_to_what_it_points_at(self):
        """§41. Not a defence against symlinks, just not blind to the obvious alternate path."""
        with Sandbox() as box:
            link = box.tmp / "_store.py"
            os.symlink(MODULE / "_store.py", link)
            report = self.scan(box.tmp)
            self.assertEqual(report["status"], _hermetic.CONTAMINATED)

    def test_a_hidden_oracle_is_found(self):
        with Sandbox() as box:
            hidden = _mlr.FIXTURE / "hidden" / "external_test_v2.py"
            shutil.copy(hidden, box.tmp / hidden.name)
            oracle = _hermetic.Sensitive(_hermetic.ORACLE, stems=[hidden.name],
                                         digests=[_mlr.digest_file(hidden)])
            report = _hermetic.scan([box.tmp], [oracle])
            self.assertEqual(report["status"], _hermetic.CONTAMINATED)
            self.assertEqual(report["findings"][0]["category"], _hermetic.ORACLE)

    def test_prior_sample_evidence_is_found_by_the_marker_it_carries(self):
        """A session database has no fixed bytes; it has the experiment's name inside it."""
        with Sandbox() as box:
            (box.tmp / "worker.db").write_bytes(b"SQLite format 3\x00 ... MLR-external ... ")
            prior = _hermetic.Sensitive(_hermetic.PRIOR_SAMPLE, stems=["worker.db"],
                                        contains=[b"MLR-external"])
            report = _hermetic.scan([box.tmp], [prior])
            self.assertEqual(report["status"], _hermetic.CONTAMINATED)
            self.assertEqual(report["findings"][0]["category"], _hermetic.PRIOR_SAMPLE)

    def test_an_unreadable_path_is_unknown_and_never_clean(self):
        """§40. A scan that cannot see is not a scan that saw nothing."""
        with Sandbox() as box:
            shut = box.tmp / "closed"
            shut.mkdir()
            (shut / "_store.py").write_text("x", encoding="utf-8")
            shut.chmod(0o000)
            try:
                report = self.scan(box.tmp)
                self.assertNotEqual(report["status"], _hermetic.CLEAN)
                self.assertEqual(report["status"], _hermetic.UNKNOWN)
                self.assertTrue(report["unreadable"])
            finally:
                shut.chmod(0o700)

    def test_a_declared_exposure_is_reported_and_not_a_finding(self):
        """Declaring is not removing. It is recorded so nobody mistakes silence for control."""
        with Sandbox() as box:
            known = box.tmp / "known"
            known.mkdir()
            shutil.copy(MODULE / "_store.py", known / "_store.py")
            report = self.scan(box.tmp, declared=[str(known)])
            self.assertEqual(report["status"], _hermetic.CLEAN)
            self.assertEqual(len(report["declared_exposures"]), 1)

    def test_the_report_says_what_it_looked_at(self):
        """§39. Absence over the scanned roots, and over nothing else."""
        with Sandbox() as box:
            report = self.scan(box.tmp)
            self.assertIn(str(box.tmp.resolve()), report["scanned_roots"])
            self.assertIn("scanned roots", report["claim"])


class RuleIdentityTest(unittest.TestCase):
    """A series must be able to prove which hermeticity rule it ran under. §48."""

    maxDiff = None

    def test_the_identity_is_stable_for_the_same_rule(self):
        self.assertEqual(_mlr.preflight_identity(), _mlr.preflight_identity())

    def test_widening_the_declared_list_changes_the_rule(self):
        with Sandbox() as box:
            self.assertNotEqual(_mlr.preflight_identity(),
                                _mlr.preflight_identity(declared=[box.tmp]))

    def test_adding_a_root_changes_the_rule(self):
        with Sandbox() as box:
            self.assertNotEqual(_mlr.preflight_identity(),
                                _mlr.preflight_identity(evidence_roots=[box.tmp]))


class MaterialisationLifecycleTest(unittest.TestCase):
    """Cleanup lives with creation, and the recogniser knows every shape that leaked. §13, §35."""

    maxDiff = None

    def test_a_materialisation_is_removed_when_its_block_ends(self):
        seen = {}
        with _mlr.materialised(_mlr.FULL) as built:
            seen["workspace"] = Path(built["workspace"])
            self.assertTrue(seen["workspace"].is_dir())
        self.assertFalse(seen["workspace"].exists())

    def test_it_is_removed_even_when_the_block_raises(self):
        seen = {}
        with self.assertRaises(RuntimeError):
            with _mlr.materialised(_mlr.CONTRACT) as built:
                seen["workspace"] = Path(built["workspace"])
                raise RuntimeError("something went wrong mid-run")
        self.assertFalse(seen["workspace"].exists())

    def test_every_shape_that_leaked_is_recognised(self):
        """The twelve that were found were named `arm`, `full`, `contract`, `c`, `f` and `again`."""
        with Sandbox() as box:
            for name in ("arm", "full", "contract", "c", "f", "again"):
                holder = box.tmp / f"tmp-{name}"
                (holder / name / "workspace").mkdir(parents=True)
                (holder / name / "runtime" / "objectstore").mkdir(parents=True)
            found = _mlr.ephemeral_materialisations([box.tmp])
            self.assertEqual(len(found), 6)

    def test_a_materialisation_at_the_top_level_is_recognised(self):
        with Sandbox() as box:
            holder = box.tmp / "plain"
            (holder / "workspace").mkdir(parents=True)
            (holder / "runtime" / "objectstore").mkdir(parents=True)
            self.assertEqual(len(_mlr.ephemeral_materialisations([box.tmp])), 1)

    def test_retained_evidence_is_never_recognised_as_ephemeral(self):
        """§36. One of these can be deleted freely and the other cannot."""
        with Sandbox() as box:
            evidence = box.tmp / "full-1789010508504"
            evidence.mkdir()
            (evidence / "worker.db").write_bytes(b"SQLite format 3\x00")
            (evidence / "grade-gate").mkdir()
            self.assertEqual(_mlr.ephemeral_materialisations([box.tmp]), ())

    def test_an_unreadable_directory_is_left_alone(self):
        with Sandbox() as box:
            shut = box.tmp / "closed"
            shut.mkdir()
            shut.chmod(0o000)
            try:
                self.assertEqual(_mlr.ephemeral_materialisations([box.tmp]), ())
            finally:
                shut.chmod(0o700)


class GenericityTest(unittest.TestCase):
    """§37. The checker must not know what it is checking for."""

    maxDiff = None

    def test_the_checker_names_no_fixture(self):
        text = (ROOT / "evals" / "_hermetic.py").read_text(encoding="utf-8")
        for word in ("objectstore", "_store", "third_party", "DeepSeek", "MLR", "external_test"):
            with self.subTest(word=word):
                self.assertNotIn(word, text)

    def test_the_fixture_supplies_what_must_be_absent(self):
        config = _mlr.hermeticity()
        categories = {kind.category for kind in config["sensitive"]}
        self.assertEqual(categories, set(_hermetic.CATEGORIES))
        for kind in config["sensitive"]:
            with self.subTest(category=kind.category):
                self.assertTrue(kind.stems or kind.path_markers)


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
