"""The freeze: one durable identity for an exact engineering contract.

The reason this milestone exists is a single fact that content hashing cannot express.
Let B's bytes be H_B, accepted against {A: H1}. Later authority requires B against
{A, C}, and B is re-accepted byte-identically. `content_sha256` is H_B in both worlds. A
record binding only content would silently mean the wrong contract.

So a binding is content **plus** the exact accepted dependency identities **plus** the
semantic review purpose — and deliberately not role, gate or attempt, which are execution
mechanics. The pair of properties this file exists to pin:

    same content + deps + purpose, different gate/attempt/role  ->  SAME identity
    same content + purpose,        different dependency set     ->  DIFFERENT identity

A freeze is a durable engineering-contract candidate. It is *not* an authorization to
execute, and nothing here claims the contract is semantically coherent.
"""
from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))

from _freeze import (  # noqa: E402
    FREEZE_FORMAT,
    V1_REVIEW_PURPOSES,
    FreezeError,
    binding_of,
    canonical_freeze_text,
    freeze_identity,
    load_freeze,
)

CH = "specs/CH-001"
A, B, C = f"{CH}/proposal.md", f"{CH}/design.md", f"{CH}/specification.md"
H = {"a": "1" * 64, "b": "2" * 64, "c": "3" * 64, "x": "4" * 64}


def record(content, depends_on=None, purpose="design-reflection",
           role="spec-reflector", gate="phases/spec/g.json", gate_sha=None):
    """An M2A ledger record — deliberately carrying the fields a freeze must ignore."""
    return {"content_sha256": content, "depends_on": depends_on or {},
            "review": {"purpose": purpose, "role": role, "gate": gate,
                       "gate_sha256": gate_sha or ("f" * 64)}}


def freeze(artifacts, fmt=FREEZE_FORMAT):
    return {"format": fmt, "artifacts": artifacts}


def binding(content, depends_on=None, purpose="design-reflection"):
    return {"content_sha256": content, "depends_on": depends_on or {},
            "review_purpose": purpose}


class EngineeringBindingTest(unittest.TestCase):
    """The core semantic proof. Content identity alone must fail these."""

    maxDiff = None

    def test_binding_keeps_content_dependencies_and_purpose(self):
        self.assertEqual(
            binding_of(record(H["b"], {A: H["a"]}, "design-reflection")),
            {"content_sha256": H["b"], "depends_on": {A: H["a"]},
             "review_purpose": "design-reflection"})

    def test_binding_drops_role_gate_and_attempt(self):
        got = binding_of(record(H["b"], {A: H["a"]}, role="reviewer", gate="x/y.json"))
        self.assertEqual(set(got), {"content_sha256", "depends_on", "review_purpose"})
        self.assertNotIn("reviewer", json.dumps(got))
        self.assertNotIn("x/y.json", json.dumps(got))

    # ---- the five states from the design check ----

    def test_same_engineering_meaning_under_a_different_gate_is_identical(self):
        one = record(H["b"], {A: H["a"]}, gate="phases/spec/attempt-1/g.json", gate_sha="a" * 64)
        two = record(H["b"], {A: H["a"]}, gate="phases/spec/attempt-9/g.json", gate_sha="b" * 64)
        self.assertEqual(binding_of(one), binding_of(two))

    def test_same_engineering_meaning_under_a_different_role_is_identical(self):
        """Role is the mechanism that satisfied the purpose, not the purpose (P2)."""
        one = record(H["b"], {A: H["a"]}, role="spec-reflector")
        two = record(H["b"], {A: H["a"]}, role="reviewer")
        self.assertEqual(binding_of(one), binding_of(two))

    def test_a_changed_dependency_set_changes_the_binding(self):
        """The defining test. Content is identical in both worlds."""
        one = record(H["b"], {A: H["a"]})
        two = record(H["b"], {A: H["a"], C: H["c"]})
        self.assertEqual(one["content_sha256"], two["content_sha256"])
        self.assertNotEqual(binding_of(one), binding_of(two))

    def test_a_changed_dependency_identity_changes_the_binding(self):
        self.assertNotEqual(binding_of(record(H["b"], {A: H["a"]})),
                            binding_of(record(H["b"], {A: H["c"]})))

    def test_a_changed_purpose_changes_the_binding(self):
        self.assertNotEqual(binding_of(record(H["b"], {A: H["a"]}, "design-reflection")),
                            binding_of(record(H["b"], {A: H["a"]}, "specification-reflection")))

    def test_changed_content_changes_the_binding(self):
        self.assertNotEqual(binding_of(record(H["b"], {A: H["a"]})),
                            binding_of(record(H["c"], {A: H["a"]})))

    def test_content_identity_alone_cannot_distinguish_these_states(self):
        """States the gap M2C-A closes, so a regression toward content-only is visible."""
        one = record(H["b"], {A: H["a"]})
        two = record(H["b"], {A: H["a"], C: H["c"]})
        three = record(H["b"], {A: H["a"]}, "specification-reflection")
        self.assertEqual(len({r["content_sha256"] for r in (one, two, three)}), 1)
        self.assertEqual(len({json.dumps(binding_of(r), sort_keys=True)
                              for r in (one, two, three)}), 3)


