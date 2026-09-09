"""The MLR-C3R instrument: a correctness oracle that judges behaviour, and attribution that
cannot be evaded by asking Python for its own documentation.

MLR-C3 ran a pilot and found that the two things every later number depends on were both wrong. The
oracle rejected a product-correct restructuring because it asserted an internal function's
signature. The attribution scored `help(objectstore)` — 5,397 bytes of the package's interior — as
`other`, and `pydoc` as *running the system*. Either defect alone would have let the paired
experiment report a substitution that did not happen.

These tests are the repair's evidence. The oracle is held against four product-correct realizations
that decompose the service differently and five that are behaviourally wrong; the attribution is
held against the whole ordinary Python introspection surface, executed for real against the fixture
rather than asserted from a list of command strings.

Nothing here invokes a model.
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

import _mlr             # noqa: E402
import _mlr_context     # noqa: E402
import _mlr_run         # noqa: E402
import _profile         # noqa: E402

FIXTURE = _mlr.FIXTURE
HIDDEN = FIXTURE / "hidden"
REALIZATIONS = FIXTURE / "realizations"


def overlay(built: dict, source: Path) -> None:
    for src in sorted(Path(source).rglob("*")):
        if src.is_file():
            dst = Path(built["workspace"]) / src.relative_to(source)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())


class Arm:
    """One materialised arm, with an optional realization laid over it."""

    def __init__(self, arm=_mlr.CONTRACT, realization: Path | None = None):
        self.arm, self.realization = arm, realization

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.built = _mlr.materialise(self.arm, self.tmp / "arm")
        if self.realization is not None:
            overlay(self.built, self.realization)
        return self

    def probe(self, code: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", "-c", code], cwd=self.built["workspace"],
                              env=_mlr.environment(self.built), capture_output=True, text=True,
                              check=False)

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


class OracleV2Test(unittest.TestCase):
    """It must accept every product-correct realization and reject every behaviourally wrong one."""

    maxDiff = None

    VALID = ("reference", "handler", "optional", "tuple")
    INVALID = ("always-created", "missing-as-empty", "no-entitlement", "unstable",
               "stores-on-unknown-report")

    @staticmethod
    def source(name: str) -> Path:
        if name == "reference":
            return FIXTURE / "reference" / "external"
        for kind in ("valid", "invalid"):
            candidate = REALIZATIONS / kind / name
            if candidate.is_dir():
                return candidate
        raise AssertionError(f"no realization named {name}")

    def judge(self, name: str, oracle: str) -> dict:
        with Arm(realization=self.source(name)) as arm:
            return _mlr_run.grade(arm.built, arm.tmp, oracle=oracle)

    def test_it_accepts_every_product_correct_realization(self):
        """Four different decompositions of the same behaviour. All are correct work."""
        for name in self.VALID:
            with self.subTest(realization=name):
                outcome = self.judge(name, _mlr_run.ORACLE_V2)
                self.assertTrue(outcome["correct"], outcome["gate_output"][-700:])

    def test_it_rejects_every_behaviourally_wrong_realization(self):
        for name in self.INVALID:
            with self.subTest(realization=name):
                self.assertFalse(self.judge(name, _mlr_run.ORACLE_V2)["correct"])

    def test_it_rejects_a_workspace_where_the_task_was_not_done(self):
        with Arm() as arm:
            self.assertFalse(_mlr_run.grade(arm.built, arm.tmp, oracle=_mlr_run.ORACLE_V2)["correct"])

    def test_the_old_oracle_rejected_correct_work_and_that_is_why_v2_exists(self):
        """The defect, pinned. v1 fails two realizations that v2 and the product both accept."""
        rejected = [n for n in self.VALID if not self.judge(n, _mlr_run.ORACLE_V1)["correct"]]
        self.assertIn("tuple", rejected, "the shape the MLR-C3 pilot actually produced")
        self.assertTrue(rejected)

    def test_the_gate_never_reaches_into_the_service_or_the_module(self):
        gate = (HIDDEN / _mlr_run.ORACLE_V2).read_text(encoding="utf-8")
        body = gate.split('"""', 2)[-1]
        for token in ("import objectstore", "objectstore.", "exports.", "_key", "_backend",
                      "third_party", "sha256"):
            with self.subTest(token=token):
                self.assertNotIn(token, body)

    def test_the_oracle_version_travels_with_the_verdict(self):
        with Arm() as arm:
            outcome = _mlr_run.grade(arm.built, arm.tmp, oracle=_mlr_run.ORACLE_V2)
            self.assertEqual(outcome["oracle"], _mlr_run.ORACLE_V2)
            self.assertIsInstance(outcome["verification_seconds"], float)


