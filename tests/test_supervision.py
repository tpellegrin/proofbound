"""A supervised launch outlives its caller, and an interrupted launch has a supported recovery.

Reproduced before the repair, credential-free, through the real front door:
- **The caller dies with the controller.** Killing the caller of `continue` killed the host
  controller; the worker and its in-boundary monitor ran on without containment or a deadline
  anyone could enforce, and the slot stayed unclassified.
- **A stalled worker outlived its deadline even with the caller alive.** The monitor's signals are
  refused inside the boundary, and the real executor's command line named nothing the host sweep
  could corroborate.

What each group falsifies:
- **The caller.** Exiting it neither stops nor orphans a launch: the supervisor finalizes it, a
  new caller waits for it, and concurrent callers start one supervisor.
- **Every interruption boundary.** Before reservation, after reservation before the worker, while
  it runs and after it ends: `recover` names each state from evidence, and `--apply` makes the one
  change it names, once. It launches nothing, invents no outcome and does not trust a reused pid.
- **A lost supervisor.** An adopting supervisor holds the recorded deadline and stops a stalled
  worker.
- **The real executor.** Stopped by the host after its monitor gives up, and adopted after its
  supervisor is killed.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/pb_workflow.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "tests"))

import _supervision                                                        # noqa: E402
from _attempt_teardown import _owned_processes                             # noqa: E402
import _host_serial                                                        # noqa: E402

#: A worker that sleeps `PB_FAKE_SECONDS` (default: effectively forever) and exits 0.
FAKE = r'''#!PYTHON
import os, sys, time
if sys.argv[1:3] == ['session', 'list']:
    print('[]'); sys.exit()
time.sleep(float(os.environ.get('PB_FAKE_SECONDS', '3000')))
'''


def setUpModule():
    _host_serial.serialise(__name__)


def tearDownModule():
    _host_serial.release()


def sandbox_available():
    return Path("/usr/bin/sandbox-exec").exists() and subprocess.run(
        ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)", "/usr/bin/true"],
        capture_output=True).returncode == 0


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_until(predicate, timeout, step=0.2):
    ends = time.monotonic() + timeout
    while time.monotonic() < ends:
        value = predicate()
        if value:
            return value
        time.sleep(step)
    return predicate()


class Harness:
    """A run with the real boundary and a stand-in worker, driven through the public CLI."""

    def __init__(self, case, *, seconds, deadline=30, margin=5, env=None):
        import _workflow_boundary as boundary
        from _execution_view import Policy, SYSTEM_EXECS
        from _executor_startup import boundary_rules
        self.case = case
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-sup-test-", dir="/private/tmp"))
        case.addCleanup(self.cleanup)
        project = self.tmp / "project"
        project.mkdir()
        (project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n")
        (project / "README.md").write_text("# p\n")
        for argv in [("init", "-q"), ("config", "user.name", "T"),
                     ("config", "user.email", "t@e.invalid"), ("add", "."), ("commit", "-qm", "i")]:
            subprocess.run(["git", "-C", str(project), *argv], check=True)
        fake = self.tmp / "bin/opencode"
        fake.parent.mkdir()
        fake.write_text(FAKE.replace("PYTHON", sys.executable))
        fake.chmod(0o755)
        self.env = {**os.environ, **(env or {})}
        start = self.cli("start", "--project", project, "--goal", "x", "--check",
                         f"{sys.executable} -c pass", "--executor", fake)
        self.run = Path(start["run"])
        config = json.loads((self.run / "run-config.json").read_text())
        self.runtime = Path(config["home"]).parent
        resolved = Path(config["paths"]["project"]).resolve()
        tools = self.runtime / "tools"
        tools.mkdir(exist_ok=True)
        boundary.stage_interpreter(tools)
        staged = tools / "opencode"
        os.link(fake, staged)
        reads = [str(ROOT), str(resolved), str(self.runtime), str(Path(sys.prefix).resolve()),
                 str(Path(sys.executable).resolve().parents[1]),
                 "/opt/homebrew/Cellar", "/opt/homebrew/opt", "/opt/homebrew/lib"]
        policy = Policy(extra_reads=reads, system_execs=(*SYSTEM_EXECS, *reads[3:]),
                        network=False, notifications=True)
        rules = boundary_rules(config["home"])
        profile = self.runtime / "boundary.sb"
        profile.write_text(boundary.profile_text(
            self.runtime, tools, resolved, policy,
            protected=[p for k, p in rules if k == "literal"],
            protected_trees=[p for k, p in rules if k == "subpath"]))
        config.update(mode="offline-test", auto_flag="", boundary_profile=str(profile),
                      executor={**config["executor"], "path": str(staged)},
                      policy=dict(aggregate_limit=1, reserve=.05, launch_ceiling=12,
                                  repair_cycles=1),
                      deadline={"seconds": deadline, "host_margin_seconds": margin,
                                "teardown_grace_seconds": 2},
                      worker_env={"PB_FAKE_SECONDS": str(seconds)})
        (self.run / "run-config.json").write_text(json.dumps(config))
        self.cli("continue", "--run", self.run)              # bind the contract; no launch yet

    def cleanup(self):
        for row in _owned_processes(self.runtime, [])["owned"]:
            try:
                os.kill(row["pid"], signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        record = _supervision.read_active(self.run) if hasattr(self, "run") else None
        if record and _supervision.alive(record):
            os.kill(record["pid"], signal.SIGKILL)
        shutil.rmtree(self.tmp, True)
        if hasattr(self, "runtime"):
            shutil.rmtree(self.runtime, True)

    def cli(self, *args, env=None):
        cp = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                            text=True, stdin=subprocess.DEVNULL, env=env or self.env, timeout=300)
        return json.loads(cp.stdout)

    def caller(self, *args, env=None):
        """`continue` in its own process session, as a coordinator host's shell would be."""
        return subprocess.Popen([sys.executable, str(CLI), *map(str, args)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL, env=env or self.env, text=True,
                                start_new_session=True)

    def kill(self, proc):
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()

    def attempt(self):
        found = sorted(self.run.glob("phases/*/tasks/*/attempts/*"))
        return found[-1] if found else None

    def terminal(self):
        a = self.attempt()
        path = a / "terminal.json" if a else None
        return json.loads(path.read_text()) if path and path.is_file() else None

    def slots(self):
        path = self.run / "launch-ledger.json"
        return ([(s["slot"], s["classification"]) for s in json.loads(path.read_text())["slots"]]
                if path.is_file() else [])

    def result(self):
        """The last supervisor's recorded result, written whether or not anyone was waiting."""
        found = sorted(_supervision.directory(self.run).glob("*.result.json"),
                       key=lambda p: p.stat().st_mtime)
        return json.loads(found[-1].read_text()) if found else None

    def owned(self):
        return _owned_processes(self.runtime, [])["owned"]

    def running_worker(self):
        a = self.attempt()
        return bool(a and (a / "attempt.json").is_file())


class AttachmentRace(unittest.TestCase):
    """`continue` waits on the launch it saw running, even when that launch finishes at once.

    Found in review of `ab99c5e`: `continue` read the supervision record, judged it running, then
    read it again to wait. A supervisor that finished in between had removed it, and the second
    read's `None` raised `TypeError`. Portable: the interleaving is injected, no boundary needed.
    """

    def setUp(self):
        import pb_workflow
        from unittest import mock
        self.pb, self.mock = pb_workflow, mock
        self.run = Path(tempfile.mkdtemp(prefix="pb-attach-"))
        self.addCleanup(shutil.rmtree, self.run, True)
        self.record = {"format": _supervision.RECORD_FORMAT, "token": "a" * 32, "mode": "launch",
                       "pid": 424242, "process_start": "x", "stage": "running"}
        # Whatever happens, `continue` must not derive a new action or launch anything.
        for name in ("_status", "config_for"):
            patcher = mock.patch.object(pb_workflow, name, side_effect=AssertionError(name))
            patcher.start()
            self.addCleanup(patcher.stop)

    def attach(self, *, alive, reads):
        with self.mock.patch.object(_supervision, "read_active", side_effect=reads), \
                self.mock.patch.object(_supervision, "alive", side_effect=alive):
            return self.pb.continue_run(self.run)

    def result(self, payload):
        _supervision._write(_supervision._result_path(self.run, self.record["token"]), payload)

    def test_a_launch_that_finishes_between_the_reads_is_still_reported(self):
        self.result({"launched": True, "status": "completed"})
        got = self.attach(alive=[True], reads=[self.record, None, None])["launch"]
        self.assertEqual((got["status"], got["supervisor"]["token"], got["supervisor"]["attached"]),
                         ("completed", self.record["token"], True))

    def test_a_launch_that_vanishes_without_a_result_is_unresolved_not_success(self):
        got = self.attach(alive=[True] + [False] * 20, reads=[self.record, None, None])["launch"]
        self.assertTrue(got["unresolved"])
        self.assertIsNone(got["launched"])
        self.assertIn("recover", " ".join(got["why"]))

    def test_an_ordinary_attachment_waits_for_the_result(self):
        timer = threading.Timer(1.0, self.result, args=({"launched": True, "status": "timeout"},))
        timer.start()
        self.addCleanup(timer.cancel)
        got = self.attach(alive=[True] * 50, reads=[self.record])["launch"]
        self.assertEqual((got["status"], got["supervisor"]["token"]), ("timeout", "a" * 32))


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class CallerExit(unittest.TestCase):
    def setUp(self):
        if not sandbox_available():
            self.skipTest("sandbox-exec cannot start inside this process")

    def test_a_killed_caller_leaves_the_launch_supervised_and_finalized(self):
        h = Harness(self, seconds=4)
        caller = h.caller("continue", "--run", h.run)
        self.assertTrue(wait_until(h.running_worker, 20))
        h.kill(caller)
        running = h.cli("status", "--run", h.run)
        self.assertEqual(running["action"], "running", running)
        self.assertTrue(wait_until(lambda: _supervision.read_active(h.run) is None, 60))
        self.assertEqual(h.slots(), [(1, "executor-reached")])
        self.assertEqual(h.terminal()["status"], "completed")
        self.assertEqual(h.owned(), [])
        self.assertEqual(h.cli("status", "--run", h.run)["action"], "gate")

    def test_a_new_caller_waits_for_the_same_supervisor_and_launches_nothing(self):
        h = Harness(self, seconds=4)
        first = h.caller("continue", "--run", h.run)
        self.assertTrue(wait_until(h.running_worker, 20))
        h.kill(first)
        second = h.cli("continue", "--run", h.run)["launch"]
        self.assertTrue(second["supervisor"]["attached"])
        self.assertEqual(second["status"], "completed")
        self.assertEqual(h.slots(), [(1, "executor-reached")])

    def test_concurrent_callers_start_one_supervisor(self):
        h = Harness(self, seconds=3)
        results = []
        threads = [threading.Thread(target=lambda: results.append(
            h.cli("continue", "--run", h.run))) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(120)
        launches = [r["launch"] for r in results if "launch" in r]
        self.assertEqual(len({l["supervisor"]["token"] for l in launches}), 1, results)
        self.assertEqual(sum(not l["supervisor"]["attached"] for l in launches), 1)
        self.assertEqual(h.slots(), [(1, "executor-reached")])

    def test_a_stalled_worker_whose_caller_is_gone_is_stopped_at_the_deadline(self):
        h = Harness(self, seconds=3000, deadline=2, margin=2)
        caller = h.caller("continue", "--run", h.run)
        self.assertTrue(wait_until(h.running_worker, 20))
        h.kill(caller)
        self.assertTrue(wait_until(lambda: _supervision.read_active(h.run) is None, 90))
        self.assertEqual(h.owned(), [])
        result = h.result()
        self.assertTrue(result["deadline"]["expired"], result)
        self.assertTrue(result["termination"]["stopped"])
        self.assertEqual(h.slots(), [(1, "executor-reached")])


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class InterruptionBoundaries(unittest.TestCase):
    """The supervisor killed at each boundary; `recover` names the state and repairs it once."""

    def setUp(self):
        if not sandbox_available():
            self.skipTest("sandbox-exec cannot start inside this process")

    def interrupted(self, stage, seconds=1):
        h = Harness(self, seconds=seconds)
        faulty = {**h.env, _supervision.FAULT_ENV: stage}
        lost = h.cli("continue", "--run", h.run, env=faulty)["launch"]
        self.assertTrue(lost["unresolved"], lost)
        self.assertEqual(h.cli("status", "--run", h.run)["action"], "blocked")
        before = h.slots()
        refused = h.cli("continue", "--run", h.run)
        self.assertEqual(refused["action"], "blocked", refused)       # nothing new is launched
        self.assertEqual(h.slots(), before)
        return h

    def test_before_reservation_nothing_is_charged_and_the_next_launch_is_the_first(self):
        h = self.interrupted("admitted")
        found = h.cli("recover", "--run", h.run)
        self.assertEqual((found["state"], h.slots()), ("supervisor-ended", []))
        h.cli("recover", "--run", h.run, "--apply")
        self.assertEqual(h.cli("recover", "--run", h.run)["state"], "clear")
        launched = h.cli("continue", "--run", h.run)["launch"]
        self.assertEqual(launched["status"], "completed")
        self.assertEqual(h.slots(), [(1, "executor-reached")])

    def test_after_reservation_before_the_worker_the_slot_is_a_pre_executor_failure(self):
        h = self.interrupted("reserved")
        found = h.cli("recover", "--run", h.run)
        self.assertEqual(found["state"], "pre-executor")
        self.assertEqual(h.slots(), [(1, "unresolved")])
        h.cli("recover", "--run", h.run, "--apply")
        self.assertEqual(h.slots(), [(1, "pre-executor-failure")])
        second = h.cli("continue", "--run", h.run)["launch"]
        self.assertEqual(second["status"], "completed")
        self.assertEqual(h.slots(), [(1, "pre-executor-failure"), (2, "executor-reached")])

    def test_after_the_worker_ends_before_finalization_recovery_classifies_once(self):
        h = self.interrupted("finalizing")
        self.assertEqual(h.terminal()["status"], "completed")
        found = h.cli("recover", "--run", h.run)
        self.assertEqual(found["state"], "terminal-unrecorded")
        applied = h.cli("recover", "--run", h.run, "--apply")["applied"]
        self.assertEqual((applied["classification"], applied["outcome"]),
                         ("executor-reached", "completed"))
        again = h.cli("recover", "--run", h.run, "--apply")
        self.assertEqual((again["state"], again["applied"]), ("clear", None))
        self.assertEqual(h.slots(), [(1, "executor-reached")])
        receipts = [json.loads(p.read_text())["action"] for p in (h.run / "receipts").glob("*")]
        self.assertEqual(receipts.count("launch reconciliation"), 1)
        self.assertEqual(h.cli("status", "--run", h.run)["action"], "gate")

    def test_a_missing_terminal_record_stays_unknown_and_blocks(self):
        h = self.interrupted("finalizing")
        (h.attempt() / "terminal.json").unlink()
        self.assertEqual(h.cli("recover", "--run", h.run)["state"], "no-terminal")
        applied = h.cli("recover", "--run", h.run, "--apply")["applied"]
        self.assertEqual(applied["outcome"], "unknown: no terminal record")
        after = h.cli("status", "--run", h.run)
        self.assertEqual(after["action"], "blocked", after)
        self.assertIn("no terminal record", after["reason"])

    def test_contradictory_evidence_changes_nothing(self):
        h = self.interrupted("finalizing")
        (h.attempt() / "terminal.json").write_text("{not json")
        before = (h.run / "launch-ledger.json").read_bytes()
        found = h.cli("recover", "--run", h.run, "--apply")
        self.assertEqual((found["state"], found["applied"]), ("contradictory", None))
        self.assertEqual((h.run / "launch-ledger.json").read_bytes(), before)

    def test_a_reused_pid_is_not_trusted_and_not_signalled(self):
        h = Harness(self, seconds=1)
        bystander = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(bystander.wait)
        self.addCleanup(bystander.kill)
        from datetime import datetime, timezone
        _supervision._write(_supervision.active_path(h.run), {
            "format": _supervision.RECORD_FORMAT, "token": "f" * 32, "mode": "launch",
            "pid": bystander.pid, "process_start": _supervision._ps(bystander.pid, "lstart"),
            "created_at": datetime.now(timezone.utc).isoformat(), "stage": "running"})
        self.assertEqual(h.cli("status", "--run", h.run)["action"], "blocked")
        self.assertEqual(h.cli("recover", "--run", h.run)["state"], "supervisor-ended")
        h.cli("recover", "--run", h.run, "--apply")
        self.assertTrue(alive(bystander.pid))
        self.assertIsNone(_supervision.read_active(h.run))


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class LostSupervisor(unittest.TestCase):
    def setUp(self):
        if not sandbox_available():
            self.skipTest("sandbox-exec cannot start inside this process")

    def lose_supervisor(self, h):
        caller = h.caller("continue", "--run", h.run)
        self.assertTrue(wait_until(h.running_worker, 20))
        record = _supervision.read_active(h.run)
        os.kill(record["pid"], signal.SIGKILL)
        h.kill(caller)
        self.assertTrue(wait_until(lambda: not alive(record["pid"]), 10))
        return record

    def test_a_running_worker_is_adopted_and_finalized_once(self):
        h = Harness(self, seconds=5)
        self.lose_supervisor(h)
        self.assertEqual(h.cli("status", "--run", h.run)["action"], "blocked")
        refused = h.cli("continue", "--run", h.run)
        self.assertEqual(refused["action"], "blocked")
        found = h.cli("recover", "--run", h.run)
        self.assertEqual((found["state"], found["read_only"]),
                         ("worker-running-unsupervised", True))
        applied = h.cli("recover", "--run", h.run, "--apply")["applied"]
        self.assertTrue(applied["adopted"])
        self.assertEqual(applied["result"]["status"], "completed")
        self.assertEqual(h.slots(), [(1, "executor-reached")])
        self.assertEqual(h.owned(), [])
        self.assertEqual(h.cli("recover", "--run", h.run, "--apply")["state"], "clear")
        self.assertEqual(h.cli("status", "--run", h.run)["action"], "gate")

    def test_a_stalled_worker_is_stopped_by_the_adopter_at_the_recorded_deadline(self):
        h = Harness(self, seconds=3000, deadline=3, margin=3)
        lost = self.lose_supervisor(h)
        self.assertIsNotNone(lost.get("host_deadline_at"))
        applied = h.cli("recover", "--run", h.run, "--apply")["applied"]
        self.assertTrue(applied["result"]["deadline"]["expired"])
        self.assertEqual(h.owned(), [])
        self.assertEqual(h.slots(), [(1, "executor-reached")])

    def test_concurrent_recoveries_adopt_once(self):
        h = Harness(self, seconds=5)
        self.lose_supervisor(h)
        results = []
        threads = [threading.Thread(target=lambda: results.append(
            h.cli("recover", "--run", h.run, "--apply"))) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(120)
        adopted = [r for r in results if (r.get("applied") or {}).get("adopted")]
        self.assertEqual(len(adopted), 1, results)
        other = next(r for r in results if r not in adopted)
        self.assertIn(other["state"], ("supervised", "clear"))
        self.assertIsNone(other["applied"])
        self.assertEqual(h.slots(), [(1, "executor-reached")])
        receipts = [json.loads(p.read_text())["action"] for p in (h.run / "receipts").glob("*")]
        self.assertEqual(receipts.count("supervision adopted"), 1)

    def test_recover_changes_nothing_while_a_supervisor_runs(self):
        h = Harness(self, seconds=4)
        caller = h.caller("continue", "--run", h.run)
        self.assertTrue(wait_until(h.running_worker, 20))
        found = h.cli("recover", "--run", h.run, "--apply")
        self.assertEqual((found["state"], found["applied"]), ("supervised", None))
        caller.communicate(timeout=60)
        self.assertEqual(h.slots(), [(1, "executor-reached")])


def pinned_executor():
    import hashlib
    import _worker_profiles as profiles
    for candidate in (Path.home() / ".proofbound/executors/opencode-1.18.29-darwin-arm64/opencode",
                      shutil.which("opencode")):
        if candidate and Path(candidate).resolve().is_file():
            path = Path(candidate).resolve()
            if hashlib.sha256(path.read_bytes()).hexdigest() == profiles.OPENCODE_SHA256:
                return path
    return None


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class RealExecutor(unittest.TestCase):
    """The pinned executor, DeepSeek's provider id redirected to a scripted loopback endpoint."""

    def setUp(self):
        self.executor = pinned_executor()
        if self.executor is None:
            self.skipTest("the pinned OpenCode 1.18.29 build is not installed on this host")
        if not sandbox_available():
            self.skipTest("sandbox-exec cannot start inside this process")

    def run_with(self, endpoint, deadline=None):
        tmp = Path(tempfile.mkdtemp(prefix="pb-sup-real-", dir="/private/tmp"))
        self.addCleanup(shutil.rmtree, tmp, True)
        home = tmp / "fake-home"
        (home / ".local/share/opencode").mkdir(parents=True)
        (home / ".local/share/opencode/auth.json").write_text(json.dumps(
            {"deepseek": {"type": "api", "key": "sk-proofbound-dummy-not-a-key"}}))
        project = tmp / "project"
        project.mkdir()
        (project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n")
        (project / "README.md").write_text("# p\n")
        for a in (("init", "-q"), ("config", "user.name", "T"),
                  ("config", "user.email", "t@x.invalid"), ("add", "."), ("commit", "-qm", "i")):
            subprocess.run(["git", "-C", str(project), *a], check=True)
        self.env = {**os.environ, "HOME": str(home)}
        run = Path(self.cli("start", "--project", project, "--goal", "Write R1.", "--check",
                            f"{sys.executable} -c pass", "--executor", self.executor,
                            "--deadline-seconds", 60)["run"])
        self.cli("authorize-spending", "--run", run, "--aggregate-limit", 0.15, "--reserve", 0.05,
                 "--launch-ceiling", 3, "--owner-authorization",
                 "TEST ONLY: dummy credential; scripted loopback provider")
        config = json.loads((run / "run-config.json").read_text())
        runtime = Path(config["home"]).parent
        self.addCleanup(shutil.rmtree, runtime, True)
        redirect = runtime / "provider-redirect.json"
        redirect.write_text(json.dumps({"provider": {"deepseek": {
            "options": {"baseURL": endpoint.url}}}}))
        config["worker_env"] = {"OPENCODE_CONFIG": str(redirect)}
        if deadline:
            config["deadline"] = deadline
        (run / "run-config.json").write_text(json.dumps(config, indent=2))
        self.cli("continue", "--run", run)
        self.addCleanup(self.stop_leftovers, runtime)
        return run, runtime

    def stop_leftovers(self, runtime):
        for row in _owned_processes(runtime, [])["owned"]:
            try:
                os.kill(row["pid"], signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

    def cli(self, *args):
        cp = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                            text=True, stdin=subprocess.DEVNULL, env=self.env, timeout=600)
        return json.loads(cp.stdout)

    def test_the_host_stops_a_stalled_worker_after_its_monitor_gives_up(self):
        """Reproduced before the repair: the worker was still running 40 s after its deadline."""
        from _stand_in_endpoint import StandInEndpoint

        class Stalled(StandInEndpoint):
            def _respond(self, request, path, headers):
                time.sleep(300)
                return super()._respond(request, path, headers)

        with Stalled(model="deepseek-v4-flash") as ep:
            run, runtime = self.run_with(ep, deadline={"seconds": 8, "host_margin_seconds": 40,
                                                       "teardown_grace_seconds": 2})
            launch = self.cli("continue", "--run", run)["launch"]
            self.assertEqual(launch["status"], "timeout")
            self.assertIn("confirmed stopped", launch["termination"]["summary"])
            self.assertEqual(_owned_processes(runtime, [])["owned"], [])

    def test_a_killed_supervisor_is_recovered_and_the_attempt_finalized(self):
        from _stand_in_endpoint import StandInEndpoint

        class Slow(StandInEndpoint):
            def _respond(self, request, path, headers):
                time.sleep(4)
                return super()._respond(request, path, headers)

        with Slow(model="deepseek-v4-flash") as ep:
            run, runtime = self.run_with(ep)
            caller = subprocess.Popen([sys.executable, str(CLI), "continue", "--run", str(run)],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      stdin=subprocess.DEVNULL, env=self.env,
                                      start_new_session=True)
            self.assertTrue(wait_until(lambda: any(run.glob(
                "phases/*/tasks/*/attempts/*/attempt.json")), 60))
            record = _supervision.read_active(run)
            os.kill(record["pid"], signal.SIGKILL)
            os.killpg(caller.pid, signal.SIGKILL)
            caller.communicate()
            self.assertEqual(self.cli("recover", "--run", run)["state"],
                             "worker-running-unsupervised")
            applied = self.cli("recover", "--run", run, "--apply")["applied"]
            self.assertEqual(applied["result"]["status"], "completed")
            self.assertEqual(self.cli("status", "--run", run)["action"], "gate")
            self.assertEqual(_owned_processes(runtime, [])["owned"], [])


if __name__ == "__main__":
    unittest.main()
