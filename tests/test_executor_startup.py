"""How the pinned executor starts: reproducibly, without runtime downloads, and diagnosably.

Credential-free; no provider is reached. What each group falsifies, rather than restates:

* the failed qualification's mechanism — given a cached model catalogue that lists the requested
  model as `deprecated`, the pinned executor fails at its first model step with no request made,
  and prints only an error reference; its cause reaches stderr only when its log is sent there;
* staging — a new run's executor configuration directory holds exactly the bytes the executor
  writes itself, and its boundary denies writes there and to the catalogue cache, while earlier
  revisions and legacy runs record no start-up policy and keep their settings digests;
* refusal — a cached catalogue, a leftover lock or breaker, an altered configuration directory, a
  `.opencode` directory or a boundary without the rules refuses a launch before a slot is reserved;
* the repaired path — through the front door with the DeepSeek profile, a dummy credential and a
  stand-in provider: consecutive attempts complete with no npm registry request, no catalogue
  written and no lock left; a model lookup failure keeps its cause in `worker.log`; an attempt
  stopped by the host leaves nothing for the next one to inherit.

The stand-in substitutes the provider endpoint (through `OPENCODE_CONFIG` in the run's worker
environment) and the credential value (a dummy in a fake `HOME`). Everything else — start,
authorization, the boundary, the launcher, the executor bytes and its start-up — is production.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _executor_startup as startup                                        # noqa: E402
import _worker_profiles as profiles                                        # noqa: E402
import _host_serial                                                        # noqa: E402
from _workflow_boundary import profile_text                                # noqa: E402

CLI = ROOT / "scripts" / "pb_workflow.py"
DUMMY_AUTH = {"deepseek": {"type": "api", "key": "sk-proofbound-dummy-not-a-key"}}

#: DeepSeek's entry as models.dev served it on 2026-09-24, trimmed to two models. The only
#: difference between them that matters here is `status`.
_MODEL = {"attachment": True, "cost": {"cache_read": 0.003, "input": 0.15, "output": 0.6,
                                        "reasoning": 0.6},
          "family": "deepseek-flash", "interleaved": {"field": "reasoning_content"},
          "knowledge": "2025-05", "last_updated": "2026-09-10",
          "limit": {"context": 1000000, "output": 393216},
          "modalities": {"input": ["text", "image"], "output": ["text"]}, "open_weights": True,
          "reasoning": True, "reasoning_options": [{"type": "toggle"}, {"type": "effort",
                                                   "values": ["low", "high", "max"]}],
          "release_date": "2026-09-10", "structured_output": True, "temperature": True,
          "tool_call": True}


def catalogue(*, deprecated: bool) -> dict:
    v4 = {**_MODEL, "id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash"}
    if deprecated:
        v4["status"] = "deprecated"
    return {"deepseek": {"id": "deepseek", "env": ["DEEPSEEK_API_KEY"],
                         "npm": "@ai-sdk/openai-compatible", "api": "https://api.deepseek.com",
                         "name": "DeepSeek", "doc": "https://api-docs.deepseek.com/",
                         "models": {"deepseek-flash": {**_MODEL, "id": "deepseek-flash",
                                                       "name": "DeepSeek V4.1 Flash"},
                                    "deepseek-v4-flash": v4}}}


def setUpModule():
    _host_serial.serialise(__name__)


def tearDownModule():
    _host_serial.release()


def git_project(root: Path) -> Path:
    project = root / "project"
    project.mkdir()
    (project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n")
    (project / "README.md").write_text("# p\n")
    for args in (("init", "-q"), ("config", "user.name", "T"),
                 ("config", "user.email", "t@example.invalid"), ("add", "."),
                 ("commit", "-qm", "i")):
        subprocess.run(["git", "-C", str(project), *args], check=True)
    return project


class Registry:
    """A stand-in npm registry that records every request and serves none."""

    def __init__(self):
        hits = self.hits = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):                                     # noqa: N802 - http.server API
                hits.append(self.path)
                self.send_response(503)
                self.send_header("content-length", "0")
                self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Settings(unittest.TestCase):
    def test_the_current_revision_records_the_policy_and_earlier_ones_are_unchanged(self):
        current = profiles.resolve()
        self.assertEqual(current["profile"]["revision"], "2026-09-24")
        self.assertEqual(current["executor"]["startup"], startup.POLICY)
        self.assertIn("deprecated", current["provider"]["catalogue"]["not_used"])
        self.assertEqual(current["billing"]["table"], "deepseek-2026-09-23")
        earlier = profiles._deepseek({**profiles.BUILTIN[profiles.DEFAULT_PROFILE],
                                      "revision": "2026-09-23"},
                                     {"source": "builtin", "path": None, "source_sha256": None})
        self.assertNotIn("startup", earlier["executor"])
        # The digest the four qualification runs of 2026-09-24 froze.
        self.assertEqual(profiles.settings_digest(earlier),
                         "7aa8ef0d05e9ea23bb46bc4314cf5f559574eecdb37e6430dd6c4ae7abbbe7b4")
        legacy = profiles.legacy({"model": "deepseek/deepseek-v4-flash", "variant": "high"})
        self.assertNotIn("startup", legacy["executor"])

    def test_a_local_profile_starts_the_executor_the_same_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            path.write_text(json.dumps({
                "format": profiles.PROFILE_FORMAT, "id": "local-test", "kind": profiles.LOCAL_KIND,
                "endpoint": "http://127.0.0.1:18080/v1", "model": "m",
                "limits": {"context": 8192, "output": 1024}, "tool_call": True}))
            self.assertEqual(profiles.resolve(path)["executor"]["startup"], startup.POLICY)


class StagingAndRefusal(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="pb-startup-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home, self.project = self.root / "home", self.root / "project"
        self.home.mkdir()
        self.project.mkdir()
        startup.stage(self.home)
        self.boundary = "".join(f'(deny file-write* ({kind} "{path}"))\n'
                                for kind, path in startup.boundary_rules(self.home))

    def problems(self, boundary="default"):
        return startup.problems(startup.observe(self.home, self.project), home=self.home,
                                boundary_text=self.boundary if boundary == "default" else boundary)

    def test_the_staged_directory_is_what_the_executor_writes_itself(self):
        directory = startup.config_dir(self.home)
        self.assertEqual(sorted(p.name for p in directory.iterdir()),
                         [".gitignore", "opencode.jsonc"])
        self.assertEqual((directory / "opencode.jsonc").read_bytes(),
                         b'{\n  "$schema": "https://opencode.ai/config.json"\n}')
        self.assertEqual(self.problems(), [])

    def test_each_inherited_state_is_refused_and_named(self):
        cases = {
            "cached model catalogue": lambda: (startup.catalogue(self.home).parent.mkdir(
                parents=True), startup.catalogue(self.home).write_text("{}")),
            "left": lambda: (startup.locks(self.home) / "a.lock.breaker").mkdir(parents=True),
            "no longer holds": lambda: (startup.config_dir(self.home) / "node_modules").mkdir(),
            "would be loaded": lambda: (self.project / ".opencode").mkdir(),
        }
        for words, plant in cases.items():
            with self.subTest(state=words):
                self.setUp()
                plant()
                found = self.problems()
                self.assertEqual(len(found), 1, found)
                self.assertIn(words, found[0])

    def test_an_edited_staged_file_is_refused(self):
        (startup.config_dir(self.home) / "opencode.jsonc").write_text('{"plugin": ["x"]}')
        self.assertIn("no longer holds", " ".join(self.problems()))

    def test_a_boundary_without_the_rules_is_refused(self):
        self.assertIn("does not deny writes", " ".join(self.problems(boundary="(version 1)")))
        self.assertIn("does not deny writes", " ".join(self.problems(boundary=None)))
        # The suite's offline injection has no boundary to check; the state checks still run.
        unbounded = startup.problems(startup.observe(self.home, self.project), home=self.home,
                                     boundary_text=None, bounded=False)
        self.assertEqual(unbounded, [])
        (self.project / ".opencode").mkdir()
        self.assertIn("would be loaded", " ".join(startup.problems(
            startup.observe(self.home, self.project), home=self.home, boundary_text=None,
            bounded=False)))

    def test_the_boundary_text_carries_the_rules(self):
        from _execution_view import Policy
        text = profile_text(self.root, self.root / "tools", self.project, Policy(),
                            protected=[str(startup.catalogue(self.home))],
                            protected_trees=[str(startup.config_dir(self.home))])
        self.assertEqual(startup.problems(startup.observe(self.home, self.project),
                                          home=self.home, boundary_text=text), [])


def pinned_executor():
    for candidate in (Path.home() / ".proofbound/executors/opencode-1.18.29-darwin-arm64/opencode",
                      shutil.which("opencode")):
        if candidate and Path(candidate).resolve().is_file():
            path = Path(candidate).resolve()
            if hashlib.sha256(path.read_bytes()).hexdigest() == profiles.OPENCODE_SHA256:
                return path
    return None


def sandbox_available():
    return Path("/usr/bin/sandbox-exec").exists() and subprocess.run(
        ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)", "/usr/bin/true"],
        capture_output=True).returncode == 0


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class RealExecutor(unittest.TestCase):
    """The pinned OpenCode with DeepSeek's provider id against a scripted loopback stand-in."""

    def setUp(self):
        self.executor = pinned_executor()
        if self.executor is None:
            self.skipTest("the pinned OpenCode 1.18.29 build is not installed on this host")
        if not sandbox_available():
            self.skipTest("sandbox-exec cannot start inside this process")
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-startup-real-", dir="/private/tmp"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = git_project(self.tmp)
        self.fake_home = self.tmp / "fake-home"
        (self.fake_home / ".local/share/opencode").mkdir(parents=True)
        (self.fake_home / ".local/share/opencode/auth.json").write_text(json.dumps(DUMMY_AUTH))
        self.registry = Registry()
        self.addCleanup(self.registry.close)

    def cli(self, *args, ok=True):
        cp = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                            text=True, stdin=subprocess.DEVNULL,
                            env={**os.environ, "HOME": str(self.fake_home)})
        if ok:
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return json.loads(cp.stdout)

    def run_with(self, endpoint, *, redirect_extra=None, deadline=None):
        """A DeepSeek run through start and authorize-spending, its provider on the stand-in."""
        run = Path(self.cli("start", "--project", self.project, "--goal", "Write R1.",
                            "--check", f"{sys.executable} -c pass", "--executor", self.executor,
                            "--deadline-seconds", 60)["run"])
        self.cli("authorize-spending", "--run", run, "--aggregate-limit", 0.15, "--reserve", 0.05,
                 "--launch-ceiling", 3, "--owner-authorization",
                 "TEST ONLY: dummy credential; provider redirected to a loopback stand-in")
        path = run / "run-config.json"
        config = json.loads(path.read_text())
        self.addCleanup(shutil.rmtree, Path(config["home"]).parent, True)
        runtime = Path(config["home"]).parent
        redirect = runtime / "provider-redirect.json"      # inside the boundary's readable tree
        redirect.write_text(json.dumps({"provider": {"deepseek": {
            "options": {"baseURL": endpoint.url}, **(redirect_extra or {})}}}))
        config["worker_env"] = {"OPENCODE_CONFIG": str(redirect),
                                "npm_config_registry": self.registry.url}
        if deadline:
            config["deadline"] = deadline
        path.write_text(json.dumps(config, indent=2))
        return run, config

    def test_a_cached_catalogue_that_deprecates_the_model_fails_before_any_request(self):
        """The failed qualification's mechanism, on the pinned bytes, outside Proofbound."""
        from _stand_in_endpoint import StandInEndpoint
        outcomes = {}
        with StandInEndpoint(model="deepseek-v4-flash") as endpoint:
            for deprecated, print_logs in ((True, False), (True, True), (False, False)):
                home = self.tmp / f"home-{deprecated}-{print_logs}"
                (home / ".local/share/opencode").mkdir(parents=True)
                (home / ".local/share/opencode/auth.json").write_text(json.dumps(DUMMY_AUTH))
                (home / ".cache/opencode").mkdir(parents=True)
                (home / ".cache/opencode/models.json").write_text(
                    json.dumps(catalogue(deprecated=deprecated)))
                redirect = self.tmp / "redirect.json"
                redirect.write_text(json.dumps({"provider": {"deepseek": {
                    "options": {"baseURL": endpoint.url}}}}))
                env = {"HOME": str(home), "LANG": "en_US.UTF-8", "TMPDIR": str(self.tmp),
                       "PATH": f"{self.executor.parent}:/usr/bin:/bin",
                       "OPENCODE_DB": str(home / "worker.db"), "OPENCODE_CONFIG": str(redirect),
                       "OPENCODE_DISABLE_MODELS_FETCH": "1",
                       "npm_config_registry": self.registry.url}
                if print_logs:
                    env["OPENCODE_PRINT_LOGS"] = "1"
                before = len(endpoint.requests)
                cp = subprocess.run([str(self.executor), "run", "--model",
                                     "deepseek/deepseek-v4-flash", "--variant", "high", "--auto",
                                     "--dir", str(self.project), "Say done."],
                                    cwd=self.project, env=env, capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, timeout=120)
                outcomes[(deprecated, print_logs)] = (
                    cp.returncode, len(endpoint.requests) - before, cp.stdout + cp.stderr)
        code, requests, output = outcomes[(True, False)]
        self.assertEqual((code, requests), (1, 0), output[-800:])
        self.assertIn('"ref": "err_', output)
        self.assertNotIn("ProviderModelNotFoundError", output)      # the detail nobody kept
        code, requests, output = outcomes[(True, True)]
        self.assertEqual((code, requests), (1, 0))
        self.assertIn("ProviderModelNotFoundError: Model not found: deepseek/deepseek-v4-flash",
                      output)
        code, requests, output = outcomes[(False, False)]
        self.assertEqual(code, 0, output[-800:])                    # only `status` differed
        self.assertGreater(requests, 0)

    def test_consecutive_attempts_start_without_downloads_or_inherited_state(self):
        from _stand_in_endpoint import StandInEndpoint
        requirements = self.project / "specs" / "CH-001" / "requirements.md"
        with StandInEndpoint(model="deepseek-v4-flash", roles={
                "spec-author": {"files": {str(requirements): "# R\n\nR1. marker\n"}}}) as ep:
            run, config = self.run_with(ep)
            home = Path(config["home"])
            self.assertIn(f'(deny file-write* (subpath "{startup.config_dir(home)}"))',
                          Path(config["boundary_profile"]).read_text())
            launches = []
            for _ in range(4):
                got = self.cli("continue", "--run", run)
                if got.get("launch"):
                    launches.append(got["launch"])
                if got.get("action") == "adjudicate":
                    break
            self.assertEqual([l["status"] for l in launches], ["completed", "completed"], launches)
        self.assertEqual(self.registry.hits, [])
        self.assertFalse(startup.catalogue(home).exists())
        self.assertFalse(startup.locks(home).exists())
        self.assertEqual(startup.problems(startup.observe(home, self.project), home=home,
                                          boundary_text=Path(config["boundary_profile"])
                                          .read_text()), [])
        for launch in launches:
            event = Path(launch["event_dir"])
            state = json.loads((event / "executor-state.json").read_text())
            self.assertEqual((state["before"]["locks"], state["after"]["locks"]), ({}, {}))
            self.assertIsNone(state["after"]["catalogue_cache"])
            self.assertTrue(state["host_sweep"]["nothing_was_running"])
            self.assertIn("level=INFO", (event / "worker.log").read_text())

    def test_a_model_lookup_failure_keeps_its_cause(self):
        from _stand_in_endpoint import StandInEndpoint
        with StandInEndpoint(model="deepseek-v4-flash") as ep:
            run, _ = self.run_with(ep, redirect_extra={"blacklist": ["deepseek-v4-flash"]})
            self.cli("continue", "--run", run)
            launch = self.cli("continue", "--run", run)["launch"]
            requests = len(ep.requests)
        self.assertEqual((launch["status"], launch["returncode"], requests),
                         ("process-error", 1, 0))
        log = (Path(launch["event_dir"]) / "worker.log").read_text()
        self.assertRegex(log, r'message=failed ref=err_\w+ error="ProviderModelNotFoundError')

    def test_a_planted_catalogue_or_lock_is_refused_before_a_slot_is_reserved(self):
        from _stand_in_endpoint import StandInEndpoint
        with StandInEndpoint(model="deepseek-v4-flash") as ep:
            run, config = self.run_with(ep)
            home = Path(config["home"])
            plants = {"cached model catalogue": startup.catalogue(home),
                      "did not finish": startup.locks(home) / "x.lock.breaker"}
            self.cli("continue", "--run", run)                  # bind the contract
            for words, path in plants.items():
                with self.subTest(state=words):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}") if path.suffix == ".json" else path.mkdir()
                    launch = self.cli("continue", "--run", run)["launch"]
                    self.assertFalse(launch["launched"])
                    self.assertIn(words, " ".join(launch["why"]))
                    ledger = json.loads((run / "launch-ledger.json").read_text()) \
                        if (run / "launch-ledger.json").exists() else {"slots": []}
                    self.assertEqual(ledger.get("slots", []), [])
                    shutil.rmtree(path) if path.is_dir() else path.unlink()
            self.assertEqual(ep.requests, [])

    def test_an_attempt_stopped_by_the_host_leaves_nothing_to_inherit(self):
        from _stand_in_endpoint import StandInEndpoint

        class Stalled(StandInEndpoint):
            def _respond(self, request, path, headers):
                time.sleep(20)
                return super()._respond(request, path, headers)

        with Stalled(model="deepseek-v4-flash") as ep:
            run, config = self.run_with(ep, deadline={
                "seconds": 5, "host_margin_seconds": 2, "teardown_grace_seconds": 2})
            self.cli("continue", "--run", run)
            launch = self.cli("continue", "--run", run)["launch"]
        home = Path(config["home"])
        self.assertTrue(launch.get("deadline", {}).get("expired") or launch["status"] == "timeout",
                        launch)
        state = json.loads((Path(launch["event_dir"]) / "executor-state.json").read_text())
        self.assertEqual(state["after"]["locks"], {})
        self.assertIsNone(state["after"]["catalogue_cache"])
        self.assertEqual(self.registry.hits, [])
        self.assertEqual(startup.problems(startup.observe(home, self.project), home=home,
                                          boundary_text=Path(config["boundary_profile"])
                                          .read_text()), [])


if __name__ == "__main__":
    unittest.main()