class InternalNamesTest(unittest.TestCase):
    """The fingerprint of implementation-derived text, derived rather than listed."""

    maxDiff = None

    def test_the_names_come_from_the_module_source(self):
        names = _mlr_context.internal_names()
        for expected in ("_store", "_backend", "_errors", "_ATTEMPTS", "_FANOUT", "_checksum",
                         "_path_for", "_with_retries", "_ChecksumMismatch"):
            with self.subTest(name=expected):
                self.assertIn(expected, names)

    def test_a_new_internal_name_is_covered_without_editing_a_list(self):
        """A hand-written list stops covering the module the day the module changes."""
        tmp = Path(tempfile.mkdtemp())
        try:
            source = tmp / "objectstore"
            shutil.copytree(FIXTURE / "runtime" / "objectstore", source)
            (source / "_store.py").write_text(
                (source / "_store.py").read_text(encoding="utf-8") + "\n_NEW_SECRET = 7\n",
                encoding="utf-8")
            self.assertIn("_NEW_SECRET", _mlr_context.internal_names(source))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_public_names_are_not_treated_as_internal(self):
        names = _mlr_context.internal_names()
        for public in ("put", "get", "delete", "exists", "NotFound", "StorageUnavailable"):
            with self.subTest(name=public):
                self.assertNotIn(public, names)

    def test_matching_is_word_bounded(self):
        """`_store` must not match inside `export_stored`, nor `objectstore`."""
        self.assertEqual(_mlr_context._internal_hits("export_stored objectstore"), [])
        self.assertIn("_store", _mlr_context._internal_hits("objectstore._store"))


