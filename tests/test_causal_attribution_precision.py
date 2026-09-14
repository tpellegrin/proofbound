#!/usr/bin/env python3
"""Every way the same bytes can arrive, and what each of them is.

The `mlr-deepseek-v4-flash-high-paired-r4` experiment was invalidated by one confident mistake: a
`contract` run printed `objectstore.__doc__`, the module's public docstring matched the source
fingerprint, and two lines of public surface were recorded as direct implementation source. A later
read of the worker log replayed those two lines, inherited the label for the whole container, and
relabelled thirty-four kilobytes of disassembly as source — erasing the runtime substitution the
experiment exists to observe.

This file is the known-answer corpus for the repair. Each case states what it expects before it
asks, and the cases are chosen so that no fixture-specific rule could satisfy them together: the
same docstring is source through one route and public surface through another, the same log is
source when it replays a read and runtime when it replays a disassembly, and the same literal is
source in one arm and the model's own in the other.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import _lineage       # noqa: E402
import _mlr           # noqa: E402
import _mlr_context   # noqa: E402

MODULE = _mlr.FIXTURE / "runtime" / "objectstore"


class Arm:
    def __init__(self, arm=_mlr.FULL):
        self.arm = arm

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-precision-"))
        self.built = _mlr.materialise(self.arm, self.tmp / "arm")
        self.workspace = Path(self.built["workspace"])
        return self

    def source(self, name="_store.py") -> str:
        return (MODULE / name).read_text(encoding="utf-8")

    def vendored(self, name="_store.py") -> str:
        return str(self.workspace / _mlr.VENDORED / "objectstore" / name)

    def log(self) -> str:
        return str(self.workspace / "DeepSeekAndDestroy" / "worker.log")

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


def grep(pattern, output):
    return {"type": "tool", "tool": "grep",
            "state": {"input": {"pattern": pattern}, "output": output, "status": "completed"}}


def thought(text):
    return {"type": "reasoning", "text": text}


def ledger(parts, built):
    events = [{"ordinal": n, "part_id": f"p{n}", "message_id": "m", "time_created": n,
               "role": part.pop("role", "assistant"), "summary": False, "part": part,
               "message": {}}
              for n, part in enumerate(parts)]
    return _mlr_context.ledger(events, built)


def item_at(led, needle, kind=None):
    """The one attributed item whose detail names this subject."""
    found = [i for i in led["items"] if needle in (i["detail"] or "")
             and (kind is None or i["kind"] == kind)]
    assert len(found) == 1, [i["detail"][:60] for i in led["items"]]
    return found[0]


def component(item, form):
    return next((c for c in item["components"] if c["form"] == form), None)


# The module's public docstring, which is both public surface and literally present in the source
# file. Every case that turns on the distinction uses this exact text.
DOCSTRING = "\n".join(
    (MODULE / "__init__.py").read_text(encoding="utf-8").split('"""')[1].strip().splitlines())

DISASSEMBLY = "\n".join(
    ["Disassembly of <code object put>:"] +
    [f"  {n}          {n * 2} LOAD_GLOBAL              {n} (_checksum)" for n in range(1, 40)])


