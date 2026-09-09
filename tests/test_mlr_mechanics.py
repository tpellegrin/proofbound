"""Measurement-mechanics probes for the modularity calibration.

MLR-C1 built two workspaces that differed in whether a module's source was present. This checks the
thing that actually matters: whether the *information* differs. It does not, unless the runtime
itself withholds the implementation — the first probe here is the one that failed before the runtime
was compiled, and it is kept because it is the difference between an information boundary and mere
friction.

The boundary is an experimental information policy, not a security boundary: it stops ordinary
development tooling from returning the implementation, and makes no claim against disassembly.

Nothing here invokes a model.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _experiment  # noqa: E402
import _mlr  # noqa: E402
import _repeat  # noqa: E402


def probe(built: dict, code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", "-c", code], cwd=built["workspace"],
                          env=_mlr.environment(built), capture_output=True, text=True, check=False)


class Built:
    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.arms = {arm: _mlr.materialise(arm, self.tmp / arm) for arm in _mlr.ARMS}
        return self.arms

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


class InformationBoundaryTest(unittest.TestCase):
    """The treatment is what an agent can learn, not where a file sits."""

    maxDiff = None

    def test_the_implementation_cannot_be_recovered_in_the_contract_arm(self):
        """The probe that failed on the C1 fixture, and the reason the runtime is compiled."""
        with Built() as arms:
            built = arms[_mlr.CONTRACT]
            for label, code in (
                ("getsource(package)",
                 "import inspect, objectstore; print(len(inspect.getsource(objectstore)))"),
                ("getsource(module)",
                 "import inspect; from objectstore import _store;"
                 " print(len(inspect.getsource(_store)))"),
            ):
                with self.subTest(route=label):
                    self.assertNotEqual(probe(built, code).returncode, 0,
                                        "ordinary tooling returned the implementation")

    def test_no_implementation_text_is_reachable_in_the_contract_arm(self):
        with Built() as arms:
            built = arms[_mlr.CONTRACT]
            result = probe(built, "import objectstore, pathlib;"
                                  " raw = pathlib.Path(objectstore.__file__).read_bytes();"
                                  " print(b'_FANOUT' in raw, b'def put' in raw)")
            self.assertEqual(result.stdout.split(), ["False", "False"])
            listing = probe(built, "import glob, os, objectstore;"
                                   " print(glob.glob(os.path.dirname(objectstore.__file__)+'/*.py'))")
            self.assertEqual(listing.stdout.strip(), "[]")

    def test_the_implementation_is_readable_in_the_full_arm(self):
        with Built() as arms:
            path = (Path(arms[_mlr.FULL]["workspace"]) / _mlr.VENDORED
                    / "objectstore" / "_store.py")
            self.assertIn("_FANOUT", path.read_text(encoding="utf-8"))

    def test_public_semantics_survive_the_boundary_and_are_equal_in_both_arms(self):
        """Docstrings and signatures are external semantics; withholding them would change the task."""
        code = ("import objectstore, inspect;"
                " print(sorted(objectstore.__all__));"
                " print('NotFound' in (objectstore.get.__doc__ or ''));"
                " print(str(inspect.signature(objectstore.put)))")
        with Built() as arms:
            outputs = {arm: probe(built, code).stdout for arm, built in arms.items()}
            self.assertEqual(outputs[_mlr.FULL], outputs[_mlr.CONTRACT])
            self.assertIn("True", outputs[_mlr.FULL])

    def test_location_is_disclosed_but_contents_are_not(self):
        """Knowing where something lives is not the same as being able to read it."""
        with Built() as arms:
            built = arms[_mlr.CONTRACT]
            where = probe(built, "import inspect, objectstore, os;"
                                 " f = inspect.getsourcefile(objectstore);"
                                 " print(bool(f), os.path.exists(f) if f else False)")
            self.assertEqual(where.stdout.split(), ["True", "False"])


class RuntimeIdentityTest(unittest.TestCase):
    """Different visibility, same executed module."""

    maxDiff = None

    def test_both_arms_execute_byte_identical_runtimes(self):
        with Built() as arms:
            self.assertEqual(arms[_mlr.FULL]["runtime_digest"],
                             arms[_mlr.CONTRACT]["runtime_digest"])

    def test_the_runtime_is_reproducible_across_materialisations(self):
        """Otherwise two slots of the same arm would not be the same experiment."""
        with Built() as arms:
            with tempfile.TemporaryDirectory() as td:
                again = _mlr.materialise(_mlr.CONTRACT, Path(td))
                self.assertEqual(again["runtime_digest"], arms[_mlr.CONTRACT]["runtime_digest"])

    def test_the_compiled_runtime_records_the_source_it_came_from(self):
        with Built() as arms:
            self.assertEqual(arms[_mlr.FULL]["source_digest"],
                             _mlr.digest_tree(_mlr.FIXTURE / "runtime" / "objectstore"))
            self.assertEqual(arms[_mlr.FULL]["source_digest"],
                             arms[_mlr.CONTRACT]["source_digest"])

    def test_the_readable_copy_is_not_what_executes(self):
        """The shadow-copy guard: work on a file the system does not load changes nothing."""
        with Built() as arms:
            built = arms[_mlr.FULL]
            guard = _mlr.executed_module_is_not_the_readable_copy(built)
            self.assertTrue(guard["from_runtime"])
            self.assertTrue(guard["readable_copy_is_editable"])
            self.assertFalse(guard["editing_the_copy_changes_execution"])

            vendored = Path(built["workspace"]) / _mlr.VENDORED / "objectstore" / "_store.py"
            vendored.write_text(vendored.read_text().replace("_ATTEMPTS = 3", "_ATTEMPTS = 9"))
            after = probe(built, "from objectstore import _store; print(_store._ATTEMPTS)")
            self.assertEqual(after.stdout.strip(), "3")


class ContextAttributionTest(unittest.TestCase):
    """Availability is not consumption, and a path is the provenance we actually have."""

    maxDiff = None

    def test_every_touched_path_is_attributed(self):
        with Built() as arms:
            built = arms[_mlr.FULL]
            workspace = Path(built["workspace"])
            cases = {
                "app/exports.py": _mlr.WORKSPACE,
                "docs/storage-contract.md": _mlr.WORKSPACE,
                str(workspace / _mlr.VENDORED / "objectstore" / "_store.py"):
                    _mlr.VENDORED_IMPLEMENTATION,
                str(Path(built["runtime"]) / "objectstore" / "_store.pyc"): _mlr.RUNTIME,
                "/etc/hosts": _mlr.OUTSIDE,
            }
            for path, expected in cases.items():
                with self.subTest(path=path[-40:]):
                    self.assertEqual(_mlr.classify_path(path, built), expected)

    def test_an_absolute_read_is_not_discarded(self):
        """`ce1_facts` drops absolute paths; here the implementation lives at one on purpose."""
        with Built() as arms:
            built = arms[_mlr.FULL]
            absolute = Path(built["workspace"]) / _mlr.VENDORED / "objectstore" / "_store.py"
            self.assertEqual(_mlr.classify_path(absolute, built), _mlr.VENDORED_IMPLEMENTATION)
            self.assertGreater(_mlr.implementation_bytes(built, [str(absolute)]), 0)

    def test_unread_implementation_counts_as_nothing(self):
        """Charging `full` for code it never opened would rig the comparison."""
        with Built() as arms:
            self.assertEqual(_mlr.implementation_bytes(arms[_mlr.FULL], ["app/api.py"]), 0)

    def test_the_contract_arm_has_no_implementation_bytes_to_consume(self):
        with Built() as arms:
            built = arms[_mlr.CONTRACT]
            self.assertEqual(_mlr.implementation_bytes(built, ["app/api.py", "/etc/hosts"]), 0)

    def test_the_contract_document_is_symmetric_and_so_cancels(self):
        with Built() as arms:
            self.assertEqual(arms[_mlr.FULL]["contract_sha256"],
                             arms[_mlr.CONTRACT]["contract_sha256"])
            for arm, built in arms.items():
                with self.subTest(arm=arm):
                    self.assertEqual(
                        _mlr.classify_path("docs/storage-contract.md", built), _mlr.WORKSPACE)


class TaskExercisesTheBoundaryTest(unittest.TestCase):
    """Check C: the task must actually need a fact about the module, not just touch it."""

    maxDiff = None

    def test_a_solution_that_ignores_absence_semantics_fails_the_gate(self):
        """If any naive patch passed, the task would measure nothing about the boundary."""
        naive = '''"""The service's request handlers. Each returns (status, body)."""
