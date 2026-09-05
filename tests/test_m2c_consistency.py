"""Durable aggregate-consistency acceptance.

M2C-A can say which exact engineering contract existed. It cannot say anyone challenged it
as a whole, and individually reflected artifacts can still contradict each other.

The fact this record carries, worded exactly because the wording decides what Proofbound
claims authority over:

    candidate C received a qualifying consistency-reflection review, and the parent
    accepted it

Not "C is consistent" — that is a semantic verdict, and Python asserting it would recreate
the PASS enum DSD deliberately deleted. The record is provenance of a *challenge*.

It lives in project state because DSD's own acceptance lives in `run_root/state.json`,
which is execution evidence and expendable. Deleting the run tree must cost provenance
verification and nothing else.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))

from _consistency import (  # noqa: E402
    CONSISTENCY_FORMAT,
    V1_CONSISTENCY_PURPOSE,
    V1_CONSISTENCY_ROLES,
    ConsistencyError,
    canonical_record_text,
    check_provenance,
    load_record,
    lookup,
    record_path,
)
from _contract import declared_candidate, declares_candidate  # noqa: E402

C1 = "a" * 64
C2 = "b" * 64
GATE = "phases/spec/tasks/t/attempts/spec-reflector-1/evidence-gate.json"


def record(candidate=C1, gate=GATE, gate_sha=None, fmt=CONSISTENCY_FORMAT):
    return {"format": fmt, "candidate": candidate, "gate": gate,
            "gate_sha256": gate_sha or ("c" * 64)}


def write(stack, doc, *, name=None):
    root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
    d = root / "consistency"
    d.mkdir()
    p = d / (name or f"{doc.get('candidate', 'x')}.json")
    p.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return d, p


class RecordSchemaTest(unittest.TestCase):
    maxDiff = None

    def test_format_and_v1_semantics_are_pinned(self):
        self.assertEqual(CONSISTENCY_FORMAT, "proofbound-consistency-acceptance-v1")
        self.assertEqual(V1_CONSISTENCY_PURPOSE, "consistency-reflection")
        self.assertEqual(sorted(V1_CONSISTENCY_ROLES), ["spec-reflector"])

    def test_a_well_formed_record_loads(self):
        with contextlib.ExitStack() as stack:
            _, p = write(stack, record())
            self.assertEqual(load_record(p)["candidate"], C1)

    def test_unknown_format_fails_closed(self):
        with contextlib.ExitStack() as stack:
            _, p = write(stack, record(fmt="proofbound-consistency-acceptance-v2"))
            with self.assertRaises(ConsistencyError) as e:
                load_record(p)
            self.assertIn("v2", str(e.exception))

    def test_missing_and_unknown_fields_fail_closed(self):
        for drop in ("format", "candidate", "gate", "gate_sha256"):
            with contextlib.ExitStack() as stack:
                doc = record()
                doc.pop(drop)
                _, p = write(stack, doc, name="r.json")
                with self.assertRaises(ConsistencyError, msg=drop):
                    load_record(p)
        with contextlib.ExitStack() as stack:
            doc = record()
            doc["role"] = "spec-reflector"          # rejected by design, not stored
            _, p = write(stack, doc)
            with self.assertRaises(ConsistencyError) as e:
                load_record(p)
            self.assertIn("role", str(e.exception))

    def test_a_malformed_candidate_identity_is_rejected(self):
        for bad in ("not-hex", C1.upper(), C1[:32], f"sha256:{C1}", " " + C1, ""):
            with contextlib.ExitStack() as stack:
                _, p = write(stack, record(candidate=bad), name="r.json")
                with self.assertRaises(ConsistencyError, msg=bad):
                    load_record(p)

    def test_unsafe_gate_paths_are_rejected(self):
        for bad in ("/abs/g.json", "../outside.json", "a/../a.json", "./g.json", ""):
            with contextlib.ExitStack() as stack:
                _, p = write(stack, record(gate=bad))
                with self.assertRaises(ConsistencyError, msg=bad):
                    load_record(p)

    def test_malformed_json_fails_closed(self):
        with contextlib.ExitStack() as stack:
            _, p = write(stack, record())
            p.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ConsistencyError):
                load_record(p)

    def test_the_record_names_its_own_subject_so_a_copy_still_means_something(self):
        """Renaming the file must not change which candidate the bytes concern."""
        with contextlib.ExitStack() as stack:
            d, p = write(stack, record())
            moved = d / "renamed.json"
            p.rename(moved)
            self.assertEqual(load_record(moved)["candidate"], C1)

    def test_a_filename_that_disagrees_with_the_candidate_is_reported(self):
        with contextlib.ExitStack() as stack:
            _, p = write(stack, record(candidate=C1), name=f"{C2}.json")
            got = load_record(p)
            self.assertEqual(got["candidate"], C1)
            self.assertTrue(got["findings"], "a 64-hex filename naming another candidate is a defect")
            self.assertEqual(got["findings"][0]["code"], "filename-candidate-mismatch")

    def test_canonical_text_is_deterministic_regardless_of_input_order(self):
        forward = {"format": CONSISTENCY_FORMAT, "candidate": C1, "gate": GATE, "gate_sha256": "c" * 64}
        reverse = {"gate_sha256": "c" * 64, "gate": GATE, "candidate": C1, "format": CONSISTENCY_FORMAT}
        self.assertEqual(canonical_record_text(forward), canonical_record_text(reverse))
        self.assertTrue(canonical_record_text(forward).endswith("}\n"))


class LookupTest(unittest.TestCase):
    """Callers must not need to know the storage layout, or use Path.exists() as semantics."""

    maxDiff = None

    def test_absent_and_accepted_are_distinguishable(self):
        with contextlib.ExitStack() as stack:
            d, _ = write(stack, record(candidate=C1))
            self.assertEqual(lookup(d, C1)["state"], "accepted")
            self.assertEqual(lookup(d, C2)["state"], "absent")

    def test_lookup_rejects_a_malformed_candidate_argument(self):
        with contextlib.ExitStack() as stack:
            d, _ = write(stack, record())
            with self.assertRaises(ConsistencyError):
                lookup(d, "nonsense")

    def test_two_accepted_candidates_coexist(self):
        """C1 and C2 are different subjects, not revisions. Neither supersedes the other."""
        with contextlib.ExitStack() as stack:
            d, _ = write(stack, record(candidate=C1))
            (d / f"{C2}.json").write_text(
                canonical_record_text(record(candidate=C2)), encoding="utf-8")
            self.assertEqual(lookup(d, C1)["state"], "accepted")
            self.assertEqual(lookup(d, C2)["state"], "accepted")

    def test_record_path_is_derived_from_the_candidate(self):
        with contextlib.ExitStack() as stack:
            d, _ = write(stack, record())
            self.assertEqual(record_path(d, C1).name, f"{C1}.json")


class ProvenanceTest(unittest.TestCase):
    """Retained evidence is a separate dimension from the durable record."""

    maxDiff = None

    def run_tree(self, stack, *, role="spec-reflector", clean=True, tamper=False):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        run = root / "runs" / "r1"
        gate = run / GATE
        gate.parent.mkdir(parents=True)
        payload = {"integrity_ok": clean, "errors": [] if clean else ["WRITE-RESTRICTION"],
                   "ready_for_interpretation": clean, "role": role, "writes_project": False}
        gate.write_text(json.dumps(payload), encoding="utf-8")
        sha = hashlib.sha256(gate.read_bytes()).hexdigest()
        if tamper:
            gate.write_text(json.dumps({**payload, "tampered": True}), encoding="utf-8")
        return run, sha, gate

    def test_intact_evidence_is_verified(self):
        with contextlib.ExitStack() as stack:
            run, sha, _ = self.run_tree(stack)
            got = check_provenance(record(gate_sha=sha), run)
            self.assertEqual(got["provenance"], "verified")

    def test_absent_evidence_is_unavailable_never_verified_and_never_a_failure(self):
        with contextlib.ExitStack() as stack:
            run, sha, gate = self.run_tree(stack)
            gate.unlink()
            self.assertEqual(check_provenance(record(gate_sha=sha), run)["provenance"], "unavailable")
            self.assertEqual(check_provenance(record(gate_sha=sha), None)["provenance"], "unavailable")

    def test_tampered_evidence_is_contradicted(self):
        with contextlib.ExitStack() as stack:
            run, sha, _ = self.run_tree(stack, tamper=True)
            got = check_provenance(record(gate_sha=sha), run)
            self.assertEqual(got["provenance"], "contradicted")

    def test_a_gate_recording_a_non_qualifying_role_is_contradicted(self):
        with contextlib.ExitStack() as stack:
            run, sha, _ = self.run_tree(stack, role="reviewer")
            got = check_provenance(record(gate_sha=sha), run)
            self.assertEqual(got["provenance"], "contradicted")
            self.assertTrue(any("role" in r for r in got["reasons"]))

    def test_an_unclean_gate_is_contradicted(self):
        with contextlib.ExitStack() as stack:
            run, sha, _ = self.run_tree(stack, clean=False)
            self.assertEqual(check_provenance(record(gate_sha=sha), run)["provenance"], "contradicted")

    def test_a_gate_path_escaping_the_run_root_fails_closed(self):
        with contextlib.ExitStack() as stack:
            run, sha, _ = self.run_tree(stack)
            with self.assertRaises(ConsistencyError):
                check_provenance({**record(gate_sha=sha), "gate": "a/../../etc/passwd"}, run)


class HistoricalSemanticsTest(unittest.TestCase):
    """M0's lesson at a new boundary: v1 must not be reinterpreted by a later live registry."""

    maxDiff = None

    def test_provenance_does_not_consult_the_live_purpose_registry(self):
        import _review_purpose
        original = dict(_review_purpose.REVIEW_PURPOSE_ROLES)
        try:
            # A future registry that drops consistency-reflection entirely, or reassigns it.
            _review_purpose.REVIEW_PURPOSE_ROLES.clear()
            _review_purpose.REVIEW_PURPOSE_ROLES["something-else"] = frozenset({"reviewer"})
            with contextlib.ExitStack() as stack:
                p = ProvenanceTest()
                run, sha, _ = p.run_tree(stack)
                got = check_provenance(record(gate_sha=sha), run)
                self.assertEqual(got["provenance"], "verified",
                                 "a v1 record must verify under v1 semantics forever")
        finally:
            _review_purpose.REVIEW_PURPOSE_ROLES.clear()
            _review_purpose.REVIEW_PURPOSE_ROLES.update(original)

    def test_v1_roles_are_a_constant_not_a_registry_read(self):
        import _consistency
        import _review_purpose
        self.assertIsNot(_consistency.V1_CONSISTENCY_ROLES,
                         _review_purpose.REVIEW_PURPOSE_ROLES.get(V1_CONSISTENCY_PURPOSE))
        self.assertIsInstance(V1_CONSISTENCY_ROLES, frozenset)


