"""Deterministic tests for the evaluation harness itself.

The harness is stochastic in use and must not be stochastic in construction. Everything here
runs against fake executables: no network, no provider, no credentials, no cost. These are
product tests of the measuring instrument, not evaluations.

The boundary they defend: the deterministic suite must never invoke a real model, and an
evaluation must never be able to report an infrastructure failure as a semantic result.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "scripts"))

import _grade  # noqa: E402
import _scenario  # noqa: E402
import _summary  # noqa: E402
import _trial  # noqa: E402

SCENARIOS = ROOT / "evals" / "scenarios"

# A fake worker that plays the reflector. Its report is chosen per test, so the harness can
# be driven through detection, non-detection and failure without a provider.
FAKE_WORKER = r'''#!/usr/bin/env python3
import os, pathlib, re, sys
a = sys.argv[1:]
if a[:2] == ['session', 'list']:
    print('[]'); raise SystemExit(0)
if not a or a[0] != 'run':
    raise SystemExit(2)
mode = os.environ.get('EVAL_FAKE_MODE', 'report')
if mode == 'crash':
    sys.stderr.write('opencode: provider unavailable\n'); raise SystemExit(3)
prompt = a[-1]
m = re.search(r'^Report: (.+)$', prompt, re.M)
if not m:
    raise SystemExit(2)
report = pathlib.Path(m.group(1).strip())
pathlib.Path(os.environ['EVAL_PROMPT_COPY']).write_text(prompt)
if mode == 'silent':
    raise SystemExit(0)
report.write_text(os.environ.get('EVAL_FAKE_REPORT', 'A reflection.\n'))
'''


@contextlib.contextmanager
def fake_worker(stack, *, mode="report", report="A reflection.\n"):
    """Put a fake `opencode` on PATH, exactly as the deterministic slices do."""
    root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
    binary = root / "opencode"
    binary.write_text(FAKE_WORKER)
    binary.chmod(0o755)
    prompt_copy = root / "prompt.txt"
    old = os.environ.copy()
    os.environ["PATH"] = str(root) + os.pathsep + os.environ["PATH"]
    os.environ["EVAL_FAKE_MODE"] = mode
    os.environ["EVAL_FAKE_REPORT"] = report
    os.environ["EVAL_PROMPT_COPY"] = str(prompt_copy)
    try:
        yield prompt_copy
    finally:
        os.environ.clear()
        os.environ.update(old)


class ScenarioTest(unittest.TestCase):
    maxDiff = None

    def test_the_shipped_suite_loads_and_is_inspectable(self):
        found = _scenario.discover(SCENARIOS)
        self.assertGreaterEqual(len(found), 3, "V1 expects 3-5 scenarios")
        self.assertLessEqual(len(found), 5)
        self.assertTrue(any(s["kind"] == "regression" for s in found))
        self.assertTrue(any(s["kind"] == "capability" for s in found))
        for s in found:
            self.assertEqual(len(s["identity"]), 64)
            self.assertIn(s["review_purpose"],
                          {"design-reflection", "specification-reflection", "proposal-reflection"})

    def test_scenario_identities_are_distinct_and_stable(self):
        found = _scenario.discover(SCENARIOS)
        ids = [s["identity"] for s in found]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual([s["identity"] for s in _scenario.discover(SCENARIOS)], ids)

    def test_changing_the_engineering_problem_changes_identity(self):
        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            src = SCENARIOS / "retry-idempotency"
            copy = root / "s"
            shutil.copytree(src, copy)
            before = _scenario.load(copy)["identity"]
            art = copy / "fixture" / "specs/CH-001/design.md"
            art.write_text(art.read_text() + "\nAn extra consideration.\n", encoding="utf-8")
            self.assertNotEqual(_scenario.load(copy)["identity"], before,
                               "fixture bytes define the engineering problem")

    def test_a_scenario_that_leaks_its_answer_is_rejected(self):
        """The system under test must never be handed the grader's property."""
        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            copy = root / "s"
            shutil.copytree(SCENARIOS / "retry-idempotency", copy)
            manifest = json.loads((copy / "scenario.json").read_text())
            art = copy / "fixture" / "specs/CH-001/design.md"
            art.write_text(art.read_text() + "\n" + manifest["property"] + "\n", encoding="utf-8")
            with self.assertRaises(_scenario.ScenarioError) as e:
                _scenario.load(copy)
            self.assertIn("leaks its planted property", str(e.exception))

    def test_malformed_scenarios_fail_closed(self):
        base = json.loads((SCENARIOS / "retry-idempotency" / "scenario.json").read_text())
        for mutate in (lambda m: m.update(format="proofbound-eval-scenario-v2"),
                       lambda m: m.pop("property"),
                       lambda m: m.update(kind="whatever"),
                       lambda m: m.update(summary="short"),
                       lambda m: m.update(artifact="../escape.md"),
                       lambda m: m.update(review_purpose="implementation-review"),
                       lambda m: m.update(extra="x")):
            with contextlib.ExitStack() as stack:
                root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
                copy = root / "s"
                shutil.copytree(SCENARIOS / "retry-idempotency", copy)
                m = dict(base)
                mutate(m)
                (copy / "scenario.json").write_text(json.dumps(m), encoding="utf-8")
                with self.assertRaises(_scenario.ScenarioError):
                    _scenario.load(copy)


