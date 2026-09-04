"""The durable change ledger: structural validity derived, never stored.

The ledger persists the artifact/dependency/review-purpose identity that DSD acceptance
already established. It is not a second acceptance engine: it never decides that a review
was good, never recomputes freshness, never reads reviewer prose, and never invents a
purpose. It records, and it can later re-derive whether what was accepted is still what
is on disk.

Two validation levels, kept strictly apart:

  structural    available from a clean Git checkout with no run history at all
  provenance    additionally available while the execution evidence still exists

Absent run evidence yields `unavailable`. It never yields `verified`, and it never
downgrades a structurally valid artifact to invalid.
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

from _artifact_identity import artifact_identity  # noqa: E402
from pb_ledger import LEDGER_FORMAT  # noqa: E402
from _artifact_identity import ARTIFACT_IDENTITY_FORMAT  # noqa: E402

PROPOSAL = "# Proposal\n\nProblem, scope, non-goals.\n"
DESIGN = "# Design\n\nApproach and alternatives.\n"
SPEC = "# Specification\n\nObservable behavior.\n"


def review(purpose="proposal-reflection", role="spec-reflector", gate="phases/spec/g.json", sha=None):
    return {"purpose": purpose, "role": role, "gate": gate,
            "gate_sha256": sha or ("a" * 64)}


class LedgerFixture(unittest.TestCase):
    maxDiff = None

    def build(self, stack, files: dict[str, str], ledger: dict):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        project = root / "project"
        project.mkdir()
        for rel, text in files.items():
            path = project / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        ledger_path = project / "ledger.json"
        ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return project, ledger_path

    def validate(self, project, ledger_path, run_root=None):
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "validate",
               "--ledger", str(ledger_path), "--project-root", str(project)]
        if run_root is not None:
            cmd += ["--run-root", str(run_root)]
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False)
        data = json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {}
        return cp, data

    def states(self, data):
        return {a["path"]: a["state"] for a in data["artifacts"]}

    def reasons(self, data, path):
        return next(a["reasons"] for a in data["artifacts"] if a["path"] == path)


def ledger(artifacts, *, fmt=LEDGER_FORMAT, identity=ARTIFACT_IDENTITY_FORMAT):
    return {"format": fmt, "artifact_identity": identity, "artifacts": artifacts}


def entry(content, depends_on=None, rev=None):
    return {"content_sha256": artifact_identity(content.encode("utf-8")),
            "depends_on": depends_on or {},
            "review": rev or review()}


class LedgerSchemaTest(LedgerFixture):
    """v1 semantics are explicit from day one. M0 already paid for getting this wrong once."""

    def test_a_well_formed_single_artifact_ledger_validates(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": entry(PROPOSAL)}))
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(self.states(data), {"a.md": "valid"})

    def test_unknown_schema_version_fails_closed(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(
                stack, {"a.md": PROPOSAL},
                ledger({"a.md": entry(PROPOSAL)}, fmt="proofbound-change-ledger-v2"))
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("proofbound-change-ledger-v2", cp.stderr)

    def test_unknown_artifact_identity_protocol_fails_closed(self):
        """A future hashing protocol must not be verified under today's assumptions."""
        with contextlib.ExitStack() as stack:
            project, path = self.build(
                stack, {"a.md": PROPOSAL},
                ledger({"a.md": entry(PROPOSAL)}, identity="proofbound-artifact-text-v2"))
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("proofbound-artifact-text-v2", cp.stderr)

    def test_missing_version_fields_fail_closed(self):
        for drop in ("format", "artifact_identity"):
            with contextlib.ExitStack() as stack:
                raw = ledger({"a.md": entry(PROPOSAL)})
                raw.pop(drop)
                project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
                cp, _ = self.validate(project, path)
                self.assertEqual(cp.returncode, 2, drop)

    def test_malformed_json_fails_closed(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({}))
            path.write_text("{not json", encoding="utf-8")
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)

    def test_missing_required_artifact_keys_fail_closed(self):
        for drop in ("content_sha256", "depends_on", "review"):
            with contextlib.ExitStack() as stack:
                bad = entry(PROPOSAL)
                bad.pop(drop)
                project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": bad}))
                cp, _ = self.validate(project, path)
                self.assertEqual(cp.returncode, 2, drop)
                self.assertIn(drop, cp.stderr)

    def test_missing_review_keys_fail_closed(self):
        for drop in ("purpose", "role", "gate", "gate_sha256"):
            with contextlib.ExitStack() as stack:
                bad = entry(PROPOSAL)
                bad["review"].pop(drop)
                project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": bad}))
                cp, _ = self.validate(project, path)
                self.assertEqual(cp.returncode, 2, drop)

    def test_non_hex_digest_fails_closed(self):
        with contextlib.ExitStack() as stack:
            bad = entry(PROPOSAL)
            bad["content_sha256"] = "not-a-digest"
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": bad}))
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)

    def test_unknown_review_purpose_in_a_stored_record_fails_closed(self):
        with contextlib.ExitStack() as stack:
            bad = entry(PROPOSAL, rev=review(purpose="architecture-review"))
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": bad}))
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("architecture-review", cp.stderr)

    def test_recorded_role_not_authorized_for_recorded_purpose_fails_closed(self):
        """Checkable from a clean checkout: the record contradicts the purpose table."""
        with contextlib.ExitStack() as stack:
            bad = entry(PROPOSAL, rev=review(purpose="proposal-reflection", role="reviewer"))
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": bad}))
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("proposal-reflection", cp.stderr)

    def test_dangling_dependency_reference_fails_closed(self):
        with contextlib.ExitStack() as stack:
            raw = ledger({"b.md": entry(DESIGN, {"a.md": artifact_identity(PROPOSAL.encode())})})
            project, path = self.build(stack, {"b.md": DESIGN}, raw)
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("a.md", cp.stderr)

    def test_unsafe_artifact_paths_fail_closed(self):
        for unsafe in ("../escape.md", "/etc/passwd", "a/../../b.md"):
            with contextlib.ExitStack() as stack:
                project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({unsafe: entry(PROPOSAL)}))
                cp, _ = self.validate(project, path)
                self.assertEqual(cp.returncode, 2, unsafe)