class ContractCandidateParsingTest(unittest.TestCase):
    """The contract binds the exact subject; reusing the existing bullet parser."""

    maxDiff = None

    def contract(self, section=""):
        return ("# Task CH-001-consistency — Challenge the candidate\n"
                "Contract revision: r0001\n\n"
                "## Objective\nChallenge the aggregate.\n\n"
                f"{section}"
                "## Review purpose\n- consistency-reflection\n\n"
                "## Acceptance criteria\n- AC-001 — the aggregate is coherent.\n")

    def test_absent_section_is_absent_not_empty(self):
        text = self.contract()
        self.assertFalse(declares_candidate(text))
        self.assertIsNone(declared_candidate(text))

    def test_a_declared_candidate_is_read(self):
        text = self.contract(f"## Proofbound candidate\n- {C1}\n\n")
        self.assertTrue(declares_candidate(text))
        self.assertEqual(declared_candidate(text), C1)

    def test_backticked_and_padded_declarations_normalize(self):
        self.assertEqual(declared_candidate(self.contract(f"## Proofbound candidate\n- `{C1}`\n\n")), C1)

    def test_malformed_or_multiple_candidates_fail_closed(self):
        for body in ("", "- NONE\n", f"- {C1}\n- {C2}\n", "- not-a-digest\n", f"- {C1.upper()}\n"):
            with self.assertRaises(ValueError, msg=body):
                declared_candidate(self.contract(f"## Proofbound candidate\n{body}\n"))

    def test_a_candidate_is_never_inferred_from_prose(self):
        text = self.contract().replace("Challenge the aggregate.",
                                       f"Challenge the aggregate {C1} thoroughly.")
        self.assertFalse(declares_candidate(text))
        self.assertIsNone(declared_candidate(text))


if __name__ == "__main__":
    unittest.main()
