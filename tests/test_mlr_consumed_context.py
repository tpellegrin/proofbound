"""Consumed-context attribution: what reached a model call, and where it came from.

MLR-C2 could say what an arm *made available* and what a tool *opened*. Neither is what the
experiment measures. These tests prove the missing step against the executor Proofbound actually
runs — the OpenCode session database `run_worker.py` points `OPENCODE_DB` at — using synthetic
sessions in exactly that schema, so no model is invoked to validate the instrument that will
measure one.

The probe that matters most is the one that refuses to give `contract` a free zero: an agent that
disassembles the module has obtained implementation-derived representation, and a metric that
scored it as "no implementation information" would report a substitution that did not happen.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _mlr            # noqa: E402
import _mlr_context    # noqa: E402
import _mlr_run        # noqa: E402

SCHEMA = """
CREATE TABLE message (id text PRIMARY KEY, session_id text NOT NULL,
                      time_created integer NOT NULL, time_updated integer NOT NULL,
                      data text NOT NULL);
CREATE TABLE part (id text PRIMARY KEY, message_id text NOT NULL, session_id text NOT NULL,
                   time_created integer NOT NULL, time_updated integer NOT NULL,
                   data text NOT NULL);
"""


def _clean_environment(**_kw):
    """A hermetic environment, so a unit test of the series machinery does not depend on the state of
    the host it happens to run on. The real preflight is exercised in its own suite."""
    return {"status": "clean", "hermeticity_identity": "test", "findings": [],
            "scanned_roots": [], "excluded_roots": [], "claim": "test", "unreadable": []}


class Session:
    """A synthetic OpenCode session in the real schema, built one part at a time."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        self.n = 0
        self.messages = 0

    def message(self, role: str, **data) -> str:
        self.messages += 1
        mid = f"msg_{self.messages:04d}"
        self.conn.execute("INSERT INTO message VALUES (?,?,?,?,?)",
                          (mid, "ses", self.messages, self.messages,
                           json.dumps({"role": role, **data})))
        return mid

    def part(self, mid: str, data: dict) -> None:
        self.n += 1
        self.conn.execute("INSERT INTO part VALUES (?,?,?,?,?,?)",
                          (f"prt_{self.n:04d}", mid, "ses", self.n, self.n, json.dumps(data)))

    def call(self, mid: str, *, input_tokens: int = 0, cost: float = 0.0) -> None:
        """One model call: it begins, and it finishes with the provider's own usage."""
        self.part(mid, {"type": "step-start"})
        self.part(mid, {"type": "step-finish", "tokens": {
            "input": input_tokens, "output": 0, "reasoning": 0,
            "cache": {"read": 0, "write": 0}}, "cost": cost})

    def tool(self, mid: str, tool: str, arguments: dict, output: str, *,
             truncated: bool = False) -> None:
        self.part(mid, {"type": "tool", "tool": tool, "callID": f"c{self.n}",
                        "state": {"status": "completed", "input": arguments, "output": output,
                                  "metadata": {"truncated": truncated}}})

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()


class Arms:
    """Both arms materialised, so attribution is exercised against real paths."""

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.arms = {arm: _mlr.materialise(arm, self.tmp / arm) for arm in _mlr.ARMS}
        self.db = self.tmp / "worker.db"
        return self

    def session(self) -> Session:
        if self.db.exists():
            self.db.unlink()
        return Session(self.db)

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


def vendored(built) -> Path:
    return Path(built["workspace"]) / _mlr.VENDORED / "objectstore" / "_store.py"