class SourceRequiresASourceReadingActivity(unittest.TestCase):
    """§1-§8. Content establishes form. Only an activity establishes that source was read."""

    maxDiff = None

    def test_1_a_direct_source_file_read_is_direct_source(self):
        with Arm() as arm:
            src = arm.source()
            item = item_at(ledger([call(), read(arm.vendored(), src), call()], arm.built),
                           "_store.py")
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(item["basis"], _mlr_context.BASIS_ARTIFACT)
            self.assertEqual(item["source_bytes"], len(src.encode("utf-8")))

    def test_2_a_public_docstring_through_introspection_is_not_source(self):
        """The exact shape that invalidated the r4 paired experiment."""
        with Arm(_mlr.CONTRACT) as arm:
            command = 'python3 -c "import objectstore; print(objectstore.__doc__)"'
            led = ledger([call(), bash(command, DOCSTRING), call()], arm.built)
            item = item_at(led, "__doc__")
            self.assertEqual(item["route"], _mlr_context.DOCUMENTATION)
            self.assertEqual(item["source_bytes"], 0)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)
            self.assertEqual(component(item, _lineage.SOURCE_FORM)["origin"],
                             _mlr_context.PUBLIC_CONTRACT)

    def test_3_the_same_docstring_read_from_the_source_file_is_source(self):
        """Identical bytes, different history. The distinction the instrument exists to make.

        This is the case that forbids the obvious wrong repair. A docstring is not "never source":
        read out of the module's own file it is source-form material obtained by reading source,
        and the byte-for-byte identical text printed by `__doc__` in case 2 is not.
        """
        with Arm() as arm:
            item = item_at(ledger([call(), read(arm.vendored("__init__.py"), DOCSTRING), call()],
                                  arm.built), "__init__.py")
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(item["basis"], _mlr_context.BASIS_ARTIFACT)
            self.assertGreater(item["source_bytes"], 0)

    def test_4_disassembly_carrying_source_equivalent_text_is_runtime(self):
        with Arm(_mlr.CONTRACT) as arm:
            body = DISASSEMBLY + "\n" + "\n".join(
                l for l in arm.source().splitlines() if len(l.strip()) >= 24)[:400]
            item = item_at(ledger([call(), bash("python3 -c 'import dis, objectstore; dis.dis(objectstore)'",
                                                body), call()], arm.built), "dis.dis")
            self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertEqual(item["source_bytes"], 0)

    def test_5_a_model_authored_exact_reconstruction_is_model_derived(self):
        with Arm(_mlr.CONTRACT) as arm:
            line = sorted(_lineage.source_fingerprint(MODULE), key=len)[-1]
            led = ledger([call(), thought(f"I believe the implementation reads:\n{line}\n"), call()],
                         arm.built)
            item = [i for i in led["items"] if i["kind"].endswith(":reasoning")][0]
            self.assertEqual(item["origin"], _mlr_context.MODEL_DERIVED)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)
            self.assertGreater(led["source_equivalent_reconstruction"]["unique_bytes"], 0)

    def test_6_a_runtime_structure_dump_is_runtime(self):
        with Arm(_mlr.CONTRACT) as arm:
            dump = "\n".join(f"{{'_ATTEMPTS': 3, '_FANOUT': 2, '_ROOT_ENV': 'X'}} row {n}"
                             for n in range(12))
            item = item_at(ledger([call(), bash('python3 -c "import objectstore; print(vars(objectstore._store))"',
                                                dump), call()], arm.built), "vars(")
            self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertEqual(item["source_bytes"], 0)

    def test_7_a_grep_over_the_real_source_file_is_source(self):
        """Sensitivity: an alternate route to the file is still a route to the file."""
        with Arm() as arm:
            src = arm.source()
            body = "\n".join(f"{arm.vendored()}:{n}: {l}"
                             for n, l in enumerate(src.splitlines(), 1))
            led = ledger([call(), grep(".", body), call()], arm.built)
            item = [i for i in led["items"] if i["kind"] == "tool:grep"][0]
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertGreater(item["source_bytes"], 0)
            self.assertLess(item["source_bytes"], len(body.encode("utf-8")),
                            "an excerpt is charged for its lines, not for its decorations")

    def test_8_a_grep_over_runtime_output_is_not_source(self):
        with Arm(_mlr.CONTRACT) as arm:
            led = ledger([call(),
                          bash("python3 -c 'import dis, objectstore; dis.dis(objectstore)' > /tmp/d.txt", ""),
                          call(), grep("LOAD", "/tmp/d.txt\n" + DISASSEMBLY), call()], arm.built)
            item = [i for i in led["items"] if i["kind"] == "tool:grep"][0]
            self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)


