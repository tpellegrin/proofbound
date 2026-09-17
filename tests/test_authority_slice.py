"""The authority slice's oracle, and one end-to-end fixture build.

The slice exists to separate four questions that the authority demonstrations could not tell
apart. These tests cover the half that must be true before any of it means anything:

* the oracle decides the **document**, not the case it sits in — a fake reviewer that passed
  because its task was called "coherent" would measure the harness's naming convention;
* it accepts a structurally different sound implementation and rejects defective ones, so it is
  discriminating rather than merely agreeable;
* its "no dispatch order works" really is nonexistence, because the enumeration is complete — the
  opposite of the bounded float search in `demo/pb-authority-demo-2/`;
* the blocked handoff refuses for the reason it is supposed to, through the shipped guard.

The full four-case replay is a command rather than a test (`pb_slice.py replay`, about 20 seconds);
one fixture is built here because it is the part most likely to rot silently when a script changes.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLICE = ROOT / "evals" / "authority_slice"
sys.path.insert(0, str(SLICE))

import _implementations as impl          # noqa: E402
import _obligations as oracle            # noqa: E402
import pb_slice                          # noqa: E402


def text(case: str) -> str:
    return (SLICE / "cases" / case / "requirements.md").read_text(encoding="utf-8")


class ObligationModelTest(unittest.TestCase):
    def test_an_unknown_obligation_is_refused_rather_than_skipped(self):
        """Silently ignoring an obligation would make an unsatisfiable document look fine."""
        broken = text("coherent-requirements").replace('"fifo-per-key"', '"whatever-seems-nice"')
        with self.assertRaises(oracle.ModelError):
            oracle.parse_model(broken)

    def test_a_document_with_no_model_block_is_refused(self):
        with self.assertRaises(oracle.ModelError):
            oracle.parse_model("# requirements\n\nbe fair.\n")

    def test_the_declared_domain_is_enumerated_in_full(self):
        model = oracle.parse_model(text("coherent-requirements"))
        sequences = oracle.domain(model)
        self.assertEqual(len(sequences), 3 + 9 + 27 + 81 + 243)
        self.assertEqual(len(set(map(tuple, sequences))), len(sequences))


class ContradictionTest(unittest.TestCase):
    def test_the_contradiction_is_minimal_in_both_senses(self):
        model = oracle.parse_model(text("contradictory-requirements"))
        conflict = oracle.first_conflict(model)
        self.assertEqual(conflict["arrivals"], ["a", "a", "b"])
        self.assertEqual(conflict["minimal_unsatisfiable_cores"], [["R2", "R3"]])
        # Minimal in the witness: no two-item sequence conflicts.
        for arrivals in (["a", "a"], ["a", "b"], ["b", "a"]):
            self.assertIsNotNone(oracle.satisfying_order(arrivals, model["obligations"]),
                                 f"{arrivals} should still be serviceable")
        # Minimal in the core: neither requirement alone is unsatisfiable.
        for single in ("R2", "R3"):
            self.assertIsNotNone(
                oracle.satisfying_order(["a", "a", "b"],
                                        {single: model["obligations"][single]}))

    def test_exhaustion_here_is_nonexistence_not_a_failed_search(self):
        """All six orders of the witness are enumerated, and every one breaks something."""
        model = oracle.parse_model(text("contradictory-requirements"))
        import itertools
        orders = list(itertools.permutations(oracle.items_of(["a", "a", "b"])))
        self.assertEqual(len(orders), 6)
        for order in orders:
            self.assertTrue(oracle.violations(list(order), ["a", "a", "b"],
                                              model["obligations"]))

    def test_the_coherent_case_is_satisfiable_over_its_whole_domain(self):
        model = oracle.parse_model(text("coherent-requirements"))
        self.assertTrue(oracle.satisfiable_everywhere(model)["satisfiable"])
        self.assertIsNone(oracle.first_conflict(model))


class DiscriminationTest(unittest.TestCase):
    """An oracle that accepts everything, or only its own reference, measures nothing."""

    def setUp(self) -> None:
        self.model = oracle.parse_model(text("coherent-requirements"))

    def test_a_structurally_different_sound_implementation_is_accepted(self):
        for name, fn in impl.CONFORMING.items():
            with self.subTest(implementation=name):
                self.assertTrue(oracle.check_implementation(fn, self.model)["conforms"])

    def test_every_defective_variant_is_rejected_for_a_named_requirement(self):
        for name, fn in impl.DEFECTIVE.items():
            with self.subTest(implementation=name):
                result = oracle.check_implementation(fn, self.model)
                self.assertFalse(result["conforms"])
                self.assertTrue(result["violated"], "a rejection must name what it broke")

    def test_each_requirement_is_separately_falsifiable(self):
        """If some requirement were unbreakable, it would not be carrying any weight."""
        broken = {rid for fn in impl.DEFECTIVE.values()
                  for rid in oracle.check_implementation(fn, self.model)["violated"]}
        self.assertEqual(broken, {"R1", "R2", "R3", "R4"})

    def test_the_verdict_follows_the_document_rather_than_the_case_name(self):
        flipped = text("coherent-requirements").replace('"R2": "fifo-per-key"',
                                                        '"R2": "fifo-global"')
        self.assertIsNotNone(oracle.first_conflict(oracle.parse_model(flipped)))
        restored = text("contradictory-requirements").replace('"R2": "fifo-global"',
                                                              '"R2": "fifo-per-key"')
        self.assertIsNone(oracle.first_conflict(oracle.parse_model(restored)))


class ProbeInputTest(unittest.TestCase):
    """What a fresh coordinator is given must not contain what it is asked to recover."""

    def test_the_probe_input_withholds_every_answer(self):
        with tempfile.TemporaryDirectory() as td:
            supplied = pb_slice.probe_input(Path(td))
        for leaked in ("candidate identity is", "no-consistency-acceptance", "R2", "authorized"):
            self.assertNotIn(leaked, supplied)
        self.assertIn("must establish for yourself", supplied)
        self.assertIn("Launch no worker", supplied)
        self.assertIn("a refusal is an answer", " ".join(supplied.lower().split()))

    def test_the_answer_key_is_not_part_of_the_agent_visible_artifact(self):
        for case in ("coherent-requirements", "contradictory-requirements"):
            key = json.loads((SLICE / "cases" / case / "case.json").read_text(encoding="utf-8"))
            self.assertEqual(key["agent_visible"], ["requirements.md"])
            body = text(case)
            self.assertNotIn(key["expected_class"], body)
            self.assertNotIn("expected_judgement", body)


class LaunchArithmeticTest(unittest.TestCase):
    """The ceiling must be derived from the paths, so a forgotten path cannot hide in it."""

    def setUp(self) -> None:
        import _launch_paths
        self.paths = _launch_paths

    def test_the_ceiling_is_the_enumerated_maximum_plus_the_relaunch_allowance(self):
        derived = self.paths.ceiling()
        worst = max(p["launches"] for p in self.paths.paths())
        self.assertEqual(derived["max_launches_on_a_path"], worst)
        self.assertEqual(derived["ceiling"],
                         worst + self.paths.MECHANICAL_RELAUNCH_ALLOWANCE)

    def test_the_repair_path_is_counted(self):
        """demo-2's ceiling was written as a sum that omitted a path its own text allowed.

        Dropping the repair edge must lower the ceiling. If it does not, the repair is not in the
        arithmetic and the run would discover that when it needed the launches.
        """
        full = self.paths.ceiling()["ceiling"]
        original = self.paths.TRANSITIONS["reviewed"]
        self.paths.TRANSITIONS["reviewed"] = [t for t in original if t[0] != "repaired"]
        self.addCleanup(self.paths.TRANSITIONS.__setitem__, "reviewed", original)
        self.assertLess(self.paths.ceiling()["ceiling"], full)

    def test_every_path_ends_in_a_terminal_state(self):
        terminal = {s for s, nxt in self.paths.TRANSITIONS.items() if not nxt}
        for path in self.paths.paths():
            self.assertIn(path["path"][-1], terminal, path)


class BlockedHandoffFixtureTest(unittest.TestCase):
    """The most discriminating case, built for real through the shipped scripts."""

    def setUp(self) -> None:
        into = Path(tempfile.mkdtemp(prefix="pb-slice-test-"))
        self.addCleanup(shutil.rmtree, into, True)
        self.record = pb_slice._handoff_case("blocked-handoff", into / "fixture")
        self.attempts = (into / "fixture" / "project"
                         / "DeepSeekAndDestroy/plans/slice/runs/r1/attempts")

    def test_each_attempt_answers_the_question_its_own_contract_declares(self):
        """Found by a fresh-context probe: the fake answered by role, so the consistency
        attempt emitted the proposal challenge verbatim and its acceptance was mechanically
        clean and semantically empty. Its contract's AC-002 was unmet and nothing noticed,
        because an integrity gate never reads the report body.
        """
        proposal = (self.attempts / "spec-reflector-1" / "report.md").read_text(encoding="utf-8")
        consistency = (self.attempts / "spec-reflector-2" / "report.md").read_text(encoding="utf-8")
        self.assertNotEqual(proposal, consistency,
                            "two different review purposes produced byte-identical evidence")
        self.assertIn("member", consistency, "AC-002 requires the single-member narrowness")
        self.assertIn("as one engineering authority", consistency)

    def test_the_guard_refuses_although_the_candidate_is_still_derivable(self):
        record = self.record
        self.assertEqual(record["status"], "completed", record)
        authorization = record["authorization"]
        self.assertFalse(authorization["authorized"])
        self.assertEqual([f["code"] for f in authorization["findings"]],
                         ["no-consistency-acceptance"])
        self.assertEqual(authorization["derived_candidate"], record["candidate"],
                         "the candidate is still derivable, which is exactly why reading it out "
                         "of a contract would get this wrong")
        self.assertTrue(record["mutation"]["removed_consistency_records"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
