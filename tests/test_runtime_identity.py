"""Two arms must be able to prove they executed the same implementation.

A twelve-slot paired run recorded two different runtimes. Eleven slots produced one digest of the
compiled package and the first produced another, and the difference was twenty-five bytes: `marshal`
had interned a single name in one materialisation and not in the other, and every reference index
behind it shifted. The opcodes, names, constants and nested code objects were identical. The
experiment had detected serialisation noise and reported implementation drift.

Bytes are the wrong identity for this claim. What the two arms have to share is what the interpreter
will execute, so the identity is taken over the structure of the compiled objects — and, because
bytecode is version-specific, over the interpreter that produced them.

Nothing here invokes a model.
"""
from __future__ import annotations

import importlib.util
import marshal
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _mlr  # noqa: E402


class Built:
    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.source = self.tmp / "src" / "pkg"
        self.source.mkdir(parents=True)
        (self.source / "__init__.py").write_text(
            "from .inner import work\n__all__ = ['work']\n", encoding="utf-8")
        (self.source / "inner.py").write_text(
            "LIMIT = 3\n\n\n"
            "def work(value):\n"
            "    def double(v):\n"
            "        return v * 2\n"
            "    return [double(v) for v in range(value + LIMIT)]\n", encoding="utf-8")
        self.runtime = self.tmp / "rt"
        _mlr.compile_runtime(self.source, self.runtime)
        return self

    def compiled(self, name):
        """`compile_runtime` names the package it builds; the test asks where it landed."""
        found = sorted(self.runtime.rglob(name))
        assert found, name
        return found[0]

    def recompile(self):
        shutil.rmtree(self.runtime, ignore_errors=True)
        _mlr.compile_runtime(self.source, self.runtime)

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)


class RuntimeStructureTest(unittest.TestCase):
    maxDiff = None

    def test_the_same_source_compiles_to_the_same_structure(self):
        with Built() as b:
            first = _mlr.runtime_structure(b.runtime)
            b.recompile()
            self.assertEqual(_mlr.runtime_structure(b.runtime), first)

    def test_serialisation_noise_does_not_change_the_structure(self):
        """The defect. Two marshal encodings of one code object are one implementation."""
        with Built() as b:
            before = _mlr.runtime_structure(b.runtime)
            pyc = b.compiled("inner.pyc")
            raw = pyc.read_bytes()
            code = marshal.loads(raw[16:])
            # Version 1 does not intern strings; version 4 does. Same object, different bytes —
            # which is the shape of the difference the paired run recorded as two runtimes.
            low, high = marshal.dumps(code, 1), marshal.dumps(code, 4)
            self.assertNotEqual(low, high)
            pyc.write_bytes(raw[:16] + low)
            self.assertEqual(_mlr.runtime_structure(b.runtime), before)
            pyc.write_bytes(raw[:16] + high)
            self.assertEqual(_mlr.runtime_structure(b.runtime), before)

    def test_byte_identity_is_the_one_that_moves(self):
        """Stated as a contrast, so the reason for a second identity stays visible."""
        with Built() as b:
            before = _mlr.digest_tree(b.runtime)
            pyc = b.compiled("inner.pyc")
            raw = pyc.read_bytes()
            pyc.write_bytes(raw[:16] + marshal.dumps(marshal.loads(raw[16:]), 1))
            self.assertNotEqual(_mlr.digest_tree(b.runtime), before)

    def test_a_changed_constant_changes_the_structure(self):
        with Built() as b:
            before = _mlr.runtime_structure(b.runtime)
            (b.source / "inner.py").write_text(
                (b.source / "inner.py").read_text(encoding="utf-8").replace("LIMIT = 3",
                                                                            "LIMIT = 4"),
                encoding="utf-8")
            b.recompile()
            self.assertNotEqual(_mlr.runtime_structure(b.runtime), before)

    def test_a_changed_nested_function_changes_the_structure(self):
        """Nested code objects are part of the implementation and part of its identity."""
        with Built() as b:
            before = _mlr.runtime_structure(b.runtime)
            (b.source / "inner.py").write_text(
                (b.source / "inner.py").read_text(encoding="utf-8").replace("return v * 2",
                                                                            "return v * 3"),
                encoding="utf-8")
            b.recompile()
            self.assertNotEqual(_mlr.runtime_structure(b.runtime), before)

    def test_a_renamed_binding_changes_the_structure(self):
        with Built() as b:
            before = _mlr.runtime_structure(b.runtime)
            (b.source / "inner.py").write_text(
                (b.source / "inner.py").read_text(encoding="utf-8").replace("double", "twice"),
                encoding="utf-8")
            b.recompile()
            self.assertNotEqual(_mlr.runtime_structure(b.runtime), before)

    def test_a_removed_module_changes_the_structure(self):
        with Built() as b:
            before = _mlr.runtime_structure(b.runtime)
            b.compiled("inner.pyc").unlink()
            self.assertNotEqual(_mlr.runtime_structure(b.runtime), before)

    def test_the_interpreter_is_part_of_the_identity(self):
        """Bytecode is version-specific, so a digest from one Python is not another's to compare."""
        with Built() as b:
            self.assertIn(importlib.util.MAGIC_NUMBER.hex(),
                          _mlr.interpreter_identity()["bytecode_magic"])
            self.assertTrue(_mlr.runtime_structure(b.runtime))


