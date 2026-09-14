#!/usr/bin/env python3
"""The eventbus fixture: does it hold the treatment, and does the qualified machinery read it?

Fixture B replicates the MLR question across a structurally different boundary. These check the
things that would make the replication uninterpretable before any model is paid to run against it:
that the treatment actually withholds source, that the executed module is the compiled one in both
arms, that the oracle accepts materially different correct solutions and rejects wrong ones, that
nothing in the workspace leaks the implementation, and that `mlr-context-6` reads the new module
without changing what any origin means.

Nothing here makes a provider call.
"""
from __future__ import annotations

import platform
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import _lineage       # noqa: E402
import _mlr           # noqa: E402
import _mlr_context   # noqa: E402

B = _mlr.EVENTBUS
ORACLE = B.root / "hidden" / "external_test.py"


def materialise(arm):
    tmp = Path(tempfile.mkdtemp(prefix="pb-fb-"))
    built = _mlr.materialise(arm, tmp / "arm", fixture=B.root)
    return tmp, built


def events(parts):
    return [{"ordinal": n, "part_id": f"p{n}", "message_id": "m", "time_created": n,
             "role": "assistant", "summary": False, "part": p, "message": {}}
            for n, p in enumerate(parts)]


def call():
    return {"type": "step-start"}


def read(path, output):
    return {"type": "tool", "tool": "read",
            "state": {"input": {"filePath": str(path)}, "output": output, "status": "completed"}}


def bash(command, output):
    return {"type": "tool", "tool": "bash",
            "state": {"input": {"command": command}, "output": output, "status": "completed"}}


class FixtureAIsUnchangedTest(unittest.TestCase):
    """The refactor that made the machinery fixture-generic must not move fixture A by a byte."""

    maxDiff = None

    def test_the_q1_fixture_still_materialises_to_its_recorded_digests(self):
        for arm, workspace in ((_mlr.FULL, "9053040a837f"), (_mlr.CONTRACT, "c93d39f6722f")):
            with self.subTest(arm=arm):
                tmp = Path(tempfile.mkdtemp(prefix="pb-fa-"))
                self.addCleanup(shutil.rmtree, tmp, True)
                built = _mlr.materialise(arm, tmp / "arm")
                # Content-derived, so these are the same wherever and whenever they are computed.
                self.assertEqual(built["workspace_digest"][:12], workspace)
                self.assertEqual(built["source_digest"][:16], "1f83c3b1f22ab756")
                self.assertEqual(built["contract_sha256"][:16], "af3d3e9be15b51ed")
                self.assertEqual(built["package"], "objectstore")
                # Compiled structure belongs to the interpreter that compiled it. The frozen value
                # is CPython 3.9.6's; under any other interpreter the relation is what holds.
                if platform.python_version().startswith("3.9."):
                    self.assertEqual(built["runtime_structure"][:16], "28ba66e1cd49b157")

    def test_the_q1_hermeticity_rule_is_unchanged(self):
        self.assertEqual(_mlr.preflight_identity()[:16], "dcbf34fb63821980")


