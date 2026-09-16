#!/usr/bin/env python3
"""The committed path that would execute `MLR-eventbus-b1-preregistration.md`, checked.

The defect these exist for was not subtle and was not caught by 981 passing tests: `grade` named
fixture A's oracle, contract and vendored package directly while everything below it had already
been parameterised, so grading fixture B raised inside a blanket `except` and every slot would have
come back an infrastructure failure. A frozen experiment that cannot be executed by the repository
is not frozen, it is stranded.

Two rules shape what is tested here. **Orchestration is tested with controlled attempts**, never
with a provider: a callable stands in for the bounded attempt and returns whatever failure the rule
under test is about. And **a deterministic test is not a field qualification** — nothing below
establishes that the instrument measures what it claims, only that the procedure the preregistration
describes is the procedure this code runs.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import _mlr            # noqa: E402
import _mlr_boundary   # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _host_serial  # noqa: E402
import _mlr_run        # noqa: E402
import _mlr_series     # noqa: E402
import _semantic_view  # noqa: E402
import _repeat         # noqa: E402
import pb_mlr          # noqa: E402

A, B = _mlr.OBJECTSTORE, _mlr.EVENTBUS
REQUIRED = pb_mlr.B1["executor_sha256"]


class FixtureIdentityTest(unittest.TestCase):
    """Each fixture answers for itself, and an unknown root is refused rather than substituted."""

    maxDiff = None

    def test_each_fixture_names_its_own_oracle_contract_and_package(self):
        self.assertEqual(A.oracle, "external_test_v2.py")
        self.assertEqual(B.oracle, "external_test.py")
        self.assertNotEqual(A.contract, B.contract)
        self.assertNotEqual(A.package, B.package)
        for spec in _mlr.FIXTURES:
            self.assertTrue(spec.gate.is_file(), f"{spec.package} ships its oracle")
            self.assertTrue(spec.task.is_file(), f"{spec.package} ships its task")
            self.assertTrue((spec.root / "base" / spec.contract).is_file())

    def test_omitting_the_fixture_still_means_the_original_one(self):
        """Legitimate historical behaviour: every signature defaulted to it and records mean it."""
        self.assertIs(_mlr.fixture_for(), A)
        self.assertIs(_mlr.fixture_for(None), A)
        self.assertIs(_mlr.fixture_for(A.root), A)
        self.assertIs(_mlr.fixture_for(B.root), B)
        self.assertIs(_mlr.fixture_for(B), B)

    def test_naming_a_root_that_is_not_a_fixture_is_refused_not_substituted(self):
        """The silent fallback would have labelled one fixture's data with another's identity."""
        tmp = Path(tempfile.mkdtemp(prefix="pb-b1-unknown-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        with self.assertRaises(_mlr.FixtureError) as caught:
            _mlr.fixture_for(tmp)
        self.assertIn("not a known MLR fixture root", str(caught.exception))

    def test_a_build_carries_the_fixture_it_was_built_from(self):
        for spec in _mlr.FIXTURES:
            with self.subTest(fixture=spec.package):
                with _mlr.materialised(_mlr.CONTRACT, fixture=spec.root) as built:
                    self.assertEqual(Path(built["fixture"]).resolve(), spec.root.resolve())
                    self.assertEqual(built["package"], spec.package)
                    self.assertIs(_mlr.fixture_for(built["fixture"]), spec)

    def test_a_build_from_before_there_was_a_second_fixture_still_reads_as_objectstore(self):
        with _mlr.materialised(_mlr.CONTRACT) as built:
            legacy = {k: v for k, v in built.items() if k not in ("fixture", "package", "vendored")}
            self.assertIs(_mlr.fixture_for(legacy.get("fixture")), A)


class GradingTest(unittest.TestCase):
    """The demonstrated defect, and the behaviour that replaces it."""

    maxDiff = None

    def grade(self, arm, *, fixture, realization=None):
        tmp = Path(tempfile.mkdtemp(prefix="pb-b1-grade-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        built = _mlr.materialise(arm, tmp / "arm", fixture=fixture)
        if realization is not None:
            shutil.copyfile(realization, Path(built["workspace"]) / "app" / "api.py")
        return _mlr_run.grade(built, tmp)

    def test_each_fixture_is_graded_by_its_own_oracle(self):
        self.assertEqual(self.grade(_mlr.CONTRACT, fixture=A.root)["oracle"], A.oracle)
        self.assertEqual(self.grade(_mlr.CONTRACT, fixture=B.root)["oracle"], B.oracle)

    def test_known_correct_fixture_b_work_passes_in_both_arms(self):
        valid = sorted((B.root / "realizations" / "valid").glob("*.py"))
        self.assertGreaterEqual(len(valid), 2, "one valid shape proves nothing about shape")
        for arm in _mlr.ARMS:
            for realization in valid:
                with self.subTest(arm=arm, realization=realization.stem):
                    outcome = self.grade(arm, fixture=B.root, realization=realization)
                    self.assertTrue(outcome["correct"], outcome["gate_output"][-400:])
                    self.assertTrue(outcome["gate_passed"])
                    self.assertTrue(outcome["regression_passed"])

    def test_a_meaningfully_wrong_fixture_b_implementation_fails_its_product_oracle(self):
        invalid = sorted((B.root / "realizations" / "invalid").glob("*.py"))
        self.assertGreaterEqual(len(invalid), 3)
        for realization in invalid:
            with self.subTest(realization=realization.stem):
                outcome = self.grade(_mlr.CONTRACT, fixture=B.root, realization=realization)
                self.assertFalse(outcome["correct"], f"{realization.stem} is wrong and passed")
                self.assertFalse(outcome["gate_passed"])

    def test_the_unfixed_fixture_b_is_not_already_correct(self):
        """If the task were already done, the experiment would measure nothing."""
        outcome = self.grade(_mlr.FULL, fixture=B.root)
        self.assertFalse(outcome["correct"])
        self.assertTrue(outcome["regression_passed"], "the shipped suite passes before the task")

    def test_boundary_evidence_is_not_a_spurious_finding_on_the_second_fixture(self):
        """`contract_unchanged` and `vendored_unchanged` must compare the fixture's own paths.

        Reading fixture A's `storage-contract.md` against fixture B's workspace raised; reading
        fixture A's vendored package name would have reported an untouched tree as moved. Both are
        recorded as boundary evidence, so a false one is a false finding about the treatment.
        """
        for arm in _mlr.ARMS:
            with self.subTest(arm=arm):
                outcome = self.grade(arm, fixture=B.root)
                self.assertTrue(outcome["contract_unchanged"])
                self.assertTrue(outcome["vendored_unchanged"])
                self.assertTrue(outcome["runtime_unchanged"])


class ConfigurationTest(unittest.TestCase):
    """The resolved configuration must be the fixture the frozen stack names."""

    maxDiff = None

    def test_the_configuration_resolves_the_selected_fixture(self):
        b = pb_mlr.configuration(model="m", samples=6, arms=list(_mlr.ARMS), fixture=B.root)
        self.assertTrue(b["source_digest"].startswith(pb_mlr.B1["source_digest"]))
        self.assertTrue(b["task_sha256"].startswith(pb_mlr.B1["task_sha256"]))
        self.assertTrue(b["contract_sha256"].startswith(pb_mlr.B1["contract_sha256"]))
        self.assertTrue(b["gate_sha256"].startswith(pb_mlr.B1["gate_sha256"]))
        self.assertEqual(b["oracle"], B.oracle)

    def test_omitting_the_fixture_reproduces_the_original_configuration_exactly(self):
        """Adding a parameter must not move the frozen identity of an objectstore series."""
        omitted = pb_mlr.configuration(model="m", samples=6, arms=list(_mlr.ARMS))
        explicit = pb_mlr.configuration(model="m", samples=6, arms=list(_mlr.ARMS),
                                        fixture=A.root)
        self.assertEqual(omitted, explicit)
        self.assertNotIn("fixture", omitted,
                         "the five digests already distinguish the fixtures; a sixth name for the "
                         "same fact would be persistent state for a derived one (P3)")

    def test_the_two_fixtures_are_never_poolable_or_resumable_into_one_another(self):
        a = pb_mlr.configuration(model="m", samples=6, arms=list(_mlr.ARMS), fixture=A.root)
        b = pb_mlr.configuration(model="m", samples=6, arms=list(_mlr.ARMS), fixture=B.root)
        self.assertNotEqual(_repeat.frozen_identity(a), _repeat.frozen_identity(b))

    def test_the_b1_configuration_is_the_frozen_identity_and_the_frozen_fixture(self):
        config = pb_mlr.b1_configuration()
        self.assertEqual(config["experiment"], pb_mlr.B1["experiment"])
        self.assertEqual(config["model"], pb_mlr.B1["model"])
        self.assertEqual(config["variant"], pb_mlr.B1["variant"])
        self.assertEqual(config["samples_per_arm"], 6)
        self.assertEqual(config["telemetry_version"], pb_mlr.B1["telemetry_version"])
        self.assertEqual(config["profile_version"], pb_mlr.B1["profile_version"])
        self.assertEqual(config["price_id"], pb_mlr.B1["price_id"])
        self.assertEqual(_mlr_series.config_fixture(config, pb_mlr.B1).resolve(),
                         B.root.resolve())

    def test_an_eventbus_identifier_over_objectstore_data_is_refused(self):
        """The mislabelling this milestone exists to make impossible."""
        wrong = pb_mlr.configuration(model=pb_mlr.B1["model"], samples=6, arms=list(_mlr.ARMS),
                                     variant=pb_mlr.B1["variant"],
                                     revision=pb_mlr.B1["revision"], fixture=A.root)
        self.assertEqual(wrong["experiment"], pb_mlr.B1["experiment"],
                         "the name alone cannot tell the fixtures apart — which is the hazard")
        with self.assertRaises(_mlr_series.SeriesRefused) as caught:
            _mlr_series.config_fixture(wrong, pb_mlr.B1)
        self.assertIn("would describe another fixture's data", str(caught.exception))


class ExecutorEligibilityTest(unittest.TestCase):
    """Absent, matching and mismatching — with controlled inputs, so any platform can run it."""

    maxDiff = None

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-b1-exec-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def executor(self, payload: bytes) -> Path:
        path = self.tmp / f"opencode-{len(payload)}"
        path.write_bytes(payload)
        return path

    def test_an_absent_executor_is_not_eligible(self):
        for candidate in (None, self.tmp / "nowhere"):
            with self.subTest(candidate=candidate):
                verdict = _mlr_series.executor_eligibility(candidate, required_sha256=REQUIRED)
                self.assertEqual(verdict["status"], "absent")
                self.assertFalse(verdict["eligible"])

    def test_a_matching_executor_is_eligible(self):
        payload = b"pretend-executor"
        import hashlib
        digest = hashlib.sha256(payload).hexdigest()
        path = self.executor(payload)
        verdict = _mlr_series.executor_eligibility(path, required_sha256=digest[:16])
        self.assertEqual(verdict["status"], "eligible")
        self.assertTrue(verdict["eligible"])
        self.assertEqual(verdict["observed"], digest)
        self.assertEqual(Path(verdict["path"]), path)

    def test_a_mismatching_executor_is_refused_and_says_what_it_found(self):
        verdict = _mlr_series.executor_eligibility(self.executor(b"some other build"),
                                                   required_sha256=REQUIRED)
        self.assertEqual(verdict["status"], "mismatch")
        self.assertFalse(verdict["eligible"])
        self.assertEqual(verdict["required"], REQUIRED)
        self.assertNotEqual(verdict["observed"][:16], REQUIRED)

    def test_identity_is_checked_and_not_a_version_string(self):
        """Two builds calling themselves the same version are still two boundaries."""
        one, two = self.executor(b"opencode 1.18.29 build a"), self.executor(b"opencode 1.18.29 b")
        import hashlib
        digest = hashlib.sha256(one.read_bytes()).hexdigest()
        self.assertTrue(_mlr_series.executor_eligibility(one, required_sha256=digest)["eligible"])
        self.assertFalse(_mlr_series.executor_eligibility(two, required_sha256=digest)["eligible"])

    def test_a_frozen_stack_with_no_executor_identity_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            _mlr_series.executor_eligibility(self.executor(b"x"), required_sha256="")


class _Attempts:
    """A stand-in for `run_bounded_attempt`, returning scripted outcomes in order.

    Records every call so a test can assert how many semantic trajectories the procedure bought,
    which is the quantity every retry rule in §10 and §11 is ultimately about.
    """

    def __init__(self, *outcomes, executor_sha256: str = None):
        self.outcomes = list(outcomes)
        self.executor_sha256 = executor_sha256
        self.calls: list[dict] = []

    def __call__(self, arm, **kw):
        self.calls.append({"arm": arm, **kw})
        if self.outcomes:
            outcome = self.outcomes.pop(0)
        else:
            outcome = valid_attempt(arm, executor_sha256=self.executor_sha256)
        return dict(outcome, arm=arm)


def valid_attempt(arm: str, *, executor_sha256: str = None, **overrides) -> dict:
    """A completed, clean attempt of the shape `run_bounded_attempt` returns."""
    base = {
        "arm": arm,
        "validity": _mlr_run.VALID, "trajectory_began": True, "view_destroyed": True,
        "model": pb_mlr.B1["model"], "variant": pb_mlr.B1["variant"], "role": pb_mlr.B1["role"],
        "auto_flag": pb_mlr.B1["permission_flag"], "oracle": pb_mlr.B1["oracle"],
        "package": pb_mlr.B1["package"],
        "source_digest": pb_mlr.B1["source_digest"] + "0" * 48,
        "task_sha256": pb_mlr.B1["task_sha256"] + "0" * 48,
        "contract_sha256": pb_mlr.B1["contract_sha256"] + "0" * 48,
        "executor": {"name": "opencode",
                     "sha256": executor_sha256 or (pb_mlr.B1["executor_sha256"] + "0" * 48)},
        "extraction": {"workspace": "workspace", "session": "worker.db"},
        "hermeticity": {"status": "clean", "findings": []},
        "context": {"unresolved": {"items": 0, "components": 0}, "contradictions": [],
                    "uncovered_events": [], "implementation_source_unique_bytes":
                        0 if arm == _mlr.CONTRACT else 5630},
        "outcome": {"correct": True, "gate_passed": True, "regression_passed": True},
        "cost": {"amount": 0.017},
        # `paired_analysis` fails closed on an incomplete profile — an execution whose telemetry is
        # absent is not an execution that consumed nothing. A stand-in without one would therefore
        # be read as twelve invalid pairs, so it carries the shape a real attempt produces.
        "profile": {"complete": True, "missing": [], "failed_tool_calls": 0,
                    "stages": [{"complete": True,
                                "usage": {"input": 20000, "output": 8000, "cache_read": 400000,
                                          "reasoning": 7000, "executor_cost": 0.012},
                                "tools": {"calls": 40, "failed_calls": 0, "by_tool": {},
                                          "seconds": 12.0},
                                "time": {"session_span_seconds": 120.0,
                                         "model_seconds_derived": 80.0,
                                         "verification_seconds": 0.1}}]},
    }
    base.update(overrides)
    return base


def failed_before_launch(**overrides) -> dict:
    """An infrastructure failure that provably preceded semantic execution (§11 A)."""
    return {"validity": _mlr_run.SETUP_FAILURE, "trajectory_began": False,
            "reason": "executor could not be started", **overrides}


def interrupted_after_launch(**overrides) -> dict:
    """A trajectory that entered the launcher and did not come back valid (§11 C)."""
    return {"validity": _mlr_run.HARNESS_FAILURE, "trajectory_began": True,
            "reason": "OperationalError: unable to open database file",
            "cost": {"amount": 0.0155}, **overrides}


class SeriesProcedureTest(unittest.TestCase):
    """Ordering, retry bounds, budget, continuation and immutability — with no provider."""

    maxDiff = None

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-b1-series-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.out = self.tmp / "series.json"
        self.config = pb_mlr.b1_configuration()
        self.executor = self.tmp / "opencode"
        self.executor.write_bytes(b"executor")
        self.digest = _mlr_boundary.executor_identity(self.executor)["sha256"]
        self.stack = dict(pb_mlr.B1, executor_sha256=self.digest)

    def attempts(self, *outcomes):
        return _Attempts(*outcomes, executor_sha256=self.digest)

    def valid(self, arm, **overrides):
        return valid_attempt(arm, executor_sha256=self.digest, **overrides)

    def run_series(self, attempts, **kw):
        kw.setdefault("extra", pb_mlr._b1_record_extras(self.stack))
        return _mlr_series.run_bounded_series(
            self.out, config=self.config, stack=self.stack, arms=list(_mlr.ARMS),
            samples=kw.pop("samples", pb_mlr.B1["samples"]), executor=self.executor,
            slots=pb_mlr.slots, attempt=attempts, **kw)

    def test_the_slot_order_is_the_preregistered_one(self):
        attempts = self.attempts()
        record = self.run_series(attempts)
        self.assertIsNone(record["stopped"])
        order = [(m["repeat"], m["item"]) for m in record["measurements"]]
        self.assertEqual(order, [
            (1, "full"), (1, "contract"), (2, "contract"), (2, "full"),
            (3, "full"), (3, "contract"), (4, "contract"), (4, "full"),
            (5, "full"), (5, "contract"), (6, "contract"), (6, "full")])
        self.assertEqual(len(attempts.calls), 12, "twelve slots, one trajectory each")

    def test_every_attempt_runs_against_the_frozen_fixture(self):
        attempts = self.attempts()
        self.run_series(attempts)
        for call in attempts.calls:
            self.assertEqual(Path(call["fixture"]).resolve(), B.root.resolve())

    def test_a_failure_before_launch_is_retried_and_bounded_at_three(self):
        attempts = self.attempts(failed_before_launch(), failed_before_launch(),
                             failed_before_launch())
        record = self.run_series(attempts, samples=1)
        self.assertEqual(record["stop_condition"], "B")
        self.assertEqual(len(attempts.calls), 3, "bounded at three, and all three are kept")
        self.assertEqual(len(record["measurements"]), 3)

    def test_a_failure_before_launch_that_then_succeeds_closes_the_slot(self):
        attempts = self.attempts(failed_before_launch(), self.valid(_mlr.FULL))
        record = self.run_series(attempts, samples=1)
        self.assertIsNone(record["stopped"])
        self.assertEqual(len(record["measurements"]), 3, "the failure is retained beside the slot")
        self.assertEqual([m["validity"] for m in record["measurements"]],
                         [_mlr_run.SETUP_FAILURE, _mlr_run.VALID, _mlr_run.VALID])

    def test_an_interrupted_trajectory_is_never_automatically_re_rolled(self):
        """§11 C. The rule that a blanket retry cannot express."""
        attempts = self.attempts(interrupted_after_launch())
        record = self.run_series(attempts, samples=1)
        self.assertEqual(record["stop_condition"], "C")
        self.assertEqual(len(attempts.calls), 1, "no second trajectory was bought")
        self.assertIn("never re-rolled", record["stop_reason"])

    def test_an_interrupted_trajectory_keeps_what_it_spent(self):
        attempts = self.attempts(interrupted_after_launch())
        record = self.run_series(attempts, samples=1)
        self.assertEqual(record["spent"], 0.0155)
        kept = record["measurements"][0]
        self.assertEqual(kept["cost"], {"amount": 0.0155})
        self.assertTrue(kept["trajectory_began"])
        self.assertIn("unable to open database file", kept["reason"])

    def test_a_restart_will_not_buy_a_second_trajectory_for_an_interrupted_slot(self):
        """The live rule and the resume rule have to be the same rule."""
        self.run_series(self.attempts(interrupted_after_launch()), samples=1)
        resumed = self.attempts()
        record = self.run_series(resumed, samples=1)
        self.assertEqual(record["stop_condition"], "C")
        self.assertEqual(len(resumed.calls), 0, "the resume launched nothing")

    def test_a_completed_slot_is_never_re_rolled_on_resume(self):
        self.run_series(self.attempts(), samples=2)
        again = self.attempts()
        record = self.run_series(again, samples=2)
        self.assertIsNone(record["stopped"])
        self.assertEqual(len(again.calls), 0, "four completed slots, nothing re-run")
        self.assertEqual(len(record["measurements"]), 4)

    def test_a_resume_across_a_changed_configuration_is_refused(self):
        self.run_series(self.attempts(), samples=1)
        other = dict(self.config, model="another/model")
        with self.assertRaises(_repeat.RepeatConfigError):
            _mlr_series.run_bounded_series(
                self.out, config=other, stack=self.stack, arms=list(_mlr.ARMS), samples=1,
                executor=self.executor, slots=pb_mlr.slots, attempt=self.attempts())

    def test_the_ceiling_stops_the_series_before_a_slot_rather_than_cutting_one_short(self):
        attempts = self.attempts(*[self.valid(a, cost={"amount": 0.11})
                               for a in ("full", "contract", "contract", "full")])
        record = self.run_series(attempts, budget=0.50, reserve=0.10)
        self.assertEqual(record["stop_condition"], "J")
        self.assertEqual(len(attempts.calls), 4,
                         "the fifth slot is not launched; the fourth is not truncated")
        self.assertEqual(record["stop_detail"]["ceiling"], 0.50)
        self.assertIn("would be exceeded", record["measurements"][-1]["reason"])

    def test_the_frozen_reserve_is_the_preregistered_one_and_not_the_module_default(self):
        self.assertEqual(pb_mlr.B1["reserve"], 0.10)
        self.assertEqual(pb_mlr.B1["ceiling"], 0.50)
        self.assertNotEqual(pb_mlr.B1["reserve"], pb_mlr._RESERVE)

    def test_a_completed_series_is_readable_by_the_committed_analysis(self):
        """The record the runner writes is the shape `paired_analysis` already reads.

        Not a result: these are controlled attempts, so the numbers are the stand-in's. What is
        being checked is that a b1 record needs no bespoke reader — the same analysis that reports
        §12's pair categories and the `contract`-source-is-zero integrity check consumes it.
        """
        record = self.run_series(self.attempts())
        written = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertIsNone(record["stopped"])
        analysis = pb_mlr.paired_analysis(written)
        self.assertEqual(analysis["experiment"], pb_mlr.B1["experiment"])
        self.assertEqual(analysis["pattern_counts"]["both-correct"], 6)
        self.assertEqual(analysis["pattern_counts"]["pair-invalid"], 0)
        self.assertEqual(analysis["incomplete_profiles"], [])
        self.assertTrue(analysis["treatment_integrity"]["contract_source_is_zero"])
        self.assertEqual(len(analysis["treatment_integrity"]["contract_source_bytes"]), 6)

    def test_the_record_carries_the_freeze_it_was_run_under(self):
        self.run_series(self.attempts(), samples=1)
        written = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(written["preregistration"], pb_mlr.B1["preregistration"])
        self.assertEqual(written["preregistration_sha256"], pb_mlr.B1["preregistration_sha256"])
        self.assertEqual(written["ceiling"], 0.50)
        self.assertEqual(written["reserve"], 0.10)
        self.assertEqual(written["max_attempts_per_slot"], 3)
        self.assertEqual(written["evidence_class"], "experiment")
        self.assertEqual(written["oracle"], B.oracle)
        self.assertTrue(written["source_digest"].startswith(pb_mlr.B1["source_digest"]))
        self.assertIn("recorded per measurement", written["host_derived_identities"])
        self.assertEqual(len(written["order"]), 12)

    def test_the_record_never_carries_a_result_family(self):
        """Naming the family is a reading of the experiment, and that is a person's to write."""
        record = self.run_series(self.attempts(interrupted_after_launch()), samples=1)
        written = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(record["stop_condition"], "C")
        for blob in (record, written):
            self.assertNotIn("family", blob)
            self.assertNotIn("outcome", blob)

    def test_a_stopped_series_stays_stopped_when_it_is_resumed(self):
        """A stop is a property of the evidence, not of the process that noticed it.

        Found in review. `done` was rebuilt from `validity == VALID` alone, and §11 D–I were only
        applied to freshly executed attempts — so a slot that executed validly and *then* tripped a
        stop condition read back as a closed slot. A restart launched nothing, reported
        `stopped: None`, and turned a series stopped for uncontrolled source into a record that
        looked clean and complete.
        """
        leak = self.valid(_mlr.CONTRACT)
        leak["context"]["implementation_source_unique_bytes"] = 412
        first = self.run_series(self.attempts(self.valid("full"), leak), samples=1)
        self.assertEqual(first["stop_condition"], "G")

        again = self.attempts()
        resumed = self.run_series(again, samples=1)
        self.assertEqual(resumed["stop_condition"], "G", "the stop survives the restart")
        self.assertIn("already recorded", resumed["stop_detail"]["note"])
        self.assertEqual(len(again.calls), 0, "and nothing was launched on top of it")
        self.assertNotIn(("contract", 1), resumed["completed_slots"])

    def test_every_stop_condition_survives_a_restart(self):
        for label, mutate in (
                ("D", lambda m: m.__setitem__("extraction", {})),
                ("E", lambda m: m["context"]["unresolved"].__setitem__("items", 1)),
                ("F", lambda m: m["context"].__setitem__("contradictions", ["x"])),
                ("G", lambda m: m.__setitem__("view_destroyed", False)),
                ("H", lambda m: m.__setitem__("model", "another/model")),
        ):
            with self.subTest(condition=label):
                self.out.unlink(missing_ok=True)
                bad = self.valid(_mlr.FULL)
                mutate(bad)
                self.assertEqual(self.run_series(self.attempts(bad), samples=1)["stop_condition"],
                                 label)
                again = self.attempts()
                self.assertEqual(self.run_series(again, samples=1)["stop_condition"], label)
                self.assertEqual(len(again.calls), 0)

    def test_a_refusal_that_never_reached_the_executor_does_not_spend_an_attempt(self):
        """§11 B counts infrastructure attempts on the slot, not environment refusals before one.

        Found in review. The ceiling and residue rows are appended with an attempt number and the
        series returns; on a later resume they were counted against the slot's three, so three
        environment refusals could exhaust a slot the executor was never offered once.
        """
        self.run_series(self.attempts(), budget=0.05, reserve=0.10, samples=1)
        written = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(len(written["measurements"]), 1)
        self.assertEqual(written["measurements"][0]["stage"], _mlr_series.NOT_OFFERED)
        self.assertEqual(_mlr_series._offered(written["measurements"], ("full", 1)), 0)

        # With the ceiling raised the slot still has all three attempts available.
        resumed = self.attempts(failed_before_launch(), failed_before_launch(),
                                failed_before_launch())
        record = self.run_series(resumed, samples=1)
        self.assertEqual(len(resumed.calls), 3, "the refusal did not consume one of the three")
        self.assertEqual(record["stop_condition"], "B")

    def test_each_attempt_records_how_far_it_got(self):
        record = self.run_series(
            self.attempts(failed_before_launch(),
                          interrupted_after_launch(launch_returncode=1,
                                                   validity=_mlr_run.SETUP_FAILURE)),
            samples=1)
        stages = [m["stage"] for m in record["measurements"]]
        self.assertEqual(stages, [_mlr_series.BEFORE_LAUNCH, _mlr_series.LAUNCHER_REFUSED])
        self.assertEqual(record["stop_condition"], "C")
        self.assertTrue(record["stop_detail"]["launcher_classified_as_pre_semantic"],
                        "the hint is surfaced for the person resolving the slot")
        self.assertIn("this refuses to make it", record["stop_detail"]["note"])

    def test_a_launcher_refusal_still_does_not_buy_a_second_trajectory(self):
        """The hint is reported; it is not promoted into permission.

        It is a substring match over log text, and the cost of it being wrong is a re-rolled
        trajectory — the one thing §11 C exists to prevent.
        """
        attempts = self.attempts(interrupted_after_launch(
            launch_returncode=1, validity=_mlr_run.SETUP_FAILURE,
            reason="opencode: command not found"))
        record = self.run_series(attempts, samples=1)
        self.assertEqual(record["stop_condition"], "C")
        self.assertEqual(len(attempts.calls), 1)

    def test_an_attempt_that_reached_the_executor_unpriced_is_not_counted_as_free(self):
        """Cost is derived from the extracted session, so an attempt that failed before extraction
        carries none. Adding nothing for it would read an unknown as zero — the one direction a
        budget must never round.
        """
        lost = interrupted_after_launch()
        lost.pop("cost")
        record = self.run_series(self.attempts(lost), samples=1)
        self.assertEqual(record["stop_condition"], "C")
        account = record["spend"]
        self.assertEqual(account["derived"], 0.0)
        self.assertFalse(account["complete"])
        self.assertEqual(len(account["unpriced"]), 1)
        self.assertEqual(account["unpriced"][0]["stage"], _mlr_series.WORKER_EXECUTED)
        self.assertIn("unknown, not zero", account["claim"])

    def test_an_attempt_that_never_reached_the_executor_genuinely_cost_nothing(self):
        record = self.run_series(self.attempts(failed_before_launch(), self.valid(_mlr.FULL)),
                                 samples=1)
        self.assertTrue(record["spend"]["complete"])
        self.assertEqual(record["spend"]["unpriced"], [])
        self.assertIn("whole of what this series spent", record["spend"]["claim"])

    def test_the_ceiling_gate_refuses_rather_than_launch_on_a_spend_it_cannot_establish(self):
        """A gate that read an unknown as zero would keep buying slots on an incomplete figure."""
        lost = valid_attempt(_mlr.FULL, executor_sha256=self.digest)
        lost.pop("cost")
        record = self.run_series(self.attempts(lost), samples=2, budget=0.50, reserve=0.10)
        self.assertEqual(record["stop_condition"], "J")
        self.assertEqual(record["stop_detail"]["reason"], "unpriced-attempt")
        self.assertFalse(record["stop_detail"]["spend"]["complete"])
        self.assertIn("spend cannot be established", record["measurements"][-1]["reason"])

    def test_a_complete_spend_still_reports_the_ceiling_reason_when_it_is_the_ceiling(self):
        attempts = self.attempts(*[self.valid(a, cost={"amount": 0.11})
                                   for a in ("full", "contract", "contract", "full")])
        record = self.run_series(attempts, budget=0.50, reserve=0.10)
        self.assertEqual(record["stop_condition"], "J")
        self.assertEqual(record["stop_detail"]["reason"], "ceiling")
        self.assertTrue(record["stop_detail"]["spend"]["complete"])

    def test_checkpointing_writes_after_every_attempt(self):
        attempts = self.attempts(self.valid("full"), interrupted_after_launch())
        self.run_series(attempts, samples=1)
        written = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(len(written["measurements"]), 2)
        self.assertEqual(written["frozen_identity"], _repeat.frozen_identity(self.config))

    def test_an_unpriced_attempt_survives_persistence_and_reload_as_unpriced(self):
        """The one direction a budget must not round, checked on the reloaded bytes.

        `spend` is computed over `measurements`, and on a resume those measurements come back
        through JSON. If the round trip dropped `trajectory_began` or `launch_returncode` the same
        attempt would re-read as a failure before the launcher, and an unknown quantity would
        become a zero on the way back from disk rather than in the arithmetic.
        """
        lost = interrupted_after_launch()
        lost.pop("cost")
        live = self.run_series(self.attempts(lost), samples=1)["spend"]

        reloaded = _repeat.load_series(self.out, self.config)
        self.assertEqual(_mlr_series.spend(reloaded), live)
        self.assertFalse(_mlr_series.spend(reloaded)["complete"])
        self.assertEqual(_mlr_series.execution_stage(reloaded[-1]),
                         _mlr_series.WORKER_EXECUTED)

    def test_the_record_states_the_spend_account_and_not_only_the_total(self):
        """A committed artifact that states a total leaves its completeness limit to be recomputed.

        `derived` and `unpriced` were separated precisely because the figure must not be read
        without its limit, so the limit travels in the record rather than only in the stdout of the
        process that happened to run it.
        """
        lost = interrupted_after_launch()
        lost.pop("cost")
        self.run_series(self.attempts(lost), samples=1)
        written = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertIn("spend", written)
        self.assertFalse(written["spend"]["complete"])
        self.assertEqual(written["spend"]["derived"], 0.0)
        self.assertIn("unknown, not zero", written["spend"]["claim"])

        analysed = pb_mlr.paired_analysis(written)
        self.assertEqual(analysed["spend"], written["spend"])

    def test_a_record_that_predates_the_stage_vocabulary_is_unknown_not_free(self):
        """Found in review. `execution_stage` fell through to `before-launch` on a missing
        `trajectory_began`, so every attempt in a record written before that key existed was
        classified "never reached the executor" and dropped from `unpriced` — and the analysis then
        claimed the series spent nothing and that the figure was whole. Absence of the fact is not
        the fact.
        """
        legacy = [{"item": "full", "repeat": 1, "validity": _mlr_run.VALID},
                  {"item": "contract", "repeat": 1, "validity": "harness-failure"}]
        account = _mlr_series.spend(legacy)
        self.assertEqual(account["derived"], 0.0)
        self.assertFalse(account["complete"])
        self.assertEqual([r["stage"] for r in account["unpriced"]],
                         [_mlr_series.UNCLASSIFIED] * 2)
        self.assertIn("cannot be placed on either side", account["claim"])
        self.assertNotIn("reached the executor", account["claim"])

        # A committed record with the vocabulary is unaffected: q1 still reproduces its own figure.
        q1 = json.loads((Path(__file__).resolve().parents[1] / "evals" / "results" /
                         "craft-mlr-deepseek-v4-flash-high-paired-q1.json"
                         ).read_text(encoding="utf-8"))
        priced = _mlr_series.spend(q1["measurements"])
        self.assertEqual(priced["derived"], q1["spent_derived"])
        self.assertTrue(priced["complete"])

    def test_the_spend_claim_does_not_say_an_in_flight_attempt_reached_the_executor(self):
        """Found in review. One sentence covered three different facts, and for an in-flight row it
        asserted exactly the one its stage exists to say was never established.
        """
        in_flight = _mlr_series.spend([{"item": "full", "repeat": 1,
                                        "stage": _mlr_series.IN_FLIGHT,
                                        "trajectory_began": True}])
        self.assertIn("never reported an outcome", in_flight["claim"])
        self.assertNotIn("reached the executor", in_flight["claim"])

        reached = _mlr_series.spend([{"item": "full", "repeat": 1, "trajectory_began": True,
                                      "launch_returncode": 1}])
        self.assertIn("reached the executor", reached["claim"])

        # Mixed, and each reason still stated as its own.
        both = _mlr_series.spend([{"item": "full", "repeat": 1, "stage": _mlr_series.IN_FLIGHT,
                                   "trajectory_began": True},
                                  {"item": "contract", "repeat": 1, "trajectory_began": True,
                                   "launch_returncode": 1}])
        self.assertIn("never reported an outcome", both["claim"])
        self.assertIn("reached the executor", both["claim"])
        self.assertIn("omits 2 attempt(s)", both["claim"])

    def test_a_failure_before_the_launcher_is_retried_even_when_it_raised(self):
        """Found in review. Three statements in `run_bounded_attempt` sat outside its "reported,
        never raised" block — resolving the fixture, hashing the executor, making the extraction
        directory. Each provably precedes the launcher and is §11 A's case, but raised from there
        they escaped the series loop, leaving the pre-attempt checkpoint as the only surviving row:
        a slot frozen in §11 C, unresumable, for a failure that never reached the executor.
        """
        for label, kw in (("an unknown fixture root",
                           {"fixture": self.tmp / "not-a-fixture"}),
                          ("an executor that vanished after the eligibility check",
                           {"executor": self.tmp / "gone"})):
            with self.subTest(case=label):
                got = _mlr_boundary.run_bounded_attempt(
                    _mlr.CONTRACT, model="provider/model", variant=None,
                    executor=kw.get("executor", self.executor),
                    fixture=kw.get("fixture", Path(pb_mlr.B1["fixture"])))
                self.assertFalse(got["trajectory_began"])
                self.assertEqual(_mlr_series.execution_stage(got), _mlr_series.BEFORE_LAUNCH)
                # The specific failure, not merely some failure: without naming it the test would
                # also pass on an unrelated error raised from inside the `try`.
                self.assertRegex(got["reason"], r"^(FixtureError|FileNotFoundError):")
                self.assertTrue(_mlr_series.spend([got])["complete"],
                                "it never reached the executor, so it genuinely cost nothing")

    def test_the_unclassified_verdict_survives_its_own_persistence(self):
        """Found in review. The verdict short-circuited on `"stage" not in record`, but the loop
        writes a stage into every measurement — so the row it had just classified `unclassified`
        re-read as `before-launch`, and the unknown became a zero on the way back from disk. The
        one place this repair could not afford to have the defect is in itself.
        """
        row = {"item": "full", "repeat": 1, "validity": _mlr_run.HARNESS_FAILURE}
        self.assertEqual(_mlr_series.execution_stage(row), _mlr_series.UNCLASSIFIED)

        persisted = {**row, "stage": _mlr_series.execution_stage(row)}
        self.assertEqual(_mlr_series.execution_stage(persisted), _mlr_series.UNCLASSIFIED)
        self.assertFalse(_mlr_series.spend([persisted])["complete"])

        # Through the actual file, not only through a dict.
        _repeat.write_series(self.out, self.config, [persisted])
        reloaded = _repeat.load_series(self.out, self.config)
        self.assertEqual(_mlr_series.execution_stage(reloaded[0]), _mlr_series.UNCLASSIFIED)
        self.assertFalse(_mlr_series.spend(reloaded)["complete"])

    def test_an_attempt_that_cannot_say_where_it_stopped_is_not_retried(self):
        """The retry gate read one key, so an attempt whose stage is `unclassified` was priced as
        unknown and retried as free in the same iteration.
        """
        mute = {"validity": _mlr_run.HARNESS_FAILURE, "reason": "said nothing about how far it got"}
        attempts = self.attempts(mute)
        record = self.run_series(attempts, samples=1)
        self.assertEqual(record["measurements"][0]["stage"], _mlr_series.UNCLASSIFIED)
        self.assertEqual(record["stop_condition"], "C")
        self.assertEqual(len(attempts.calls), 1, "not offered again")
        self.assertFalse(record["spend"]["complete"])

    def test_the_in_flight_row_does_not_claim_the_launcher_was_entered(self):
        """Found in review. `trajectory_began` is documented as set the instant the launcher is
        entered; the row is written before the launcher exists. Its stage carries the same
        consequence without the record asserting a fact nothing established.
        """
        class Killed(BaseException):
            pass

        def killed(arm, **kw):
            raise Killed("host killed the process")

        with self.assertRaises(Killed):
            self.run_series(killed, samples=1)
        row = json.loads(self.out.read_text(encoding="utf-8"))["measurements"][0]
        self.assertEqual(row["stage"], _mlr_series.IN_FLIGHT)
        self.assertNotIn("trajectory_began", row)

        # And the consequence is unchanged: unpriced, and the slot is not offered again.
        self.assertFalse(_mlr_series.spend([row])["complete"])
        resumed = self.attempts()
        again = self.run_series(resumed, samples=1)
        self.assertEqual(again["stop_condition"], "C")
        self.assertEqual(again["stop_detail"]["stage"], _mlr_series.IN_FLIGHT)
        self.assertEqual(len(resumed.calls), 0)

    def test_the_spend_claim_states_each_reason_once(self):
        """Found in review. Keyed by stage, so two attempts unpriced for the same reason produced a
        claim that said the identical thing twice.
        """
        claim = _mlr_series.spend([
            {"item": "full", "repeat": 1, "trajectory_began": True, "launch_returncode": 1},
            {"item": "contract", "repeat": 1, "trajectory_began": True, "launch_returncode": 0},
        ])["claim"]
        self.assertIn("omits 2 attempt(s)", claim)
        self.assertEqual(claim.count("reached the executor"), 1)
        self.assertIn("2 that reached the executor", claim)

    def test_retention_that_cannot_be_written_does_not_destroy_the_attempt(self):
        """Found in review. The retention copy sat in an unguarded `finally`, which runs on the
        success path too: an unusable `--keep` raised out of the attempt *after* the outcome, the
        context ledger and the cost were computed. The money was spent, the trajectory was lost,
        and the loop's pre-attempt checkpoint became the only surviving row — a slot frozen in
        §11 C by a mistyped path.
        """
        got = _mlr_boundary.run_bounded_attempt(
            _mlr.CONTRACT, model="provider/model", variant=None,
            executor=self.executor, fixture=Path(pb_mlr.B1["fixture"]),
            keep=Path("/dev/null/not-a-directory"))
        self.assertIsInstance(got, dict, "reported, never raised")
        self.assertIn("evidence_error", got, "and the failure is named rather than swallowed")
        self.assertIn("NotADirectoryError", got["evidence_error"])
        self.assertNotIn("evidence", got)

    def test_preflight_refuses_an_unwritable_retention_directory_before_spending(self):
        """A path is checkable for nothing, and §11 has no case for "the evidence was mislaid"."""
        blocked = pb_mlr.b1_preflight(executor=None, keep=Path("/dev/null/x"))
        self.assertIn("the evidence retention directory can be written", blocked["blocked_by"])
        usable = pb_mlr.b1_preflight(executor=None, keep=self.tmp / "evidence")
        self.assertNotIn("the evidence retention directory can be written",
                         usable["blocked_by"])
        self.assertTrue((self.tmp / "evidence").is_dir())

    def test_a_timed_out_attempt_spends_its_slot_and_survives_a_resume(self):
        """A deadline is not a reason to buy the slot again.

        The worker was stopped, but it had commenced: §11 C preserves it, contributes no
        measurement and never re-rolls it. The disposition has to survive the record round trip too,
        or a restart would read the slot as merely unfinished and offer it a second trajectory.
        """
        # The shape the controller really writes: no `launch_returncode`, because the timeout
        # branch returns before one is assigned. An earlier version of this test supplied one and
        # so passed for the wrong reason.
        timed_out = {"validity": _mlr_run.HARNESS_FAILURE, "trajectory_began": True,
                     "timed_out": True, "terminal_status": "controller-timeout",
                     "attempt_deadline_seconds": 1800,
                     "worker_monotonic_seconds": 1800.2, "worker_wall_seconds": 5439.9,
                     "termination": {"found": 2, "stopped": True, "survivors": []},
                     "reason": "the controller's 1800s deadline expired"}
        attempts = self.attempts(timed_out)
        record = self.run_series(attempts, samples=1)
        self.assertEqual(record["stop_condition"], "C")
        self.assertEqual(len(attempts.calls), 1, "the slot was offered again after a timeout")
        self.assertFalse(record["spend"]["complete"],
                         "a stopped trajectory with no derived cost is unknown, not free")

        written = json.loads(self.out.read_text(encoding="utf-8"))
        row = written["measurements"][0]
        self.assertTrue(row["timed_out"])
        self.assertEqual(row["terminal_status"], "controller-timeout")
        self.assertNotIn("launch_returncode", row)
        self.assertTrue(row["termination"]["stopped"])
        # Both clocks survive, which is the whole point of recording two of them.
        self.assertEqual(row["attempt_deadline_seconds"], 1800)
        self.assertLess(row["worker_monotonic_seconds"], row["worker_wall_seconds"])

        resumed = self.attempts()
        again = self.run_series(resumed, samples=1)
        self.assertEqual(again["stop_condition"], "C")
        self.assertEqual(len(resumed.calls), 0, "a resume bought a trajectory the loop refused")

    def test_an_attempt_cannot_declare_its_own_stage(self):
        """Classification is the loop's, from what the attempt got to, not the attempt's claim.

        `execution_stage` honours a recorded `not-offered`/`in-flight` because the loop writes
        those, and both mean "this cost nothing" or "this is unknown". An attempt returning either
        would price a real trajectory at zero and leave all three of the slot's attempts unspent.
        """
        lying = interrupted_after_launch(stage=_mlr_series.NOT_OFFERED)
        lying.pop("cost")
        record = self.run_series(self.attempts(lying), samples=1)
        self.assertEqual(record["measurements"][0]["stage"], _mlr_series.WORKER_EXECUTED)
        self.assertEqual(record["stop_condition"], "C")
        self.assertFalse(record["spend"]["complete"], "unknown, not free on the attempt's word")
        self.assertEqual(_mlr_series._offered(record["measurements"], ("full", 1)), 1)

    def test_a_process_killed_inside_an_attempt_leaves_the_slot_recorded(self):
        """Found in review. `write_series` ran when an attempt *returned*, so a SIGKILL or a host
        timeout inside one appended nothing: the slot left no trace at all. A resume — which the
        runbook itself tells the operator to reach after clearing the stale view the kill left
        behind — then found no prior attempt on the slot, offered it again, and bought a second
        trajectory for a slot §11 C may already have spent.
        """
        class Killed(BaseException):
            """Not an Exception: `run_bounded_attempt` catches those and reports them."""

        def killed(arm, **kw):
            raise Killed("the host killed the process mid-attempt")

        with self.assertRaises(Killed):
            self.run_series(killed, samples=1)

        written = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(len(written["measurements"]), 1)
        row = written["measurements"][0]
        self.assertEqual(row["stage"], _mlr_series.IN_FLIGHT)
        self.assertEqual((row["item"], row["repeat"]), ("full", 1))
        self.assertEqual(_mlr_series.execution_stage(row), _mlr_series.IN_FLIGHT)

        # Unknown, not zero: nothing established that it stopped short of the provider.
        self.assertFalse(written["spend"]["complete"])
        self.assertEqual(written["spend"]["derived"], 0.0)

        # And the slot is not offered again.
        resumed = self.attempts()
        record = self.run_series(resumed, samples=1)
        self.assertEqual(record["stop_condition"], "C")
        self.assertEqual(record["stop_detail"]["stage"], _mlr_series.IN_FLIGHT)
        self.assertEqual(len(resumed.calls), 0, "no second trajectory for a slot it cannot acquit")

    def test_the_in_flight_row_is_replaced_by_the_outcome_it_was_standing_in_for(self):
        """It marks the absence of an answer, so it must not survive one arriving.

        A phantom row would count against §11 B's three, invalidate the spend account of every
        clean series, and read as an interrupted trajectory on the next resume.
        """
        attempts = self.attempts(failed_before_launch())
        record = self.run_series(attempts, samples=1)
        stages = [m["stage"] for m in record["measurements"]]
        self.assertEqual(stages, [_mlr_series.BEFORE_LAUNCH, _mlr_series.WORKER_EXECUTED,
                                  _mlr_series.WORKER_EXECUTED])
        self.assertNotIn(_mlr_series.IN_FLIGHT, stages)
        self.assertTrue(record["spend"]["complete"])
        self.assertIsNone(record["stopped"])
        self.assertEqual(record["completed_slots"], [("contract", 1), ("full", 1)])
        self.assertEqual(_mlr_series._offered(record["measurements"], ("full", 1)), 2)