class CanonicalSerializationTest(unittest.TestCase):
    """Ordering that affects identity is protocol, not implementation detail (M0's lesson)."""

    maxDiff = None

    def test_identity_is_sha256_of_the_canonical_bytes(self):
        import hashlib
        doc = freeze({A: binding(H["a"], purpose="proposal-reflection")})
        self.assertEqual(freeze_identity(doc),
                         hashlib.sha256(canonical_freeze_text(doc).encode("utf-8")).hexdigest())

    def test_input_ordering_never_affects_the_bytes(self):
        forward = freeze({A: binding(H["a"], purpose="proposal-reflection"),
                          B: binding(H["b"], {A: H["a"]}),
                          C: binding(H["c"], {A: H["a"], B: H["b"]}, "specification-reflection")})
        reverse = freeze({C: binding(H["c"], {B: H["b"], A: H["a"]}, "specification-reflection"),
                          B: binding(H["b"], {A: H["a"]}),
                          A: binding(H["a"], purpose="proposal-reflection")})
        self.assertEqual(canonical_freeze_text(forward), canonical_freeze_text(reverse))
        self.assertEqual(freeze_identity(forward), freeze_identity(reverse))

    def test_serialization_is_stable_across_repeated_calls(self):
        doc = freeze({B: binding(H["b"], {A: H["a"]})})
        first = canonical_freeze_text(doc)
        for _ in range(5):
            self.assertEqual(canonical_freeze_text(doc), first)

    def test_canonical_text_ends_with_exactly_one_newline(self):
        text = canonical_freeze_text(freeze({A: binding(H["a"], purpose="proposal-reflection")}))
        self.assertTrue(text.endswith("}\n"))
        self.assertFalse(text.endswith("\n\n"))

    def test_each_engineering_field_moves_the_identity(self):
        base = freeze({B: binding(H["b"], {A: H["a"]})})
        for changed in (freeze({B: binding(H["c"], {A: H["a"]})}),
                        freeze({B: binding(H["b"], {A: H["c"]})}),
                        freeze({B: binding(H["b"], {A: H["a"]}, "specification-reflection")}),
                        freeze({B: binding(H["b"], {A: H["a"], C: H["c"]})}),
                        freeze({A: binding(H["a"], purpose="proposal-reflection"),
                                B: binding(H["b"], {A: H["a"]})})):
            self.assertNotEqual(freeze_identity(changed), freeze_identity(base))

    def test_a_round_trip_through_canonical_text_preserves_identity(self):
        doc = freeze({A: binding(H["a"], purpose="proposal-reflection"),
                      B: binding(H["b"], {A: H["a"]})})
        reparsed = json.loads(canonical_freeze_text(doc))
        self.assertEqual(freeze_identity(reparsed), freeze_identity(doc))