class LedgerDerivedStateTest(LedgerFixture):
    """States are computed from content and closure. No state enum is ever persisted."""

    def test_no_state_field_is_stored_in_the_ledger(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": entry(PROPOSAL)}))
            stored = json.loads(path.read_text())
            self.assertNotIn("state", json.dumps(stored))
            self.assertNotIn("valid", json.dumps(stored))

    def test_own_content_drift_makes_an_artifact_invalid(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": entry(PROPOSAL)}))
            (project / "a.md").write_text(PROPOSAL + "edited\n", encoding="utf-8")
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.states(data), {"a.md": "invalid"})
            self.assertTrue(any("content" in r for r in self.reasons(data, "a.md")))

    def test_a_missing_artifact_file_is_invalid_with_a_reason(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": entry(PROPOSAL)}))
            (project / "a.md").unlink()
            cp, data = self.validate(project, path)
            self.assertEqual(self.states(data), {"a.md": "invalid"})
            self.assertTrue(any("missing" in r.lower() for r in self.reasons(data, "a.md")))

    def test_a_crlf_checkout_does_not_invalidate_anything(self):
        """The whole reason identity is canonical rather than raw bytes."""
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": entry(PROPOSAL)}))
            (project / "a.md").write_bytes(PROPOSAL.replace("\n", "\r\n").encode("utf-8"))
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 0)
            self.assertEqual(self.states(data), {"a.md": "valid"})

    def test_dependency_content_drift_makes_the_dependent_need_revalidation(self):
        with contextlib.ExitStack() as stack:
            a_id = artifact_identity(PROPOSAL.encode())
            raw = ledger({"a.md": entry(PROPOSAL),
                          "b.md": entry(DESIGN, {"a.md": a_id}, review("design-reflection"))})
            project, path = self.build(stack, {"a.md": PROPOSAL, "b.md": DESIGN}, raw)
            (project / "a.md").write_text(PROPOSAL + "revised\n", encoding="utf-8")
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.states(data), {"a.md": "invalid", "b.md": "needs-revalidation"})
            self.assertTrue(any("a.md" in r for r in self.reasons(data, "b.md")))

    def test_dependency_reaccepted_with_new_content_moves_the_ground_under_the_dependent(self):
        """A's ledger record advanced; B was reviewed against the older accepted A."""
        with contextlib.ExitStack() as stack:
            old_a = artifact_identity(PROPOSAL.encode())
            revised = PROPOSAL + "revised\n"
            raw = ledger({"a.md": entry(revised),
                          "b.md": entry(DESIGN, {"a.md": old_a}, review("design-reflection"))})
            project, path = self.build(stack, {"a.md": revised, "b.md": DESIGN}, raw)
            cp, data = self.validate(project, path)
            self.assertEqual(self.states(data), {"a.md": "valid", "b.md": "needs-revalidation"})
            self.assertTrue(any("changed from" in r for r in self.reasons(data, "b.md")))

    def test_byte_identical_reacceptance_does_not_disturb_the_dependent(self):
        """Identity is content, not attempt. Re-authoring identical text changes nothing."""
        with contextlib.ExitStack() as stack:
            a_id = artifact_identity(PROPOSAL.encode())
            raw = ledger({"a.md": entry(PROPOSAL),
                          "b.md": entry(DESIGN, {"a.md": a_id}, review("design-reflection"))})
            project, path = self.build(stack, {"a.md": PROPOSAL, "b.md": DESIGN}, raw)
            (project / "a.md").write_text(PROPOSAL, encoding="utf-8")  # rewritten, same content
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 0)
            self.assertEqual(self.states(data), {"a.md": "valid", "b.md": "valid"})

    def test_own_content_mismatch_outranks_dependency_staleness(self):
        """Precedence: an artifact that is not itself the accepted artifact is invalid."""
        with contextlib.ExitStack() as stack:
            a_id = artifact_identity(PROPOSAL.encode())
            raw = ledger({"a.md": entry(PROPOSAL),
                          "b.md": entry(DESIGN, {"a.md": a_id}, review("design-reflection"))})
            project, path = self.build(stack, {"a.md": PROPOSAL, "b.md": DESIGN}, raw)
            (project / "a.md").write_text("moved\n", encoding="utf-8")
            (project / "b.md").write_text("also moved\n", encoding="utf-8")
            cp, data = self.validate(project, path)
            self.assertEqual(self.states(data), {"a.md": "invalid", "b.md": "invalid"})
            self.assertTrue(any("content" in r for r in self.reasons(data, "b.md")))

    def test_states_carry_reasons_not_just_labels(self):
        with contextlib.ExitStack() as stack:
            a_id = artifact_identity(PROPOSAL.encode())
            raw = ledger({"a.md": entry(PROPOSAL),
                          "b.md": entry(DESIGN, {"a.md": a_id}, review("design-reflection"))})
            project, path = self.build(stack, {"a.md": PROPOSAL, "b.md": DESIGN}, raw)
            (project / "a.md").write_text("moved\n", encoding="utf-8")
            _, data = self.validate(project, path)
            for artifact in data["artifacts"]:
                if artifact["state"] != "valid":
                    self.assertTrue(artifact["reasons"], artifact)


