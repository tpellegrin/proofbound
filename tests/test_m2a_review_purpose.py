"""Declared review purpose: a closed vocabulary, mechanically enforced at acceptance.

The guarantee this file pins is narrow and worth stating exactly:

    the declared purpose was reviewed by a role authorized for that declared purpose.

It is emphatically NOT:

    Python proved the reviewer performed a philosophically correct architecture review.

The second claim is semantic and stays with humans and agents. Python only compares a
declared string against a constant table and a role recorded on an integrity gate.

`purpose != capability != role`. Several purposes map to one role today. They stay
separate names anyway, because collapsing them would destroy durable engineering
provenance and force retro-classification the moment a role is added.
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

from _contract import declared_review_purpose, declares_review_purpose  # noqa: E402
from _review_purpose import (  # noqa: E402
    REVIEW_PURPOSES,
    REVIEW_PURPOSE_ROLES,
    ReviewPurposeError,
    assert_role_qualifies,
    qualifying_roles,
)
from _roles import INDEPENDENT_REVIEW_ROLES, ROLE_NAMES  # noqa: E402


def contract_text(purpose_section: str = "") -> str:
    return (
        "# Task CH-001-proposal — Author the change proposal\n"
        "Contract revision: r0001\n\n"
        "## Objective\n"
        "Author the change proposal for CH-001.\n\n"
        f"{purpose_section}"
        "## Allowed source changes\n"
        "- `specs/CH-001/proposal.md`\n\n"
        "## Acceptance criteria\n"
        "- AC-001 — the proposal states problem, scope and non-goals.\n"
    )


class ReviewPurposeVocabularyTest(unittest.TestCase):
    maxDiff = None

    def test_vocabulary_is_closed_and_pinned(self):
        self.assertEqual(
            sorted(REVIEW_PURPOSES),
            ["consistency-reflection", "design-reflection", "implementation-review",
             "proposal-reflection", "specification-reflection"],
        )

    def test_every_qualifying_role_is_a_real_role_that_can_review_independently(self):
        """Structural guard: the table can never authorize a role that cannot review.

        Without this, a typo or a future edit could name a role that does not exist, or a
        writer role, and acceptance would quietly authorize the wrong thing.
        """
        for purpose, roles in REVIEW_PURPOSE_ROLES.items():
            self.assertTrue(roles, f"{purpose} has no qualifying role")
            for role in roles:
                self.assertIn(role, ROLE_NAMES, f"{purpose} names unknown role {role}")
                self.assertIn(role, INDEPENDENT_REVIEW_ROLES, f"{purpose} names non-reviewing role {role}")

    def test_distinct_purposes_survive_even_when_they_share_one_role(self):
        """purpose != role. Four reflection purposes, one qualifying role, four names."""
        reflections = ["proposal-reflection", "design-reflection",
                       "specification-reflection", "consistency-reflection"]
        for purpose in reflections:
            self.assertEqual(qualifying_roles(purpose), frozenset({"spec-reflector"}))
        self.assertEqual(len(set(reflections)), 4, "purposes must remain distinguishable")
        self.assertEqual(qualifying_roles("implementation-review"), frozenset({"reviewer"}))

    def test_unknown_purpose_fails_closed(self):
        for unknown in ("architecture-review", "", "REFLECTION", "design_reflection", "spec-reflector"):
            with self.assertRaises(ReviewPurposeError, msg=unknown):
                qualifying_roles(unknown)

    def test_qualifying_role_is_accepted_and_others_are_refused(self):
        assert_role_qualifies("design-reflection", "spec-reflector")
        assert_role_qualifies("implementation-review", "reviewer")
        with self.assertRaises(ReviewPurposeError):
            assert_role_qualifies("design-reflection", "reviewer")
        with self.assertRaises(ReviewPurposeError):
            assert_role_qualifies("implementation-review", "spec-reflector")
        with self.assertRaises(ReviewPurposeError):
            assert_role_qualifies("design-reflection", "spec-author")

    def test_the_table_is_not_mutable_through_the_public_surface(self):
        self.assertIsInstance(qualifying_roles("design-reflection"), frozenset)


class ReviewPurposeContractParsingTest(unittest.TestCase):
    maxDiff = None

    def test_absent_section_is_absent_not_empty(self):
        text = contract_text()
        self.assertFalse(declares_review_purpose(text))
        self.assertIsNone(declared_review_purpose(text))

    def test_declared_purpose_is_read_by_the_existing_bullet_parser(self):
        text = contract_text("## Review purpose\n- design-reflection\n\n")
        self.assertTrue(declares_review_purpose(text))
        self.assertEqual(declared_review_purpose(text), "design-reflection")

    def test_backticked_and_mixed_case_declarations_normalize(self):
        text = contract_text("## Review purpose\n- `Design-Reflection`\n\n")
        self.assertEqual(declared_review_purpose(text), "design-reflection")

    def test_present_but_empty_section_fails_closed(self):
        for body in ("", "- NONE\n", "NONE\n", "design-reflection\n"):
            with self.assertRaises(ValueError, msg=body):
                declared_review_purpose(contract_text(f"## Review purpose\n{body}\n"))

    def test_multiple_declared_purposes_fail_closed(self):
        text = contract_text("## Review purpose\n- design-reflection\n- implementation-review\n\n")
        with self.assertRaises(ValueError):
            declared_review_purpose(text)

    def test_purpose_is_never_inferred_from_prose_or_paths(self):
        """Prose mentioning a purpose elsewhere must not create a declaration."""
        text = contract_text().replace(
            "Author the change proposal for CH-001.",
            "Author the change proposal for CH-001. This needs design-reflection, obviously.\n"
            "See specs/CH-001/design-reflection.md and ## Review purpose in the guide.",
        )
        self.assertFalse(declares_review_purpose(text))
        self.assertIsNone(declared_review_purpose(text))


class ReviewPurposeAcceptanceEnforcementTest(unittest.TestCase):
    """Enforcement at the real acceptance boundary, with synthetic cold evidence.

    No worker is launched here: with no attempt tree the inherited freshness rule does not
    engage, which isolates exactly one thing — the declared-purpose check. The heavy
    real-worker path is proved end to end in the M2A slice test.
    """

    maxDiff = None

    def scratch(self, stack, *, purpose_section: str, gate_role: str):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        project = root / "project"
        run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
        task_root = run / "phases" / "spec" / "tasks" / "CH-001-proposal"
        contract = task_root / "contracts" / "r0001.md"
        contract.parent.mkdir(parents=True)
        contract.write_text(contract_text(purpose_section), encoding="utf-8")

        event = task_root / "attempts" / "cold-1"
        event.mkdir(parents=True)
        report = event / "report.md"
        report.write_text("Reflected on the proposal against the repository.\n", encoding="utf-8")
        gate = event / "evidence-gate.json"
        gate.write_text(json.dumps({
            "integrity_ok": True,
            "errors": [],
            "ready_for_interpretation": True,
            "role": gate_role,
            "writes_project": False,
            "task": str(contract.resolve()),
            "report": str(report.resolve()),
            "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "scope": {"changed_count": 0},
        }), encoding="utf-8")

        (run / "state.json").write_text(json.dumps({
            "project_worktree": str(project.resolve()),
            "execution_status": "active",
            "phases": {"spec": {"status": "in-progress", "tasks": {"CH-001-proposal": {
                "status": "in-review",
                "current_contract": {
                    "revision": 1,
                    "path": str(contract.resolve()),
                    "sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
                },
            }}}},
        }), encoding="utf-8")
        return run, gate

    def accept(self, run, gate):
        return subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
             "--run-root", str(run.resolve()), "--phase-id", "spec",
             "--task-id", "CH-001-proposal", "--evidence-gate", str(gate)],
            text=True, capture_output=True, check=False,
        )

    def test_declared_purpose_with_a_qualifying_role_is_accepted(self):
        with contextlib.ExitStack() as stack:
            run, gate = self.scratch(
                stack, purpose_section="## Review purpose\n- proposal-reflection\n\n",
                gate_role="spec-reflector")
            cp = self.accept(run, gate)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_declared_purpose_with_a_non_qualifying_role_is_refused(self):
        """`reviewer` can review independently, but is not authorized for this purpose."""
        with contextlib.ExitStack() as stack:
            run, gate = self.scratch(
                stack, purpose_section="## Review purpose\n- proposal-reflection\n\n",
                gate_role="reviewer")
            cp = self.accept(run, gate)
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("proposal-reflection", cp.stderr)
            self.assertIn("reviewer", cp.stderr)

    def test_unknown_declared_purpose_is_refused(self):
        with contextlib.ExitStack() as stack:
            run, gate = self.scratch(
                stack, purpose_section="## Review purpose\n- architecture-review\n\n",
                gate_role="spec-reflector")
            cp = self.accept(run, gate)
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("architecture-review", cp.stderr)

    def test_malformed_purpose_section_is_refused(self):
        with contextlib.ExitStack() as stack:
            run, gate = self.scratch(
                stack,
                purpose_section="## Review purpose\n- proposal-reflection\n- design-reflection\n\n",
                gate_role="spec-reflector")
            cp = self.accept(run, gate)
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("Review purpose", cp.stderr)

    def test_inherited_contract_without_the_section_keeps_its_exact_semantics(self):
        """The compatibility seam: absence is absence, not a failure and not a default."""
        with contextlib.ExitStack() as stack:
            run, gate = self.scratch(stack, purpose_section="", gate_role="reviewer")
            cp = self.accept(run, gate)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(json.loads(cp.stdout)["status"], "accepted")

    def test_implementation_review_purpose_requires_the_reviewer_role(self):
        with contextlib.ExitStack() as stack:
            run, gate = self.scratch(
                stack, purpose_section="## Review purpose\n- implementation-review\n\n",
                gate_role="spec-reflector")
            self.assertNotEqual(self.accept(run, gate).returncode, 0)
        with contextlib.ExitStack() as stack:
            run, gate = self.scratch(
                stack, purpose_section="## Review purpose\n- implementation-review\n\n",
                gate_role="reviewer")
            self.assertEqual(self.accept(run, gate).returncode, 0)


if __name__ == "__main__":
    unittest.main()


class ReviewPurposeContractRenderingTest(unittest.TestCase):
    """The supported contract constructor must be able to produce an M2A contract.

    `render_task_contract.py` validates its spec against a strict whitelist, so without an
    explicit field a Proofbound specification contract could not be created through the
    supported path at all.
    """

    maxDiff = None

    def render(self, stack, spec_extra):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        run = root / "project" / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
        run.mkdir(parents=True)
        spec = {"run_root": str(run), "phase_id": "spec", "task_id": "CH-001-proposal",
                "objective": "Author the change proposal.", "write_paths": ["specs/CH-001/proposal.md"],
                "acceptance": ["the proposal states problem, scope and non-goals"], **spec_extra}
        cp = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "render_task_contract.py"), "--spec", "-"],
            input=json.dumps(spec), text=True, capture_output=True, check=False)
        return cp

    def test_a_declared_purpose_is_rendered_and_parses_back(self):
        with contextlib.ExitStack() as stack:
            cp = self.render(stack, {"review_purpose": "proposal-reflection"})
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            text = Path(json.loads(cp.stdout)["path"]).read_text(encoding="utf-8")
            self.assertIn("## Review purpose\n- proposal-reflection\n", text)
            self.assertEqual(declared_review_purpose(text), "proposal-reflection")

    def test_an_unknown_purpose_fails_at_contract_construction(self):
        with contextlib.ExitStack() as stack:
            cp = self.render(stack, {"review_purpose": "architecture-review"})
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("architecture-review", cp.stderr)

    def test_omitting_the_field_renders_an_inherited_contract_unchanged(self):
        with contextlib.ExitStack() as stack:
            cp = self.render(stack, {})
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            text = Path(json.loads(cp.stdout)["path"]).read_text(encoding="utf-8")
            self.assertNotIn("Review purpose", text)
            self.assertIsNone(declared_review_purpose(text))
