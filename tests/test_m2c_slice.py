"""M2C-A vertical slice: a durable contract identity through the real machinery.

Three nodes accepted through actual DSD launches, gates and acceptance, frozen, and then
subjected to every mutation that could plausibly rewrite what the freeze means.

The two properties that justify the milestone:

    an equivalent fresh re-review (new gate, new attempt) leaves the identity UNCHANGED
    a changed dependency set changes it, even with byte-identical content

and the durability property: after the ledger is withdrawn from and the graph is deleted,
the freeze still says exactly what the contract was.
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
NODES = {"a": "proposal.md", "b": "design.md", "c": "specification.md"}
PURPOSE = {"a": "proposal-reflection", "b": "design-reflection", "c": "specification-reflection"}
ALT_PURPOSE = {"b": "specification-reflection"}

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
target = project / os.environ['DSD_FAKE_TARGET']
if 'DSD SPEC AUTHOR' in prompt:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(os.environ['DSD_FAKE_BODY'])
    if os.environ.get('DSD_FAKE_MODE') == 'forge_freeze':
        d = project / 'specs' / 'CH-001' / 'freezes'
        d.mkdir(parents=True, exist_ok=True)
        (d / ('0' * 64 + '.json')).write_text('{"format":"proofbound-freeze-v1","artifacts":{}}\n')
    report.write_text('Authored in %s.\n' % attempt)
elif 'DSD SPEC REFLECTOR' in prompt:
    report.write_text('Reflection from %s.\n' % attempt)
else:
    report.write_text('Completed.\n')
'''


def contract(node, purpose, revision=1):
    return (f"# Task CH-001-{node} — Author {NODES[node]}\n"
            f"Contract revision: r{revision:04d}\n\n"
            "## Objective\n" f"Author {NODES[node]}.\n\n"
            "## Review purpose\n" f"- {purpose}\n\n"
            "## Allowed source changes\n" f"- `{CH}/{NODES[node]}`\n\n"
            "## Acceptance criteria\n- AC-001 — states problem, scope and non-goals.\n")


class M2CSliceTest(unittest.TestCase):
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
        (project / CH / "notes.md").write_text("scratch\n")
        self.sh(["git", "-C", str(project), "add", "-A"])
        self.sh(["git", "-C", str(project), "commit", "-qm", "base"])

        tasks = {}
        for node in NODES:
            for rev, purpose in ((1, PURPOSE[node]), (2, ALT_PURPOSE.get(node, PURPOSE[node]))):
                path = run / "phases" / "spec" / "tasks" / f"CH-001-{node}" / "contracts" / f"r{rev:04d}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contract(node, purpose, rev), encoding="utf-8")
            first = run / "phases" / "spec" / "tasks" / f"CH-001-{node}" / "contracts" / "r0001.md"
            tasks[f"CH-001-{node}"] = {"status": "prepared", "current_contract": {
                "revision": 1, "path": str(first.resolve()),
                "sha256": hashlib.sha256(first.read_bytes()).hexdigest()}}

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
                "freezes": project / CH / "freezes"}

    def declare(self, ctx, topology):
        from _change_graph import GRAPH_FORMAT, canonical_graph_text
        ctx["graph"].write_text(canonical_graph_text({"format": GRAPH_FORMAT, "artifacts": {
            f"{CH}/{NODES[n]}": [f"{CH}/{NODES[d]}" for d in deps] for n, deps in topology.items()}}),
            encoding="utf-8")

    def use_contract_revision(self, ctx, node, revision):
        state = json.loads((ctx["run"] / "state.json").read_text())
        path = ctx["run"] / "phases" / "spec" / "tasks" / f"CH-001-{node}" / "contracts" / f"r{revision:04d}.md"
        task = state["phases"]["spec"]["tasks"][f"CH-001-{node}"]
        task["current_contract"] = {"revision": revision, "path": str(path.resolve()),
                                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        task["status"] = "prepared"
        (ctx["run"] / "state.json").write_text(json.dumps(state))

    def accept(self, ctx, node, deps=(), *, body=None, mode="ok"):
        env = dict(ctx["env"]); env["DSD_FAKE_TARGET"] = f"{CH}/{NODES[node]}"
        env["DSD_FAKE_BODY"] = body if body is not None else f"# {NODES[node]}\nContent.\n"
        env["DSD_FAKE_MODE"] = mode
        def launch(role, inputs=()):
            cmd = [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch",
                   "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                   "--task-id", f"CH-001-{node}", "--role", role, "--auto-flag="]
            for i in inputs: cmd += ["--input", str(i)]
            cp = self.sh(cmd, env=env)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            return Path(json.loads(cp.stdout)["event_dir"])
        def gate():
            return self.sh([PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "gate",
                            "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                            "--task-id", f"CH-001-{node}"])
        author = launch("spec-author")
        g = gate()
        if mode != "ok":
            return author, g
        reflector = launch("spec-reflector", [author / "report.md"])
        self.assertEqual(gate().returncode, 0)
        acc = self.sh([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                       "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                       "--task-id", f"CH-001-{node}", "--evidence-gate",
                       str(reflector / "evidence-gate.json"), "--next-action", "n"])
        self.assertEqual(acc.returncode, 0, acc.stdout + acc.stderr)
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "record",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
               "--task-id", f"CH-001-{node}", "--artifact", str(ctx["project"] / CH / NODES[node]),
               "--ledger", str(ctx["ledger"])]
        for d in deps: cmd += ["--depends-on", str(ctx["project"] / CH / NODES[d])]
        rec = self.sh(cmd)
        self.assertEqual(rec.returncode, 0, rec.stdout + rec.stderr)
        return author, reflector

    def freeze_cmd(self, ctx, *args, run_root=True):
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_freeze.py"), *args]
        if args[0] in ("create", "compare") or (len(args) > 1 and args[0] == "compare"):
            cmd += ["--graph", str(ctx["graph"]), "--ledger", str(ctx["ledger"]),
                    "--project-root", str(ctx["project"])]
            if run_root: cmd += ["--run-root", str(ctx["run"].resolve())]
        if args[0] == "create":
            cmd += ["--into", str(ctx["freezes"])]
        cp = self.sh(cmd)
        return cp, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {})

    def candidate_identity(self, ctx):
        """Derive without writing, to observe identity movement."""
        from _change_graph import load_graph
        from _freeze import derive, freeze_identity
        from pb_ledger import load_ledger
        graph = load_graph(ctx["graph"], ctx["project"])
        return freeze_identity(derive(graph, load_ledger(ctx["ledger"])))

    # ---------- the slice ----------

    def test_m2c_a_end_to_end(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": [], "b": ["a"], "c": ["a", "b"]})

            # 1-3. Accept the three nodes through real mechanics.
            self.accept(ctx, "a")
            self.accept(ctx, "b", deps=["a"])
            self.accept(ctx, "c", deps=["a", "b"])
            cp, _ = self.freeze_cmd(ctx, "validate", str(ctx["graph"]))  # sanity: not a freeze
            self.assertEqual(cp.returncode, 2)

            # 4-6. Create F1; identity is recomputable and generation deterministic.
            cp, created = self.freeze_cmd(ctx, "create")
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            F1 = created["identity"]
            self.assertEqual(created["provenance"], "verified")
            f1_path = Path(created["freeze"])
            self.assertEqual(f1_path.name, f"{F1}.json")
            f1_bytes = f1_path.read_bytes()
            cp, again = self.freeze_cmd(ctx, "create")
            self.assertEqual(again["identity"], F1)
            self.assertFalse(again["created"], "identical derivation must not rewrite the file")
            self.assertEqual(f1_path.read_bytes(), f1_bytes)

            # 7. Internally valid, and role/gate never entered the bytes.
            cp, v = self.freeze_cmd(ctx, "validate", str(f1_path))
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(v["identity"], F1)
            text = f1_path.read_text()
            for leaked in ("spec-reflector", "evidence-gate", "attempts", "gate_sha256", "role"):
                self.assertNotIn(leaked, text, f"{leaked!r} leaked into engineering identity")

            # 8. Current project still produces F1.
            cp, cmp1 = self.freeze_cmd(ctx, "compare", str(f1_path))
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertTrue(cmp1["candidate"]["equivalent"])
            self.assertEqual(cmp1["provenance"], "verified")

            # 9-10. Equivalent fresh re-review: new attempt, new gate, identical meaning.
            self.accept(ctx, "b", deps=["a"])
            self.assertEqual(self.candidate_identity(ctx), F1,
                             "an equivalent re-review must not churn the contract identity")

            # 11-12. Changed dependency set with byte-identical content -> different identity.
            from _artifact_identity import artifact_identity_file
            before = artifact_identity_file(ctx["project"] / CH / NODES["b"])
            self.declare(ctx, {"a": [], "b": ["a", "c"], "c": ["a"]})
            self.accept(ctx, "c", deps=["a"])
            self.accept(ctx, "b", deps=["a", "c"])
            self.assertEqual(artifact_identity_file(ctx["project"] / CH / NODES["b"]), before,
                             "B's bytes must be unchanged for this to prove anything")
            F2 = self.candidate_identity(ctx)
            self.assertNotEqual(F2, F1, "a changed dependency set must change the identity")

            # 13. F1 is still internally valid and still says what it always said.
            cp, v = self.freeze_cmd(ctx, "validate", str(f1_path))
            self.assertEqual(cp.returncode, 0)
            self.assertEqual(v["identity"], F1)

            # 14-16. Withdraw B: F1 unchanged and still interpretable; candidate diverges.
            self.assertEqual(self.sh([PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "withdraw",
                                      "--ledger", str(ctx["ledger"]), "--project-root",
                                      str(ctx["project"]), "--artifact",
                                      str(ctx["project"] / CH / NODES["b"])]).returncode, 0)
            self.assertEqual(f1_path.read_bytes(), f1_bytes)
            cp, v = self.freeze_cmd(ctx, "validate", str(f1_path))
            self.assertEqual(cp.returncode, 0, "withdrawal must not invalidate a historical freeze")
            frozen_b = json.loads(f1_path.read_text())["artifacts"][f"{CH}/{NODES['b']}"]
            self.assertEqual(frozen_b["review_purpose"], "design-reflection")
            self.assertIn(f"{CH}/{NODES['a']}", frozen_b["depends_on"])
            cp, cmp2 = self.freeze_cmd(ctx, "compare", str(f1_path))
            self.assertEqual(cp.returncode, 1, "not-computable must not report as equivalent")
            self.assertFalse(cmp2["candidate"]["computable"], "unsatisfied graph is not a candidate")
            self.assertEqual(cmp2["repository"], [], "B's bytes are untouched by withdrawal")

            # 17-18. Restore the original engineering binding: candidate returns to exactly F1.
            self.declare(ctx, {"a": [], "b": ["a"], "c": ["a", "b"]})
            self.accept(ctx, "b", deps=["a"])
            self.accept(ctx, "c", deps=["a", "b"])
            self.assertEqual(self.candidate_identity(ctx), F1)

            # 19-21. Reformat the graph only: graph identity moves, contract identity does not.
            graph_before = artifact_identity_file(ctx["graph"])
            ctx["graph"].write_text(json.dumps(json.loads(ctx["graph"].read_text()),
                                               indent=4, sort_keys=True) + "\n", encoding="utf-8")
            self.assertNotEqual(artifact_identity_file(ctx["graph"]), graph_before)
            self.assertEqual(self.candidate_identity(ctx), F1,
                             "graph formatting is authoring history, not engineering meaning")

            # 22-23. Delete the graph: F1 stays interpretable; candidate becomes not-computable.
            ctx["graph"].unlink()
            cp, v = self.freeze_cmd(ctx, "validate", str(f1_path))
            self.assertEqual(cp.returncode, 0, "a freeze must not need its graph")
            cp, cmp3 = self.freeze_cmd(ctx, "compare", str(f1_path))
            self.assertFalse(cmp3["candidate"]["computable"])
            self.assertEqual(cmp3["repository"], [], "files still carry the frozen identities")

            # 24-25. Remove the run tree: identity and structure unchanged, provenance degrades.
            archived = ctx["root"] / "archived"
            shutil.move(str(ctx["project"] / "DeepSeekAndDestroy"), str(archived))
            self.assertEqual(f1_path.read_bytes(), f1_bytes)
            cp, v = self.freeze_cmd(ctx, "validate", str(f1_path))
            self.assertEqual(cp.returncode, 0)
            self.assertEqual(v["identity"], F1)

            # 26. Restore it; provenance returns independently.
            shutil.move(str(archived), str(ctx["project"] / "DeepSeekAndDestroy"))
            self.declare(ctx, {"a": [], "b": ["a"], "c": ["a", "b"]})
            cp, cmp4 = self.freeze_cmd(ctx, "compare", str(f1_path))
            self.assertEqual(cmp4["provenance"], "verified")
            self.assertTrue(cmp4["candidate"]["equivalent"])

            # 27-29. Corrupt a retained gate: identity untouched, provenance contradicted,
            # and creating a *new* durable record from contradicted evidence is refused.
            gate = Path(json.loads(ctx["ledger"].read_text())["artifacts"]
                        [f"{CH}/{NODES['a']}"]["review"]["gate"])
            (ctx["run"] / gate).write_text('{"integrity_ok": true, "errors": [], '
                                           '"ready_for_interpretation": true, "role": "spec-reflector",'
                                           ' "tampered": true}', encoding="utf-8")
            self.assertEqual(f1_path.read_bytes(), f1_bytes)
            cp, v = self.freeze_cmd(ctx, "validate", str(f1_path))
            self.assertEqual(cp.returncode, 0)
            self.assertEqual(v["identity"], F1)
            cp, cmp5 = self.freeze_cmd(ctx, "compare", str(f1_path))
            self.assertEqual(cmp5["provenance"], "contradicted")
            cp, _ = self.freeze_cmd(ctx, "create")
            self.assertEqual(cp.returncode, 2)
            self.assertIn("contradict", cp.stderr)

    # ---------- focused proofs ----------

    def test_a_purpose_change_alone_changes_the_contract_identity(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"b": []})
            self.accept(ctx, "b")
            before = self.candidate_identity(ctx)
            # Same bytes, same (empty) dependencies; only the declared purpose differs.
            self.use_contract_revision(ctx, "b", 2)
            self.accept(ctx, "b")
            self.assertNotEqual(self.candidate_identity(ctx), before)
            self.assertEqual(json.loads(ctx["ledger"].read_text())["artifacts"]
                             [f"{CH}/{NODES['b']}"]["review"]["purpose"], "specification-reflection")

    def test_a_freeze_is_interpretable_with_nothing_but_itself(self):
        """Copy the file alone into an empty directory; internal validation still works."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": [], "b": ["a"]})
            self.accept(ctx, "a")
            self.accept(ctx, "b", deps=["a"])
            cp, created = self.freeze_cmd(ctx, "create")
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            bare = Path(stack.enter_context(tempfile.TemporaryDirectory())) / "f.json"
            shutil.copyfile(created["freeze"], bare)
            cp = self.sh([PYTHON, str(ROOT / "scripts" / "pb_freeze.py"), "validate", str(bare)])
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(json.loads(cp.stdout)["identity"], created["identity"])

    def test_creation_refuses_an_unsatisfied_graph(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": [], "b": ["a"]})
            self.accept(ctx, "a")
            cp, _ = self.freeze_cmd(ctx, "create")
            self.assertEqual(cp.returncode, 2)
            self.assertIn("unsatisfied graph", cp.stderr)
            self.assertFalse(ctx["freezes"].exists())

    def test_a_worker_writing_a_freeze_is_caught_by_the_inherited_write_boundary(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": []})
            author, gate = self.accept(ctx, "a", mode="forge_freeze")
            g = json.loads(gate.stdout)
            self.assertFalse(g["integrity_ok"])
            self.assertTrue(any("WRITE-RESTRICTION" in e for e in g["errors"]), g["errors"])
            self.assertTrue(any("freezes/" in e for e in g["errors"]), g["errors"])
            acc = self.sh([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                           "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                           "--task-id", "CH-001-a", "--evidence-gate",
                           str(author / "evidence-gate.json")])
            self.assertNotEqual(acc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
