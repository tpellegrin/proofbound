"""Where information came from, what it looks like, and how it arrived — three questions.

The paired DeepSeek calibration was invalidated by a single item: an agent disassembled the compiled
module into a temporary file and read the file back, and 29,499 bytes of the module's interior were
recorded as `other` because the last path they had passed through was `/tmp`. The same run contained
the mirror-image mistake — a shell command that merely *named* the module's directory turned its own
directory listing into implementation source — and a third case that neither rule could have handled:
an agent with no source available reconstructed two of the module's source lines from bytecode, and
the bytes matched source exactly while the origin was the model.

No single rule survives all three. Path-first loses the disassembly. Content-first promotes the
reconstruction to a boundary failure that never happened. So origin follows the strongest evidence
available — a link to the event that produced the information, then the identity of the artifact
opened, then the family of request, and only then the bytes — while *form* answers the separate
question of what the delivered representation encodes, and *route* answers how it arrived.

The test that matters most is the last one: two byte-identical representations must be able to carry
different origins, because they were produced by different histories.

Nothing here invokes a model. The retained-trajectory cases are derived from evidence that has
already been paid for and is not re-run.
"""
from __future__ import annotations

import json
import re
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

MODULE = _mlr.FIXTURE / "runtime" / "objectstore"
TRAJECTORIES = _mlr.FIXTURE / "trajectories"


class Arm:
    def __init__(self, arm=_mlr.FULL):
        self.arm = arm

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.built = _mlr.materialise(self.arm, self.tmp / "arm")
        self.workspace = Path(self.built["workspace"])
        return self

    def source(self, name="_store.py") -> str:
        return (MODULE / name).read_text(encoding="utf-8")

    def vendored(self, name="_store.py") -> str:
        return str(self.workspace / _mlr.VENDORED / "objectstore" / name)

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


def call():
    return {"type": "step-start"}


def bash(command, output, status="completed"):
    return {"type": "tool", "tool": "bash",
            "state": {"input": {"command": command}, "output": output, "status": status}}


def read(path, output):
    return {"type": "tool", "tool": "read",
            "state": {"input": {"filePath": str(path)}, "output": output, "status": "completed"}}


def write_tool(path, output=""):
    return {"type": "tool", "tool": "write",
            "state": {"input": {"filePath": str(path)}, "output": output, "status": "completed"}}


def thought(text):
    return {"type": "reasoning", "text": text}


def events(parts, role="assistant"):
    out = []
    for ordinal, part in enumerate(parts):
        out.append({"ordinal": ordinal, "part_id": f"p{ordinal}", "message_id": "m",
                    "time_created": ordinal, "role": part.pop("role", role), "summary": False,
                    "part": part, "message": {}})
    return out


def ledger(parts, built):
    return _mlr_context.ledger(events(parts), built)


def only(led, kind_prefix="tool:"):
    """The one attributed item of interest, when a case delivers exactly one."""
    items = [i for i in led["items"] if i["kind"].startswith(kind_prefix)]
    assert len(items) == 1, [i["kind"] for i in items]
    return items[0]


DISASSEMBLY = "\n".join(
    ["Disassembly of <code object put>:",
     "objectstore/_store.py version 3.9.6"] +
    [f"  {n}          {n * 2} LOAD_GLOBAL              {n} (_checksum)" for n in range(1, 40)])

RUNTIME_DUMP = "\n".join(
    f"{{'_ATTEMPTS': 3, '_FANOUT': 2, '_ROOT_ENV': 'OBJECTSTORE_ROOT'}} entry {n}"
    for n in range(20))


