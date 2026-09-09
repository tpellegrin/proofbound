"""Deterministic tests for the repaired calibration case.

The repair rests on one claim: every state can satisfy the same product contract, so no
deterministic test can separate the sound architectures from the degraded one, and what differs is
only which code had to learn how a provider reports its outcomes. These tests hold that claim up.

They also guard the property the previous case lost — that the probe must not reward the
degradation — and the property it never had: that the deterministic suite must not become an
architecture oracle.

Nothing here invokes a model.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _craft  # noqa: E402

CASE = ROOT / "evals" / "craft" / "notification-provider-boundary"
REFERENCE = CASE / "reference-beacon"
STATES = ("state-a", "state-b", "state-c")


def build(state: str, *, with_beacon: bool, into: Path) -> Path:
    """One state, optionally with the reference implementation of the future change applied."""
    project = into / "p"
    shutil.copytree(CASE / "states" / state, project,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if with_beacon:
        ref = REFERENCE / state
        for src in sorted(ref.rglob("*")):
            if src.is_file():
                dst = project / src.relative_to(ref)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    return project


def run_suite(project: Path, test_file: str) -> bool:
    target = project / test_file
    target.write_bytes((CASE / test_file).read_bytes())
    cp = subprocess.run([sys.executable, "-B", "-m", "unittest", test_file[:-3], "-q"],
                        cwd=project, capture_output=True, text=True, check=False)
    target.unlink()
    return cp.returncode == 0


class ProductContractTest(unittest.TestCase):
    """Every architecture must be able to satisfy the same product behaviour, before and after."""

    maxDiff = None

    def test_every_state_exhibits_the_accepted_behaviour_before_the_change(self):
        for state in STATES:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as td:
                project = build(state, with_beacon=False, into=Path(td))
                self.assertTrue(run_suite(project, "behaviour_test.py"))

    def test_no_state_already_satisfies_the_future_change(self):
        """Otherwise the probe measures nothing."""
        for state in STATES:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as td:
                project = build(state, with_beacon=False, into=Path(td))
                self.assertFalse(run_suite(project, "future_test.py"))

    def test_every_state_can_satisfy_the_future_change(self):
        """The degradation must be architectural, never functional."""
        for state in STATES:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as td:
                project = build(state, with_beacon=True, into=Path(td))
                self.assertTrue(run_suite(project, "future_test.py"),
                                f"{state} cannot satisfy the product contract")

    def test_the_change_does_not_disturb_the_original_provider(self):
        for state in STATES:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as td:
                project = build(state, with_beacon=True, into=Path(td))
                self.assertTrue(run_suite(project, "behaviour_test.py"))

    def test_the_deterministic_suite_is_not_an_architecture_oracle(self):
        """The decisive property: no deterministic result separates sound from degraded.

        If it could, correctness would answer the question and craft evaluation would be
        unnecessary — and any calibration built on it would be measuring its own test suite.
        """
        results = {}
        for state in STATES:
            with tempfile.TemporaryDirectory() as td:
                project = build(state, with_beacon=True, into=Path(td))
                results[state] = (run_suite(project, "behaviour_test.py"),
                                  run_suite(project, "future_test.py"))
        self.assertEqual(len(set(results.values())), 1,
                         f"deterministic outcomes differ by state: {results}")


class ProbeSemanticsTest(unittest.TestCase):
    """The probe must vary how a provider *reports* outcomes, not only what it is called."""

    maxDiff = None

    def setUp(self):
        self.contract = (CASE / "future-contract.md").read_text(encoding="utf-8")
        self.intent = (CASE / "intent.md").read_text(encoding="utf-8")
        self.future = (CASE / "future_test.py").read_text(encoding="utf-8")

    def test_the_contract_is_the_repaired_revision(self):
        self.assertIn("r0002", self.contract)

    def test_the_probe_varies_outcome_reporting_and_not_only_wire_format(self):
        flat = " ".join(self.contract.split())
        self.assertIn("reports what happened in the response body", flat)
        for token in ("accepted", "refused", "unavailable"):
            with self.subTest(token=token):
                self.assertIn(token, flat)

    def test_the_status_line_alone_cannot_decide_the_outcome(self):
        """Three different product outcomes must all be reachable behind one HTTP status."""
        body_cases = re.findall(r'\(200, \{"result": "(\w+)"', self.future)
        self.assertEqual({"accepted", "refused", "unavailable"}, set(body_cases))

    def test_the_intent_names_the_volatile_decision_without_placing_it(self):
        flat = " ".join(self.intent.split())
        self.assertIn("Providers differ in how they report the outcome of a delivery attempt",
                      flat)
        self.assertIn("outcome vocabulary above is the same for all of them", flat)

    def test_the_intent_prescribes_no_mechanism(self):
        """A criterion the intent supplies would leave no baseline to compare a treatment against."""
        low = self.intent.lower()
        for token in ("interface", "adapter", "protocol", "registry", "boundary", "module",
                      "package", "inject", "must live", "belongs in", "should live"):
            with self.subTest(token=token):
                self.assertNotIn(token, low)

    def test_the_product_vocabulary_is_unchanged_by_the_probe(self):
        """Integration substitution, not a product capability change."""
        flat = " ".join(self.contract.split())
        self.assertIn("the outcome vocabulary is identical for both providers", flat.lower())
        for token in ("sent", "rejected", "failed"):
            with self.subTest(token=token):
                self.assertIn(token, self.intent)

    def test_the_hidden_gate_asserts_behaviour_and_never_structure(self):
        """A gate that named files or patterns would decide the architecture for the evaluator."""
        low = self.future.lower()
        for token in ("delivery/", "sender", "adapter", "registry", "provider module",
                      "files changed", "import delivery"):
            with self.subTest(token=token):
                self.assertNotIn(token, low)


class ReferenceImplementationTest(unittest.TestCase):
    """Ground-truth material: never worker-visible, and never allowed to change a state."""

    maxDiff = None

    def test_every_state_has_a_reference_implementation(self):
        for state in STATES:
            with self.subTest(state=state):
                self.assertTrue((REFERENCE / state).is_dir())

    def test_the_reference_material_is_invisible_to_the_case_loader(self):
        """It must not reach a state's identity, a worker's repository, or a prompt."""
        case = _craft.load(CASE)
        for state in case["states"]:
            for path in _craft._fixture_files(Path(state["fixture"])):
                self.assertNotIn("reference-beacon", path.parts)
        self.assertEqual(len({s["identity"] for s in case["states"]}), len(case["states"]))

    def test_the_probe_no_longer_rewards_the_degradation(self):
        """The old case's decisive defect: the degraded state changed one file, the sound ones three.

        Counts are descriptive, never architecture truth — the point is only that the change-locality
        lens no longer points the wrong way.
        """
        changed = {}
        for state in STATES:
            ref = REFERENCE / state
            changed[state] = sorted(str(p.relative_to(ref)) for p in ref.rglob("*")
                                    if p.is_file())
        counts = {s: len(v) for s, v in changed.items()}
        self.assertEqual(len(set(counts.values())), 1,
                         f"the probe changes a different number of files per state: {counts}")

    def test_provider_outcome_knowledge_stays_provider_specific_in_the_sound_states(self):
        """Discrimination, checked mechanically on the reference patches.

        `result` is the field Beacon reports its outcome in. In the sound states only a
        provider-specific file mentions it; in the degraded state a provider-independent one does.
        """
        for state in ("state-a", "state-b"):
            with self.subTest(state=state):
                holders = [str(p.relative_to(REFERENCE / state))
                           for p in (REFERENCE / state).rglob("*.py")
                           if p.is_file() and '"result"' in p.read_text(encoding="utf-8")]
                self.assertEqual(holders, [h for h in holders if "beacon" in h.lower()],
                                 f"{state}: a file that is not Beacon's holds its convention")

    def test_provider_outcome_knowledge_escapes_in_the_degraded_state(self):
        holders = [str(p.relative_to(REFERENCE / "state-c"))
                   for p in (REFERENCE / "state-c").rglob("*.py")
                   if p.is_file() and '"result"' in p.read_text(encoding="utf-8")]
        self.assertTrue(holders, "the degraded reference no longer represents the pressure")
        self.assertFalse([h for h in holders if "beacon" in h.lower()],
                         "the degraded state acquired a provider-specific file")
        self.assertIn("notifications/status.py", holders)


if __name__ == "__main__":
    unittest.main()