class ArtifactsCarryTheirProducersHistory(unittest.TestCase):
    """§9-§10. What an activity wrote is what that activity was doing."""

    maxDiff = None

    def test_9_a_temporary_artifact_made_from_source_is_source(self):
        with Arm() as arm:
            src = arm.source()
            led = ledger([call(), bash(f"cat {arm.vendored()} > /tmp/copy.txt", ""), call(),
                          read("/tmp/copy.txt", src), call()], arm.built)
            item = item_at(led, "/tmp/copy.txt", "tool:read")
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(item["basis"], _mlr_context.BASIS_ANCESTRY)
            self.assertEqual(item["source_bytes"], len(src.encode("utf-8")))

    def test_10_a_temporary_artifact_made_from_runtime_is_not_source(self):
        with Arm(_mlr.CONTRACT) as arm:
            led = ledger([call(),
                          bash("python3 -c 'import dis, objectstore; dis.dis(objectstore)' > /tmp/d.txt", ""),
                          call(), read("/tmp/d.txt", DISASSEMBLY), call()], arm.built)
            item = item_at(led, "/tmp/d.txt", "tool:read")
            self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)


class ReplayKeepsHistoryWithoutSpreadingIt(unittest.TestCase):
    """§11-§13. The granularity half of the repair."""

    maxDiff = None

    def test_11_a_log_replaying_only_source_is_source(self):
        with Arm() as arm:
            src = arm.source()
            led = ledger([call(), read(arm.vendored(), src), call(),
                          read(arm.log(), "> Read\n" + src), call()], arm.built)
            item = item_at(led, "worker.log")
            self.assertEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)
            self.assertEqual(item["basis"], _mlr_context.BASIS_ANCESTRY)

    def test_12_a_log_replaying_a_small_span_is_charged_that_span(self):
        """The r4 propagation defect, as a known answer.

        Two lines of replayed source inside a large log must not make the log source, must not
        relabel the disassembly beside them, and must not be charged for the container.
        """
        with Arm() as arm:
            src = arm.source()
            span = "\n".join(l for l in src.splitlines() if len(l.strip()) >= 24)[:200]
            mixed = "\n".join(["[INFO] worker started"] * 40 + [span, DISASSEMBLY] +
                              ["[INFO] step done"] * 40)
            led = ledger([call(), read(arm.vendored(), src), call(),
                          read(arm.log(), mixed), call()], arm.built)
            item = item_at(led, "worker.log")
            self.assertEqual(item["origin"], _mlr_context.IMPLEMENTATION_RUNTIME,
                             "the container is what most of it is")
            self.assertLess(item["source_bytes"], len(mixed.encode("utf-8")) // 4,
                            "a replayed span is not the log it sits in")
            self.assertEqual(component(item, _lineage.DISASSEMBLY)["origin"],
                             _mlr_context.IMPLEMENTATION_RUNTIME,
                             "a disassembly beside a replayed span is still a disassembly")

    def test_13_replaying_the_same_material_twice_does_not_inflate_it(self):
        with Arm() as arm:
            src = arm.source()
            led = ledger([call(), read(arm.vendored(), src), call(),
                          read(arm.log(), "> Read\n" + src), call(),
                          read(arm.log(), "> Read\n" + src), call()], arm.built)
            self.assertEqual(led["implementation_source_unique_bytes"],
                             len(src.encode("utf-8")))
            self.assertGreater(led["implementation_source"]["replays"], 0)


class ContentEqualityNeverDecides(unittest.TestCase):
    """§14-§16. The invariant, stated against the cases that most tempt a content rule."""

    maxDiff = None

    def test_14_the_same_literal_in_the_contract_and_in_the_source(self):
        with Arm(_mlr.CONTRACT) as arm:
            contract = (arm.workspace / "docs" / "storage-contract.md")
            led = ledger([call(), read(contract, contract.read_text(encoding="utf-8")), call()],
                         arm.built)
            item = item_at(led, "storage-contract.md")
            self.assertEqual(item["origin"], _mlr_context.PUBLIC_CONTRACT)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)

    def test_15_a_path_without_its_contents_is_metadata_and_never_source(self):
        with Arm() as arm:
            listing = f"{_mlr.VENDORED}/objectstore/_store.py\n{_mlr.VENDORED}/objectstore/_backend.py\n"
            item = item_at(ledger([call(), bash("git ls-files", listing), call()], arm.built),
                           "git ls-files")
            self.assertEqual(item["source_bytes"], 0)
            self.assertEqual(component(item, _lineage.PATH_METADATA)["origin"],
                             _lineage.IMPLEMENTATION_METADATA)

    def test_16_help_on_the_package_is_public_surface(self):
        with Arm(_mlr.CONTRACT) as arm:
            led = ledger([call(),
                          bash('python3 -c "import objectstore; help(objectstore)"',
                               f"Help on package objectstore:\n\nDESCRIPTION\n{DOCSTRING}\n"),
                          call()], arm.built)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)