class PythonSurfaceAttributionTest(unittest.TestCase):
    """Every ordinary route, executed for real, and classified by what it actually returned."""

    maxDiff = None

    # (label, code producing OUT, expected provenance)
    DISCLOSING = (
        ("help(package)", "import io,contextlib,objectstore\nb=io.StringIO()\n"
                          "with contextlib.redirect_stdout(b): help(objectstore)\nOUT=b.getvalue()"),
        ("help(private module)", "import io,contextlib\nfrom objectstore import _store\n"
                                 "b=io.StringIO()\n"
                                 "with contextlib.redirect_stdout(b): help(_store)\nOUT=b.getvalue()"),
        ("pydoc.render_doc", "import pydoc,objectstore\nOUT=pydoc.render_doc(objectstore)"),
        ("vars(_store)", "from objectstore import _store\n"
                         "OUT=repr({k:v for k,v in vars(_store).items() if not k.startswith('__')})"),
        ("dir(package)", "import objectstore\nOUT=repr(dir(objectstore))"),
        ("__dict__", "import objectstore\nOUT=repr(list(objectstore.__dict__))"),
        ("inspect.getmembers", "import inspect,objectstore\n"
                               "OUT=repr([n for n,_ in inspect.getmembers(objectstore)])"),
        ("co_names", "import objectstore\nOUT=repr(objectstore.put.__code__.co_names)"),
        ("disassembly", "import io,dis\nfrom objectstore import _store\nb=io.StringIO()\n"
                        "for n in dir(_store):\n    o=getattr(_store,n)\n"
                        "    if hasattr(o,'__code__'): dis.dis(o,file=b)\nOUT=b.getvalue()"),
        ("module enumeration", "import pkgutil,objectstore\n"
                               "OUT=repr([m.name for m in pkgutil.iter_modules(objectstore.__path__)])"),
    )

    PUBLIC = (
        ("__all__", "import objectstore\nOUT=repr(objectstore.__all__)"),
        ("signatures", "import inspect,objectstore\n"
                       "OUT='\\n'.join(n+str(inspect.signature(getattr(objectstore,n)))"
                       " for n in ('put','get','delete','exists'))"),
        ("docstrings", "import inspect,objectstore\n"
                       "OUT='\\n'.join(inspect.getdoc(getattr(objectstore,n)) or ''"
                       " for n in objectstore.__all__)"),
    )

    REFUSED = (
        ("inspect.getsource", "import inspect,objectstore\n"
                              "try: OUT=inspect.getsource(objectstore)\n"
                              "except Exception as e: OUT='REFUSED '+type(e).__name__"),
        ("loader.get_source", "import importlib.util\n"
                              "l=importlib.util.find_spec('objectstore._store').loader\n"
                              "OUT=repr(l.get_source('objectstore._store'))"),
        ("importlib.metadata", "import importlib.metadata as md\n"
                               "try: OUT=md.version('objectstore')\n"
                               "except Exception as e: OUT='REFUSED '+type(e).__name__"),
    )

    @staticmethod
    def run_route(arm, code):
        result = arm.probe(code + "\nimport sys\nsys.stdout.write("
                                  "OUT if isinstance(OUT,str) else repr(OUT))")
        return result.stdout if result.returncode == 0 else ""

    def test_every_disclosing_route_is_implementation_derived(self):
        """The MLR-C3 defect: `help` and `pydoc` returned the interior and were not counted."""
        with Arm() as arm:
            for label, code in self.DISCLOSING:
                with self.subTest(route=label):
                    output = self.run_route(arm, code)
                    self.assertTrue(output, f"{label} produced nothing to classify")
                    self.assertTrue(_mlr_context._internal_hits(output),
                                    f"{label} did not disclose an internal name")
                    route = _mlr_context.command_route(f"python3 -c 'objectstore {code}'", arm.built)
                    self.assertEqual(
                        _mlr_context._command_provenance(route, output, arm.built),
                        _mlr_context.IMPLEMENTATION_RUNTIME, label)

    def test_the_public_surface_is_not_charged_as_implementation(self):
        """Signatures and docstrings are the module's public semantics in both arms."""
        with Arm() as arm:
            for label, code in self.PUBLIC:
                with self.subTest(route=label):
                    output = self.run_route(arm, code)
                    self.assertTrue(output)
                    self.assertEqual(_mlr_context._internal_hits(output), [], label)
                    route = _mlr_context.command_route(f"python3 -c 'objectstore {code}'", arm.built)
                    self.assertEqual(
                        _mlr_context._command_provenance(route, output, arm.built),
                        _mlr_context.PUBLIC_CONTRACT, label)

    def test_source_recovery_routes_are_still_refused(self):
        with Arm() as arm:
            for label, code in self.REFUSED:
                with self.subTest(route=label):
                    output = self.run_route(arm, code)
                    self.assertNotIn("def put", output, label)
                    self.assertNotIn("_FANOUT =", output, label)

    def test_pydoc_is_not_scored_as_running_the_system(self):
        with Arm() as arm:
            self.assertEqual(
                _mlr_context.command_route("python3 -m pydoc objectstore", arm.built),
                _mlr_context.DOCUMENTATION)

    def test_a_run_that_prints_an_internal_traceback_stays_a_run_but_is_flagged(self):
        """Its bytes are test output; the disclosure is recorded rather than reclassified."""
        with Arm() as arm:
            output = 'FAILED\n  File "objectstore/_store.py", in _with_retries\nRan 5 tests'
            self.assertEqual(
                _mlr_context._command_provenance(_mlr_context.RUN, output, arm.built),
                _mlr_context.BEHAVIOUR)
            self.assertIn("_with_retries", _mlr_context._internal_hits(output))


SCHEMA = """
CREATE TABLE message (id text PRIMARY KEY, session_id text NOT NULL,
                      time_created integer NOT NULL, time_updated integer NOT NULL,
                      data text NOT NULL);
CREATE TABLE part (id text PRIMARY KEY, message_id text NOT NULL, session_id text NOT NULL,
                   time_created integer NOT NULL, time_updated integer NOT NULL,
                   data text NOT NULL);
"""


