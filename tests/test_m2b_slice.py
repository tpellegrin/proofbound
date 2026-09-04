"""M2B vertical slice: a declared topology enforced against real accepted artifacts.

Three nodes, because M2A already proved two artifacts and one edge, and three is the
smallest graph that has a *topology* rather than an edge.

Everything here runs through the inherited machinery: real launches, real integrity gates,
real acceptance, real ledger recording. The graph sits above all of it and changes none of
it. The two steps that matter most are the topology revisions — adding a sibling must
disturb nothing, and adding an edge must be visible without rewriting any artifact's
content validity.
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
NODES = {"a": "proposal.md", "b": "design.md", "c": "specification.md", "d": "tasks.md"}
PURPOSE = {"a": "proposal-reflection", "b": "design-reflection",
           "c": "specification-reflection", "d": "design-reflection"}

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
target = project / os.environ['DSD_FAKE_TARGET']
if 'DSD SPEC AUTHOR' in prompt:
    target.parent.mkdir(parents=True, exist_ok=True)
    body = os.environ.get('DSD_FAKE_BODY', '')
    target.write_text(body if body else '# %s (%s)\nProblem, scope, non-goals.\n' % (task, attempt))
    if mode == 'forge_graph':
        (project / 'specs' / 'CH-001' / 'graph.json').write_text('{"format":"x"}\n')
    report.write_text('Authored %s in %s.\n' % (task, attempt))
elif 'DSD SPEC REFLECTOR' in prompt:
    report.write_text('Reflection from %s on %s.\n' % (attempt, task))
else:
    report.write_text('Completed.\n')
'''


def contract(node: str, revision: int = 1) -> str:
    rel = f"{CH}/{NODES[node]}"
    return (
        f"# Task CH-001-{node} — Author {NODES[node]}\n"
        f"Contract revision: r{revision:04d}\n\n"
        "## Objective\n"
        f"Author {NODES[node]} for CH-001.\n\n"
        "## Review purpose\n"
        f"- {PURPOSE[node]}\n\n"
        "## Allowed source changes\n"
        f"- `{rel}`\n\n"
        "## Acceptance criteria\n"
        "- AC-001 — the artifact states problem, scope and non-goals.\n"
    )


class M2BSliceTest(unittest.TestCase):
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
        (project / CH).mkdir(parents=True)
        (project / CH / "request.md").write_text("Intent: persist media state.\n")
        # Ordinary, never-accepted files that must not affect graph satisfaction.
        (project / CH / "notes.md").write_text("scratch thinking\n")
        (project / CH / "research.txt").write_text("links\n")
        self.sh(["git", "-C", str(project), "add", "-A"])
        self.sh(["git", "-C", str(project), "commit", "-qm", "base"])

        tasks = {}
        for node in NODES:
            path = run / "phases" / "spec" / "tasks" / f"CH-001-{node}" / "contracts" / "r0001.md"
            path.parent.mkdir(parents=True)
            path.write_text(contract(node), encoding="utf-8")
            tasks[f"CH-001-{node}"] = {
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
            "execution_status": "active", "next_action": "launch spec-author",
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
                "graph": project / CH / "graph.json", "ledger": project / CH / "ledger.json"}

    # ---------- parent operations ----------

    def declare(self, ctx, topology):
        """Parent writes the graph. Ordinary project state, canonically serialized."""
        sys.path.insert(0, str(ROOT / "scripts"))
        from _change_graph import GRAPH_FORMAT, canonical_graph_text
        doc = {"format": GRAPH_FORMAT,
               "artifacts": {f"{CH}/{NODES[n]}": [f"{CH}/{NODES[d]}" for d in deps]
                             for n, deps in topology.items()}}
        ctx["graph"].write_text(canonical_graph_text({"format": doc["format"],
                                                      "artifacts": doc["artifacts"]}),
                                encoding="utf-8")

    def launch(self, ctx, node, role, *, mode="ok", body=None, inputs=()):
        env = dict(ctx["env"])
        env["DSD_FAKE_MODE"] = mode
        env["DSD_FAKE_TARGET"] = f"{CH}/{NODES[node]}"
        if body is not None:
            env["DSD_FAKE_BODY"] = body
        cmd = [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
               "--task-id", f"CH-001-{node}", "--role", role, "--auto-flag="]
        for path in inputs:
            cmd += ["--input", str(path)]
        cp = self.sh(cmd, env=env)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return Path(json.loads(cp.stdout)["event_dir"])

    def gate(self, ctx, node):
        return self.sh([PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "gate",
                        "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                        "--task-id", f"CH-001-{node}"])

    def accept_and_record(self, ctx, node, deps=(), *, body=None):
        author = self.launch(ctx, node, "spec-author", body=body)
        self.assertEqual(self.gate(ctx, node).returncode, 0)
        reflector = self.launch(ctx, node, "spec-reflector", inputs=[author / "report.md"])
        self.assertEqual(self.gate(ctx, node).returncode, 0)
        acc = self.sh([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                       "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                       "--task-id", f"CH-001-{node}", "--evidence-gate",
                       str(reflector / "evidence-gate.json"), "--next-action", "next"])
        self.assertEqual(acc.returncode, 0, acc.stdout + acc.stderr)
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "record",
               "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
               "--task-id", f"CH-001-{node}", "--artifact", str(ctx["project"] / CH / NODES[node]),
               "--ledger", str(ctx["ledger"])]
        for d in deps:
            cmd += ["--depends-on", str(ctx["project"] / CH / NODES[d])]
        rec = self.sh(cmd)
        self.assertEqual(rec.returncode, 0, rec.stdout + rec.stderr)
        return rec

    def check(self, ctx, *, run_root=True):
        cmd = [PYTHON, str(ROOT / "scripts" / "pb_graph.py"), "validate",
               "--graph", str(ctx["graph"]), "--ledger", str(ctx["ledger"]),
               "--project-root", str(ctx["project"])]
        if run_root:
            cmd += ["--run-root", str(ctx["run"].resolve())]
        cp = self.sh(cmd)
        return cp, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {})

    def codes(self, data):
        return sorted(f["code"] for f in data["findings"])

    def states(self, data):
        return {a["path"]: a["state"] for a in data["artifacts"]}

    # ---------- the slice ----------

    def test_three_node_graph_end_to_end(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            A, B, C = f"{CH}/{NODES['a']}", f"{CH}/{NODES['b']}", f"{CH}/{NODES['c']}"
            D = f"{CH}/{NODES['d']}"

            # 1. Declared, nothing accepted.
            self.declare(ctx, {"a": [], "b": ["a"], "c": ["a", "b"]})
            ctx["ledger"].write_text(json.dumps(
                {"format": "proofbound-change-ledger-v1",
                 "artifact_identity": "proofbound-artifact-text-v1", "artifacts": {}},
                indent=2, sort_keys=True) + "\n", encoding="utf-8")
            cp, data = self.check(ctx)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["missing-accepted-record"] * 3)

            # 2-3. Accept A, then B against A. Still incomplete.
            self.accept_and_record(ctx, "a")
            self.assertEqual(self.codes(self.check(ctx)[1]), ["missing-accepted-record"] * 2)
            self.accept_and_record(ctx, "b", deps=["a"])
            self.assertEqual(self.codes(self.check(ctx)[1]), ["missing-accepted-record"])

            # 4. Accept C against A and B — satisfied.
            self.accept_and_record(ctx, "c", deps=["a", "b"])
            cp, data = self.check(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])
            self.assertEqual(self.states(data), {A: "valid", B: "valid", C: "valid"})
            self.assertEqual({a["provenance"] for a in data["artifacts"]}, {"verified"})
            self.assertEqual({a["declared"] for a in data["artifacts"]}, {True})

            # Ordinary files beside the artifacts never became members.
            self.assertTrue((ctx["project"] / CH / "notes.md").is_file())
            self.assertNotIn("notes.md", json.dumps(data["findings"]))

            # 5. Mutate A: ordinary M2A staleness, propagated transitively.
            accepted_bytes = (ctx["project"] / CH / NODES["a"]).read_bytes()
            (ctx["project"] / CH / NODES["a"]).write_text("# Proposal\nrewritten\n")
            cp, data = self.check(ctx)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.states(data),
                             {A: "invalid", B: "needs-revalidation", C: "needs-revalidation"})
            self.assertEqual(set(self.codes(data)), {"artifact-not-valid"})

            # 6. Restore exact accepted bytes.
            (ctx["project"] / CH / NODES["a"]).write_bytes(accepted_bytes)
            cp, data = self.check(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

            # 7. Add sibling D to the graph only. MANDATORY: nothing goes stale.
            self.declare(ctx, {"a": [], "b": ["a"], "c": ["a", "b"], "d": []})
            cp, data = self.check(ctx)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["missing-accepted-record"])
            self.assertEqual(self.states(data), {A: "valid", B: "valid", C: "valid"},
                             "adding a sibling must not make any artifact stale")

            # 8. Accept D — satisfied again.
            self.accept_and_record(ctx, "d")
            self.assertEqual(self.check(ctx)[0].returncode, 0)

            # 9. Require B -> D. B's bytes never moved; only topology diverged.
            self.declare(ctx, {"a": [], "b": ["a", "d"], "c": ["a", "b"], "d": []})
            cp, data = self.check(ctx)
            self.assertEqual(cp.returncode, 1)
            self.assertEqual(self.codes(data), ["missing-required-edge"])
            self.assertEqual(self.states(data),
                             {A: "valid", B: "valid", C: "valid", D: "valid"},
                             "an edge addition must not rewrite artifact content validity")
            self.assertEqual(data["findings"][0]["artifact"], B)
            self.assertEqual(data["findings"][0]["related"], [D])

            # 10. Re-author and re-reflect B against A and D, under the same contract.
            self.accept_and_record(ctx, "b", deps=["a", "d"], body="# Design\nrevised against D.\n")
            cp, data = self.check(ctx)
            self.assertEqual(cp.returncode, 1, "C was reviewed against the older B")
            self.assertEqual(self.states(data)[C], "needs-revalidation")
            self.accept_and_record(ctx, "c", deps=["a", "b"], body="# Spec\nrevised.\n")
            cp, data = self.check(ctx)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(data["findings"], [])

            # 11. Run tree removed: identical structural findings, provenance degrades only.
            with_run = self.check(ctx)[1]
            archived = ctx["root"] / "archived-run"
            shutil.move(str(ctx["project"] / "DeepSeekAndDestroy"), str(archived))
            cp, without = self.check(ctx, run_root=False)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(without["findings"], with_run["findings"])
            self.assertEqual(self.states(without), self.states(with_run))
            self.assertEqual({a["provenance"] for a in without["artifacts"]}, {"unavailable"})
            self.assertEqual({a["provenance"] for a in with_run["artifacts"]}, {"verified"})

            # 12. Restore the run tree: provenance returns independently.
            shutil.move(str(archived), str(ctx["project"] / "DeepSeekAndDestroy"))
            cp, restored = self.check(ctx)
            self.assertEqual(cp.returncode, 0)
            self.assertEqual({a["provenance"] for a in restored["artifacts"]}, {"verified"})

    # ---------- authority ----------

    def test_a_worker_writing_the_graph_is_caught_by_the_inherited_write_boundary(self):
        """No graph-specific blocker: the inherited integrity gate already refuses."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": []})
            author = self.launch(ctx, "a", "spec-author", mode="forge_graph")
            cp = self.gate(ctx, "a")
            gate = json.loads(cp.stdout)
            self.assertFalse(gate["integrity_ok"])
            self.assertTrue(any("WRITE-RESTRICTION" in e for e in gate["errors"]), gate["errors"])
            self.assertTrue(any("graph.json" in e for e in gate["errors"]), gate["errors"])
            acc = self.sh([PYTHON, str(ROOT / "scripts" / "dsd_state.py"), "accept-task",
                           "--run-root", str(ctx["run"].resolve()), "--phase-id", "spec",
                           "--task-id", "CH-001-a", "--evidence-gate",
                           str(author / "evidence-gate.json")])
            self.assertNotEqual(acc.returncode, 0)
            self.assertIn("integrity gate is not clean", acc.stderr)

    def test_withdrawal_lets_authority_remove_a_node(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": [], "b": ["a"]})
            ctx["ledger"].write_text(json.dumps(
                {"format": "proofbound-change-ledger-v1",
                 "artifact_identity": "proofbound-artifact-text-v1", "artifacts": {}},
                indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self.accept_and_record(ctx, "a")
            self.accept_and_record(ctx, "b", deps=["a"])
            self.assertEqual(self.check(ctx)[0].returncode, 0)

            # Authority drops B from the topology; its record is now undeclared.
            self.declare(ctx, {"a": []})
            cp, data = self.check(ctx)
            self.assertEqual(self.codes(data), ["undeclared-member"])

            withdraw = [PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "withdraw",
                        "--ledger", str(ctx["ledger"]), "--project-root", str(ctx["project"]),
                        "--artifact", str(ctx["project"] / CH / NODES["b"])]
            self.assertEqual(self.sh(withdraw).returncode, 0)
            self.assertEqual(self.check(ctx)[0].returncode, 0)

    def test_withdrawal_refuses_to_orphan_a_recorded_dependency(self):
        """Removing A while B depends on it would make the ledger unloadable."""
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            self.declare(ctx, {"a": [], "b": ["a"]})
            ctx["ledger"].write_text(json.dumps(
                {"format": "proofbound-change-ledger-v1",
                 "artifact_identity": "proofbound-artifact-text-v1", "artifacts": {}},
                indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self.accept_and_record(ctx, "a")
            self.accept_and_record(ctx, "b", deps=["a"])
            cp = self.sh([PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "withdraw",
                          "--ledger", str(ctx["ledger"]), "--project-root", str(ctx["project"]),
                          "--artifact", str(ctx["project"] / CH / NODES["a"])])
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("still a recorded dependency", cp.stderr)

    def test_withdrawing_an_absent_record_fails_cleanly(self):
        with contextlib.ExitStack() as stack:
            ctx = self.scratch(stack)
            ctx["ledger"].write_text(json.dumps(
                {"format": "proofbound-change-ledger-v1",
                 "artifact_identity": "proofbound-artifact-text-v1", "artifacts": {}},
                indent=2, sort_keys=True) + "\n", encoding="utf-8")
            cp = self.sh([PYTHON, str(ROOT / "scripts" / "pb_ledger.py"), "withdraw",
                          "--ledger", str(ctx["ledger"]), "--project-root", str(ctx["project"]),
                          "--artifact", str(ctx["project"] / CH / NODES["a"])])
            self.assertEqual(cp.returncode, 2)
            self.assertIn("no accepted record to withdraw", cp.stderr)


if __name__ == "__main__":
    unittest.main()
