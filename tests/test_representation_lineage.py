"""Representation lineage and observer isolation.

MLR-C3D found the instrument losing information it had already classified. An agent read the
module's source; the executor echoed that read into `worker.log`; the agent read the log back; and
the log's path said `harness`, so implementation source was counted as harness. A second run listed
the repository and the module's file names were counted as behaviour.

Both are one defect: the measurement asked *how* text arrived and treated the answer as *what the
text was*. These tests hold the repair to that diagnosis rather than to the two symptoms — the
adversarial matrix covers copy, replay, search, version control, introspection and self-authored
text, and it must keep answering correctly when a route nobody anticipated delivers the same bytes.

Nothing here invokes a model.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _lineage       # noqa: E402
import _mlr           # noqa: E402
import _mlr_context   # noqa: E402
import _mlr_run       # noqa: E402

MODULE = _mlr.FIXTURE / "runtime" / "objectstore"


class Arm:
    def __init__(self, arm=_mlr.FULL):
        self.arm = arm

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.built = _mlr.materialise(self.arm, self.tmp / "arm")
        self.workspace = Path(self.built["workspace"])
        return self

    def source(self, name="_store.py") -> str:
        return (self.workspace / _mlr.VENDORED / "objectstore" / name).read_text(encoding="utf-8")

    def application(self) -> str:
        return (self.workspace / "app" / "exports.py").read_text(encoding="utf-8")

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


class FingerprintTest(unittest.TestCase):
    """The marks by which the module's text is recognised must actually be distinctive."""

    maxDiff = None

    def test_the_fingerprint_comes_from_the_module_source(self):
        marks = _lineage.source_fingerprint(MODULE)
        self.assertGreater(len(marks), 40)
        self.assertTrue(all(len(m) >= _lineage.MIN_FINGERPRINT for m in marks))

    def test_no_fingerprint_line_appears_anywhere_else_in_the_fixture(self):
        """A mark shared with the application would make application text look like source."""
        marks = _lineage.source_fingerprint(MODULE)
        elsewhere = [
            *(_mlr.FIXTURE / "base").rglob("*.py"),
            *(_mlr.FIXTURE / "reference").rglob("*.py"),
            _mlr.FIXTURE / "base" / "docs" / "storage-contract.md",
            _mlr.FIXTURE / "tasks" / "external.md",
            _mlr.FIXTURE / "hidden" / "external_test_v2.py",
        ]
        for path in elsewhere:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertEqual(_lineage.source_in(text, marks)["bytes"], 0,
                                 f"{path.name} collides with the module fingerprint")

    def test_a_short_generic_line_is_never_a_mark(self):
        marks = _lineage.source_fingerprint(MODULE)
        for generic in ("import os", "return None", "pass", "import hashlib"):
            with self.subTest(line=generic):
                self.assertNotIn(generic, marks)

    def test_identity_is_order_independent(self):
        """The same lines in a different order are the same information, not two of it."""
        a = _lineage.source_identity("alpha\nbeta\ngamma")
        b = _lineage.source_identity("gamma\nalpha\nbeta")
        self.assertEqual(a, b)
        self.assertNotEqual(a, _lineage.source_identity("alpha\nbeta"))


