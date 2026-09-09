"""Deterministic tests for repeated measurement of the craft instrument.

A reliability experiment is only worth its provider calls if the thing being repeated genuinely
does not move. These tests defend that: identical bytes on every repeat, no repeat able to see
another, missing measurements kept apart from semantic ones, and a record that cannot silently
splice two configurations together.

Nothing here invokes a model.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "scripts"))

import _craft  # noqa: E402
import _repeat  # noqa: E402
import pb_craft  # noqa: E402

CASE = ROOT / "evals" / "craft" / "notification-provider-boundary"
ANCHORS = CASE / "anchors"
PREREG = CASE / "reliability-preregistration.md"


class AnchorCorpusTest(unittest.TestCase):
    """The frozen reports are the measurand of layer G. They must not drift."""

    maxDiff = None

    def setUp(self):
        self.manifest, self.anchors = pb_craft._anchors(CASE)
        self.case = _craft.load(CASE)

    def test_every_anchor_matches_its_recorded_hash(self):
        """`_anchors` raises on mismatch; this pins that the committed corpus is consistent."""
        for anchor in self.anchors:
            with self.subTest(anchor=anchor["id"]):
                data = (ANCHORS / f"{anchor['id']}.md").read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), anchor["sha256"])
                self.assertEqual(len(data), anchor["bytes"])

    def test_a_tampered_anchor_stops_the_run(self):
        import shutil
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "case"
            shutil.copytree(CASE, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            target = copy / "anchors" / "g1.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                pb_craft._anchors(copy)

    def test_the_corpus_covers_every_outcome_class(self):
        """A corpus of one shape would measure the grader on one shape."""
        self.assertEqual(
            {a["prior_outcome"] for a in self.anchors},
            {_craft.RECOGNISED_UPHELD, _craft.FALSE_DEGRADATION,
             _craft.MISSED_DEGRADATION, _craft.RECOGNISED_DEGRADED})

    def test_the_corpus_includes_both_sides_of_a_reversal(self):
        """The reports that disagreed about one implementation are the sharpest anchors."""
        by_instance = {}
        for anchor in self.anchors:
            by_instance.setdefault(anchor["instance"], set()).add(anchor["prior_outcome"])
        self.assertTrue(any(len(v) > 1 for v in by_instance.values()),
                        "no instance contributes two differently-graded reports")

    def test_every_anchor_names_a_declared_state(self):
        declared = {s["id"] for s in self.case["states"]}
        for anchor in self.anchors:
            with self.subTest(anchor=anchor["id"]):
                self.assertIn(anchor["state"], declared)

    def test_no_anchor_report_names_a_state_or_restates_the_property(self):
        """A report that named its own state, or quoted the manifest, would unblind the grader.

        Deliberately not a check for the status *words*: "preserved" and "degraded" are ordinary
        English in an architecture review — one anchor says the domain contract "is preserved per
        provider" — and excluding reports that use them would select an unrepresentative corpus
        for exactly the vocabulary the grader is asked about.
        """
        words = re.findall(r"[a-z]{4,}", self.case["property"]["scenario"].lower())
        needles = {" ".join(words[i:i + 6]) for i in range(len(words) - 5)}
        for anchor in self.anchors:
            low = anchor["report"].lower()
            with self.subTest(anchor=anchor["id"]):
                for state in self.case["states"]:
                    self.assertNotIn(state["id"], low)
                flat = " ".join(re.findall(r"[a-z]{4,}", low))
                self.assertFalse([n for n in needles if n in flat])

    def test_the_selection_rule_was_recorded_and_is_not_outcome_shopping(self):
        rule = " ".join(self.manifest["selection_rule"].lower().split())
        self.assertIn("never for observed instability", rule)
        self.assertIn("no repeated grading had been run", rule)

    def test_anchors_are_invisible_to_the_case_loader(self):
        """Adding a corpus must not change any state identity or reach worker-visible material."""
        identities = {s["id"]: s["identity"] for s in self.case["states"]}
        self.assertEqual(len(set(identities.values())), len(identities))
        for state in self.case["states"]:
            for path in _craft._fixture_files(Path(state["fixture"])):
                self.assertNotIn("anchors", path.parts)


class PreRegistrationTest(unittest.TestCase):
    """The experiment's decisions must exist in the repository before its results do."""

    maxDiff = None

    def setUp(self):
        # Wrapped prose: a declared decision is no less declared for falling across two lines.
        self.text = " ".join(PREREG.read_text(encoding="utf-8").split())

    def test_the_preregistration_exists_and_fixes_both_repetition_counts(self):
        self.assertIn("N = 15", self.text)
        self.assertIn("N = 10", self.text)

    def test_it_declares_the_coding_rubric_and_the_interpretation_categories(self):
        for needle in ("asserts-breach", "asserts-sound", "observes-without-concluding",
                       "High observed repeatability", "Material variance", "Severe instability"):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_it_states_what_cannot_be_frozen(self):
        """Claiming laboratory repeatability the provider does not support would be false."""
        low = self.text.lower()
        self.assertIn("neither temperature nor seed", low)
        self.assertIn("intermediate precision", low)

    def test_it_forbids_the_optimisations_this_milestone_must_not_make(self):
        low = self.text.lower()
        for forbidden in ("no missing criterion", "no question routing", "no ensembling",
                          "no model comparison", "no reliability state"):
            with self.subTest(forbidden=forbidden):
                self.assertIn(forbidden, low)


