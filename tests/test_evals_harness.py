"""Deterministic tests for the evaluation harness itself.

The harness is stochastic in use and must not be stochastic in construction. Everything here
runs against fake executables: no network, no provider, no credentials, no cost. These are
product tests of the measuring instrument, not evaluations.

The boundary they defend: the deterministic suite must never invoke a real model, and an
evaluation must never be able to report an infrastructure failure as a semantic result.
"""
from __future__ import annotations

import contextlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "scripts"))

import _compare  # noqa: E402
import _grade  # noqa: E402
import _scenario  # noqa: E402
import _summary  # noqa: E402
import _trial  # noqa: E402

SCENARIOS = ROOT / "evals" / "scenarios"

# A fake worker that plays the reflector. Its report is chosen per test, so the harness can
# be driven through detection, non-detection and failure without a provider.
FAKE_WORKER = r'''#!/usr/bin/env python3
import json, os, pathlib, re, sys
a = sys.argv[1:]
if a[:2] == ['session', 'list']:
    print('[]'); raise SystemExit(0)
if not a or a[0] != 'run':
    raise SystemExit(2)
mode = os.environ.get('EVAL_FAKE_MODE', 'report')
if mode == 'crash':
    sys.stderr.write('opencode: provider unavailable\n'); raise SystemExit(3)
prompt = a[-1]
pathlib.Path(os.environ['EVAL_PROMPT_COPY']).with_name('argv.json').write_text(json.dumps(a))
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
        """Small enough that a human can read every scenario, which is the actual constraint.

        Two populations live here — the anchors the first baseline measured and the
        calibration candidates that came after — so the bound is on inspectability, not on
        either group's size.
        """
        found = _scenario.discover(SCENARIOS)
        self.assertGreaterEqual(len(found), 3)
        self.assertLessEqual(len(found), 12, "a suite nobody can read stops being calibrated")
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
            self.assertIn("leaks planted property", str(e.exception))

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

    def test_the_requested_model_is_the_model_the_worker_actually_runs(self):
        """A summary naming one model while the pipeline ran another is a false record.

        This is a regression guard: the first live smoke trial ran the inherited default
        instead of the requested model, because the model reached the run state through an
        environment variable that was set after the state was written.
        """
        with contextlib.ExitStack() as stack:
            prompt_copy = stack.enter_context(fake_worker(stack))
            got = _trial.run_trial(self.scenario(), model="probe/model-under-test")
            self.assertEqual(got["validity"], _trial.VALID, got.get("reason"))
            argv = json.loads((prompt_copy.parent / "argv.json").read_text())
            self.assertIn("--model", argv)
            self.assertEqual(argv[argv.index("--model") + 1], "probe/model-under-test")
            # And the same model is what the trial reports for the record.
            self.assertEqual(got["model"], "probe/model-under-test")
            self.assertEqual(
                got["state"]["worker_runtime"]["model"], "probe/model-under-test")

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


class HarnessVersionTest(unittest.TestCase):
    """`opencode-cli` names a protocol, not a release."""

    maxDiff = None

    def _fake_harness(self, stack, body):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        binary = root / "pb-fake-harness"
        binary.write_text(body)
        binary.chmod(0o755)
        return str(binary.name), root

    def test_version_comes_from_the_executable_that_would_run_trials(self):
        with contextlib.ExitStack() as stack:
            name, root = self._fake_harness(
                stack, "#!/bin/sh\necho '9.9.9-test'\n")
            old = os.environ["PATH"]
            os.environ["PATH"] = str(root) + os.pathsep + old
            try:
                self.assertEqual(_trial.harness_version(name), "9.9.9-test")
            finally:
                os.environ["PATH"] = old

    def test_a_harness_that_cannot_report_a_version_is_unknown_not_assumed(self):
        with contextlib.ExitStack() as stack:
            name, root = self._fake_harness(stack, "#!/bin/sh\nexit 3\n")
            old = os.environ["PATH"]
            os.environ["PATH"] = str(root) + os.pathsep + old
            try:
                self.assertIsNone(_trial.harness_version(name))
            finally:
                os.environ["PATH"] = old

    def test_a_missing_harness_is_unknown(self):
        self.assertIsNone(_trial.harness_version("definitely-not-a-real-binary-xyz"))

    def test_the_historical_baseline_still_loads_and_is_not_reinterpreted(self):
        """A record written before the field existed reads as unknown, never as current."""
        recorded = ROOT / "evals" / "results" / "eval-v1.json"
        if not recorded.is_file():
            self.skipTest("no committed baseline")
        summary = _summary.load(recorded)
        self.assertNotIn("harness_version", summary["system"],
                         "the historical baseline must not be backfilled")
        self.assertIn("version-unknown", _summary.render(summary))


class CalibrationScenarioTest(unittest.TestCase):
    """Declared difficulty is checked, not merely asserted."""

    maxDiff = None

    # The identities recorded by the first live baseline. If any of these move, the original
    # measurement stops being comparable with anything, so they are pinned here explicitly.
    V1_IDENTITIES = {
        "adversarial-weaken-upstream": "7d92af1530f6abdaf5bd86f3c94adcc25bb3f138297df22c0ab5cb5183a8cda8",
        "cache-invalidation-gap": "36dc8aeb45c9196fe1eb4fb9b091e9b65edfc63caf775d1b4d8a140b6fc4d363",
        "ordering-contradiction": "ea028a8c7dcedf5589763484cc467c2977864240bd6fe012027260646db19979",
        "retry-idempotency": "8415e2fe4469e77bd9f4b434abfbc2fcb6a554a9f74761110e43f51dd2b40a95",
    }

    def test_the_first_baselines_scenarios_are_byte_for_byte_unchanged(self):
        for name, expected in self.V1_IDENTITIES.items():
            with self.subTest(scenario=name):
                self.assertEqual(_scenario.load(SCENARIOS / name)["identity"], expected)

    def test_calibration_metadata_is_not_part_of_scenario_identity(self):
        """It changes nothing the system under test receives, exactly like the rubric."""
        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            src = SCENARIOS / "freshness-batching-conflict"
            copy = root / "copy"
            shutil.copytree(src, copy)
            manifest = json.loads((copy / "scenario.json").read_text())
            before = _scenario.load(copy)["identity"]
            manifest["distractors"] = manifest["distractors"] + [
                "An additional defensible concern recorded for grading purposes only."]
            manifest["notes"] = "Calibration bookkeeping, invisible to the worker."
            (copy / "scenario.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(_scenario.load(copy)["identity"], before)

    def _mutated(self, stack, name, mutate):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        copy = root / "copy"
        shutil.copytree(SCENARIOS / name, copy)
        manifest = json.loads((copy / "scenario.json").read_text())
        mutate(manifest)
        (copy / "scenario.json").write_text(json.dumps(manifest), encoding="utf-8")
        return copy

    def test_the_difficulty_vocabulary_is_closed(self):
        with contextlib.ExitStack() as stack:
            copy = self._mutated(stack, "freshness-batching-conflict",
                                 lambda m: m.update(dimensions=["extremely-hard"]))
            with self.assertRaises(_scenario.ScenarioError):
                _scenario.load(copy)

    def test_dependency_distance_requires_something_the_contract_does_not_name(self):
        """The dimension's whole point: if everything is handed over, nothing is discovered."""
        with contextlib.ExitStack() as stack:
            copy = self._mutated(
                stack, "retention-transitive-conflict",
                lambda m: m.update(reachable_from=["specs/CH-101/specification.md",
                                                   "specs/CH-101/design.md"]))
            with self.assertRaises(_scenario.ScenarioError) as caught:
                _scenario.load(copy)
            self.assertIn("nothing has to be discovered", str(caught.exception))

    def test_competing_concerns_requires_actual_competing_concerns(self):
        with contextlib.ExitStack() as stack:
            copy = self._mutated(
                stack, "crowded-availability-review",
                lambda m: m.update(distractors=m["distractors"][:1]))
            with self.assertRaises(_scenario.ScenarioError):
                _scenario.load(copy)

    def test_a_distractor_that_restates_the_property_is_rejected(self):
        """Otherwise a negative control built from it would grade as a detection."""
        with contextlib.ExitStack() as stack:
            copy = self._mutated(
                stack, "crowded-availability-review",
                lambda m: m.update(distractors=[m["property"], m["distractors"][0]]))
            with self.assertRaises(_scenario.ScenarioError) as caught:
                _scenario.load(copy)
            self.assertIn("restates planted property", str(caught.exception))

    def test_reachable_material_must_actually_be_in_the_fixture(self):
        with contextlib.ExitStack() as stack:
            copy = self._mutated(stack, "freshness-batching-conflict",
                                 lambda m: m.update(reachable_from=["specs/nope.md"]))
            with self.assertRaises(_scenario.ScenarioError):
                _scenario.load(copy)

    def test_every_calibration_candidate_declares_a_checked_dimension(self):
        for scenario in _scenario.discover(SCENARIOS):
            if scenario["id"] in self.V1_IDENTITIES:
                continue
            with self.subTest(scenario=scenario["id"]):
                self.assertTrue(scenario["dimensions"],
                                "a calibration candidate must declare what makes it hard")
                vocabulary = (_scenario.DIFFICULTY_DIMENSIONS
                              if scenario["shape"] == _scenario.SINGLE
                              else _scenario.PROPERTY_DIMENSIONS)
                self.assertLessEqual(set(scenario["dimensions"]), vocabulary)

    def test_the_suite_exercises_more_than_one_reasoning_structure(self):
        declared = {d for s in _scenario.discover(SCENARIOS) for d in s["dimensions"]}
        self.assertGreaterEqual(len(declared), 2, "one dimension is not a calibration suite")

    def test_dependency_distance_scenarios_put_material_outside_the_contract(self):
        """The mechanical expression of 'Proofbound is on the causal path'."""
        for scenario in _scenario.discover(SCENARIOS):
            if _scenario.DEPENDENCY_DISTANCE not in scenario["dimensions"]:
                continue
            with self.subTest(scenario=scenario["id"]):
                contract = Path(scenario["contract"]).read_text(encoding="utf-8")
                unnamed = [r for r in scenario["reachable_from"] if r not in contract]
                self.assertTrue(unnamed, "nothing has to be discovered")


class ComparisonTest(unittest.TestCase):
    """Comparison reports what differs. It never decides who won."""

    maxDiff = None

    def summary(self, *, model="m/a", detected=5, valid=5, sha="deadbeef", ident="i1",
                kind="capability", scenario_id="s1", harness_version="1.0.0"):
        return {
            "format": _summary.SUMMARY_FORMAT, "recorded_at": "2026-01-01T00:00:00+00:00",
            "system": {"proofbound_sha": sha, "harness": "opencode-cli",
                       "harness_version": harness_version, "model": model,
                       "grader_model": "g/x", "role": "spec-reflector", "python": "3.14"},
            "scenarios": [{"id": scenario_id, "identity": ident, "kind": kind,
                           "counts": {"attempted": valid, "valid": valid,
                                      "setup_failures": 0, "harness_failures": 0,
                                      "mechanical_ok": valid,
                                      "semantic_detected": detected,
                                      "semantic_not_detected": valid - detected,
                                      "grading_unavailable": 0},
                           "resources": {"median_elapsed_seconds": 10.0}}],
            "totals": {},
        }

    def test_changing_only_the_model_is_a_controlled_comparison(self):
        got = _compare.compare(self.summary(model="m/a"), self.summary(model="m/b"))
        self.assertEqual(got["differing_fields"], ["model"])
        self.assertTrue(got["controlled"])

    def test_changing_more_than_the_model_is_not_controlled(self):
        got = _compare.compare(self.summary(model="m/a"),
                               self.summary(model="m/b", sha="cafe"))
        self.assertFalse(got["controlled"])
        self.assertIn("proofbound_sha", got["differing_fields"])
        self.assertIn("more than the model differs", _compare.render(got))

    def test_a_different_harness_version_breaks_the_comparison(self):
        got = _compare.compare(self.summary(model="m/a"),
                               self.summary(model="m/b", harness_version="2.0.0"))
        self.assertFalse(got["controlled"])
        self.assertIn("harness_version", got["differing_fields"])

    def test_a_field_neither_run_recorded_is_unverified_not_agreement(self):
        a, b = self.summary(model="m/a"), self.summary(model="m/b")
        del a["system"]["harness_version"], b["system"]["harness_version"]
        got = _compare.compare(a, b)
        self.assertIn("harness_version", got["unverified_fields"])
        self.assertNotIn("harness_version", got["differing_fields"])
        self.assertIn("unverified", _compare.render(got))

    def test_scenarios_are_matched_by_identity_not_by_name(self):
        """Same id, different content, is not the same measurement."""
        got = _compare.compare(self.summary(model="m/a", ident="i1"),
                               self.summary(model="m/b", ident="i1", scenario_id="renamed"))
        self.assertEqual(len(got["scenarios"]), 1)
        with self.assertRaises(_compare.ComparisonError):
            _compare.compare(self.summary(ident="i1"), self.summary(ident="i2"))

    def test_a_differing_scenario_population_is_surfaced_and_not_controlled(self):
        a = self.summary(model="m/a", ident="i1")
        b = self.summary(model="m/b", ident="i1")
        b["scenarios"].append({**a["scenarios"][0], "id": "extra", "identity": "i2"})
        got = _compare.compare(a, b)
        self.assertFalse(got["populations_match"])
        self.assertFalse(got["controlled"])
        self.assertEqual(got["only_in_b"], ["extra"])
        self.assertIn("did not evaluate the same scenario set", _compare.render(got))

    def test_a_provider_change_riding_along_with_the_model_is_named(self):
        got = _compare.compare(self.summary(model="alpha/x"), self.summary(model="beta/y"))
        self.assertFalse(got["provider"]["same"])
        self.assertIn("provider", _compare.render(got))

    def test_results_are_stratified_so_easy_anchors_cannot_dominate(self):
        a = self.summary(model="m/a", ident="i1", kind="capability", detected=1)
        b = self.summary(model="m/b", ident="i1", kind="capability", detected=5)
        for summary, det in ((a, 5), (b, 5)):
            summary["scenarios"].append({**summary["scenarios"][0], "id": "anchor",
                                         "identity": "i2", "kind": "regression",
                                         "counts": {**summary["scenarios"][0]["counts"],
                                                    "semantic_detected": det,
                                                    "semantic_not_detected": 5 - det}})
        got = _compare.compare(a, b)
        self.assertEqual(got["strata"]["capability"]["a"]["semantic_detected"], 1)
        self.assertEqual(got["strata"]["capability"]["b"]["semantic_detected"], 5)
        self.assertEqual(got["strata"]["regression"]["a"]["semantic_detected"], 5)
        self.assertIn("stratum", _compare.render(got))

    def test_comparison_never_names_a_winner(self):
        got = _compare.compare(self.summary(model="m/a", detected=0),
                               self.summary(model="m/b", detected=5))
        blob = json.dumps(got).lower() + _compare.render(got).lower()
        for forbidden in ("winner", "best_model", "recommended", "promote", "rank",
                          "score", "wins", "better"):
            self.assertNotIn(forbidden, blob, f"{forbidden!r} must not be protocol")
        self.assertIn("human judgement", _compare.render(got))

    def test_comparison_is_derived_and_writes_nothing(self):
        """The state test: everything here recomputes from the two named summaries."""
        source = inspect.getsource(_compare)
        for forbidden in ("write_text", "open(", "mkdir", "json.dump"):
            self.assertNotIn(forbidden, source, "a comparison must not persist anything")


class GraderBlindnessTest(unittest.TestCase):
    """A grader that knew which model wrote a report could rank rather than judge."""

    maxDiff = None

    def test_the_grading_prompt_carries_only_the_property_and_the_report(self):
        filled = _grade.GRADER_PROMPT.format(property="PROPERTY-TOKEN", report="REPORT-TOKEN")
        self.assertIn("PROPERTY-TOKEN", filled)
        self.assertIn("REPORT-TOKEN", filled)
        for leak in ("model", "provider", "proofbound", "baseline", "previous", "version"):
            self.assertNotIn(leak, filled.lower().replace("reviewer's report", ""),
                             f"grading prompt mentions {leak!r}")

    def test_the_grader_is_never_told_the_worker_model(self):
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, "DETECTED\n", "")

        scenario = _scenario.load(SCENARIOS / "retry-idempotency")
        trial = {"report": "The retry conflicts with the proposal.", "model": "secret/worker-model"}
        with unittest.mock.patch.object(_grade.subprocess, "run", fake_run), \
             unittest.mock.patch.object(_grade.shutil, "which", lambda x: "/bin/true"):
            got = _grade.semantic(trial, scenario, grader_model="grader/model")
        self.assertEqual(got["result"], _grade.DETECTED)
        self.assertNotIn("secret/worker-model", " ".join(seen["cmd"]))


MULTI = ["checkout-obligations", "session-lifecycle-obligations", "migration-obligations"]


class MultiPropertySchemaTest(unittest.TestCase):
    """A scenario declares one shape, and the shape it declares is the one that is checked."""

    maxDiff = None

    def scenario_copy(self, stack, name="checkout-obligations", mutate=None):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        copy = root / "copy"
        shutil.copytree(SCENARIOS / name, copy)
        manifest = json.loads((copy / "scenario.json").read_text())
        if mutate:
            mutate(manifest)
        (copy / "scenario.json").write_text(json.dumps(manifest), encoding="utf-8")
        return copy

    def test_the_shipped_multi_property_scenarios_load(self):
        for name in MULTI:
            with self.subTest(scenario=name):
                sc = _scenario.load(SCENARIOS / name)
                self.assertEqual(sc["shape"], _scenario.MULTI)
                self.assertEqual(len(sc["properties"]), 3)
                self.assertGreaterEqual(len(sc["distractors"]), len(sc["properties"]))
                self.assertGreaterEqual(len({p["dimension"] for p in sc["properties"]}), 2)

    # Distinct obligations, so the pool itself satisfies the shape rules under test: varied
    # dimensions, no textual restatement, and one that depends on unnamed material.
    POOL = [
        ("charged-twice", "direct",
         "Money leaves the shopper account a second time when a settled request repeats."),
        ("kept-past-the-limit", "dependency-distance",
         "Sensitive submissions linger far beyond the interval an accepted rule permits."),
        ("region-loss-stops-sales", "indirect-implication",
         "Nobody can complete a purchase while one datacentre is unreachable."),
        ("stale-price-served", "direct",
         "Shoppers see an amount that no longer matches what billing will take."),
        ("audit-trail-gap", "indirect-implication",
         "Reconstructing who approved a refund becomes impossible after compaction."),
    ]

    def test_property_count_is_bounded_on_both_sides(self):
        for count, ok in ((1, False), (2, True), (3, True), (4, True), (5, False)):
            with self.subTest(count=count), contextlib.ExitStack() as stack:
                def mutate(m, n=count):
                    policy = m["properties"][2]["reachable_from"]
                    named = m["properties"][0]["reachable_from"]
                    m["properties"] = [
                        {"id": pid, "dimension": dim, "statement": text,
                         "reachable_from": policy if dim == "dependency-distance" else named}
                        for pid, dim, text in self.POOL[:n]]
                    m["distractors"] = m["distractors"] * 3
                copy = self.scenario_copy(stack, mutate=mutate)
                if ok:
                    self.assertEqual(len(_scenario.load(copy)["properties"]), count)
                else:
                    with self.assertRaises(_scenario.ScenarioError):
                        _scenario.load(copy)

    def test_a_scenario_declares_one_shape_not_both(self):
        with contextlib.ExitStack() as stack:
            copy = self.scenario_copy(stack, mutate=lambda m: m.update(property="x" * 40))
            with self.assertRaises(_scenario.ScenarioError) as caught:
                _scenario.load(copy)
            self.assertIn("never both", str(caught.exception))

    def test_malformed_properties_fail_closed(self):
        cases = {
            "duplicate ids": lambda m: m["properties"].__setitem__(
                1, {**m["properties"][1], "id": m["properties"][0]["id"]}),
            "bad id": lambda m: m["properties"][0].update(id="Not Kebab"),
            "unknown dimension": lambda m: m["properties"][0].update(dimension="very-hard"),
            "missing statement": lambda m: m["properties"][0].pop("statement"),
            "unknown field": lambda m: m["properties"][0].update(weight=3),
            "thin statement": lambda m: m["properties"][0].update(statement="too short"),
            "not a list": lambda m: m.update(properties={"id": "x"}),
        }
        for label, mutate in cases.items():
            with self.subTest(case=label), contextlib.ExitStack() as stack:
                copy = self.scenario_copy(stack, mutate=mutate)
                with self.assertRaises(_scenario.ScenarioError):
                    _scenario.load(copy)

    def test_scenario_shape_constraints_are_enforced(self):
        cases = {
            "too few distractors": lambda m: m.update(distractors=m["distractors"][:2]),
            "one dimension only": lambda m: [p.update(dimension="direct")
                                             for p in m["properties"]],
            "nothing to discover": lambda m: [p.update(reachable_from=[])
                                              for p in m["properties"]],
        }
        for label, mutate in cases.items():
            with self.subTest(case=label), contextlib.ExitStack() as stack:
                copy = self.scenario_copy(stack, mutate=mutate)
                with self.assertRaises(_scenario.ScenarioError):
                    _scenario.load(copy)

    def test_properties_that_restate_each_other_are_rejected(self):
        """Three views of one reasoning chain measure one thing three times."""
        with contextlib.ExitStack() as stack:
            copy = self.scenario_copy(stack, mutate=lambda m: m["properties"][1].update(
                statement=m["properties"][0]["statement"]))
            with self.assertRaises(_scenario.ScenarioError) as caught:
                _scenario.load(copy)
            self.assertIn("restate", str(caught.exception))

    def test_every_property_is_leak_checked_not_just_the_first(self):
        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            copy = root / "copy"
            shutil.copytree(SCENARIOS / "checkout-obligations", copy)
            manifest = json.loads((copy / "scenario.json").read_text())
            leaked = manifest["properties"][2]["statement"]
            artifact = copy / "fixture" / manifest["artifact"]
            artifact.write_text(artifact.read_text() + "\n" + leaked + "\n", encoding="utf-8")
            with self.assertRaises(_scenario.ScenarioError) as caught:
                _scenario.load(copy)
            self.assertIn(manifest["properties"][2]["id"], str(caught.exception))


class MultiPropertyIdentityTest(unittest.TestCase):
    """Identity covers what defines the problem, in the shape the manifest declared."""

    maxDiff = None

    def mutated_identity(self, stack, mutate):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        copy = root / "copy"
        shutil.copytree(SCENARIOS / "checkout-obligations", copy)
        manifest = json.loads((copy / "scenario.json").read_text())
        mutate(manifest)
        (copy / "scenario.json").write_text(json.dumps(manifest), encoding="utf-8")
        return _scenario.load(copy)["identity"]

    def setUp(self):
        self.base = _scenario.load(SCENARIOS / "checkout-obligations")["identity"]

    def test_an_unchanged_copy_keeps_its_identity(self):
        with contextlib.ExitStack() as stack:
            self.assertEqual(self.mutated_identity(stack, lambda m: None), self.base)

    def test_the_property_set_is_part_of_identity(self):
        cases = {
            "statement": lambda m: m["properties"][0].update(
                statement=m["properties"][0]["statement"] + " And one more consequence."),
            "id": lambda m: m["properties"][0].update(id="renamed-obligation"),
            "dimension": lambda m: m["properties"][1].update(dimension="direct"),
            "reachable_from": lambda m: m["properties"][0].update(reachable_from=[]),
            "removed": lambda m: m.update(
                properties=[m["properties"][0], m["properties"][2]]),
            "reordered": lambda m: m.update(properties=list(reversed(m["properties"]))),
        }
        for label, mutate in cases.items():
            with self.subTest(change=label), contextlib.ExitStack() as stack:
                self.assertNotEqual(self.mutated_identity(stack, mutate), self.base,
                                    f"changing {label} must change identity")

    def test_evaluation_configuration_is_not_part_of_identity(self):
        for label, mutate in {
            "distractors": lambda m: m.update(distractors=m["distractors"] + [
                "An extra defensible concern recorded for grading purposes only."]),
            "notes": lambda m: m.update(notes="Calibration bookkeeping, invisible to the worker."),
        }.items():
            with self.subTest(change=label), contextlib.ExitStack() as stack:
                self.assertEqual(self.mutated_identity(stack, mutate), self.base)

    def test_fixture_bytes_still_change_identity(self):
        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            copy = root / "copy"
            shutil.copytree(SCENARIOS / "checkout-obligations", copy)
            art = copy / "fixture" / "specs" / "CH-201" / "design.md"
            art.write_text(art.read_text() + "\n## Notes\nAn extra section.\n", encoding="utf-8")
            self.assertNotEqual(_scenario.load(copy)["identity"], self.base)


class PerPropertyGradingTest(unittest.TestCase):
    """One call per property, and each call sees only its own property."""

    maxDiff = None

    @contextlib.contextmanager
    def fake_grader(self, verdicts):
        """Answer each grader call by matching the property statement it was handed."""
        seen = []

        def fake_run(cmd, **kwargs):
            prompt = cmd[-1]
            seen.append(prompt)
            for statement, verdict in verdicts.items():
                if statement in prompt:
                    return subprocess.CompletedProcess(cmd, 0, verdict + "\n", "")
            return subprocess.CompletedProcess(cmd, 1, "", "no matching property")

        with unittest.mock.patch.object(_grade.subprocess, "run", fake_run), \
             unittest.mock.patch.object(_grade.shutil, "which", lambda x: "/bin/true"):
            yield seen

    def test_one_independent_call_per_property(self):
        scenario = _scenario.load(SCENARIOS / "checkout-obligations")
        verdicts = {p["statement"]: "DETECTED" for p in scenario["properties"]}
        with self.fake_grader(verdicts) as seen:
            got = _grade.semantic({"report": "A reflection.", "model": "secret/worker"},
                                  scenario, grader_model="g/x")
        self.assertEqual(len(seen), 3, "one call per planted obligation")
        self.assertEqual(got["result"], _grade.DETECTED)
        self.assertEqual(sorted(got["properties"]), sorted(p["id"] for p in scenario["properties"]))

    def test_each_call_is_blind_to_the_other_properties_and_to_the_worker(self):
        scenario = _scenario.load(SCENARIOS / "checkout-obligations")
        statements = [p["statement"] for p in scenario["properties"]]
        verdicts = {st: "DETECTED" for st in statements}
        with self.fake_grader(verdicts) as seen:
            _grade.semantic({"report": "A reflection.", "model": "secret/worker-model"},
                            scenario, grader_model="g/x")
        for prompt in seen:
            present = [st for st in statements if st in prompt]
            self.assertEqual(len(present), 1, "a grader call saw more than one property")
            self.assertNotIn("secret/worker-model", prompt)
            self.assertNotIn("DETECTED\n", prompt.replace(_grade.GRADER_PROMPT[:40], ""))

    def test_a_report_can_find_two_obligations_and_still_miss_the_third(self):
        """The case a multi-property suite exists to observe."""
        scenario = _scenario.load(SCENARIOS / "checkout-obligations")
        props = scenario["properties"]
        verdicts = {props[0]["statement"]: "DETECTED",
                    props[1]["statement"]: "DETECTED",
                    props[2]["statement"]: "NOT_DETECTED"}
        with self.fake_grader(verdicts):
            got = _grade.semantic({"report": "Two findings."}, scenario, grader_model="g/x")
        self.assertEqual(got["result"], _grade.NOT_DETECTED)
        self.assertEqual(got["properties"][props[0]["id"]]["result"], _grade.DETECTED)
        self.assertEqual(got["properties"][props[2]["id"]]["result"], _grade.NOT_DETECTED)

    def test_one_ungradeable_property_makes_the_trial_ungraded_not_incomplete(self):
        scenario = _scenario.load(SCENARIOS / "checkout-obligations")
        props = scenario["properties"]
        verdicts = {props[0]["statement"]: "DETECTED", props[1]["statement"]: "DETECTED"}
        with self.fake_grader(verdicts):
            got = _grade.semantic({"report": "x"}, scenario, grader_model="g/x")
        self.assertEqual(got["result"], _grade.UNAVAILABLE)

    def test_trial_verdict_is_arithmetic_and_matches_k1_history_exactly(self):
        d, n, u = _grade.DETECTED, _grade.NOT_DETECTED, _grade.UNAVAILABLE
        self.assertEqual(_grade.trial_verdict([d]), d)
        self.assertEqual(_grade.trial_verdict([n]), n)
        self.assertEqual(_grade.trial_verdict([u]), u)
        self.assertEqual(_grade.trial_verdict([d, d, d]), d)
        self.assertEqual(_grade.trial_verdict([d, n, d]), n)
        self.assertEqual(_grade.trial_verdict([d, d, u]), u)
        self.assertEqual(_grade.trial_verdict([]), u)

    def test_a_single_property_scenario_grades_exactly_as_it_used_to(self):
        scenario = _scenario.load(SCENARIOS / "retry-idempotency")
        with self.fake_grader({scenario["properties"][0]["statement"]: "DETECTED"}) as seen:
            got = _grade.semantic({"report": "x"}, scenario, grader_model="g/x")
        self.assertEqual(len(seen), 1)
        self.assertEqual(got["result"], _grade.DETECTED)
        self.assertIn("reason", got)


class PropertyMetricsTest(unittest.TestCase):
    """Per-obligation counts sit under the trial counts; neither replaces the other."""

    maxDiff = None

    def scenario(self):
        return _scenario.load(SCENARIOS / "checkout-obligations")

    def graded(self, scenario, vectors, validity=_trial.VALID):
        out = []
        for vector in vectors:
            props = {p["id"]: {"result": r} for p, r in zip(scenario["properties"], vector)}
            out.append({
                "trial": {"validity": validity, "prompt_bytes": 1, "context_bytes": 1,
                          "elapsed_seconds": 1.0},
                "mechanical": {"ok": True},
                "semantic": {"result": _grade.trial_verdict(list(vector)), "properties": props},
            })
        return out

    def test_per_property_counts_expose_where_the_reflector_is_weak(self):
        scenario = self.scenario()
        d, n = _grade.DETECTED, _grade.NOT_DETECTED
        graded = self.graded(scenario, [(d, d, n), (d, d, n), (d, d, d)])
        summary = _summary.summarize([{"scenario": scenario, "graded": graded}],
                                     system={"model": "m"})
        props = summary["scenarios"][0]["properties"]
        ids = [p["id"] for p in scenario["properties"]]
        self.assertEqual(props[ids[0]]["detected"], 3)
        self.assertEqual(props[ids[2]]["detected"], 1)
        self.assertEqual(props[ids[2]]["gradeable"], 3)
        # Complete-trial reliability is a different question from per-property completeness.
        self.assertEqual(summary["scenarios"][0]["counts"]["semantic_detected"], 1)
        rendered = _summary.render(summary)
        self.assertIn(ids[2], rendered, "the breakdown must be rendered, not just the total")
        self.assertIn("obligations", rendered)

    def test_an_invalid_trial_is_not_three_property_misses(self):
        scenario = self.scenario()
        graded = self.graded(scenario, [(_grade.DETECTED,) * 3], validity=_trial.SETUP_FAILURE)
        summary = _summary.summarize([{"scenario": scenario, "graded": graded}],
                                     system={"model": "m"})
        entry = summary["scenarios"][0]
        self.assertEqual(entry["counts"]["setup_failures"], 1)
        for counts in entry["properties"].values():
            self.assertEqual(counts["gradeable"], 0)
            self.assertEqual(counts["not_detected"], 0)

    def test_a_single_property_scenario_reports_one_obligation(self):
        scenario = _scenario.load(SCENARIOS / "retry-idempotency")
        graded = self.graded(scenario, [(_grade.DETECTED,), (_grade.NOT_DETECTED,)])
        summary = _summary.summarize([{"scenario": scenario, "graded": graded}],
                                     system={"model": "m"})
        entry = summary["scenarios"][0]
        self.assertEqual(list(entry["properties"]), ["primary"])
        self.assertEqual(entry["counts"]["semantic_detected"], 1)
        self.assertEqual(entry["counts"]["semantic_not_detected"], 1)

    def test_historical_summaries_still_load_and_render(self):
        for name in ("eval-v1.json", "calibration-screening-reference.json"):
            path = ROOT / "evals" / "results" / name
            if not path.is_file():
                continue
            with self.subTest(summary=name):
                summary = _summary.load(path)
                self.assertNotIn("properties", summary["scenarios"][0],
                                 "history must not be rewritten with synthesised properties")
                self.assertIn("complete", _summary.render(summary))


class PropertyComparisonTest(unittest.TestCase):
    """Comparison gains a per-obligation view and two effectiveness denominators."""

    maxDiff = None

    def summary(self, *, model, vectors):
        scenario = _scenario.load(SCENARIOS / "checkout-obligations")
        graded = PropertyMetricsTest().graded(scenario, vectors)
        return _summary.summarize([{"scenario": scenario, "graded": graded}],
                                  system={"proofbound_sha": "abc", "harness": "opencode-cli",
                                          "harness_version": "1.0.0", "model": model,
                                          "grader_model": "g/x", "role": "spec-reflector",
                                          "python": "3.14"})

    def test_the_per_property_breakdown_is_compared_and_rendered(self):
        d, n = _grade.DETECTED, _grade.NOT_DETECTED
        a = self.summary(model="p/a", vectors=[(d, d, n), (d, d, n), (d, d, n)])
        b = self.summary(model="p/b", vectors=[(d, d, d), (d, d, d), (d, d, d)])
        got = _compare.compare(a, b)
        self.assertTrue(got["controlled"])
        props = got["scenarios"][0]["properties"]
        self.assertEqual(len(props), 3)
        third = props[2]
        self.assertEqual(third["a"]["detected"], 0)
        self.assertEqual(third["b"]["detected"], 3)
        rendered = _compare.render(got)
        self.assertIn(third["id"], rendered)

    def test_both_effectiveness_views_are_reported(self):
        d = _grade.DETECTED
        a = self.summary(model="p/a", vectors=[(d, d, d)])
        b = self.summary(model="p/b", vectors=[(d, d, d)])
        rendered = _compare.render(_compare.compare(a, b))
        self.assertIn("end-to-end", rendered)
        self.assertIn("conditional", rendered)
        self.assertIn("attempted", rendered)

    def test_no_winner_appears_even_with_a_large_gap(self):
        d, n = _grade.DETECTED, _grade.NOT_DETECTED
        a = self.summary(model="p/a", vectors=[(n, n, n)])
        b = self.summary(model="p/b", vectors=[(d, d, d)])
        got = _compare.compare(a, b)
        blob = json.dumps(got).lower() + _compare.render(got).lower()
        for forbidden in ("winner", "best_model", "recommended", "promote", "score", "wins"):
            self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main()
