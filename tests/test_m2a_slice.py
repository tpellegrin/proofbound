"""M2A vertical slice: an accepted artifact becomes a durable, self-validating record.

The thesis:

    Proofbound can persist a compact, version-controlled record of an accepted artifact
    and its dependency/review provenance, derive validity from content identity and
    dependency closure without the run tree, and preserve semantic review purpose without
    creating a second acceptance engine.

Two artifacts and one dependency edge, because one artifact cannot prove dependency
staleness — the mechanism everything later is built on. The full DAG is deferred.

Everything that rejects here must still be inherited DSD enforcement, except the two new
mechanical checks M2A introduces: declared review purpose, and ledger recording fidelity.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))

from _artifact_identity import artifact_identity  # noqa: E402

# A fake `opencode` that plays whichever role the prompt names, and writes the artifact
# belonging to whichever task the report path identifies. Each author attempt writes
# attempt-distinct content so scope movement is real rather than a no-op rewrite.
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
task = report.parent.parent.parent.name
mode = os.environ.get('DSD_FAKE_MODE', 'ok')
ARTIFACTS = {'CH-001-proposal': 'specs/CH-001/proposal.md',
             'CH-001-design': 'specs/CH-001/design.md'}
artifact = project / ARTIFACTS[task]
if 'DSD SPEC AUTHOR' in prompt:
    artifact.parent.mkdir(parents=True, exist_ok=True)
    body = os.environ.get('DSD_FAKE_BODY', '')
    if body:
        artifact.write_text(body)
    else:
        artifact.write_text('# %s (%s)\nProblem, scope, non-goals.\n' % (task, attempt))
    if mode == 'forge_ledger':
        # A worker trying to write the durable ledger itself.
        led = project / 'specs' / 'CH-001' / 'ledger.json'
        led.write_text('{"format": "proofbound-change-ledger-v1", "artifact_identity":'
                       ' "proofbound-artifact-text-v1", "artifacts": {}}\n')
    report.write_text('Authored %s in %s.\n' % (task, attempt))
elif 'DSD SPEC REFLECTOR' in prompt:
    report.write_text('Reflection from %s: challenged %s against the repository.\n' % (attempt, task))
else:
    report.write_text('Completed.\n')
'''


def contract(task_id: str, artifact: str, purpose: str, *, title: str) -> str:
    return (
        f"# Task {task_id} — {title}\n"
        "Contract revision: r0001\n\n"
        "## Objective\n"
        f"{title} for CH-001.\n\n"
        "## Review purpose\n"
        f"- {purpose}\n\n"
        "## Allowed source changes\n"
        f"- `{artifact}`\n\n"
        "## Acceptance criteria\n"
        "- AC-001 — the artifact states problem, scope and non-goals.\n"
    )


PROPOSAL_TASK = "CH-001-proposal"
DESIGN_TASK = "CH-001-design"
PROPOSAL_REL = "specs/CH-001/proposal.md"
DESIGN_REL = "specs/CH-001/design.md"
LEDGER_REL = "specs/CH-001/ledger.json"

CONTRACTS = {
    PROPOSAL_TASK: contract(PROPOSAL_TASK, PROPOSAL_REL, "proposal-reflection",
                            title="Author the change proposal"),
    DESIGN_TASK: contract(DESIGN_TASK, DESIGN_REL, "design-reflection",
                          title="Author the design"),
}


class M2ASliceTest(unittest.TestCase):
    maxDiff = None

    # ---------- scaffolding ----------

    def sh(self, cmd, **kw):
        return subprocess.run(cmd, text=True, capture_output=True, check=False, **kw)

    def scratch(self, stack):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        project = root / "project"
        run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
        (root / "bin").mkdir()
        (root / "external").mkdir()

        self.sh(["git", "init", "-q", str(project)])
        self.sh(["git", "-C", str(project), "config", "user.email", "dsd@test.invalid"])
        self.sh(["git", "-C", str(project), "config", "user.name", "DSD Test"])
        (project / "PLAN.md").write_text("plan\n")
        (project / "specs" / "CH-001").mkdir(parents=True)
        (project / "specs" / "CH-001" / "request.md").write_text("Intent: persist media state.\n")
        self.sh(["git", "-C", str(project), "add", "-A"])
        self.sh(["git", "-C", str(project), "commit", "-qm", "base"])

        tasks = {}
        for task_id, text in CONTRACTS.items():
            path = run / "phases" / "spec" / "tasks" / task_id / "contracts" / "r0001.md"
            path.parent.mkdir(parents=True)
            path.write_text(text, encoding="utf-8")
            tasks[task_id] = {
                "status": "prepared",
                "current_contract": {"revision": 1, "path": str(path.resolve()),
                                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
            }

        prep = self.sh([PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                        "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                        "--plan", str((project / "PLAN.md").resolve())])
        self.assertEqual(prep.returncode, 0, prep.stdout + prep.stderr)

        (run / "state.json").write_text(json.dumps({
            "project_worktree": str(project.resolve()),
            "execution_status": "active",
            "next_action": "launch spec-author",
            "worker_rules": json.loads(prep.stdout),
            "worker_runtime": {"harness": "opencode-cli", "model": "m",
                               "opencode": {"run_db": str((root / "external" / "w.db").resolve())}},
            "phases": {"spec": {"status": "in-progress", "tasks": tasks}},
        }))

        fake = root / "bin" / "opencode"
        fake.write_text(FAKE_OPENCODE)
        fake.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(root / "bin") + os.pathsep + env.get("PATH", "")
        return {"root": root, "project": project, "run": run, "env": env,
                "ledger": project / LEDGER_REL}

    def launch(self, ctx, task_id, role, *, mode="ok", body=None, inputs=()):
        env = dict(ctx["env"])
        env["DSD_FAKE_MODE"] = mode
        if body is not None:
            env["DSD_FAKE_BODY"] = body
        cmd = [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
               "--task-id", task_id, "--role", role, "--auto-flag="]
        for path in inputs:
            cmd += ["--input", str(path)]
        cp = self.sh(cmd, env=env)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return Path(json.loads(cp.stdout)["event_dir"])

    def gate(self, ctx, task_id):
        cp = self.sh([PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "gate",
                      "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                      "--task-id", task_id])
        return cp, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {})

    def accept(self, ctx, task_id, gate_path):
        return self.sh([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                        "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                        "--task-id", task_id, "--evidence-gate", str(gate_path),
                        "--next-action", "next"])

    def ledger_record(self, ctx, task_id, artifact_rel, *deps):
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "record",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
               "--task-id", task_id, "--artifact", str(ctx["project"] / artifact_rel),
               "--ledger", str(ctx["ledger"])]
        for dep in deps:
            cmd += ["--depends-on", str(ctx["project"] / dep)]
        return self.sh(cmd)

    def validate(self, ctx, *, run_root=True, project=None):
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "validate",
               "--ledger", str(ctx["ledger"]),
               "--project-root", str(project or ctx["project"])]
        if run_root:
            cmd += ["--run-root", str(ctx["run"].resolve())]
        cp = self.sh(cmd)
        return cp, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {})

    def states(self, data):
        return {a["path"]: a["state"] for a in data["artifacts"]}

    def author_and_accept(self, ctx, task_id, *, mode="ok", body=None):
        """One full inherited cycle: bounded mutation -> fresh independent reflection -> accept."""
        author = self.launch(ctx, task_id, "spec-author", mode=mode, body=body)
        cp, _ = self.gate(ctx, task_id)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        reflector = self.launch(ctx, task_id, "spec-reflector", inputs=[author / "report.md"])
        cp, gate = self.gate(ctx, task_id)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertTrue(gate["integrity_ok"], gate.get("errors"))
        accepted = self.accept(ctx, task_id, reflector / "evidence-gate.json")
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        return author, reflector

    # ---------- the full scenario ----------

    def test_two_artifacts_one_edge_end_to_end(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)

            # 1-4. Artifact A: authored, independently reflected, accepted by inherited mechanics.
            _, reflector_a = self.author_and_accept(ctx, PROPOSAL_TASK)

            # 5. The parent — not either worker — records A.
            rec = self.ledger_record(ctx, PROPOSAL_TASK, PROPOSAL_REL)
            self.assertEqual(rec.returncode, 0, rec.stdout + rec.stderr)
            recorded_a = json.loads(rec.stdout)
            self.assertEqual(recorded_a["review"]["purpose"], "proposal-reflection")
            self.assertEqual(recorded_a["review"]["role"], "spec-reflector")

            # 6-8. Artifact B, reviewed under a different purpose, recorded against accepted A.
            self.author_and_accept(ctx, DESIGN_TASK)
            rec_b = self.ledger_record(ctx, DESIGN_TASK, DESIGN_REL, PROPOSAL_REL)
            self.assertEqual(rec_b.returncode, 0, rec_b.stdout + rec_b.stderr)
            recorded_b = json.loads(rec_b.stdout)
            self.assertEqual(recorded_b["review"]["purpose"], "design-reflection")
            self.assertEqual(recorded_b["depends_on"], {PROPOSAL_REL: recorded_a["content_sha256"]})

            # Purposes stay distinguishable although one role satisfied both.
            stored = json.loads(ctx["ledger"].read_text())
            self.assertEqual(stored["artifacts"][PROPOSAL_REL]["review"]["purpose"], "proposal-reflection")
            self.assertEqual(stored["artifacts"][DESIGN_REL]["review"]["purpose"], "design-reflection")
            self.assertEqual({stored["artifacts"][k]["review"]["role"] for k in stored["artifacts"]},
                             {"spec-reflector"})
            # No absolute machine paths leak into a committed record.
            self.assertNotIn(str(ctx["root"]), ctx["ledger"].read_text())

            # 9-10. Both valid; provenance verified while the run tree exists.
            cp, data = self.validate(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(self.states(data), {PROPOSAL_REL: "valid", DESIGN_REL: "valid"})
            self.assertEqual(data["provenance"], "verified")

            # 11-13. A's bytes move outside the recorded accepted identity.
            accepted_bytes = (ctx["project"] / PROPOSAL_REL).read_bytes()
            (ctx["project"] / PROPOSAL_REL).write_text("# Proposal\nrewritten by hand\n")
            cp, data = self.validate(ctx)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.states(data),
                             {PROPOSAL_REL: "invalid", DESIGN_REL: "needs-revalidation"})

            # 14-16. The run tree disappears. Structural classification is unmoved;
            # provenance becomes unavailable rather than verified — and never "invalid".
            archived = ctx["root"] / "archived-run"
            shutil.move(str(ctx["project"] / "DeepSeekAndDestroy"), str(archived))
            cp_no_run, without = self.validate(ctx, run_root=False)
            self.assertEqual(cp_no_run.returncode, 1)
            self.assertEqual(self.states(without), self.states(data))
            self.assertEqual(without["provenance"], "unavailable")

            # 17-19. Restoring A's exact accepted content restores both, through the edge.
            (ctx["project"] / PROPOSAL_REL).write_bytes(accepted_bytes)
            cp, restored = self.validate(ctx, run_root=False)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(self.states(restored), {PROPOSAL_REL: "valid", DESIGN_REL: "valid"})
            self.assertEqual(restored["provenance"], "unavailable")

            # 20. The ledger was never inside either worker's write boundary.
            for text in CONTRACTS.values():
                self.assertNotIn(LEDGER_REL, text)

    # ---------- the parent owns the ledger ----------

    def test_a_worker_writing_the_ledger_is_caught_by_the_inherited_write_boundary(self):
        """Forging through ordinary bounded mutation fails before any acceptance exists.

        No Proofbound-specific defense is involved: the ledger is simply outside the
        contract's declared write boundary, so the inherited integrity gate refuses.
        """
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            author = self.launch(ctx, PROPOSAL_TASK, "spec-author", mode="forge_ledger")
            cp, gate = self.gate(ctx, PROPOSAL_TASK)
            self.assertFalse(gate["integrity_ok"])
            self.assertTrue(any("WRITE-RESTRICTION" in e for e in gate["errors"]), gate["errors"])
            self.assertTrue(any(LEDGER_REL in e for e in gate["errors"]), gate["errors"])

            # The forged ledger exists on disk, but the attempt that wrote it can never be
            # accepted, so nothing downstream will ever treat it as recorded provenance.
            self.assertTrue(ctx["ledger"].is_file())
            accepted = self.accept(ctx, PROPOSAL_TASK, author / "evidence-gate.json")
            self.assertNotEqual(accepted.returncode, 0)
            self.assertIn("integrity gate is not clean", accepted.stderr)
            task = json.loads((ctx["run"] / "state.json").read_text())["phases"]["spec"]["tasks"]
            self.assertNotEqual(task[PROPOSAL_TASK].get("status"), "accepted")

    def test_parent_ledger_write_does_not_disturb_accepted_scope_evidence(self):
        """The highest mechanical risk in M2A, measured rather than argued."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            _, reflector = self.author_and_accept(ctx, PROPOSAL_TASK)
            gate_path = reflector / "evidence-gate.json"
            gate = json.loads(gate_path.read_text())
            diff_path = Path(gate["scope"]["diff"])
            before = (gate_path.read_bytes(), diff_path.read_bytes(),
                      json.loads((ctx["run"] / "state.json").read_text())["phases"]["spec"]
                      ["tasks"][PROPOSAL_TASK]["accepted"])

            self.assertEqual(self.ledger_record(ctx, PROPOSAL_TASK, PROPOSAL_REL).returncode, 0)

            after = (gate_path.read_bytes(), diff_path.read_bytes(),
                     json.loads((ctx["run"] / "state.json").read_text())["phases"]["spec"]
                     ["tasks"][PROPOSAL_TASK]["accepted"])
            self.assertEqual(before, after, "recording contaminated the accepted attempt evidence")

            cp, data = self.validate(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["provenance"], "verified")

    def test_recording_requires_an_accepted_task(self):
        """The ledger records acceptance; it cannot confer it."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            author = self.launch(ctx, PROPOSAL_TASK, "spec-author")
            self.gate(ctx, PROPOSAL_TASK)
            rec = self.ledger_record(ctx, PROPOSAL_TASK, PROPOSAL_REL)
            self.assertNotEqual(rec.returncode, 0)
            self.assertIn("does not confer it", rec.stderr)
            self.assertFalse(ctx["ledger"].exists())

    def test_recording_an_artifact_outside_the_accepted_write_boundary_is_refused(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.author_and_accept(ctx, PROPOSAL_TASK)
            rec = self.ledger_record(ctx, PROPOSAL_TASK, "specs/CH-001/request.md")
            self.assertNotEqual(rec.returncode, 0)
            self.assertIn("write boundary", rec.stderr)

    def test_recording_against_a_stale_dependency_is_refused(self):
        """Fabricating provenance against ground that has already moved."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.author_and_accept(ctx, PROPOSAL_TASK)
            self.assertEqual(self.ledger_record(ctx, PROPOSAL_TASK, PROPOSAL_REL).returncode, 0)
            self.author_and_accept(ctx, DESIGN_TASK)
            (ctx["project"] / PROPOSAL_REL).write_text("# Proposal\ndrifted\n")
            rec = self.ledger_record(ctx, DESIGN_TASK, DESIGN_REL, PROPOSAL_REL)
            self.assertNotEqual(rec.returncode, 0)
            self.assertIn("invalid", rec.stderr)

    # ---------- purpose and identity, through the real machinery ----------

    def test_a_reviewer_cannot_satisfy_a_reflection_purpose(self):
        """`reviewer` has the independent-review capability but not this purpose."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            author = self.launch(ctx, PROPOSAL_TASK, "spec-author")
            self.gate(ctx, PROPOSAL_TASK)
            wrong = self.launch(ctx, PROPOSAL_TASK, "reviewer", inputs=[author / "report.md"])
            cp, gate = self.gate(ctx, PROPOSAL_TASK)
            self.assertTrue(gate["integrity_ok"], gate.get("errors"))
            accepted = self.accept(ctx, PROPOSAL_TASK, wrong / "evidence-gate.json")
            self.assertNotEqual(accepted.returncode, 0)
            self.assertIn("proposal-reflection", accepted.stderr)

    def test_byte_identical_reauthoring_does_not_invalidate_the_dependent(self):
        """Identity is content, not attempt: a new author attempt with the same text is inert."""
        body = "# Proposal\nStable text.\n"
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.author_and_accept(ctx, PROPOSAL_TASK, body=body)
            self.assertEqual(self.ledger_record(ctx, PROPOSAL_TASK, PROPOSAL_REL).returncode, 0)
            self.author_and_accept(ctx, DESIGN_TASK)
            self.assertEqual(
                self.ledger_record(ctx, DESIGN_TASK, DESIGN_REL, PROPOSAL_REL).returncode, 0)

            # A later author attempt rewrites the identical bytes and is re-recorded.
            (ctx["project"] / PROPOSAL_REL).write_text(body)
            cp, data = self.validate(ctx, run_root=False)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(self.states(data), {PROPOSAL_REL: "valid", DESIGN_REL: "valid"})

    def test_a_crlf_working_tree_keeps_every_artifact_valid(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.author_and_accept(ctx, PROPOSAL_TASK)
            self.assertEqual(self.ledger_record(ctx, PROPOSAL_TASK, PROPOSAL_REL).returncode, 0)
            path = ctx["project"] / PROPOSAL_REL
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
            cp, data = self.validate(ctx, run_root=False)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(self.states(data), {PROPOSAL_REL: "valid"})

    def test_the_ledger_validates_from_a_bare_copy_with_no_run_history(self):
        """The durability claim: a clean checkout is enough for structural validation."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.author_and_accept(ctx, PROPOSAL_TASK)
            self.assertEqual(self.ledger_record(ctx, PROPOSAL_TASK, PROPOSAL_REL).returncode, 0)
            self.author_and_accept(ctx, DESIGN_TASK)
            self.assertEqual(
                self.ledger_record(ctx, DESIGN_TASK, DESIGN_REL, PROPOSAL_REL).returncode, 0)

            clone = ctx["root"] / "clean"
            clone.mkdir()
            for rel in (PROPOSAL_REL, DESIGN_REL, LEDGER_REL):
                dest = clone / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ctx["project"] / rel, dest)

            cp = self.sh([PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "validate",
                          "--ledger", str(clone / LEDGER_REL), "--project-root", str(clone)])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            data = json.loads(cp.stdout)
            self.assertEqual(self.states(data), {PROPOSAL_REL: "valid", DESIGN_REL: "valid"})
            self.assertEqual(data["provenance"], "unavailable")


if __name__ == "__main__":
    unittest.main()