class LedgerTransitiveClosureTest(LedgerFixture):
    """The correction that a direct-edge validator gets silently wrong.

    A accepted H1; B depends on A@H1; C depends on B@HB. A drifts. Every *direct* edge in
    the ledger still matches its recorded target, so a naive validator calls C valid. It
    is not: the ground under B moved, and C was reviewed against B.
    """

    def three_node(self):
        a_id = artifact_identity(PROPOSAL.encode())
        b_id = artifact_identity(DESIGN.encode())
        return ledger({
            "a.md": entry(PROPOSAL),
            "b.md": entry(DESIGN, {"a.md": a_id}, review("design-reflection")),
            "c.md": entry(SPEC, {"b.md": b_id}, review("specification-reflection")),
        })

    def test_intact_chain_is_valid(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(
                stack, {"a.md": PROPOSAL, "b.md": DESIGN, "c.md": SPEC}, self.three_node())
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(self.states(data), {"a.md": "valid", "b.md": "valid", "c.md": "valid"})

    def test_invalidity_propagates_through_an_intact_intermediate_edge(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(
                stack, {"a.md": PROPOSAL, "b.md": DESIGN, "c.md": SPEC}, self.three_node())
            (project / "a.md").write_text(PROPOSAL + "revised\n", encoding="utf-8")
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.states(data),
                             {"a.md": "invalid", "b.md": "needs-revalidation",
                              "c.md": "needs-revalidation"})
            # C's own direct edge is untouched; only the closure explains its state.
            self.assertEqual(json.loads(path.read_text())["artifacts"]["c.md"]["depends_on"],
                             {"b.md": artifact_identity(DESIGN.encode())})
            self.assertTrue(any("b.md" in r for r in self.reasons(data, "c.md")))

    def test_closure_handles_a_diamond_without_double_counting(self):
        a_id = artifact_identity(PROPOSAL.encode())
        b_id = artifact_identity(DESIGN.encode())
        c_id = artifact_identity(SPEC.encode())
        raw = ledger({
            "a.md": entry(PROPOSAL),
            "b.md": entry(DESIGN, {"a.md": a_id}, review("design-reflection")),
            "c.md": entry(SPEC, {"a.md": a_id}, review("design-reflection")),
            "d.md": entry("# D\n", {"b.md": b_id, "c.md": c_id}, review("consistency-reflection")),
        })
        with contextlib.ExitStack() as stack:
            project, path = self.build(
                stack, {"a.md": PROPOSAL, "b.md": DESIGN, "c.md": SPEC, "d.md": "# D\n"}, raw)
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            (project / "a.md").write_text("moved\n", encoding="utf-8")
            cp, data = self.validate(project, path)
            self.assertEqual(self.states(data), {
                "a.md": "invalid", "b.md": "needs-revalidation",
                "c.md": "needs-revalidation", "d.md": "needs-revalidation"})

    def test_a_dependency_cycle_fails_safely_rather_than_recursing(self):
        a_id = artifact_identity(PROPOSAL.encode())
        b_id = artifact_identity(DESIGN.encode())
        raw = ledger({
            "a.md": entry(PROPOSAL, {"b.md": b_id}),
            "b.md": entry(DESIGN, {"a.md": a_id}, review("design-reflection")),
        })
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL, "b.md": DESIGN}, raw)
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("cycle", cp.stderr.lower())

    def test_a_self_dependency_fails_safely(self):
        raw = ledger({"a.md": entry(PROPOSAL, {"a.md": artifact_identity(PROPOSAL.encode())})})
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)
            self.assertIn("cycle", cp.stderr.lower())

    def test_a_deep_chain_does_not_exhaust_the_interpreter_stack(self):
        # Well past the default recursion limit of 1000: this guards the topological
        # pre-pass, without which closure would be genuinely recursive and would crash.
        depth = 5000
        artifacts, files, prev, prev_id = {}, {}, None, None
        for i in range(depth):
            name, text = f"n{i:04d}.md", f"# Node {i}\n"
            files[name] = text
            deps = {prev: prev_id} if prev else {}
            artifacts[name] = entry(text, deps, review("design-reflection"))
            prev, prev_id = name, artifact_identity(text.encode())
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, files, ledger(artifacts))
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 0, cp.stderr[-2000:])
            (project / "n0000.md").write_text("moved\n", encoding="utf-8")
            cp, data = self.validate(project, path)
            states = self.states(data)
            self.assertEqual(states["n0000.md"], "invalid")
            self.assertEqual(states[f"n{depth - 1:04d}.md"], "needs-revalidation")