class RepeatMechanicsTest(unittest.TestCase):
    """What Python may decide here: counts, hashes, pairing, missingness. Never semantics."""

    maxDiff = None

    def test_a_failed_call_and_an_unparseable_answer_are_not_outcomes(self):
        for reason, expected in (("call failed: boom", _repeat.CALL_FAILURE),
                                 ("unparseable grader output: 'hmm'", _repeat.PARSE_FAILURE)):
            got = _repeat.grade_once(
                "report", "scenario", status=_craft.DEGRADED,
                grader=lambda *a, **k: {"claim": _craft.UNAVAILABLE, "reason": reason},
                outcome=_craft.outcome, unavailable=_craft.UNAVAILABLE)
            with self.subTest(reason=reason):
                self.assertEqual(got["status"], expected)
                self.assertIsNone(got["outcome"])
                self.assertIsNone(got["claim"])

    def test_missing_measurements_never_enter_a_distribution(self):
        measurements = [
            {"item": "g1", "repeat": 1, "status": _repeat.GRADED, "outcome": "recognised-upheld"},
            {"item": "g1", "repeat": 2, "status": _repeat.GRADED, "outcome": "recognised-upheld"},
            {"item": "g1", "repeat": 3, "status": _repeat.PARSE_FAILURE, "outcome": None},
            {"item": "g1", "repeat": 4, "status": _repeat.CALL_FAILURE, "outcome": None},
        ]
        got = _repeat.distribution(measurements, "g1")
        self.assertEqual(got["counts"], {"recognised-upheld": 2})
        self.assertEqual(got["graded"], 2)
        self.assertEqual(got["attempted"], 4)
        self.assertEqual(got["parse_failures"], 1)
        self.assertEqual(got["call_failures"], 1)
        # Two of four calls succeeded and both agreed: the modal share is 2/2, not 2/4.
        self.assertEqual(got["modal_share"], 1.0)

    def test_a_distribution_reports_dispersion_rather_than_a_verdict(self):
        measurements = [
            {"item": "x", "repeat": n, "status": _repeat.GRADED,
             "outcome": "recognised-degraded" if n <= 6 else "missed-degradation"}
            for n in range(1, 11)]
        got = _repeat.distribution(measurements, "x")
        self.assertEqual(got["counts"],
                         {"recognised-degraded": 6, "missed-degradation": 4})
        self.assertEqual(got["distinct_outcomes"], 2)
        self.assertEqual(got["modal_share"], 0.6)
        self.assertFalse(got["unanimous"])
        for forbidden in ("score", "rank", "reliable", "verdict", "winner"):
            self.assertNotIn(forbidden, json.dumps(got).lower())

    def test_the_order_of_results_is_retained(self):
        """First-run effects cannot be looked for in a record that threw the order away."""
        measurements = [{"item": "x", "repeat": n, "status": _repeat.GRADED,
                         "outcome": "a" if n == 1 else "b"} for n in (3, 1, 2)]
        self.assertEqual(_repeat.distribution(measurements, "x")["order"], ["a", "b", "b"])

    def test_a_resume_across_a_different_configuration_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "series.json"
            first = {"repeats": 15, "system": {"grader_model": "m"}}
            _repeat.write_series(out, first, [{"item": "g1", "repeat": 1}])
            self.assertEqual(len(_repeat.load_series(out, first)), 1)
            for changed in ({"repeats": 10, "system": {"grader_model": "m"}},
                            {"repeats": 15, "system": {"grader_model": "other"}}):
                with self.subTest(changed=changed):
                    with self.assertRaises(_repeat.RepeatConfigError):
                        _repeat.load_series(out, changed)

    def test_a_series_survives_interruption_and_resumes_without_repeating_work(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "series.json"
            config = {"repeats": 3, "system": {"grader_model": "m"}}
            done = []
            for n in (1, 2):
                done.append({"item": "g1", "repeat": n, "status": _repeat.GRADED})
                _repeat.write_series(out, config, done)
            resumed = _repeat.load_series(out, config)
            self.assertEqual(len(resumed), 2)
            self.assertTrue(_repeat._already_done(resumed, ("g1", 2)))
            self.assertFalse(_repeat._already_done(resumed, ("g1", 3)))
            self.assertFalse(list(out.parent.glob("*.partial")))

    def test_the_durable_record_carries_hashes_and_never_report_text(self):
        raw = [{"item": "i", "repeat": 1, "report": "secret prose", "report_sha256": "abc",
                "reason": "grader prose", "outcome": "recognised-upheld"}]
        redacted = _repeat.redact(raw)
        self.assertNotIn("report", redacted[0])
        self.assertNotIn("reason", redacted[0])
        self.assertEqual(redacted[0]["report_sha256"], "abc")
        self.assertEqual(redacted[0]["outcome"], "recognised-upheld")


class RepeatedMeasurementIsIndependentTest(unittest.TestCase):
    """Repetition only measures repeatability while the repeats cannot influence each other."""

    maxDiff = None

    def test_no_repeated_call_continues_a_session(self):
        source = (ROOT / "evals" / "_craft.py").read_text(encoding="utf-8")
        call = source.split("def _model_call", 1)[1].split("def reflect", 1)[0]
        for flag in ("--continue", "--session", "--fork", "-c", "resume"):
            with self.subTest(flag=flag):
                self.assertNotIn(f'"{flag}"', call)

    def test_every_grader_repeat_receives_identical_bytes(self):
        seen = []
        with tempfile.TemporaryDirectory() as td:
            args = argparse.Namespace(case=CASE, grader_model="g", repeats=3,
                                      question="verdict", problem_state="state-c",
                                      out=Path(td) / "g.json")

            def spy(report, scenario, **kw):
                seen.append((report, scenario, tuple(sorted(kw.items()))))
                return {"claim": _craft.CLAIMS_UPHELD, "reason": "ok"}

            with unittest.mock.patch.object(pb_craft, "provider_available", lambda: (True, "")), \
                 unittest.mock.patch.object(_craft, "classify_claim", spy), \
                 contextlib.redirect_stdout(io.StringIO()):
                pb_craft.cmd_regrade(args)

            manifest, anchors = pb_craft._anchors(CASE)
            self.assertEqual(len(seen), len(anchors) * 3)
            for anchor in anchors:
                calls = [c for c in seen if c[0] == anchor["report"]]
                self.assertEqual(len(calls), 3, f"{anchor['id']} was not graded three times")
                self.assertEqual(len(set(calls)), 1, "repeats differed in what was sent")

    def test_the_grader_never_learns_the_declared_status_or_the_repeat_index(self):
        filled = _craft.GRADER_PROMPT.format(scenario="S", report="R")
        for token in ("repeat", "attempt", "again", "previous", "state-a", "state-c",
                      "degraded architecture", "preserved"):
            with self.subTest(token=token):
                self.assertNotIn(token, filled.lower())

    def test_the_reflector_repeat_uses_the_untreated_prompt_and_no_treatment(self):
        source = (ROOT / "evals" / "pb_craft.py").read_text(encoding="utf-8")
        body = source.split("def cmd_repeat_reflect", 1)[1].split("def cmd_sample", 1)[0]
        self.assertNotIn("treatment=", body)
        self.assertIn('"treatment": None', body)

    def test_python_decides_no_semantics_anywhere_in_the_repeat_module(self):
        """Counts, hashes and pairing are mechanical. Whether a report is right is not."""
        source = (ROOT / "evals" / "_repeat.py").read_text(encoding="utf-8")
        for forbidden in ("def is_correct", "def agrees_semantically", "similarity",
                          "embedding", "difflib"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


class ReliabilityRecordTest(unittest.TestCase):
    """Committed reliability evidence stays evidence: no score, no state, no promotion."""

    maxDiff = None

    def test_no_reliability_record_carries_a_score_or_a_persisted_verdict(self):
        for name in ("craft-grader-repeat-v1.json", "craft-reflector-repeat-v1.json"):
            path = ROOT / "evals" / "results" / name
            if not path.is_file():
                continue
            with self.subTest(record=name):
                record = json.loads(path.read_text(encoding="utf-8"))
                blob = json.dumps(record).lower()
                for forbidden in ("score", "rank", "winner", "reliable\":", "stable\":",
                                  "confidence", "gold"):
                    self.assertNotIn(forbidden, blob)
                self.assertEqual(len(record["frozen_identity"]), 64)
                for measurement in record["measurements"]:
                    self.assertNotIn("report", measurement)

    def test_no_reliability_state_leaked_into_engineering_state(self):
        """`P3`: reliability is derived evaluation evidence, never a recorded property."""
        for path in sorted((ROOT / "evals" / "results").glob("*.json")):
            if path.name.startswith("craft-"):
                continue
            blob = path.read_text(encoding="utf-8").lower()
            with self.subTest(summary=path.name):
                for token in ("repeatab", "frozen_identity", "modal_share"):
                    self.assertNotIn(token, blob)


if __name__ == "__main__":
    unittest.main()
