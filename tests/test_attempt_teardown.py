"""The host controller owns termination, because nothing inside the boundary can.

The worker runs under `sandbox-exec` with a profile that denies `signal`. A deadline enforced from
in there cannot be enforced: the monitor exits, the launcher exits, and the controller returns a
normal-looking classification while the worker and its descendants keep running.

Reproduced through the real front door on macOS before this existed — a 5 second deadline returned
after 26.7 s and left the worker (reparented to init) and a `setsid` grandchild that ignores
`SIGTERM` both alive. These tests hold that closed.

Credential-free throughout: the worker is a local fake and no provider is reached.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/pb_workflow.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

#: A worker that blocks and leaves behind a grandchild in its own session which ignores SIGTERM —
#: the shape that neither a group signal nor an ancestry walk alone would catch.
BLOCKING = r'''#!PYTHON
import os, subprocess, sys, time
args = sys.argv[1:]
if args[:2] == ['session', 'list']:
    print('[]'); sys.exit()
subprocess.Popen([sys.executable, '-c',
                  'import os,signal,time\nos.setsid()\n'
                  'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                  'open(os.environ["PB_CHILD_PIDFILE"],"w").write(str(os.getpid()))\n'
                  'time.sleep(3000)'])
time.sleep(3000)
'''


def alive(pid):
    if pid is None:
        return None
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True          # a process we cannot signal is the opposite of one that stopped
    except OSError:
        return False
    return True


class TeardownUnitTest(unittest.TestCase):
    """The parts that need no sandbox, so they run everywhere."""

    def test_an_unreadable_process_table_is_unknown_not_empty(self):
        import _attempt_teardown as teardown

        original = teardown._process_table
        teardown._process_table = lambda: None
        try:
            record = teardown.stop_attempt(Path("/nonexistent/runtime"), Path("/nonexistent/run"))
        finally:
            teardown._process_table = original
        self.assertTrue(record["table_unavailable"])
        self.assertFalse(record["stopped"])
        self.assertTrue(teardown.survivors_remain(record),
                        "not knowing is not the same as nothing surviving")
        self.assertIn("could not be read", record["summary"])

    def test_nothing_running_is_said_plainly_and_is_not_a_stop(self):
        import _attempt_teardown as teardown

        with tempfile.TemporaryDirectory() as raw:
            record = teardown.stop_attempt(Path(raw), Path(raw))
        self.assertTrue(record["nothing_was_running"])
        self.assertTrue(record["stopped"])
        self.assertFalse(teardown.survivors_remain(record))
        self.assertIn("no process", record["summary"])


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class HostControllerTerminationTest(unittest.TestCase):
    """The real front door, the real boundary, a worker that will not stop by itself."""

    def build(self, *, deadline, margin):
        from test_operator_workflow import FAKE            # noqa: F401  (shape reference only)
        import _workflow_boundary as boundary
        from _execution_view import Policy, SYSTEM_EXECS

        tmp = Path(tempfile.mkdtemp(prefix="pb-teardown-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        project = tmp / "project"; project.mkdir()
        (project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n")
        (project / "README.md").write_text("# p\n")
        for argv in [("init", "-q"), ("config", "user.name", "T"),
                     ("config", "user.email", "t@e.invalid"), ("add", "."), ("commit", "-qm", "i")]:
            subprocess.run(["git", "-C", str(project), *argv], check=True)
        fake = tmp / "bin/opencode"; fake.parent.mkdir()
        fake.write_text(BLOCKING.replace("PYTHON", sys.executable)); fake.chmod(0o755)

        start = subprocess.run([sys.executable, str(CLI), "start", "--project", str(project),
                                "--goal", "x", "--check", f"{sys.executable} -c pass",
                                "--executor", str(fake)], capture_output=True, text=True)
        self.assertEqual(start.returncode, 0, start.stderr)
        run = Path(json.loads(start.stdout)["run"])
        config = json.loads((run / "run-config.json").read_text())
        runtime = Path(config["home"]).parent
        self.addCleanup(shutil.rmtree, runtime, True)

        # Resolved paths only: the sandbox sees /private/var/..., and a rule naming /var/... denies.
        resolved = Path(config["paths"]["project"]).resolve()
        tools = runtime / "tools"; tools.mkdir(exist_ok=True)
        boundary.stage_interpreter(tools)
        staged = tools / "opencode"
        if not staged.exists():
            os.link(fake, staged)
        reads = [str(ROOT), str(resolved), str(runtime), str(Path(sys.prefix).resolve()),
                 str(Path(sys.executable).resolve().parents[1]),
                 "/opt/homebrew/Cellar", "/opt/homebrew/opt", "/opt/homebrew/lib"]
        policy = Policy(extra_reads=reads, system_execs=(*SYSTEM_EXECS, *reads[3:]),
                        network=False, notifications=True)
        profile = runtime / "boundary.sb"
        # As authorization builds it, including the start-up rules a new run's settings require.
        from _executor_startup import boundary_rules
        rules = boundary_rules(config["home"])
        profile.write_text(boundary.profile_text(
            runtime, tools, resolved, policy,
            protected=[path for kind, path in rules if kind == "literal"],
            protected_trees=[path for kind, path in rules if kind == "subpath"]))

        pidfile = resolved / "child.pid"
        config.update(mode="offline-test", auto_flag="", boundary_profile=str(profile),
                      executor={**config["executor"], "path": str(staged)},
                      policy=dict(aggregate_limit=1, reserve=.05, launch_ceiling=12, repair_cycles=1),
                      deadline={"seconds": deadline, "host_margin_seconds": margin,
                                "teardown_grace_seconds": 3},
                      worker_env={"PB_CHILD_PIDFILE": str(pidfile)})
        (run / "run-config.json").write_text(json.dumps(config))
        return run, pidfile, runtime

    def drive_to_launch(self, run):
        for _ in range(6):
            cp = subprocess.run([sys.executable, str(CLI), "continue", "--run", str(run)],
                                capture_output=True, text=True, timeout=600)
            payload = json.loads(cp.stdout)
            if "launch" in payload:
                return payload["launch"]
        self.fail("never reached a launch")

    def test_a_blocked_worker_and_its_setsid_grandchild_are_both_stopped(self):
        run, pidfile, runtime = self.build(deadline=5, margin=15)
        launch = self.drive_to_launch(run)

        child = int(pidfile.read_text()) if pidfile.is_file() else None
        self.assertIsNotNone(child, "the fake worker never started its grandchild")
        self.assertFalse(alive(child), "the grandchild outlived the attempt")

        termination = launch.get("termination")
        self.assertIsNotNone(termination, "a blocked worker must produce a termination record")
        self.assertEqual(termination["survivors"], [], termination["summary"])
        self.assertTrue(termination["stopped"])
        # Delivery is not death: the record must rest on a liveness sweep, and say so.
        self.assertIn("confirmed stopped", termination["summary"])

        # Nothing that named this runtime is left behind.
        table = subprocess.run(["/bin/ps", "-Ao", "pid=,command="], capture_output=True, text=True)
        stragglers = [l for l in table.stdout.splitlines() if str(runtime) in l]
        self.assertEqual(stragglers, [], "processes naming this runtime survived the attempt")

    def test_the_host_bound_fires_before_the_launcher_gives_up(self):
        """The two bounds are independent, and the host's is the one that always applies.

        The in-boundary launcher takes its own time to conclude — measured at ~26 s for a 5 s
        deadline, because its teardown grace runs even though the signals it sends cannot be
        delivered. A host bound shorter than that fires first, which is the path that must work
        when the launcher does not return at all.
        """
        run, pidfile, runtime = self.build(deadline=3, margin=5)
        launch = self.drive_to_launch(run)

        self.assertTrue(launch.get("deadline", {}).get("expired"),
                        "the host bound should have fired")
        self.assertEqual(launch["deadline"]["worker_seconds"], 3)
        self.assertEqual(launch["deadline"]["host_bound_seconds"], 8)
        self.assertIn("monotonic", launch["deadline"]["clock"])
        self.assertIn("provider", launch["deadline"]["note"],
                      "terminating locally says nothing about provider billing")
        self.assertEqual(launch["termination"]["survivors"], [])
        child = int(pidfile.read_text()) if pidfile.is_file() else None
        self.assertFalse(alive(child))

    def test_a_timed_out_attempt_is_recorded_and_does_not_start_a_replacement(self):
        run, pidfile, runtime = self.build(deadline=3, margin=5)
        launch = self.drive_to_launch(run)
        receipts = [json.loads(p.read_text()) for p in (run / "receipts").glob("*.json")]
        deadlines = [r for r in receipts if r["action"] == "attempt deadline"]
        self.assertTrue(deadlines, "a terminated attempt must leave a receipt")
        # One attempt, one slot. A deadline is not permission to try again.
        ledger = json.loads((run / "launch-ledger.json").read_text())
        self.assertEqual(len(ledger["slots"]), 1, "timeout must not create a new trajectory")


if __name__ == "__main__":
    unittest.main()
