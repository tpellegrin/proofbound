"""M2C-C vertical slice: implementation work bound to an exact engineering candidate.

Artifacts are accepted, a graph is satisfied, a candidate is frozen and independently
challenged, and only then may implementation be authorized against it. The task's immutable
contract names the candidate, and that contract is its authority for the rest of its life.

The properties that justify the milestone:

    a freeze alone does not authorize — the aggregate challenge is required
    engineering intent moving to C2 does not rebind a running C1 task
    a C1 task still accepts after the project has moved on
    a historical candidate does not authorize new work
    divergent candidates are visible without being a failure
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

CH = "specs/CH-001"
NODES = {"a": "proposal.md", "b": "design.md"}
PURPOSE = {"a": "proposal-reflection", "b": "design-reflection"}

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
target = os.environ.get('DSD_FAKE_TARGET', '')
if 'DSD SPEC AUTHOR' in prompt or 'DSD IMPLEMENTER' in prompt:
    t = project / target
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(os.environ['DSD_FAKE_BODY'])
    report.write_text('Wrote %s in %s.\n' % (target, attempt))
else:
    report.write_text('Reviewed in %s.\n' % attempt)
'''


def spec_contract(node):
    return (f"# Task CH-001-{node} — Author {NODES[node]}\n"
            "Contract revision: r0001\n\n## Objective\n" f"Author {NODES[node]}.\n\n"
            "## Review purpose\n" f"- {PURPOSE[node]}\n\n"
            "## Allowed source changes\n" f"- `{CH}/{NODES[node]}`\n\n"
            "## Acceptance criteria\n- AC-001 — stated.\n")


def consistency_contract(candidate, revision):
    return (f"# Task CH-001-consistency — Challenge the candidate\n"
            f"Contract revision: r{revision:04d}\n\n## Objective\nChallenge the aggregate.\n\n"
            "## Review purpose\n- consistency-reflection\n\n"
            f"## Proofbound candidate\n- {candidate}\n\n"
            "## Allowed source changes\nNONE\n\n"
            "## Acceptance criteria\n- AC-001 — coherent.\n")


def impl_contract(task_id, candidate, revision=1):
    """An implementation task whose engineering authority is exactly this candidate."""
    return (f"# Task {task_id} — Implement against the accepted contract\n"
            f"Contract revision: r{revision:04d}\n\n## Objective\nImplement the change.\n\n"
            "## Review purpose\n- implementation-review\n\n"
            f"## Proofbound candidate\n- {candidate}\n\n"
            "## Allowed source changes\n" f"- `src/{task_id}.py`\n\n"
            "## Acceptance criteria\n- AC-001 — implemented.\n")


class M2CCSliceTest(unittest.TestCase):
    maxDiff = None

    def sh(self, cmd, **kw):
        return subprocess.run(cmd, text=True, capture_output=True, check=False, **kw)

    # ---------- scaffolding ----------

    def scratch(self, stack):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        project = root / "project"
        run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
        (root / "bin").mkdir(); (root / "external").mkdir()
        self.sh(["git", "init", "-q", str(project)])
        self.sh(["git", "-C", str(project), "config", "user.email", "d@t.invalid"])
        self.sh(["git", "-C", str(project), "config", "user.name", "T"])
        (project / "PLAN.md").write_text("plan\n")
        (project / CH).mkdir(parents=True); (project / "src").mkdir()
        self.sh(["git", "-C", str(project), "add", "-A"])
        self.sh(["git", "-C", str(project), "commit", "-qm", "base"])

        tasks = {}
        for node in NODES:
            p = run / "phases" / "spec" / "tasks" / f"CH-001-{node}" / "contracts" / "r0001.md"
            p.parent.mkdir(parents=True); p.write_text(spec_contract(node), encoding="utf-8")
            tasks[f"CH-001-{node}"] = {"status": "prepared", "current_contract": {
                "revision": 1, "path": str(p.resolve()),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}}
        for t in ("CH-001-consistency", "T1", "T2"):
            (run / "phases" / "spec" / "tasks" / t / "contracts").mkdir(parents=True)
            tasks[t] = {"status": "prepared"}

        prep = self.sh([PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                        "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                        "--plan", str((project / "PLAN.md").resolve())])
        self.assertEqual(prep.returncode, 0, prep.stdout + prep.stderr)
        (run / "state.json").write_text(json.dumps({
            "project_worktree": str(project.resolve()), "execution_status": "active",
            "next_action": "launch", "worker_rules": json.loads(prep.stdout),
            "worker_runtime": {"harness": "opencode-cli", "model": "m",
                               "opencode": {"run_db": str((root / "external" / "w.db").resolve())}},
            "phases": {"spec": {"status": "in-progress", "tasks": tasks}}}))
        fake = root / "bin" / "opencode"; fake.write_text(FAKE_OPENCODE); fake.chmod(0o755)
        env = os.environ.copy(); env["PATH"] = str(root / "bin") + os.pathsep + env["PATH"]
        ledger = project / CH / "ledger.json"
        ledger.write_text(json.dumps({"format": "proofbound-change-ledger-v1",
                                      "artifact_identity": "proofbound-artifact-text-v1",
                                      "artifacts": {}}, indent=2, sort_keys=True) + "\n")
        return {"root": root, "project": project, "run": run, "env": env,
                "graph": project / CH / "graph.json", "ledger": ledger,
                "freezes": project / CH / "freezes", "consistency": project / CH / "consistency"}

    def declare(self, ctx):
        from _change_graph import GRAPH_FORMAT, canonical_graph_text
        ctx["graph"].write_text(canonical_graph_text({"format": GRAPH_FORMAT, "artifacts": {
            f"{CH}/{NODES['a']}": [], f"{CH}/{NODES['b']}": [f"{CH}/{NODES['a']}"]}}))

    def bind(self, ctx, task_id, text, revision):
        p = ctx["run"] / "phases" / "spec" / "tasks" / task_id / "contracts" / f"r{revision:04d}.md"
        p.write_text(text, encoding="utf-8")
        state = json.loads((ctx["run"] / "state.json").read_text())
        task = state["phases"]["spec"]["tasks"][task_id]
        task["current_contract"] = {"revision": revision, "path": str(p.resolve()),
                                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        task["status"] = "prepared"; task.pop("accepted", None)
        (ctx["run"] / "state.json").write_text(json.dumps(state))
        return p

    def launch(self, ctx, task_id, role, env_extra=None, inputs=()):
        env = dict(ctx["env"]); env.update(env_extra or {})
        cmd = [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
               "--task-id", task_id, "--role", role, "--auto-flag="]
        for i in inputs:
            cmd += ["--input", str(i)]
        cp = self.sh(cmd, env=env)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return Path(json.loads(cp.stdout)["event_dir"])

    def gate(self, ctx, task_id):
        return self.sh([PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "gate",
                        "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                        "--task-id", task_id])

    def accept(self, ctx, task_id, gate_path):
        return self.sh([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                        "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                        "--task-id", task_id, "--evidence-gate", str(gate_path),
                        "--next-action", "n"])

    def accept_artifact(self, ctx, node, deps=(), *, body=None):
        env = {"DSD_FAKE_TARGET": f"{CH}/{NODES[node]}",
               "DSD_FAKE_BODY": body if body is not None else f"# {NODES[node]}\nContent.\n"}
        task = f"CH-001-{node}"
        author = self.launch(ctx, task, "spec-author", env)
        self.assertEqual(self.gate(ctx, task).returncode, 0)
        refl = self.launch(ctx, task, "spec-reflector", env, [author / "report.md"])
        self.assertEqual(self.gate(ctx, task).returncode, 0)
        self.assertEqual(self.accept(ctx, task, refl / "evidence-gate.json").returncode, 0)
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "record",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec", "--task-id", task,
               "--artifact", str(ctx["project"] / CH / NODES[node]), "--ledger", str(ctx["ledger"])]
        for d in deps:
            cmd += ["--depends-on", str(ctx["project"] / CH / NODES[d])]
        cp = self.sh(cmd)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def freeze(self, ctx):
        cp = self.sh([PYTHON, str(ROOT / "scripts" / "pb_freeze.py"), "create",
                      "--graph", str(ctx["graph"]), "--ledger", str(ctx["ledger"]),
                      "--project-root", str(ctx["project"]),
                      "--run-root", str(ctx["run"].resolve()), "--into", str(ctx["freezes"])])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return json.loads(cp.stdout)["identity"]

    def challenge_and_record(self, ctx, candidate, revision):
        self.bind(ctx, "CH-001-consistency", consistency_contract(candidate, revision), revision)
        refl = self.launch(ctx, "CH-001-consistency", "spec-reflector")
        self.assertEqual(self.gate(ctx, "CH-001-consistency").returncode, 0)
        self.assertEqual(self.accept(ctx, "CH-001-consistency",
                                     refl / "evidence-gate.json").returncode, 0)
        cp = self.sh([PYTHON, str(ROOT / "scripts" / "pb_consistency.py"), "record",
                      "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                      "--task-id", "CH-001-consistency",
                      "--freeze", str(ctx["freezes"] / f"{candidate}.json"),
                      "--into", str(ctx["consistency"])])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def authorize(self, ctx, *, contract=None, candidate=None, run_root=True):
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_execution.py"), "authorize",
               "--graph", str(ctx["graph"]), "--ledger", str(ctx["ledger"]),
               "--project-root", str(ctx["project"]), "--consistency", str(ctx["consistency"])]
        if contract: cmd += ["--contract", str(contract)]
        if candidate: cmd += ["--candidate", candidate]
        if run_root: cmd += ["--run-root", str(ctx["run"].resolve())]
        cp = self.sh(cmd)
        return cp, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {})

    def report(self, ctx):
        cp = self.sh([PYTHON, str(ROOT / "scripts" / "pb_execution.py"), "report",
                      "--run-root", str(ctx["run"].resolve())])
        return cp, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {})

    def implement_and_accept(self, ctx, task_id, candidate, revision=1):
        contract = self.bind(ctx, task_id, impl_contract(task_id, candidate, revision), revision)
        cp, got = self.authorize(ctx, contract=contract)
        env = {"DSD_FAKE_TARGET": f"src/{task_id}.py", "DSD_FAKE_BODY": f"V = '{task_id}'\n"}
        impl = self.launch(ctx, task_id, "implementer", env)
        self.assertEqual(self.gate(ctx, task_id).returncode, 0)
        rev = self.launch(ctx, task_id, "reviewer", env, [impl / "report.md"])
        self.assertEqual(self.gate(ctx, task_id).returncode, 0)
        acc = self.accept(ctx, task_id, rev / "evidence-gate.json")
        return cp, got, acc, rev

    # ---------- the slice ----------

    def test_m2c_c_end_to_end(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx)
            self.accept_artifact(ctx, "a")
            self.accept_artifact(ctx, "b", deps=["a"])
            C1 = self.freeze(ctx)

            # 1. A freeze alone does not authorize: the aggregate challenge is required.
            cp, got = self.authorize(ctx, candidate=C1)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual([f["code"] for f in got["findings"]], ["no-consistency-acceptance"])

            # 2. Challenge C1, then authorization succeeds.
            self.challenge_and_record(ctx, C1, 1)
            cp, got = self.authorize(ctx, candidate=C1)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertTrue(got["authorized"])
            self.assertEqual(got["provenance"], "verified")

            # 3. Authorize and run a real implementation task bound to C1.
            cp, got, acc, rev1 = self.implement_and_accept(ctx, "T1", C1)
            self.assertEqual(cp.returncode, 0, "authorization must pass for a C1 contract")
            self.assertEqual(got["candidate"], C1)
            self.assertEqual(acc.returncode, 0, acc.stdout + acc.stderr)

            # 4. Engineering intent moves to C2.
            self.accept_artifact(ctx, "a", body="# proposal.md\nRevised.\n")
            self.accept_artifact(ctx, "b", deps=["a"])
            C2 = self.freeze(ctx)
            self.assertNotEqual(C2, C1)

            # T1 is still a C1 task: nothing rebound it, and its acceptance stands.
            task = json.loads((ctx["run"] / "state.json").read_text())["phases"]["spec"]["tasks"]["T1"]
            self.assertEqual(task["status"], "accepted")
            from _contract import declared_candidate
            self.assertEqual(declared_candidate(Path(task["current_contract"]["path"])
                                                .read_text(encoding="utf-8")), C1)

            # 5. The historical candidate no longer authorizes NEW work.
            cp, got = self.authorize(ctx, candidate=C1)
            self.assertEqual(cp.returncode, 1)
            self.assertIn("candidate-not-current", [f["code"] for f in got["findings"]])
            self.assertEqual(got["current"], C2)

            # 6. And C2 cannot authorize until it is challenged in its own right.
            cp, got = self.authorize(ctx, candidate=C2)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual([f["code"] for f in got["findings"]], ["no-consistency-acceptance"])

            # 7. Challenge C2; a second implementation task binds it.
            self.challenge_and_record(ctx, C2, 2)
            cp, got, acc, _ = self.implement_and_accept(ctx, "T2", C2)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(acc.returncode, 0, acc.stdout + acc.stderr)

            # 8. Divergence is visible, and is information rather than failure.
            cp, rep = self.report(ctx)
            self.assertEqual(cp.returncode, 1, "divergence is reported")
            self.assertTrue(rep["divergent"])
            self.assertEqual(sorted(rep["candidates"]), sorted([C1, C2]))
            bound = {t["task"]: t["candidate"] for t in rep["tasks"]}
            self.assertEqual(bound["spec/T1"], C1)
            self.assertEqual(bound["spec/T2"], C2)
            # The inherited spec tasks never went through Proofbound authorization.
            self.assertIsNone(bound["spec/CH-001-a"])
            self.assertNotIn("invalid", json.dumps(rep))

            # 9. THE REPLAY PROOF: T1's accepted review cannot be accepted for a C2 contract.
            self.bind(ctx, "T1", impl_contract("T1", C2, 2), 2)
            replay = self.accept(ctx, "T1", rev1 / "evidence-gate.json")
            self.assertNotEqual(replay.returncode, 0, "C1 evidence must never qualify a C2 task")
            self.assertIn("not bound to task.current_contract", replay.stderr)

            # 10. Deleting the consistency run evidence leaves authorization working.
            gate_rel = json.loads((ctx["consistency"] / f"{C2}.json").read_text())["gate"]
            (ctx["run"] / gate_rel).unlink()
            cp, got = self.authorize(ctx, candidate=C2)
            self.assertEqual(cp.returncode, 0, "expendable evidence must not become authority")
            self.assertEqual(got["provenance"], "unavailable")

            # 11. Corrupting it instead refuses new work.
            (ctx["run"] / gate_rel).parent.mkdir(parents=True, exist_ok=True)
            (ctx["run"] / gate_rel).write_text(json.dumps(
                {"integrity_ok": True, "errors": [], "ready_for_interpretation": True,
                 "role": "spec-reflector", "tampered": True}), encoding="utf-8")
            cp, got = self.authorize(ctx, candidate=C2)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(got["provenance"], "contradicted")

    # ---------- focused proofs ----------

    def test_a_contract_without_a_candidate_is_not_proofbound_bound(self):
        """Compatibility: inherited tasks are reported honestly, not treated as errors."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx)
            self.accept_artifact(ctx, "a")
            self.accept_artifact(ctx, "b", deps=["a"])
            legacy = self.bind(ctx, "T1", impl_contract("T1", "x").replace(
                f"## Proofbound candidate\n- x\n\n", ""), 1)
            cp, got = self.authorize(ctx, contract=legacy)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual([f["code"] for f in got["findings"]], ["no-candidate-declared"])

    def test_a_contract_naming_a_different_candidate_than_requested_is_refused(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx)
            self.accept_artifact(ctx, "a")
            self.accept_artifact(ctx, "b", deps=["a"])
            C1 = self.freeze(ctx)
            self.challenge_and_record(ctx, C1, 1)
            contract = self.bind(ctx, "T1", impl_contract("T1", C1), 1)
            cp, got = self.authorize(ctx, contract=contract, candidate="b" * 64)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual([f["code"] for f in got["findings"]], ["contract-candidate-mismatch"])

    def test_a_worker_cannot_rewrite_its_own_engineering_authority(self):
        """Editing the candidate changes the contract hash, which acceptance rejects."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx)
            self.accept_artifact(ctx, "a")
            self.accept_artifact(ctx, "b", deps=["a"])
            C1 = self.freeze(ctx)
            self.challenge_and_record(ctx, C1, 1)
            contract = self.bind(ctx, "T1", impl_contract("T1", C1), 1)
            env = {"DSD_FAKE_TARGET": "src/T1.py", "DSD_FAKE_BODY": "V = 1\n"}
            impl = self.launch(ctx, "T1", "implementer", env)
            self.assertEqual(self.gate(ctx, "T1").returncode, 0)
            rev = self.launch(ctx, "T1", "reviewer", env, [impl / "report.md"])
            self.assertEqual(self.gate(ctx, "T1").returncode, 0)
            # Rewrite the candidate in place, as a worker might attempt.
            contract.write_text(contract.read_text().replace(C1, "b" * 64), encoding="utf-8")
            acc = self.accept(ctx, "T1", rev / "evidence-gate.json")
            self.assertNotEqual(acc.returncode, 0)
            self.assertIn("current contract missing or changed", acc.stderr)


if __name__ == "__main__":
    unittest.main()