class RepresentationFormTest(unittest.TestCase):
    """What a delivered text encodes, decided by the text and by nothing else."""

    maxDiff = None

    def decompose(self, text):
        return _mlr_context._components(text)

    def test_module_source_lines_are_source_form(self):
        comp = self.decompose((MODULE / "_store.py").read_text(encoding="utf-8"))
        self.assertEqual(_lineage.form_of(comp), _lineage.SOURCE_FORM)

    def test_opcodes_are_disassembly(self):
        comp = self.decompose(DISASSEMBLY)
        self.assertEqual(_lineage.form_of(comp), _lineage.DISASSEMBLY)

    def test_a_disassembly_behind_a_line_numbering_reader_is_still_a_disassembly(self):
        """The pair-5 shape. The old decomposition undecorated for source and nothing else."""
        numbered = "\n".join(f"{n + 1}: {line}" for n, line in enumerate(DISASSEMBLY.splitlines()))
        self.assertEqual(_lineage.form_of(self.decompose(numbered)), _lineage.DISASSEMBLY)

    def test_a_namespace_dump_is_runtime_structure(self):
        self.assertEqual(_lineage.form_of(self.decompose(RUNTIME_DUMP)),
                         _lineage.RUNTIME_STRUCTURE)

    def test_module_file_names_alone_are_path_metadata(self):
        listing = "\n".join(f"objectstore/{n}" for n in ("_store.py", "_backend.py", "_errors.py"))
        self.assertEqual(_lineage.form_of(self.decompose(listing)), _lineage.PATH_METADATA)

    def test_components_are_disjoint_and_sum_to_the_whole(self):
        """No byte may be counted under two forms; §17."""
        mixed = "header line\n" + DISASSEMBLY + "\n" + \
                (MODULE / "_errors.py").read_text(encoding="utf-8")
        comp = self.decompose(mixed)
        self.assertEqual(sum(comp["bytes"].values()), comp["total"])
        self.assertGreater(comp["bytes"][_lineage.DISASSEMBLY], 0)
        self.assertGreater(comp["bytes"][_lineage.SOURCE_FORM], 0)

    def test_a_metadata_header_cannot_hide_a_dominant_body(self):
        """§15. The predicate that required zero metadata is what let 29 KB of opcodes through."""
        header = "\n".join("objectstore/_store.py referenced" for _ in range(30))
        comp = self.decompose(header + "\n" + DISASSEMBLY * 4)
        self.assertGreater(comp["bytes"][_lineage.PATH_METADATA], 0)
        self.assertEqual(_lineage.form_of(comp), _lineage.DISASSEMBLY)