class Session:
    """A synthetic OpenCode session in the real schema."""

    def __init__(self, path: Path):
        self.conn = sqlite3.connect(Path(path))
        self.conn.executescript(SCHEMA)
        self.n = self.messages = 0
        self.clock = 1000

    def message(self, role="assistant", **data):
        self.messages += 1
        mid = f"m{self.messages:04d}"
        self.clock += 100
        self.conn.execute("INSERT INTO message VALUES (?,?,?,?,?)",
                          (mid, "s", self.clock, self.clock, json.dumps({"role": role, **data})))
        return mid

    def part(self, mid, data):
        self.n += 1
        self.clock += 10
        self.conn.execute("INSERT INTO part VALUES (?,?,?,?,?,?)",
                          (f"p{self.n:04d}", mid, "s", self.clock, self.clock, json.dumps(data)))

    def call(self, mid, *, input_tokens=0, output_tokens=0, cost=0.0):
        self.part(mid, {"type": "step-start"})
        self.part(mid, {"type": "step-finish",
                        "tokens": {"input": input_tokens, "output": output_tokens, "reasoning": 0,
                                   "cache": {"read": 0, "write": 0}}, "cost": cost})

    def tool(self, mid, tool, arguments, output, *, status="completed", ms=25):
        start = self.clock
        self.part(mid, {"type": "tool", "tool": tool, "callID": f"c{self.n}",
                        "state": {"status": status, "input": arguments, "output": output,
                                  "metadata": {}, "time": {"start": start, "end": start + ms}}})

    def close(self):
        self.conn.commit()
        self.conn.close()


