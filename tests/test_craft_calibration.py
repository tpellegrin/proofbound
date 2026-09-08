"""Deterministic tests for the system-craft calibration instrument.

The instrument's whole claim is that it recognises architectural quality rather than
resemblance to a preferred implementation. These tests defend the structure that claim rests
on: three behaviourally identical states, ground truth that never reaches anything that judges,
and no state or label visible in any prompt.

Nothing here invokes a model.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "scripts"))

import _craft  # noqa: E402

CASE = ROOT / "evals" / "craft" / "notification-provider-boundary"


def run_suite(state_fixture: Path, test_file: Path) -> bool:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td) / "p"
        shutil.copytree(state_fixture, project,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (project / test_file.name).write_bytes(test_file.read_bytes())
        cp = subprocess.run([sys.executable, "-B", "-m", "unittest", test_file.stem, "-q"],
                            cwd=project, capture_output=True, text=True, check=False)
        return cp.returncode == 0


class GroundTruthTest(unittest.TestCase):
    """The fixtures are the experiment. If they are not controls, nothing downstream matters."""

    maxDiff = None

    def setUp(self):
        self.case = _craft.load(CASE)

    def test_every_state_exhibits_the_same_accepted_behaviour(self):
        """Architectural difference only counts if functional difference is excluded."""
        behaviour = Path(self.case["behaviour_test"])
        for state in self.case["states"]:
            with self.subTest(state=state["id"]):
                self.assertTrue(run_suite(Path(state["fixture"]), behaviour),
                                "state does not exhibit the accepted behaviour")

    def test_no_state_already_satisfies_the_future_change(self):
        """Otherwise the probe measures nothing."""
        future = Path(self.case["future_test"])
        for state in self.case["states"]:
            with self.subTest(state=state["id"]):
                self.assertFalse(run_suite(Path(state["fixture"]), future))

    def test_the_case_declares_a_degradation_and_more_than_one_sound_state(self):
        statuses = [g["status"] for g in self.case["ground_truth"].values()]
        self.assertIn(_craft.DEGRADED, statuses, "no sensitivity control")
        self.assertGreaterEqual(statuses.count(_craft.PRESERVED), 2, "no specificity control")

    def test_a_case_with_one_sound_state_is_refused(self):
        """A single good state cannot separate recognising quality from recognising style."""
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "case"
            shutil.copytree(CASE, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            raw = json.loads((copy / "case.json").read_text())
            raw["states"] = [s for s in raw["states"] if s["id"] != "state-b"]
            (copy / "case.json").write_text(json.dumps(raw))
            with self.assertRaises(_craft.CraftCaseError) as caught:
                _craft.load(copy)
            self.assertIn("recognising resemblance", str(caught.exception))

    def test_a_case_with_no_degradation_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "case"
            shutil.copytree(CASE, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            raw = json.loads((copy / "case.json").read_text())
            for state in raw["states"]:
                state["status"] = _craft.PRESERVED
            (copy / "case.json").write_text(json.dumps(raw))
            with self.assertRaises(_craft.CraftCaseError):
                _craft.load(copy)

    def test_state_identities_are_distinct_and_ignore_build_artefacts(self):
        identities = [s["identity"] for s in self.case["states"]]
        self.assertEqual(len(set(identities)), len(identities))
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "case"
            shutil.copytree(CASE, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            cache = copy / "states" / "state-a" / "__pycache__"
            cache.mkdir()
            (cache / "app.cpython-999.pyc").write_bytes(b"\x00\x9f not utf-8")
            self.assertEqual([s["identity"] for s in _craft.load(copy)["states"]], identities)


class BlindnessTest(unittest.TestCase):
    """Ground truth must never reach anything that judges."""

    maxDiff = None

    def setUp(self):
        self.case = _craft.load(CASE)

    def test_the_worker_path_carries_no_status(self):
        for state in self.case["states"]:
            with self.subTest(state=state["id"]):
                self.assertEqual(sorted(state), ["contract", "fixture", "id", "identity"])
                self.assertNotIn("status", json.dumps(state))

    def test_worker_visible_material_never_names_a_state_or_a_status(self):
        visible = [Path(self.case[k]) for k in ("intent", "contract", "behaviour_test")]
        for state in self.case["states"]:
            visible += _craft._fixture_files(Path(state["fixture"]))
        for path in visible:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in _craft.FORBIDDEN_IN_PROMPTS:
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)

    def test_worker_visible_material_never_restates_the_property(self):
        words = re.findall(r"[a-z]{4,}", self.case["property"]["scenario"].lower())
        needles = {" ".join(words[i:i + 6]) for i in range(len(words) - 5)}
        visible = [Path(self.case[k]) for k in ("intent", "contract", "behaviour_test")]
        for state in self.case["states"]:
            visible += _craft._fixture_files(Path(state["fixture"]))
        for path in visible:
            flat = " ".join(re.findall(
                r"[a-z]{4,}", path.read_text(encoding="utf-8", errors="ignore").lower()))
            with self.subTest(path=path.name):
                self.assertFalse(any(n in flat for n in needles))

    def test_the_craft_prompt_shows_one_system_and_no_labels(self):
        filled = _craft.CRAFT_PROMPT.format(intent="INTENT", contract="CONTRACT",
                                            before="BEFORE", diff="DIFF")
        for token in _craft.FORBIDDEN_IN_PROMPTS:
            self.assertNotIn(token, filled.lower())
        self.assertNotIn(self.case["property"]["scenario"][:60].lower(), filled.lower())
        self.assertIn("You have not been shown any other system", filled)

    def test_the_grader_sees_the_property_but_never_the_answer(self):
        filled = _craft.GRADER_PROMPT.format(scenario="SCENARIO", report="REPORT")
        for token in ("state-a", "state-b", "state-c", "preserved", "ground truth",
                      "expected", "calibration"):
            self.assertNotIn(token, filled.lower())


class OutcomeTest(unittest.TestCase):
    """Python combines a blind claim with ground truth. It judges nothing."""

    maxDiff = None

    def test_the_four_outcomes_are_derived_not_asked(self):
        self.assertEqual(_craft.outcome(_craft.DEGRADED, _craft.CLAIMS_DEGRADED),
                         _craft.RECOGNISED_DEGRADED)
        self.assertEqual(_craft.outcome(_craft.DEGRADED, _craft.CLAIMS_UPHELD),
                         _craft.MISSED_DEGRADATION)
        self.assertEqual(_craft.outcome(_craft.PRESERVED, _craft.CLAIMS_DEGRADED),
                         _craft.FALSE_DEGRADATION)
        self.assertEqual(_craft.outcome(_craft.PRESERVED, _craft.CLAIMS_UPHELD),
                         _craft.RECOGNISED_UPHELD)

    def test_an_ungradeable_claim_stays_ungradeable(self):
        from _grade import UNAVAILABLE
        for status in (_craft.DEGRADED, _craft.PRESERVED):
            self.assertEqual(_craft.outcome(status, UNAVAILABLE), UNAVAILABLE)

    def test_no_score_rank_or_privileged_state_is_ever_a_field(self):
        """Prose may say "do not rank"; a field named `rank` would be the thing itself."""
        source = (ROOT / "evals" / "_craft.py").read_text(encoding="utf-8")
        source += (ROOT / "evals" / "pb_craft.py").read_text(encoding="utf-8")
        for forbidden in ("craft_score", "architecture_score", "quality_score", "rank",
                          "winner", "distance_to_reference", "gold_state", "reference_state",
                          "golden"):
            for pattern in (rf'"{forbidden}"', rf"'{forbidden}'", rf"\b{forbidden}\s*="):
                with self.subTest(forbidden=forbidden, pattern=pattern):
                    self.assertIsNone(re.search(pattern, source, re.I),
                                      f"{forbidden!r} appears as a field or variable")


class Ce1Test(unittest.TestCase):
    """Discovery-context facts are derived from evidence the run already produced."""

    maxDiff = None

    def test_read_not_changed_is_derived_from_log_and_scope_diff(self):
        with tempfile.TemporaryDirectory() as td:
            event = Path(td) / "attempt"
            event.mkdir()
            (event / "worker.log").write_text(
                "→ Read app.py\n"
                "→ Read notifications/model.py\n"
                "← Write delivery/beacon.py\n", encoding="utf-8")
            (event / "scope-diff.json").write_text(json.dumps(
                {"added": ["delivery/beacon.py"], "changed": ["app.py"],
                 "modified": [], "removed": []}), encoding="utf-8")
            facts = _craft.ce1_facts({"event_dir": str(event), "elapsed_seconds": 1.0})
        self.assertIn("notifications/model.py", facts["read_not_changed"])
        self.assertNotIn("app.py", facts["read_not_changed"])
        self.assertEqual(facts["tool_calls"], 3)

    def test_missing_evidence_yields_no_facts_rather_than_zeroes(self):
        self.assertEqual(_craft.ce1_facts({}), {})


class HistoricalCompatibilityTest(unittest.TestCase):
    maxDiff = None

    def test_the_craft_surface_does_not_touch_evaluation_scenarios(self):
        """Craft calibration is a separate surface; the measured populations do not move."""
        import _scenario
        scenarios = ROOT / "evals" / "scenarios"
        self.assertEqual(
            _scenario.load(scenarios / "retry-idempotency")["identity"],
            "8415e2fe4469e77bd9f4b434abfbc2fcb6a554a9f74761110e43f51dd2b40a95")
        self.assertEqual(
            _scenario.load(scenarios / "checkout-obligations")["identity"],
            "63c9f42f0c9b0fd903d723c9309637cb170d00ab0977e4630c928ec7d355b91d")

    def test_no_committed_evaluation_summary_gained_craft_fields(self):
        for path in sorted((ROOT / "evals" / "results").glob("*.json")):
            with self.subTest(summary=path.name):
                blob = path.read_text(encoding="utf-8").lower()
                for token in ("craft", "architecture", "state-a", "state-c"):
                    self.assertNotIn(token, blob)


if __name__ == "__main__":
    unittest.main()