class TrialTest(unittest.TestCase):
    """Trials drive the real pipeline; only the worker executable is faked."""

    maxDiff = None

    def scenario(self):
        return _scenario.load(SCENARIOS / "retry-idempotency")

    def test_a_trial_runs_the_real_pipeline_and_is_valid(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(fake_worker(stack, report="The retry policy conflicts with the proposal.\n"))
            got = _trial.run_trial(self.scenario(), model="fake/model")
            self.assertEqual(got["validity"], _trial.VALID, got.get("reason"))
            self.assertEqual(got["gate"]["role"], "spec-reflector")
            self.assertTrue(got["gate"]["integrity_ok"], got["gate"].get("errors"))
            self.assertFalse(got["gate"]["writes_project"], "the reflector must be read-only")
            self.assertGreater(got["prompt_bytes"], 0)
            self.assertIn("retry policy", got["report"])

    def test_the_planted_property_never_reaches_the_worker(self):
        """The leakage proof, taken from the exact bytes the worker received."""
        scenario = self.scenario()
        with contextlib.ExitStack() as stack:
            prompt_copy = stack.enter_context(fake_worker(stack))
            got = _trial.run_trial(scenario, model="fake/model")
            self.assertEqual(got["validity"], _trial.VALID, got.get("reason"))
            # The prompt is a pointer list, so check it *and* the contract it names.
            prompt = prompt_copy.read_text().lower()
            contract = Path(scenario["contract"]).read_text(encoding="utf-8").lower()
            for haystack, label in ((prompt, "launch prompt"), (contract, "task contract")):
                self.assertNotIn(scenario["property"].lower()[:80], haystack, label)
            # The accepted context that makes the contradiction discoverable IS reachable.
            self.assertIn("proposal", contract)
            self.assertGreater(got["context_bytes"], 0, "supplied material must be measurable")

    def test_an_unavailable_provider_is_a_setup_failure_not_a_missed_contradiction(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(fake_worker(stack, mode="crash"))
            got = _trial.run_trial(self.scenario(), model="fake/model")
            self.assertIn(got["validity"], {_trial.SETUP_FAILURE, _trial.HARNESS_FAILURE})
            self.assertNotEqual(got["validity"], _trial.VALID)

    def test_a_worker_that_produces_no_report_is_not_a_semantic_result(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(fake_worker(stack, mode="silent"))
            got = _trial.run_trial(self.scenario(), model="fake/model")
            self.assertEqual(got["validity"], _trial.SETUP_FAILURE)
            # Classified by Proofbound's own report_state, not by a heuristic here.
            self.assertIn("launcher-skeleton", got["reason"])

    def test_trials_do_not_leak_state_into_one_another(self):
        """Each trial starts from a pristine fixture copy."""
        scenario = self.scenario()
        with contextlib.ExitStack() as stack:
            stack.enter_context(fake_worker(stack))
            first = _trial.run_trial(scenario, model="fake/model")
            second = _trial.run_trial(scenario, model="fake/model")
            self.assertNotEqual(first["event_dir"], second["event_dir"])
            self.assertEqual(first["validity"], _trial.VALID)
            self.assertEqual(second["validity"], _trial.VALID)
            # Neither trial's temporary tree survives, so nothing can carry over.
            self.assertFalse(Path(first["event_dir"]).exists())
            self.assertFalse(Path(second["event_dir"]).exists())

    def test_a_missing_executable_refuses_before_any_trial(self):
        ok, detail = _trial.provider_available("definitely-not-a-real-binary-xyz")
        self.assertFalse(ok)
        self.assertIn("not on PATH", detail)


class MechanicalGradeTest(unittest.TestCase):
    """Graded from Proofbound's own state, never by reading prose."""

    maxDiff = None

    def trial(self, **over):
        base = {"validity": _trial.VALID, "report": "Something.\n",
                "gate": {"role": "spec-reflector", "integrity_ok": True, "errors": [],
                         "ready_for_interpretation": True, "writes_project": False,
                         "scope": {"changed_count": 0, "git_head_changed": False}},
                "state": {"phases": {"spec": {"tasks": {"EVAL-artifact": {"status": "in-review"}}}}}}
        base.update(over)
        return base

    def test_a_clean_independent_reflection_grades_ok(self):
        self.assertTrue(_grade.mechanical(self.trial())["ok"])

    def test_each_mechanical_violation_is_named(self):
        cases = [
            ({"gate": {**self.trial()["gate"], "role": "reviewer"}}, "role"),
            ({"gate": {**self.trial()["gate"], "integrity_ok": False, "errors": ["X"]}}, "not clean"),
            ({"gate": {**self.trial()["gate"], "writes_project": True}}, "read-only"),
            ({"gate": {**self.trial()["gate"], "scope": {"changed_count": 2}}}, "mutated"),
            ({"report": "   "}, "no report"),
            ({"state": {"phases": {"spec": {"tasks": {"EVAL-artifact": {"status": "accepted"}}}}}},
             "accepted"),
        ]
        for over, needle in cases:
            got = _grade.mechanical(self.trial(**over))
            self.assertFalse(got["ok"], over)
            self.assertTrue(any(needle in f for f in got["findings"]), got["findings"])


class SemanticGradeTest(unittest.TestCase):
    maxDiff = None

    def test_verdicts_are_parsed_strictly(self):
        self.assertEqual(_grade.classify("DETECTED\nthe retry conflicts")["result"], _grade.DETECTED)
        self.assertEqual(_grade.classify("NOT_DETECTED")["result"], _grade.NOT_DETECTED)
        self.assertEqual(_grade.classify("NOT DETECTED\nreason")["result"], _grade.NOT_DETECTED)

    def test_malformed_or_missing_output_never_invents_a_score(self):
        for bad in ("", "   ", "maybe", "I think it found it", "{json}", "3/5"):
            self.assertEqual(_grade.classify(bad)["result"], _grade.UNAVAILABLE, bad)

    def test_an_unavailable_grader_reports_unavailable(self):
        got = _grade.semantic({"report": "x"}, {"property": "y"},
                              grader_model="m", executable="definitely-not-real-xyz")
        self.assertEqual(got["result"], _grade.UNAVAILABLE)
        self.assertEqual(got["grader_model"], "m")


class SummaryTest(unittest.TestCase):
    maxDiff = None

    def graded(self, validity, mech=True, sem=_grade.DETECTED):
        return {"trial": {"validity": validity, "prompt_bytes": 100, "elapsed_seconds": 1.0},
                "mechanical": {"ok": mech, "findings": []},
                "semantic": {"result": sem, "reason": ""}}

    def suite(self):
        scenario = _scenario.load(SCENARIOS / "retry-idempotency")
        return [{"scenario": scenario, "graded": [
            self.graded(_trial.VALID),
            self.graded(_trial.VALID, sem=_grade.NOT_DETECTED),
            self.graded(_trial.VALID, sem=_grade.UNAVAILABLE),
            self.graded(_trial.SETUP_FAILURE),
            self.graded(_trial.HARNESS_FAILURE),
        ]}]

    def test_attempted_and_valid_are_both_reported(self):
        """A provider that failed half the time must not look like a 50% score."""
        s = _summary.summarize(self.suite(), system={"model": "m"})
        counts = s["scenarios"][0]["counts"]
        self.assertEqual(counts["attempted"], 5)
        self.assertEqual(counts["valid"], 3)
        self.assertEqual(counts["setup_failures"], 1)
        self.assertEqual(counts["harness_failures"], 1)
        self.assertEqual(counts["semantic_detected"], 1)
        self.assertEqual(counts["semantic_not_detected"], 1)
        self.assertEqual(counts["grading_unavailable"], 1)

    def test_invalid_trials_are_retained_not_dropped(self):
        s = _summary.summarize(self.suite(), system={"model": "m"})
        kinds = [t["validity"] for t in s["scenarios"][0]["trials"]]
        self.assertIn(_trial.SETUP_FAILURE, kinds)
        self.assertIn(_trial.HARNESS_FAILURE, kinds)

    def test_there_is_no_composite_score(self):
        s = _summary.summarize(self.suite(), system={"model": "m"})
        blob = json.dumps(s).lower()
        # `kind: regression` is the scenario taxonomy, not a verdict, so it is not listed.
        for forbidden in ("score", "winner", "approved", "production_ready", "better", "rating"):
            self.assertNotIn(forbidden, blob, f"{forbidden!r} must not be protocol")

    def test_no_raw_evidence_reaches_the_committed_summary(self):
        s = _summary.summarize(self.suite(), system={"model": "m"})
        blob = json.dumps(s)
        # Metric *names* like median_prompt_bytes are fine; raw evidence is not.
        for forbidden in ("transcript", "event_dir", "launch-prompt", "worker.log",
                          "\"report\"", "evidence"):
            self.assertNotIn(forbidden, blob.lower(), f"{forbidden} leaked into the summary")
        # The planted property must never be committed either — it is grader-only.
        self.assertNotIn("property", blob.lower())

    def test_unknown_summary_versions_fail_closed(self):
        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            p = root / "s.json"
            p.write_text(json.dumps({"format": "proofbound-eval-summary-v2"}), encoding="utf-8")
            with self.assertRaises(_summary.SummaryError):
                _summary.load(p)

    def test_render_shows_per_scenario_counts_not_only_a_total(self):
        s = _summary.summarize(self.suite(), system={"model": "m"})
        text = _summary.render(s)
        self.assertIn("retry-idempotency", text)
        self.assertIn("attempted 5", text)
        self.assertIn("valid 3", text)


class BoundaryTest(unittest.TestCase):
    """The deterministic suite must never need a provider."""

    maxDiff = None

    def test_the_cli_refuses_to_run_without_a_worker_executable(self):
        env = dict(os.environ)
        env["PATH"] = "/nonexistent"
        cp = subprocess.run([sys.executable, str(ROOT / "evals" / "pb_eval.py"), "run",
                             "--trials", "1"], text=True, capture_output=True, env=env, check=False)
        self.assertEqual(cp.returncode, 2)
        self.assertIn("cannot run trials", cp.stderr)

    def test_listing_scenarios_needs_no_provider(self):
        cp = subprocess.run([sys.executable, str(ROOT / "evals" / "pb_eval.py"), "list"],
                            text=True, capture_output=True, check=False)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("retry-idempotency", cp.stdout)

    def test_no_product_script_imports_the_evaluation_harness(self):
        """Dependency direction: eval may use the product, never the reverse."""
        for path in sorted((ROOT / "scripts").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for name in ("_scenario", "_trial", "_grade", "_summary", "pb_eval"):
                self.assertNotIn(f"import {name}", text, f"{path.name} imports eval module {name}")


if __name__ == "__main__":
    unittest.main()