class TreatmentTest(unittest.TestCase):
    """What each arm can read."""

    maxDiff = None

    def test_full_exposes_the_module_source_and_contract_does_not(self):
        for arm, expected in ((_mlr.FULL, True), (_mlr.CONTRACT, False)):
            with self.subTest(arm=arm):
                tmp, built = materialise(arm)
                self.addCleanup(shutil.rmtree, tmp, True)
                copy = Path(built["workspace"]) / built["vendored"] / built["package"]
                self.assertEqual(copy.is_dir(), expected)
                if expected:
                    self.assertTrue(sorted(copy.glob("*.py")))

    def test_both_arms_execute_the_compiled_runtime_not_the_readable_copy(self):
        """The mistake that killed the approved internal control, checked on the new fixture."""
        for arm in _mlr.ARMS:
            with self.subTest(arm=arm):
                tmp, built = materialise(arm)
                self.addCleanup(shutil.rmtree, tmp, True)
                report = _mlr.executed_module_is_not_the_readable_copy(built)
                self.assertTrue(report["from_runtime"], report)

    def test_both_arms_share_runtime_structure_and_contract(self):
        tmp_f, full = materialise(_mlr.FULL)
        tmp_c, contract = materialise(_mlr.CONTRACT)
        self.addCleanup(shutil.rmtree, tmp_f, True)
        self.addCleanup(shutil.rmtree, tmp_c, True)
        self.assertEqual(full["runtime_structure"], contract["runtime_structure"])
        self.assertEqual(full["contract_sha256"], contract["contract_sha256"])
        self.assertEqual(full["source_digest"], contract["source_digest"])

    def test_the_only_workspace_difference_is_the_vendored_source(self):
        tmp_f, full = materialise(_mlr.FULL)
        tmp_c, contract = materialise(_mlr.CONTRACT)
        self.addCleanup(shutil.rmtree, tmp_f, True)
        self.addCleanup(shutil.rmtree, tmp_c, True)
        difference = _mlr.arm_difference(full, contract)
        self.assertEqual(difference["only_contract"], [])
        prefix = B.vendored.as_posix() + "/"
        self.assertTrue(difference["only_full"])
        for path in difference["only_full"]:
            self.assertTrue(path.startswith(prefix), path)

    def test_the_shipped_suite_passes_in_both_arms(self):
        for arm in _mlr.ARMS:
            with self.subTest(arm=arm):
                tmp, built = materialise(arm)
                self.addCleanup(shutil.rmtree, tmp, True)
                result = _mlr.run_tests(built, data_root=tmp / "data")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class LeakTest(unittest.TestCase):
    """CONTRACT must not be able to read the implementation by another route."""

    maxDiff = None

    def setUp(self):
        self.marks = _lineage.source_fingerprint(B.source)
        self.tmp, self.built = materialise(_mlr.CONTRACT)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.workspace = Path(self.built["workspace"])

    def test_no_module_source_file_exists_anywhere_in_the_workspace(self):
        """By the module's distinctive file names.

        `__init__.py` is what every Python package calls its entry point, so a bare name match
        would flag the application's own packages. The private stems are distinctive on their own,
        which is the same distinction `_lineage.module_reference` makes; a copy of the entry point
        would be caught by content in the next test, and is.
        """
        stems = {p.name for p in B.source.glob("*.py") if not p.name.startswith("__")}
        self.assertTrue(stems, "the module must have private files worth hiding")
        found = [p.relative_to(self.workspace).as_posix()
                 for p in self.workspace.rglob("*.py") if p.name in stems]
        self.assertEqual(found, [], "a readable copy reached the contract workspace")

    def test_no_file_in_the_workspace_carries_the_implementation_verbatim(self):
        offenders = []
        for path in self.workspace.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            hit = _lineage.source_in(text, self.marks)
            if hit["lines"]:
                offenders.append((path.relative_to(self.workspace).as_posix(), hit["lines"]))
        # The package docstring is public surface and is legitimately reachable in both arms;
        # it is the only overlap the contract documents, and it is measured, not hidden.
        self.assertEqual(offenders, [], f"implementation text reachable in contract: {offenders}")

    def test_the_public_contract_is_not_the_implementation_in_prose(self):
        text = (self.workspace / B.contract).read_text(encoding="utf-8")
        self.assertEqual(_lineage.source_in(text, self.marks)["lines"], 0)

    def test_the_runtime_ships_no_source_beside_the_bytecode(self):
        runtime = Path(self.built["runtime"])
        self.assertTrue(sorted((runtime / B.package).glob("*.pyc")))
        self.assertEqual(sorted(runtime.rglob("*.py")), [])

    def test_the_hermeticity_rule_covers_the_new_module(self):
        rule = _mlr.hermeticity(fixture=B.root)
        controlled = next(k for k in rule["sensitive"]
                          if k.category == "controlled-evidence")
        source = sorted(B.source.glob("*.py"))
        self.assertEqual(sorted(controlled.digests), sorted(_mlr.digest_file(p) for p in source))
        self.assertTrue(controlled.marks)