class FreezeSchemaTest(unittest.TestCase):
    maxDiff = None

    def load(self, stack, doc, *, raw=None):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        path = root / "f.json"
        path.write_text(raw if raw is not None else json.dumps(doc, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        return load_freeze(path)

    def test_format_tag_is_pinned(self):
        self.assertEqual(FREEZE_FORMAT, "proofbound-freeze-v1")

    def test_a_well_formed_freeze_loads(self):
        with contextlib.ExitStack() as stack:
            got = self.load(stack, freeze({A: binding(H["a"], purpose="proposal-reflection"),
                                           B: binding(H["b"], {A: H["a"]})}))
            self.assertEqual(sorted(got["artifacts"]), sorted([A, B]))

    def test_unknown_format_fails_closed(self):
        with contextlib.ExitStack() as stack:
            with self.assertRaises(FreezeError) as e:
                self.load(stack, freeze({A: binding(H["a"])}, fmt="proofbound-freeze-v2"))
            self.assertIn("proofbound-freeze-v2", str(e.exception))

    def test_unknown_top_level_and_binding_fields_are_rejected(self):
        with contextlib.ExitStack() as stack:
            doc = freeze({A: binding(H["a"], purpose="proposal-reflection")})
            doc["graph_sha256"] = H["a"]
            with self.assertRaises(FreezeError):
                self.load(stack, doc)
        with contextlib.ExitStack() as stack:
            doc = freeze({A: binding(H["a"], purpose="proposal-reflection")})
            doc["artifacts"][A]["role"] = "spec-reflector"
            with self.assertRaises(FreezeError) as e:
                self.load(stack, doc)
            self.assertIn("role", str(e.exception))

    def test_missing_binding_fields_fail_closed(self):
        for drop in ("content_sha256", "depends_on", "review_purpose"):
            with contextlib.ExitStack() as stack:
                doc = freeze({A: binding(H["a"], purpose="proposal-reflection")})
                doc["artifacts"][A].pop(drop)
                with self.assertRaises(FreezeError, msg=drop):
                    self.load(stack, doc)

    def test_malformed_digests_are_rejected(self):
        lettered = "abcdef01" * 8          # digits alone have no case to reject
        for bad in ("not-hex", lettered.upper(), H["a"][:32], f"sha256:{H['a']}",
                    " " + H["a"], H["a"] + "0"):
            with contextlib.ExitStack() as stack:
                with self.assertRaises(FreezeError, msg=bad):
                    self.load(stack, freeze({A: binding(bad, purpose="proposal-reflection")}))

    def test_unsafe_paths_are_rejected_not_normalized(self):
        for bad in (f"./{CH}/a.md", f"{CH}/../CH-001/a.md", "specs\\CH-001\\a.md",
                    "/abs/a.md", "../outside.md"):
            with contextlib.ExitStack() as stack:
                with self.assertRaises(FreezeError, msg=bad):
                    self.load(stack, freeze({bad: binding(H["a"], purpose="proposal-reflection")}))

    def test_case_colliding_members_are_rejected(self):
        with contextlib.ExitStack() as stack:
            with self.assertRaises(FreezeError):
                self.load(stack, freeze({f"{CH}/a.md": binding(H["a"], purpose="proposal-reflection"),
                                         f"{CH}/A.md": binding(H["b"], purpose="proposal-reflection")}))

    def test_malformed_json_fails_closed(self):
        with contextlib.ExitStack() as stack:
            with self.assertRaises(FreezeError):
                self.load(stack, None, raw="{not json")

    def test_self_dependency_and_cycles_fail_closed(self):
        with contextlib.ExitStack() as stack:
            with self.assertRaises(FreezeError):
                self.load(stack, freeze({A: binding(H["a"], {A: H["a"]}, "proposal-reflection")}))
        with contextlib.ExitStack() as stack:
            with self.assertRaises(FreezeError) as e:
                self.load(stack, freeze({A: binding(H["a"], {B: H["b"]}, "proposal-reflection"),
                                         B: binding(H["b"], {A: H["a"]})}))
            self.assertIn("cycle", str(e.exception).lower())

    def test_a_dependency_on_a_member_must_match_that_members_content(self):
        """Catches a hand-edited freeze whose internal identities disagree."""
        with contextlib.ExitStack() as stack:
            with self.assertRaises(FreezeError) as e:
                self.load(stack, freeze({A: binding(H["a"], purpose="proposal-reflection"),
                                         B: binding(H["b"], {A: H["c"]})}))
            self.assertIn("disagree", str(e.exception).lower())

    def test_a_dependency_on_a_non_member_is_legal(self):
        """Model A: members are exactly the graph's declared contract; targets may be external."""
        with contextlib.ExitStack() as stack:
            got = self.load(stack, freeze({B: binding(H["b"], {"docs/architecture/x.md": H["x"]})}))
            self.assertEqual(got["artifacts"][B]["depends_on"], {"docs/architecture/x.md": H["x"]})


class HistoricalPurposeSemanticsTest(unittest.TestCase):
    """M0's lesson: v1 must not be reinterpreted through a later live registry."""

    maxDiff = None

    def test_v1_vocabulary_is_pinned_as_a_constant(self):
        self.assertEqual(sorted(V1_REVIEW_PURPOSES),
                         ["consistency-reflection", "design-reflection", "implementation-review",
                          "proposal-reflection", "specification-reflection"])

    def test_v1_validation_does_not_consult_the_live_registry(self):
        """If the live registry loses a purpose, an existing v1 freeze must still verify."""
        import _freeze
        import _review_purpose
        original = dict(_review_purpose.REVIEW_PURPOSE_ROLES)
        try:
            _review_purpose.REVIEW_PURPOSE_ROLES.clear()
            _review_purpose.REVIEW_PURPOSE_ROLES["something-else"] = frozenset({"reviewer"})
            with contextlib.ExitStack() as stack:
                root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
                p = root / "f.json"
                p.write_text(json.dumps(freeze({A: binding(H["a"], purpose="proposal-reflection")}),
                                        indent=2, sort_keys=True) + "\n", encoding="utf-8")
                self.assertEqual(sorted(_freeze.load_freeze(p)["artifacts"]), [A])
        finally:
            _review_purpose.REVIEW_PURPOSE_ROLES.clear()
            _review_purpose.REVIEW_PURPOSE_ROLES.update(original)

    def test_a_purpose_outside_the_v1_vocabulary_fails_closed(self):
        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            p = root / "f.json"
            p.write_text(json.dumps(freeze({A: binding(H["a"], purpose="architecture-decision-reflection")}),
                                    indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaises(FreezeError) as e:
                load_freeze(p)
            self.assertIn("architecture-decision-reflection", str(e.exception))


if __name__ == "__main__":
    unittest.main()