from app import accounts, exports, reports


def create_export(user_id: str, report_id: str):
    try:
        body = exports.create(user_id, report_id)
    except accounts.UnknownAccount:
        return 404, b"no such account"
    except exports.ExportForbidden:
        return 403, b"upgrade required"
    except reports.UnknownReport:
        return 404, b"no such report"
    return 201, body


def download_export(user_id: str, report_id: str):
    # Assumes a missing object reads back as nothing, which the module does not do.
    try:
        body = exports.fetch(user_id, report_id)
    except accounts.UnknownAccount:
        return 404, b"no such account"
    if not body:
        return 201, exports.create(user_id, report_id)
    return 200, body
'''
        with Built() as arms:
            built = arms[_mlr.CONTRACT]
            (Path(built["workspace"]) / "app" / "api.py").write_text(naive, encoding="utf-8")
            result = _mlr.run_gate(built, _mlr.FIXTURE / "hidden" / "external_test.py",
                                   data_root=Path(built["workspace"]).parent / "naive")
            self.assertNotEqual(result.returncode, 0,
                                "the task can be satisfied without knowing how absence is reported")


class ExperimentShapeTest(unittest.TestCase):
    """The paired run C3 needs is expressible on the substrate that already exists."""

    maxDiff = None

    def manifest(self, **over):
        base = {
            "format": _experiment.FORMAT, "id": "mlr-shape",
            "claim": "Implementation access provides no correctness value outside the module.",
            "measurand": "Implementation bytes that entered reasoning on correct runs, per arm.",
            "baseline": "The full arm, with the module's source readable in the repository.",
            "treatment": "The contract arm, the same system without a readable implementation.",
            "primary_comparison": "Correctness parity first, then implementation bytes consumed.",
            "falsifier": "Correctness drops without the implementation, or full never reads it.",
            "adoption_rule": "Adopt the local claim only if correctness does not regress.",
            "frozen": ["fixture revision", "runtime digest", "contract sha", "read boundary"],
            "guardrails": ["correctness must not regress in the contract arm"],
            "invalid_if": ["the two arms execute different runtime digests"],
            "samples_per_cell": 3,
            "instances": ["external-task"],
            "pressures": [{"id": "correct", "statement": "The hidden gate for the task passes."}],
            "arms": [{"id": "baseline", "treatment": None}, {"id": "contract", "treatment": None}],
        }
        base.update(over)
        return base

    def load(self, tmp: Path, manifest: dict):
        import json
        path = tmp / "experiment.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return _experiment.load(path)

    def test_slots_pair_the_arms_on_one_task(self):
        with tempfile.TemporaryDirectory() as td:
            loaded = self.load(Path(td), self.manifest())
            slots = _experiment.slots(loaded)
            self.assertEqual(len(slots), 6)
            for sample in (1, 2, 3):
                arms = {s["arm"] for s in slots if s["sample"] == sample}
                self.assertEqual(arms, {"baseline", "contract"})

    def test_arm_order_is_pre_generated_and_neither_arm_leads_every_time(self):
        with tempfile.TemporaryDirectory() as td:
            loaded = self.load(Path(td), self.manifest())
            slots = _experiment.slots(loaded)
            leaders = {slots[i]["arm"] for i in range(0, len(slots), 2)}
            self.assertEqual(leaders, {"baseline", "contract"})

    def test_the_read_boundary_is_part_of_configuration_identity(self):
        """A run where the implementation is readable is not the same treatment as one where it
        is not, so the two must not be able to resume into each other."""
        with tempfile.TemporaryDirectory() as td:
            loaded = self.load(Path(td), self.manifest())
            compiled = _experiment.configuration(loaded, {"read_boundary": "bytecode-runtime"})
            source = _experiment.configuration(loaded, {"read_boundary": "source-runtime"})
            self.assertNotEqual(_repeat.frozen_identity(compiled),
                                _repeat.frozen_identity(source))

    def test_a_changed_runtime_refuses_to_resume(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            loaded = self.load(tmp, self.manifest())
            config = _experiment.configuration(loaded, {"runtime_digest": "aaa"})
            out = tmp / "series.json"
            _repeat.write_series(out, config, [{"item": "x", "repeat": 1}])
            self.assertEqual(len(_repeat.load_series(out, config)), 1)
            moved = _experiment.configuration(loaded, {"runtime_digest": "bbb"})
            with self.assertRaises(_repeat.RepeatConfigError):
                _repeat.load_series(out, moved)


if __name__ == "__main__":
    unittest.main()


class KnowledgeSurvivesTheSourceBoundaryTest(unittest.TestCase):
    """What `contract` can still learn about the interior, recorded as a fact of the design.

    MLR-C2 wrote that in `contract` the implementation quantity is "structurally zero, because no
    implementation text is reachable". The first half is true only of *text*. These probes pin how
    much implementation-derived knowledge survives, because the measurand and the interpretation
    categories are built on their answers: a boundary that hides source while leaving the hidden
    decisions two ordinary lines away is a source-visibility treatment, not a knowledge treatment,
    and must be described as one.

    They are regression tests as much as evidence. If a later change makes any of this unreachable,
    the treatment has silently become stronger than the one the experiment was pre-registered on.
    """

    maxDiff = None

    def test_the_hidden_decisions_are_recoverable_without_any_source(self):
        with Built() as arms:
            result = probe(arms[_mlr.CONTRACT],
                           "from objectstore import _store;"
                           " print(sorted((k, v) for k, v in vars(_store).items()"
                           " if isinstance(v, int) and not k.startswith('__')))")
            self.assertEqual(result.returncode, 0, result.stderr[-300:])
            self.assertIn("_ATTEMPTS", result.stdout)
            self.assertIn("_FANOUT", result.stdout)

    def test_the_private_structure_is_enumerable(self):
        with Built() as arms:
            result = probe(arms[_mlr.CONTRACT],
                           "from objectstore import _store;"
                           " print([n for n in dir(_store) if n.startswith('_')"
                           " and not n.startswith('__')])")
            self.assertEqual(result.returncode, 0, result.stderr[-300:])
            for name in ("_checksum", "_path_for", "_with_retries", "_ChecksumMismatch"):
                with self.subTest(name=name):
                    self.assertIn(name, result.stdout)

    def test_disassembly_renders_the_logic_the_source_would_have_shown(self):
        with Built() as arms:
            result = probe(arms[_mlr.CONTRACT],
                           "import io, dis; from objectstore import _store\n"
                           "buf = io.StringIO()\n"
                           "for name in dir(_store):\n"
                           "    obj = getattr(_store, name)\n"
                           "    if hasattr(obj, '__code__'): dis.dis(obj, file=buf)\n"
                           "print(len(buf.getvalue()))")
            self.assertEqual(result.returncode, 0, result.stderr[-300:])
            self.assertGreater(int(result.stdout.strip()), 1000)

    def test_the_public_representation_is_small_and_identical_in_both_arms(self):
        """§18: the contract is not the whole public surface, so report what the rest costs."""
        sizes = {}
        with Built() as arms:
            for arm, built in arms.items():
                result = probe(built,
                               "import inspect, objectstore\n"
                               "total = len(inspect.getdoc(objectstore) or '')\n"
                               "for n in objectstore.__all__:\n"
                               "    o = getattr(objectstore, n)\n"
                               "    total += len(inspect.getdoc(o) or '')\n"
                               "    try: total += len(str(inspect.signature(o)))\n"
                               "    except Exception: pass\n"
                               "print(total)")
                self.assertEqual(result.returncode, 0, result.stderr[-300:])
                sizes[arm] = int(result.stdout.strip())
        self.assertEqual(sizes[_mlr.FULL], sizes[_mlr.CONTRACT])
        contract_doc = (_mlr.FIXTURE / "base" / "docs" / "storage-contract.md").stat().st_size
        self.assertLess(sizes[_mlr.CONTRACT], contract_doc,
                        "docstrings that rivalled the contract would make it the smaller half")