class SourceConsumptionTest(unittest.TestCase):
    """The `full` arm's implementation source: read, not read, and read more than once."""

    maxDiff = None

    def test_a_source_read_is_attributed_and_measured(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            body = vendored(built).read_text(encoding="utf-8")
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "read", {"filePath": str(vendored(built))}, body)
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertEqual(led["implementation_source_unique_bytes"],
                             len(body.encode("utf-8")))
            self.assertEqual(led["by_provenance"][_mlr_context.IMPLEMENTATION_SOURCE]["items"], 1)

    def test_an_arm_that_never_opens_the_implementation_consumes_none_of_it(self):
        """Availability is not consumption: `full` carries the source whether or not it is read."""
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "read", {"filePath": "app/exports.py"}, "def build_export(): ...")
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)
            self.assertGreater(led["by_provenance"][_mlr_context.APPLICATION]["unique_bytes"], 0)

    def test_an_absolute_read_of_the_implementation_is_not_discarded(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            absolute = str(vendored(built).resolve())
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "read", {"filePath": absolute}, "x" * 500)
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertEqual(led["implementation_source_unique_bytes"], 500)

    def test_a_search_is_attributed_by_what_it_returned(self):
        """MLR-C3D-R3 changed this rule, and the change is the point.

        A search used to be called source because one of the paths it returned sat under the module.
        That is how a `glob` listing four file paths was charged 1,382 bytes to the primary measurand
        with no source line in it. A search that returns the module's *lines* is source; a search that
        returns its *names* is metadata; the tool is the same either way.
        """
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            module = (_mlr.FIXTURE / "runtime" / "objectstore" / "_store.py").read_text()
            body = "\n".join(f"{_mlr.VENDORED.as_posix()}/objectstore/_store.py:{n}: {line}"
                              for n, line in enumerate(module.splitlines(), start=1)
                              if len(line.strip()) >= 40)
            names = f"{_mlr.VENDORED.as_posix()}/objectstore/_store.py:41: def put(...)"
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "grep", {"pattern": "def put"}, body)
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertGreater(led["implementation_source_unique_bytes"], 0)

            b = Arms()
            with b as c:
                s = c.session()
                m = s.message("assistant")
                s.call(m)
                s.tool(m, "grep", {"pattern": "def put"}, names)
                s.call(m)
                s.close()
                only_names = _mlr_context.consumed(c.db, c.arms[_mlr.FULL])
            self.assertEqual(only_names["implementation_source_unique_bytes"], 0)
            self.assertGreater(only_names["implementation_metadata"]["references"], 0)


class RuntimeRepresentationTest(unittest.TestCase):
    """`contract` has no source to read, and that must not be recorded as no implementation."""

    maxDiff = None

    def test_disassembly_is_implementation_derived_and_not_a_free_zero(self):
        with Arms() as a:
            built = a.arms[_mlr.CONTRACT]
            listing = "\n".join(f"  {i} LOAD_GLOBAL  _checksum" for i in range(200))
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "bash",
                   {"command": "python -c 'import dis, objectstore; dis.dis(objectstore.put)'"},
                   listing)
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)
            self.assertGreater(led["implementation_runtime_unique_bytes"], 0)
            # Source, runtime and metadata are separate units and are never summed.
            self.assertGreater(led["implementation_derived"]["runtime_unique_bytes"], 0)
            self.assertEqual(led["implementation_derived"]["source_unique_bytes"], 0)

    def test_reading_module_constants_is_implementation_derived(self):
        """The two hidden decisions are two ordinary lines away; the ledger must see that."""
        with Arms() as a:
            built = a.arms[_mlr.CONTRACT]
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "bash",
                   {"command": "python -c 'from objectstore import _store; print(vars(_store))'"},
                   "{'_ATTEMPTS': 3, '_FANOUT': 2}")
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertGreater(led["implementation_runtime_unique_bytes"], 0)

    def test_running_the_service_is_behaviour_and_is_kept_apart(self):
        with Arms() as a:
            built = a.arms[_mlr.CONTRACT]
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "bash", {"command": "python -m unittest discover -s tests"}, "OK\n")
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertGreater(led["by_provenance"][_mlr_context.BEHAVIOUR]["unique_bytes"], 0)
            self.assertEqual(led["implementation_derived"]["source_unique_bytes"], 0)
            self.assertEqual(led["implementation_derived"]["runtime_unique_bytes"], 0)

    def test_internal_names_delivered_by_any_route_are_flagged(self):
        """A traceback through the module's interior is implementation-derived text, whoever asked."""
        with Arms() as a:
            built = a.arms[_mlr.CONTRACT]
            trace = ('Traceback:\n  File "objectstore/_store.py", line 61, in _with_retries\n'
                     "objectstore._store._ChecksumMismatch\n")
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "bash", {"command": "python -m unittest tests.test_service"}, trace)
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertEqual(led["items_carrying_internal_names"], 1)
            self.assertIn("_ChecksumMismatch", led["items"][-1]["internal_names"])