class MaterialisedArmsTest(unittest.TestCase):
    """What the fixture records, and what the two arms can therefore claim about each other."""

    maxDiff = None

    def test_both_arms_share_one_structural_runtime_identity(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            full = _mlr.materialise(_mlr.FULL, tmp / "full")
            contract = _mlr.materialise(_mlr.CONTRACT, tmp / "contract")
            self.assertEqual(full["runtime_structure"], contract["runtime_structure"])
            self.assertEqual(full["source_digest"], contract["source_digest"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_interpreter_is_recorded_beside_the_identity(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            built = _mlr.materialise(_mlr.CONTRACT, tmp / "arm")
            for field in ("version", "implementation", "cache_tag", "bytecode_magic"):
                self.assertIn(field, built["interpreter"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_structural_identity_is_not_source_identity(self):
        """§47. They are different facts and are recorded separately."""
        tmp = Path(tempfile.mkdtemp())
        try:
            built = _mlr.materialise(_mlr.FULL, tmp / "arm")
            self.assertNotEqual(built["runtime_structure"], built["source_digest"])
            self.assertNotEqual(built["runtime_structure"], built["runtime_digest"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class FrozenIdentityTest(unittest.TestCase):
    """What a series binds, and what it therefore refuses to resume across. §66, §84."""

    maxDiff = None

    def config(self, **kw):
        import pb_mlr
        base = dict(model="deepseek/deepseek-v4-flash", samples=2, arms=["full", "contract"],
                    variant="high")
        base.update(kw)
        return pb_mlr.configuration(**base)

    def test_the_oracle_in_force_is_the_one_bound(self):
        """It bound the first oracle while the second was the one being run."""
        import _mlr_run
        config = self.config()
        self.assertEqual(config["oracle"], _mlr_run.ORACLE)
        self.assertEqual(config["gate_sha256"],
                         _mlr.digest_file(_mlr.FIXTURE / "hidden" / _mlr_run.ORACLE))

    def test_the_interpreter_is_part_of_the_frozen_configuration(self):
        self.assertEqual(self.config()["interpreter"], _mlr.interpreter_identity())

    def test_a_revision_makes_a_different_experiment(self):
        """A repaired instrument may not inherit the name of the series it invalidated."""
        plain = self.config()["experiment"]
        revised = self.config(revision="r2")["experiment"]
        self.assertNotEqual(plain, revised)
        self.assertTrue(revised.startswith(plain))

    def test_changing_the_attribution_semantics_changes_the_identity(self):
        """§84. A later classifier must not be able to silently reinterpret an earlier record."""
        import _repeat
        config = self.config()
        moved = dict(config, telemetry_version="something-else")
        self.assertNotEqual(_repeat.frozen_identity(config), _repeat.frozen_identity(moved))

    def test_a_paired_series_does_not_describe_itself_as_a_headroom_pilot(self):
        self.assertIn("paired", self.config()["purpose"])
        self.assertIn("headroom", self.config(arms=["full"])["purpose"])


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