class StopConditionTest(unittest.TestCase):
    """§11 D–I on a completed attempt, each from the evidence the attempt already recorded."""

    maxDiff = None

    def defect(self, **overrides):
        attempt = valid_attempt(_mlr.CONTRACT, **overrides)
        return _mlr_series.validity_defect(attempt, pb_mlr.B1)

    def test_a_clean_attempt_trips_nothing(self):
        self.assertIsNone(self.defect())

    def test_a_failed_extraction_stops_the_series(self):
        self.assertEqual(self.defect(extraction={"workspace": "workspace"})[0], "D")

    def test_unresolved_attribution_stops_the_series_at_either_granularity(self):
        self.assertEqual(self.defect(context={"unresolved": {"items": 2, "components": 0}})[0], "E")
        self.assertEqual(self.defect(context={"unresolved": {"items": 0, "components": 1}})[0], "E")

    def test_a_contradiction_or_an_uncovered_event_stops_the_series(self):
        self.assertEqual(self.defect(context={"contradictions": ["x"]})[0], "F")
        self.assertEqual(self.defect(context={"uncovered_events": ["y"]})[0], "F")

    def test_uncontrolled_source_reaching_contract_stops_the_series(self):
        letter, evidence = self.defect(
            context={"implementation_source_unique_bytes": 412,
                     "unresolved": {"items": 0, "components": 0}})
        self.assertEqual(letter, "G")
        self.assertIn("412", evidence)

    def test_a_hermeticity_finding_inside_the_view_stops_the_series(self):
        self.assertEqual(self.defect(hermeticity={"findings": [{"path": "/x"}]})[0], "G")

    def test_a_surviving_view_is_cross_slot_contamination(self):
        self.assertEqual(self.defect(view_destroyed=False)[0], "G")

    def test_stack_drift_stops_the_series(self):
        for field, value in (("model", "another/model"), ("variant", "medium"),
                             ("oracle", "external_test_v2.py"), ("package", "objectstore"),
                             ("role", "reviewer"), ("auto_flag", "")):
            with self.subTest(field=field):
                self.assertEqual(self.defect(**{field: value})[0], "H")

    def test_a_different_executor_is_drift(self):
        letter, evidence = self.defect(executor={"name": "opencode", "sha256": "dead" * 16})
        self.assertEqual(letter, "H")
        self.assertIn("executor", evidence)

    def test_a_host_difference_is_not_drift(self):
        """§5 records interpreter, boundary and hermeticity digests as execution facts."""
        self.assertIsNone(self.defect(interpreter="3.14.7",
                                      boundary_identity="0" * 64,
                                      hermeticity={"findings": [],
                                                   "hermeticity_identity": "beef" * 16}))

    def test_an_ungradeable_workspace_stops_the_series(self):
        attempt = valid_attempt(_mlr.CONTRACT)
        attempt.pop("outcome")
        attempt["reason"] = "the oracle could not be run"
        self.assertEqual(_mlr_series.validity_defect(attempt, pb_mlr.B1)[0], "I")

    def test_a_field_a_historical_record_never_carried_is_not_drift(self):
        """Absence is not change, and a stop condition that says otherwise stops on its own history.

        Written from a real false positive. `package` is new in this milestone, so every attempt in
        q1's committed record lacks it; the first version of `drift` read that `None` as a
        mismatch and reported all twelve known-good trajectories as stack drift.
        """
        attempt = valid_attempt(_mlr.CONTRACT)
        for field in ("package", "oracle", "model", "variant", "role", "auto_flag",
                      "source_digest", "task_sha256", "contract_sha256", "executor"):
            with self.subTest(missing=field):
                without = {k: v for k, v in attempt.items() if k != field}
                self.assertEqual(_mlr_series.drift(without, pb_mlr.B1), [],
                                 f"an absent {field} was read as drift")

    def test_the_stop_conditions_pass_cleanly_over_a_real_valid_series(self):
        """Cross-checked against q1's twelve committed measurements.

        This reads the committed record and nothing else. It does not re-run q1, re-read any
        session database, regrade any workspace, or establish anything about when q1 executed.
        """
        record = json.loads((Path(__file__).resolve().parents[1] / "evals" / "results" /
                             "craft-mlr-deepseek-v4-flash-high-paired-q1.json"
                             ).read_text(encoding="utf-8"))
        stack = {"model": record["model"], "variant": record["variant"],
                 "oracle": record["oracle"], "package": "objectstore", "role": record["role"],
                 "permission_flag": record["permission_flag"],
                 "source_digest": record["source_digest"][:16],
                 "task_sha256": record["task_sha256"][:16],
                 "contract_sha256": record["contract_sha256"][:16],
                 "executor_sha256": record["executor"]["sha256"][:16]}
        self.assertEqual(len(record["measurements"]), 12)
        for measurement in record["measurements"]:
            with self.subTest(slot=measurement["slot"], arm=measurement["arm"]):
                self.assertIsNone(_mlr_series.validity_defect(measurement, stack))

    def test_every_stop_condition_is_one_the_preregistration_defines(self):
        text = (Path(__file__).resolve().parents[1] / pb_mlr.B1["preregistration"]
                ).read_text(encoding="utf-8")
        for letter in _mlr_series.STOP_CONDITIONS:
            with self.subTest(condition=letter):
                self.assertIn(f"| {letter} ·", text, f"§11 defines condition {letter}")


