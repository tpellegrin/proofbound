"""Deterministic validity tests for the modularity and local-reasoning fixture.

The fixture's whole claim is that it presents two comparable views of one working system, differing
only in whether a module's source is part of the repository. These tests hold that claim up: same
runtime, same contract, same tasks, same behaviour, one intended difference, and an external task
that is genuinely solvable from the contract alone.

They also pin the reason the approved internal control was not built — that editing the readable
copy does not change the running system — so the gap cannot be quietly forgotten.

Nothing here invokes a model.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _mlr  # noqa: E402

FIXTURE = _mlr.FIXTURE
HIDDEN = FIXTURE / "hidden"
REFERENCE = FIXTURE / "reference"


def apply_reference(built: dict, name: str) -> None:
    source = REFERENCE / name
    for src in sorted(source.rglob("*")):
        if src.is_file():
            dst = Path(built["workspace"]) / src.relative_to(source)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())


class Built:
    """Both arms materialised into one temporary directory, torn down together."""

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.arms = {arm: _mlr.materialise(arm, self.tmp / arm) for arm in _mlr.ARMS}
        return self.arms

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


class SameSystemTest(unittest.TestCase):
    """Whatever else differs, both arms must be running the same software."""

    maxDiff = None

    def test_both_arms_execute_the_same_module(self):
        with Built() as arms:
            self.assertEqual(arms[_mlr.FULL]["runtime_digest"],
                             arms[_mlr.CONTRACT]["runtime_digest"])

    def test_the_readable_copy_is_the_module_that_runs(self):
        """A copy that could drift would let the arms compare different implementations."""
        with Built() as arms:
            self.assertEqual(arms[_mlr.FULL]["vendored_digest"],
                             _mlr.digest_tree(FIXTURE / "runtime" / "objectstore"))
            self.assertIsNone(arms[_mlr.CONTRACT]["vendored_digest"])

    def test_both_arms_expose_an_identical_contract(self):
        with Built() as arms:
            self.assertEqual(arms[_mlr.FULL]["contract_sha256"],
                             arms[_mlr.CONTRACT]["contract_sha256"])

    def test_both_arms_pass_the_same_baseline_behaviour(self):
        with Built() as arms:
            for arm, built in arms.items():
                with self.subTest(arm=arm):
                    result = _mlr.run_tests(built, data_root=Path(built["workspace"]).parent / "d")
                    self.assertEqual(result.returncode, 0,
                                     (result.stdout + result.stderr)[-800:])

    def test_the_only_difference_between_the_arms_is_the_readable_copy(self):
        with Built() as arms:
            diff = _mlr.arm_difference(arms[_mlr.FULL], arms[_mlr.CONTRACT])
            self.assertEqual(diff["unintended"], [], "an unintended arm difference exists")
            self.assertEqual(diff["only_contract"], [])
            self.assertTrue(diff["only_full"])
            for path in diff["only_full"]:
                self.assertTrue(path.startswith(_mlr.VENDORED.as_posix() + "/"))

    def test_the_readable_copy_is_not_importable(self):
        """If it were, the arms would execute different files that merely start out identical."""
        with Built() as arms:
            built = arms[_mlr.FULL]
            probe = self.probe(built, "import objectstore; print(objectstore.__file__)")
            self.assertEqual(probe.returncode, 0, probe.stderr[-400:])
            resolved = Path(probe.stdout.strip())
            self.assertFalse(str(resolved).startswith(str(Path(built["workspace"]).resolve())),
                             f"the workspace copy is on sys.path: {resolved}")

    @staticmethod
    def probe(built, code):
        import subprocess
        return subprocess.run([sys.executable, "-B", "-c", code], cwd=built["workspace"],
                              env=_mlr.environment(built), capture_output=True, text=True,
                              check=False)


class ExternalTaskTest(unittest.TestCase):
    """Exercise, contract sufficiency and responsibility validity, for the task that was built."""

    maxDiff = None

    def test_the_hidden_gate_fails_before_the_task_is_done(self):
        """Otherwise the probe measures nothing."""
        with Built() as arms:
            for arm, built in arms.items():
                with self.subTest(arm=arm):
                    result = _mlr.run_gate(built, HIDDEN / "external_test.py",
                                           data_root=Path(built["workspace"]).parent / "before")
                    self.assertNotEqual(result.returncode, 0)

    def test_the_reference_solution_satisfies_the_gate_in_both_arms(self):
        with Built() as arms:
            for arm, built in arms.items():
                with self.subTest(arm=arm):
                    apply_reference(built, "external")
                    result = _mlr.run_gate(built, HIDDEN / "external_test.py",
                                           data_root=Path(built["workspace"]).parent / "after")
                    self.assertEqual(result.returncode, 0,
                                     (result.stdout + result.stderr)[-900:])

    def test_the_reference_solution_keeps_the_services_own_tests_passing(self):
        with Built() as arms:
            built = arms[_mlr.CONTRACT]
            apply_reference(built, "external")
            result = _mlr.run_tests(built, data_root=Path(built["workspace"]).parent / "own")
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-800:])

    def test_the_reference_solution_changes_only_application_code(self):
        """Responsibility validity: an external task must not need the module or its contract."""
        changed = sorted(p.relative_to(REFERENCE / "external").as_posix()
                         for p in (REFERENCE / "external").rglob("*") if p.is_file())
        self.assertTrue(changed)
        for path in changed:
            self.assertTrue(path.startswith("app/"), f"reference touches {path}")

    def test_the_gate_asserts_behaviour_and_never_structure(self):
        gate = (HIDDEN / "external_test.py").read_text(encoding="utf-8")
        # Private helpers included: a gate that reaches into one would break when an agent
        # legitimately restructures the application, and would then be measuring shape.
        for token in ("import objectstore", "objectstore.", "exports._", "api._",
                      "_backend", "_checksum", "sha256", "third_party"):
            with self.subTest(token=token):
                self.assertNotIn(token, gate)

    def test_the_task_text_is_one_artifact_shared_by_both_arms(self):
        """No arm-specific wording can exist if there is only one file."""
        task = (FIXTURE / "tasks" / "external.md").read_text(encoding="utf-8")
        low = task.lower()
        for token in ("without inspecting", "do not read", "contract only", "third_party",
                      "implementation is hidden", "modular"):
            with self.subTest(token=token):
                self.assertNotIn(token, low)


class ContractTest(unittest.TestCase):
    """The contract must state external semantics, not internals, and must not solve the task."""

    maxDiff = None

    def setUp(self):
        self.contract = (FIXTURE / "base" / "docs" / "storage-contract.md").read_text(
            encoding="utf-8")

    def test_it_states_the_facts_the_external_task_needs(self):
        low = self.contract.lower()
        self.assertIn("notfound", low)
        self.assertIn("safe to repeat", low)
        self.assertIn("immediately visible", low)

    def test_it_leaks_no_implementation_detail(self):
        low = self.contract.lower()
        for token in ("checksum", "sha256", "retry", "backoff", "attempts", "chunk", "fan-out",
                      "filesystem", "directory", "tempfile", "os.replace", "_store", "_backend"):
            with self.subTest(token=token):
                self.assertNotIn(token, low)

    def test_it_does_not_solve_the_task(self):
        """Module semantics belong here; what the service should return does not."""
        low = self.contract.lower()
        # Service-domain vocabulary, not ordinary English: the contract may say that absence is
        # "reported", and must not say anything about exports, statuses or handlers.
        for token in ("404", "403", "201", "http", "export", "endpoint", "handler",
                      "the report", "account"):
            with self.subTest(token=token):
                self.assertNotIn(token, low)

    def test_it_teaches_nothing_about_the_hypothesis(self):
        low = self.contract.lower()
        for token in ("encapsulat", "you do not need", "boundary owns", "well designed",
                      "modular", "implementation detail is hidden"):
            with self.subTest(token=token):
                self.assertNotIn(token, low)

    def test_the_contract_is_much_smaller_than_the_implementation(self):
        """Descriptive only, and not a threshold: if they were comparable there would be nothing
        to substitute, and the experiment would have no manipulation to make."""
        contract = len(self.contract.encode("utf-8"))
        implementation = sum(p.stat().st_size for p in
                             (FIXTURE / "runtime" / "objectstore").rglob("*.py"))
        self.assertLess(contract, implementation)


class InternalControlGapTest(unittest.TestCase):
    """The approved control could not be built. Pin the reason so it cannot be forgotten."""

    maxDiff = None

    def test_editing_the_readable_copy_does_not_change_the_running_system(self):
        with Built() as arms:
            built = arms[_mlr.FULL]
            vendored = Path(built["workspace"]) / _mlr.VENDORED / "objectstore" / "_store.py"
            vendored.write_text(vendored.read_text().replace("_ATTEMPTS = 3", "_ATTEMPTS = 5"))
            probe = SameSystemTest.probe(
                built, "from objectstore import _store; print(_store._ATTEMPTS)")
            self.assertEqual(probe.stdout.strip(), "3",
                             "the workspace copy is executing; the arms would differ")
            self.assertEqual(_mlr.digest_tree(Path(built["runtime"])), built["runtime_digest"])

    def test_no_internal_control_task_is_frozen_in_this_revision(self):
        task = (FIXTURE / "tasks" / "internal-control.md").read_text(encoding="utf-8")
        self.assertIn("NOT BUILT", task)
        self.assertFalse((HIDDEN / "internal_test.py").exists())
        self.assertFalse((REFERENCE / "internal").exists())


if __name__ == "__main__":
    unittest.main()