class LedgerProvenanceBoundaryTest(LedgerFixture):
    """Structural validity and provenance availability are different questions."""

    def run_tree(self, stack, *, role="spec-reflector"):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        run = root / "runs" / "r1"
        event = run / "phases" / "spec" / "tasks" / "t" / "attempts" / "a1"
        event.mkdir(parents=True)
        gate = event / "evidence-gate.json"
        gate.write_text(json.dumps({
            "integrity_ok": True, "errors": [], "ready_for_interpretation": True,
            "role": role, "writes_project": False,
        }), encoding="utf-8")
        rel = gate.relative_to(run).as_posix()
        return run, rel, hashlib.sha256(gate.read_bytes()).hexdigest(), gate

    def test_provenance_is_unavailable_when_no_run_tree_is_supplied(self):
        with contextlib.ExitStack() as stack:
            project, path = self.build(stack, {"a.md": PROPOSAL}, ledger({"a.md": entry(PROPOSAL)}))
            cp, data = self.validate(project, path)
            self.assertEqual(cp.returncode, 0)
            self.assertEqual(data["provenance"], "unavailable")
            self.assertEqual(data["artifacts"][0]["review"]["provenance"], "unavailable")

    def test_provenance_is_verified_when_the_recorded_gate_is_intact(self):
        with contextlib.ExitStack() as stack:
            run, rel, sha, _ = self.run_tree(stack)
            raw = ledger({"a.md": entry(PROPOSAL, rev=review(gate=rel, sha=sha))})
            project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
            cp, data = self.validate(project, path, run_root=run)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["provenance"], "verified")

    def test_structural_state_is_identical_with_and_without_the_run_tree(self):
        """The invariant that justifies the ledger existing at all."""
        with contextlib.ExitStack() as stack:
            run, rel, sha, _ = self.run_tree(stack)
            a_id = artifact_identity(PROPOSAL.encode())
            raw = ledger({
                "a.md": entry(PROPOSAL, rev=review(gate=rel, sha=sha)),
                "b.md": entry(DESIGN, {"a.md": a_id}, review("design-reflection", gate=rel, sha=sha)),
            })
            project, path = self.build(stack, {"a.md": PROPOSAL, "b.md": DESIGN}, raw)
            (project / "a.md").write_text("moved\n", encoding="utf-8")

            _, with_run = self.validate(project, path, run_root=run)
            _, without = self.validate(project, path)
            self.assertEqual(self.states(with_run), self.states(without))
            self.assertEqual(self.states(without), {"a.md": "invalid", "b.md": "needs-revalidation"})
            self.assertEqual(with_run["provenance"], "verified")
            self.assertEqual(without["provenance"], "unavailable")

    def test_a_deleted_gate_reports_unavailable_never_verified_and_never_invalid(self):
        with contextlib.ExitStack() as stack:
            run, rel, sha, gate = self.run_tree(stack)
            raw = ledger({"a.md": entry(PROPOSAL, rev=review(gate=rel, sha=sha))})
            project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
            gate.unlink()
            cp, data = self.validate(project, path, run_root=run)
            self.assertEqual(cp.returncode, 0, "absent evidence is not a structural failure")
            self.assertEqual(self.states(data), {"a.md": "valid"})
            self.assertEqual(data["provenance"], "unavailable")
            self.assertEqual(data["artifacts"][0]["review"]["provenance"], "unavailable")

    def test_a_tampered_gate_is_a_provenance_contradiction(self):
        """Present-but-wrong is different from absent, and must not read as verified."""
        with contextlib.ExitStack() as stack:
            run, rel, sha, gate = self.run_tree(stack)
            raw = ledger({"a.md": entry(PROPOSAL, rev=review(gate=rel, sha=sha))})
            project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
            gate.write_text(json.dumps({"integrity_ok": True, "errors": [],
                                        "ready_for_interpretation": True, "role": "spec-reflector",
                                        "tampered": True}), encoding="utf-8")
            cp, data = self.validate(project, path, run_root=run)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(data["provenance"], "contradicted")
            self.assertEqual(self.states(data), {"a.md": "valid"}, "structure is still intact")

    def test_a_gate_recording_a_different_role_is_a_contradiction(self):
        with contextlib.ExitStack() as stack:
            run, rel, sha, _ = self.run_tree(stack, role="reviewer")
            raw = ledger({"a.md": entry(PROPOSAL, rev=review(gate=rel, sha=sha))})
            project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
            cp, data = self.validate(project, path, run_root=run)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(data["provenance"], "contradicted")
            self.assertTrue(any("role" in r for r in data["artifacts"][0]["review"]["reasons"]))

    def test_an_unclean_gate_is_a_contradiction(self):
        with contextlib.ExitStack() as stack:
            run, rel, _, gate = self.run_tree(stack)
            gate.write_text(json.dumps({
                "integrity_ok": False, "errors": ["WRITE-RESTRICTION"],
                "ready_for_interpretation": False, "role": "spec-reflector"}), encoding="utf-8")
            sha = hashlib.sha256(gate.read_bytes()).hexdigest()
            raw = ledger({"a.md": entry(PROPOSAL, rev=review(gate=rel, sha=sha))})
            project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
            cp, data = self.validate(project, path, run_root=run)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(data["provenance"], "contradicted")

    def test_a_gate_path_escaping_the_run_root_fails_closed(self):
        with contextlib.ExitStack() as stack:
            run, _, sha, _ = self.run_tree(stack)
            raw = ledger({"a.md": entry(PROPOSAL, rev=review(gate="../../etc/passwd", sha=sha))})
            project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
            cp, _ = self.validate(project, path, run_root=run)
            self.assertEqual(cp.returncode, 2)

    def test_an_absolute_gate_path_is_rejected_by_the_schema(self):
        """A committed record must never embed a machine-local absolute path."""
        with contextlib.ExitStack() as stack:
            raw = ledger({"a.md": entry(PROPOSAL, rev=review(gate="/Users/someone/run/g.json"))})
            project, path = self.build(stack, {"a.md": PROPOSAL}, raw)
            cp, _ = self.validate(project, path)
            self.assertEqual(cp.returncode, 2)


if __name__ == "__main__":
    unittest.main()