class RetrospectLayoutTest(unittest.TestCase):
    """Re-reading a retained session must know which module it is looking at."""

    maxDiff = None

    def test_the_recovered_layout_carries_the_fixture_the_session_ran_under(self):
        """Found in review. `_rebuilt` dropped `package` and `vendored`, and both fall back to
        objectstore when absent — so `retrospect` would have re-read an eventbus session with
        objectstore fingerprints and looked for its vendored copy at a path that does not exist.
        """
        measurement = {
            "arm": _mlr.FULL, "fixture": str(B.root), "package": B.package,
            "vendored": str(B.vendored),
            "event_dir": "/tmp/view/workspace/DeepSeekAndDestroy/plans/mlr/runs/r1",
            "evidence_gate": {"log": "/tmp/view/workspace/run.log"},
        }
        layout = pb_mlr._rebuilt(measurement)
        self.assertEqual(layout["package"], B.package)
        self.assertEqual(Path(layout["fixture"]).resolve(), B.root.resolve())
        self.assertEqual(str(layout["vendored"]), str(B.vendored))
        self.assertIs(_mlr.fixture_for(layout["fixture"]), B)

    def test_a_record_written_before_the_fields_existed_still_reads_as_objectstore(self):
        layout = pb_mlr._rebuilt({
            "arm": _mlr.FULL,
            "evidence_gate": {"log": "/tmp/view/workspace/run.log"}})
        self.assertNotIn("package", layout)
        self.assertIs(_mlr.fixture_for(layout.get("fixture")), A)

    def test_path_classification_follows_the_fixture_the_layout_names(self):
        """The consequence the missing fields would have had, stated as behaviour."""
        layout = {"arm": _mlr.FULL, "workspace": "/tmp/view/workspace",
                  "runtime": "/tmp/view/runtime", "package": B.package,
                  "vendored": str(B.vendored)}
        inside = f"/tmp/view/workspace/{B.vendored}/{B.package}/_registry.py"
        self.assertEqual(_mlr.classify_path(inside, layout), _mlr.VENDORED_IMPLEMENTATION)
        without = {k: v for k, v in layout.items() if k not in ("package", "vendored")}
        self.assertEqual(_mlr.classify_path(inside, without), _mlr.WORKSPACE,
                         "which is exactly the misreading the carried fields prevent")