class TheInvalidatingTrace(unittest.TestCase):
    """§17-§18. The exact trajectory that broke the instrument, and the ones that shaped it."""

    maxDiff = None

    R4_SLOT3 = ('python3 -c "import objectstore; '
                "print([x for x in dir(objectstore) if not x.startswith('__')]); "
                'print(objectstore.__doc__)"')

    def test_17_the_exact_r4_slot_three_command_charges_no_direct_source(self):
        with Arm(_mlr.CONTRACT) as arm:
            output = ("['delete', 'exists', 'get', 'put', 'ObjectStoreError']\n" + DOCSTRING + "\n")
            led = ledger([call(), bash(self.R4_SLOT3, output), call()], arm.built)
            item = item_at(led, "__doc__")
            self.assertEqual(led["implementation_source_unique_bytes"], 0)
            self.assertEqual(item["source_bytes"], 0)
            self.assertNotEqual(item["origin"], _lineage.IMPLEMENTATION_SOURCE)

    def test_17b_and_its_worker_log_replay_does_not_become_source(self):
        """The whole r4 slot-3 chain: introspection, then the log that replayed it."""
        with Arm(_mlr.CONTRACT) as arm:
            output = ("['delete', 'exists', 'get', 'put', 'ObjectStoreError']\n" + DOCSTRING + "\n")
            log = ("\n".join(["[INFO] worker step"] * 60) + "\n" + output + "\n" +
                   DISASSEMBLY + "\n" + "\n".join(["[INFO] worker step"] * 60))
            led = ledger([call(), bash(self.R4_SLOT3, output), call(),
                          read(arm.log(), log), call()], arm.built)
            self.assertEqual(led["implementation_source_unique_bytes"], 0)
            self.assertEqual(led["implementation_source"]["delivered_bytes"], 0)
            replay = item_at(led, "worker.log")
            self.assertEqual(component(replay, _lineage.DISASSEMBLY)["origin"],
                             _mlr_context.IMPLEMENTATION_RUNTIME)

    def test_18_the_defects_that_shaped_r1_r2_and_r3_stay_repaired(self):
        with Arm() as arm:
            src = arm.source()
            # R1: a log echoing a source read is not harness output.
            led = ledger([call(), read(arm.vendored(), src), call(),
                          read(arm.log(), "> Read\n" + src), call()], arm.built)
            self.assertEqual(item_at(led, "worker.log")["origin"], _lineage.IMPLEMENTATION_SOURCE)
        with Arm(_mlr.CONTRACT) as arm:
            # R2: a disassembly behind a numbered reader is still a disassembly.
            numbered = "\n".join(f"{n:>4}: {l}" for n, l in enumerate(DISASSEMBLY.splitlines(), 1))
            item = item_at(ledger([call(), read("/tmp/d.txt", numbered), call()], arm.built),
                           "/tmp/d.txt")
            self.assertEqual(component(item, _lineage.DISASSEMBLY)["origin"],
                             _mlr_context.IMPLEMENTATION_RUNTIME)
            # R3: a request family outranks file names.
            run = item_at(ledger([call(), bash("python3 -m unittest tests.external_test",
                                               "Ran 5 tests\n" * 20 +
                                               '  File "objectstore/_store.py", in put\n'), call()],
                                 arm.built), "unittest")
            self.assertEqual(run["origin"], _mlr_context.BEHAVIOUR)


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