class DeliveryAccountingTest(unittest.TestCase):
    """Unique and repeated are different questions; truncation decides which bytes were received."""

    maxDiff = None

    def test_unique_and_delivered_volume_are_both_retained(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            body = "y" * 1000
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "read", {"filePath": str(vendored(built))}, body)
            for _ in range(5):
                s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            source = led["by_provenance"][_mlr_context.IMPLEMENTATION_SOURCE]
            self.assertEqual(source["unique_bytes"], 1000)
            self.assertEqual(source["delivered_bytes"], 5000)

    def test_the_same_text_read_twice_counts_once_as_unique_and_twice_as_delivered(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            body = "z" * 400
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "read", {"filePath": str(vendored(built))}, body)
            s.call(m)
            s.tool(m, "read", {"filePath": str(vendored(built))}, body)
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            source = led["by_provenance"][_mlr_context.IMPLEMENTATION_SOURCE]
            self.assertEqual(source["unique_bytes"], 400)
            self.assertEqual(source["items"], 2)
            self.assertEqual(source["delivered_bytes"], 400 * 2 + 400 * 1)

    def test_consumed_is_what_the_model_received_not_what_the_file_holds(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            whole = vendored(built).read_text(encoding="utf-8")
            shown = whole[:300]
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "read", {"filePath": str(vendored(built))}, shown, truncated=True)
            s.call(m)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertEqual(led["implementation_source_unique_bytes"], len(shown.encode()))
            self.assertLess(led["implementation_source_unique_bytes"],
                            len(whole.encode("utf-8")))
            self.assertEqual(led["truncated_items"], 1)

    def test_a_representation_that_entered_no_later_call_is_delivered_to_none(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            s = a.session()
            m = s.message("assistant")
            s.call(m)
            s.tool(m, "read", {"filePath": str(vendored(built))}, "w" * 100)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            source = led["by_provenance"][_mlr_context.IMPLEMENTATION_SOURCE]
            self.assertEqual(source["unique_bytes"], 100)
            self.assertEqual(source["delivered_bytes"], 0)


class SymmetryTest(unittest.TestCase):
    """The public representation is common treatment and must be recorded, never assumed away."""

    maxDiff = None

    def contract_session(self, a, built):
        text = (Path(built["workspace"]) / "docs" / "storage-contract.md").read_text(
            encoding="utf-8")
        s = a.session()
        m = s.message("assistant")
        s.call(m)
        s.tool(m, "read", {"filePath": "docs/storage-contract.md"}, text)
        s.call(m)
        s.close()
        return _mlr_context.consumed(a.db, built), text

    def test_the_contract_is_recorded_identically_in_both_arms(self):
        totals = {}
        for arm in _mlr.ARMS:
            with Arms() as a:
                led, text = self.contract_session(a, a.arms[arm])
                totals[arm] = led["by_provenance"][_mlr_context.PUBLIC_CONTRACT]["unique_bytes"]
                self.assertEqual(totals[arm], len(text.encode("utf-8")))
        self.assertEqual(totals[_mlr.FULL], totals[_mlr.CONTRACT])

    def test_the_task_prompt_is_harness_context_and_not_attributed_to_the_module(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            s = a.session()
            m = s.message("user")
            s.part(m, {"type": "text", "text": "DSD IMPLEMENTER for MLR-external. Read, in order:"})
            am = s.message("assistant")
            s.call(am)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertGreater(led["by_provenance"][_mlr_context.HARNESS]["unique_bytes"], 0)
            self.assertEqual(led["implementation_derived"]["source_unique_bytes"], 0)

    def test_provider_token_usage_is_retained_beside_the_byte_accounting(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            s = a.session()
            m = s.message("assistant")
            s.call(m, input_tokens=1200, cost=0.5)
            s.call(m, input_tokens=1800, cost=0.25)
            s.close()
            led = _mlr_context.consumed(a.db, built)
            self.assertEqual(led["model_calls"], 2)
            self.assertEqual(led["tokens"]["input"], 3000)
            self.assertEqual(led["tokens"]["calls_finished"], 2)
            self.assertAlmostEqual(led["tokens"]["cost"], 0.75)

    def test_a_summarised_session_is_flagged_so_delivery_is_read_as_an_upper_bound(self):
        with Arms() as a:
            built = a.arms[_mlr.FULL]
            s = a.session()
            m = s.message("assistant", summary=True)
            s.call(m)
            s.close()
            self.assertTrue(_mlr_context.consumed(a.db, built)["summarised"])

    def test_a_missing_database_is_an_empty_ledger_and_never_a_zero_reading(self):
        """No telemetry is a setup failure upstream; it must not look like "consumed nothing"."""
        with Arms() as a:
            led = _mlr_context.consumed(a.tmp / "absent.db", a.arms[_mlr.FULL])
            self.assertEqual(led["model_calls"], 0)
            self.assertEqual(led["items"], [])


class ExecutorTest(unittest.TestCase):
    """The attempt harness, up to the point where a model would be invoked."""

    maxDiff = None

    def test_both_arms_prepare_an_identical_run_shape(self):
        shapes = {}
        for arm in _mlr.ARMS:
            tmp = Path(tempfile.mkdtemp())
            try:
                built = _mlr.materialise(arm, tmp / "arm")
                run, db, contract = _mlr_run._prepare(
                    built, tmp, model="test/model",
                    task=_mlr.FIXTURE / "tasks" / "external.md")
                state = json.loads((run / "state.json").read_text(encoding="utf-8"))
                self.assertEqual(state["worker_runtime"]["model"], "test/model")
                self.assertFalse(Path(db).resolve().is_relative_to(
                    Path(built["workspace"]).resolve()),
                    "the session database must not live inside the project being measured")
                self.assertEqual(contract.read_bytes(),
                                 (_mlr.FIXTURE / "tasks" / "external.md").read_bytes())
                shapes[arm] = sorted(
                    p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file())
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(shapes[_mlr.FULL], shapes[_mlr.CONTRACT])

    def test_the_agents_python_is_the_one_that_compiled_the_runtime(self):
        """A fixture the agent cannot import measures nothing, and fails in a confusing way."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built = _mlr.materialise(_mlr.FULL, tmp / "arm")
            env = _mlr_run.pin_interpreter(tmp, _mlr.environment(built))
            found = shutil.which("python3", path=env["PATH"])
            self.assertIsNotNone(found)
            self.assertEqual(Path(found).resolve(), Path(sys.executable).resolve())
            probe = subprocess.run(["python3", "-c", "import objectstore; print(objectstore.put)"],
                                   cwd=built["workspace"], env=env, capture_output=True, text=True,
                                   check=False)
            self.assertEqual(probe.returncode, 0, probe.stderr[-400:])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_untouched_fixture_is_graded_incorrect(self):
        """If a workspace that did no work graded correct, every later number would be noise."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built = _mlr.materialise(_mlr.CONTRACT, tmp / "arm")
            outcome = _mlr_run.grade(built, tmp)
            self.assertFalse(outcome["correct"])
            self.assertFalse(outcome["gate_passed"])
            self.assertTrue(outcome["regression_passed"])
            self.assertTrue(outcome["contract_unchanged"])
            self.assertTrue(outcome["runtime_unchanged"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_reference_solution_is_graded_correct_in_both_arms(self):
        for arm in _mlr.ARMS:
            with self.subTest(arm=arm):
                tmp = Path(tempfile.mkdtemp())
                try:
                    built = _mlr.materialise(arm, tmp / "arm")
                    source = _mlr.FIXTURE / "reference" / "external"
                    for src in sorted(source.rglob("*")):
                        if src.is_file():
                            dst = Path(built["workspace"]) / src.relative_to(source)
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            dst.write_bytes(src.read_bytes())
                    outcome = _mlr_run.grade(built, tmp)
                    self.assertTrue(outcome["correct"], outcome["gate_output"][-600:])
                    self.assertTrue(outcome["contract_unchanged"])
                    self.assertTrue(outcome["vendored_unchanged"])
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


class SeriesTest(unittest.TestCase):
    """Slots, resume and the pre-registered classification, exercised without a model."""

    maxDiff = None

    def setUp(self):
        sys.path.insert(0, str(ROOT / "evals"))
        import pb_mlr
        self.pb = pb_mlr

    def measurement(self, repeat, *, correct=True, source=0, runtime=0,
                    validity=_mlr_run.VALID):
        return {"item": _mlr.FULL, "repeat": repeat, "validity": validity,
                "outcome": {"correct": correct},
                "profile": {"complete": True},
                "context": {"implementation_source_unique_bytes": source,
                            "implementation_runtime_unique_bytes": runtime,
                            "model_calls": 3, "tokens": {"input": 100}},
                "elapsed_seconds": 1.0}

    def record(self, measurements, arms=None):
        return {"experiment": self.pb.PILOT, "arms": arms or [_mlr.FULL],
                "measurements": measurements}

    def test_slots_are_preallocated_and_rotate_the_arm_order(self):
        pairs = self.pb.slots([_mlr.FULL, _mlr.CONTRACT], 4)
        self.assertEqual(len(pairs), 8)
        leaders = [pairs[i]["item"] for i in range(0, 8, 2)]
        self.assertEqual(set(leaders), set(_mlr.ARMS), "one arm led every sample")
        self.assertEqual(len(self.pb.slots([_mlr.FULL], 6)), 6)

    def test_a_series_refuses_to_resume_across_a_changed_configuration(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            out = tmp / "series.json"
            config = self.pb.configuration(model="m", samples=6, arms=[_mlr.FULL])
            import _repeat
            _repeat.write_series(out, config, [self.measurement(1)])
            self.assertEqual(len(_repeat.load_series(out, config)), 1)
            other = self.pb.configuration(model="m", samples=8, arms=[_mlr.FULL])
            with self.assertRaises(_repeat.RepeatConfigError):
                _repeat.load_series(out, other)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_pilot_and_the_paired_series_are_different_experiments(self):
        pilot = self.pb.configuration(model="m", samples=6, arms=[_mlr.FULL])
        paired = self.pb.configuration(model="m", samples=6, arms=list(_mlr.ARMS))
        self.assertNotEqual(pilot["experiment"], paired["experiment"])
        self.assertEqual(pilot["evidence_class"], "development")
        import _repeat
        self.assertNotEqual(_repeat.frozen_identity(pilot), _repeat.frozen_identity(paired))

    def test_too_few_correct_runs_is_invalid_and_never_a_headroom_reading(self):
        rows = [self.measurement(1, correct=True, source=4000),
                self.measurement(2, correct=False, source=4000),
                self.measurement(3, correct=False, source=4000)]
        self.assertEqual(self.pb.analyse(self.record(rows))["headroom"], self.pb.INVALID)

    def test_missing_telemetry_on_a_completed_attempt_is_invalid(self):
        rows = [self.measurement(i) for i in (1, 2, 3, 4)]
        rows[0].pop("context")
        self.assertEqual(self.pb.analyse(self.record(rows))["headroom"], self.pb.INVALID)

    def test_correct_runs_that_never_read_the_module_report_no_headroom(self):
        rows = [self.measurement(i, source=0) for i in range(1, 7)]
        result = self.pb.analyse(self.record(rows))
        self.assertEqual(result["headroom"], self.pb.NO_HEADROOM)
        self.assertEqual(result["arms"][_mlr.FULL]["correct_runs_reading_source"], 0)

    def test_a_single_trivial_match_is_not_headroom(self):
        rows = [self.measurement(1, source=40)] + [self.measurement(i) for i in range(2, 7)]
        self.assertEqual(self.pb.analyse(self.record(rows))["headroom"], self.pb.NO_HEADROOM)

    def test_small_but_repeated_reads_are_limited_headroom(self):
        rows = [self.measurement(i, source=400) for i in range(1, 5)] + \
               [self.measurement(i, source=0) for i in (5, 6)]
        self.assertEqual(self.pb.analyse(self.record(rows))["headroom"],
                         self.pb.LIMITED_HEADROOM)

    def test_substantial_reads_by_most_correct_runs_are_material_headroom(self):
        rows = [self.measurement(i, source=2200) for i in range(1, 5)] + \
               [self.measurement(i, source=0) for i in (5, 6)]
        self.assertEqual(self.pb.analyse(self.record(rows))["headroom"],
                         self.pb.MATERIAL_HEADROOM)

    def test_consumption_on_failed_runs_is_reported_but_does_not_make_headroom(self):
        rows = [self.measurement(i, correct=True, source=0) for i in range(1, 5)] + \
               [self.measurement(i, correct=False, source=4405) for i in (5, 6)]
        result = self.pb.analyse(self.record(rows))
        self.assertEqual(result["headroom"], self.pb.NO_HEADROOM)
        self.assertEqual(result["arms"][_mlr.FULL]["failed_source_bytes"], [4405, 4405])

    def test_an_invalid_attempt_does_not_close_its_slot(self):
        """A provider outage must not become "this run consumed no implementation"."""
        tmp = Path(tempfile.mkdtemp())
        try:
            out = tmp / "series.json"
            calls = []

            def fake(arm, *, model, keep=None, **kw):
                calls.append(arm)
                if len(calls) == 1:
                    return {"validity": _mlr_run.SETUP_FAILURE, "reason": "provider unavailable"}
                return {"validity": _mlr_run.VALID, "outcome": {"correct": True},
                        "profile": {"complete": True},
                        "context": {"implementation_source_unique_bytes": 0,
                                    "implementation_runtime_unique_bytes": 0,
                                    "model_calls": 1, "tokens": {"input": 1}}}

            original = _mlr_run.run_attempt
            _mlr_run.run_attempt = fake
            try:
                record = self.pb.run_series(out, model="m", samples=2, arms=[_mlr.FULL],
                                            keep=None, preflight=_clean_environment)
            finally:
                _mlr_run.run_attempt = original
            rows = record["measurements"]
            self.assertEqual(len(rows), 3, "the failed attempt was kept and the slot re-run")
            self.assertEqual(sum(1 for r in rows if r["validity"] == _mlr_run.VALID), 2)
            analysis = self.pb.analyse({"arms": [_mlr.FULL], "measurements": rows})
            self.assertEqual(analysis["arms"][_mlr.FULL]["valid"], 2)
            self.assertEqual(len(analysis["arms"][_mlr.FULL]["invalid"]), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_thresholds_come_from_the_preregistration_and_not_the_data(self):
        text = (ROOT / "evals" / "craft" / "modularity-local-reasoning"
                / "MLR-C3-pilot-preregistration.md").read_text(encoding="utf-8")
        self.assertIn(str(self.pb.INCIDENTAL_BYTES), text)
        self.assertIn(f"{self.pb.SUBSTANTIAL_BYTES:,}", text)
        self.assertIn(str(self.pb.MIN_CORRECT), text)


class RepairedDefectsTest(unittest.TestCase):
    """The two MLR-C3 defects, now repaired, kept so the repair cannot silently regress.

    Both were pinned as tests when they were found; they are inverted rather than deleted, because
    that each was once true is the reason the current behaviour is asserted at all. The detailed
    replacements live in `test_mlr_instrument_v2.py`, against real realizations and real interpreter
    output rather than strings.
    """

    maxDiff = None

    def realise(self, tmp, name):
        built = _mlr.materialise(_mlr.CONTRACT, tmp / "arm")
        source = _mlr.FIXTURE / "realizations" / "valid" / name
        for src in sorted(source.rglob("*")):
            if src.is_file():
                dst = Path(built["workspace"]) / src.relative_to(source)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        return built

    def test_the_oracle_no_longer_rejects_a_product_correct_restructuring(self):
        """MLR-C3 §9: v1 failed the `(body, created)` shape the pilot actually produced."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built = self.realise(tmp, "tuple")
            self.assertTrue(_mlr_run.grade(built, tmp, oracle=_mlr_run.ORACLE_V2)["correct"])
            self.assertFalse(_mlr_run.grade(built, tmp, oracle=_mlr_run.ORACLE_V1)["correct"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_documentation_routes_are_now_attributed(self):
        """MLR-C3 §10: `help` was scored `other` and `pydoc` as running the system."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built = _mlr.materialise(_mlr.CONTRACT, tmp / "arm")
            for command in ('python3 -c "import objectstore; help(objectstore)"',
                            "python3 -m pydoc objectstore",
                            'python3 -c "import objectstore; help(objectstore._store)"'):
                with self.subTest(command=command):
                    self.assertEqual(_mlr_context.command_route(command, built),
                                     _mlr_context.DOCUMENTATION)
            self.assertEqual(
                _mlr_context._command_provenance(
                    _mlr_context.DOCUMENTATION, "PACKAGE CONTENTS _store _backend", built),
                _mlr_context.IMPLEMENTATION_RUNTIME)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_disassembly_and_source_paths_are_still_attributed(self):
        """The repair added a route family; it must not cost the ones that already worked."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built = _mlr.materialise(_mlr.CONTRACT, tmp / "arm")
            for command in ('python -c "import dis, objectstore; dis.dis(objectstore.put)"',
                            'python -c "from objectstore import _store; print(vars(_store))"'):
                with self.subTest(command=command):
                    self.assertEqual(_mlr_context.command_route(command, built),
                                     _mlr_context.INTROSPECTION)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
