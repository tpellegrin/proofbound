"""Execution authority: which engineering candidate governs an implementation task.

M2C-C is deliberately thin. It composes three shipped facts and adds no state:

    the current graph and ledger derive exactly C
    C has a durable aggregate consistency acceptance
    that acceptance's provenance is not contradicted

and then lets the inherited immutable-contract machinery do the binding, because a
contract naming C already has a different hash from one naming C2.

The policy that needs defending is that `unavailable` provenance still authorizes.
Execution evidence is expendable by design; if losing it blocked new work, deleting an old
run tree would silently convert accepted engineering authority into unauthorized
authority, making evidence *availability* into authority.
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
from _change_graph import GRAPH_FORMAT, canonical_graph_text  # noqa: E402
from _consistency import CONSISTENCY_FORMAT, canonical_record_text, record_path  # noqa: E402
from _execution import authorize, bound_candidates  # noqa: E402
from _freeze import canonical_freeze_text, current_candidate, freeze_identity  # noqa: E402

CH = "specs/CH-001"
A, B = f"{CH}/proposal.md", f"{CH}/design.md"


def ledger_record(content, deps=None, purpose="proposal-reflection"):
    return {"content_sha256": artifact_identity(content.encode()), "depends_on": deps or {},
            "review": {"purpose": purpose, "role": "spec-reflector",
                       "gate": "phases/spec/g.json", "gate_sha256": "f" * 64}}


class Fixture(unittest.TestCase):
    """A satisfied two-artifact change, with the pieces M2C-C composes."""

    maxDiff = None

    def build(self, stack, *, a_body="# A\n", accept_consistency=True,
              gate_role="spec-reflector", gate_present=True, tamper=False):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        project = root / "project"
        (project / CH).mkdir(parents=True)
        b_body = "# B\n"
        (project / A).write_text(a_body); (project / B).write_text(b_body)

        graph = project / CH / "graph.json"
        graph.write_text(canonical_graph_text({"format": GRAPH_FORMAT,
                                               "artifacts": {A: [], B: [A]}}))
        ledger = project / CH / "ledger.json"
        ledger.write_text(json.dumps({
            "format": "proofbound-change-ledger-v1",
            "artifact_identity": "proofbound-artifact-text-v1",
            "artifacts": {A: ledger_record(a_body),
                          B: ledger_record(b_body, {A: artifact_identity(a_body.encode())},
                                           "design-reflection")}}, indent=2, sort_keys=True) + "\n")

        _g, _l, candidate = current_candidate(graph, ledger, project)
        C = freeze_identity(candidate)
        freezes = project / CH / "freezes"; freezes.mkdir()
        (freezes / f"{C}.json").write_text(canonical_freeze_text(candidate))

        run = root / "runs" / "r1"
        gate_rel = "phases/spec/tasks/t/attempts/spec-reflector-1/evidence-gate.json"
        gate = run / gate_rel
        gate.parent.mkdir(parents=True)
        payload = {"integrity_ok": True, "errors": [], "ready_for_interpretation": True,
                   "role": gate_role, "writes_project": False}
        gate.write_text(json.dumps(payload))
        gate_sha = hashlib.sha256(gate.read_bytes()).hexdigest()
        if tamper:
            gate.write_text(json.dumps({**payload, "tampered": True}))
        if not gate_present:
            gate.unlink()

        consistency = project / CH / "consistency"
        if accept_consistency:
            consistency.mkdir()
            record_path(consistency, C).write_text(canonical_record_text(
                {"format": CONSISTENCY_FORMAT, "candidate": C,
                 "gate": gate_rel, "gate_sha256": gate_sha}))
        else:
            consistency.mkdir()

        return {"project": project, "graph": graph, "ledger": ledger, "run": run,
                "consistency": consistency, "C": C, "root": root}

    _UNSET = object()

    def auth(self, ctx, candidate=_UNSET, *, run_root=True):
        # Sentinel, not `or`: an empty-string candidate must reach production, not be
        # silently replaced by the valid one.
        candidate = ctx["C"] if candidate is self._UNSET else candidate
        return authorize(candidate=candidate, graph_path=ctx["graph"],
                         ledger_path=ctx["ledger"], project_root=ctx["project"],
                         consistency_dir=ctx["consistency"],
                         run_root=ctx["run"] if run_root else None)

    def codes(self, result):
        return sorted(f["code"] for f in result["findings"])


class AuthorizationTest(Fixture):
    def test_current_and_verified_authorizes(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            got = self.auth(ctx)
            self.assertTrue(got["authorized"], got["findings"])
            self.assertEqual(got["provenance"], "verified")

    def test_unavailable_provenance_still_authorizes(self):
        """The load-bearing policy: expendable evidence must not become authority."""
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack, gate_present=False)
            got = self.auth(ctx)
            self.assertTrue(got["authorized"], got["findings"])
            self.assertEqual(got["provenance"], "unavailable")

    def test_no_run_root_at_all_still_authorizes(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            got = self.auth(ctx, run_root=False)
            self.assertTrue(got["authorized"], got["findings"])
            self.assertEqual(got["provenance"], "unavailable")

    def test_contradicted_provenance_refuses(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack, tamper=True)
            got = self.auth(ctx)
            self.assertFalse(got["authorized"])
            self.assertEqual(got["provenance"], "contradicted")
            self.assertIn("consistency-provenance-contradicted", self.codes(got))

    def test_a_gate_role_that_never_qualified_refuses(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack, gate_role="reviewer")
            got = self.auth(ctx)
            self.assertFalse(got["authorized"])
            self.assertEqual(got["provenance"], "contradicted")

    def test_missing_consistency_acceptance_refuses(self):
        """A freeze alone is not authority: that gap is exactly why M2C-B exists."""
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack, accept_consistency=False)
            got = self.auth(ctx)
            self.assertFalse(got["authorized"])
            self.assertEqual(self.codes(got), ["no-consistency-acceptance"])

    def test_a_historical_candidate_does_not_authorize_new_work(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            C1 = ctx["C"]
            (ctx["project"] / A).write_text("# A\nrevised\n")     # engineering intent moves
            got = self.auth(ctx, C1)
            self.assertFalse(got["authorized"])
            self.assertIn("candidate-not-derivable", self.codes(got))

    def test_declaring_a_candidate_that_is_not_the_current_one_refuses(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            got = self.auth(ctx, "b" * 64)
            self.assertFalse(got["authorized"])
            # Both are true and both are useful: it is neither the current candidate nor
            # one that was ever challenged.
            self.assertEqual(self.codes(got),
                             ["candidate-not-current", "no-consistency-acceptance"])
            self.assertEqual(got["current"], ctx["C"])

    def test_a_non_derivable_candidate_refuses(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            (ctx["project"] / B).unlink()          # graph no longer satisfied
            got = self.auth(ctx)
            self.assertFalse(got["authorized"])
            self.assertIn("candidate-not-derivable", self.codes(got))

    def test_a_malformed_candidate_refuses(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            for bad in ("not-hex", ctx["C"].upper(), ctx["C"][:32], ""):
                got = self.auth(ctx, bad)
                self.assertFalse(got["authorized"], bad)
                self.assertEqual(self.codes(got), ["malformed-candidate"], bad)

    def test_a_malformed_consistency_record_refuses(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            record_path(ctx["consistency"], ctx["C"]).write_text("{not json", encoding="utf-8")
            got = self.auth(ctx)
            self.assertFalse(got["authorized"])
            self.assertIn("malformed-consistency-record", self.codes(got))

    def test_findings_name_the_mechanical_reason(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack, accept_consistency=False)
            got = self.auth(ctx)
            self.assertTrue(all({"code", "reason"} <= set(f) for f in got["findings"]))


class StabilityTest(Fixture):
    """Authorization binds engineering meaning, not incidental history."""

    def test_a_graph_reformat_does_not_disturb_authorization(self):
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            ctx["graph"].write_text(json.dumps(json.loads(ctx["graph"].read_text()),
                                               indent=4, sort_keys=True) + "\n")
            got = self.auth(ctx)
            self.assertTrue(got["authorized"], got["findings"])

    def test_an_equivalent_artifact_rerecord_does_not_disturb_authorization(self):
        """Same content, dependencies and purpose: C is unchanged, so acceptance still applies."""
        with contextlib.ExitStack() as stack:
            ctx = self.build(stack)
            doc = json.loads(ctx["ledger"].read_text())
            doc["artifacts"][A]["review"]["gate"] = "phases/spec/other-attempt/g.json"
            doc["artifacts"][A]["review"]["gate_sha256"] = "e" * 64
            ctx["ledger"].write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
            got = self.auth(ctx)
            self.assertTrue(got["authorized"], got["findings"])
            self.assertEqual(got["candidate"], ctx["C"])


class BoundCandidateReportTest(unittest.TestCase):
    """Which candidate governs each task — derived from immutable contracts, never stored."""

    maxDiff = None

    def run_with(self, stack, tasks):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        run = root / "runs" / "r1"
        state = {"execution_status": "active", "phases": {"impl": {"tasks": {}}}}
        for task_id, (candidate, status) in tasks.items():
            d = run / "phases" / "impl" / "tasks" / task_id / "contracts"
            d.mkdir(parents=True)
            body = (f"# Task {task_id}\nContract revision: r0001\n\n## Objective\nDo it.\n\n"
                    "## Review purpose\n- implementation-review\n\n")
            if candidate:
                body += f"## Proofbound candidate\n- {candidate}\n\n"
            body += "## Acceptance criteria\n- AC-001 — done.\n"
            p = d / "r0001.md"; p.write_text(body, encoding="utf-8")
            state["phases"]["impl"]["tasks"][task_id] = {
                "status": status,
                "current_contract": {"revision": 1, "path": str(p.resolve()),
                                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}}
        run.mkdir(parents=True, exist_ok=True)
        (run / "state.json").write_text(json.dumps(state))
        return run

    def test_two_tasks_naming_different_candidates_are_both_reported(self):
        C1, C2 = "a" * 64, "b" * 64
        with contextlib.ExitStack() as stack:
            run = self.run_with(stack, {"T1": (C1, "accepted"), "T2": (C2, "accepted")})
            got = bound_candidates(run)
            self.assertEqual({t["task"]: t["candidate"] for t in got["tasks"]},
                             {"impl/T1": C1, "impl/T2": C2})
            self.assertEqual(sorted(got["candidates"]), sorted([C1, C2]))
            self.assertTrue(got["divergent"])

    def test_divergence_is_information_not_a_failure(self):
        """Mixed candidates are legitimate; there is no barrier and no failure verdict."""
        C1, C2 = "a" * 64, "b" * 64
        with contextlib.ExitStack() as stack:
            run = self.run_with(stack, {"T1": (C1, "accepted"), "T2": (C2, "accepted")})
            got = bound_candidates(run)
            self.assertNotIn("invalid", json.dumps(got))
            self.assertNotIn("failed", json.dumps(got))
            self.assertNotIn("error", json.dumps(got))

    def test_one_candidate_across_tasks_is_not_divergent(self):
        C1 = "a" * 64
        with contextlib.ExitStack() as stack:
            run = self.run_with(stack, {"T1": (C1, "accepted"), "T2": (C1, "in-progress")})
            got = bound_candidates(run)
            self.assertFalse(got["divergent"])
            self.assertEqual(got["candidates"], [C1])

    def test_inherited_tasks_without_a_candidate_are_reported_as_unbound(self):
        """Compatibility: a task with no Proofbound binding is not an error."""
        C1 = "a" * 64
        with contextlib.ExitStack() as stack:
            run = self.run_with(stack, {"T1": (C1, "accepted"), "Legacy": (None, "accepted")})
            got = bound_candidates(run)
            unbound = [t for t in got["tasks"] if t["candidate"] is None]
            self.assertEqual([t["task"] for t in unbound], ["impl/Legacy"])
            self.assertEqual(got["candidates"], [C1])
            self.assertFalse(got["divergent"])


if __name__ == "__main__":
    unittest.main()