class SubstantiveFrozenPropertyTest(unittest.TestCase):
    """What the host-derived digests are permitted to hide, and what must be checked anyway.

    §5 records the interpreter, the semantic boundary digest and the hermeticity rule digest per
    slot as execution facts, because each legitimately varies with the machine — the rule's identity
    includes its absolute scan roots and the boundary exposes the launching interpreter's install
    path. So a difference in those digests is a host difference and is reported, never compared.

    A digest cannot say *why* it moved. A repository at another path and a rule that quietly stopped
    controlling the oracle produce equally different digests, so "reported, never compared" would
    hide the second along with the first. These pin the substantive properties directly, so that the
    permitted difference cannot conceal a change to what the rule checks or what the boundary
    exposes. Fixture A's shape was already pinned by q1's freeze test; fixture B's was not.
    """

    maxDiff = None

    def setUp(self):
        self.rule = _mlr.hermeticity(fixture=B.root)
        self.by = {k.category: k for k in self.rule["sensitive"]}

    def test_the_rule_checks_all_five_categories(self):
        import _hermetic
        self.assertEqual(sorted(self.by), sorted(_hermetic.CATEGORIES))

    def test_controlled_evidence_is_the_eventbus_source_by_content_and_by_name(self):
        source = sorted(B.source.glob("*.py"))
        self.assertTrue(source)
        controlled = self.by["controlled-evidence"]
        self.assertEqual(sorted(controlled.digests),
                         sorted(_mlr.digest_file(p) for p in source))
        self.assertEqual(sorted(controlled.stems), sorted(p.name for p in source))
        self.assertTrue(controlled.marks, "the source fingerprint is part of the rule")

    def test_the_oracle_reference_prior_sample_and_results_stay_controlled(self):
        self.assertEqual(sorted(self.by["oracle"].digests), [_mlr.digest_file(B.gate)])
        self.assertTrue(self.by["reference-solution"].digests)
        self.assertEqual(self.by["prior-sample"].contains, (b"MLR-external",))
        self.assertEqual(self.by["experiment-result"].path_markers, ("craft-mlr-",))

    def test_nothing_is_declared_exposed_before_a_run(self):
        self.assertEqual(self.rule["declared"], [])

    def test_the_scan_roots_keep_their_meaning(self):
        """Which places are searched is policy. Where they are on this machine is not."""
        import tempfile as _tempfile
        roots = [str(r) for r in self.rule["roots"]]
        self.assertEqual(len(roots), 3)
        self.assertEqual(roots[0], _tempfile.gettempdir())
        self.assertEqual(roots[1], "/tmp")
        self.assertEqual(Path(roots[2]), Path(__file__).resolve().parents[1],
                         "the repository is a scanned root and not an exception")

    def test_a_substantive_change_and_a_moved_repository_are_indistinguishable_by_digest(self):
        """Why the properties above are pinned directly rather than through the identity."""
        import _hermetic
        base = _hermetic.identity(self.rule["sensitive"], self.rule["roots"], [])
        moved = _hermetic.identity(self.rule["sensitive"],
                                   [*self.rule["roots"][:2], "/elsewhere/proofbound"], [])
        without_oracle = _hermetic.identity(
            [k for k in self.rule["sensitive"] if k.category != "oracle"], self.rule["roots"], [])
        declared = _hermetic.identity(self.rule["sensitive"], self.rule["roots"], ["/an/exposure"])
        self.assertNotEqual(base, moved, "a moved repository is a permitted host difference")
        self.assertNotEqual(base, without_oracle, "so is losing a category, to the digest")
        self.assertNotEqual(base, declared)
        self.assertEqual(len({moved, without_oracle, declared}), 3,
                         "three different digests, and the digest cannot say which is which")

    def test_the_boundary_exposes_only_what_the_treatment_requires(self):
        """The policy's substantive fields, independent of the digest they produce."""
        policy = _mlr_boundary.policy(executor=None)
        self.assertIs(policy.network, True, "the executor must reach its provider")
        self.assertIs(policy.notifications, False)
        self.assertEqual(policy.declared, ())
        self.assertEqual(policy.tools, (), "no tool is bound when no executor is selected")
        self.assertEqual(policy.system_reads, _semantic_view.SYSTEM_READS)
        self.assertEqual(policy.traversal, _semantic_view.TRAVERSAL)
        exposure = _mlr_boundary.interpreter_exposure()
        self.assertEqual(set(policy.extra_reads), set(exposure),
                         "the only extra readable root is the launching interpreter's install")
        self.assertEqual(set(policy.system_execs),
                         set(_semantic_view.SYSTEM_EXECS) | set(exposure))

    def test_the_boundary_binds_its_executor_by_content(self):
        tmp = Path(tempfile.mkdtemp(prefix="pb-b1-policy-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        one, two = tmp / "a", tmp / "b"
        one.write_bytes(b"one")
        two.write_bytes(b"two")
        self.assertEqual(len(_mlr_boundary.policy(executor=one).tools), 1)
        self.assertNotEqual(_mlr_boundary.policy(executor=one).identity(),
                            _mlr_boundary.policy(executor=two).identity())

    def test_the_interpreter_requirement_is_enforced_by_the_runtime_not_by_a_digest(self):
        """Both arms must execute the same compiled module, whatever interpreter compiled it."""
        full = _mlr.materialise(_mlr.FULL, Path(tempfile.mkdtemp(prefix="pb-b1-i1-")) / "arm",
                                fixture=B.root)
        contract = _mlr.materialise(_mlr.CONTRACT,
                                    Path(tempfile.mkdtemp(prefix="pb-b1-i2-")) / "arm",
                                    fixture=B.root)
        for built in (full, contract):
            self.addCleanup(shutil.rmtree, Path(built["workspace"]).parents[1], True)
        self.assertEqual(full["runtime_structure"], contract["runtime_structure"],
                         "the two arms execute the same compiled implementation")
        self.assertEqual(full["interpreter"], _mlr.interpreter_identity())
        loaded = _mlr.executed_module_is_not_the_readable_copy(full)
        self.assertTrue(loaded["from_runtime"], "the module that executes is the compiled one")
        self.assertTrue(loaded["readable_copy_is_editable"], "and `full` still carries a copy")


class BoundedExecutionTest(unittest.TestCase):
    """The b1 path goes through the semantic boundary, and cannot quietly stop doing so."""

    maxDiff = None

    def test_the_default_attempt_is_the_bounded_one(self):
        import inspect
        source = inspect.getsource(_mlr_series.run_bounded_series)
        self.assertIn("attempt or _mlr_boundary.run_bounded_attempt", source)
        self.assertNotIn("_mlr_run.run_attempt", source,
                         "there is no unbounded fallback in the b1 series")

    def test_the_bounded_attempt_marks_a_trajectory_the_moment_the_launcher_is_entered(self):
        import inspect
        source = inspect.getsource(_mlr_boundary.run_bounded_attempt)
        began = source.index('result["trajectory_began"] = True')
        launched = source.index("launched = launch(")
        self.assertLess(began, launched,
                        "the flag is set before the call, so a crash inside it still counts")
        self.assertIn('"trajectory_began": False', source, "it starts false")

    def test_the_bounded_attempt_grades_the_fixture_it_ran(self):
        import inspect
        source = inspect.getsource(_mlr_boundary.run_bounded_attempt)
        self.assertIn("fixture=fixture", source)
        self.assertIn('spec.oracle', source)

    def test_run_b1_refuses_to_start_when_preflight_is_not_launchable(self):
        tmp = Path(tempfile.mkdtemp(prefix="pb-b1-refuse-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        wrong = tmp / "opencode"
        wrong.write_bytes(b"not the frozen executor")
        with self.assertRaises(_mlr_series.SeriesRefused) as caught:
            pb_mlr.run_b1(tmp / "out.json", executor=wrong)
        self.assertIn("executor is the frozen one", str(caught.exception))
        self.assertFalse((tmp / "out.json").exists(), "a refusal writes no experimental record")


class PreflightTest(unittest.TestCase):
    """The dry run resolves the real configuration and buys nothing."""

    maxDiff = None

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-b1-pre-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_preflight_reports_the_frozen_identity_order_and_bounds(self):
        report = pb_mlr.b1_preflight(executor=None)
        self.assertEqual(report["experiment"], pb_mlr.B1["experiment"])
        self.assertTrue(report["identity_matches_the_freeze"])
        self.assertEqual(report["n_pairs"], 6)
        self.assertEqual(report["slots"], 12)
        self.assertEqual(report["max_attempts_per_slot"], 3)
        self.assertEqual(report["ceiling"], 0.50)
        self.assertEqual(report["reserve"], 0.10)
        self.assertEqual([(s["pair"], s["arm"]) for s in report["order"]],
                         [(1, "full"), (1, "contract"), (2, "contract"), (2, "full"),
                          (3, "full"), (3, "contract"), (4, "contract"), (4, "full"),
                          (5, "full"), (5, "contract"), (6, "contract"), (6, "full")])

    def test_preflight_confirms_the_committed_frozen_fixture_and_document(self):
        report = pb_mlr.b1_preflight(executor=None)
        passed = {c["check"] for c in report["checks"] if c["ok"]}
        for required in ("the preregistration is the committed frozen one",
                         "fixture is the frozen one", "task is the frozen one",
                         "public contract is the frozen one", "hidden oracle is the frozen one",
                         "the resolved configuration is the frozen stack's fixture"):
            self.assertIn(required, passed)

    def test_preflight_without_an_eligible_executor_is_not_launchable(self):
        report = pb_mlr.b1_preflight(executor=None)
        self.assertFalse(report["launchable"])
        self.assertIn("executor is the frozen one", report["blocked_by"])

    def test_preflight_reports_host_derived_identities_beside_the_frozen_host_and_never_compares(self):
        report = pb_mlr.b1_preflight(executor=None)
        host = report["host_derived_identities"]
        self.assertEqual(host["recorded_on_the_frozen_host"]["interpreter"], "CPython 3.9.6")
        self.assertEqual(host["recorded_on_the_frozen_host"]["boundary_identity"],
                         "b88bd43109184459")
        self.assertIn("host difference", host["note"])
        names = {c["check"] for c in report["checks"]}
        self.assertNotIn("interpreter is the frozen one", names,
                         "a host-derived identity must never become a launch condition")

    def test_the_host_scan_is_informational_and_does_not_block(self):
        """The repository is a scanned root and holds the canonical fixture, always."""
        report = pb_mlr.b1_preflight(executor=None)
        scan = next(c for c in report["checks"] if c["check"].startswith("host scan"))
        self.assertFalse(scan["blocking"])
        self.assertNotIn(scan["check"], report["blocked_by"])

    def test_preflight_writes_no_experimental_record(self):
        before = sorted(p.name for p in (Path(__file__).resolve().parents[1]
                                         / "evals" / "results").glob("*.json"))
        pb_mlr.b1_preflight(executor=None)
        after = sorted(p.name for p in (Path(__file__).resolve().parents[1]
                                        / "evals" / "results").glob("*.json"))
        self.assertEqual(before, after)


class FrozenStackFidelityTest(unittest.TestCase):
    """The machine-readable stack is only safe while it cannot drift from the document."""

    maxDiff = None

    def setUp(self):
        raw = (Path(__file__).resolve().parents[1]
               / pb_mlr.B1["preregistration"]).read_text(encoding="utf-8")
        # Whitespace-normalised, because the document is hard-wrapped: a phrase the freeze depends
        # on may fall across a line break, and a test that failed on the wrap rather than on the
        # meaning would teach the next reader to loosen the assertion.
        self.text = " ".join(raw.split())

    def test_the_preregistration_is_the_one_the_stack_was_read_from(self):
        document = Path(__file__).resolve().parents[1] / pb_mlr.B1["preregistration"]
        self.assertEqual(_mlr.digest_file(document), pb_mlr.B1["preregistration_sha256"])

    def test_every_frozen_digest_appears_in_the_document(self):
        for key in ("source_digest", "task_sha256", "contract_sha256", "gate_sha256",
                    "executor_sha256"):
            with self.subTest(key=key):
                self.assertIn(pb_mlr.B1[key], self.text)

    def test_every_frozen_setting_appears_in_the_document(self):
        for value in (pb_mlr.B1["model"], pb_mlr.B1["oracle"], pb_mlr.B1["package"],
                      pb_mlr.B1["price_id"], pb_mlr.B1["telemetry_version"],
                      pb_mlr.B1["profile_version"], pb_mlr.B1["role"],
                      pb_mlr.B1["permission_flag"]):
            with self.subTest(value=value):
                self.assertIn(value, self.text)

    def test_the_host_derived_identities_are_the_ones_the_document_calls_host_derived(self):
        for value in pb_mlr.B1["host_derived"].values():
            self.assertIn(value, self.text)
        self.assertIn("recorded per slot as execution facts", self.text)

    def test_n_the_retry_cap_and_the_ceiling_are_the_document_s(self):
        self.assertIn("N = 6 pairs", self.text)
        self.assertIn("three per slot", self.text)
        self.assertIn("$0.50 ceiling", self.text)
        self.assertIn("$0.10 reserve", self.text)


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()


def setUpModule() -> None:
    """One host-state suite at a time. asserts cross-slot isolation against host temp state."""
    _host_serial.serialise(__name__)


def tearDownModule() -> None:
    _host_serial.release()
