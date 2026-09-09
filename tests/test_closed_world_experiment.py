"""Deterministic tests for the closed-world multi-sample substrate.

The substrate's whole claim is that it measures each sample against a column declared before the
run, and never lets one sample stand in for another. These tests defend that: no sample lost to a
disagreeing sample, no missing measurement converted into a semantic one, no slot satisfied by the
wrong pressure or the wrong arm, no splicing across configurations, and no whole-report verdict
reconstructed anywhere.

Nothing here invokes a model.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "scripts"))

import _craft  # noqa: E402
import _experiment  # noqa: E402
import _grade  # noqa: E402
import _repeat  # noqa: E402
import pb_craft  # noqa: E402

CASE = ROOT / "evals" / "craft" / "notification-provider-boundary"


def valid_experiment(**over) -> dict:
    base = {
        "format": _experiment.FORMAT,
        "id": "example",
        "claim": "Supplying the accepted consequence increases independent discovery of P.",
        "measurand": "Per-sample discovery frequency of pressure P on each instance.",
        "baseline": "The untreated craft measuring context, unchanged.",
        "treatment": "Exactly one added accepted consequence in the measuring context.",
        "primary_comparison": "Within-instance shift in discovery frequency, baseline vs treated.",
        "falsifier": "Discovery frequency does not shift beyond same-condition dispersion.",
        "adoption_rule": "Adopt only the local claim, and only if no guardrail regresses.",
        "frozen": ["implementation evidence", "reflector model", "grader contract"],
        "guardrails": ["false pressure on sound architectures must not rise"],
        "invalid_if": ["the treatment states the expected answer"],
        "samples_per_cell": 2,
        "instances": ["inst-a", "inst-b"],
        "pressures": [{"id": "p1", "statement": "The planted problem, stated at length enough."},
                      {"id": "p2", "statement": "A second planted problem, also long enough."}],
        "arms": [{"id": "baseline", "treatment": None}, {"id": "treated", "treatment": "x.md"}],
    }
    base.update(over)
    return base


def write(tmp: Path, experiment: dict) -> Path:
    path = tmp / "experiment.json"
    path.write_text(json.dumps(experiment), encoding="utf-8")
    return path


class ManifestValidationTest(unittest.TestCase):
    """Python checks the shape of an experiment. It never judges whether it is a good one."""

    maxDiff = None

    def test_a_well_formed_experiment_loads(self):
        with tempfile.TemporaryDirectory() as td:
            got = _experiment.load(write(Path(td), valid_experiment()))
            self.assertEqual(got["id"], "example")

    def test_every_pre_registered_field_is_required(self):
        for field in _experiment.REQUIRED_TEXT:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                bad = valid_experiment(**{field: "short"})
                with self.assertRaises(_experiment.ExperimentError):
                    _experiment.load(write(Path(td), bad))
        for field in _experiment.REQUIRED_LIST:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                with self.assertRaises(_experiment.ExperimentError):
                    _experiment.load(write(Path(td), valid_experiment(**{field: []})))

    def test_a_malformed_sample_budget_is_refused(self):
        for budget in (0, -1, "many", 1.5, None):
            with self.subTest(budget=budget), tempfile.TemporaryDirectory() as td:
                with self.assertRaises(_experiment.ExperimentError):
                    _experiment.load(write(Path(td), valid_experiment(samples_per_cell=budget)))

    def test_duplicate_or_unnamed_columns_are_refused(self):
        cases = [
            {"pressures": [{"id": "p1", "statement": "x" * 30},
                           {"id": "p1", "statement": "y" * 30}]},
            {"pressures": []},
            {"pressures": [{"id": "p|1", "statement": "x" * 30}]},
            {"pressures": [{"id": "p1", "statement": "too short"}]},
            {"instances": ["a", "a"]},
            {"instances": []},
            {"arms": [{"id": "a"}, {"id": "a"}]},
            {"arms": []},
        ]
        for over in cases:
            with self.subTest(over=str(over)[:60]), tempfile.TemporaryDirectory() as td:
                with self.assertRaises(_experiment.ExperimentError):
                    _experiment.load(write(Path(td), valid_experiment(**over)))

    def test_a_treatment_arm_without_its_baseline_is_refused(self):
        """A treatment measured alone is not a comparison, however many samples it has."""
        with tempfile.TemporaryDirectory() as td:
            bad = valid_experiment(arms=[{"id": "treated", "treatment": "x.md"},
                                         {"id": "also-treated", "treatment": "y.md"}])
            with self.assertRaises(_experiment.ExperimentError) as caught:
                _experiment.load(write(Path(td), bad))
            self.assertIn("baseline", str(caught.exception))

    def test_a_single_arm_measurement_is_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            got = _experiment.load(write(Path(td), valid_experiment(
                arms=[{"id": "baseline", "treatment": None}])))
            self.assertEqual(len(got["arms"]), 1)


class SlotAllocationTest(unittest.TestCase):
    """Which cell is measured next must never depend on what earlier cells returned."""

    maxDiff = None

    def setUp(self):
        self.experiment = valid_experiment()

    def test_slots_are_preallocated_and_complete(self):
        slots = _experiment.slots(self.experiment)
        self.assertEqual(len(slots), 2 * 2 * 2)  # samples x instances x arms
        self.assertEqual(len({s["reflection_slot"] for s in slots}), len(slots))

    def test_slot_allocation_is_deterministic(self):
        self.assertEqual(_experiment.slots(self.experiment),
                         _experiment.slots(copy.deepcopy(self.experiment)))

    def test_no_arm_holds_a_fixed_position(self):
        """Baseline first every time would let provider drift line up with the comparison."""
        firsts = set()
        slots = _experiment.slots(self.experiment)
        for i in range(0, len(slots), len(self.experiment["arms"])):
            firsts.add(slots[i]["arm"])
        self.assertEqual(firsts, {"baseline", "treated"})

    def test_a_sample_cannot_satisfy_another_pressures_slot(self):
        slot = _experiment.slots(self.experiment)[0]
        rows = _experiment.measurement_rows(self.experiment, slot)
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["item"], rows[1]["item"])
        for row in rows:
            self.assertEqual(_experiment.split_slot(row["item"])[0], slot["instance"])

    def test_a_sample_cannot_satisfy_another_arms_slot(self):
        by_arm = {}
        for slot in _experiment.slots(self.experiment):
            if slot["instance"] == "inst-a" and slot["sample"] == 1:
                by_arm[slot["arm"]] = _experiment.measurement_rows(self.experiment, slot)
        self.assertEqual(len(by_arm), 2)
        baseline = {r["item"] for r in by_arm["baseline"]}
        treated = {r["item"] for r in by_arm["treated"]}
        self.assertFalse(baseline & treated)

    def test_every_declared_cell_is_addressable(self):
        cells = set(_experiment.cells(self.experiment))
        produced = {r["item"] for s in _experiment.slots(self.experiment)
                    for r in _experiment.measurement_rows(self.experiment, s)}
        self.assertEqual(cells, produced)


class MeasurementSemanticsTest(unittest.TestCase):
    """The distribution is the result. Nothing collapses it."""

    maxDiff = None

    def test_a_minority_detection_survives_intact(self):
        rows = [{"item": "i|baseline|p1", "repeat": n, "status": _repeat.GRADED,
                 "outcome": _grade.NOT_DETECTED} for n in range(1, 6)]
        rows[2]["outcome"] = _grade.DETECTED
        got = _repeat.distribution(rows, "i|baseline|p1")
        self.assertEqual(got["counts"], {_grade.NOT_DETECTED: 4, _grade.DETECTED: 1})
        self.assertEqual(got["order"].count(_grade.DETECTED), 1)
        self.assertFalse(got["unanimous"])

    def test_no_sample_is_lost_because_another_disagrees(self):
        rows = [{"item": "c", "repeat": n, "status": _repeat.GRADED,
                 "outcome": _grade.DETECTED if n % 2 else _grade.NOT_DETECTED}
                for n in range(1, 11)]
        got = _repeat.distribution(rows, "c")
        self.assertEqual(got["graded"], 10)
        self.assertEqual(sum(got["counts"].values()), 10)

    def test_a_failed_sample_is_not_a_not_detected(self):
        rows = [
            {"item": "c", "repeat": 1, "status": _repeat.GRADED, "outcome": _grade.DETECTED},
            {"item": "c", "repeat": 2, "status": _repeat.PARSE_FAILURE, "outcome": None},
            {"item": "c", "repeat": 3, "status": _repeat.CALL_FAILURE, "outcome": None},
            {"item": "c", "repeat": 4, "status": _repeat.REFLECTION_FAILURE, "outcome": None},
        ]
        got = _repeat.distribution(rows, "c")
        self.assertEqual(got["counts"], {_grade.DETECTED: 1})
        self.assertNotIn(_grade.NOT_DETECTED, got["counts"])
        self.assertEqual((got["parse_failures"], got["call_failures"],
                          got["reflection_failures"]), (1, 1, 1))

    def test_derived_counts_do_not_depend_on_record_order(self):
        rows = [{"item": "c", "repeat": n, "status": _repeat.GRADED,
                 "outcome": _grade.DETECTED if n < 4 else _grade.NOT_DETECTED}
                for n in range(1, 7)]
        forward = _repeat.distribution(rows, "c")
        backward = _repeat.distribution(list(reversed(rows)), "c")
        self.assertEqual(forward["counts"], backward["counts"])
        self.assertEqual(forward["order"], backward["order"])

    def test_the_substrate_derives_no_verdict_and_no_score(self):
        rows = [{"item": "c", "repeat": n, "status": _repeat.GRADED,
                 "outcome": _grade.DETECTED} for n in range(1, 4)]
        blob = json.dumps(_repeat.distribution(rows, "c")).lower()
        for forbidden in ("verdict", "score", "confidence", "probability", "consensus",
                          "disputed", "winner", "better"):
            self.assertNotIn(forbidden, blob)

    def test_trial_verdict_keeps_its_original_meaning_and_is_not_used_here(self):
        """The legacy AND-collapse stays correct for its own consumer, and out of this path."""
        self.assertEqual(_grade.trial_verdict([_grade.DETECTED, _grade.DETECTED]),
                         _grade.DETECTED)
        self.assertEqual(_grade.trial_verdict([_grade.DETECTED, _grade.NOT_DETECTED]),
                         _grade.NOT_DETECTED)
        self.assertEqual(_grade.trial_verdict([_grade.DETECTED, _grade.UNAVAILABLE]),
                         _grade.UNAVAILABLE)
        source = (ROOT / "evals" / "pb_craft.py").read_text(encoding="utf-8")
        body = source.split("def cmd_sample", 1)[1].split("def parser", 1)[0]
        self.assertNotIn("trial_verdict", body)


class ConfigurationIdentityTest(unittest.TestCase):
    """A resume must continue the same experiment, never splice two."""

    maxDiff = None

    def setUp(self):
        self.system = {"reflector_model": "m", "grader_model": "g"}
        self.config = _experiment.configuration(valid_experiment(), self.system)

    def test_the_configuration_covers_what_the_comparison_depends_on(self):
        for key in ("experiment", "samples_per_cell", "instances", "pressures", "arms", "system"):
            self.assertIn(key, self.config)

    def test_changing_anything_load_bearing_changes_the_identity(self):
        base = _repeat.frozen_identity(self.config)
        variants = [
            _experiment.configuration(valid_experiment(samples_per_cell=3), self.system),
            _experiment.configuration(valid_experiment(instances=["inst-a"]), self.system),
            _experiment.configuration(
                valid_experiment(pressures=[{"id": "p1", "statement": "z" * 30}]), self.system),
            _experiment.configuration(valid_experiment(), {**self.system, "grader_model": "g2"}),
        ]
        for variant in variants:
            self.assertNotEqual(base, _repeat.frozen_identity(variant))

    def test_a_result_from_another_configuration_cannot_be_resumed_into_this_one(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "series.json"
            _repeat.write_series(out, self.config, [{"item": "i|baseline|p1", "repeat": 1}])
            self.assertEqual(len(_repeat.load_series(out, self.config)), 1)
            other = _experiment.configuration(valid_experiment(samples_per_cell=9), self.system)
            with self.assertRaises(_repeat.RepeatConfigError):
                _repeat.load_series(out, other)


class ExecutorTest(unittest.TestCase):
    """The executor is exercised without a model, because a run must not be needed to trust it."""

    maxDiff = None

    def _run(self, tmp: Path, experiment: dict, reflector, grader, *, out=None, raw=None):
        case = _craft.load(CASE)
        # Arms name their treatment by path; materialise any the caller left symbolic.
        experiment = copy.deepcopy(experiment)
        for arm in experiment["arms"]:
            if arm.get("treatment") and not Path(arm["treatment"]).is_file():
                path = tmp / Path(arm["treatment"]).name
                path.write_text("TREATMENT TEXT", encoding="utf-8")
                arm["treatment"] = str(path)
        instances = experiment["instances"]
        trials = [{"instance": name, "state": "state-a", "diff": f"diff for {name}",
                   "identity": case["states"][0]["identity"]} for name in instances]
        args = argparse.Namespace(
            case=CASE, experiment=write(tmp, experiment), evidence=tmp,
            reflector_model="m", grader_model="g",
            out=out or tmp / "durable.json", raw=raw or tmp / "raw.json")
        with unittest.mock.patch.object(pb_craft, "_retained_trials", lambda *a: trials), \
             unittest.mock.patch.object(pb_craft, "provider_available", lambda: (True, "")), \
             unittest.mock.patch.object(_craft, "reflect", reflector), \
             unittest.mock.patch.object(_grade, "grade_property", grader), \
             contextlib.redirect_stdout(io.StringIO()):
            pb_craft.cmd_sample(args)
        return json.loads((out or tmp / "durable.json").read_text()), \
            json.loads((raw or tmp / "raw.json").read_text())

    def test_every_declared_cell_is_measured_exactly_once(self):
        experiment = valid_experiment()
        with tempfile.TemporaryDirectory() as td:
            durable, raw = self._run(
                Path(td), experiment,
                lambda **kw: {"report": "a report"},
                lambda report, statement, **kw: {"result": _grade.DETECTED, "reason": ""})
        keys = [(m["item"], m["repeat"]) for m in durable["measurements"]]
        self.assertEqual(len(keys), len(set(keys)), "a slot was measured twice")
        self.assertEqual(len(keys), 2 * 2 * 2 * 2)  # samples x instances x arms x pressures
        self.assertEqual(len(raw["measurements"]), 2 * 2 * 2)

    def test_the_treatment_never_reaches_the_baseline_arm(self):
        seen = []
        experiment = valid_experiment()
        with tempfile.TemporaryDirectory() as td:
            def spy(**kw):
                seen.append(kw.get("treatment"))
                return {"report": "a report"}

            self._run(Path(td), experiment, spy,
                      lambda report, statement, **kw: {"result": _grade.DETECTED, "reason": ""})
        self.assertEqual(seen.count(None), 4, "a baseline sample received a treatment")
        self.assertEqual(seen.count("TREATMENT TEXT"), 4)

    def test_each_pressure_is_graded_against_its_own_statement(self):
        asked = []
        with tempfile.TemporaryDirectory() as td:
            self._run(Path(td), valid_experiment(),
                      lambda **kw: {"report": "a report"},
                      lambda report, statement, **kw: (
                          asked.append(statement) or {"result": _grade.DETECTED, "reason": ""}))
        statements = {p["statement"] for p in valid_experiment()["pressures"]}
        self.assertEqual(set(asked), statements)
        # samples x instances x arms x pressures: every cell asked its own question.
        self.assertEqual(len(asked), 16)
        self.assertEqual(asked.count(statements.pop()), 8)

    def test_a_reflection_failure_is_recorded_and_never_graded(self):
        with tempfile.TemporaryDirectory() as td:
            durable, _ = self._run(
                Path(td), valid_experiment(),
                lambda **kw: {"report": None, "reason": "call failed: boom"},
                lambda report, statement, **kw: self.fail("graded a missing report"))
        for m in durable["measurements"]:
            self.assertEqual(m["status"], _repeat.REFLECTION_FAILURE)
            self.assertIsNone(m["outcome"])

    def test_an_interrupted_run_resumes_into_the_same_structure(self):
        experiment = valid_experiment()
        calls = {"n": 0}

        def dies_partway(**kw):
            calls["n"] += 1
            if calls["n"] > 3:
                raise KeyboardInterrupt
            return {"report": f"report {calls['n']}"}

        grader = lambda report, statement, **kw: {"result": _grade.DETECTED, "reason": ""}
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            with self.assertRaises(KeyboardInterrupt):
                self._run(tmp, experiment, dies_partway, grader)
            partial = json.loads((tmp / "durable.json").read_text())
            self.assertTrue(partial["measurements"])
            self.assertLess(len(partial["measurements"]), 16)
            # Resume: the reflector answers again for the slots that never ran.
            durable, raw = self._run(tmp, experiment,
                                     lambda **kw: {"report": "resumed report"}, grader)
        keys = [(m["item"], m["repeat"]) for m in durable["measurements"]]
        self.assertEqual(sorted(keys), sorted(set(keys)))
        self.assertEqual(len(keys), 16)
        self.assertEqual(len(raw["measurements"]), 8)

    def test_a_completed_slot_is_never_re_measured_on_resume(self):
        experiment = valid_experiment()
        grader = lambda report, statement, **kw: {"result": _grade.DETECTED, "reason": ""}
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            first, _ = self._run(tmp, experiment, lambda **kw: {"report": "first"}, grader)
            second, raw = self._run(
                tmp, experiment,
                lambda **kw: self.fail("re-reflected a completed slot"), grader)
        self.assertEqual(first["measurements"], second["measurements"])
        self.assertTrue(all(r["report"] == "first" for r in raw["measurements"]))

    def test_the_durable_record_keeps_hashes_and_not_report_text(self):
        with tempfile.TemporaryDirectory() as td:
            durable, raw = self._run(
                Path(td), valid_experiment(),
                lambda **kw: {"report": "sensitive prose"},
                lambda report, statement, **kw: {"result": _grade.DETECTED, "reason": ""})
        self.assertNotIn("sensitive prose", json.dumps(durable))
        self.assertIn("sensitive prose", json.dumps(raw))
        for m in durable["measurements"]:
            self.assertEqual(len(m["report_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
