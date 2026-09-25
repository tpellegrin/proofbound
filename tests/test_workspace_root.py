"""The project-local workspace root: `.proofbound/` for new runs, `DeepSeekAndDestroy/` still honoured.

Stand-ins validate mechanics only. The legacy run here is created by the same `start` code with the
root order reversed, which is exactly what `start` did before `.proofbound/` existed.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CLI = SCRIPTS / "pb_workflow.py"
sys.path.insert(0, str(SCRIPTS))
import _workspace  # noqa: E402
import claude_worker_rewake  # noqa: E402
import context_checkpoint  # noqa: E402

from tests.test_operator_workflow import FAKE  # noqa: E402

#: Runs `pb_workflow.py` exactly as it stood before `.proofbound/`: the legacy root first.
LEGACY_START = (
    "import runpy, sys\n"
    f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
    "import _workspace\n"
    "_workspace.ROOTS = (_workspace.LEGACY_WORKSPACE, _workspace.WORKSPACE)\n"
    f"sys.argv = [{str(CLI)!r}, *sys.argv[1:]]\n"
    f"runpy.run_path({str(CLI)!r}, run_name='__main__')\n"
)


class WorkspaceRules(unittest.TestCase):
    def test_new_runs_go_under_proofbound_and_existing_runs_are_found_where_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            self.assertEqual(_workspace.run_for(project, "C1"),
                             project / ".proofbound" / "plans" / "C1" / "runs" / "first")
            legacy = project / "DeepSeekAndDestroy" / "plans" / "C1" / "runs" / "first"
            legacy.mkdir(parents=True)
            self.assertEqual(_workspace.run_for(project, "C1"), legacy)
            self.assertEqual(_workspace.run_for(project, "C2"),
                             project / ".proofbound" / "plans" / "C2" / "runs" / "first")

    def test_a_run_under_both_roots_is_refused_not_chosen(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            for root in _workspace.ROOTS:
                (project / root / "plans" / "C1" / "runs" / "first").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "more than one workspace root"):
                _workspace.run_for(project, "C1")

    def test_both_roots_are_generated_state_and_nothing_else_is(self):
        for path in (".proofbound", ".proofbound/plans/x", "DeepSeekAndDestroy",
                     "DeepSeekAndDestroy/plans/x/runs/first/state.json", "/.proofbound/"):
            self.assertTrue(_workspace.is_generated(path), path)
        for path in ("specs/C1/goal.md", "src/.proofbound", "proofbound", ".proofboundx/a",
                     "DeepSeekAndDestroyX", "docs/DeepSeekAndDestroy/a"):
            self.assertFalse(_workspace.is_generated(path), path)

    def test_a_run_is_confined_to_a_workspace_root_of_its_own_project(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "p"
            for root in _workspace.ROOTS:
                run = project / root / "plans" / "c" / "runs" / "first"
                self.assertEqual(_workspace.containing(project, run), project / root)
                self.assertEqual(_workspace.project_of(run), project.resolve())
            for outside in (project / "specs" / "c", Path(td) / "other" / ".proofbound" / "x"):
                with self.assertRaisesRegex(ValueError, "must live under"):
                    _workspace.containing(project, outside)

    def test_recovery_discovers_active_runs_under_either_root(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            found = []
            for root in _workspace.ROOTS:
                state = project / root / "plans" / "c" / "runs" / "first" / "state.json"
                state.parent.mkdir(parents=True)
                state.write_text(json.dumps({"execution_status": "in-progress"}))
                found.append(state.resolve())
            self.assertEqual(context_checkpoint.active_state_paths(project), sorted(found))

    def test_rewake_accepts_a_terminal_under_either_root_and_nothing_outside(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td).resolve()
            payload = {"cwd": str(project)}
            with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": ""}):
                for root in _workspace.ROOTS:
                    terminal = project / root / "plans" / "c" / "runs" / "r" / "terminal.json"
                    self.assertEqual(claude_worker_rewake.safe_terminal(terminal, payload), terminal)
                self.assertIsNone(claude_worker_rewake.safe_terminal(project / "specs" / "terminal.json", payload))


class Lifecycle(unittest.TestCase):
    """The real front door, driven to a sealed delivery with the credential-free stand-in."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb workspace "))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = self.tmp / "project"; self.project.mkdir()
        self.fake = self.tmp / "bin/opencode"; self.fake.parent.mkdir()
        self.fake.write_text(FAKE.replace("PYTHON", sys.executable)); self.fake.chmod(0o755)

    def init(self, ignore):
        (self.project / ".gitignore").write_text(ignore)
        (self.project / "README.md").write_text("# Greeting library\n")
        for args in [("init", "-q"), ("config", "user.name", "Test Owner"),
                     ("config", "user.email", "owner@example.invalid"), ("add", "."), ("commit", "-qm", "initial")]:
            subprocess.run(["git", "-C", str(self.project), *args], check=True)

    def run_cli(self, *args, ok=True, legacy=False):
        argv = [sys.executable, "-c", LEGACY_START] if legacy else [sys.executable, str(CLI)]
        cp = subprocess.run([*argv, *map(str, args)], capture_output=True, text=True)
        if ok:
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            return json.loads(cp.stdout)
        self.assertNotEqual(cp.returncode, 0, cp.stdout)
        return cp.stdout + cp.stderr

    def start(self, legacy=False):
        result = self.run_cli("start", "--project", self.project, "--change", "C1",
                              "--goal", "Add a greeting function and tests.",
                              "--check", f"{sys.executable} -m unittest discover",
                              "--executor", self.fake, legacy=legacy)
        run = Path(result["run"])
        config = json.loads((run / "run-config.json").read_text())
        self.addCleanup(shutil.rmtree, Path(config["home"]).parent, True)
        # Test-only injected stand-in, as in test_operator_workflow.
        config["mode"] = "offline-test"
        config["policy"] = dict(aggregate_limit=1, reserve=.05, launch_ceiling=12, repair_cycles=1)
        config["auto_flag"] = ""
        (run / "run-config.json").write_text(json.dumps(config))
        return run

    def deliver(self, run):
        for _ in range(25):
            status = self.run_cli("status", "--run", run)
            if status.get("task") == "implementation" and status["action"] == "adjudicate":
                break
            if status["action"] == "adjudicate":
                self.run_cli("decide", "--run", run, "--decision", "accept", "--reason", "TEST ONLY scripted decision")
            else:
                result = self.run_cli("continue", "--run", run)
                if "launch" in result:
                    self.assertEqual(result["launch"].get("returncode"), 0, result)
        else:
            self.fail("did not reach implementation")
        self.run_cli("decide", "--run", run, "--decision", "accept", "--reason", "TEST ONLY scripted acceptance")
        report = self.tmp / "final.md"
        report.write_text("Added greeting. Stand-in mechanics only, not a real-agent trial.")
        return Path(self.run_cli("finish", "--run", run, "--report", report, "--report-source", "relayed")["delivery"])

    def patched_paths(self, delivery):
        return {line.split(" b/", 1)[1] for line in (delivery / "change.patch").read_text().splitlines()
                if line.startswith("diff --git ")}

    def test_a_new_run_is_created_under_proofbound_and_delivers_without_workflow_state(self):
        # Neither root is ignored, and the legacy root holds an unrelated untracked file: the
        # delivery must still leave out every workspace root by itself.
        self.init("__pycache__/\n")
        stray = self.project / "DeepSeekAndDestroy" / "notes.txt"
        run = self.start()
        stray.parent.mkdir(); stray.write_text("an older run's leftovers\n")
        self.assertEqual(run, self.project.resolve() / ".proofbound" / "plans" / "C1" / "runs" / "first")
        self.assertFalse((self.project / "DeepSeekAndDestroy" / "plans").exists())
        delivery = self.deliver(run)
        paths = self.patched_paths(delivery)
        self.assertIn("greeting.py", paths)
        self.assertTrue(any(p.startswith("specs/C1/") for p in paths), paths)
        # Literal roots, not the predicate under test.
        self.assertFalse([p for p in paths if p.split("/")[0] in (".proofbound", "DeepSeekAndDestroy")], paths)
        baselines = [json.loads(p.read_text()) for p in run.rglob("scope-baseline.json")]
        self.assertTrue(baselines)
        self.assertTrue(all(b["exclude_prefixes"] == [".proofbound"] for b in baselines))

    def test_a_legacy_run_stays_usable_where_it_was_recorded(self):
        self.init("DeepSeekAndDestroy/\n__pycache__/\n")
        run = self.start(legacy=True)
        self.assertEqual(run, self.project.resolve() / "DeepSeekAndDestroy" / "plans" / "C1" / "runs" / "first")
        # The same start today returns that run rather than creating a second one.
        again = self.run_cli("start", "--project", self.project, "--change", "C1",
                             "--goal", "Add a greeting function and tests.", "--executor", self.fake,
                             "--check", f"{sys.executable} -m unittest discover")
        self.assertTrue(again["existing"]); self.assertEqual(Path(again["run"]), run)
        delivery = self.deliver(run)
        self.assertEqual(delivery, run / "delivery")
        paths = self.patched_paths(delivery)
        self.assertIn("greeting.py", paths)
        # Literal roots, not the predicate under test.
        self.assertFalse([p for p in paths if p.split("/")[0] in (".proofbound", "DeepSeekAndDestroy")], paths)
        baselines = [json.loads(p.read_text()) for p in run.rglob("scope-baseline.json")]
        self.assertTrue(all(b["exclude_prefixes"] == ["DeepSeekAndDestroy"] for b in baselines))
        self.assertFalse((self.project / ".proofbound").exists(),
                         "continuing a legacy run created a second workspace")

    def test_start_refuses_a_change_present_under_both_roots_and_changes_nothing(self):
        self.init(".proofbound/\nDeepSeekAndDestroy/\n__pycache__/\n")
        run = self.start()
        twin = self.project / "DeepSeekAndDestroy" / "plans" / "C1" / "runs" / "first"
        shutil.copytree(run, twin)
        before = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file() and ".git" not in p.parts}
        out = self.run_cli("start", "--project", self.project, "--change", "C1",
                           "--goal", "Add a greeting function and tests.", "--executor", self.fake,
                           "--check", f"{sys.executable} -m unittest discover", ok=False)
        self.assertIn("more than one workspace root", out)
        after = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertEqual(before, after)


class AdapterReinstall(unittest.TestCase):
    def test_reinstalling_over_a_legacy_install_replaces_its_hooks_instead_of_adding_more(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"; project.mkdir()
            cmd = [sys.executable, str(SCRIPTS / "install_harness_adapter.py"), "--harness", "claude-code",
                   "--project-root", str(project), "--skill-root", str(ROOT)]
            cp = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            settings = project / ".claude" / "settings.json"
            fresh = json.loads(settings.read_text())
            # What an install made before `.proofbound/` left behind.
            settings.write_text(settings.read_text().replace("/.proofbound/tools/", "/DeepSeekAndDestroy/tools/"))
            cp = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            reinstalled = json.loads(settings.read_text())
            self.assertEqual(reinstalled, fresh)
            self.assertNotIn("DeepSeekAndDestroy", settings.read_text())
            self.assertTrue((project / ".proofbound" / "tools" / "context_checkpoint.py").is_file())
            self.assertFalse((project / "DeepSeekAndDestroy").exists())


if __name__ == "__main__":
    unittest.main()