class ExecutionProfileTest(unittest.TestCase):
    """The reusable half: what an execution cost, with nothing about object storage in it."""

    maxDiff = None

    _seq = 0

    def build(self, tmp):
        ExecutionProfileTest._seq += 1
        db = Path(tmp) / f"w{ExecutionProfileTest._seq}.db"
        s = Session(db)
        m = s.message()
        s.call(m, input_tokens=1000, output_tokens=100, cost=0.5)
        s.tool(m, "read", {"filePath": "app/api.py"}, "x" * 40, ms=30)
        s.tool(m, "bash", {"command": "false"}, "boom", status="error", ms=70)
        s.call(m, input_tokens=1500, output_tokens=200, cost=0.25)
        s.close()
        return db

    def test_it_reports_usage_tools_and_time_without_experiment_semantics(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            got = _profile.profile(self.build(tmp), stage="implementer", model="m/x",
                                   elapsed_seconds=12.5, verification_seconds=2.0)
            self.assertTrue(got["complete"])
            self.assertEqual(got["usage"]["calls_started"], 2)
            self.assertEqual(got["usage"]["input"], 2500)
            self.assertEqual(got["usage"]["output"], 300)
            self.assertAlmostEqual(got["usage"]["cost"], 0.75)
            self.assertEqual(got["tools"]["calls"], 2)
            self.assertEqual(got["tools"]["failed_calls"], 1)
            self.assertEqual(got["tools"]["by_tool"], {"bash": 1, "read": 1})
            self.assertAlmostEqual(got["tools"]["seconds"], 0.1)
            self.assertEqual(got["time"]["harness_seconds"], 12.5)
            self.assertEqual(got["time"]["verification_seconds"], 2.0)
            self.assertIsNotNone(got["time"]["model_seconds_derived"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_it_knows_nothing_about_this_experiment(self):
        """If the profile mentioned the fixture it would not describe any other pipeline."""
        text = (ROOT / "evals" / "_profile.py").read_text(encoding="utf-8").lower()
        for token in ("objectstore", "implementation-source", "contract arm", "full arm",
                      "vendored", "modularity"):
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_an_absent_session_is_incomplete_and_never_zero(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            got = _profile.profile(Path(tmp) / "absent.db", stage="implementer", model="m/x")
            self.assertFalse(got["complete"])
            self.assertIn("session-transcript", got["missing"])
            run = _profile.pipeline([got], outcome={"correct": True})
            self.assertFalse(run["complete"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_pipeline_carries_stages_and_totals_together(self):
        """The pipeline is the unit of value; the stages are why it behaved as it did."""
        tmp = Path(tempfile.mkdtemp())
        try:
            one = _profile.profile(self.build(tmp), stage="implementer", model="m/x")
            two = _profile.profile(self.build(tmp), stage="reviewer", model="m/x")
            run = _profile.pipeline([one, two], outcome={"correct": True})
            self.assertEqual([s["stage"] for s in run["stages"]], ["implementer", "reviewer"])
            self.assertEqual(run["usage"]["input"], 5000)
            self.assertEqual(run["tool_calls"], 4)
            self.assertEqual(run["failed_tool_calls"], 2)
            self.assertTrue(run["complete"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_there_is_no_scalar_efficiency_anywhere(self):
        """Nothing in Proofbound may exchange quality for cost, so nothing here computes a rate."""
        import re
        text = (ROOT / "evals" / "_profile.py").read_text(encoding="utf-8")
        code = "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith(("#", "*", '"""')))
        for pattern in (r"\bdef\s+\w*score", r"\b\w*score\w*\s*=", r"\brank\w*\s*=",
                        r"correct\w*\s*/", r"/\s*(?:tokens|seconds|cost)\b"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, code, re.I),
                                  f"a scalar quality/cost rate appears: {pattern}")


class LedgerV2Test(unittest.TestCase):
    """Routes, disclosure and the accounting that must not double-count them."""

    maxDiff = None

    def ledger(self, tmp, built, build):
        db = Path(tmp) / "w.db"
        s = Session(db)
        build(s)
        s.close()
        return _mlr_context.consumed(db, built)

    def test_documentation_output_is_counted_as_implementation_runtime(self):
        with Arm() as arm:
            body = "Help on package objectstore:\nPACKAGE CONTENTS\n    _backend\n    _store\n" * 20
            led = self.ledger(arm.tmp, arm.built, lambda s: (
                s.call(m := s.message()),
                s.tool(m, "bash", {"command": 'python3 -c "import objectstore; help(objectstore)"'},
                       body),
                s.call(m)))
            self.assertGreater(led["implementation_runtime_unique_bytes"], 0)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)
            self.assertEqual(led["by_route"][_mlr_context.DOCUMENTATION]["items"], 1)

    def test_a_public_signature_query_is_not_charged_as_implementation(self):
        with Arm() as arm:
            led = self.ledger(arm.tmp, arm.built, lambda s: (
                s.call(m := s.message()),
                s.tool(m, "bash",
                       {"command": 'python3 -c "import inspect,objectstore;'
                                   ' print(inspect.signature(objectstore.put))"'},
                       "put(key: str, payload: bytes) -> None"),
                s.call(m)))
            self.assertEqual(led["implementation_derived"]["unique_bytes"], 0)
            self.assertGreater(led["by_provenance"][_mlr_context.PUBLIC_CONTRACT]["unique_bytes"], 0)

    def test_disclosure_is_reported_beside_provenance_and_never_added_to_it(self):
        with Arm() as arm:
            output = "Ran 5 tests\n" * 30 + '  File "objectstore/_store.py", in _with_retries\n'
            led = self.ledger(arm.tmp, arm.built, lambda s: (
                s.call(m := s.message()),
                s.tool(m, "bash", {"command": "python3 -m unittest discover -s tests"}, output),
                s.call(m)))
            self.assertGreater(led["by_provenance"][_mlr_context.BEHAVIOUR]["unique_bytes"], 0)
            self.assertEqual(led["implementation_derived"]["unique_bytes"], 0)
            self.assertGreater(led["disclosure"]["unique_bytes"], 0)
            self.assertIn("_with_retries", led["disclosure"]["names"])

    def test_a_source_read_still_dominates_and_stays_source(self):
        with Arm(arm=_mlr.FULL) as arm:
            path = Path(arm.built["workspace"]) / _mlr.VENDORED / "objectstore" / "_store.py"
            body = path.read_text(encoding="utf-8")
            led = self.ledger(arm.tmp, arm.built, lambda s: (
                s.call(m := s.message()),
                s.tool(m, "read", {"filePath": str(path)}, body),
                s.call(m)))
            self.assertEqual(led["implementation_source_unique_bytes"],
                             len(body.encode("utf-8")))
            self.assertEqual(led["implementation_runtime_unique_bytes"], 0)

    def test_unique_and_delivered_stay_separate(self):
        with Arm(arm=_mlr.FULL) as arm:
            path = Path(arm.built["workspace"]) / _mlr.VENDORED / "objectstore" / "_errors.py"
            led = self.ledger(arm.tmp, arm.built, lambda s: (
                s.call(m := s.message()),
                s.tool(m, "read", {"filePath": str(path)}, "q" * 300),
                s.call(m), s.call(m), s.call(m)))
            source = led["by_provenance"][_mlr_context.IMPLEMENTATION_SOURCE]
            self.assertEqual(source["unique_bytes"], 300)
            self.assertEqual(source["delivered_bytes"], 900)


if __name__ == "__main__":
    unittest.main()
