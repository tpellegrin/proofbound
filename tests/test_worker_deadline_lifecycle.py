"""The attempt deadline, enforced where the worker is actually owned.

Before this, the only limit anywhere in the chain was the controller's own
`subprocess.run(timeout=...)` on its child. That bounds how long the *controller* waits. It does
not bound the worker: `dsd_attempt.py launch` detaches the monitor into its own session, the
monitor owned the worker through an unbounded `proc.wait()`, and `wait_worker.py` polled with a
default that was larger than the controller's patience. A controller that gave up therefore left a
worker running — still calling a provider — while the view it ran in was destroyed underneath it.

These tests drive the real `run_worker.py` with fake `opencode` executables and short deadlines.
Nothing here asserts that a timeout argument was passed; every case checks that the processes are
gone and that the evidence the attempt produced survived being stopped.

No provider, no network, no cost.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))

import run_worker  # noqa: E402

PROTOCOL_NAMES = (
    'COMMON.md', 'PROOF-PATTERNS.md', 'roles/dsd-implementer/SKILL.md', 'roles/dsd-fixer/SKILL.md',
    'roles/dsd-reviewer/SKILL.md', 'roles/dsd-verification/SKILL.md', 'roles/dsd-discovery/SKILL.md',
    'roles/dsd-phase-surveyor/SKILL.md', 'roles/dsd-recovery/SKILL.md',
    'roles/dsd-phase-auditor/SKILL.md', 'roles/dsd-evidence-clerk/SKILL.md')

#: Deadlines are deliberately short. Where a test needs to observe a state rather than a duration
#: it polls for it, so the suite does not depend on how fast this machine happens to be.
DEADLINE = 1.0
POLL_LIMIT = 30.0


def alive(pid: int) -> bool:
    """Whether a pid is still a live process, as opposed to reaped or never ours."""
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def wait_until(predicate, limit: float = POLL_LIMIT, interval: float = 0.02) -> bool:
    """Poll for a state instead of sleeping for a guess."""
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class StopWorkerTest(unittest.TestCase):
    """`run_worker.stop_worker`, against real processes rather than a mock."""

    maxDiff = None

    def spawn(self, script: str, *, own_session: bool = True):
        """Spawn a process and capture its group id, exactly as `child_run` does.

        The capture is part of the contract being tested: taken at spawn, the group stays
        reachable after the direct process is reaped, which is the case where descendants are
        still running and still need stopping.
        """
        proc = subprocess.Popen([PYTHON, "-c", script], stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=own_session)
        self.addCleanup(self._reap, proc)
        try:
            pgid = os.getpgid(proc.pid)
        except OSError:                                     # pragma: no cover
            pgid = None
        return proc, pgid

    def _reap(self, proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError:
                proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - the cleanup of a cleanup
            pass

    def test_a_descendant_that_outlives_its_parent_is_stopped_too(self):
        """The reason a group signal is used at all.

        A stuck attempt is rarely stuck in the process the monitor launched; it is stuck in
        something that process started. Signalling only the direct child leaves the executor's own
        subprocesses alive and still talking to a provider.
        """
        marker = Path(tempfile.mkdtemp(prefix="pb-deadline-")) / "grandchild.pid"
        self.addCleanup(shutil.rmtree, marker.parent, True)
        proc, pgid = self.spawn(textwrap.dedent(f'''
            import os, subprocess, sys, time
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
            open({str(marker)!r}, "w").write(str(child.pid))
            # The parent exits immediately; the descendant keeps running in the same group.
            '''))
        self.assertTrue(wait_until(marker.is_file), "grandchild never reported its pid")
        grandchild = int(marker.read_text())
        self.assertTrue(wait_until(lambda: proc.poll() is not None), "parent should exit on its own")
        self.assertTrue(alive(grandchild), "the descendant should have outlived its parent")

        # The parent is reaped, so the group is no longer discoverable from its pid. Looking it up
        # at this point is the mistake the captured value exists to prevent.
        with self.assertRaises(ProcessLookupError):
            os.getpgid(proc.pid)

        record = run_worker.stop_worker(proc, grace=5.0, pgid=pgid)

        self.assertEqual(record["scope"], "process-group")
        self.assertTrue(record["sigterm"])
        self.assertTrue(wait_until(lambda: not alive(grandchild)),
                        "the descendant survived termination of the group it belonged to")

    def test_a_worker_that_ignores_sigterm_is_escalated_to_sigkill(self):
        ready = Path(tempfile.mkdtemp(prefix="pb-deadline-")) / "ready"
        self.addCleanup(shutil.rmtree, ready.parent, True)
        # Signalled only once the handler is installed. Signalling a process that has not finished
        # booting kills it by default action and the escalation would never be exercised — the
        # first version of this test passed for that reason.
        proc, pgid = self.spawn(textwrap.dedent(f'''
            import signal, time
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            open({str(ready)!r}, "w").write("ready")
            while True:
                time.sleep(0.05)
            '''))
        self.assertTrue(wait_until(ready.is_file), "the worker never installed its handler")

        record = run_worker.stop_worker(proc, grace=2.0, pgid=pgid)

        self.assertTrue(record["sigterm"])
        self.assertTrue(record["sigkill"], "SIGTERM was ignored and nothing escalated")
        self.assertNotIn("unreaped", record)
        self.assertTrue(wait_until(lambda: proc.poll() is not None))

    def test_a_worker_that_exits_first_is_not_an_error(self):
        """The deadline racing a normal exit is expected, and is reported rather than raised."""
        proc, pgid = self.spawn("pass")
        self.assertTrue(wait_until(lambda: proc.poll() is not None))
        record = run_worker.stop_worker(proc, grace=2.0, pgid=pgid)
        self.assertTrue(record["stopped"], record)
        self.assertTrue(record["already_exited"], record)
        self.assertFalse(record["sigterm"], "there was nothing left to signal")
        self.assertNotIn("unreaped", record)

    def test_a_refused_signal_is_never_reported_as_a_stop(self):
        """The distinction the semantic view forces, because inside it every signal is refused.

        `EPERM` and "no such process" are opposite facts. Reporting them alike would let a worker
        that is still running — and still calling a provider — be recorded as terminated, which is
        the one error this whole path exists to avoid. Signalling is stubbed rather than provoked
        for real: the only locally available `EPERM` targets are processes this test does not own.
        """
        class NeverExits:
            pid = 424242
            returncode = None

            def wait(self, timeout=None):
                raise subprocess.TimeoutExpired(cmd="worker", timeout=timeout)

            def send_signal(self, sig):
                raise PermissionError(errno.EPERM, "Operation not permitted")

        def refuse(*_args, **_kwargs):
            raise PermissionError(errno.EPERM, "Operation not permitted")

        original = os.killpg
        os.killpg = refuse
        self.addCleanup(setattr, os, "killpg", original)
        try:
            record = run_worker.stop_worker(NeverExits(), grace=0.05, pgid=NeverExits.pid)
        finally:
            os.killpg = original

        self.assertFalse(record["stopped"], "a refused signal was reported as a stop")
        self.assertTrue(record["unreaped"])
        self.assertNotIn("already_exited", record,
                         "refusal must not be recorded as the process having exited")
        self.assertIn("sigterm_refused", record)
        self.assertIn("sigkill_refused", record)
        self.assertFalse(record["sigterm"])
        self.assertFalse(record["sigkill"])

    def test_it_refuses_to_signal_the_group_the_monitor_is_in(self):
        """Killing its own group would take out the writer of `terminal.json`.

        Nothing this attempt does not own is ever signalled, which is the whole safety argument for
        using a group signal in the first place.
        """
        proc, pgid = self.spawn("import time; time.sleep(600)", own_session=False)
        self.assertEqual(pgid, os.getpgid(0), "test precondition")

        record = run_worker.stop_worker(proc, grace=5.0, pgid=pgid)

        self.assertEqual(record["scope"], "process", "it signalled its own process group")
        self.assertIsNone(record["pgid"])
        self.assertTrue(wait_until(lambda: proc.poll() is not None))


class WorkerDeadlineTest(unittest.TestCase):
    """The real `run_worker.py` lifecycle, with a fake `opencode` and a one-second deadline."""

    maxDiff = None

    #: A fake executor. `--mode` decides how it behaves once the model call would begin.
    FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, signal, subprocess, sys, time
args = sys.argv[1:]
db = pathlib.Path(os.environ["OPENCODE_DB"])
db.parent.mkdir(parents=True, exist_ok=True)
if args[:2] == ["session", "list"]:
    title_file = db.with_suffix(".title")
    title = title_file.read_text() if title_file.exists() else ""
    print(json.dumps([{"id": "ses_fake", "title": title}]))
    raise SystemExit(0)
if not args or args[0] != "run":
    raise SystemExit(2)
db.with_suffix(".title").write_text(args[args.index("--title") + 1])
mode = os.environ["PB_FAKE_MODE"]
sys.stdout.write("fake worker started\n")
sys.stdout.flush()
if mode == "prompt":
    # Finishes well inside the deadline.
    raise SystemExit(0)
if mode == "stall":
    while True:
        time.sleep(0.05)
if mode == "ignore-term":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(0.05)
if mode == "descendant":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    pathlib.Path(os.environ["PB_FAKE_DESCENDANT"]).write_text(str(child.pid))
    while True:
        time.sleep(0.05)
raise SystemExit(2)
'''

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-deadline-lifecycle-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def worker_rules(self, run: Path):
        revision = run / "worker-rules" / "r0001"
        rules = revision / "WORKER_RULES.md"
        rules.parent.mkdir(parents=True, exist_ok=True)
        rules.write_text("rules")
        protocol = revision / "protocol"
        protocol.mkdir(exist_ok=True)
        digest = hashlib.sha256()
        for name in PROTOCOL_NAMES:
            path = protocol / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
            digest.update(name.encode()); digest.update(b"\0")
            digest.update(path.read_bytes()); digest.update(b"\0")
        state = {
            "revision": 1, "path": str(rules.resolve()),
            "sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
            "protocol_dir": str(protocol.resolve()),
            "protocol_fingerprint": digest.hexdigest(),
            "protocol": {n: hashlib.sha256((protocol / n).read_bytes()).hexdigest()
                         for n in PROTOCOL_NAMES},
        }
        manifest = revision / "MANIFEST.json"
        manifest.write_text(json.dumps({"format": "dsd-worker-rules-manifest-v2", **state},
                                       indent=2, sort_keys=True) + "\n")
        return rules

    def launch(self, mode: str, *, timeout: float | None = DEADLINE, grace: float = 2.0,
               detach: bool = False):
        """Run the real monitor against the fake executor and return its event directory."""
        project = self.tmp / mode / "project"
        run = project / "DeepSeekAndDestroy" / "run"
        run.mkdir(parents=True)
        bin_dir = self.tmp / mode / "bin"
        bin_dir.mkdir(parents=True)
        fake = bin_dir / "opencode"
        fake.write_text(self.FAKE)
        fake.chmod(0o755)

        prompt = run / "prompt.txt"; prompt.write_text("Do task")
        report = run / "report.md"
        scope = run / "scope-baseline.json"; scope.write_text("{}\n")
        contract = run / "U1-contract.md"
        contract.write_text("# Task U1\n## Allowed source changes\nNONE\n\n")
        rules = self.worker_rules(run)
        event_dir = run / "event"
        log = event_dir / "worker.log"
        db = self.tmp / mode / "external" / "workers.db"
        self.descendant_marker = self.tmp / mode / "descendant.pid"

        # PATH is *replaced*, not prepended to. Inheriting the host's PATH leaves a real
        # `opencode` reachable, and `run_worker` resolves the executable by name — so a harness
        # that merely puts a fake in front is one ordering mistake away from launching the real
        # executor against real credentials. This was not hypothetical: an earlier revision of
        # this file built `env` and forgot to pass it, and the real 1.18.30 binary ran.
        env = os.environ.copy()
        env["PATH"] = os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])
        env["PB_FAKE_MODE"] = mode
        env["PB_FAKE_DESCENDANT"] = str(self.descendant_marker)
        resolved = shutil.which("opencode", path=env["PATH"])
        self.assertEqual(resolved, str(fake),
                         "refusing to launch: `opencode` does not resolve to this test's fake")

        argv = [PYTHON, str(ROOT / "scripts" / "run_worker.py"),
                "--project-root", str(project), "--run-root", str(run),
                "--task-id", "U1", "--role", "implementer",
                "--prompt-file", str(prompt), "--task-contract", str(contract),
                "--worker-rules", str(rules), "--scope-baseline", str(scope),
                "--report", str(report), "--event-dir", str(event_dir),
                "--log", str(log), "--db", str(db), "--auto-flag", ""]
        if timeout is not None:
            argv += ["--timeout", str(timeout)]
        argv += ["--termination-grace", str(grace)]
        if detach:
            argv.append("--detach")
        cp = subprocess.run(argv, text=True, capture_output=True, check=False, env=env)
        return event_dir, log, cp

    def terminal(self, event_dir: Path) -> dict:
        path = event_dir / "terminal.json"
        self.assertTrue(wait_until(path.is_file), f"no terminal.json under {event_dir}")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_a_worker_that_finishes_inside_the_deadline_is_untouched(self):
        event_dir, log, cp = self.launch("prompt", timeout=60.0)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        terminal = self.terminal(event_dir)
        self.assertEqual(terminal["status"], "completed")
        self.assertFalse(terminal["timed_out"])
        self.assertIsNone(terminal["termination"])
        self.assertEqual(terminal["timeout_seconds"], 60.0)
        self.assertLess(terminal["worker_monotonic_seconds"], 60.0)
        self.assertIn("fake worker started", log.read_text())

    def test_a_stalled_worker_is_stopped_at_the_deadline_and_its_evidence_survives(self):
        started = time.monotonic()
        event_dir, log, cp = self.launch("stall")
        took = time.monotonic() - started

        terminal = self.terminal(event_dir)
        self.assertEqual(terminal["status"], "timeout")
        self.assertTrue(terminal["timed_out"])
        self.assertEqual(terminal["timeout_seconds"], DEADLINE)
        self.assertTrue(terminal["termination"]["sigterm"])
        self.assertNotIn("unreaped", terminal["termination"])
        self.assertFalse(alive(terminal["worker_pid"]), "the worker outlived its own deadline")

        # It actually stopped, rather than being reported as stopped.
        self.assertLess(took, 60.0, "the deadline did not bound the attempt")
        self.assertGreaterEqual(terminal["worker_monotonic_seconds"], DEADLINE)

        # Evidence recovery: the log, the report binding and the scope freeze all survive being
        # terminated, which is what makes a timed-out attempt auditable instead of merely lost.
        self.assertIn("fake worker started", log.read_text())
        self.assertIsNotNone(terminal["terminal_report"])
        self.assertIsNotNone(terminal["terminal_scope"])
        self.assertTrue((event_dir / "attempt.json").is_file())

    def test_a_worker_that_ignores_sigterm_is_still_stopped(self):
        event_dir, _log, _cp = self.launch("ignore-term")
        terminal = self.terminal(event_dir)
        self.assertEqual(terminal["status"], "timeout")
        self.assertTrue(terminal["termination"]["sigterm"])
        self.assertTrue(terminal["termination"]["sigkill"], "nothing escalated past SIGTERM")
        self.assertFalse(alive(terminal["worker_pid"]))

    def test_a_descendant_of_the_worker_does_not_survive_the_deadline(self):
        event_dir, _log, _cp = self.launch("descendant")
        terminal = self.terminal(event_dir)
        self.assertEqual(terminal["status"], "timeout")
        self.assertTrue(wait_until(self.descendant_marker.is_file),
                        "the fake worker never reported a descendant")
        descendant = int(self.descendant_marker.read_text())
        self.assertTrue(wait_until(lambda: not alive(descendant)),
                        "a tool subprocess outlived the attempt that started it")
        self.assertFalse(alive(terminal["worker_pid"]))

    def test_the_deadline_is_enforced_when_the_controller_is_not_waiting_at_all(self):
        """The case the old arrangement could not handle.

        `--detach` returns immediately, so nothing upstream is waiting on this worker. The limit
        has to live with the monitor that owns it, and this is the test that it does: no controller
        is present to notice, and the worker is stopped anyway.
        """
        event_dir, _log, cp = self.launch("stall", detach=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        launched = json.loads(cp.stdout)
        self.assertEqual(launched["status"], "launched")

        terminal = self.terminal(event_dir)
        self.assertEqual(terminal["status"], "timeout")
        self.assertTrue(terminal["timed_out"])
        self.assertFalse(alive(terminal["worker_pid"]))

    def test_an_omitted_deadline_still_waits_without_a_bound(self):
        """Other callers of this script are unchanged; the limit is opt-in by argument."""
        event_dir, _log, cp = self.launch("prompt", timeout=None)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        terminal = self.terminal(event_dir)
        self.assertEqual(terminal["status"], "completed")
        self.assertFalse(terminal["timed_out"])
        self.assertIsNone(terminal["timeout_seconds"])

    def test_the_launcher_forwards_the_deadline_into_the_monitors_argv(self):
        """End to end through the real `dsd_attempt.py launch`, with a fake executor.

        Two earlier versions of this test were not tests. The first grepped the source; the second
        only exercised `argparse`. Deleting both forwarding lines in `dsd_attempt.launch` left the
        suite green in each case. What establishes the forward is the monitor's own
        `terminal.json`: `timeout_seconds` is written from the value `run_worker` was given, so if
        the launcher drops it the field comes back `None`.
        """
        sys.path.insert(0, str(ROOT / "scripts"))

        project = self.tmp / "forward" / "project"
        run = project / "DeepSeekAndDestroy" / "run"
        run.mkdir(parents=True)
        bin_dir = self.tmp / "forward" / "bin"
        bin_dir.mkdir(parents=True)
        fake = bin_dir / "opencode"
        fake.write_text(self.FAKE)
        fake.chmod(0o755)

        # The launcher captures a scope baseline with `--git-dirty`, so the project root has to be
        # a real repository, as it is for a staged arm.
        (project / "PLAN.md").write_text("Plan.\n", encoding="utf-8")
        for argv in (["git", "init", "-q"],
                     ["git", "config", "user.email", "t@test.invalid"],
                     ["git", "config", "user.name", "T"],
                     ["git", "add", "PLAN.md"],
                     ["git", "commit", "-qm", "base"]):
            done = subprocess.run(argv, cwd=project, capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        contract = run / "contract.md"
        contract.write_text("# Task T\n## Allowed source changes\nNONE\n\n", encoding="utf-8")
        db = self.tmp / "forward" / "external" / "workers.db"
        # The revision is created by `prepare_worker_rules.py` below, which owns it and refuses to
        # overwrite one that already exists — so this test must not pre-create its own.

        prep = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
             "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
             "--plan", str((project / "PLAN.md").resolve())],
            capture_output=True, text=True, check=False)
        if prep.returncode != 0:
            self.fail(f"could not prepare worker rules: {prep.stderr[:300]}")

        (run / "state.json").write_text(json.dumps({
            "project_worktree": str(project.resolve()),
            "execution_status": "active",
            "next_action": "launch implementer",
            "worker_rules": json.loads(prep.stdout),
            "worker_runtime": {"harness": "opencode-cli", "model": "fake/model",
                               "opencode": {"run_db": str(db.resolve())}},
            "phases": {"build": {"status": "in-progress", "tasks": {"T": {
                "status": "prepared",
                "current_contract": {
                    "revision": 1, "path": str(contract.resolve()),
                    "sha256": hashlib.sha256(contract.read_bytes()).hexdigest()}}}}},
        }), encoding="utf-8")

        env = os.environ.copy()
        env["PATH"] = os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])
        env["PB_FAKE_MODE"] = "prompt"
        env["PB_FAKE_DESCENDANT"] = str(self.tmp / "forward" / "unused.pid")
        self.assertEqual(shutil.which("opencode", path=env["PATH"]), str(fake),
                         "refusing to launch: `opencode` does not resolve to this test's fake")

        done = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "dsd_attempt.py"), "launch",
             "--run-root", str(run), "--phase-id", "build", "--task-id", "T",
             "--role", "implementer", "--auto-flag=", "--timeout", "90",
             "--termination-grace", "5"],
            capture_output=True, text=True, check=False, env=env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

        terminals = sorted(run.rglob("terminal.json"))
        self.assertEqual(len(terminals), 1, f"expected one terminal event, got {terminals}")
        terminal = json.loads(terminals[0].read_text(encoding="utf-8"))
        self.assertEqual(terminal["status"], "completed", terminal)
        self.assertEqual(terminal["timeout_seconds"], 90.0,
                         "the launcher did not forward the deadline to the monitor")
        self.assertFalse(terminal["timed_out"])

    def test_both_clocks_are_recorded_so_neither_can_be_mistaken_for_the_other(self):
        """The confusion this milestone exists to close.

        b1 reported slot durations of 5,440 s against a 1,800 s limit and they were not in conflict:
        the limit is monotonic and the reported duration was wall clock, which on a suspended host
        is a strictly larger and different quantity. A record that states one number cannot be read
        safely, so the terminal event states both.
        """
        event_dir, _log, _cp = self.launch("prompt", timeout=60.0)
        terminal = self.terminal(event_dir)
        self.assertIn("worker_monotonic_seconds", terminal)
        self.assertIn("worker_wall_seconds", terminal)
        self.assertIsInstance(terminal["worker_monotonic_seconds"], float)
        self.assertIsInstance(terminal["worker_wall_seconds"], float)


class SandboxSignalTest(unittest.TestCase):
    """The measurement the whole design rests on: the view forbids signalling.

    This is why the deadline cannot be enforced by the monitor that owns the worker, and why the
    controller has to do it from outside. If this ever stops being true the enforcement could move
    inward, so it is asserted rather than remembered.
    """

    maxDiff = None

    #: The child is spawned in its own session on purpose — that is the real configuration, and it
    #: is also the only safe one to probe with: signalling its *own* group is permitted, so a probe
    #: whose child shared its group would kill the probe instead of demonstrating the refusal.
    PROBE = (
        "import json, os, signal, subprocess, sys, time\n"
        "child = subprocess.Popen(['/usr/bin/python3', '-c',\n"
        "                          'import time\\nwhile True: time.sleep(0.05)'],\n"
        "                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,\n"
        "                         start_new_session=True)\n"
        "time.sleep(0.3)\n"
        "out = {}\n"
        "try:\n"
        "    os.kill(child.pid, signal.SIGTERM); out['kill'] = 'delivered'\n"
        "except OSError as exc:\n"
        "    out['kill'] = 'errno=%d' % exc.errno\n"
        "try:\n"
        "    os.killpg(os.getpgid(child.pid), signal.SIGTERM); out['killpg'] = 'delivered'\n"
        "except OSError as exc:\n"
        "    out['killpg'] = 'errno=%d' % exc.errno\n"
        "try:\n"
        "    out['child_exited'] = child.wait(timeout=1.0)\n"
        "except subprocess.TimeoutExpired:\n"
        "    out['child_exited'] = None\n"
        "out['child_pid'] = child.pid\n"
        "print(json.dumps(out))\n"
    )

    def _reap_from_outside(self, pid: int) -> None:
        """Kill a process the sandboxed probe could not, and wait for it to actually go."""
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            return
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except OSError:
                return
            time.sleep(0.05)

    @unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").exists(),
                         "the macOS sandbox mechanism is not available on this platform")
    def test_a_process_inside_the_view_cannot_signal_even_its_own_child(self):
        sys.path.insert(0, str(ROOT / "evals"))
        import _semantic_view

        with _semantic_view.semantic_view() as view:
            done = view.run(["/usr/bin/python3", "-c", self.PROBE], timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        got = json.loads(done.stdout)
        # The probe's whole point is that the child survived being signalled from inside the view,
        # so it is still running and nothing inside the view could ever reap it. The controller is
        # outside and can, which is the same asymmetry the repair depends on. Earlier revisions of
        # this test left one immortal process on the host per run.
        self.addCleanup(self._reap_from_outside, got["child_pid"])
        self.assertEqual(got["kill"], "errno=%d" % errno.EPERM,
                         "the view now permits signalling; enforcement could move inward")
        self.assertEqual(got["killpg"], "errno=%d" % errno.EPERM)
        self.assertIsNone(got["child_exited"], "the child was stopped despite the refusal")


class ControllerEnforcementTest(unittest.TestCase):
    """The enforcement that takes effect for a real slot, through the real view.

    The fake executor spawns the three shapes that each defeated an earlier revision of this
    repair: a tool subprocess that ignores SIGTERM, one that leaves the process group via
    `setsid`, and — supplied by the launcher itself, not the fake — a `wait_worker` helper that
    the launcher never records and that inherits the controller's own process group.
    """

    maxDiff = None

    FAKE = (
        "#!/usr/bin/python3\n"
        "import os, pathlib, signal, subprocess, sys, time\n"
        "a = sys.argv[1:]\n"
        "db = pathlib.Path(os.environ['OPENCODE_DB'])\n"
        "db.parent.mkdir(parents=True, exist_ok=True)\n"
        "if a[:2] == ['session', 'list']:\n"
        "    print('[]'); raise SystemExit(0)\n"
        "if a and a[0] == 'run':\n"
        "    stubborn = subprocess.Popen(['/usr/bin/python3', '-c',\n"
        "        \"import signal,time\\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\\n\"\n"
        "        \"while True: time.sleep(0.05)\"])\n"
        "    escapee = subprocess.Popen(['/usr/bin/python3', '-c',\n"
        "        'import time\\nwhile True: time.sleep(0.05)'], start_new_session=True)\n"
        "    db.parent.joinpath('kids.json').write_text(\n"
        "        '{\"stubborn\": %d, \"escapee\": %d}' % (stubborn.pid, escapee.pid))\n"
        "    sys.stdout.write('stalling\\n'); sys.stdout.flush()\n"
        "    while True:\n"
        "        time.sleep(0.05)\n"
        "raise SystemExit(2)\n"
    )

    #: Substrings that identify a process this attempt started. A bare pid diff would also count
    #: whatever the operating system happened to launch during the seconds the attempt ran.
    SIGNATURE = ("pb-sem-", "pb-tool-", "pb-fake-executor-", "wait_worker", "fake/model",
                 "time.sleep(0.05)")

    def attempt_processes(self) -> dict[int, str]:
        done = subprocess.run(["/bin/ps", "-Ao", "pid=,command="], capture_output=True, text=True,
                              check=False)
        found = {}
        for line in done.stdout.splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[0].isdigit() and any(k in parts[1]
                                                              for k in self.SIGNATURE):
                found[int(parts[0])] = parts[1][:120]
        return found

    @unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").exists(),
                         "the macOS sandbox mechanism is not available on this platform")
    def test_a_stalled_slot_is_stopped_at_the_deadline_and_nothing_is_left_running(self):
        """Not "a signal was sent": every pid is checked, and so is the whole host afterwards.

        This is the case b1's arrangement could not handle. The controller's wait would expire,
        `subprocess.run` would kill `sandbox-exec`, and the detached monitor and its worker would
        keep running in their own sessions while the view was destroyed around them.
        """
        sys.path.insert(0, str(ROOT / "evals"))
        import _mlr
        import _mlr_boundary
        import _semantic_view

        holder = Path(tempfile.mkdtemp(prefix="pb-fake-executor-",
                                       dir=_semantic_view.DEFAULT_PARENT))
        self.addCleanup(shutil.rmtree, holder, True)
        fake = holder / "opencode"
        fake.write_text(self.FAKE)
        fake.chmod(0o755)

        before = set(self.attempt_processes())
        started = time.monotonic()
        got = _mlr_boundary.run_bounded_attempt(
            _mlr.CONTRACT, model="fake/model", variant=None, executor=fake,
            fixture=ROOT / "evals" / "craft" / "modularity-local-reasoning" / "fixture-b",
            timeout=4)
        took = time.monotonic() - started

        self.assertTrue(got["timed_out"])
        self.assertEqual(got["terminal_status"], "controller-timeout")
        self.assertEqual(got["validity"], "harness-failure")
        self.assertEqual(got["attempt_deadline_seconds"], 4)
        self.assertLess(took, 120.0, "the deadline did not bound the attempt")
        self.assertTrue(got["trajectory_began"], "§11 C must govern: commencement happened")

        stop = got["termination"]
        self.assertTrue(stop["stopped"], stop)
        self.assertEqual(stop["survivors"], [], stop)
        self.assertNotIn("nothing_was_running", stop)

        # Every way a process can be owned must actually be exercised here, or this test would
        # pass while the hard cases went unnoticed.
        reasons = {row["owned_because"] for row in stop["owned"]}
        # The two shapes that each defeated an earlier revision must be present. Asserting the
        # exact set would make this fail on a loaded host where the fake's children have not been
        # forked yet inside the four-second deadline — a scheduling accident, not a defect.
        self.assertIn("recorded", reasons, stop["owned"])
        self.assertIn("names-the-view", reasons,
                      "the launcher's own helpers were not recognised as owned")
        self.assertTrue({"process-group", "descends-from-recorded"} & reasons,
                        f"no tool subprocess was recognised at all: {stop['owned']}")
        self.assertGreaterEqual(stop["found"], 3, stop)
        self.assertTrue(stop["escalated"], "a SIGTERM-ignoring child should force SIGKILL")

        # And the host is clean: nothing recognisable as part of this attempt is still alive.
        # Polled, because reaping is not instantaneous.
        def clean() -> bool:
            return not (set(self.attempt_processes()) - before)

        self.assertTrue(wait_until(clean, limit=20.0),
                        f"leaked past the deadline: "
                        f"{ {k: v for k, v in self.attempt_processes().items() if k not in before} }")

        self.assertIn("workspace", got["extraction"], "evidence must survive being stopped")

    @unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/sandbox-exec").exists(),
                         "the macOS sandbox mechanism is not available on this platform")
    def test_nothing_found_is_reported_as_nothing_found(self):
        """`all([])` is `True`, which once turned "found nothing" into "stopped everything"."""
        sys.path.insert(0, str(ROOT / "evals"))
        import _mlr_boundary

        empty = Path(tempfile.mkdtemp(prefix="pb-empty-run-"))
        self.addCleanup(shutil.rmtree, empty, True)
        stop = _mlr_boundary._stop_attempt(Path("/private/tmp/pb-sem-nonexistent-view"), empty,
                                           grace=0.1)
        self.assertEqual(stop["found"], 0)
        self.assertTrue(stop["nothing_was_running"])
        self.assertIn("no process this attempt owned was still running",
                      _mlr_boundary._stop_summary(stop))
        self.assertNotIn("confirmed stopped", _mlr_boundary._stop_summary(stop))

    def test_an_unreadable_attempt_record_does_not_read_as_a_clean_stop(self):
        sys.path.insert(0, str(ROOT / "evals"))
        import _mlr_boundary

        run = Path(tempfile.mkdtemp(prefix="pb-corrupt-run-"))
        self.addCleanup(shutil.rmtree, run, True)
        attempt = run / "phases" / "build" / "tasks" / "T" / "attempts" / "implementer-1"
        attempt.mkdir(parents=True)
        (attempt / "attempt.json").write_text("{ this is not json", encoding="utf-8")

        self.assertEqual(_mlr_boundary._attempt_processes(run), [],
                         "an unreadable record yields no pids")
        stop = _mlr_boundary._stop_attempt(Path("/private/tmp/pb-sem-nonexistent-view"), run,
                                           grace=0.1)
        # Nothing could be identified, and the wording says exactly that rather than claiming
        # everything was stopped.
        self.assertTrue(stop["nothing_was_running"])
        self.assertIn("no process this attempt owned", _mlr_boundary._stop_summary(stop))

    def test_a_recorded_pid_that_no_longer_names_this_view_is_not_signalled(self):
        """Pid reuse. A recorded number that cannot be corroborated is reported, never signalled.

        Otherwise a pid recorded half an hour earlier, exited and reused since, would be signalled
        on the strength of the number alone — and its whole group with it.
        """
        sys.path.insert(0, str(ROOT / "evals"))
        import _mlr_boundary

        # This test's own pid is certainly alive and certainly does not name the view.
        scan = _mlr_boundary._owned_processes(
            Path("/private/tmp/pb-sem-nonexistent-view"), [os.getpid(), os.getppid()])
        self.assertEqual(scan["owned"], [],
                         "the controller's own processes must never be owned")
        self.assertEqual(scan["groups"], [], "nor any group they lead")
        self.assertEqual(scan["uncorroborated"], sorted([os.getpid(), os.getppid()]),
                         "the mismatch must be surfaced, not dropped")
        # And the prose says so too, not just the structured record.
        self.assertIn("could not be corroborated", _mlr_boundary._stop_summary(
            {"found": 0, "stopped": True, "nothing_was_running": True,
             "uncorroborated_pids": scan["uncorroborated"]}))


class DeadlineLayeringTest(unittest.TestCase):
    """That the layers agree on who decides, which is what went wrong originally."""

    maxDiff = None

    def setUp(self):
        sys.path.insert(0, str(ROOT / "evals"))

    def test_the_controller_decides_and_the_in_view_limits_sit_behind_it(self):
        """Reversed from the first attempt at this repair, and for a measured reason.

        Setting the in-view limit first looked safer — let the process that owns the worker decide.
        It cannot: the view denies it any signal, so it would write a `terminal.json` saying
        "timeout" while the worker it could not touch kept running, and that disposition would be
        read as authoritative. The ordering is checked by calling `launch` and reading the argv and
        the timeout it actually used, rather than by grepping the source for a line.
        """
        import _mlr_boundary
        import _mlr_run

        seen: dict[str, Any] = {}

        class FakeView:
            """Just enough view for `launch` to assemble its command and its own wait."""

            root = Path("/private/tmp/pb-sem-fake")
            tools_root = Path("/private/tmp/pb-tool-fake")
            runtime = root / "runtime"
            data = root / "data"

            def run(self, argv, **kw):
                seen["argv"] = list(argv)
                seen["timeout"] = kw.get("timeout")
                return subprocess.CompletedProcess(argv, 0, "{}", "")

        staged = {"binaries": Path("/b"), "harness": Path("/h"), "run": Path("/r"),
                  "db": Path("/d/worker.db")}
        _mlr_boundary.launch(FakeView(), staged, variant=None,
                             cleared={"status": "clean"}, timeout=100)

        self.assertEqual(seen["timeout"], 100,
                         "the controller's own wait must be the deadline itself")
        argv = seen["argv"]
        inner = float(argv[argv.index("--timeout") + 1])
        self.assertGreater(inner, 100, "the in-view limit must sit behind the controller's")
        self.assertEqual(inner, 100 + _mlr_run.TERMINATION_GRACE_SECONDS
                         + _mlr_boundary.INNER_DEADLINE_MARGIN_SECONDS)
        self.assertIn("--termination-grace", argv)

    def test_a_timeout_never_authorises_a_fresh_trajectory(self):
        """§11 C: commencement occurred, so the slot is spent whatever the deadline did.

        The record is the shape the controller really writes — no `launch_returncode`, because the
        timeout branch returns before one is assigned.
        """
        import _mlr_series
        timed_out = {"item": "contract", "repeat": 3, "validity": "harness-failure",
                     "trajectory_began": True, "timed_out": True,
                     "terminal_status": "controller-timeout"}
        self.assertEqual(_mlr_series.execution_stage(timed_out), _mlr_series.WORKER_EXECUTED)
        # The other branch: a deadline the monitor noticed arrives with a non-zero launch return
        # code, and leaving it in place would classify the slot `launcher-refused` — the launcher
        # declining to start a worker that in fact ran. The controller drops it for that reason,
        # and this is what would break if it stopped doing so.
        self.assertEqual(
            _mlr_series.execution_stage({**timed_out, "launch_returncode": 1}),
            _mlr_series.LAUNCHER_REFUSED,
            "if this changes, the controller no longer needs to drop the return code")
        account = _mlr_series.spend([timed_out])
        self.assertFalse(account["complete"],
                         "a timed-out attempt with no derived cost is unknown, not free")
        self.assertEqual(account["unpriced"][0]["stage"], _mlr_series.WORKER_EXECUTED)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