class OracleTest(unittest.TestCase):
    """The gate must judge behaviour, not shape."""

    maxDiff = None

    def gate(self, realization=None):
        tmp = Path(tempfile.mkdtemp(prefix="pb-fb-gate-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        built = _mlr.materialise(_mlr.CONTRACT, tmp / "arm", fixture=B.root)
        if realization is not None:
            shutil.copyfile(realization, Path(built["workspace"]) / "app" / "api.py")
        gate = _mlr.run_gate(built, ORACLE, data_root=tmp / "gate")
        suite = _mlr.run_tests(built, data_root=tmp / "suite")
        return gate.returncode == 0, suite.returncode == 0

    def test_the_unfixed_fixture_fails_the_gate(self):
        """If the task were already done, the experiment would measure nothing."""
        passed, suite = self.gate()
        self.assertFalse(passed)
        self.assertTrue(suite, "the fixture's own suite must pass before the task is done")

    def test_every_valid_solution_is_accepted(self):
        realizations = sorted((B.root / "realizations" / "valid").glob("*.py"))
        self.assertGreaterEqual(len(realizations), 2, "one valid shape proves nothing about shape")
        for path in realizations:
            with self.subTest(realization=path.stem):
                passed, suite = self.gate(path)
                self.assertTrue(passed, f"{path.stem} is correct and was rejected")
                self.assertTrue(suite)

    def test_every_invalid_solution_is_rejected(self):
        realizations = sorted((B.root / "realizations" / "invalid").glob("*.py"))
        self.assertGreaterEqual(len(realizations), 3)
        for path in realizations:
            with self.subTest(realization=path.stem):
                passed, _ = self.gate(path)
                self.assertFalse(passed, f"{path.stem} is wrong and was accepted")

    def test_the_two_valid_solutions_are_materially_different(self):
        a, b = sorted((B.root / "realizations" / "valid").glob("*.py"))
        first, second = a.read_text(encoding="utf-8"), b.read_text(encoding="utf-8")
        self.assertNotEqual(first, second)
        self.assertIn("failures", first)
        self.assertNotIn("receipt.failures", second,
                         "the second solution must not reach the answer the same way")


class AttributionCompatibilityTest(unittest.TestCase):
    """`mlr-context-6` must read the new module without any origin changing meaning."""

    maxDiff = None

    def test_a_source_read_in_full_is_direct_implementation_source(self):
        tmp, built = materialise(_mlr.FULL)
        self.addCleanup(shutil.rmtree, tmp, True)
        path = Path(built["workspace"]) / built["vendored"] / built["package"] / "_dispatch.py"
        led = _mlr_context.ledger(
            events([call(), read(path, path.read_text(encoding="utf-8")), call()]), built)
        item = [i for i in led["items"] if i["kind"].startswith("tool:")][0]
        self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
        self.assertEqual(item["basis"], _mlr_context.BASIS_ARTIFACT)
        self.assertGreater(led["implementation_source_unique_bytes"], 0)

    def test_the_public_docstring_through_the_runtime_is_not_source(self):
        """The R6 property, on the new fixture: its docstring is in the fingerprint too."""
        doc = (B.source / "__init__.py").read_text(encoding="utf-8").split('"""')[1]
        self.assertGreater(_lineage.source_in(doc, _lineage.source_fingerprint(B.source))["lines"],
                           0, "the calibration only means something if the text overlaps")
        tmp, built = materialise(_mlr.CONTRACT)
        self.addCleanup(shutil.rmtree, tmp, True)
        led = _mlr_context.ledger(
            events([call(), bash('python3 -c "import eventbus; print(eventbus.__doc__)"', doc),
                    call()]), built)
        item = [i for i in led["items"] if i["kind"].startswith("tool:")][0]
        self.assertEqual(item["source_bytes"], 0)
        self.assertNotEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
        self.assertEqual(led["implementation_source_unique_bytes"], 0)

    def test_a_disassembly_in_contract_is_runtime_representation(self):
        body = "\n".join(["Disassembly of <code object _fan_out>:"] +
                         [f"  {n}    {n * 2} LOAD_GLOBAL   {n} (_registry)" for n in range(1, 40)])
        tmp, built = materialise(_mlr.CONTRACT)
        self.addCleanup(shutil.rmtree, tmp, True)
        led = _mlr_context.ledger(
            events([call(), bash("python3 -c 'import dis, eventbus; dis.dis(eventbus)'", body),
                    call()]), built)
        self.assertEqual(led["implementation_source_unique_bytes"], 0)
        self.assertGreater(led["implementation_runtime_unique_bytes"], 0)
        self.assertEqual(led["unresolved"]["items"], 0)
        self.assertEqual(led["unresolved"]["components"], 0)
        self.assertEqual(led["contradictions"], [])

    def test_reading_one_fixture_does_not_contaminate_the_next(self):
        """A process that attributes both fixtures must answer about the right module each time.

        The fingerprints are cached per fixture and selected from the mapping handed in. If
        selection were left over from the previous call, a ledger would answer about whichever
        module happened to be read first, which is a confident wrong answer of exactly the kind
        `mlr-context-6` exists to stop.
        """
        tmp_b, built_b = materialise(_mlr.CONTRACT)
        self.addCleanup(shutil.rmtree, tmp_b, True)
        _mlr_context.ledger(events([call()]), built_b)

        tmp_a = Path(tempfile.mkdtemp(prefix="pb-fa-"))
        self.addCleanup(shutil.rmtree, tmp_a, True)
        built_a = _mlr.materialise(_mlr.FULL, tmp_a / "arm")
        source = (_mlr.OBJECTSTORE.source / "_store.py").read_text(encoding="utf-8")
        path = Path(built_a["workspace"]) / built_a["vendored"] / "objectstore" / "_store.py"
        led = _mlr_context.ledger(events([call(), read(path, source), call()]), built_a)
        self.assertGreater(led["implementation_source_unique_bytes"], 0,
                           "objectstore source read after an eventbus session must still be source")

    def test_the_attribution_version_did_not_move(self):
        import pb_mlr
        config = pb_mlr.configuration(model="m", samples=1, arms=list(_mlr.ARMS))
        self.assertEqual(config["telemetry_version"], "mlr-context-6")


class ModuleBehaviourTest(unittest.TestCase):
    """The guarantees the contract makes, checked against the module that makes them."""

    maxDiff = None

    def setUp(self):
        sys.path.insert(0, str(B.root / "runtime"))
        self.addCleanup(lambda: sys.path.remove(str(B.root / "runtime")))
        import eventbus
        self.bus = eventbus
        eventbus.reset()
        self.addCleanup(eventbus.reset)

    def test_a_failing_consumer_does_not_stop_the_others(self):
        seen = []
        self.bus.subscribe("t", "a", lambda e: seen.append("a"))
        self.bus.subscribe("t", "b", lambda e: (_ for _ in ()).throw(RuntimeError("no")))
        self.bus.subscribe("t", "c", lambda e: seen.append("c"))
        receipt = self.bus.publish("t", {"n": 1})
        self.assertEqual(sorted(seen), ["a", "c"])
        self.assertEqual(receipt.failed, ("b",))
        self.assertEqual(sorted(receipt.delivered), ["a", "c"])
        self.assertFalse(receipt.ok)

    def test_publish_does_not_raise_because_a_consumer_did(self):
        self.bus.subscribe("t", "a", lambda e: (_ for _ in ()).throw(ValueError("boom")))
        receipt = self.bus.publish("t", {})
        self.assertEqual(receipt.failures[0][0], "a")
        self.assertIn("boom", receipt.failures[0][1])

    def test_each_consumer_receives_its_own_copy(self):
        seen = []
        self.bus.subscribe("t", "a", lambda e: e.__setitem__("x", 99))
        self.bus.subscribe("t", "b", lambda e: seen.append(e["x"]))
        event = {"x": 1}
        self.bus.publish("t", event)
        self.assertEqual(seen, [1])
        self.assertEqual(event["x"], 1, "the caller's own object must not change either")

    def test_a_name_may_not_be_registered_twice_for_a_topic(self):
        self.bus.subscribe("t", "a", lambda e: None)
        with self.assertRaises(self.bus.DuplicateConsumer):
            self.bus.subscribe("t", "a", lambda e: None)

    def test_a_topic_with_no_consumers_is_not_an_error(self):
        receipt = self.bus.publish("quiet", {})
        self.assertTrue(receipt.ok)
        self.assertEqual(receipt.delivered, ())

    def test_publishing_from_inside_a_handler_is_deferred(self):
        order = []
        self.bus.subscribe("outer", "a", lambda e: (order.append("a"),
                                                    self.bus.publish("inner", {})))
        self.bus.subscribe("outer", "b", lambda e: order.append("b"))
        self.bus.subscribe("inner", "c", lambda e: order.append("c"))
        self.bus.publish("outer", {})
        self.assertEqual(order[-1], "c", "the nested event lands after the current fan-out")
        self.assertEqual(sorted(order[:-1]), ["a", "b"])


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