class AdversarialProvenanceTest(unittest.TestCase):
    """Every delivery route the matrix names, with its expected origin declared up front."""

    maxDiff = None

    def resolve(self, arm, route, requested, text):
        return _mlr_context.resolve_origin(route, requested, text)

    def test_a_direct_source_read_counts_the_whole_delivered_rendering(self):
        with Arm() as arm:
            src = arm.source()
            got = self.resolve(arm, _mlr_context.SOURCE_FILE,
                               _lineage.IMPLEMENTATION_SOURCE, src)
            self.assertEqual(got["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(got["source_bytes"], len(src.encode("utf-8")))
            self.assertFalse(got["by_lineage"], "the path already knew this one")

    def test_source_echoed_through_a_harness_log_is_still_source(self):
        """The MLR-C3D defect. Three of five DeepSeek runs read their own worker log."""
        with Arm() as arm:
            got = self.resolve(arm, _mlr_context.SOURCE_FILE, _mlr_context.HARNESS,
                               "> Read _store.py\n" + arm.source() + "\n> done")
            self.assertEqual(got["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertGreater(got["source_bytes"], 1000)
            self.assertTrue(got["by_lineage"])

    def test_application_text_replayed_through_a_log_does_not_become_source(self):
        with Arm() as arm:
            got = self.resolve(arm, _mlr_context.SOURCE_FILE, _mlr_context.HARNESS,
                               "> Read exports.py\n" + arm.application())
            self.assertEqual(got["origin"], _mlr_context.HARNESS)
            self.assertEqual(got["source_bytes"], 0)

    def test_a_mixed_log_charges_only_the_source_lines(self):
        with Arm() as arm:
            src = arm.source()
            mixed = "harness preamble\n" + src[:600] + "\n" + arm.application()[:300]
            got = self.resolve(arm, _mlr_context.SOURCE_FILE, _mlr_context.HARNESS, mixed)
            self.assertEqual(got["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertGreater(got["source_bytes"], 0)
            self.assertLess(got["source_bytes"], len(mixed.encode("utf-8")))

    def test_a_copy_through_a_scratch_file_keeps_its_ancestry(self):
        with Arm() as arm:
            got = self.resolve(arm, _mlr_context.SOURCE_FILE, _mlr_context.OTHER, arm.source())
            self.assertEqual(got["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertTrue(got["by_lineage"])

    def test_a_grep_excerpt_is_charged_for_the_lines_it_returned(self):
        with Arm() as arm:
            line = '_store.py:29:    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()'
            got = self.resolve(arm, _mlr_context.SEARCH, _mlr_context.OTHER, line)
            self.assertEqual(got["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertGreater(got["source_bytes"], 0)
            self.assertLess(got["source_bytes"], 200, "an excerpt is not the whole file")

    def test_git_ls_files_is_metadata_and_never_source_bytes(self):
        """The second MLR-C3D escape. File names disclose structure, not implementation."""
        with Arm() as arm:
            listing = ("third_party/objectstore-1.4.0/objectstore/_store.py\n"
                       "third_party/objectstore-1.4.0/objectstore/_backend.py\n")
            got = self.resolve(arm, _mlr_context.UNKNOWN, _mlr_context.OTHER, listing)
            self.assertEqual(got["origin"], _lineage.IMPLEMENTATION_METADATA)
            # MLR-C3D-R3: a request family outranks file names, because a test run that prints one
            # module path is a test run. The names are still counted; only the label of the container
            # moves.
            run = self.resolve(arm, _mlr_context.RUN, _mlr_context.BEHAVIOUR, listing)
            self.assertEqual(run["origin"], _mlr_context.BEHAVIOUR)
            self.assertTrue([c for c in run["components"]
                             if c["form"] == _lineage.PATH_METADATA])
            self.assertEqual(got["source_bytes"], 0)
            self.assertGreater(got["metadata"]["references"], 0)
            self.assertIn("_store.py", got["metadata"]["names"])

    def test_git_show_that_returns_source_is_source(self):
        with Arm() as arm:
            got = self.resolve(arm, _mlr_context.RUN, _mlr_context.BEHAVIOUR, arm.source())
            self.assertEqual(got["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertTrue(got["by_lineage"])

    def test_a_test_run_whose_traceback_names_a_file_stays_a_test_run(self):
        """Mixed provenance is decided by share, not by the smallest part of the artifact."""
        with Arm() as arm:
            output = "Ran 5 tests\n" * 30 + '  File "objectstore/_store.py", in _with_retries'
            got = self.resolve(arm, _mlr_context.RUN, _mlr_context.BEHAVIOUR, output)
            self.assertEqual(got["origin"], _mlr_context.BEHAVIOUR)
            self.assertEqual(got["source_bytes"], 0)
            self.assertGreater(got["metadata"]["references"], 0,
                               "the disclosure is still recorded on the item")

    def test_model_authored_text_naming_an_internal_is_not_repository_source(self):
        with Arm() as arm:
            got = self.resolve(arm, _mlr_context.UNKNOWN, _mlr_context.OTHER,
                               "Next I will check _ATTEMPTS and _FANOUT in the store module.")
            self.assertEqual(got["source_bytes"], 0)
            self.assertNotEqual(got["origin"], _lineage.IMPLEMENTATION_SOURCE)

    def test_introspection_output_stays_runtime_and_never_becomes_source(self):
        with Arm() as arm:
            for text in ("LOAD_GLOBAL _checksum\n" * 50,
                         "{'_ATTEMPTS': 3, '_FANOUT': 2}"):
                with self.subTest(text=text[:24]):
                    got = self.resolve(arm, _mlr_context.INTROSPECTION,
                                       _lineage.IMPLEMENTATION_RUNTIME, text)
                    self.assertEqual(got["origin"], _lineage.IMPLEMENTATION_RUNTIME)
                    self.assertEqual(got["source_bytes"], 0)

    def test_a_public_signature_is_not_charged_as_implementation(self):
        with Arm() as arm:
            got = self.resolve(arm, _mlr_context.INTROSPECTION, _mlr_context.PUBLIC_CONTRACT,
                               "put(key: str, payload: bytes) -> None")
            self.assertEqual(got["origin"], _mlr_context.PUBLIC_CONTRACT)
            self.assertEqual(got["source_bytes"], 0)


SCHEMA = """
CREATE TABLE message (id text PRIMARY KEY, session_id text, time_created integer,
                      time_updated integer, data text);
CREATE TABLE part (id text PRIMARY KEY, message_id text, session_id text, time_created integer,
                   time_updated integer, data text);
"""


class ReplayAccountingTest(unittest.TestCase):
    """Replay must cost context without inventing new information."""

    maxDiff = None

    _seq = 0

    def ledger(self, arm, deliveries):
        ReplayAccountingTest._seq += 1
        db = arm.tmp / f"w{ReplayAccountingTest._seq}.db"
        conn = sqlite3.connect(db)
        conn.executescript(SCHEMA)
        conn.execute("INSERT INTO message VALUES ('m1','s',1,1,?)",
                     (json.dumps({"role": "assistant", "modelID": "m", "providerID": "p"}),))
        n = 0

        def part(data):
            nonlocal n
            n += 1
            conn.execute("INSERT INTO part VALUES (?,?,?,?,?,?)",
                         (f"p{n:03d}", "m1", "s", n, n, json.dumps(data)))

        for path, text in deliveries:
            part({"type": "step-start"})
            part({"type": "tool", "tool": "read", "state": {
                "status": "completed", "input": {"filePath": str(path)},
                "output": text, "metadata": {}}})
        part({"type": "step-start"})
        part({"type": "step-finish", "tokens": {"input": 1, "output": 1, "reasoning": 0,
                                                "cache": {"read": 0, "write": 0}}, "cost": 0})
        conn.commit()
        conn.close()
        return _mlr_context.consumed(db, arm.built)

    def test_the_same_source_replayed_is_one_representation_and_two_deliveries(self):
        with Arm() as arm:
            path = arm.workspace / _mlr.VENDORED / "objectstore" / "_store.py"
            log = arm.workspace / "DeepSeekAndDestroy" / "worker.log"
            led = self.ledger(arm, [(path, arm.source()), (log, "> Read\n" + arm.source())])
            source = led["implementation_source"]
            self.assertEqual(source["distinct_representations"], 1)
            self.assertEqual(source["replays"], 1)
            self.assertGreater(source["delivered_bytes"], source["unique_bytes"])
            self.assertEqual(led["attributed_by_lineage"], 1)

    def test_reading_the_same_file_twice_does_not_inflate_unique_source(self):
        with Arm() as arm:
            path = arm.workspace / _mlr.VENDORED / "objectstore" / "_store.py"
            once = self.ledger(arm, [(path, arm.source())])
            twice = self.ledger(arm, [(path, arm.source()), (path, arm.source())])
            self.assertEqual(once["implementation_source"]["unique_bytes"],
                             twice["implementation_source"]["unique_bytes"])
            self.assertGreater(twice["implementation_source"]["delivered_bytes"],
                               once["implementation_source"]["delivered_bytes"])

    def test_file_names_never_accumulate_into_source_bytes(self):
        with Arm() as arm:
            listing = "\n".join(f"third_party/objectstore-1.4.0/objectstore/{n}"
                                for n in ("_store.py", "_backend.py", "_errors.py")) * 50
            path = arm.workspace / "listing.txt"
            led = self.ledger(arm, [(path, listing)])
            self.assertEqual(led["implementation_source"]["unique_bytes"], 0)
            self.assertGreater(led["implementation_metadata"]["references"], 0)

    def test_unknown_disclosure_is_unresolved_rather_than_zero(self):
        """Honest incompleteness beats clean-looking false precision."""
        with Arm() as arm:
            path = arm.workspace / "mystery.txt"
            led = self.ledger(arm, [(path, "the retry count is _ATTEMPTS which is three")])
            self.assertEqual(led["unresolved"]["items"], 1)
            self.assertGreater(led["unresolved"]["bytes"], 0)


class ObserverIsolationTest(unittest.TestCase):
    """What the evaluator creates, and what the evaluated agent can reach."""

    maxDiff = None

    def prepared(self, tmp, arm=_mlr.CONTRACT):
        built = _mlr.materialise(arm, tmp / "arm")
        run, db, contract = _mlr_run._prepare(built, tmp, model="test/model",
                                              task=_mlr.FIXTURE / "tasks" / "external.md")
        return built, run, db

    def test_the_session_transcript_database_is_outside_the_workspace(self):
        """OpenCode's own record of the run must not be part of the run's own repository."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built, _, db = self.prepared(tmp)
            workspace = Path(built["workspace"]).resolve()
            self.assertNotIn(workspace, Path(db).resolve().parents)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_hidden_oracle_is_not_in_the_workspace_during_the_run(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            built, _, _ = self.prepared(tmp)
            workspace = Path(built["workspace"])
            self.assertEqual(list(workspace.rglob("external_test*.py")), [])
            self.assertEqual(list(workspace.rglob("*fetch_or_create*")), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_harness_artifact_names_the_arm_or_the_experiment(self):
        """Treatment blindness: an agent must not be able to read which arm it is in."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built, run, _ = self.prepared(tmp)
            leaked = []
            for path in Path(run).rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
                for token in ("full-headroom", "mlr-deepseek", "contract arm", "\"arm\"",
                              "treatment", "third_party"):
                    if token in text:
                        leaked.append((path.name, token))
            self.assertEqual(leaked, [], f"harness artifacts disclose the treatment: {leaked}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_each_attempt_gets_its_own_workspace_so_samples_cannot_see_each_other(self):
        """`P12`: a fresh sample that could read the previous one is not fresh."""
        first = Path(tempfile.mkdtemp())
        second = Path(tempfile.mkdtemp())
        try:
            a, _, _ = self.prepared(first)
            b, _, _ = self.prepared(second)
            self.assertNotEqual(Path(a["workspace"]).resolve(),
                                Path(b["workspace"]).resolve())
            self.assertNotIn(Path(first).resolve(), Path(b["workspace"]).resolve().parents)
        finally:
            shutil.rmtree(first, ignore_errors=True)
            shutil.rmtree(second, ignore_errors=True)

    def test_the_worker_log_remains_inside_the_workspace_and_that_is_recorded(self):
        """The channel MLR-C3D found. DSD binds the log into the run root, so the repair is
        measurement-side; this pins the fact so it cannot be quietly forgotten."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built, run, _ = self.prepared(tmp)
            workspace = Path(built["workspace"]).resolve()
            self.assertIn(workspace, Path(run).resolve().parents,
                          "DSD requires the run root under the project root")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class GenericityTest(unittest.TestCase):
    """Lineage mechanics must not learn this fixture's vocabulary."""

    maxDiff = None

    def test_the_lineage_module_knows_nothing_about_this_experiment(self):
        text = (ROOT / "evals" / "_lineage.py").read_text(encoding="utf-8").lower()
        for token in ("objectstore", "_store", "contract arm", "full arm", "modularity",
                      "download_export", "notification"):
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_it_takes_its_fingerprint_from_whatever_source_it_is_given(self):
        """Given a different module, it produces that module's marks and no others."""
        tmp = Path(tempfile.mkdtemp())
        try:
            other = tmp / "other"
            other.mkdir()
            (other / "thing.py").write_text(
                "def compute_the_special_value(argument):\n"
                "    return argument * 41 + 1  # a distinctive line\n", encoding="utf-8")
            marks = _lineage.source_fingerprint(other)
            self.assertTrue(marks)
            self.assertEqual(_lineage.source_in("def compute_the_special_value(argument):",
                                                marks)["lines"], 1)
            self.assertEqual(_lineage.source_in("import os", marks)["lines"], 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