class CausalPrecedenceTest(unittest.TestCase):
    """The adversarial matrix: every route, with the origin it must produce declared up front."""

    maxDiff = None

    def test_a_direct_source_read_is_source(self):
        with Arm() as arm:
            item = only(ledger([call(), read(arm.vendored(), arm.source()), call()], arm.built))
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(item["form"], _lineage.SOURCE_FORM)
            self.assertEqual(item["basis"], _mlr_context.BASIS_ARTIFACT)

    def test_source_copied_to_a_temporary_file_is_still_source(self):
        """§92 A. The copy changes the route and nothing else."""
        with Arm() as arm:
            led = ledger([call(),
                          bash(f"cp {arm.vendored()} /tmp/x", ""),
                          call(),
                          read("/tmp/x", arm.source()),
                          call()], arm.built)
            item = [i for i in led["items"] if i["detail"] == "/tmp/x"][0]
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(item["basis"], _mlr_context.BASIS_ANCESTRY)
            self.assertGreater(led["implementation_source_unique_bytes"], 1000)

    def test_a_disassembly_delivered_inline_is_runtime(self):
        with Arm(_mlr.CONTRACT) as arm:
            item = only(ledger([call(),
                                bash("python -c 'import dis, objectstore; dis.dis(objectstore)'",
                                     DISASSEMBLY),
                                call()], arm.built))
            self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertEqual(item["form"], _lineage.DISASSEMBLY)

    def test_a_disassembly_through_a_temporary_file_is_still_runtime(self):
        """§92 B, and the defect that invalidated the paired experiment."""
        with Arm(_mlr.CONTRACT) as arm:
            led = ledger([call(),
                          bash("python -c 'import dis, marshal, objectstore' > /tmp/dis.txt 2>&1; "
                               "wc -l /tmp/dis.txt", "     593 /tmp/dis.txt"),
                          call(),
                          read("/tmp/dis.txt", DISASSEMBLY),
                          call()], arm.built)
            item = [i for i in led["items"] if i["detail"] == "/tmp/dis.txt"][0]
            self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertEqual(item["form"], _lineage.DISASSEMBLY)
            self.assertEqual(item["basis"], _mlr_context.BASIS_ANCESTRY)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)

    def test_the_byte_count_that_produced_the_file_is_not_charged_for_its_body(self):
        """§38. The `wc -l` call exposed thirty-four bytes and must be charged for thirty-four."""
        with Arm(_mlr.CONTRACT) as arm:
            led = ledger([call(),
                          bash("python -c 'import dis, marshal' > /tmp/dis.txt; wc -l /tmp/dis.txt",
                               "     593 /tmp/dis.txt"),
                          call(),
                          read("/tmp/dis.txt", DISASSEMBLY),
                          call()], arm.built)
            producer = [i for i in led["items"] if i["kind"] == "tool:bash"][0]
            self.assertLess(producer["bytes"], 100)
            self.assertNotEqual(producer["form"], _lineage.DISASSEMBLY)

    def test_a_reconstructed_source_line_is_not_direct_source(self):
        """§92 C and the reason content-first would have been the wrong repair."""
        with Arm(_mlr.CONTRACT) as arm:
            line = sorted(_lineage.source_fingerprint(MODULE), key=len)[-1]
            led = ledger([call(),
                          bash("python -c 'import dis, objectstore'", DISASSEMBLY),
                          call(),
                          thought(f"From the disassembly the body must be:\n{line}\nwhich explains "
                                  "the behaviour I need to preserve."),
                          call()], arm.built)
            item = [i for i in led["items"] if i["kind"] == "assistant:reasoning"][0]
            self.assertEqual(item["origin"], _lineage.MODEL_DERIVED)
            self.assertEqual(item["basis"], _mlr_context.BASIS_AUTHOR)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)

    def test_a_reconstruction_is_visible_as_its_own_representation(self):
        """§92 D. Not direct source, and not invisible either."""
        with Arm(_mlr.CONTRACT) as arm:
            line = sorted(_lineage.source_fingerprint(MODULE), key=len)[-1]
            led = ledger([call(),
                          bash("python -c 'import dis, objectstore'", DISASSEMBLY),
                          call(),
                          thought(f"the body is:\n{line}\n"),
                          call()], arm.built)
            recon = led["source_equivalent_reconstruction"]
            self.assertGreater(recon["unique_bytes"], 0)
            self.assertEqual(recon["by_origin"], {_lineage.MODEL_DERIVED: 1})
            self.assertEqual(recon["after_implementation_representation"], 1)

    def test_a_matching_line_with_no_prior_evidence_is_still_not_source(self):
        """§34. Content equality is never promoted to provenance for text the model wrote."""
        with Arm(_mlr.CONTRACT) as arm:
            line = sorted(_lineage.source_fingerprint(MODULE), key=len)[-1]
            led = ledger([call(), thought(f"I would write:\n{line}\n"), call()], arm.built)
            item = [i for i in led["items"] if i["kind"] == "assistant:reasoning"][0]
            self.assertEqual(item["origin"], _lineage.MODEL_DERIVED)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)
            self.assertEqual(
                led["source_equivalent_reconstruction"]["after_implementation_representation"], 0)

    def test_reconstruction_written_to_a_file_and_read_back_stays_model_derived(self):
        """§21's third temporary-file case: the bytes came out of the model, not the module."""
        with Arm(_mlr.CONTRACT) as arm:
            line = sorted(_lineage.source_fingerprint(MODULE), key=len)[-1]
            led = ledger([call(),
                          bash(f"cat > /tmp/guess.py <<'EOF'\n{line}\nEOF", ""),
                          call(),
                          read("/tmp/guess.py", line),
                          call()], arm.built)
            item = [i for i in led["items"] if i["detail"] == "/tmp/guess.py"][0]
            self.assertEqual(item["origin"], _lineage.MODEL_DERIVED)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)

    def test_listing_the_repository_is_metadata(self):
        """§79 G."""
        with Arm() as arm:
            listing = "\n".join(f"third_party/objectstore-1.4.0/objectstore/{n}"
                                for n in ("__init__.py", "_store.py", "_backend.py", "_errors.py"))
            item = only(ledger([call(), bash("git ls-files", listing), call()], arm.built))
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_METADATA)
            self.assertEqual(item["form"], _lineage.PATH_METADATA)
            self.assertEqual(item["source_bytes"], 0)

    def test_showing_a_source_file_through_version_control_is_source(self):
        """§79 H."""
        with Arm() as arm:
            item = only(ledger([call(),
                                bash(f"git show HEAD:{_mlr.VENDORED.as_posix()}/objectstore/"
                                     "_store.py", arm.source()),
                                call()], arm.built))
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertGreater(item["source_bytes"], 1000)

    def test_naming_the_module_directory_does_not_make_output_source(self):
        """§92 G. The `full` over-attribution, fixed generically rather than for its two runs."""
        with Arm() as arm:
            output = ("1.4.0 /tmp/arm/runtime/objectstore/__init__.pyc\n"
                      "PYTHONPATH=/tmp/arm/runtime\nobjectstore\n")
            item = only(ledger([call(),
                                bash(f"cat {_mlr.VENDORED.as_posix()}/VERSION; "
                                     f"ls {_mlr.VENDORED.as_posix()}", output),
                                call()], arm.built))
            self.assertNotEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(item["source_bytes"], 0)

    def test_a_diff_is_split_by_what_it_actually_returned(self):
        """§79 J. Marker decoration is stripped before the line is judged."""
        with Arm() as arm:
            lines = [l for l in arm.source().splitlines() if len(l.strip()) >= 40][:6]
            diff = "diff --git a/objectstore/_store.py b/objectstore/_store.py\n" + \
                   "\n".join("+" + l for l in lines)
            item = only(ledger([call(), bash("git diff", diff), call()], arm.built))
            self.assertGreater(item["form_bytes"][_lineage.SOURCE_FORM], 0)
            self.assertGreater(item["form_bytes"][_lineage.PATH_METADATA], 0)
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)

    def test_a_log_that_echoes_a_source_read_keeps_the_source_ancestry(self):
        """§92 M. The log is a route."""
        with Arm() as arm:
            log = arm.workspace / "DeepSeekAndDestroy" / "worker.log"
            led = ledger([call(), read(arm.vendored(), arm.source()), call(),
                          read(log, "> Read\n" + arm.source()), call()], arm.built)
            echo = [i for i in led["items"] if str(log) in i["detail"]][0]
            self.assertEqual(echo["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(echo["basis"], _mlr_context.BASIS_ANCESTRY)

    def test_a_log_that_echoes_a_disassembly_keeps_the_runtime_ancestry(self):
        with Arm(_mlr.CONTRACT) as arm:
            log = arm.workspace / "DeepSeekAndDestroy" / "worker.log"
            led = ledger([call(), bash("python -c 'import dis, objectstore'", DISASSEMBLY), call(),
                          read(log, "> Bash\n" + DISASSEMBLY), call()], arm.built)
            echo = [i for i in led["items"] if str(log) in i["detail"]][0]
            self.assertEqual(echo["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)

    def test_a_log_that_echoes_the_models_own_text_keeps_the_model_ancestry(self):
        """The case content-first would get wrong: source-shaped bytes, model history."""
        with Arm(_mlr.CONTRACT) as arm:
            log = arm.workspace / "DeepSeekAndDestroy" / "worker.log"
            line = sorted(_lineage.source_fingerprint(MODULE), key=len)[-1]
            led = ledger([call(), thought(f"my guess:\n{line}\n"), call(),
                          read(log, "> assistant\nmy guess:\n" + line), call()], arm.built)
            echo = [i for i in led["items"] if str(log) in i["detail"]][0]
            self.assertEqual(echo["origin"], _lineage.MODEL_DERIVED)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)

    def test_a_public_docstring_is_public(self):
        """§79 N."""
        with Arm(_mlr.CONTRACT) as arm:
            public = ("Help on package objectstore:\n\nNAME\n    objectstore\n\n"
                      "FUNCTIONS\n    put(key: str, payload: bytes) -> None\n"
                      "        Store `payload` under `key`.\n")
            item = only(ledger([call(), bash("python -c 'help(objectstore)'", public), call()],
                               arm.built))
            self.assertEqual(item["origin"], _mlr_context.PUBLIC_CONTRACT)

    def test_a_traceback_is_not_source_because_it_names_a_file(self):
        """§79 O."""
        with Arm(_mlr.CONTRACT) as arm:
            trace = ('Traceback (most recent call last):\n'
                     '  File "objectstore/_store.py", line 55, in get\n'
                     'objectstore._errors.NotFound: exports/eu/u-3/monthly.csv\n')
            item = only(ledger([call(), bash("python -m unittest tests.test_service", trace),
                                call()], arm.built))
            self.assertEqual(item["source_bytes"], 0)
            self.assertNotEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)

    def test_internal_names_with_no_recognisable_form_fail_closed(self):
        """§79 R, §56. Missing is never zero."""
        with Arm(_mlr.CONTRACT) as arm:
            led = ledger([call(), read(arm.workspace / "mystery.txt",
                                       "the retry count is _ATTEMPTS which is three"), call()],
                         arm.built)
            self.assertEqual(led["unresolved"]["items"], 1)
            self.assertGreater(led["unresolved"]["bytes"], 0)

    def test_known_ancestry_and_a_clear_form_are_not_unresolved(self):
        """§56's second half: the strongest evidence available is used, not withheld."""
        with Arm(_mlr.CONTRACT) as arm:
            led = ledger([call(), bash("python -c 'import dis, objectstore' > /tmp/d.txt", ""),
                          call(), read("/tmp/d.txt", DISASSEMBLY), call()], arm.built)
            self.assertEqual(led["unresolved"]["items"], 0)

    def test_rereading_the_same_material_does_not_inflate_unique_representation(self):
        """§92 K."""
        with Arm() as arm:
            once = ledger([call(), read(arm.vendored(), arm.source()), call()], arm.built)
            twice = ledger([call(), read(arm.vendored(), arm.source()), call(),
                            read(arm.vendored(), arm.source()), call()], arm.built)
            self.assertEqual(once["implementation_source"]["unique_bytes"],
                             twice["implementation_source"]["unique_bytes"])
            self.assertGreater(twice["implementation_source"]["delivered_bytes"],
                               once["implementation_source"]["delivered_bytes"])


class EscapeDetectionTest(unittest.TestCase):
    """Contradiction, not reclassification. §54, §55."""

    maxDiff = None

    def test_a_runtime_body_under_a_weakly_evidenced_other_is_a_contradiction(self):
        item = {"basis": _mlr_context.BASIS_DEFAULT, "origin": _mlr_context.OTHER,
                "bytes": 1000, "form_bytes": {f: 0 for f in _lineage.SUBSTANTIVE_FORMS}}
        item["form_bytes"][_lineage.DISASSEMBLY] = 950
        self.assertIsNotNone(_mlr_context.contradiction(item))

    def test_a_source_origin_with_no_source_content_is_a_contradiction(self):
        item = {"basis": _mlr_context.BASIS_ROUTE, "origin": _lineage.IMPLEMENTATION_SOURCE,
                "bytes": 300, "form_bytes": {f: 0 for f in _lineage.SUBSTANTIVE_FORMS}}
        item["form_bytes"][_lineage.PATH_METADATA] = 300
        self.assertIsNotNone(_mlr_context.contradiction(item))

    def test_a_reconstruction_under_a_settled_origin_is_not_an_escape(self):
        """Otherwise the instrument could not see the thing it was repaired to see."""
        item = {"basis": _mlr_context.BASIS_AUTHOR, "origin": _lineage.MODEL_DERIVED,
                "bytes": 200, "form_bytes": {f: 0 for f in _lineage.SUBSTANTIVE_FORMS}}
        item["form_bytes"][_lineage.SOURCE_FORM] = 200
        self.assertIsNone(_mlr_context.contradiction(item))

    def test_the_detector_never_changes_an_origin(self):
        with Arm(_mlr.CONTRACT) as arm:
            led = ledger([call(), bash("python -c 'import dis, objectstore'", DISASSEMBLY), call()],
                         arm.built)
            before = [i["origin"] for i in led["items"]]
            for item in led["items"]:
                _mlr_context.contradiction(item)
            self.assertEqual([i["origin"] for i in led["items"]], before)


class RetainedTrajectoryTest(unittest.TestCase):
    """The already-paid adversarial corpus. §30, §80.

    These fixtures are derived from the invalid paired run and are test material, not results. Each
    records the run it came from; none of them alters it.
    """

    maxDiff = None

    def load(self, name):
        doc = json.loads((TRAJECTORIES / f"{name}.json").read_text(encoding="utf-8"))
        parts = []
        for entry in doc["parts"]:
            kind = entry["type"]
            if kind == "step-start":
                parts.append(call())
                continue
            if kind == "tool":
                output = entry.get("output")
                if output is None:
                    output = (MODULE / entry["output_from_module"]).read_text(encoding="utf-8")
                parts.append({"type": "tool", "tool": entry["tool"],
                              "state": {"input": entry["input"], "output": output,
                                        "status": entry.get("status")}})
                continue
            parts.append({"type": kind, "text": entry.get("text", "")})
        return doc, _mlr_context.ledger(events(parts), doc["built"])

    def test_every_fixture_declares_where_it_came_from(self):
        """§31, §84. Derived material says so, and says which run it was derived from."""
        found = sorted(TRAJECTORIES.glob("*.json"))
        self.assertGreaterEqual(len(found), 6)
        for path in found:
            with self.subTest(fixture=path.stem):
                doc = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("derived", doc["kind"])
                self.assertIn("not an experiment record", doc["kind"])
                for field in ("experiment", "record", "arm", "pair", "note"):
                    self.assertIn(field, doc["derived_from"])

    def test_the_temporary_file_disassembly_is_runtime_and_was_recorded_as_other(self):
        """§32. The defect is closed, and the fixture shows what the old rule would have said."""
        doc, led = self.load("runtime-through-temporary-file")
        item = [i for i in led["items"] if i["kind"] == "tool:read"][0]
        self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
        self.assertEqual(item["form"], _lineage.DISASSEMBLY)
        self.assertEqual(item["basis"], _mlr_context.BASIS_ANCESTRY)
        self.assertEqual(led["implementation_source_unique_bytes"], 0)
        # What the path alone says, which is what the previous instrument recorded.
        self.assertEqual(_mlr_context.classify_file(item["detail"], doc["built"]),
                         _mlr_context.OTHER)

    def test_the_reconstruction_is_not_source_and_is_not_invisible(self):
        """§33. The most important regression: matching bytes, non-matching history."""
        doc, led = self.load("source-equivalent-reconstruction")
        item = [i for i in led["items"] if i["kind"].endswith("reasoning")][0]
        self.assertEqual(item["origin"], _lineage.MODEL_DERIVED)
        self.assertEqual(led["implementation_source_unique_bytes"], 0)
        recon = led["source_equivalent_reconstruction"]
        self.assertGreater(recon["unique_bytes"], 0)
        self.assertEqual(recon["after_implementation_representation"], 1)
        self.assertGreater(item["form_bytes"][_lineage.SOURCE_FORM], 0)

    def test_a_directory_mention_no_longer_charges_the_primary_measurand(self):
        """§31 of the report, and the second defect of the invalid run."""
        for pair in (4, 5):
            with self.subTest(pair=pair):
                _, led = self.load(f"module-directory-named-without-source-{pair}")
                self.assertEqual(led["implementation_source_unique_bytes"], 0)
                item = [i for i in led["items"] if i["kind"] == "tool:bash"][0]
                self.assertNotEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)

    def test_an_ordinary_source_read_is_unchanged(self):
        """The repair must not cost the measurement what it already measured correctly."""
        _, led = self.load("direct-source-read")
        item = [i for i in led["items"] if i["kind"] == "tool:read"][0]
        self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
        self.assertEqual(item["basis"], _mlr_context.BASIS_ARTIFACT)
        self.assertEqual(led["implementation_source_unique_bytes"],
                         len((MODULE / "_store.py").read_text(encoding="utf-8").encode("utf-8")))

    def test_an_ordinary_runtime_probe_is_unchanged(self):
        _, led = self.load("runtime-introspection-direct")
        item = [i for i in led["items"] if i["kind"] == "tool:bash"][0]
        self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
        self.assertEqual(led["implementation_source_unique_bytes"], 0)


SCHEMA = """
CREATE TABLE message (id text PRIMARY KEY, session_id text, time_created integer,
                      time_updated integer, data text);
CREATE TABLE part (id text PRIMARY KEY, message_id text, session_id text, time_created integer,
                   time_updated integer, data text);
"""


class RetrospectiveDiagnosisTest(unittest.TestCase):
    """Re-attributing a finished series is diagnosis of the instrument, never a new result. §50, §84.
    """

    maxDiff = None

    def series(self, arm, deliveries):
        """A minimal completed record, with one retained session it can be re-read from."""
        evidence = arm.tmp / "evidence" / "full-1"
        evidence.mkdir(parents=True)
        conn = sqlite3.connect(evidence / "worker.db")
        conn.executescript(SCHEMA)
        conn.execute("INSERT INTO message VALUES ('m1','s',1,1,?)",
                     (json.dumps({"role": "assistant"}),))
        for n, data in enumerate(deliveries, start=1):
            conn.execute("INSERT INTO part VALUES (?,?,?,?,?,?)",
                         (f"p{n:03d}", "m1", "s", n, n, json.dumps(data)))
        conn.commit()
        conn.close()
        return {
            "experiment": "series-under-test",
            "frozen_identity": "0" * 64,
            "telemetry_version": "an-earlier-version",
            "model": "provider/model",
            "arms": [_mlr.FULL],
            "measurements": [{
                "arm": _mlr.FULL, "repeat": 1, "attempt": 1, "validity": "valid",
                "outcome": {"correct": True},
                "evidence": str(evidence),
                "event_dir": f"{arm.built['workspace']}/plans/x/attempts/implementer-1",
            }],
        }

    def test_the_report_says_it_is_not_the_experiment_result(self):
        import pb_mlr
        with Arm() as arm:
            record = self.series(arm, [{"type": "step-start"},
                                       {"type": "tool", "tool": "read",
                                        "state": {"status": "completed",
                                                  "input": {"filePath": arm.vendored()},
                                                  "output": arm.source(), "metadata": {}}},
                                       {"type": "step-start"}])
            report = pb_mlr.retrospect(record)
            self.assertIn("not the recorded experiment result", report["kind"])
            self.assertEqual(report["source_record"]["telemetry_version"], "an-earlier-version")
            self.assertNotEqual(report["recomputed_under"]["telemetry_version"],
                                report["source_record"]["telemetry_version"])

    def test_the_source_record_is_not_modified(self):
        import pb_mlr
        with Arm() as arm:
            record = self.series(arm, [{"type": "step-start"}])
            before = json.dumps(record, sort_keys=True)
            pb_mlr.retrospect(record)
            self.assertEqual(json.dumps(record, sort_keys=True), before)

    def test_a_session_that_is_gone_is_reported_and_not_counted_as_clean(self):
        """Missing evidence is missing, never a clean pass."""
        import pb_mlr
        with Arm() as arm:
            record = self.series(arm, [{"type": "step-start"}])
            shutil.rmtree(Path(record["measurements"][0]["evidence"]))
            report = pb_mlr.retrospect(record)
            self.assertFalse(report["explained"])
            self.assertEqual(len(report["unavailable"]), 1)

    def test_relocated_sessions_are_found_by_the_name_the_record_carries(self):
        import pb_mlr
        with Arm() as arm:
            record = self.series(arm, [{"type": "step-start"}])
            moved = arm.tmp / "moved"
            moved.mkdir()
            shutil.move(str(Path(record["measurements"][0]["evidence"])), str(moved / "full-1"))
            self.assertFalse(pb_mlr.retrospect(record)["explained"])
            self.assertTrue(pb_mlr.retrospect(record, evidence_root=moved)["explained"])


class GenericityTest(unittest.TestCase):
    """§81. The reusable half must not know what it is measuring."""

    maxDiff = None

    # Identifiers that belong to this fixture, and tokens that name its arms or its milestone.
    FIXTURE_WORDS = ("objectstore", "_store", "_backend", "third_party", "pair 5", "pair 6")
    FIXTURE_TOKENS = (r"\bFULL\b", r"\bCONTRACT\b", r"\bMLR\b", r"\bC3D\b")

    def test_the_representation_layer_names_no_fixture(self):
        text = (ROOT / "evals" / "_lineage.py").read_text(encoding="utf-8")
        for word in self.FIXTURE_WORDS:
            with self.subTest(word=word):
                self.assertNotIn(word, text)
        for token in self.FIXTURE_TOKENS:
            with self.subTest(token=token):
                self.assertIsNone(re.search(token, text))

    def test_the_representation_layer_takes_its_vocabulary_as_arguments(self):
        """Fixture-specific truth lives in the caller, which is what makes it reusable."""
        comp = _lineage.components("anything at all", frozenset(), (), None)
        self.assertEqual(comp["bytes"][_lineage.SOURCE_FORM], 0)
        self.assertEqual(sum(comp["bytes"].values()), comp["total"])

    def test_forms_and_origins_are_separate_vocabularies(self):
        """A form is not an origin; conflating them is the defect this milestone repaired."""
        self.assertFalse(set(_lineage.FORMS) & set(_lineage.ORIGINS))


class PersistenceDisciplineTest(unittest.TestCase):
    """§82. Persist the link that cannot be recomputed; derive everything else."""

    maxDiff = None

    def test_the_session_indexes_hold_links_and_not_verdicts(self):
        with Arm(_mlr.CONTRACT) as arm:
            session = _mlr_context._Session(arm.built)
            session.note_artifact("/tmp/d.txt", _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertEqual(session.artifact("/tmp/d.txt"),
                             _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertIsNone(session.artifact("/tmp/other.txt"))

    def test_reconstruction_order_is_derived_rather_than_stored(self):
        """Whether reconstruction followed implementation is a fact about the item list."""
        with Arm(_mlr.CONTRACT) as arm:
            line = sorted(_lineage.source_fingerprint(MODULE), key=len)[-1]
            after = ledger([call(), bash("python -c 'import dis, objectstore'", DISASSEMBLY),
                            call(), thought(line), call()], arm.built)
            before = ledger([call(), thought(line), call(),
                             bash("python -c 'import dis, objectstore'", DISASSEMBLY), call()],
                            arm.built)
            self.assertEqual(
                after["source_equivalent_reconstruction"]["after_implementation_representation"], 1)
            self.assertEqual(
                before["source_equivalent_reconstruction"]["after_implementation_representation"], 0)


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
