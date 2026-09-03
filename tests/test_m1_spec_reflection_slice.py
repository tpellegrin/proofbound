"""M1 vertical slice: a specification artifact is an ordinary reviewed project mutation.

The thesis this file exists to prove is narrow and mechanical:

    a spec-author's project mutation cannot be accepted without a fresh, independent,
    non-mutating reflection of that exact mutation — enforced by the inherited
    mutation -> independent review -> acceptance machinery, not by new Proofbound code.

Every rejection asserted here must come from existing DSD enforcement. If a test in this
file starts needing a Proofbound-specific check to pass, the architectural thesis is wrong.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

# A fake `opencode` that plays whichever role the rendered prompt names. Each author
# attempt writes distinct content, so scope movement is real rather than a no-op rewrite.
FAKE_OPENCODE = r'''#!/usr/bin/env python3
import os, pathlib, re, sys
a = sys.argv[1:]
if a[:2] == ['session', 'list']:
    print('[]'); raise SystemExit(0)
if not a or a[0] != 'run':
    raise SystemExit(2)
prompt = a[-1]
report = pathlib.Path(re.search(r'^Report: (.+)$', prompt, re.M).group(1).strip())
project = pathlib.Path(a[a.index('--dir') + 1])
attempt = report.parent.name
mode = os.environ.get('DSD_FAKE_MODE', 'ok')
artifact = project / 'specs' / 'CH-001' / 'proposal.md'
if 'DSD SPEC AUTHOR' in prompt:
    if mode == 'stray':
        (project / 'src.py').write_text('VALUE = 99\n')
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('# Proposal (%s)\nProblem, scope, non-goals.\n' % attempt)
    report.write_text('Authored the proposal in %s: problem, scope and non-goals stated.\n' % attempt)
elif 'DSD SPEC REFLECTOR' in prompt:
    if mode == 'reflector_writes':
        artifact.write_text('# Proposal\nedited by the reflector\n')
    report.write_text('Reflection from %s: challenged the proposal against the repository.\n' % attempt)
elif 'DSD IMPLEMENTER' in prompt:
    (project / 'src.py').write_text('VALUE = 2\n')
    report.write_text('Implemented the requested behavior.\n')
elif 'DSD REVIEWER' in prompt:
    report.write_text('Independent review reached the production path; no task-relevant defect.\n')
else:
    report.write_text('Completed.\n')
'''

SPEC_CONTRACT = (
    "# Task CH-001-proposal — Author the change proposal\n"
    "Contract revision: r0001\n\n"
    "## Objective\n"
    "Author the change proposal for CH-001.\n\n"
    "## Allowed source changes\n"
    "- `specs/CH-001/proposal.md`\n\n"
    "## Acceptance criteria\n"
    "- AC-001 — the proposal states problem, scope and non-goals.\n"
)

IMPL_CONTRACT = (
    "# Task U1 — Set value\n"
    "Contract revision: r0001\n\n"
    "## Objective\n"
    "Set the value.\n\n"
    "## Acceptance criteria\n"
    "- AC-001 — VALUE equals 2.\n"
)


class SpecReflectionSliceTest(unittest.TestCase):
    maxDiff = None

    # ---------- scaffolding ----------

    def sh(self, cmd, **kw):
        return subprocess.run(cmd, text=True, capture_output=True, check=False, **kw)

    def scratch(self, stack, *, task_id="CH-001-proposal", contract_text=SPEC_CONTRACT):
        """One isolated project + run + bound contract + fake worker runtime."""
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        project = root / "project"
        run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
        task_root = run / "phases" / "spec" / "tasks" / task_id
        contract = task_root / "contracts" / "r0001.md"
        contract.parent.mkdir(parents=True)
        (root / "bin").mkdir()
        (root / "external").mkdir()

        self.sh(["git", "init", "-q", str(project)])
        self.sh(["git", "-C", str(project), "config", "user.email", "dsd@test.invalid"])
        self.sh(["git", "-C", str(project), "config", "user.name", "DSD Test"])
        (project / "PLAN.md").write_text("plan\n")
        (project / "src.py").write_text("VALUE = 1\n")
        (project / "specs" / "CH-001").mkdir(parents=True)
        (project / "specs" / "CH-001" / "request.md").write_text("Intent: persist media state.\n")
        self.sh(["git", "-C", str(project), "add", "-A"])
        self.sh(["git", "-C", str(project), "commit", "-qm", "base"])

        contract.write_text(contract_text)
        prep = self.sh([PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                        "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                        "--plan", str((project / "PLAN.md").resolve())])
        self.assertEqual(prep.returncode, 0, prep.stdout + prep.stderr)

        state = {
            "project_worktree": str(project.resolve()),
            "execution_status": "active",
            "next_action": "launch spec-author",
            "worker_rules": json.loads(prep.stdout),
            "worker_runtime": {"harness": "opencode-cli", "model": "m",
                               "opencode": {"run_db": str((root / "external" / "w.db").resolve())}},
            "phases": {"spec": {"status": "in-progress", "tasks": {task_id: {
                "status": "prepared",
                "current_contract": {"revision": 1, "path": str(contract.resolve()),
                                     "sha256": hashlib.sha256(contract.read_bytes()).hexdigest()},
            }}}},
        }
        (run / "state.json").write_text(json.dumps(state))

        fake = root / "bin" / "opencode"
        fake.write_text(FAKE_OPENCODE)
        fake.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(root / "bin") + os.pathsep + env.get("PATH", "")

        return {"root": root, "project": project, "run": run, "task_root": task_root,
                "contract": contract, "env": env, "task_id": task_id, "phase_id": "spec"}

    def launch(self, ctx, role, *, mode="ok", inputs=()):
        env = dict(ctx["env"])
        env["DSD_FAKE_MODE"] = mode
        cmd = [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", ctx["phase_id"],
               "--task-id", ctx["task_id"], "--role", role, "--auto-flag="]
        for path in inputs:
            cmd += ["--input", str(path)]
        cp = self.sh(cmd, env=env)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return Path(json.loads(cp.stdout)["event_dir"])

    def gate(self, ctx):
        cp = self.sh([PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "gate",
                      "--run-root", str(ctx["run"].resolve()), "--phase-id", ctx["phase_id"],
                      "--task-id", ctx["task_id"]])
        return cp, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {})

    def accept(self, ctx, gate_path):
        return self.sh([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                        "--run-root", str(ctx["run"].resolve()), "--phase-id", ctx["phase_id"],
                        "--task-id", ctx["task_id"], "--evidence-gate", str(gate_path),
                        "--next-action", "next"])

    def task_state(self, ctx):
        state = json.loads((ctx["run"] / "state.json").read_text())
        return state["phases"][ctx["phase_id"]]["tasks"][ctx["task_id"]]

    # ---------- the slice ----------

    def test_spec_mutation_needs_fresh_independent_reflection_to_be_accepted(self):
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)

            author = self.launch(ctx, "spec-author")
            cp, gate = self.gate(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertTrue(gate["integrity_ok"])
            artifact = ctx["project"] / "specs" / "CH-001" / "proposal.md"
            self.assertTrue(artifact.is_file(), "spec-author performed no allowed mutation")

            # The author's own attempt can never be its own independent review.
            self_accept = self.accept(ctx, author / "evidence-gate.json")
            self.assertNotEqual(self_accept.returncode, 0)
            self.assertIn("independent-review", self_accept.stderr)

            reflector = self.launch(ctx, "spec-reflector", inputs=[author / "report.md"])
            cp, gate = self.gate(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertTrue(gate["integrity_ok"])
            reservation = json.loads((reflector / "launch-reservation.json").read_text())
            self.assertFalse(reservation["writes_project"], "reflector must be project-read-only")

            accepted = self.accept(ctx, reflector / "evidence-gate.json")
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            task = self.task_state(ctx)
            self.assertEqual(task["status"], "accepted")
            self.assertEqual(Path(task["accepted"]["semantic_report"]["path"]).parent, reflector)
            # Acceptance records provenance, never a verdict the orchestrator had to author.
            self.assertNotIn("last_verdict", task)
            self.assertNotIn("verdict", json.dumps(task))

            check = self.sh([PYTHON, str(ROOT / "scripts" / "check_state.py"),
                             str(ctx["run"] / "state.json")])
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_fail_then_revise_under_the_same_contract_needs_fresh_reflection(self):
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)

            author1 = self.launch(ctx, "spec-author")
            self.gate(ctx)
            reflector1 = self.launch(ctx, "spec-reflector", inputs=[author1 / "report.md"])
            self.gate(ctx)

            # FAIL: the parent routes the findings back as ordinary exact input.
            author2 = self.launch(ctx, "spec-author", inputs=[reflector1 / "report.md"])
            cp, gate = self.gate(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertTrue(gate["integrity_ok"])

            # The revision did not need a new contract revision.
            self.assertEqual(sorted(p.name for p in (ctx["task_root"] / "contracts").iterdir()),
                             ["r0001.md"])
            self.assertIn(str(reflector1 / "report.md"),
                          (author2 / "launch-prompt.txt").read_text())

            stale = self.accept(ctx, reflector1 / "evidence-gate.json")
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("predates later project mutation", stale.stderr)

            reflector2 = self.launch(ctx, "spec-reflector", inputs=[author2 / "report.md"])
            self.gate(ctx)
            accepted = self.accept(ctx, reflector2 / "evidence-gate.json")
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            self.assertEqual(self.task_state(ctx)["status"], "accepted")

    def test_a_second_author_attempt_cannot_stand_in_for_reflection(self):
        """Independence is a role capability, not merely a different attempt."""
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.launch(ctx, "spec-author")
            self.gate(ctx)
            author2 = self.launch(ctx, "spec-author")
            self.gate(ctx)
            rejected = self.accept(ctx, author2 / "evidence-gate.json")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("independent-review", rejected.stderr)

    def test_a_read_only_non_review_role_cannot_qualify(self):
        """The capability set stays narrow: read-only alone is not independent review."""
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            author = self.launch(ctx, "spec-author")
            self.gate(ctx)
            clerk = self.launch(ctx, "evidence-clerk", inputs=[author / "report.md"])
            self.gate(ctx)
            rejected = self.accept(ctx, clerk / "evidence-gate.json")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("independent-review", rejected.stderr)

    def test_review_capability_is_shared_but_doctrine_is_not(self):
        """A deliberate, documented consequence — pinned so it cannot change silently.

        `reviewer` and `spec-reflector` both carry independent-review *capability*, so either
        can satisfy acceptance mechanically. Which one a task warrants stays a parent role
        choice: making Python decide that would require it to classify task semantics, which
        the architecture forbids. What keeps them distinct is doctrine — each attempt loads
        exactly one role protocol.
        """
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            author = self.launch(ctx, "spec-author")
            self.gate(ctx)
            reviewer = self.launch(ctx, "reviewer", inputs=[author / "report.md"])
            self.gate(ctx)
            accepted = self.accept(ctx, reviewer / "evidence-gate.json")
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            prompt = (reviewer / "launch-prompt.txt").read_text()
            self.assertIn("dsd-reviewer/SKILL.md", prompt)
            self.assertNotIn("dsd-spec-reflector/SKILL.md", prompt)

    def test_spec_author_write_outside_allowed_scope_fails_confinement(self):
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.launch(ctx, "spec-author", mode="stray")
            cp, gate = self.gate(ctx)
            self.assertNotEqual(cp.returncode, 0)
            self.assertFalse(gate["integrity_ok"])
            self.assertTrue(any("WRITE-RESTRICTION" in e for e in gate["errors"]), gate["errors"])
            self.assertTrue(any("src.py" in e for e in gate["errors"]), gate["errors"])

    def test_spec_reflector_mutating_reviewed_scope_fails_integrity(self):
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            author = self.launch(ctx, "spec-author")
            self.gate(ctx)
            self.launch(ctx, "spec-reflector", mode="reflector_writes",
                        inputs=[author / "report.md"])
            cp, gate = self.gate(ctx)
            self.assertNotEqual(cp.returncode, 0)
            self.assertFalse(gate["integrity_ok"])
            self.assertTrue(any("READONLY-SCOPE-MOVED" in e for e in gate["errors"]), gate["errors"])

    def test_reflector_prompt_carries_only_what_the_parent_named(self):
        """Reflection independence is also a context property, not only a capability."""
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            author = self.launch(ctx, "spec-author")
            self.gate(ctx)
            reflector = self.launch(ctx, "spec-reflector")
            prompt = (reflector / "launch-prompt.txt").read_text()
            self.assertIn("dsd-spec-reflector/SKILL.md", prompt)
            self.assertNotIn("dsd-spec-author/SKILL.md", prompt)
            self.assertNotIn(str(author / "report.md"), prompt)
            self.assertNotIn(str(author / "worker.log"), prompt)

    def test_existing_implementation_flow_is_unchanged(self):
        import contextlib
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack, task_id="U1", contract_text=IMPL_CONTRACT)
            impl = self.launch(ctx, "implementer")
            cp, gate = self.gate(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertTrue(gate["integrity_ok"])
            self.assertEqual((ctx["project"] / "src.py").read_text(), "VALUE = 2\n")
            self.assertNotEqual(self.accept(ctx, impl / "evidence-gate.json").returncode, 0)
            reviewer = self.launch(ctx, "reviewer", inputs=[impl / "report.md"])
            self.gate(ctx)
            accepted = self.accept(ctx, reviewer / "evidence-gate.json")
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)


class SpecRoleClassificationTest(unittest.TestCase):
    """Registry-level guards against accidental semantic broadening."""

    def roles_module(self):
        scripts = str(ROOT / "scripts")
        sys.path.insert(0, scripts)
        try:
            import importlib
            import _roles
            return importlib.reload(_roles)
        finally:
            sys.path.remove(scripts)

    def test_independent_review_capability_is_exactly_the_two_review_roles(self):
        roles = self.roles_module()
        self.assertEqual(set(roles.INDEPENDENT_REVIEW_ROLES), {"reviewer", "spec-reflector"})

    def test_spec_roles_have_the_intended_capabilities(self):
        roles = self.roles_module()
        self.assertIn("spec-author", roles.ALWAYS_PROJECT_WRITER_ROLES)
        self.assertIn("spec-reflector", roles.ALWAYS_READ_ONLY_ROLES)
        self.assertNotIn("spec-reflector", roles.ALWAYS_PROJECT_WRITER_ROLES)
        self.assertNotIn("spec-author", roles.INDEPENDENT_REVIEW_ROLES)

    def test_inherited_role_capabilities_are_untouched(self):
        roles = self.roles_module()
        self.assertEqual(set(roles.ALWAYS_PROJECT_WRITER_ROLES), {"implementer", "fixer", "spec-author"})
        self.assertEqual(set(roles.CONDITIONALLY_WRITING_ROLES), {"verification"})
        for role in ("reviewer", "evidence-clerk", "discovery", "recovery",
                     "phase-auditor", "phase-surveyor"):
            self.assertIn(role, roles.ALWAYS_READ_ONLY_ROLES)

    def test_every_registered_role_has_a_protocol_file(self):
        roles = self.roles_module()
        for role, relative in roles.ROLE_SKILLS.items():
            self.assertTrue((ROOT / "worker" / relative).is_file(), role)


if __name__ == "__main__":
    unittest.main()
