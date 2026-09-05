"""M2C-B vertical slice: an aggregate challenge, durably recorded.

Two artifacts and a graph become a candidate C. A fresh spec-reflector challenges the
aggregate under a contract that names C, the parent accepts it, and the acceptance is
copied into project state. Then every boundary that could rewrite what that means is
attacked.

The properties that justify the milestone:

    a review of C1 can never be accepted for a contract naming C2 — without any nonce,
    reservation field or new freshness machinery

    the record survives deletion of the run tree; only provenance degrades

    C's engineering identity never moves because a challenge happened
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
if 'DSD SPEC AUTHOR' in prompt:
    t = project / target
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(os.environ['DSD_FAKE_BODY'])
    report.write_text('Authored in %s.\n' % attempt)
elif 'DSD SPEC REFLECTOR' in prompt:
    if os.environ.get('DSD_FAKE_MODE') == 'forge_record':
        d = project / 'specs' / 'CH-001' / 'consistency'
        d.mkdir(parents=True, exist_ok=True)
        (d / ('0' * 64 + '.json')).write_text('{"format":"x"}\n')
    report.write_text('Aggregate reflection from %s.\n' % attempt)
else:
    report.write_text('Completed.\n')
'''


def artifact_contract(node, revision=1):
    return (f"# Task CH-001-{node} — Author {NODES[node]}\n"
            f"Contract revision: r{revision:04d}\n\n"
            "## Objective\n" f"Author {NODES[node]}.\n\n"
            "## Review purpose\n" f"- {PURPOSE[node]}\n\n"
            "## Allowed source changes\n" f"- `{CH}/{NODES[node]}`\n\n"
            "## Acceptance criteria\n- AC-001 — states problem, scope and non-goals.\n")


def consistency_contract(candidate, revision=1):
    """Binds the aggregate challenge to one exact candidate. Read-only: no writes declared."""
    return (f"# Task CH-001-consistency — Challenge the candidate\n"
            f"Contract revision: r{revision:04d}\n\n"
            "## Objective\nChallenge the aggregate engineering contract for coherence.\n\n"
            "## Review purpose\n- consistency-reflection\n\n"
            "## Proofbound candidate\n" f"- {candidate}\n\n"
            "## Allowed source changes\nNONE\n\n"
            "## Acceptance criteria\n- AC-001 — the accepted artifacts do not contradict each other.\n")


class M2CBSliceTest(unittest.TestCase):
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
        (project / CH).mkdir(parents=True)
        self.sh(["git", "-C", str(project), "add", "-A"])
        self.sh(["git", "-C", str(project), "commit", "-qm", "base"])

        tasks = {}
        for node in NODES:
            p = run / "phases" / "spec" / "tasks" / f"CH-001-{node}" / "contracts" / "r0001.md"
            p.parent.mkdir(parents=True)
            p.write_text(artifact_contract(node), encoding="utf-8")
            tasks[f"CH-001-{node}"] = {"status": "prepared", "current_contract": {
                "revision": 1, "path": str(p.resolve()),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}}
        # The consistency task exists with no bound contract yet; each revision is written
        # when a candidate is known, exactly as a parent would.
        (run / "phases" / "spec" / "tasks" / "CH-001-consistency" / "contracts").mkdir(parents=True)
        tasks["CH-001-consistency"] = {"status": "prepared"}

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

    def declare(self, ctx, topology):
        from _change_graph import GRAPH_FORMAT, canonical_graph_text
        ctx["graph"].write_text(canonical_graph_text({"format": GRAPH_FORMAT, "artifacts": {
            f"{CH}/{NODES[n]}": [f"{CH}/{NODES[d]}" for d in deps] for n, deps in topology.items()}}),
            encoding="utf-8")

    def launch(self, ctx, task_id, role, *, env_extra=None, inputs=()):
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
        author = self.launch(ctx, task, "spec-author", env_extra=env)
        self.assertEqual(self.gate(ctx, task).returncode, 0)
        reflector = self.launch(ctx, task, "spec-reflector", env_extra=env,
                                inputs=[author / "report.md"])
        self.assertEqual(self.gate(ctx, task).returncode, 0)
        self.assertEqual(self.accept(ctx, task, reflector / "evidence-gate.json").returncode, 0)
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "record",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
               "--task-id", task, "--artifact", str(ctx["project"] / CH / NODES[node]),
               "--ledger", str(ctx["ledger"])]
        for d in deps:
            cmd += ["--depends-on", str(ctx["project"] / CH / NODES[d])]
        cp = self.sh(cmd)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def freeze(self, ctx):
        cp = self.sh([PYTHON, str(ROOT / "scripts" / "pb_freeze.py"), "create",
                      "--graph", str(ctx["graph"]), "--ledger", str(ctx["ledger"]),
                      "--project-root", str(ctx["project"]), "--run-root", str(ctx["run"].resolve()),
                      "--into", str(ctx["freezes"])])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return json.loads(cp.stdout)["identity"]

    def bind_consistency_contract(self, ctx, candidate, revision):
        """The parent writes an immutable contract naming exactly this candidate."""
        p = (ctx["run"] / "phases" / "spec" / "tasks" / "CH-001-consistency" / "contracts"
             / f"r{revision:04d}.md")
        p.write_text(consistency_contract(candidate, revision), encoding="utf-8")
        state = json.loads((ctx["run"] / "state.json").read_text())
        task = state["phases"]["spec"]["tasks"]["CH-001-consistency"]
        task["current_contract"] = {"revision": revision, "path": str(p.resolve()),
                                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        task["status"] = "prepared"
        task.pop("accepted", None)
        (ctx["run"] / "state.json").write_text(json.dumps(state))
        return p

    def challenge(self, ctx, *, mode="ok"):
        """Run the aggregate challenge and accept it. Returns the reflector attempt dir."""
        reflector = self.launch(ctx, "CH-001-consistency", "spec-reflector",
                                env_extra={"DSD_FAKE_MODE": mode})
        gate = self.gate(ctx, "CH-001-consistency")
        if mode != "ok":
            return reflector, gate
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        acc = self.accept(ctx, "CH-001-consistency", reflector / "evidence-gate.json")
        self.assertEqual(acc.returncode, 0, acc.stdout + acc.stderr)
        return reflector, gate

    def record(self, ctx, candidate):
        return self.sh([PYTHON, str(ROOT / "scripts" / "pb_consistency.py"), "record",
                        "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                        "--task-id", "CH-001-consistency",
                        "--freeze", str(ctx["freezes"] / f"{candidate}.json"),
                        "--into", str(ctx["consistency"])])

    def status(self, ctx, candidate, *, run_root=True):
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_consistency.py"), "status",
               "--into", str(ctx["consistency"]), "--candidate", candidate]
        if run_root:
            cmd += ["--run-root", str(ctx["run"].resolve())]
        cp = self.sh(cmd)
        return cp, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {})

    # ---------- the slice ----------

    def test_m2c_b_end_to_end(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": [], "b": ["a"]})
            self.accept_artifact(ctx, "a")
            self.accept_artifact(ctx, "b", deps=["a"])
            C1 = self.freeze(ctx)

            # Nothing challenged yet.
            cp, s = self.status(ctx, C1)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(s["state"], "absent")

            # Challenge C1 through real mechanics and record it.
            self.bind_consistency_contract(ctx, C1, 1)
            self.challenge(ctx)
            rec = self.record(ctx, C1)
            self.assertEqual(rec.returncode, 0, rec.stdout + rec.stderr)
            record_path = Path(json.loads(rec.stdout)["record"])
            record_bytes = record_path.read_bytes()

            cp, s = self.status(ctx, C1)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(s["state"], "accepted")
            self.assertEqual(s["provenance"], "verified")
            self.assertEqual(s["findings"], [])

            # The record carries exactly four fields, and no verdict of any kind.
            stored = json.loads(record_bytes)
            self.assertEqual(sorted(stored), ["candidate", "format", "gate", "gate_sha256"])
            for forbidden in ("role", "purpose", "approved", "consistent", "status", "timestamp"):
                self.assertNotIn(forbidden, stored)

            # The challenge did not move the engineering identity.
            self.assertEqual(self.freeze(ctx), C1, "a challenge must not change what C means")

            # Re-review of the same C: fresh attempt, new gate, same subject.
            self.bind_consistency_contract(ctx, C1, 2)
            self.challenge(ctx)
            again = self.record(ctx, C1)
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertTrue(json.loads(again.stdout)["refreshed"])
            self.assertEqual(sorted(p.name for p in ctx["consistency"].iterdir()),
                             [f"{C1}.json"], "re-review refreshes one subject, it does not accrue")
            self.assertEqual(self.status(ctx, C1)[1]["provenance"], "verified")
            # The refresh repointed provenance at the newer gate while the subject — the
            # candidate the record concerns — is unchanged. Git carries the history.
            refreshed = json.loads(record_path.read_bytes())
            self.assertEqual(refreshed["candidate"], C1)
            self.assertNotEqual(refreshed["gate"], json.loads(record_bytes)["gate"])
            record_bytes = record_path.read_bytes()

            # Engineering intent moves: C2 is a different subject with no acceptance.
            self.accept_artifact(ctx, "a", body="# proposal.md\nRevised.\n")
            self.accept_artifact(ctx, "b", deps=["a"])
            C2 = self.freeze(ctx)
            self.assertNotEqual(C2, C1)
            cp, s2 = self.status(ctx, C2)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(s2["state"], "absent")
            self.assertEqual(self.status(ctx, C1)[1]["state"], "accepted",
                             "C1's historical acceptance survives the project moving on")

            # THE REPLAY PROOF: the accepted C1 review cannot be accepted for a C2 contract.
            c1_gate = None
            for d in sorted((ctx["run"] / "phases" / "spec" / "tasks" / "CH-001-consistency"
                             / "attempts").iterdir()):
                if (d / "evidence-gate.json").is_file():
                    c1_gate = d / "evidence-gate.json"
            self.bind_consistency_contract(ctx, C2, 3)
            replay = self.accept(ctx, "CH-001-consistency", c1_gate)
            self.assertNotEqual(replay.returncode, 0, "a C1 review must never qualify C2")
            self.assertIn("not bound to task.current_contract", replay.stderr)

            # C2 earns its own acceptance; both coexist as distinct subjects.
            self.challenge(ctx)
            self.assertEqual(self.record(ctx, C2).returncode, 0)
            self.assertEqual(self.status(ctx, C2)[1]["state"], "accepted")
            self.assertEqual(self.status(ctx, C1)[1]["state"], "accepted")
            self.assertEqual(sorted(p.name for p in ctx["consistency"].iterdir()),
                             sorted([f"{C1}.json", f"{C2}.json"]))

            # Run tree deleted: durable acceptance intact, provenance degrades only.
            archived = ctx["root"] / "archived"
            shutil.move(str(ctx["project"] / "DeepSeekAndDestroy"), str(archived))
            cp, s = self.status(ctx, C1, run_root=False)
            self.assertEqual(cp.returncode, 0, "absent evidence is not a failure")
            self.assertEqual(s["state"], "accepted")
            self.assertEqual(s["provenance"], "unavailable")
            self.assertEqual(record_path.read_bytes(), record_bytes)

            # Restored: provenance returns independently of the record.
            shutil.move(str(archived), str(ctx["project"] / "DeepSeekAndDestroy"))
            self.assertEqual(self.status(ctx, C1)[1]["provenance"], "verified")

            # Retained evidence corrupted: the record and its identity do not move.
            gate_rel = json.loads(record_bytes)["gate"]
            (ctx["run"] / gate_rel).write_text(json.dumps(
                {"integrity_ok": True, "errors": [], "ready_for_interpretation": True,
                 "role": "spec-reflector", "tampered": True}), encoding="utf-8")
            cp, s = self.status(ctx, C1)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(s["state"], "accepted")
            self.assertEqual(s["provenance"], "contradicted")
            self.assertEqual(record_path.read_bytes(), record_bytes)

    # ---------- authority and refusals ----------

    def test_a_worker_writing_a_consistency_record_is_caught_by_the_write_boundary(self):
        """The reflector cannot self-record acceptance; no new permission system is needed."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": []})
            self.accept_artifact(ctx, "a")
            C = self.freeze(ctx)
            self.bind_consistency_contract(ctx, C, 1)
            reflector, gate = self.challenge(ctx, mode="forge_record")
            g = json.loads(gate.stdout)
            self.assertFalse(g["integrity_ok"])
            self.assertTrue(any("READONLY-SCOPE-MOVED" in e or "WRITE-RESTRICTION" in e
                                for e in g["errors"]), g["errors"])
            acc = self.accept(ctx, "CH-001-consistency", reflector / "evidence-gate.json")
            self.assertNotEqual(acc.returncode, 0)
            self.assertIn("integrity gate is not clean", acc.stderr)
            self.assertEqual(self.record(ctx, C).returncode, 2, "no acceptance, nothing to record")

    def test_recording_requires_an_accepted_task(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": []})
            self.accept_artifact(ctx, "a")
            C = self.freeze(ctx)
            self.bind_consistency_contract(ctx, C, 1)
            self.launch(ctx, "CH-001-consistency", "spec-reflector")
            self.gate(ctx, "CH-001-consistency")
            rec = self.record(ctx, C)
            self.assertEqual(rec.returncode, 2)
            self.assertIn("does not confer it", rec.stderr)
            self.assertFalse(ctx["consistency"].exists())

    def test_recording_refuses_a_contract_naming_a_different_candidate(self):
        """The freeze supplied must be the one the contract bound."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": [], "b": ["a"]})
            self.accept_artifact(ctx, "a")
            self.accept_artifact(ctx, "b", deps=["a"])
            C1 = self.freeze(ctx)
            self.bind_consistency_contract(ctx, C1, 1)
            self.challenge(ctx)
            # Move engineering intent, derive C2, then try to record C1's review against it.
            self.accept_artifact(ctx, "a", body="# proposal.md\nRevised.\n")
            self.accept_artifact(ctx, "b", deps=["a"])
            C2 = self.freeze(ctx)
            rec = self.sh([PYTHON, str(ROOT / "scripts" / "pb_consistency.py"), "record",
                           "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                           "--task-id", "CH-001-consistency",
                           "--freeze", str(ctx["freezes"] / f"{C2}.json"),
                           "--into", str(ctx["consistency"])])
            self.assertEqual(rec.returncode, 2)
            self.assertIn("but the supplied freeze is", rec.stderr)

    def test_recording_refuses_a_non_consistency_purpose(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": []})
            self.accept_artifact(ctx, "a")
            C = self.freeze(ctx)
            # An ordinary artifact task was accepted under design-reflection, not an
            # aggregate challenge; its acceptance must not become a consistency record.
            rec = self.sh([PYTHON, str(ROOT / "scripts" / "pb_consistency.py"), "record",
                           "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                           "--task-id", "CH-001-a",
                           "--freeze", str(ctx["freezes"] / f"{C}.json"),
                           "--into", str(ctx["consistency"])])
            self.assertEqual(rec.returncode, 2)
            self.assertIn("requires 'consistency-reflection'", rec.stderr)


if __name__ == "__main__":
    unittest.main()
